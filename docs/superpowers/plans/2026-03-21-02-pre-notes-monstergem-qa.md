# Plan 02 Pre-Notes — MonsterGen + QAChecker

**Status:** Pre-notes only — full plan to be written when Plan 01 is complete
**Source:** Live Roll20 campaign export analyzed 2026-03-21

These notes must be incorporated into Plan 02 when it is written. They represent
discoveries from the Roll20 export that change the plan's scope and approach.

---

## Key Discovery: 105 NPCs Already Built

The campaign already has 105 NPC/monster characters in Roll20. MonsterGen's first
task is NOT to generate all monsters — it is to perform a **gap analysis**: compare
the existing 105 against the full Thracia monster roster and generate only what's
missing.

**Full list of existing monsters:** See `docs/roll20-npc-schema.md` → "Existing
Monsters Already in Roll20" section.

---

## MonsterGen Task Order (Revised)

1. **Gap Analyzer agent** (new — not in original spec)
   - Input: `docs/roll20-npc-schema.md` (existing monsters list) + Thracia monster
     source PDF/markdown from `data/input/`
   - Output: `data/output/pending/monster-gaps.json` — list of monsters that exist
     in the module but NOT in Roll20
   - Run QAChecker on this output before MonsterGen uses it

2. **MonsterGen** — generates only the monsters in the gap list
   - Use exact field names from `docs/roll20-npc-schema.md`
   - Until SheetPatcher is complete: store armor vectors in `description` field as
     text ("AC: P13/S14/B12") — do NOT invent new fields
   - NPC format: `is_npc: 1`, `hd`, `ac`, `fort`, `ref`, `will`, `init`, `act`,
     `speed`, `sp`, `description`, `repeating_attacks_*`

3. **QAChecker** — validates MonsterGen output against the NPC schema

---

## NPC Field Names (from live export — exact)

These are confirmed field names from the actual Roll20 DCC character sheet.
Plan 02 must use these exactly — no guessing.

```
is_npc          → 1 (integer)
hd              → "3d8" (string, hit dice notation)
hit_points      → { current: N, max: N }
ac              → N (integer, single value until SheetPatcher)
fort            → N (integer, save bonus)
ref             → N (integer, save bonus)
will            → N (integer, save bonus)
init            → N (integer, initiative modifier)
act             → "1d20" (string, action die)
speed           → "30" (string, feet)
alignment       → "lawful"/"neutral"/"chaotic"
sp              → "" (string, special powers plain text)
description     → "" (string, full abilities plain text)
repeating_attacks_-KEY_name    → "Spear"
repeating_attacks_-KEY_attack  → "+2"
repeating_attacks_-KEY_damage  → "1d8"
repeating_attacks_-KEY_type    → "piercing"/"slashing"/"bludgeoning"
```

Use `-npc_attack_1`, `-npc_attack_2` etc. as the repeating section keys.

---

## QAChecker Validation Rules (Minimum)

QAChecker must verify MonsterGen output contains:
- `is_npc` equals 1
- `name` is non-empty string
- `hd` matches pattern like "NdN" or "NdN+N"
- `hit_points.current` equals `hit_points.max` (fresh NPC, not yet injured)
- `hit_points.max` is a positive integer
- `ac` is integer between 8 and 30
- `fort`, `ref`, `will` are integers between -5 and +15
- `init` is integer between -5 and +10
- `act` matches pattern like "1d20", "1d20+1d16"
- `alignment` is one of "lawful", "neutral", "chaotic"
- At least one `repeating_attacks_*_name` entry exists
- `description` contains armor vector text if `ac` is not the only AC variant

---

## Existing NPC Examples for Reference

Plan 02 should include these as test fixtures — known-good NPC data from the campaign
that QAChecker can validate against:

**Gnoll (simple):** ac=13, hd="2d8", fort=2, ref=1, will=0
**Acolyte of Thanatos:** ac=13, hd="1d8", fort=1, ref=0, will=2
**Barrow Wight:** ac=15, hd="3d8", fort=2, ref=1, will=3
**Anteus (boss):** ac=21, hd="4d12", fort=5, ref=4, will=3
