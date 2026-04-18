# Plan 04 — RoomGen + EncounterGen Design

**Date:** 2026-04-18
**Status:** Approved
**Author:** Brainstorming session with Claude Code
**Project home:** `C:\Users\lheur\Documents\thracia-agents\`
**Parent spec:** `docs/superpowers/specs/2026-03-21-thracia-roll20-automation-design.md`

---

## Overview

Two new Phase 1 content agents that complete the content generation pipeline:

- **RoomGen** — extracts room entries from the Caverns of Thracia PDF and generates one Roll20 handout JSON per room, with player-facing description in `notes` and full GM content in `gmnotes`.
- **EncounterGen** — extracts explicit wandering monster tables from the PDF and generates a Roll20 API script (`.js`) per level that creates a rollable table and a GM-whisper macro button.

Both agents share a new `parse_pdf.py` extraction module and follow the existing pipeline: staged input → Claude API → `data/output/pending/` → QAChecker → `data/output/ready/`.

---

## Architecture

### New Files

| File | Role |
|---|---|
| `agents/in-progress/parse_pdf.py` | Shared pdfplumber extraction — splits rooms by header, writes staged text to `data/input/` |
| `agents/in-progress/room_gen.py` | Reads staged room text, calls Claude in batches of 5, writes handout JSON to `data/output/pending/` |
| `agents/in-progress/encounter_gen.py` | Reads staged wandering table text, calls Claude to parse, writes `.js` script directly to `data/output/ready/` |
| `prompts/room_gen.txt` | Claude prompt for player/GM content separation — edit to tune without touching Python |
| `prompts/encounter_gen.txt` | Claude prompt for wandering table parsing — edit to tune without touching Python |
| `data/input/pdf_sections.json` | User-maintained page range config mapping each level/environment to PDF pages |

### Pipeline

```
PDF
  └─ parse_pdf.py (pdfplumber, per page range)
       ├─ data/input/rooms_{section}.txt
       │    └─ room_gen.py (Claude API, batched)
       │         └─ data/output/pending/room_{section}_{sanitized_name}.json
       │              └─ QAChecker → ready/ or flagged/
       └─ data/input/wandering_{section}.txt
            └─ encounter_gen.py (Claude API, single call)
                 └─ data/output/ready/wandering_{section}.js
```

The encounter JS skips QAChecker — it is executable Roll20 API script, not a character sheet, and mechanical field validation does not apply to it.

---

## pdf_sections.json

User populates this file once from the PDF table of contents. All agents read page ranges from it when `--all` is passed.

```json
{
  "level_1": { "room_pages": [120, 145], "encounter_pages": [115, 120] },
  "level_2": { "room_pages": [146, 175], "encounter_pages": [175, 178] },
  "level_3": { "room_pages": [179, 210], "encounter_pages": [210, 212] }
}
```

Sections can be added for any named environment in the module (surface areas, special zones, etc.). The key name becomes the section identifier used in output filenames.

---

## parse_pdf.py

Shared extraction module. Not an agent — imported by both `room_gen.py` and `encounter_gen.py`.

### Room Extraction

- Opens PDF at specified page range using pdfplumber.
- Concatenates extracted text across pages.
- Splits into room blocks using a two-pattern regex:
  - **Primary:** `Area \d+-\d+` (e.g., `Area 1-2 - Hall of the Bats:`)
  - **Fallback:** title-case or all-caps line followed by a colon (catches irregular headers like `Bat Infested Hallway:`)
- Writes `data/input/rooms_{section}.txt` with room blocks separated by a `---ROOM---` delimiter line.
- If the staged file already exists, extraction is skipped unless `--reextract` is passed (avoids repeated pdfplumber runs on a large PDF).

### Wandering Table Extraction

- Same pdfplumber extraction at encounter page range.
- Writes raw text as-is to `data/input/wandering_{section}.txt` — the tables are structured enough that raw extraction is sufficient for Claude to parse.

---

## room_gen.py

### Input

`data/input/rooms_{section}.txt` — split room blocks from `parse_pdf.py`.

### Processing

- Reads all room blocks from the staged file.
- Batches 5 rooms per Claude API call with `prompts/room_gen.txt`.
- Prompt instructs Claude to return a JSON array. Each entry:
  - `name` — room header as written in the module (e.g., `"Area 1-2 - Hall of the Bats"`)
  - `notes` — player-facing content only: the atmospheric opening description (what the party sees, smells, hears on entry). HTML-formatted for Roll20.
  - `gmnotes` — all GM content: monsters and their stats references, tactics, traps, hazards, treasure, secrets, special mechanics. HTML-formatted.
- Validates Claude response structure before writing.

### Output

One JSON file per room written to `data/output/pending/`:

```json
{
  "type": "handout",
  "name": "Area 1-2 - Hall of the Bats",
  "notes": "<p>The air in this chamber...</p>",
  "gmnotes": "<p><strong>Encounter:</strong> 3d6 bats (Init +4...)<br><strong>Traps:</strong> Slippery guano — DC 8 Reflex or prone each round of combat.</p>",
  "folder": "Level 1"
}
```

Filename: `room_{section}_{sanitized_name}.json` (e.g., `room_level_1_area_1_2_hall_of_the_bats.json`).

### Roll20 Import

Handout JSONs are imported via Roll20 API script in Phase 3 (bulk import MCP tool). For Phase 1, the user manually creates handouts or pastes a generated import script. Once created, handouts are linked to map pins by dragging from the journal — one-time, ~5 seconds per room.

---

## encounter_gen.py

### Input

`data/input/wandering_{section}.txt` — raw wandering table text from `parse_pdf.py`.

### Processing

- Sends full raw table text to Claude with `prompts/encounter_gen.txt` in a single API call.
- Prompt instructs Claude to return a JSON array of table entries:
  - `name` — monster name including number appearing (e.g., `"Gnoll (1d3)"`)
  - `weight` — integer die weight (frequency on the table)
  - `notes` — optional faction or morale note (e.g., `"negotiate on morale failure"`)
- Validates response structure, then generates the `.js` output file from the parsed data (no second Claude call).

### Output

`data/output/ready/wandering_{section}.js`:

```javascript
// Wandering Monster Table — Level 1
// Paste into Roll20 API sandbox and run once.

on('ready', function() {
    const table = createObj('rollabletable', {
        name: 'wandering-level-1',
        showplayers: false
    });

    const entries = [
        { name: 'Gnoll (1d3)', weight: 2 },
        { name: 'Lizardman mercenary (1d2)', weight: 1 },
        // ...
    ];

    entries.forEach(function(e) {
        createObj('tableitem', {
            rollabletableid: table.id,
            name: e.name,
            weight: e.weight
        });
    });

    createObj('macro', {
        name: 'Wandering-Level-1',
        action: '/w gm &{template:default} {{name=Level 1 Wandering Monster}} {{result=[[1t[wandering-level-1]]]}}',
        visibleto: ''
    });

    log('wandering-level-1 table and macro created.');
});
```

User pastes the JS into the Roll20 API sandbox and runs it once per level. The macro appears as a button in the Roll20 macro bar.

---

## CLI

### Commands

```
python run.py room --level 1 --pages 120-145     # single level, explicit pages
python run.py room --level 1                      # single level, pages from pdf_sections.json
python run.py room --all                          # all sections in pdf_sections.json

python run.py encounter --level 1 --pages 115-120
python run.py encounter --level 1
python run.py encounter --all
```

### Flags

| Flag | Description |
|---|---|
| `--level N` | Process section `level_N` from `pdf_sections.json` |
| `--pages X-Y` | Override page range from config |
| `--all` | Process all sections defined in `pdf_sections.json` |
| `--reextract` | Force re-extraction even if staged file exists |

### Behavior

- `room` command: extract (if needed) → generate → auto-run QAChecker on new pending files (same as `monster` command).
- `encounter` command: extract (if needed) → generate → write directly to `ready/` (no QA step).

---

## QAChecker Extension

New handout validation pass added to `qa_checker.py`:

**Required fields:** `type`, `name`, `notes`, `gmnotes`
**Type check:** `type` must equal `"handout"`
**Non-empty check:** `notes` and `gmnotes` must be non-empty strings

Handout files are identified by `"type": "handout"` in the JSON — QAChecker runs the appropriate validation pass based on this field.

---

## Testing

Target: ~15-20 new tests across four areas.

### parse_pdf.py tests (~5)
- Room splitting correctly identifies primary header pattern (`Area 1-2 - Name:`)
- Room splitting correctly identifies fallback irregular header pattern
- Delimiter format in output file is correct
- Skip extraction if staged file exists (no `--reextract`)
- Force re-extraction with `--reextract`

### room_gen.py tests (~5)
- Handout JSON has all required fields
- `type` field is `"handout"`
- `notes` and `gmnotes` are non-empty strings
- Filename sanitization produces valid paths
- Batch of 5 rooms produces 5 output files (integration test with real Claude call)

### encounter_gen.py tests (~5)
- Table entry JSON has `name` and `weight` fields
- JS output contains `createObj('rollabletable'` call
- JS output contains correct number of `createObj('tableitem'` calls
- JS output contains macro with `/w gm` whisper action
- `wandering-level-{N}` table name matches section key

### QAChecker tests (~5)
- Handout with all fields passes validation
- Missing `notes` produces error
- Missing `gmnotes` produces error
- Wrong `type` value produces error
- Non-handout JSON is not subject to handout validation pass

---

## Dependencies

- `pdfplumber` — add to `requirements.txt` and install in `thracia-agents` conda env
- All other dependencies already present (`anthropic`, `pytest`, standard library)

---

## Open Questions

- Page ranges for all levels and environments need to be determined by the user before running `--all`. These are entered once into `pdf_sections.json`.
- The Caverns of Thracia PDF may have multi-column layouts on some pages. pdfplumber's `extract_text()` handles single-column well; multi-column pages may need `extract_words()` with column sorting. This can be addressed during the build sprint if extraction quality is poor.
- The Grave Robbers of Thracia and other companion modules are out of scope for this plan. `pdf_sections.json` keys can reference any PDF section but this plan only covers the primary Caverns of Thracia module.
