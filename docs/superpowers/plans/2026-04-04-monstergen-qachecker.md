# MonsterGen + QAChecker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 4-module MonsterGen + QAChecker pipeline that parses DCC/5e monster stat blocks, identifies Roll20 gaps, generates Roll20-ready JSON via Claude API, and validates output before it reaches Roll20.

**Architecture:** Four focused modules wired through run.py. Data flows: `dcc_statblocks.txt + lore_5e_sections.txt → master_monsters.csv → gap_report.txt → pending/*.json → ready/ or flagged/`. Each stage produces a reviewable artifact before the next stage runs.

**Tech Stack:** Python 3.11, anthropic==0.86.0, pytest==9.0.2, stdlib csv/re/json/pathlib

---

## File Structure

### New files
| File | Responsibility |
|---|---|
| `agents/in-progress/parse_statblocks.py` | Parse DCC + 5e text → master_monsters.csv |
| `agents/in-progress/gap_analysis.py` | CSV vs Roll20 export → gap_report.txt |
| `agents/in-progress/monster_gen.py` | Gap list + CSV + Claude → Roll20 JSON in pending/ |
| `agents/in-progress/qa_checker.py` | Mechanical + Claude validation → ready/ or flagged/ |
| `tests/test_parse_statblocks.py` | Unit tests for parse_statblocks.py |
| `tests/test_gap_analysis.py` | Unit tests for gap_analysis.py |
| `tests/test_monster_gen.py` | Unit tests for monster_gen.py |
| `tests/test_qa_checker.py` | Unit tests for qa_checker.py |
| `conftest.py` | Adds `agents/in-progress/` to sys.path for all tests |
| `data/input/monster-source/.gitkeep` | Placeholder for source text input directory |

### Modified files
| File | Change |
|---|---|
| `run.py` | Replace `monster --level/--input` with `--parse/--gap-analysis/--generate [--name/--all]`; remove `qa --input` |
| `tests/test_cli.py` | Update monster and qa command tests to match new CLI |

---

### Task 1: Scaffold input directory + sys.path + update CLI

**Files:**
- Create: `data/input/monster-source/.gitkeep`
- Create: `conftest.py`
- Modify: `run.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Create the source input directory**

```bash
mkdir -p data/input/monster-source
touch data/input/monster-source/.gitkeep
```

- [ ] **Step 2: Create conftest.py to expose agents on sys.path**

```python
# conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "agents" / "in-progress"))
```

- [ ] **Step 3: Write failing CLI tests for the new monster and qa interface**

Replace `TestMonsterCommand` and `TestQACommand` in `tests/test_cli.py`:

```python
class TestMonsterCommand:
    def test_monster_parse_flag(self):
        args = parse_args(['monster', '--parse'])
        assert args.command == 'monster'
        assert args.parse is True

    def test_monster_gap_analysis_flag(self):
        args = parse_args(['monster', '--gap-analysis'])
        assert args.gap_analysis is True

    def test_monster_generate_with_name(self):
        args = parse_args(['monster', '--generate', '--name', 'Stirge'])
        assert args.generate is True
        assert args.name == 'Stirge'

    def test_monster_generate_with_all(self):
        args = parse_args(['monster', '--generate', '--all'])
        assert args.generate is True
        assert args.all is True

    def test_monster_generate_no_subarg_allowed(self):
        # --generate with no --name or --all is allowed (treated as --all in handler)
        args = parse_args(['monster', '--generate'])
        assert args.generate is True

    def test_monster_requires_action_flag(self):
        with pytest.raises(SystemExit):
            parse_args(['monster'])


class TestQACommand:
    def test_qa_no_args(self):
        args = parse_args(['qa'])
        assert args.command == 'qa'
```

- [ ] **Step 4: Run tests to confirm they fail**

```
python -m pytest tests/test_cli.py::TestMonsterCommand tests/test_cli.py::TestQACommand -v
```

Expected: FAIL — old CLI doesn't have `--parse`, `--gap-analysis`, `--generate`

- [ ] **Step 5: Update run.py monster and qa parsers**

Replace the `monster_parser` block and `qa_parser` block in `build_parser()`:

```python
# -------------------------------------------------------------------------
# monster command
# -------------------------------------------------------------------------
monster_parser = subparsers.add_parser(
    'monster',
    help='Parse stat blocks, run gap analysis, or generate Roll20 JSON'
)
monster_action_group = monster_parser.add_mutually_exclusive_group(required=True)
monster_action_group.add_argument(
    '--parse', action='store_true',
    help='Parse dcc_statblocks.txt + lore_5e_sections.txt → master_monsters.csv'
)
monster_action_group.add_argument(
    '--gap-analysis', action='store_true', dest='gap_analysis',
    help='Compare master_monsters.csv vs Roll20 export → gap_report.txt'
)
monster_action_group.add_argument(
    '--generate', action='store_true',
    help='Generate Roll20 JSON for monsters in gap_report.txt (use --name or --all)'
)
monster_parser.add_argument(
    '--name', type=str,
    help='Generate sheet for a single named monster (force-regenerate, bypasses gap report)'
)
monster_parser.add_argument(
    '--all', action='store_true',
    help='Generate sheets for all monsters listed in gap_report.txt'
)

# -------------------------------------------------------------------------
# qa command
# -------------------------------------------------------------------------
qa_parser = subparsers.add_parser(
    'qa',
    help='Run QA validation on all files in data/output/pending/'
)
```

- [ ] **Step 6: Run tests to confirm they pass**

```
python -m pytest tests/test_cli.py -v
```

Expected: all 9 original tests + 7 new tests pass

- [ ] **Step 7: Commit**

```bash
git add conftest.py data/input/monster-source/.gitkeep run.py tests/test_cli.py
git commit -m "feat: scaffold source input dir, update CLI for monster and qa commands"
```

---

### Task 2: parse_statblocks.py — DCC parser

**Files:**
- Create: `agents/in-progress/parse_statblocks.py`
- Create: `tests/test_parse_statblocks.py`

- [ ] **Step 1: Write failing DCC parser tests**

Create `tests/test_parse_statblocks.py`:

```python
# tests/test_parse_statblocks.py
import pytest
from parse_statblocks import parse_dcc_block, split_dcc_blocks, _parse_movement

STIRGE_BLOCK = (
    "Stirge (1d4): Init +6; Atk bite +0 melee (1d3+1 plus blood drain); Crit M/d4; "
    "AC 10; HD 1d5+1 (hp 4 each); MV 30', fly 60'; Act 1d20; "
    "SP blood drain (1 Stamina, DC 7 Fort save negates); "
    "SV Fort +2, Ref +6, Will +0; AL C."
)

GNOLL_BLOCK = (
    "Gnoll (2d6): Init +1; Atk spear +3 melee (1d8+2) / bite +1 melee (1d4); "
    "Crit M/d6; AC 14; HD 2d8+2 (hp 11 each); MV 30'; Act 1d20; "
    "SV Fort +3, Ref +1, Will +0; AL C."
)


class TestParseDCCBlock:
    def test_name(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['name'] == 'Stirge'

    def test_quantity(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['quantity'] == '1d4'

    def test_init(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['init'] == '+6'

    def test_attacks_raw(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['attacks_raw'] == 'bite +0 melee (1d3+1 plus blood drain)'

    def test_crit(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['crit'] == 'M/d4'

    def test_ac(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['ac'] == '10'

    def test_hd(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['hd'] == '1d5+1'

    def test_hp_avg(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['hp_avg'] == '4'

    def test_speed(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['speed'] == '30'

    def test_fly(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['fly'] == '60'

    def test_no_fly(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert row['fly'] == ''

    def test_act(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['act'] == '1d20'

    def test_sp_raw(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['sp_raw'] == 'blood drain (1 Stamina, DC 7 Fort save negates)'

    def test_no_sp(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert row['sp_raw'] == ''

    def test_fort(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['fort'] == '+2'

    def test_ref(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['ref'] == '+6'

    def test_will(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['will'] == '+0'

    def test_alignment(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['alignment'] == 'C'

    def test_source_is_dcc(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['source'] == 'dcc'

    def test_multi_attack(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert 'spear +3 melee (1d8+2)' in row['attacks_raw']
        assert 'bite +1 melee (1d4)' in row['attacks_raw']
        assert '/' in row['attacks_raw']


class TestSplitDCCBlocks:
    def test_split_two_blocks(self):
        text = STIRGE_BLOCK + "\n\n" + GNOLL_BLOCK
        blocks = split_dcc_blocks(text)
        assert len(blocks) == 2

    def test_first_block_is_stirge(self):
        text = STIRGE_BLOCK + "\n\n" + GNOLL_BLOCK
        blocks = split_dcc_blocks(text)
        assert 'Stirge' in blocks[0]
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_parse_statblocks.py -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement parse_statblocks.py — DCC functions**

Create `agents/in-progress/parse_statblocks.py`:

```python
# agents/in-progress/parse_statblocks.py
#
# Stage 1: Parse DCC and 5e stat block text into master_monsters.csv.
#
# Usage: python run.py monster --parse
# Input:  data/input/monster-source/dcc_statblocks.txt
#         data/input/monster-source/lore_5e_sections.txt
# Output: data/input/master_monsters.csv

import csv
import re
from pathlib import Path

CSV_COLUMNS = [
    'name', 'quantity', 'hd', 'hp_avg', 'ac', 'init', 'speed', 'fly',
    'act', 'fort', 'ref', 'will', 'alignment', 'attacks_raw', 'sp_raw',
    'crit', 'source', 'notes'
]

# ---------------------------------------------------------------------------
# DCC parsing
# ---------------------------------------------------------------------------

def split_dcc_blocks(text):
    """Split raw DCC text into a list of individual stat block strings.

    A block starts with a line matching: Name (quantity):
    Each block runs until the start of the next.
    """
    header_re = re.compile(r'(?m)^[A-Z][A-Za-z\s\'-]+\s*\([^)]+\)\s*:')
    positions = [m.start() for m in header_re.finditer(text)]
    blocks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        block = text[pos:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _parse_movement(mv_text):
    """Extract (speed, fly) from MV text like "30', fly 60'"."""
    speed_m = re.match(r'(\d+)', mv_text.strip())
    speed = speed_m.group(1) if speed_m else ''
    fly_m = re.search(r'fly\s+(\d+)', mv_text, re.IGNORECASE)
    fly = fly_m.group(1) if fly_m else ''
    return speed, fly


def parse_dcc_block(text):
    """Parse a single DCC stat block string into a CSV row dict."""
    text = text.strip()
    header = re.match(r'^(.+?)\s*\(([^)]+)\)\s*:', text)
    if not header:
        raise ValueError(f"Cannot parse DCC header from: {text[:60]}")
    name = header.group(1).strip()
    quantity = header.group(2).strip()
    body = text[header.end():]

    def get(pattern, default=''):
        m = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else default

    init = get(r'Init\s+([+-]\d+)')
    # Atk field ends at the next semicolon
    attacks_raw = get(r'Atk\s+(.*?)\s*;')
    crit = get(r'Crit\s+(\S+)')
    ac = get(r'AC\s+(\d+)')
    hd = get(r'HD\s+(\S+)')
    hp_avg = get(r'HD\s+\S+\s*\(hp\s+(\d+)')
    mv_text = get(r'MV\s+(.*?)\s*;')
    speed, fly = _parse_movement(mv_text)
    act = get(r'Act\s+(\S+)')
    # SP is optional; terminated by "; SV"
    sp_raw = get(r'\bSP\s+(.*?)\s*;\s*SV\b')
    fort = get(r'Fort\s+([+-]\d+)')
    ref = get(r'Ref\s+([+-]\d+)')
    will = get(r'Will\s+([+-]\d+)')
    alignment = get(r'\bAL\s+([CNL])')

    return {
        'name': name, 'quantity': quantity, 'hd': hd, 'hp_avg': hp_avg,
        'ac': ac, 'init': init, 'speed': speed, 'fly': fly, 'act': act,
        'fort': fort, 'ref': ref, 'will': will, 'alignment': alignment,
        'attacks_raw': attacks_raw, 'sp_raw': sp_raw, 'crit': crit,
        'source': 'dcc', 'notes': ''
    }
```

- [ ] **Step 4: Run DCC tests to confirm they pass**

```
python -m pytest tests/test_parse_statblocks.py::TestParseDCCBlock tests/test_parse_statblocks.py::TestSplitDCCBlocks -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/parse_statblocks.py tests/test_parse_statblocks.py conftest.py
git commit -m "feat: add DCC stat block parser with 22 passing tests"
```

---

### Task 3: parse_statblocks.py — 5e parser

**Files:**
- Modify: `agents/in-progress/parse_statblocks.py`
- Modify: `tests/test_parse_statblocks.py`

- [ ] **Step 1: Write failing 5e parser tests**

Add to `tests/test_parse_statblocks.py`:

```python
from parse_statblocks import parse_5e_block, split_5e_blocks, _cr_to_hd

CAVE_FISHER_BLOCK = """Cave Fisher
Large monstrosity, unaligned

Armor Class 16 (natural armor)
Hit Points 58 (9d10 + 9)
Speed 20 ft., climb 20 ft.

STR  DEX  CON  INT  WIS  CHA
16   13   12   1    10   3
(+3) (+1) (+1) (-5) (0)  (-4)

Saving Throws CON +3, WIS +2
Challenge 3 (700 XP)"""

ZOMBIE_BLOCK = """Zombie
Medium undead, neutral evil

Armor Class 8
Hit Points 22 (3d8 + 9)
Speed 20 ft.

STR  DEX  CON  INT  WIS  CHA
13   6    16   3    6    5
(+1) (-2) (+3) (-4) (-2) (-3)

Saving Throws WIS +0
Challenge 1/4 (50 XP)"""

GHOUL_BLOCK = """Ghoul
Medium undead, chaotic evil

Armor Class 12
Hit Points 22 (5d8)
Speed 30 ft.

STR  DEX  CON  INT  WIS  CHA
13   15   10   7    10   6
(+1) (+2) (0)  (-2) (0)  (-2)

Challenge 1 (200 XP)"""


class TestParse5eBlock:
    def test_name(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['name'] == 'Cave Fisher'

    def test_ac(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['ac'] == '16'

    def test_hp_avg(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['hp_avg'] == '58'

    def test_cr3_maps_to_3d8(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['hd'] == '3d8'

    def test_fort_from_con_save(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['fort'] == '+3'

    def test_ref_absent_defaults_to_zero(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['ref'] == '+0'

    def test_will_from_wis_save(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['will'] == '+2'

    def test_init_from_dex_modifier(self):
        # DEX modifier (+1) → init = "+1"
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['init'] == '+1'

    def test_speed(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['speed'] == '20'

    def test_alignment_unaligned_maps_to_N(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['alignment'] == 'N'

    def test_alignment_neutral_evil_maps_to_N(self):
        # NE is on the neutral axis — maps to N, not C
        row = parse_5e_block('Zombie', ZOMBIE_BLOCK)
        assert row['alignment'] == 'N'

    def test_alignment_chaotic_evil_maps_to_C(self):
        row = parse_5e_block('Ghoul', GHOUL_BLOCK)
        assert row['alignment'] == 'C'

    def test_source_is_5e(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['source'] == '5e'

    def test_default_quantity(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['quantity'] == '1'

    def test_default_act(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['act'] == '1d20'

    def test_default_crit(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['crit'] == 'M/d6'


class TestCRToHD:
    def test_cr_quarter(self):
        assert _cr_to_hd(0.25) == '1d6'

    def test_cr_half(self):
        assert _cr_to_hd(0.5) == '1d6'

    def test_cr_1(self):
        assert _cr_to_hd(1) == '1d8'

    def test_cr_2(self):
        assert _cr_to_hd(2) == '2d8'

    def test_cr_3(self):
        assert _cr_to_hd(3) == '3d8'

    def test_cr_6(self):
        assert _cr_to_hd(6) == '6d8'

    def test_cr_less_than_quarter(self):
        assert _cr_to_hd(0) == '1d4'


class TestSplit5eBlocks:
    def test_extract_by_name(self):
        text = CAVE_FISHER_BLOCK + "\n\n" + ZOMBIE_BLOCK
        blocks = split_5e_blocks(text)
        assert 'cave fisher' in blocks
        assert 'zombie' in blocks

    def test_name_lookup_is_case_insensitive(self):
        blocks = split_5e_blocks(CAVE_FISHER_BLOCK)
        assert 'cave fisher' in blocks

    def test_unknown_name_not_in_dict(self):
        blocks = split_5e_blocks(CAVE_FISHER_BLOCK)
        assert 'phase spider' not in blocks
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_parse_statblocks.py::TestParse5eBlock tests/test_parse_statblocks.py::TestCRToHD tests/test_parse_statblocks.py::TestSplit5eBlocks -v
```

Expected: FAIL with ImportError or AttributeError

- [ ] **Step 3: Implement 5e parsing functions — add to parse_statblocks.py**

```python
# ---------------------------------------------------------------------------
# 5e parsing
# ---------------------------------------------------------------------------

def _5e_alignment_to_dcc(alignment_text):
    """Map 5e alignment string to DCC single character.

    Mapping: lawful* → L, chaotic* → C, everything else (neutral, NE, NG, unaligned) → N.
    Spec: LG/LN/LE → L, CG/CN/CE → C, N/TN/unaligned → N.
    Note: neutral evil (NE) maps to N — it is on the neutral axis, not chaotic.
    """
    text = alignment_text.lower().strip()
    if 'lawful' in text:
        return 'L'
    if 'chaotic' in text:
        return 'C'
    return 'N'


def _parse_cr(cr_text):
    """Parse CR string like '3', '1/4', '1/2' into a float."""
    cr_text = cr_text.strip()
    if '/' in cr_text:
        num, denom = cr_text.split('/')
        return int(num) / int(denom)
    try:
        return float(cr_text)
    except ValueError:
        return 0.0


def _cr_to_hd(cr):
    """Map CR float to DCC HD string."""
    if cr < 0.25:
        return '1d4'
    elif cr < 1:
        return '1d6'
    elif cr == 1:
        return '1d8'
    else:
        n = int(cr)
        return f'{n}d8'


def _parse_dex_modifier(block_text):
    """Extract DEX ability modifier from the ability score block.

    The ability score block looks like:
      STR  DEX  CON  INT  WIS  CHA
      16   13   12   1    10   3
      (+3) (+1) (+1) (-5) (0)  (-4)

    The modifier line is the line with parenthesized values. DEX is the 2nd entry.
    Returns the modifier as a signed string like '+1' or '-2'.
    """
    # Find the modifier line: a line where most tokens are (±N)
    mod_line_re = re.compile(r'^\s*\([+-]?\d+\)(?:\s+\([+-]?\d+\)){3,}', re.MULTILINE)
    m = mod_line_re.search(block_text)
    if not m:
        return '+0'
    tokens = re.findall(r'\(([+-]?\d+)\)', m.group())
    if len(tokens) < 2:
        return '+0'
    val = tokens[1]  # DEX is index 1
    if not val.startswith(('+', '-')):
        val = '+' + val
    return val


def _parse_5e_saves(saves_text):
    """Parse 'CON +3, DEX +1, WIS +2' into (fort, ref, will) strings.

    Returns tuple of signed strings. Any save not mentioned defaults to '+0'.
    """
    def find(abbr):
        m = re.search(rf'\b{abbr}\s+([+-]\d+)', saves_text or '', re.IGNORECASE)
        return m.group(1) if m else '+0'
    return find('CON'), find('DEX'), find('WIS')


def _parse_5e_speed(speed_text):
    """Extract (speed, fly) from '20 ft., climb 20 ft.' or '30 ft., fly 60 ft.'"""
    speed_m = re.match(r'(\d+)', speed_text.strip())
    speed = speed_m.group(1) if speed_m else ''
    fly_m = re.search(r'fly\s+(\d+)', speed_text, re.IGNORECASE)
    fly = fly_m.group(1) if fly_m else ''
    return speed, fly


def split_5e_blocks(text):
    """Split 5e lore text into a dict of {name_lower: block_text}.

    A block starts with a name line immediately followed by a type line
    matching: <Size> <type>, <alignment>
    """
    type_line_re = re.compile(
        r'^(Tiny|Small|Medium|Large|Huge|Gargantuan)\s+\S.*?,\s+\S',
        re.IGNORECASE
    )
    lines = text.split('\n')
    blocks = {}
    current_name = None
    current_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ''
        if next_line and type_line_re.match(next_line.strip()):
            # This line is a creature name
            if current_name is not None:
                blocks[current_name.lower()] = '\n'.join(current_lines)
            current_name = line.strip()
            current_lines = [line, next_line]
            i += 2
        elif current_name is not None:
            current_lines.append(line)
            i += 1
        else:
            i += 1

    if current_name is not None:
        blocks[current_name.lower()] = '\n'.join(current_lines)
    return blocks


def parse_5e_block(name, block_text):
    """Parse a 5e stat block string into a CSV row dict."""
    def get(pattern, default=''):
        m = re.search(pattern, block_text, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else default

    type_line = re.search(
        r'(Tiny|Small|Medium|Large|Huge|Gargantuan)\s+\S.*?,\s+(.+)',
        block_text, re.IGNORECASE
    )
    alignment_text = type_line.group(2).strip() if type_line else ''
    alignment = _5e_alignment_to_dcc(alignment_text)

    ac = get(r'Armor Class\s+(\d+)')
    hp_avg = get(r'Hit Points\s+(\d+)')

    cr_text = get(r'Challenge\s+([\d/]+)')
    cr = _parse_cr(cr_text)
    hd = _cr_to_hd(cr)

    speed_text = get(r'Speed\s+([^\n]+)')
    speed, fly = _parse_5e_speed(speed_text)

    init = _parse_dex_modifier(block_text)

    saves_text = get(r'Saving Throws\s+([^\n]+)')
    fort, ref, will = _parse_5e_saves(saves_text)

    # Actions block
    actions_m = re.search(r'\bActions\b\s*\n(.*?)(?=\n[A-Z][a-z]|\Z)', block_text, re.DOTALL)
    attacks_raw = actions_m.group(1).strip() if actions_m else ''

    # Special abilities (text between type line and first section header)
    sp_m = re.search(r'\n\n(.*?)(?=\n\n[A-Z])', block_text, re.DOTALL)
    sp_raw = sp_m.group(1).strip() if sp_m else ''

    return {
        'name': name,
        'quantity': '1',
        'hd': hd,
        'hp_avg': hp_avg,
        'ac': ac,
        'init': init,
        'speed': speed,
        'fly': fly,
        'act': '1d20',
        'fort': fort,
        'ref': ref,
        'will': will,
        'alignment': alignment,
        'attacks_raw': attacks_raw,
        'sp_raw': sp_raw,
        'crit': 'M/d6',
        'source': '5e',
        'notes': ''
    }
```

- [ ] **Step 4: Run 5e tests to confirm they pass**

```
python -m pytest tests/test_parse_statblocks.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/parse_statblocks.py tests/test_parse_statblocks.py
git commit -m "feat: add 5e stat block parser with CR->HD table and alignment mapping"
```

---

### Task 4: parse_statblocks.py — merge logic + CSV write + run()

**Files:**
- Modify: `agents/in-progress/parse_statblocks.py`
- Modify: `tests/test_parse_statblocks.py`

- [ ] **Step 1: Write failing merge and run() tests**

Add to `tests/test_parse_statblocks.py`:

```python
from parse_statblocks import merge_rows, run
import csv
import io

STIRGE_ROW = parse_dcc_block(STIRGE_BLOCK)
STIRGE_5E_ROW = {
    'name': 'Stirge', 'quantity': '1', 'hd': '1d8', 'hp_avg': '100',
    'ac': '99', 'init': '+1', 'speed': '5', 'fly': '', 'act': '1d20',
    'fort': '+99', 'ref': '+99', 'will': '+99', 'alignment': 'L',
    'attacks_raw': '5e_attack', 'sp_raw': '5e_sp', 'crit': 'M/d12',
    'source': '5e', 'notes': ''
}


class TestMergeRows:
    def test_dcc_authoritative_for_ac(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['ac'] == '10'  # DCC value, not 5e's '99'

    def test_dcc_authoritative_for_init(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['init'] == '+6'

    def test_source_becomes_both(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['source'] == 'both'

    def test_name_preserved(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['name'] == 'Stirge'


class TestRunLorePreservation:
    """When source='both', the 5e lore block must remain in the lore index
    (accessible via split_5e_blocks) for Stage 3 flavor text lookup.
    The merge only affects the CSV fields — the lore index is separate.
    """
    def test_both_source_lore_block_still_in_5e_index(self, tmp_path):
        from parse_statblocks import split_5e_blocks, run as parse_run

        dcc_path = tmp_path / 'dcc_statblocks.txt'
        dcc_path.write_text(STIRGE_BLOCK, encoding='utf-8')

        # A minimal 5e block for Stirge
        stirge_5e = (
            "Stirge\n"
            "Tiny beast, unaligned\n\n"
            "Armor Class 10\n"
            "Hit Points 2 (1d4)\n"
            "Speed 10 ft., fly 40 ft.\n\n"
            "STR  DEX  CON  INT  WIS  CHA\n"
            "4    16   11   2    8    6\n"
            "(-3) (+3) (0)  (-4) (-1) (-2)\n\n"
            "Challenge 1/8 (25 XP)\n"
        )
        lore_path = tmp_path / 'lore_5e_sections.txt'
        lore_path.write_text(stirge_5e, encoding='utf-8')
        csv_path = tmp_path / 'master_monsters.csv'

        parse_run(
            dcc_path=str(dcc_path),
            lore_path=str(lore_path),
            csv_path=str(csv_path)
        )

        # The lore index must still contain 'stirge' so Stage 3 can retrieve it
        lore_blocks = split_5e_blocks(lore_path.read_text(encoding='utf-8'))
        assert 'stirge' in lore_blocks
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_parse_statblocks.py::TestMergeRows -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement merge_rows() and run() — add to parse_statblocks.py**

```python
# ---------------------------------------------------------------------------
# Merge + CSV write
# ---------------------------------------------------------------------------

MECHANIC_FIELDS = [
    'ac', 'hd', 'hp_avg', 'init', 'fort', 'ref', 'will', 'speed', 'fly',
    'act', 'attacks_raw', 'sp_raw', 'crit', 'quantity', 'alignment'
]


def merge_rows(dcc_row, five_e_row):
    """Merge DCC (authoritative) and 5e rows. Returns a new row with source='both'."""
    merged = dict(five_e_row)
    for field in MECHANIC_FIELDS:
        merged[field] = dcc_row[field]
    merged['source'] = 'both'
    merged['name'] = dcc_row['name']
    return merged


def run(
    dcc_path='data/input/monster-source/dcc_statblocks.txt',
    lore_path='data/input/monster-source/lore_5e_sections.txt',
    csv_path='data/input/master_monsters.csv'
):
    """Parse source files and write master_monsters.csv.

    Reads DCC text and (optionally) 5e lore text. Merges overlapping entries
    with DCC as authoritative source. Writes result to master_monsters.csv.
    """
    dcc_rows = {}
    dcc_text = Path(dcc_path).read_text(encoding='utf-8') if Path(dcc_path).exists() else ''
    for block in split_dcc_blocks(dcc_text):
        try:
            row = parse_dcc_block(block)
            dcc_rows[row['name'].lower()] = row
        except ValueError as e:
            print(f"[WARN] Skipping malformed DCC block: {e}")

    lore_blocks = {}
    if Path(lore_path).exists():
        lore_text = Path(lore_path).read_text(encoding='utf-8')
        lore_blocks = split_5e_blocks(lore_text)

    five_e_rows = {}
    for name_lower, block_text in lore_blocks.items():
        try:
            name_display = next(
                (r for r in block_text.split('\n') if r.strip()), name_lower
            ).strip()
            row = parse_5e_block(name_display, block_text)
            five_e_rows[name_lower] = row
        except Exception as e:
            print(f"[WARN] Skipping malformed 5e block '{name_lower}': {e}")

    # Merge: DCC-only, 5e-only, both
    all_names = set(dcc_rows.keys()) | set(five_e_rows.keys())
    output_rows = []
    for name_lower in sorted(all_names):
        if name_lower in dcc_rows and name_lower in five_e_rows:
            output_rows.append(merge_rows(dcc_rows[name_lower], five_e_rows[name_lower]))
        elif name_lower in dcc_rows:
            output_rows.append(dcc_rows[name_lower])
        else:
            output_rows.append(five_e_rows[name_lower])

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(output_rows)} monsters to {csv_path}")


if __name__ == '__main__':
    run()
```

- [ ] **Step 4: Run all parse_statblocks tests**

```
python -m pytest tests/test_parse_statblocks.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/parse_statblocks.py tests/test_parse_statblocks.py
git commit -m "feat: add merge logic and CSV writer to parse_statblocks"
```

---

### Task 5: gap_analysis.py

**Files:**
- Create: `agents/in-progress/gap_analysis.py`
- Create: `tests/test_gap_analysis.py`

- [ ] **Step 1: Write failing gap analysis tests**

Create `tests/test_gap_analysis.py`:

```python
# tests/test_gap_analysis.py
import csv
import json
import pytest
from pathlib import Path
from gap_analysis import find_gaps, run


def make_csv(tmp_path, rows):
    """Write a minimal master_monsters.csv to tmp_path."""
    path = tmp_path / 'master_monsters.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name'])
        writer.writeheader()
        for name in rows:
            writer.writerow({'name': name})
    return path


def make_roll20(tmp_path, names):
    """Write a minimal thracia-characters.json to tmp_path."""
    path = tmp_path / 'thracia-characters.json'
    chars = [{'name': n} for n in names]
    path.write_text(json.dumps(chars), encoding='utf-8')
    return path


class TestFindGaps:
    def test_monster_in_csv_not_in_roll20_is_a_gap(self):
        gaps = find_gaps(['Stirge', 'Gnoll'], ['Gnoll'])
        assert 'Stirge' in gaps

    def test_monster_in_both_is_not_a_gap(self):
        gaps = find_gaps(['Gnoll'], ['Gnoll'])
        assert 'Gnoll' not in gaps

    def test_matching_is_case_insensitive(self):
        gaps = find_gaps(['Cave Fisher'], ['cave fisher'])
        assert 'Cave Fisher' not in gaps

    def test_matching_strips_whitespace(self):
        gaps = find_gaps(['Stirge'], ['  Stirge  '])
        assert 'Stirge' not in gaps

    def test_returns_csv_casing(self):
        gaps = find_gaps(['Cave Fisher'], ['gnoll'])
        assert 'Cave Fisher' in gaps

    def test_empty_csv_returns_no_gaps(self):
        gaps = find_gaps([], ['Gnoll'])
        assert gaps == []


class TestRun:
    def test_gap_report_is_one_name_per_line(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Cave Fisher', 'Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        lines = report_path.read_text().strip().split('\n')
        assert lines == ['Cave Fisher']

    def test_gap_report_has_no_headers(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Stirge'])
        roll20_path = make_roll20(tmp_path, [])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        content = report_path.read_text()
        assert 'name' not in content.lower()

    def test_no_gaps_writes_empty_file(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        assert report_path.read_text().strip() == ''

    def test_no_gaps_prints_message(self, tmp_path, capsys):
        csv_path = make_csv(tmp_path, ['Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_gap_analysis.py -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement gap_analysis.py**

Create `agents/in-progress/gap_analysis.py`:

```python
# agents/in-progress/gap_analysis.py
#
# Stage 2: Compare master_monsters.csv against Roll20 export.
# Writes gap_report.txt — one name per line — for missing monsters.
#
# Usage: python run.py monster --gap-analysis

import csv
import json
from pathlib import Path

CSV_PATH = 'data/input/master_monsters.csv'
ROLL20_PATH = 'data/input/thracia-exports/thracia-characters.json'
REPORT_PATH = 'data/output/gap_report.txt'


def find_gaps(csv_names, roll20_names):
    """Return list of csv_names that have no case-insensitive match in roll20_names."""
    roll20_lower = {n.strip().lower() for n in roll20_names}
    return [name for name in csv_names if name.strip().lower() not in roll20_lower]


def run(
    csv_path=CSV_PATH,
    roll20_path=ROLL20_PATH,
    report_path=REPORT_PATH
):
    """Compare CSV against Roll20 export, write gap_report.txt."""
    # Read monster names from CSV
    csv_names = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_names.append(row['name'])

    # Read NPC names from Roll20 export
    roll20_data = json.loads(Path(roll20_path).read_text(encoding='utf-8'))
    # Roll20 export: list of character objects, each with a 'name' key
    roll20_names = [char.get('name', '') for char in roll20_data]

    gaps = find_gaps(csv_names, roll20_names)

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(gaps))
        if gaps:
            f.write('\n')

    if gaps:
        print(f"{len(gaps)} monsters missing from Roll20. See {report_path}")
    else:
        print("No gaps found. Nothing to generate.")


if __name__ == '__main__':
    run()
```

- [ ] **Step 4: Run gap analysis tests**

```
python -m pytest tests/test_gap_analysis.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/gap_analysis.py tests/test_gap_analysis.py
git commit -m "feat: add gap_analysis module with 8 passing tests"
```

---

### Task 6: monster_gen.py — deterministic transforms

**Files:**
- Create: `agents/in-progress/monster_gen.py`
- Create: `tests/test_monster_gen.py`

- [ ] **Step 1: Write failing deterministic transform tests**

Create `tests/test_monster_gen.py`:

```python
# tests/test_monster_gen.py
import pytest
from monster_gen import (
    strip_sign, alignment_to_words, sanitize_filename,
    build_description, build_hit_points
)

STIRGE_ROW = {
    'name': 'Stirge', 'quantity': '1d4', 'hd': '1d5+1', 'hp_avg': '4',
    'ac': '10', 'init': '+6', 'speed': '30', 'fly': '60', 'act': '1d20',
    'fort': '+2', 'ref': '+6', 'will': '+0', 'alignment': 'C',
    'attacks_raw': 'bite +0 melee (1d3+1 plus blood drain)',
    'sp_raw': 'blood drain (1 Stamina, DC 7 Fort save negates)',
    'crit': 'M/d4', 'source': 'dcc', 'notes': ''
}

FISHER_ROW = {
    'name': 'Cave Fisher', 'quantity': '1', 'hd': '3d8', 'hp_avg': '58',
    'ac': '16', 'init': '+1', 'speed': '20', 'fly': '', 'act': '1d20',
    'fort': '+3', 'ref': '+0', 'will': '+2', 'alignment': 'N',
    'attacks_raw': 'filament +5 melee (grapple)',
    'sp_raw': '', 'crit': 'M/d6', 'source': '5e', 'notes': ''
}


class TestStripSign:
    def test_positive_drops_plus(self):
        assert strip_sign('+6') == 6

    def test_zero_drops_plus(self):
        assert strip_sign('+0') == 0

    def test_negative_preserved(self):
        assert strip_sign('-1') == -1

    def test_returns_int(self):
        assert isinstance(strip_sign('+3'), int)


class TestAlignmentToWords:
    def test_C_is_chaotic(self):
        assert alignment_to_words('C') == 'chaotic'

    def test_L_is_lawful(self):
        assert alignment_to_words('L') == 'lawful'

    def test_N_is_neutral(self):
        assert alignment_to_words('N') == 'neutral'


class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert sanitize_filename('Cave Fisher') == 'cave_fisher.json'

    def test_lowercase(self):
        assert sanitize_filename('Stirge') == 'stirge.json'


class TestBuildHitPoints:
    def test_current_equals_max(self):
        hp = build_hit_points('4')
        assert hp['current'] == hp['max']

    def test_value_is_from_hp_avg(self):
        hp = build_hit_points('58')
        assert hp['max'] == 58

    def test_values_are_integers(self):
        hp = build_hit_points('4')
        assert isinstance(hp['max'], int)


class TestBuildDescription:
    def test_contains_qty(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Qty: 1d4' in desc

    def test_contains_crit(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Crit: M/d4' in desc

    def test_contains_fly_when_present(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Fly: 60' in desc

    def test_no_fly_when_absent(self):
        desc = build_description(FISHER_ROW, armor_str='AC: P16/S16/B16')
        assert 'Fly:' not in desc

    def test_contains_armor_str(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'AC: P10/S10/B10' in desc

    def test_contains_faction(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Faction: none' in desc

    def test_contains_morale(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Morale DC:' in desc
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_monster_gen.py::TestStripSign tests/test_monster_gen.py::TestAlignmentToWords tests/test_monster_gen.py::TestSanitizeFilename tests/test_monster_gen.py::TestBuildHitPoints tests/test_monster_gen.py::TestBuildDescription -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement deterministic functions in monster_gen.py**

Create `agents/in-progress/monster_gen.py`:

```python
# agents/in-progress/monster_gen.py
#
# Stage 3: Generate Roll20 JSON for monsters listed in gap_report.txt.
# Calls Claude API for sp expansion, attack details, and armor vectors.
#
# Usage:
#   python run.py monster --generate --all
#   python run.py monster --generate --name "Stirge"

import csv
import json
import re
import sys
from pathlib import Path

import anthropic

CSV_PATH = 'data/input/master_monsters.csv'
SCHEMA_PATH = 'docs/roll20-npc-schema.md'
LORE_PATH = 'data/input/monster-source/lore_5e_sections.txt'
GAP_REPORT_PATH = 'data/output/gap_report.txt'
PENDING_DIR = 'data/output/pending'

ALIGNMENT_MAP = {'C': 'chaotic', 'L': 'lawful', 'N': 'neutral'}


def strip_sign(value):
    """Strip leading '+' from a signed number string. Preserve '-'. Return int."""
    return int(str(value).lstrip('+'))


def alignment_to_words(code):
    """Convert single-character alignment code to full word."""
    return ALIGNMENT_MAP.get(code.upper(), 'neutral')


def sanitize_filename(name):
    """Convert monster name to a safe filename: lowercase, spaces→underscores."""
    safe = re.sub(r'[^\w\s-]', '', name.lower())
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe + '.json'


def build_hit_points(hp_avg):
    """Build Roll20 hit_points object from hp_avg string."""
    val = int(hp_avg)
    return {'current': val, 'max': val}


def build_description(row, armor_str, morale_dc=11):
    """Build the Roll20 description field from CSV row values and Claude-provided armor string."""
    parts = [
        armor_str,
        f"Crit: {row['crit']}.",
        f"Qty: {row['quantity']}.",
    ]
    if row.get('fly'):
        parts.append(f"Fly: {row['fly']}.")
    parts.append("Faction: none.")
    parts.append(f"Morale DC: {morale_dc}.")
    if row.get('notes'):
        parts.append(row['notes'])
    return ' '.join(parts)
```

- [ ] **Step 4: Run deterministic tests**

```
python -m pytest tests/test_monster_gen.py::TestStripSign tests/test_monster_gen.py::TestAlignmentToWords tests/test_monster_gen.py::TestSanitizeFilename tests/test_monster_gen.py::TestBuildHitPoints tests/test_monster_gen.py::TestBuildDescription -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/monster_gen.py tests/test_monster_gen.py
git commit -m "feat: add monster_gen deterministic transforms with 14 passing tests"
```

---

### Task 7: monster_gen.py — Claude API integration

**Files:**
- Modify: `agents/in-progress/monster_gen.py`
- Modify: `tests/test_monster_gen.py`

Note: Ensure `ANTHROPIC_API_KEY` is set in your environment before running integration tests. Unit tests mock the API.

- [ ] **Step 1: Write failing Claude integration tests (mocked)**

Add to `tests/test_monster_gen.py`:

```python
import json
from unittest.mock import patch, MagicMock
from monster_gen import generate_sheet, load_csv_by_name

MOCK_CLAUDE_RESPONSE = json.dumps({
    "armor_str": "AC: P10/S10/B10",
    "sp": "Blood drain: on hit, target loses 1 Stamina (DC 7 Fort negates).",
    "attacks": [
        {"name": "Bite", "attack": "+0", "damage": "1d3+1", "type": "piercing"}
    ],
    "morale_dc": 11
})

SCHEMA_CONTENT = "# Roll20 NPC Schema\nField reference."


class TestGenerateSheet:
    def _mock_claude(self, response_text):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=response_text)]
        mock_client.messages.create.return_value = mock_msg
        return mock_client

    def test_output_contains_is_npc(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['is_npc'] == 1

    def test_output_name_preserved(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['name'] == 'Stirge'

    def test_alignment_converted_to_words(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['alignment'] == 'chaotic'

    def test_fort_is_int_without_plus(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['fort'] == 2
        assert isinstance(sheet['fort'], int)

    def test_init_is_int_without_plus(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['init'] == 6

    def test_hit_points_structure(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['hit_points'] == {'current': 4, 'max': 4}

    def test_attack_1_keys_present(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'repeating_attacks_-npc_attack_1_name' in sheet
        assert 'repeating_attacks_-npc_attack_1_attack' in sheet
        assert 'repeating_attacks_-npc_attack_1_damage' in sheet
        assert 'repeating_attacks_-npc_attack_1_type' in sheet

    def test_attack_1_name_value(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['repeating_attacks_-npc_attack_1_name'] == 'Bite'

    def test_sp_field_populated(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'Blood drain' in sheet['sp']

    def test_description_contains_armor_str(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'AC: P10/S10/B10' in sheet['description']

    def test_multi_attack_generates_multiple_keys(self):
        multi_row = dict(STIRGE_ROW)
        multi_row['attacks_raw'] = 'claw +2 melee (1d4) / claw +2 melee (1d4) / bite +4 melee (1d8)'
        multi_response = json.dumps({
            "armor_str": "AC: P10/S10/B10",
            "sp": "",
            "attacks": [
                {"name": "Claw", "attack": "+2", "damage": "1d4", "type": "slashing"},
                {"name": "Claw", "attack": "+2", "damage": "1d4", "type": "slashing"},
                {"name": "Bite", "attack": "+4", "damage": "1d8", "type": "piercing"},
            ],
            "morale_dc": 11
        })
        client = self._mock_claude(multi_response)
        sheet = generate_sheet(multi_row, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'repeating_attacks_-npc_attack_3_name' in sheet

    def test_empty_attacks_raw_generates_unarmed_strike(self):
        no_attack_row = dict(FISHER_ROW)
        no_attack_row['attacks_raw'] = ''
        unarmed_response = json.dumps({
            "armor_str": "AC: P16/S16/B16",
            "sp": "",
            "attacks": [
                {"name": "Unarmed Strike", "attack": "+0", "damage": "1d3",
                 "type": "bludgeoning"}
            ],
            "morale_dc": 11
        })
        client = self._mock_claude(unarmed_response)
        sheet = generate_sheet(no_attack_row, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['repeating_attacks_-npc_attack_1_name'] == 'Unarmed Strike'

    def test_empty_sp_raw_gives_empty_sp(self):
        client = self._mock_claude(json.dumps({
            "armor_str": "AC: P16/S16/B16",
            "sp": "",
            "attacks": [{"name": "Filament", "attack": "+5", "damage": "special",
                         "type": "piercing"}],
            "morale_dc": 11
        }))
        sheet = generate_sheet(FISHER_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['sp'] == ''
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_monster_gen.py::TestGenerateSheet -v
```

Expected: FAIL with ImportError (generate_sheet not defined yet)

- [ ] **Step 3: Implement generate_sheet() and the Claude prompt — add to monster_gen.py**

```python
def _build_prompt(row, schema, lore_block):
    """Build the Claude prompt for monster sheet generation."""
    lore_section = f"\n\n5e lore block:\n{lore_block}" if lore_block else ""
    return f"""You are generating a Roll20 NPC sheet for a DCC RPG campaign.

Monster CSV data:
{json.dumps(row, indent=2)}

Roll20 schema reference:
{schema}
{lore_section}

Generate a JSON object with these fields:
- armor_str: armor vector string like "AC: P10/S10/B10"
  - Natural armor creatures (beasts, monstrosities, undead): all vectors equal ac
  - Armored humanoids: use the equipment table (chain mail = S17/P15/B13, etc.)
  - Shield adds +1 to all vectors
- sp: expanded special ability text (empty string if sp_raw is empty)
- attacks: list of attack objects, one per attack in attacks_raw (split on "/")
  Each attack: {{"name": str, "attack": str (with sign, e.g. "+0"), "damage": str, "type": str}}
  If attacks_raw is empty: generate one placeholder Unarmed Strike (+0, 1d3, bludgeoning)
  Attack type inferred from name: bite/filament→piercing, claw/talon→slashing, slam/crush→bludgeoning
- morale_dc: integer, default 11; increase to 13-15 for fear auras or fanatical creatures

Return ONLY the JSON object, no other text."""


def generate_sheet(row, schema, lore_block, client=None):
    """Generate a complete Roll20 JSON sheet for one monster.

    Args:
        row: dict from master_monsters.csv
        schema: contents of docs/roll20-npc-schema.md
        lore_block: 5e lore text for this monster (empty string if none)
        client: anthropic.Anthropic() client (injectable for testing)

    Returns:
        dict: complete Roll20 JSON sheet
    """
    if client is None:
        client = anthropic.Anthropic()

    prompt = _build_prompt(row, schema, lore_block)
    message = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2048,
        messages=[{'role': 'user', 'content': prompt}]
    )
    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith('```'):
        response_text = re.sub(r'^```\w*\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text.strip())

    claude_data = json.loads(response_text)

    # Build the Roll20 sheet
    sheet = {
        'is_npc': 1,
        'name': row['name'],
        'hd': row['hd'],
        'hit_points': build_hit_points(row['hp_avg']),
        'ac': int(row['ac']),
        'fort': strip_sign(row['fort']),
        'ref': strip_sign(row['ref']),
        'will': strip_sign(row['will']),
        'init': strip_sign(row['init']),
        'act': row['act'],
        'speed': row['speed'],
        'alignment': alignment_to_words(row['alignment']),
        'sp': claude_data.get('sp', ''),
        'description': build_description(
            row,
            armor_str=claude_data['armor_str'],
            morale_dc=claude_data.get('morale_dc', 11)
        )
    }

    # Expand attacks into repeating_attacks_* keys
    for i, attack in enumerate(claude_data.get('attacks', []), start=1):
        prefix = f'repeating_attacks_-npc_attack_{i}'
        sheet[f'{prefix}_name'] = attack['name']
        sheet[f'{prefix}_attack'] = attack['attack']
        sheet[f'{prefix}_damage'] = attack['damage']
        sheet[f'{prefix}_type'] = attack['type']

    return sheet
```

- [ ] **Step 4: Run Claude integration tests**

```
python -m pytest tests/test_monster_gen.py::TestGenerateSheet -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/monster_gen.py tests/test_monster_gen.py
git commit -m "feat: add Claude API integration for monster sheet generation, 13 passing tests"
```

---

### Task 8: monster_gen.py — CLI dispatch + file I/O

**Files:**
- Modify: `agents/in-progress/monster_gen.py`
- Modify: `tests/test_monster_gen.py`

- [ ] **Step 1: Write failing CLI dispatch tests**

Add to `tests/test_monster_gen.py`:

```python
from monster_gen import load_csv_by_name, write_sheet, run_generate_all, run_generate_name

class TestLoadCSVByName:
    def test_finds_monster_by_name(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'hp_avg'])
            writer.writeheader()
            writer.writerow({'name': 'Stirge', 'hp_avg': '4'})
        row = load_csv_by_name('Stirge', str(csv_path))
        assert row['hp_avg'] == '4'

    def test_returns_none_for_missing_monster(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name'])
            writer.writeheader()
        row = load_csv_by_name('Stirge', str(csv_path))
        assert row is None


class TestWriteSheet:
    def test_writes_json_file(self, tmp_path):
        pending = tmp_path / 'pending'
        pending.mkdir()
        sheet = {'name': 'Stirge', 'is_npc': 1}
        write_sheet(sheet, str(pending))
        assert (pending / 'stirge.json').exists()

    def test_overwrites_existing_file(self, tmp_path):
        pending = tmp_path / 'pending'
        pending.mkdir()
        (pending / 'stirge.json').write_text('{"old": true}')
        sheet = {'name': 'Stirge', 'is_npc': 1}
        write_sheet(sheet, str(pending))
        data = json.loads((pending / 'stirge.json').read_text())
        assert 'old' not in data

    def test_empty_gap_report_prints_no_gaps(self, tmp_path, capsys):
        report = tmp_path / 'gap_report.txt'
        report.write_text('')
        csv_path = tmp_path / 'master_monsters.csv'
        csv_path.write_text('name\n')
        run_generate_all(
            gap_report_path=str(report),
            csv_path=str(csv_path),
            pending_dir=str(tmp_path / 'pending')
        )
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out

    def test_missing_gap_report_prints_no_gaps(self, tmp_path, capsys):
        csv_path = tmp_path / 'master_monsters.csv'
        csv_path.write_text('name\n')
        run_generate_all(
            gap_report_path=str(tmp_path / 'nonexistent_gap_report.txt'),
            csv_path=str(csv_path),
            pending_dir=str(tmp_path / 'pending')
        )
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out


class TestRunGenerateName:
    def test_missing_monster_exits_nonzero(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name'])
            writer.writeheader()
        with pytest.raises(SystemExit) as exc:
            run_generate_name('Nonexistent', csv_path=str(csv_path))
        assert exc.value.code != 0

    def test_generate_name_bypasses_gap_report(self, tmp_path):
        """--name should generate even if monster is not in gap_report.txt."""
        from unittest.mock import patch, MagicMock
        # CSV has Stirge; gap_report is empty (Stirge already in Roll20)
        csv_path = tmp_path / 'master_monsters.csv'
        from parse_statblocks import CSV_COLUMNS
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerow({col: STIRGE_ROW.get(col, '') for col in CSV_COLUMNS})
        pending = tmp_path / 'pending'
        mock_sheet = {'name': 'Stirge', 'is_npc': 1}
        with patch('monster_gen.generate_sheet', return_value=mock_sheet):
            run_generate_name(
                'Stirge',
                csv_path=str(csv_path),
                pending_dir=str(pending)
            )
        assert (pending / 'stirge.json').exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_monster_gen.py::TestLoadCSVByName tests/test_monster_gen.py::TestWriteSheet tests/test_monster_gen.py::TestRunGenerateName -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement file I/O and dispatch functions — add to monster_gen.py**

```python
def load_csv_by_name(name, csv_path=CSV_PATH):
    """Find and return the CSV row for a monster by name. Returns None if not found."""
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['name'].strip().lower() == name.strip().lower():
                return row
    return None


def load_all_csv(csv_path=CSV_PATH):
    """Return all rows from master_monsters.csv as a list of dicts."""
    with open(csv_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_sheet(sheet, pending_dir=PENDING_DIR):
    """Write a Roll20 JSON sheet to pending_dir/<sanitized_name>.json."""
    Path(pending_dir).mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(sheet['name'])
    path = Path(pending_dir) / filename
    path.write_text(json.dumps(sheet, indent=2), encoding='utf-8')
    print(f"  Wrote {path}")


def _get_lore_block(name, lore_path=LORE_PATH):
    """Return the 5e lore block for a monster name, or empty string."""
    if not Path(lore_path).exists():
        return ''
    from parse_statblocks import split_5e_blocks
    text = Path(lore_path).read_text(encoding='utf-8')
    blocks = split_5e_blocks(text)
    return blocks.get(name.strip().lower(), '')


def run_generate_all(
    gap_report_path=GAP_REPORT_PATH,
    csv_path=CSV_PATH,
    pending_dir=PENDING_DIR,
    client=None
):
    """Generate sheets for all monsters in gap_report.txt."""
    # Missing file treated as empty
    if not Path(gap_report_path).exists():
        print("No gaps found. Nothing to generate.")
        return

    names = [
        line.strip()
        for line in Path(gap_report_path).read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]
    if not names:
        print("No gaps found. Nothing to generate.")
        return

    schema = Path(SCHEMA_PATH).read_text(encoding='utf-8') if Path(SCHEMA_PATH).exists() else ''
    if client is None:
        client = anthropic.Anthropic()

    for name in names:
        row = load_csv_by_name(name, csv_path)
        if not row:
            print(f"[WARN] '{name}' in gap report but not in CSV — skipping")
            continue
        lore = _get_lore_block(name)
        print(f"Generating: {name}")
        sheet = generate_sheet(row, schema=schema, lore_block=lore, client=client)
        write_sheet(sheet, pending_dir)


def run_generate_name(
    name,
    csv_path=CSV_PATH,
    pending_dir=PENDING_DIR,
    client=None
):
    """Generate a sheet for a single named monster (bypasses gap report)."""
    row = load_csv_by_name(name, csv_path)
    if not row:
        print(f"Error: Monster '{name}' not found in master_monsters.csv")
        sys.exit(1)

    schema = Path(SCHEMA_PATH).read_text(encoding='utf-8') if Path(SCHEMA_PATH).exists() else ''
    if client is None:
        client = anthropic.Anthropic()

    lore = _get_lore_block(name)
    print(f"Generating: {name}")
    sheet = generate_sheet(row, schema=schema, lore_block=lore, client=client)
    write_sheet(sheet, pending_dir)
```

- [ ] **Step 4: Run all monster_gen tests**

```
python -m pytest tests/test_monster_gen.py -v
```

Expected: all pass (mocked tests pass; integration tests that call real API are skipped)

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/monster_gen.py tests/test_monster_gen.py
git commit -m "feat: add monster_gen CLI dispatch and file I/O"
```

---

### Task 9: qa_checker.py — Pass 1 mechanical checks

**Files:**
- Create: `agents/in-progress/qa_checker.py`
- Create: `tests/test_qa_checker.py`

- [ ] **Step 1: Write failing Pass 1 tests**

Create `tests/test_qa_checker.py`:

```python
# tests/test_qa_checker.py
import json
import pytest
from qa_checker import pass1_check

VALID_SHEET = {
    'is_npc': 1,
    'name': 'Stirge',
    'hd': '1d5+1',
    'hit_points': {'current': 4, 'max': 4},
    'ac': 10,
    'fort': 2,
    'ref': 6,
    'will': 0,
    'init': 6,
    'act': '1d20',
    'speed': '30',
    'alignment': 'chaotic',
    'sp': 'Blood drain: on hit, target loses 1 Stamina.',
    'description': 'AC: P10/S10/B10. Crit: M/d4. Qty: 1d4. Faction: none. Morale DC: 11.',
    'repeating_attacks_-npc_attack_1_name': 'Bite',
    'repeating_attacks_-npc_attack_1_attack': '+0',
    'repeating_attacks_-npc_attack_1_damage': '1d3+1',
    'repeating_attacks_-npc_attack_1_type': 'piercing',
}


class TestPass1Check:
    def test_valid_sheet_passes(self):
        errors = pass1_check(VALID_SHEET)
        assert errors == []

    def test_missing_required_field_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['hd']
        errors = pass1_check(sheet)
        assert any('hd' in e for e in errors)

    def test_missing_sp_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['sp']
        errors = pass1_check(sheet)
        assert any('sp' in e for e in errors)

    def test_hit_points_mismatch_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['hit_points'] = {'current': 3, 'max': 4}
        errors = pass1_check(sheet)
        assert any('hit_points' in e for e in errors)

    def test_invalid_hd_notation_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['hd'] = 'five dice'
        errors = pass1_check(sheet)
        assert any('hd' in e for e in errors)

    def test_invalid_alignment_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['alignment'] = 'evil'
        errors = pass1_check(sheet)
        assert any('alignment' in e for e in errors)

    def test_description_missing_armor_vector_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['description'] = 'No armor info here.'
        errors = pass1_check(sheet)
        assert any('description' in e for e in errors)

    def test_attack_group_missing_damage_key_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['repeating_attacks_-npc_attack_1_damage']
        errors = pass1_check(sheet)
        assert any('attack' in e.lower() for e in errors)

    def test_attack_value_as_number_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['repeating_attacks_-npc_attack_1_attack'] = 0  # should be "+0" string
        errors = pass1_check(sheet)
        assert any('attack' in e.lower() for e in errors)

    def test_ac_as_string_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['ac'] = '10'  # should be int
        errors = pass1_check(sheet)
        assert any('ac' in e for e in errors)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_qa_checker.py::TestPass1Check -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement qa_checker.py Pass 1**

Create `agents/in-progress/qa_checker.py`:

```python
# agents/in-progress/qa_checker.py
#
# Stage 4: Validate generated Roll20 JSON before it reaches Roll20.
# Pass 1: mechanical deterministic checks
# Pass 2: Claude judgment review
#
# Usage: python run.py qa

import json
import re
import shutil
import sys
from pathlib import Path

import anthropic

PENDING_DIR = 'data/output/pending'
READY_DIR = 'data/output/ready'
FLAGGED_DIR = 'data/output/flagged'

REQUIRED_FIELDS = [
    'is_npc', 'name', 'hd', 'hit_points', 'ac', 'fort', 'ref', 'will',
    'init', 'act', 'speed', 'alignment', 'sp', 'description'
]
ATTACK_SUFFIXES = ['_name', '_attack', '_damage', '_type']
VALID_ALIGNMENTS = {'lawful', 'neutral', 'chaotic'}
HD_RE = re.compile(r'^\d+d\d+([+-]\d+)?$')
ARMOR_VECTOR_RE = re.compile(r'AC:\s*P\d+/S\d+/B\d+')
NUMBER_FIELDS = {'is_npc', 'ac', 'fort', 'ref', 'will', 'init'}
STRING_FIELDS = {'name', 'hd', 'act', 'speed', 'alignment', 'sp', 'description'}


def pass1_check(sheet):
    """Run mechanical validation on a sheet dict. Returns list of error strings."""
    errors = []

    # Required fields present
    for field in REQUIRED_FIELDS:
        if field not in sheet:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors  # Can't check types/values if fields are missing

    # Type checks: numeric fields
    for field in NUMBER_FIELDS:
        if not isinstance(sheet.get(field), (int, float)):
            errors.append(f"Field '{field}' must be a number, got {type(sheet[field]).__name__}")

    # Type checks: string fields
    for field in STRING_FIELDS:
        if not isinstance(sheet.get(field), str):
            errors.append(f"Field '{field}' must be a string")

    # hit_points structure
    hp = sheet.get('hit_points', {})
    if not isinstance(hp, dict):
        errors.append("hit_points must be an object")
    else:
        if not isinstance(hp.get('current'), (int, float)):
            errors.append("hit_points.current must be a number")
        if not isinstance(hp.get('max'), (int, float)):
            errors.append("hit_points.max must be a number")
        if isinstance(hp.get('current'), (int, float)) and isinstance(hp.get('max'), (int, float)):
            if hp['current'] != hp['max']:
                errors.append(
                    f"hit_points.current ({hp['current']}) must equal hit_points.max ({hp['max']})"
                )

    # HD notation
    hd = sheet.get('hd', '')
    if isinstance(hd, str) and not HD_RE.match(hd):
        errors.append(f"Invalid HD notation: '{hd}' (expected e.g. '2d8+3')")

    # Alignment
    alignment = sheet.get('alignment', '')
    if alignment not in VALID_ALIGNMENTS:
        errors.append(f"Invalid alignment: '{alignment}' (must be lawful/neutral/chaotic)")

    # Description armor vector
    desc = sheet.get('description', '')
    if not ARMOR_VECTOR_RE.search(desc):
        errors.append("description missing armor vector pattern (e.g. 'AC: P10/S10/B10')")

    # Attack group 1: all four keys must be present
    prefix = 'repeating_attacks_-npc_attack_1'
    for suffix in ATTACK_SUFFIXES:
        key = prefix + suffix
        if key not in sheet:
            errors.append(f"Missing attack key: {key}")

    # All _attack values must be strings
    for key, value in sheet.items():
        if key.endswith('_attack') and 'repeating_attacks' in key:
            if not isinstance(value, str):
                errors.append(
                    f"Attack bonus '{key}' must be a string (e.g. '+0'), got {type(value).__name__}"
                )

    return errors
```

- [ ] **Step 4: Run Pass 1 tests**

```
python -m pytest tests/test_qa_checker.py::TestPass1Check -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/qa_checker.py tests/test_qa_checker.py
git commit -m "feat: add qa_checker Pass 1 mechanical validation with 10 passing tests"
```

---

### Task 10: qa_checker.py — Pass 2 + routing

**Files:**
- Modify: `agents/in-progress/qa_checker.py`
- Modify: `tests/test_qa_checker.py`

- [ ] **Step 1: Write failing Pass 2 and routing tests**

Add to `tests/test_qa_checker.py`:

```python
import shutil
from unittest.mock import MagicMock, patch
from qa_checker import pass2_check, route_sheet, run


def make_mock_client(response_text):
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


class TestPass2Check:
    def test_pass_response_returns_pass(self):
        client = make_mock_client("PASS Stats look appropriate for a small insect.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'PASS'

    def test_flag_response_returns_flag(self):
        client = make_mock_client("FLAG will save of 10 is implausible for a mindless creature.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'FLAG'
        assert 'will save' in reason

    def test_malformed_response_treated_as_flag(self):
        client = make_mock_client("This sheet looks reasonable to me.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'FLAG'
        assert 'malformed' in reason


class TestRouteSheet:
    def test_passing_sheet_goes_to_ready(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=[],
            pass2_result='PASS',
            pass2_reason='',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (ready / 'stirge.json').exists()
        assert not (flagged / 'stirge.json').exists()

    def test_failing_sheet_goes_to_flagged_with_report(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=['Missing field: hd'],
            pass2_result='PASS',
            pass2_reason='',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (flagged / 'stirge.json').exists()
        assert (flagged / 'stirge_qa_report.txt').exists()
        assert not (ready / 'stirge.json').exists()

    def test_pass2_flag_goes_to_flagged_with_report(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=[],
            pass2_result='FLAG',
            pass2_reason='will save too high for an insect',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (flagged / 'stirge.json').exists()
        report = (flagged / 'stirge_qa_report.txt').read_text()
        assert 'will save' in report
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_qa_checker.py::TestPass2Check tests/test_qa_checker.py::TestRouteSheet -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement pass2_check(), route_sheet(), and run() — add to qa_checker.py**

```python
def pass2_check(sheet, client=None):
    """Run Claude judgment review. Returns (result, reason) where result is 'PASS' or 'FLAG'."""
    if client is None:
        client = anthropic.Anthropic()

    prompt = f"""You are reviewing a DCC RPG monster sheet for a Roll20 campaign.
Check whether the stats are plausible for this type of creature.
Flag anything implausible: saves too high/low for creature type, HD mismatched with apparent power, etc.

Sheet:
{json.dumps(sheet, indent=2)}

Respond with PASS or FLAG as the first word of your first line.
If PASS: brief notes (or just PASS with nothing else).
If FLAG: explain the specific concern after FLAG on the same line."""

    message = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=512,
        messages=[{'role': 'user', 'content': prompt}]
    )
    response = message.content[0].text.strip()
    first_word = response.split()[0].upper() if response.split() else ''

    if first_word == 'PASS':
        return 'PASS', response[4:].strip()
    elif first_word == 'FLAG':
        return 'FLAG', response[4:].strip()
    else:
        return 'FLAG', 'malformed QA response'


def route_sheet(sheet_path, pass1_errors, pass2_result, pass2_reason,
                ready_dir=READY_DIR, flagged_dir=FLAGGED_DIR):
    """Move a sheet file to ready/ or flagged/ based on QA results.

    Writes a _qa_report.txt alongside any flagged sheet.
    """
    sheet_path = Path(sheet_path)
    stem = sheet_path.stem
    passed = not pass1_errors and pass2_result == 'PASS'

    if passed:
        Path(ready_dir).mkdir(parents=True, exist_ok=True)
        shutil.move(str(sheet_path), str(Path(ready_dir) / sheet_path.name))
    else:
        Path(flagged_dir).mkdir(parents=True, exist_ok=True)
        shutil.move(str(sheet_path), str(Path(flagged_dir) / sheet_path.name))
        report_lines = []
        if pass1_errors:
            report_lines.append("Pass 1 errors:")
            for e in pass1_errors:
                report_lines.append(f"  - {e}")
        if pass2_result == 'FLAG':
            report_lines.append(f"Pass 2 flag: {pass2_reason}")
        report_path = Path(flagged_dir) / f"{stem}_qa_report.txt"
        report_path.write_text('\n'.join(report_lines), encoding='utf-8')


def run(
    pending_dir=PENDING_DIR,
    ready_dir=READY_DIR,
    flagged_dir=FLAGGED_DIR,
    client=None
):
    """Run QA on all .json files in pending_dir."""
    if client is None:
        client = anthropic.Anthropic()

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
        sheet = json.loads(json_file.read_text(encoding='utf-8'))
        errors = pass1_check(sheet)
        result, reason = pass2_check(sheet, client=client)
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
            flagged_dir=flagged_dir
        )

    print(f"{passed} passed, {flagged} flagged")


if __name__ == '__main__':
    run()
```

- [ ] **Step 4: Run all qa_checker tests**

```
python -m pytest tests/test_qa_checker.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/qa_checker.py tests/test_qa_checker.py
git commit -m "feat: add qa_checker Pass 2 and file routing with 8 passing tests"
```

---

### Task 11: Wire all modules into run.py + final verification

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Add imports and wire handlers in run.py main()**

Add after `import sys` at the top of `run.py`:

```python
import sys
from pathlib import Path

# Add agents to path so run.py can import them
sys.path.insert(0, str(Path(__file__).parent / 'agents' / 'in-progress'))
```

Replace the `handlers` dict in `main()`:

```python
def main():
    parser = build_parser()
    args = parser.parse_args()

    import parse_statblocks
    import gap_analysis
    import monster_gen
    import qa_checker

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

    handlers = {
        'monster':   handle_monster,
        'room':      lambda a: print(f"[RoomGen] Not yet implemented. Args: {vars(a)}"),
        'encounter': lambda a: print(f"[EncounterGen] Not yet implemented. Args: {vars(a)}"),
        'qa':        lambda a: qa_checker.run(),
        'sheet':     lambda a: print(f"[Sheet:{a.sheet_action}] Not yet implemented. Args: {vars(a)}"),
        'session':   lambda a: print(f"[Session:{a.session_action}] Not yet implemented. Args: {vars(a)}"),
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)
```

- [ ] **Step 2: Run the full test suite**

```
python -m pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 3: Smoke test the CLI (no API calls)**

```bash
python run.py monster --parse
# Expected: "Wrote 0 monsters to data/input/master_monsters.csv" (or similar, no error)

python run.py monster --gap-analysis
# Expected: prints gap count or "No gaps found"

python run.py qa
# Expected: "No files to validate in pending/" or similar

python run.py monster --generate --name "Nonexistent"
# Expected: "Error: Monster 'Nonexistent' not found..." + non-zero exit
```

- [ ] **Step 4: Update PROGRESS.md**

In `PROGRESS.md`, add under Completed:
```
- 2026-04-04 — Plan 02 complete: parse_statblocks, gap_analysis, monster_gen, qa_checker
```

Update Current Sprint:
```
- Active task: None — Plan 02 complete
- Next session goal: Plan 03 — SheetAuditor + SheetPatcher
```

- [ ] **Step 5: Commit**

```bash
git add run.py PROGRESS.md
git commit -m "feat: wire all Plan 02 modules into run.py — MonsterGen + QAChecker complete"
```

---

## End-to-End Workflow (after all tasks complete)

```bash
# 1. Drop source material into input directory
cp /path/to/statblocks.txt data/input/monster-source/dcc_statblocks.txt
cp /path/to/lore.txt data/input/monster-source/lore_5e_sections.txt

# 2. Parse stat blocks → CSV (review CSV before continuing)
python run.py monster --parse

# 3. Identify gaps → gap report (review report before generating)
python run.py monster --gap-analysis

# 4. Generate one or all missing monsters
python run.py monster --generate --name "Cave Fisher"
python run.py monster --generate --all

# 5. Validate all pending sheets
python run.py qa

# 6. Review ready/ and flagged/ — fix flagged sheets manually, then move to ready/
```

## Environment Setup Reminder

```bash
conda activate thracia-agents
export ANTHROPIC_API_KEY=<your-key>   # Required for Tasks 7, 10 and end-to-end use
```
