# Plan 04 — RoomGen + EncounterGen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build RoomGen and EncounterGen agents that extract room entries and wandering monster tables from the Caverns of Thracia PDF and produce Roll20-ready handout JSONs and rollable-table API scripts.

**Architecture:** A shared `parse_pdf.py` module uses pdfplumber to extract and stage text from the PDF. `room_gen.py` batches room text to Claude and writes handout JSONs to `data/output/pending/`. `encounter_gen.py` sends wandering table text to Claude for parsing, then generates a `.js` Roll20 API script directly to `data/output/ready/`. The existing QAChecker is extended to validate handout JSONs by dispatching on the `type` field.

**Tech Stack:** Python 3.11, pdfplumber, anthropic SDK, pytest

---

## File Map

| Action | File |
|---|---|
| Create | `agents/in-progress/parse_pdf.py` |
| Create | `agents/in-progress/room_gen.py` |
| Create | `agents/in-progress/encounter_gen.py` |
| Create | `prompts/room_gen.txt` |
| Create | `prompts/encounter_gen.txt` |
| Create | `data/input/pdf_sections.json` |
| Create | `tests/test_parse_pdf.py` |
| Create | `tests/test_room_gen.py` |
| Create | `tests/test_encounter_gen.py` |
| Modify | `agents/in-progress/qa_checker.py` |
| Modify | `tests/test_qa_checker.py` |
| Modify | `run.py` |
| Modify | `tests/test_cli.py` |
| Modify | `requirements.txt` |

---

## Task 1: Install pdfplumber and create pdf_sections.json

**Files:**
- Modify: `requirements.txt`
- Create: `data/input/pdf_sections.json`

- [ ] **Step 1: Install pdfplumber into the conda env**

```bash
conda run -n thracia-agents pip install pdfplumber
```

Expected: `Successfully installed pdfplumber-...`

- [ ] **Step 2: Add pdfplumber to requirements.txt**

Open `requirements.txt` and add this line (keep alphabetical order):

```
pdfplumber==0.11.4
```

(Run `conda run -n thracia-agents pip show pdfplumber` first to confirm the installed version, then use that exact version.)

- [ ] **Step 3: Create pdf_sections.json**

Create `data/input/pdf_sections.json`. Fill in the actual page numbers by checking the Caverns of Thracia PDF table of contents. The structure below uses placeholder ranges — replace with real values before running `--all`.

```json
{
  "level_1": { "room_pages": [120, 145], "encounter_pages": [115, 120] },
  "level_2": { "room_pages": [146, 175], "encounter_pages": [175, 178] },
  "level_3": { "room_pages": [179, 210], "encounter_pages": [210, 212] }
}
```

- [ ] **Step 4: Verify pdfplumber can open the PDF**

```bash
conda run -n thracia-agents python -c "
import pdfplumber
with pdfplumber.open('C:/Users/lheur/Documents/Obsidian Vault/Adventures/Caverns_of_Thracia_-_DCC_v2.pdf') as pdf:
    print(f'Pages: {len(pdf.pages)}')
    print(pdf.pages[125].extract_text()[:300])
"
```

Expected: prints page count and sample text from page 126. If text is garbled or empty, the PDF may need `extract_words()` with column sorting — flag this before continuing.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt data/input/pdf_sections.json
git commit -m "chore: install pdfplumber and add pdf_sections.json config"
```

---

## Task 2: parse_pdf.py — extraction module

**Files:**
- Create: `agents/in-progress/parse_pdf.py`
- Create: `tests/test_parse_pdf.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_parse_pdf.py`:

```python
# tests/test_parse_pdf.py
import sys
from pathlib import Path
import pytest

from parse_pdf import split_rooms, ROOMS_DELIMITER


class TestSplitRooms:
    def test_primary_header_splits_two_rooms(self):
        text = (
            "Area 1-1 - Entry Hall\nBats fill the ceiling.\n\n"
            "Area 1-2 - Hall of the Bats\nMore bats here."
        )
        blocks = split_rooms(text)
        assert len(blocks) == 2
        assert "Entry Hall" in blocks[0]
        assert "Hall of the Bats" in blocks[1]

    def test_fallback_header_splits_correctly(self):
        text = (
            "Bat Infested Hallway:\nDescription here.\n\n"
            "Area 1-2 - Normal Room\nAnother room."
        )
        blocks = split_rooms(text)
        assert len(blocks) == 2
        assert "Bat Infested Hallway" in blocks[0]

    def test_single_room_returns_one_block(self):
        text = "Area 1-1 - Entry Hall\nJust one room."
        blocks = split_rooms(text)
        assert len(blocks) == 1

    def test_empty_blocks_are_excluded(self):
        text = "\n\n\nArea 1-1 - Entry Hall\nContent here."
        blocks = split_rooms(text)
        assert all(b.strip() for b in blocks)
        assert len(blocks) == 1

    def test_delimiter_appears_in_joined_output(self):
        text = "Area 1-1 - Entry Hall\nA.\n\nArea 1-2 - Next\nB."
        blocks = split_rooms(text)
        joined = f"\n{ROOMS_DELIMITER}\n".join(blocks)
        assert ROOMS_DELIMITER in joined
        assert joined.count(ROOMS_DELIMITER) == 1


class TestExtractRooms:
    def test_skips_extraction_if_staged_file_exists(self, tmp_path, monkeypatch):
        staged = tmp_path / "rooms_level_1.txt"
        staged.write_text("existing content")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: (_ for _ in ()).throw(AssertionError("should not call _extract_text")))

        result = parse_pdf.extract_rooms("level_1", (120, 125), reextract=False)
        assert result.read_text() == "existing content"

    def test_reextract_overwrites_existing_file(self, tmp_path, monkeypatch):
        staged = tmp_path / "rooms_level_1.txt"
        staged.write_text("old content")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "input").mkdir(parents=True)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: "Area 1-1 - Room\nNew content.")

        result = parse_pdf.extract_rooms("level_1", (120, 125), reextract=True)
        assert "New content" in result.read_text()

    def test_extract_wandering_skips_if_staged_exists(self, tmp_path, monkeypatch):
        staged = tmp_path / "wandering_level_1.txt"
        staged.write_text("existing table")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: (_ for _ in ()).throw(AssertionError("should not be called")))

        result = parse_pdf.extract_wandering("level_1", (115, 120), reextract=False)
        assert result.read_text() == "existing table"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
conda run -n thracia-agents python -m pytest tests/test_parse_pdf.py -v
```

Expected: `ImportError: No module named 'parse_pdf'` or similar — all tests fail.

- [ ] **Step 3: Implement parse_pdf.py**

Create `agents/in-progress/parse_pdf.py`:

```python
# agents/in-progress/parse_pdf.py
#
# Shared PDF extraction module used by room_gen.py and encounter_gen.py.
# Extracts text from targeted page ranges of the Thracia PDF and writes
# staged text files to data/input/. Re-extraction is skipped if staged
# files already exist (use reextract=True to force).

import re
from pathlib import Path

import pdfplumber

PDF_PATH = 'C:/Users/lheur/Documents/Obsidian Vault/Adventures/Caverns_of_Thracia_-_DCC_v2.pdf'
ROOMS_DELIMITER = '---ROOM---'

# Primary: "Area 1-2" or "Area 1-2 - Name"
PRIMARY_HEADER_RE = re.compile(r'^Area\s+\d+-\d+', re.IGNORECASE)
# Fallback: "Bat Infested Hallway:" (Title Case ending in colon)
FALLBACK_HEADER_RE = re.compile(r"^[A-Z][A-Za-z\s\'-]{3,}:$")


def split_rooms(text):
    """Split raw PDF text into room blocks by header pattern.

    Tries the primary 'Area X-Y' pattern first, falls back to title-case
    lines ending in a colon for irregular headers like 'Bat Infested Hallway:'.

    Returns:
        list[str]: non-empty room text blocks
    """
    lines = text.splitlines()
    blocks = []
    current_lines = []

    for line in lines:
        stripped = line.strip()
        is_header = PRIMARY_HEADER_RE.match(stripped) or FALLBACK_HEADER_RE.match(stripped)
        if is_header:
            if current_lines:
                block = '\n'.join(current_lines).strip()
                if block:
                    blocks.append(block)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        block = '\n'.join(current_lines).strip()
        if block:
            blocks.append(block)

    return blocks


def _extract_text(pages):
    """Extract and concatenate text from PDF pages (1-based range, inclusive)."""
    start, end = pages
    chunks = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i in range(start - 1, end):  # pdfplumber is 0-indexed
            page = pdf.pages[i]
            chunks.append(page.extract_text() or '')
    return '\n'.join(chunks)


def extract_rooms(section_key, pages, reextract=False):
    """Extract and stage room blocks for a PDF section.

    Args:
        section_key: e.g. 'level_1'
        pages: (start, end) tuple of 1-based page numbers (inclusive)
        reextract: if True, re-extract even if staged file exists

    Returns:
        Path to staged rooms_{section_key}.txt file
    """
    out_path = Path(f'data/input/rooms_{section_key}.txt')
    if out_path.exists() and not reextract:
        return out_path

    text = _extract_text(pages)
    blocks = split_rooms(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f'\n{ROOMS_DELIMITER}\n'.join(blocks), encoding='utf-8')
    print(f"parse_pdf: {len(blocks)} rooms extracted → {out_path}")
    return out_path


def extract_wandering(section_key, pages, reextract=False):
    """Extract and stage wandering table text for a PDF section.

    Args:
        section_key: e.g. 'level_1'
        pages: (start, end) tuple of 1-based page numbers (inclusive)
        reextract: if True, re-extract even if staged file exists

    Returns:
        Path to staged wandering_{section_key}.txt file
    """
    out_path = Path(f'data/input/wandering_{section_key}.txt')
    if out_path.exists() and not reextract:
        return out_path

    text = _extract_text(pages)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding='utf-8')
    print(f"parse_pdf: wandering table extracted → {out_path}")
    return out_path
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
conda run -n thracia-agents python -m pytest tests/test_parse_pdf.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/parse_pdf.py tests/test_parse_pdf.py
git commit -m "feat: add parse_pdf extraction module with room splitting and 8 passing tests"
```

---

## Task 3: prompts/room_gen.txt

**Files:**
- Create: `prompts/room_gen.txt`

No tests — this is a plain text prompt file. Quality is validated by the integration test in Task 4.

- [ ] **Step 1: Create prompts/room_gen.txt**

```
You are processing dungeon room entries from the Caverns of Thracia for a Roll20 DCC campaign.

Given a batch of raw room text blocks (each preceded by [Room N]), return a JSON array with one object per room.

Each object must have these exact fields:
- "type": always the string "handout"
- "name": the room header exactly as it appears in the source (e.g. "Area 1-2 - Hall of the Bats")
- "notes": player-facing atmospheric description only — what the party sees, smells, and hears on entry. This is typically the opening paragraph (often italicized in the original). Do NOT include any mechanical content: no monster stats, no DCs, no treasure values, no trap mechanics. Format as valid HTML using <p> tags.
- "gmnotes": all GM content — monsters with stat references, tactics, traps with DCs, treasure, secrets, special mechanics. Format as valid HTML using <p>, <strong>, and <br> tags. Organize clearly with bold headings for each section (Encounter, Traps, Treasure, Secrets).
- "folder": the dungeon level this room belongs to, derived from the room number prefix (e.g. "Level 1" for Area 1-2, "Level 2" for Area 2-5)

Rules:
- If no player-facing description exists, set "notes" to "<p>No description.</p>"
- If no GM content exists, set "gmnotes" to "<p>No notes.</p>"
- Preserve all mechanical details in gmnotes exactly — do not paraphrase DC values, damage rolls, or creature names
- Return ONLY the JSON array. No markdown code fences. No explanatory text before or after.
```

- [ ] **Step 2: Commit**

```bash
git add prompts/room_gen.txt
git commit -m "feat: add room_gen prompt template"
```

---

## Task 4: room_gen.py

**Files:**
- Create: `agents/in-progress/room_gen.py`
- Create: `tests/test_room_gen.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_room_gen.py`:

```python
# tests/test_room_gen.py
import json
import pytest
from unittest.mock import MagicMock

from room_gen import (
    sanitize_filename,
    read_room_blocks,
    validate_handout,
    parse_claude_response,
)

VALID_HANDOUT = {
    "type": "handout",
    "name": "Area 1-2 - Hall of the Bats",
    "notes": "<p>The air is thick with bat guano.</p>",
    "gmnotes": "<p><strong>Encounter:</strong> 3d6 bats. DC 8 Reflex or prone.</p>",
    "folder": "Level 1",
}


class TestSanitizeFilename:
    def test_produces_valid_filename(self):
        name = sanitize_filename("level_1", "Area 1-2 - Hall of the Bats")
        assert name.startswith("room_level_1_")
        assert name.endswith(".json")
        assert " " not in name

    def test_special_chars_removed(self):
        name = sanitize_filename("level_1", "Area 1-2: Room (Special)")
        assert "(" not in name
        assert ")" not in name
        assert ":" not in name


class TestReadRoomBlocks:
    def test_reads_blocks_split_by_delimiter(self, tmp_path):
        f = tmp_path / "rooms_level_1.txt"
        f.write_text("Block one content\n---ROOM---\nBlock two content", encoding="utf-8")
        blocks = read_room_blocks(str(f))
        assert len(blocks) == 2
        assert "Block one" in blocks[0]
        assert "Block two" in blocks[1]

    def test_empty_blocks_excluded(self, tmp_path):
        f = tmp_path / "rooms_level_1.txt"
        f.write_text("Block one\n---ROOM---\n   \n---ROOM---\nBlock two", encoding="utf-8")
        blocks = read_room_blocks(str(f))
        assert len(blocks) == 2


class TestValidateHandout:
    def test_valid_handout_passes(self):
        assert validate_handout(VALID_HANDOUT) == []

    def test_missing_type_fails(self):
        h = dict(VALID_HANDOUT)
        del h["type"]
        errors = validate_handout(h)
        assert any("type" in e for e in errors)

    def test_wrong_type_fails(self):
        h = dict(VALID_HANDOUT, type="monster")
        errors = validate_handout(h)
        assert any("type" in e for e in errors)

    def test_missing_notes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["notes"]
        errors = validate_handout(h)
        assert any("notes" in e for e in errors)

    def test_empty_notes_fails(self):
        h = dict(VALID_HANDOUT, notes="")
        errors = validate_handout(h)
        assert any("notes" in e for e in errors)

    def test_missing_gmnotes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["gmnotes"]
        errors = validate_handout(h)
        assert any("gmnotes" in e for e in errors)


class TestParseClaudeResponse:
    def test_bare_json_parses(self):
        raw = json.dumps([VALID_HANDOUT])
        result = parse_claude_response(raw)
        assert isinstance(result, list)
        assert result[0]["name"] == VALID_HANDOUT["name"]

    def test_markdown_fenced_json_parses(self):
        raw = "```json\n" + json.dumps([VALID_HANDOUT]) + "\n```"
        result = parse_claude_response(raw)
        assert result[0]["type"] == "handout"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
conda run -n thracia-agents python -m pytest tests/test_room_gen.py -v
```

Expected: `ImportError: No module named 'room_gen'`

- [ ] **Step 3: Implement room_gen.py**

Create `agents/in-progress/room_gen.py`:

```python
# agents/in-progress/room_gen.py
#
# Stage: Generate Roll20 handout JSONs from staged room text.
# Reads rooms_{section_key}.txt, batches 5 rooms per Claude call,
# writes one handout JSON per room to data/output/pending/.
#
# Usage: python run.py room --level 1

import json
import re
from pathlib import Path

import anthropic

PROMPT_PATH = 'prompts/room_gen.txt'
PENDING_DIR = 'data/output/pending'
BATCH_SIZE = 5
ROOMS_DELIMITER = '---ROOM---'


def sanitize_filename(section_key, room_name):
    """Convert section key + room name to a safe output filename."""
    safe = re.sub(r'[^\w\s-]', '', room_name.lower())
    safe = re.sub(r'\s+', '_', safe.strip())
    return f'room_{section_key}_{safe}.json'


def read_room_blocks(staged_path):
    """Read room blocks from a staged file. Returns list of non-empty block strings."""
    text = Path(staged_path).read_text(encoding='utf-8')
    return [b.strip() for b in text.split(ROOMS_DELIMITER) if b.strip()]


def parse_claude_response(response_text):
    """Parse Claude JSON array response, stripping markdown fences if present."""
    text = response_text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text.strip())
    return json.loads(text)


def validate_handout(handout):
    """Validate handout dict structure. Returns list of error strings (empty = valid)."""
    errors = []
    for field in ('type', 'name', 'notes', 'gmnotes', 'folder'):
        if field not in handout:
            errors.append(f"Missing field: {field}")
    if errors:
        return errors
    if handout.get('type') != 'handout':
        errors.append(f"type must be 'handout', got '{handout.get('type')}'")
    if not isinstance(handout.get('notes'), str) or not handout['notes'].strip():
        errors.append("notes must be a non-empty string")
    if not isinstance(handout.get('gmnotes'), str) or not handout['gmnotes'].strip():
        errors.append("gmnotes must be a non-empty string")
    return errors


def _build_prompt(blocks, prompt_template):
    """Combine prompt template with a batch of room blocks."""
    rooms_text = '\n\n'.join(f'[Room {i + 1}]\n{b}' for i, b in enumerate(blocks))
    return prompt_template + '\n\n' + rooms_text


def generate_handouts(section_key, staged_path, client=None):
    """Call Claude to generate handout dicts for all rooms in staged file.

    Returns:
        list[tuple[str, dict]]: (filename, handout_dict) pairs
    """
    if client is None:
        client = anthropic.Anthropic()

    prompt_template = Path(PROMPT_PATH).read_text(encoding='utf-8')
    blocks = read_room_blocks(staged_path)
    results = []

    for i in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[i:i + BATCH_SIZE]
        prompt = _build_prompt(batch, prompt_template)
        message = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': prompt}]
        )
        handouts = parse_claude_response(message.content[0].text)
        for handout in handouts:
            filename = sanitize_filename(section_key, handout.get('name', f'room_{i}'))
            results.append((filename, handout))

    return results


def run(section_key, staged_path):
    """Write handout JSONs to data/output/pending/."""
    Path(PENDING_DIR).mkdir(parents=True, exist_ok=True)
    results = generate_handouts(section_key, staged_path)
    for filename, handout in results:
        out_path = Path(PENDING_DIR) / filename
        out_path.write_text(json.dumps(handout, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"RoomGen: {len(results)} handouts written to {PENDING_DIR}/")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
conda run -n thracia-agents python -m pytest tests/test_room_gen.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/room_gen.py tests/test_room_gen.py
git commit -m "feat: add room_gen agent with handout JSON generation and 11 passing tests"
```

---

## Task 5: prompts/encounter_gen.txt

**Files:**
- Create: `prompts/encounter_gen.txt`

- [ ] **Step 1: Create prompts/encounter_gen.txt**

```
You are parsing a wandering monster table from the Caverns of Thracia DCC module.

Given raw text extracted from the PDF, locate the wandering monster table and extract its entries.

Return a JSON array where each object represents one table entry with these exact fields:
- "name": monster name with number appearing in parentheses (e.g. "Gnoll (1d3)" or "Lizardman mercenary (1d2)")
- "weight": integer representing how many faces of the die resolve to this entry. If all entries appear once on a d12, each weight is 1. If an entry spans multiple die results, use the count (e.g. results 1-2 = weight 2).
- "notes": optional string with faction or morale context relevant to the encounter (e.g. "negotiate on morale failure", "check Ring of Agamemnos control"). Empty string if none.

Rules:
- Include every distinct entry in the table
- Preserve exact monster names as they appear in the module
- Do not invent entries not present in the source text
- Return ONLY the JSON array. No markdown code fences. No explanatory text.

Example output:
[
  {"name": "Gnoll (1d3)", "weight": 2, "notes": "negotiate on morale failure"},
  {"name": "Lizardman mercenary (1d2)", "weight": 1, "notes": ""}
]
```

- [ ] **Step 2: Commit**

```bash
git add prompts/encounter_gen.txt
git commit -m "feat: add encounter_gen prompt template"
```

---

## Task 6: encounter_gen.py

**Files:**
- Create: `agents/in-progress/encounter_gen.py`
- Create: `tests/test_encounter_gen.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_encounter_gen.py`:

```python
# tests/test_encounter_gen.py
import json
import pytest
from unittest.mock import MagicMock

from encounter_gen import validate_entries, build_js, parse_claude_response

SAMPLE_ENTRIES = [
    {"name": "Gnoll (1d3)", "weight": 2, "notes": "negotiate on morale failure"},
    {"name": "Lizardman mercenary (1d2)", "weight": 1, "notes": ""},
    {"name": "Giant Bat (1d6)", "weight": 1, "notes": ""},
]


class TestValidateEntries:
    def test_valid_entries_pass(self):
        assert validate_entries(SAMPLE_ENTRIES) == []

    def test_missing_name_fails(self):
        entries = [{"weight": 2, "notes": ""}]
        errors = validate_entries(entries)
        assert any("name" in e for e in errors)

    def test_missing_weight_fails(self):
        entries = [{"name": "Gnoll (1d3)", "notes": ""}]
        errors = validate_entries(entries)
        assert any("weight" in e for e in errors)

    def test_string_weight_fails(self):
        entries = [{"name": "Gnoll (1d3)", "weight": "2", "notes": ""}]
        errors = validate_entries(entries)
        assert any("weight" in e for e in errors)

    def test_empty_list_passes(self):
        assert validate_entries([]) == []


class TestBuildJs:
    def test_contains_createobj_rollabletable(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "createObj('rollabletable'" in js

    def test_tableitem_count_matches_entries(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert js.count("createObj('tableitem'") == len(SAMPLE_ENTRIES)

    def test_contains_gm_whisper_macro(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "/w gm" in js

    def test_table_name_uses_section_key(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "wandering-level-1" in js

    def test_macro_name_uses_section_key(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "Wandering-Level-1" in js


class TestParseClaudeResponse:
    def test_bare_json_array_parses(self):
        raw = json.dumps(SAMPLE_ENTRIES)
        result = parse_claude_response(raw)
        assert len(result) == 3
        assert result[0]["name"] == "Gnoll (1d3)"

    def test_markdown_fenced_json_parses(self):
        raw = "```json\n" + json.dumps(SAMPLE_ENTRIES) + "\n```"
        result = parse_claude_response(raw)
        assert result[0]["weight"] == 2
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
conda run -n thracia-agents python -m pytest tests/test_encounter_gen.py -v
```

Expected: `ImportError: No module named 'encounter_gen'`

- [ ] **Step 3: Implement encounter_gen.py**

Create `agents/in-progress/encounter_gen.py`:

```python
# agents/in-progress/encounter_gen.py
#
# Stage: Generate a Roll20 API script from a staged wandering monster table.
# Calls Claude to parse the raw table text, then writes a .js file that
# creates the rollable table and GM-whisper macro in Roll20.
#
# Usage: python run.py encounter --level 1

import json
import re
from pathlib import Path

import anthropic

PROMPT_PATH = 'prompts/encounter_gen.txt'
READY_DIR = 'data/output/ready'


def parse_claude_response(response_text):
    """Parse Claude JSON array response, stripping markdown fences if present."""
    text = response_text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text.strip())
    return json.loads(text)


def validate_entries(entries):
    """Validate list of table entry dicts. Returns list of error strings."""
    errors = []
    for i, e in enumerate(entries):
        if 'name' not in e:
            errors.append(f"Entry {i}: missing 'name'")
        if 'weight' not in e:
            errors.append(f"Entry {i}: missing 'weight'")
        elif not isinstance(e['weight'], int):
            errors.append(f"Entry {i}: 'weight' must be int, got {type(e['weight']).__name__}")
    return errors


def build_js(section_key, entries):
    """Build Roll20 API script string from parsed table entries.

    The script uses on('ready') so it executes once when pasted into the
    API sandbox. Creates a GM-only rollable table and a macro whisper button.
    """
    table_name = f'wandering-{section_key.replace("_", "-")}'
    macro_name = f'Wandering-{section_key.replace("_", "-").title()}'
    display_name = section_key.replace('_', ' ').title()
    action = (
        f"/w gm &{{template:default}} {{{{name={display_name} Wandering Monster}}}}"
        f" {{{{result=[[1t[{table_name}]]]}}}}"
    )

    entry_lines = '\n'.join(
        f"    createObj('tableitem', {{rollabletableid: table.id, "
        f"name: {json.dumps(e['name'])}, weight: {e['weight']}}});"
        for e in entries
    )

    return (
        f"// Wandering Monster Table — {display_name}\n"
        f"// Paste into Roll20 API sandbox and run once.\n\n"
        f"on('ready', function() {{\n"
        f"    var table = createObj('rollabletable', {{\n"
        f"        name: '{table_name}',\n"
        f"        showplayers: false\n"
        f"    }});\n\n"
        f"{entry_lines}\n\n"
        f"    createObj('macro', {{\n"
        f"        name: '{macro_name}',\n"
        f"        action: '{action}',\n"
        f"        visibleto: ''\n"
        f"    }});\n\n"
        f"    log('{table_name} table and macro created.');\n"
        f"}});\n"
    )


def parse_wandering_table(staged_path, client=None):
    """Call Claude to parse staged wandering table text. Returns list of entry dicts."""
    if client is None:
        client = anthropic.Anthropic()

    raw_text = Path(staged_path).read_text(encoding='utf-8')
    prompt_template = Path(PROMPT_PATH).read_text(encoding='utf-8')
    prompt = prompt_template + '\n\n' + raw_text

    message = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2048,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return parse_claude_response(message.content[0].text)


def run(section_key, staged_path):
    """Parse wandering table and write .js script to data/output/ready/."""
    entries = parse_wandering_table(staged_path)
    errors = validate_entries(entries)
    if errors:
        for e in errors:
            print(f"[EncounterGen] ERROR: {e}")
        return

    js_content = build_js(section_key, entries)
    Path(READY_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(READY_DIR) / f'wandering_{section_key}.js'
    out_path.write_text(js_content, encoding='utf-8')
    print(f"EncounterGen: {len(entries)} entries → {out_path}")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
conda run -n thracia-agents python -m pytest tests/test_encounter_gen.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/encounter_gen.py tests/test_encounter_gen.py
git commit -m "feat: add encounter_gen agent with JS table generation and 12 passing tests"
```

---

## Task 7: QAChecker — handout validation

**Files:**
- Modify: `agents/in-progress/qa_checker.py`
- Modify: `tests/test_qa_checker.py`

- [ ] **Step 1: Write the failing tests**

Add a new `TestHandoutValidation` class to `tests/test_qa_checker.py`. Append after the existing `TestRouteSheet` class:

```python
import shutil
from qa_checker import pass1_handout_check, run as qa_run

VALID_HANDOUT = {
    "type": "handout",
    "name": "Area 1-2 - Hall of the Bats",
    "notes": "<p>The air is thick with bat guano.</p>",
    "gmnotes": "<p><strong>Encounter:</strong> 3d6 bats.</p>",
    "folder": "Level 1",
}


class TestPass1HandoutCheck:
    def test_valid_handout_passes(self):
        assert pass1_handout_check(VALID_HANDOUT) == []

    def test_missing_notes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["notes"]
        errors = pass1_handout_check(h)
        assert any("notes" in e for e in errors)

    def test_missing_gmnotes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["gmnotes"]
        errors = pass1_handout_check(h)
        assert any("gmnotes" in e for e in errors)

    def test_wrong_type_fails(self):
        h = dict(VALID_HANDOUT, type="monster")
        errors = pass1_handout_check(h)
        assert any("type" in e for e in errors)

    def test_empty_notes_fails(self):
        h = dict(VALID_HANDOUT, notes="   ")
        errors = pass1_handout_check(h)
        assert any("notes" in e for e in errors)


class TestHandoutDispatch:
    def test_valid_handout_routes_to_ready(self, tmp_path):
        pending = tmp_path / "pending"
        ready = tmp_path / "ready"
        flagged = tmp_path / "flagged"
        pending.mkdir()
        (pending / "room.json").write_text(json.dumps(VALID_HANDOUT), encoding="utf-8")

        qa_run(
            pending_dir=str(pending),
            ready_dir=str(ready),
            flagged_dir=str(flagged),
        )
        assert (ready / "room.json").exists()

    def test_handout_with_empty_notes_routes_to_flagged(self, tmp_path):
        pending = tmp_path / "pending"
        ready = tmp_path / "ready"
        flagged = tmp_path / "flagged"
        pending.mkdir()
        bad = dict(VALID_HANDOUT, notes="")
        (pending / "room.json").write_text(json.dumps(bad), encoding="utf-8")

        qa_run(
            pending_dir=str(pending),
            ready_dir=str(ready),
            flagged_dir=str(flagged),
        )
        assert (flagged / "room.json").exists()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
conda run -n thracia-agents python -m pytest tests/test_qa_checker.py::TestPass1HandoutCheck tests/test_qa_checker.py::TestHandoutDispatch -v
```

Expected: `ImportError: cannot import name 'pass1_handout_check'`

- [ ] **Step 3: Add pass1_handout_check to qa_checker.py**

Add after the existing constants block (before `pass1_check`):

```python
HANDOUT_REQUIRED_FIELDS = ['type', 'name', 'notes', 'gmnotes']


def pass1_handout_check(handout):
    """Validate a handout dict. Returns list of error strings (empty = valid)."""
    errors = []
    for field in HANDOUT_REQUIRED_FIELDS:
        if field not in handout:
            errors.append(f"Missing required field: {field}")
    if errors:
        return errors
    if handout.get('type') != 'handout':
        errors.append(f"type must be 'handout', got '{handout.get('type')}'")
    if not isinstance(handout.get('notes'), str) or not handout['notes'].strip():
        errors.append("notes must be a non-empty string")
    if not isinstance(handout.get('gmnotes'), str) or not handout['gmnotes'].strip():
        errors.append("gmnotes must be a non-empty string")
    return errors
```

- [ ] **Step 4: Update run() to dispatch on type**

Replace the existing `run()` function body's inner loop with this dispatched version:

```python
def run(
    pending_dir=PENDING_DIR,
    ready_dir=READY_DIR,
    flagged_dir=FLAGGED_DIR,
    client=None
):
    """Run QA on all .json files in pending_dir."""
    pending_path = Path(pending_dir)
    if not pending_path.exists():
        print("No pending directory found.")
        return

    json_files = list(pending_path.glob('*.json'))
    if not json_files:
        print("No files to validate in pending/")
        return

    passed = 0
    flagged = 0

    for json_file in json_files:
        data = json.loads(json_file.read_text(encoding='utf-8'))

        if data.get('type') == 'handout':
            errors = pass1_handout_check(data)
            result = 'PASS' if not errors else 'FLAG'
            reason = '; '.join(errors)
        else:
            if client is None:
                client = anthropic.Anthropic()
            errors = pass1_check(data)
            result, reason = pass2_check(data, client=client)

        if not errors and result == 'PASS':
            passed += 1
        else:
            flagged += 1

        route_sheet(
            sheet_path=str(json_file),
            pass1_errors=errors,
            pass2_result=result,
            pass2_reason=reason,
            ready_dir=ready_dir,
            flagged_dir=flagged_dir,
        )

    print(f"{passed} passed, {flagged} flagged")
```

- [ ] **Step 5: Run all qa_checker tests — verify they pass**

```bash
conda run -n thracia-agents python -m pytest tests/test_qa_checker.py -v
```

Expected: all tests PASS (existing + 7 new).

- [ ] **Step 6: Commit**

```bash
git add agents/in-progress/qa_checker.py tests/test_qa_checker.py
git commit -m "feat: extend QAChecker with handout validation pass and 7 new tests"
```

---

## Task 8: run.py — rewire room and encounter commands

**Files:**
- Modify: `run.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

In `tests/test_cli.py`, replace the existing `TestRoomCommand` and `TestEncounterCommand` classes with:

```python
class TestRoomCommand:
    def test_room_with_level(self):
        args = parse_args(["room", "--level", "1"])
        assert args.command == "room"
        assert args.level == 1

    def test_room_with_level_and_pages(self):
        args = parse_args(["room", "--level", "1", "--pages", "120-145"])
        assert args.pages == "120-145"

    def test_room_with_all_flag(self):
        args = parse_args(["room", "--all"])
        assert args.all is True

    def test_room_with_reextract(self):
        args = parse_args(["room", "--level", "1", "--reextract"])
        assert args.reextract is True

    def test_room_no_args_allowed(self):
        args = parse_args(["room"])
        assert args.command == "room"


class TestEncounterCommand:
    def test_encounter_with_level(self):
        args = parse_args(["encounter", "--level", "1"])
        assert args.command == "encounter"
        assert args.level == 1

    def test_encounter_with_all(self):
        args = parse_args(["encounter", "--all"])
        assert args.all is True

    def test_encounter_with_pages_override(self):
        args = parse_args(["encounter", "--level", "1", "--pages", "115-120"])
        assert args.pages == "115-120"

    def test_encounter_with_reextract(self):
        args = parse_args(["encounter", "--level", "1", "--reextract"])
        assert args.reextract is True
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
conda run -n thracia-agents python -m pytest tests/test_cli.py::TestRoomCommand tests/test_cli.py::TestEncounterCommand -v
```

Expected: failures because room uses `--input` and encounter doesn't have `--all`/`--pages`/`--reextract`.

- [ ] **Step 3: Update the room and encounter parsers in run.py**

Replace the existing `room_parser` block (lines 91–98) with:

```python
    # -------------------------------------------------------------------------
    # room command
    # -------------------------------------------------------------------------
    room_parser = subparsers.add_parser(
        'room',
        help='Extract rooms from PDF and generate Roll20 handout JSONs'
    )
    room_parser.add_argument(
        '--level', type=int,
        help='Dungeon level to process (e.g. 1 → section level_1 in pdf_sections.json)'
    )
    room_parser.add_argument(
        '--pages', type=str,
        help='Override page range from config (e.g. 120-145)'
    )
    room_parser.add_argument(
        '--all', action='store_true',
        help='Process all sections defined in data/input/pdf_sections.json'
    )
    room_parser.add_argument(
        '--reextract', action='store_true',
        help='Force re-extraction even if staged file exists'
    )
```

Replace the existing `encounter_parser` block (lines 103–110) with:

```python
    # -------------------------------------------------------------------------
    # encounter command
    # -------------------------------------------------------------------------
    encounter_parser = subparsers.add_parser(
        'encounter',
        help='Extract wandering tables from PDF and generate Roll20 API scripts'
    )
    encounter_parser.add_argument(
        '--level', type=int,
        help='Dungeon level to process (e.g. 1 → section level_1 in pdf_sections.json)'
    )
    encounter_parser.add_argument(
        '--pages', type=str,
        help='Override page range from config (e.g. 115-120)'
    )
    encounter_parser.add_argument(
        '--all', action='store_true',
        help='Process all sections defined in data/input/pdf_sections.json'
    )
    encounter_parser.add_argument(
        '--reextract', action='store_true',
        help='Force re-extraction even if staged file exists'
    )
```

- [ ] **Step 4: Run CLI tests — verify they pass**

```bash
conda run -n thracia-agents python -m pytest tests/test_cli.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Wire the handlers in main()**

First, add `from pathlib import Path` to the imports block at the top of `run.py` (after the existing `import sys` line).

Then **replace the entire existing `main()` function** with the following:

```python
def main():
    """Parse arguments and dispatch to the appropriate agent."""
    import json as _json

    parser = build_parser()
    args = parser.parse_args()

    import parse_statblocks
    import gap_analysis
    import monster_gen
    import qa_checker
    import sheet_auditor
    import sheet_patcher
    import parse_pdf
    import room_gen
    import encounter_gen

    def _resolve_sections(a, pages_key):
        """Return {section_key: (start, end)} from CLI args + pdf_sections.json."""
        config_path = Path('data/input/pdf_sections.json')
        if a.all:
            config = _json.loads(config_path.read_text(encoding='utf-8'))
            return {k: tuple(v[pages_key]) for k, v in config.items()}
        if a.level:
            section_key = f'level_{a.level}'
            if a.pages:
                start, end = map(int, a.pages.split('-'))
                return {section_key: (start, end)}
            config = _json.loads(config_path.read_text(encoding='utf-8'))
            return {section_key: tuple(config[section_key][pages_key])}
        print("Specify --level N or --all. See --help.")
        return {}

    def handle_monster(a):
        if a.parse:
            parse_statblocks.run()
        elif a.gap_analysis:
            gap_analysis.run()
        elif a.generate:
            if a.name:
                monster_gen.run_generate_name(a.name)
            else:
                monster_gen.run_generate_all()

    def handle_room(a):
        sections = _resolve_sections(a, 'room_pages')
        for section_key, pages in sections.items():
            staged = parse_pdf.extract_rooms(section_key, pages, reextract=a.reextract)
            room_gen.run(section_key, str(staged))
        if sections:
            qa_checker.run()

    def handle_encounter(a):
        sections = _resolve_sections(a, 'encounter_pages')
        for section_key, pages in sections.items():
            staged = parse_pdf.extract_wandering(section_key, pages, reextract=a.reextract)
            encounter_gen.run(section_key, str(staged))

    def handle_sheet(a):
        if a.audit:
            sheet_auditor.run()
        if a.patch:
            sheet_patcher.run_patch()
        if not a.audit and not a.patch:
            print("Specify --audit, --patch, or both. See --help.")

    handlers = {
        'monster':   handle_monster,
        'room':      handle_room,
        'encounter': handle_encounter,
        'qa':        lambda a: qa_checker.run(),
        'sheet':     handle_sheet,
        'session':   lambda a: print(f"[Session:{a.session_action}] Not yet implemented. Args: {vars(a)}"),
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)
```

Also add `from pathlib import Path` at the top of run.py if not already present.

- [ ] **Step 6: Run the full test suite**

```bash
conda run -n thracia-agents python -m pytest tests/ -v
```

Expected: all tests PASS. Note the count — it should be the previous count plus the new tests from Tasks 2, 4, 6, and 7.

- [ ] **Step 7: Commit**

```bash
git add run.py tests/test_cli.py
git commit -m "feat: wire room and encounter commands into run.py with full CLI and handler dispatch"
```

---

## Post-implementation smoke test

After all tasks are committed, verify the pipeline end-to-end:

- [ ] **Verify room extraction runs without error**

First, confirm the correct page numbers in `data/input/pdf_sections.json` (check the PDF table of contents). Then:

```bash
conda run -n thracia-agents python run.py room --level 1 --reextract
```

Expected: prints extraction count, then `RoomGen: N handouts written to data/output/pending/`, then QA summary.

- [ ] **Check one output handout**

```bash
conda run -n thracia-agents python -c "
import json
from pathlib import Path
files = list(Path('data/output/ready').glob('room_level_1_*.json'))
if files:
    print(json.dumps(json.loads(files[0].read_text()), indent=2)[:800])
else:
    print('No files in ready/ — check flagged/ for errors')
"
```

- [ ] **Verify encounter extraction runs without error**

```bash
conda run -n thracia-agents python run.py encounter --level 1 --reextract
```

Expected: prints `EncounterGen: N entries → data/output/ready/wandering_level_1.js`

- [ ] **Check the generated JS**

```bash
conda run -n thracia-agents python -c "
from pathlib import Path
js = Path('data/output/ready/wandering_level_1.js').read_text()
print(js[:600])
"
```

Expected: shows `on('ready', ...)` wrapper, `createObj('rollabletable', ...)`, table items, and macro.
