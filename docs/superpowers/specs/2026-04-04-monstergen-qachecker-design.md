# MonsterGen + QAChecker Design Spec

**Date:** 2026-04-04
**Phase:** Phase 1 — Content Generation
**Plan:** Plan 02
**Status:** Approved — ready for implementation

---

## Overview

Two agents that together form the first complete content pipeline:

1. **MonsterGen** — reads monster source material, identifies gaps against existing Roll20 NPCs, and generates Roll20-ready JSON for missing monsters using Claude AI
2. **QAChecker** — validates every generated sheet mechanically and with a Claude judgment pass before anything reaches Roll20

The pipeline is fully auditable: each stage produces reviewable output before the next stage runs.

---

## Architecture

Four modules, each with one job:

```
parse_statblocks.py   DCC text + 5e sections → master CSV
gap_analysis.py       CSV vs Roll20 export   → gap report
monster_gen.py        gap list + CSV + Claude → Roll20 JSON
qa_checker.py         mechanical + Claude     → ready or flagged
```

Wired together via `run.py`:

```
python run.py monster --parse
python run.py monster --gap-analysis
python run.py monster --generate [--name "Stirge" | --all]
python run.py qa
```

---

## File Layout

```
agents/in-progress/
  parse_statblocks.py
  gap_analysis.py
  monster_gen.py
  qa_checker.py

data/input/
  thracia-exports/
    thracia-characters.json       # existing Roll20 NPCs (already staged)
  monster-source/
    dcc_statblocks.txt            # raw DCC stat block text (user pastes in)
    lore_5e_sections.txt          # relevant 5e PDF sections (user pastes in)
  master_monsters.csv             # output of parse_statblocks — user reviews before generation

data/output/
  gap_report.txt                  # Stage 2 output — lives at root of output/, not in pending/
  pending/                        # MonsterGen writes JSON here
  ready/                          # QAChecker promotes passing sheets
  flagged/                        # QAChecker holds sheets needing review

docs/
  roll20-npc-schema.md            # already exists in repo — defines all Roll20 field names
```

The Obsidian vault is never read directly. The 5e PDF content is copied into `lore_5e_sections.txt` manually.

---

## Stage 1: parse_statblocks.py

Parses raw source text into a structured master CSV.

### DCC Stat Block Format

Input (`dcc_statblocks.txt`) is raw text copied from the campaign book. Each stat block follows this format:

```
Stirge (1d4): Init +6; Atk bite +0 melee (1d3+1 plus blood drain); Crit M/d4;
AC 10; HD 1d5+1 (hp 4 each); MV 30', fly 60'; Act 1d20;
SP blood drain (1 Stamina, DC 7 Fort save negates);
SV Fort +2, Ref +6, Will +0; AL C.
```

Parser extracts all structured fields using regex. `attacks_raw` and `sp_raw` are stored as-is for Claude to expand during generation.

### 5e Stat Block Format

Input (`lore_5e_sections.txt`) is text copied from the 5e lore PDF. Each 5e stat block follows standard 5e monster format. The parser must extract: name, AC, HP (average), CR, CON/DEX/WIS save bonuses, DEX ability score modifier, speed, and alignment. A complete example showing all required fields:

```
Cave Fisher
Large monstrosity, unaligned

Armor Class 16 (natural armor)
Hit Points 58 (9d10 + 9)
Speed 20 ft., climb 20 ft.

STR  DEX  CON  INT  WIS  CHA
16   13   12   1    10   3
(+3) (+1) (+1) (-5) (0)  (-4)

Saving Throws CON +3, WIS +2
Challenge 3 (700 XP)
```

- **Alignment** is on the creature type line (e.g., `Large monstrosity, unaligned` → `unaligned` → maps to `N`)
- **DEX modifier** is in the ability score block, in parentheses under the DEX column — use this for `init`
- **`Saving Throws` line** provides save bonuses; any save not listed defaults to 0
- **CR** is on the Challenge line
- **Lore section extraction**: a block is identified by a name line immediately followed by a type line matching `<Size> <type>, <alignment>` (e.g. `Large monstrosity, unaligned`). The block continues until a blank line is followed by another name+type pair, or until end of file. Any content that does not match a name+type opening (section headers, tables, footnotes, blank lines) terminates the current block — the parser does not need to interpret such content. The parser indexes blocks by creature name (case-insensitive). If a name match is not found at Stage 3 lookup, an empty string is used as lore context.

### 5e-to-DCC Translation

For monsters sourced only from the 5e lore document, stats are translated to DCC equivalents:

| 5e field | DCC field | Method |
|---|---|---|
| AC | `ac` | Direct carry-over |
| HP (average) | `hp_avg` | Direct carry-over from the printed average |
| CR | `hd` | See CR→HD table below — stored independently of `hp_avg` |
| CON save bonus | `fort` | Direct mapping (absent from Saving Throws line = 0) |
| DEX save bonus | `ref` | Direct mapping (absent from Saving Throws line = 0) |
| WIS save bonus | `will` | Direct mapping (absent from Saving Throws line = 0) |
| Speed | `speed` | Walking speed only; fly speed stored in `fly` column |
| DEX ability modifier | `init` | Parse from ability score block, not from any printed initiative |
| Alignment | `alignment` | LG/LN/LE → L, N/TN/unaligned → N, CG/CN/CE → C |

**`hd` and `hp_avg` are stored independently.** For 5e monsters, `hd` is derived from CR and `hp_avg` is copied from the stat block. They are not guaranteed to be arithmetically consistent. Stage 3 uses `hp_avg` as the authoritative value for `hit_points.max`.

**5e-only monster defaults for fields not present in the 5e format:**

| CSV column | Default for 5e-only | Notes |
|---|---|---|
| `quantity` | `"1"` | 5e encounter tables not used |
| `crit` | `"M/d6"` | Standard DCC default |
| `act` | `"1d20"` | Standard DCC action die |
| `attacks_raw` | parsed from 5e "Actions" block if present; `""` if absent | Parser reads the Actions section of the 5e stat block |
| `sp_raw` | parsed from 5e special ability text if present; `""` if absent | |

**`source = "both"` merge logic:** DCC is authoritative for all numeric/mechanical CSV fields (`ac`, `hd`, `hp_avg`, `init`, `fort`, `ref`, `will`, `speed`, `fly`, `act`, `attacks_raw`, `sp_raw`, `crit`, `quantity`, `alignment`). The 5e version's values for these fields are discarded. The 5e block is retained in the parser's lore index under the monster's name, available to Stage 3 for flavor text only.

### CR → HD Table

| CR | HD |
|---|---|
| CR < ¼ | 1d4 |
| ¼ ≤ CR < ½ | 1d6 |
| ½ ≤ CR < 1 | 1d6 |
| CR = 1 | 1d8 |
| CR = 2 | 2d8 |
| CR = 3 | 3d8 |
| CR = 4 | 4d8 |
| CR ≥ 5 | CR × d8 (e.g. CR 6 → 6d8) |

### Alignment Storage

The master CSV stores alignment as a single character (`C`, `L`, or `N`). Conversion to full words (`"chaotic"`, `"lawful"`, `"neutral"`) happens in `monster_gen.py` when building the Roll20 JSON. The CSV never stores long-form alignment strings.

### Master CSV Schema

| Column | Example | Notes |
|---|---|---|
| `name` | `Stirge` | |
| `quantity` | `1d4` | encounter quantity — written to `description` by Stage 3 |
| `hd` | `1d5+1` | |
| `hp_avg` | `4` | authoritative for `hit_points.max` |
| `ac` | `10` | |
| `init` | `+6` | stored with sign in CSV; converted to plain number in Stage 3 |
| `speed` | `30` | string; walking speed only (all CSV columns are strings) |
| `fly` | `60` | string, optional — empty string `""` if absent; appears in `description` only, not as a Roll20 field |
| `act` | `1d20` | |
| `fort` | `+2` | stored with sign in CSV; converted to plain number in Stage 3 |
| `ref` | `+6` | stored with sign in CSV; converted to plain number in Stage 3 |
| `will` | `+0` | stored with sign in CSV; converted to plain number in Stage 3 |
| `alignment` | `C` | single character: C, L, or N |
| `attacks_raw` | `bite +0 melee (1d3+1 plus blood drain)` | full raw text; multiple attacks separated by `/` |
| `sp_raw` | `blood drain (1 Stamina, DC 7 Fort save negates)` | empty string if absent |
| `crit` | `M/d4` | written to `description` by Stage 3 |
| `source` | `dcc` / `5e` / `both` | set by parser |
| `notes` | | manual review field — passed to Claude in Stage 3 as context |

---

## Stage 2: gap_analysis.py

Compares `master_monsters.csv` against `thracia-characters.json` to identify monsters in the CSV that have no matching character in Roll20.

- Name matching: case-insensitive, whitespace-stripped
- Output: `data/output/gap_report.txt` — one monster name per line, exact CSV casing, no headers or extra decoration. Example:
  ```
  Cave Fisher
  Ochre Jelly
  Phase Spider
  ```
- Stage 3 reads this file as machine input — every line is treated as a monster name to generate
- If all CSV monsters already exist in Roll20, writes an empty file and prints: `No gaps found. Nothing to generate.`
- User reviews the gap report and approves generation before Stage 3 runs

---

## Stage 3: monster_gen.py

Generates a complete Roll20 JSON sheet for each missing monster. Calls the Claude API.

### Idempotency

Both `--generate --all` and `--generate --name "X"` **overwrite** any existing file at the target path in `pending/`. Re-running generation always replaces stale output.

If `gap_report.txt` does not exist or is empty, `--generate --all` prints `No gaps found. Nothing to generate.` and exits 0. (Both cases are treated identically — a missing file is treated as an empty file.)

`--generate --name "X"` bypasses `gap_report.txt` entirely — it generates a sheet for the named monster regardless of whether it appears in the gap report, and regardless of whether the monster already exists in Roll20. This is intentional: `--name` is a force-regenerate command for any monster in the CSV. The named monster must exist in `master_monsters.csv`; if not found, print `Error: Monster 'X' not found in master_monsters.csv` and exit with a non-zero code.

### Filename Sanitization

Output filename: spaces replaced with underscores, special characters stripped. Example: `Cave Fisher` → `cave_fisher.json`. The JSON `name` field retains the original casing from the CSV.

### Claude prompt inputs
- Full CSV row for the monster (all columns including `notes`)
- Contents of `docs/roll20-npc-schema.md`
- Relevant 5e lore block extracted from `lore_5e_sections.txt` by name match (if `source = "both"` or `"5e"`; empty string if `source = "dcc"` or no match found)

### AI-filled fields

**Armor vectors** (written into `description` as `AC: P14/S14/B13.`):
- Natural armor (beasts, undead, monstrosities): all three vectors equal `ac`. Claude infers natural armor from creature type.
- Armored creatures (humanoids described as wearing armor): Claude uses these reference values:
| Armor                | Base AC | S   | P   | B   | max AGL modifier | Check penalty | Speed penalty | Fumble die | Cost  | Examples                           |
| -------------------- | ------- | --- | --- | --- | ---------------- | ------------- | ------------- | ---------- | ----- | ---------------------------------- |
| (Unarmored)          | 10      | 10  | 10  | 10  |                  | -             | -             | d4         | -     |                                    |
| Padded               | 11      | 11  | 11  | 11  | +8               | -             | -             | d6         | 5     | gambeson                           |
| Light armor          | 12      | 12  | 12  | 12  | +4               | -1            | -             | d6         | 20    | cuir boille, linothorax            |
| Improved light armor | 13      | 14  | 14  | 12  | +4               | -2            | -             | d8         | 45    | scaled linothorax, studded leather |
| Scale mail           | 14      | 14  | 15  | 14  | +2               | -3            | -5'           | d10        | 80    | lorica squamata, lamellar          |
| Chain mail           | 15      | 17  | 15  | 13  | +2               | -5            | -5'           | d8         | 100   | lorica hamata, chainmail           |
| Breastplate          | 16      | 17  | 17  | 16  | +1               | -5            | -5'           | d12        | 200   |                                    |
| Banded mail          | 16      | 18  | 17  | 17  | +0               | -5            | -5'           | d12        | 250   | lorica segmentata, laminar         |
| Half-plate           | 17      | 20  | 18  | 17  | +0               | -7            | -10'          | d16        | 550   | Panoply                            |
| Full plate           | 18      | 22  | 21  | 18  | +0               | -8            | -10'          | d16        | 1200  |                                    |
  - Shield: adds +1 to all vectors
- Claude selects the appropriate armor type based on creature description. No external equipment file is required.
- Armor vector values may differ from `ac` — this is expected and not validated by QA.

**`sp` field**: expands `sp_raw` into clean Roll20 display text.
- `sp_raw = "blood drain (1 Stamina, DC 7 Fort save negates)"` → `sp = "Blood drain: on hit, target loses 1 Stamina (DC 7 Fort negates)."`
- `sp_raw = ""` → `sp = ""`

**`attacks_raw = ""`**: if empty (possible for 5e-only monsters with no Actions block), Claude generates a placeholder attack: name = `"Unarmed Strike"`, attack = `"+0"`, damage = `"1d3"`, type = `"bludgeoning"`.

**`description` field**: combines the following in order:
- Armor vectors: `AC: P10/S10/B10.`
- Crit: `Crit: M/d4.`
- Quantity: `Qty: 1d4.`
- Fly speed (if `fly` is non-empty): `Fly: 60.` — omitted entirely if `fly = ""`
- Faction: `Faction: none.`
- Morale DC: `Morale DC: 11.`
- Any 5e flavor lore or `notes` content appended at end.

Example: `"AC: P10/S10/B10. Crit: M/d4. Qty: 1d4. Faction: none. Morale DC: 11."`

**Morale DC**: default 11. Claude may adjust upward (13–15) for creatures with fear auras, fanatical behavior, or explicit notes. Not mechanically validated by QA.

**Multiple attacks**: Claude generates one attack group per attack found in `attacks_raw`. Multiple attacks are separated by `/` in the CSV. The full Roll20 key pattern for attack N is `repeating_attacks_-npc_attack_N_<field>` where N is 1, 2, 3, etc. Example: `"claw +2 melee (1d4) / claw +2 melee (1d4) / bite +4 melee (1d8)"` → three groups with keys `repeating_attacks_-npc_attack_1_name`, `repeating_attacks_-npc_attack_2_name`, `repeating_attacks_-npc_attack_3_name` (and corresponding `_attack`, `_damage`, `_type` keys for each).

**Attack type**: Claude infers from the attack name/weapon (`bite` → `piercing`, `claw` → `slashing`, `slam` → `bludgeoning`, `spear` → `piercing`, etc.). This is a Claude judgment call.

**Alignment conversion**: `C` → `"chaotic"`, `L` → `"lawful"`, `N` → `"neutral"`. Happens in `monster_gen.py` — not in the parser.

**Save and init conversion**: `fort`, `ref`, `will`, and `init` are stored in the CSV with a sign prefix. Conversion rule: strip the leading `+` for positive values; preserve the leading `-` for negative values. The CSV always stores a sign character, including for zero (`+0`). Examples: `+6` → `6`, `+0` → `0`, `-1` → `-1`. This rule applies **only** to these four fields — attack bonus strings (e.g. `repeating_attacks_-npc_attack_1_attack`) retain their sign prefix as-is (e.g. `"+0"`, `"+3"`, `"-1"`).

**`hit_points` field**: `{"current": N, "max": N}` where N equals `hp_avg` from the CSV. `hp_avg` is authoritative — Stage 3 does not recompute it from `hd`.

### Output
One JSON file per monster: `data/output/pending/<sanitized_name>.json`

### Roll20 JSON structure
`docs/roll20-npc-schema.md` already exists in the repo and defines all field names and types. Required fields for every generated sheet:

| Field | Type | Example |
|---|---|---|
| `is_npc` | number | `1` |
| `name` | string | `"Stirge"` |
| `hd` | string | `"1d5+1"` |
| `hit_points` | object | `{"current": 4, "max": 4}` |
| `ac` | number | `10` |
| `fort` | number | `2` |
| `ref` | number | `6` |
| `will` | number | `0` |
| `init` | number | `6` |
| `act` | string | `"1d20"` |
| `speed` | string | `"30"` |
| `alignment` | string | `"chaotic"` |
| `sp` | string | `"Blood drain: ..."` or `""` |
| `description` | string | `"AC: P10/S10/B10. Crit: M/d4. Qty: 1d4. Faction: none. Morale DC: 11."` |
| `repeating_attacks_-npc_attack_1_name` | string | `"Bite"` |
| `repeating_attacks_-npc_attack_1_attack` | string | `"+0"` |
| `repeating_attacks_-npc_attack_1_damage` | string | `"1d3+1"` |
| `repeating_attacks_-npc_attack_1_type` | string | `"piercing"` |

---

## Stage 4: qa_checker.py

Two-pass validation for every `.json` file in `data/output/pending/`.

### Pass 1 — Mechanical (deterministic)

- All required fields present (including `sp`)
- Correct types: `is_npc` is number; `ac`, `fort`, `ref`, `will`, `init` are numbers; `name`, `hd`, `act`, `speed`, `alignment`, `sp`, `description` are strings; `hit_points` is object with `current` and `max` keys (both numbers)
- `hit_points.max` equals `hit_points.current` (they must match)
- HD is valid dice notation matching `\d+d\d+([+-]\d+)?`
- `alignment` is one of `"lawful"`, `"neutral"`, `"chaotic"`
- `description` contains armor vectors matching pattern `AC: P\d+/S\d+/B\d+`
- Attack group 1 is complete: all four keys present — `repeating_attacks_-npc_attack_1_name`, `repeating_attacks_-npc_attack_1_attack`, `repeating_attacks_-npc_attack_1_damage`, `repeating_attacks_-npc_attack_1_type`
- All `repeating_attacks_*_attack` values are strings (e.g. `"+0"`, not number `0`)

Note: QA does **not** check `hit_points.max` against the `hd` expression — `hp_avg` from the CSV is authoritative and may differ from the `hd` die average (especially for 5e-sourced monsters).

### Pass 2 — Claude judgment review

Claude reads the complete sheet and flags implausible stat combinations for the creature type (e.g. a giant rat with `will = 10`, a zombie with `ref = 8`, a weak creature with 20 HD).

Returns a response where the **first word** of the first line is either `PASS` or `FLAG`. Everything after that word is treated as optional notes (for `PASS`) or the reason (for `FLAG`). If Claude's response does not start with `PASS` or `FLAG`, the checker treats it as `FLAG` with reason `"malformed QA response"` and moves the file to `flagged/`.

### Output routing

| Result | Destination | Additional file |
|---|---|---|
| Pass 1 + Pass 2 pass | `data/output/ready/` | — |
| Pass 1 fails | `data/output/flagged/` | `<name>_qa_report.txt` |
| Pass 2 flags | `data/output/flagged/` | `<name>_qa_report.txt` with Claude reasoning |

CLI output: `python run.py qa` → `5 passed, 2 flagged`

---

## Testing Strategy

TDD throughout. Claude API calls mocked in unit tests; real API used only in integration tests.

### parse_statblocks.py
- Parse known DCC stat block string → assert correct CSV row values for all fields
- Parse 5e stat block → assert correct save translation (CON→fort, DEX→ref, WIS→will)
- Parse 5e stat block with absent CON save → `fort = 0`
- Parse 5e alignment `"unaligned"` → `N`; `"chaotic evil"` → `C`
- Parse 5e DEX modifier from ability score block → `init` (not from printed initiative)
- Handle missing optional fields: no fly speed → `fly = ""`; no SP → `sp_raw = ""`
- `source = "both"` when same name appears in both input files
- CR exactly ¼ → `1d6`; CR 3 → `3d8`; CR 6 → `6d8`
- Multi-attack DCC stat block → `attacks_raw` contains all attacks separated by `/`
- 5e lore section extraction: given a file with two monsters, extracting by name returns only the matching block

### gap_analysis.py
- Monster in CSV but not in Roll20 export → name appears in `gap_report.txt`
- Monster in both CSV and Roll20 export → does NOT appear in `gap_report.txt`
- Name matching is case-insensitive and strips whitespace
- `gap_report.txt` is one name per line, no headers
- All CSV monsters exist in Roll20 → `gap_report.txt` is empty, CLI prints "No gaps found"

### monster_gen.py
- CSV row → output JSON contains all required Roll20 fields
- Natural armor creature → armor vector values in `description` all equal `ac`
- `hit_points` is `{"current": N, "max": N}` where N equals `hp_avg` from CSV
- Alignment `C` → `"chaotic"`, `L` → `"lawful"`, `N` → `"neutral"`
- `fort`, `ref`, `will`, `init` stored as plain integers (no `+` sign) in output JSON
- `sp_raw = "blood drain (...)"` + mock Claude response → `sp` field matches expected expanded string
- `sp_raw = ""` → `sp = ""`
- `attacks_raw = ""` → output contains placeholder attack (Unarmed Strike, +0, 1d3, bludgeoning)
- Three-attack `attacks_raw` → output JSON contains keys `repeating_attacks_-npc_attack_1_name`, `repeating_attacks_-npc_attack_2_name`, `repeating_attacks_-npc_attack_3_name`
- `quantity = "1d4"` → `description` contains `Qty: 1d4`
- `crit = "M/d4"` → `description` contains `Crit: M/d4`
- `fly = "60"` → `description` contains `Fly: 60`
- `fly = ""` → `description` does not contain `Fly:`
- `name = "Cave Fisher"` → output filename is `cave_fisher.json`
- Running `--generate` when `pending/<name>.json` already exists → file is overwritten
- `gap_report.txt` is empty → `--generate --all` prints "No gaps found" and exits 0
- `gap_report.txt` does not exist → `--generate --all` prints "No gaps found" and exits 0
- `--generate --name "X"` where "X" is not in CSV → prints error and exits non-zero
- Claude API call is mocked in unit tests

### qa_checker.py
- Missing required field (including `sp`) → Pass 1 fails, file goes to `flagged/`
- Attack group 1 missing `_damage` key → Pass 1 fails
- `hit_points.current ≠ hit_points.max` → Pass 1 fails
- Invalid HD notation → Pass 1 fails
- `alignment = "evil"` → Pass 1 fails
- `description` missing armor vector pattern → Pass 1 fails
- Valid complete sheet → Pass 1 passes
- Claude Pass 2 call is mocked in unit tests
