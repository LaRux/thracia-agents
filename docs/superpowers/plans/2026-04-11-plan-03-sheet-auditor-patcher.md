# SheetAuditor + SheetPatcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit all non-archived NPC sheets in the Roll20 export for quality issues, produce human-readable and machine-readable reports, and generate full replacement sheets for auto-fixable NPCs.

**Architecture:** SheetAuditor reads `thracia-characters.json`, filters NPCs, runs quality checks, and writes `audit_report.md` + `audit_report.json`. After human review, SheetPatcher reads the JSON and writes full replacement sheets to `pending/` for QAChecker to validate. `average_from_hd` is extracted to a shared `utils.py` used by both SheetPatcher and the existing MonsterGen.

**Tech Stack:** Python 3, pathlib, json, re, datetime. No external dependencies beyond existing project setup.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agents/in-progress/utils.py` | Create | Shared helpers: `average_from_hd` |
| `agents/in-progress/sheet_auditor.py` | Create | NPC filter, quality checks, report generation |
| `agents/in-progress/sheet_patcher.py` | Create | Read audit JSON, write pending replacement sheets |
| `agents/in-progress/monster_gen.py` | Modify | Import `average_from_hd` from utils instead of defining it |
| `tests/test_utils.py` | Create | Tests for `average_from_hd` |
| `tests/test_sheet_auditor.py` | Create | Tests for filter, checks, assembly, report writing |
| `tests/test_sheet_patcher.py` | Create | Tests for patch file output |
| `tests/test_monster_gen.py` | Modify | Remove `average_from_hd` import (now in test_utils.py) |
| `tests/test_cli.py` | Modify | Update sheet command tests: subcommands → flags |
| `run.py` | Modify | Update sheet parser to flags; wire `handle_sheet` |

---

## Task 1: Create utils.py and test_utils.py

**Files:**
- Create: `agents/in-progress/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_utils.py
import pytest
from utils import average_from_hd

class TestAverageFromHd:
    def test_basic_dice(self):
        assert average_from_hd('10d12') == 65  # 10*(12+1)//2 = 65

    def test_dice_with_bonus(self):
        assert average_from_hd('1d5+1') == 4   # 1*(5+1)//2 + 1 = 3+1 = 4

    def test_small_die(self):
        assert average_from_hd('2d8') == 9     # 2*(8+1)//2 = 9

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            average_from_hd('invalid')
```

- [ ] **Step 2: Run test — verify FAIL**

```
python -m pytest tests/test_utils.py -v
```
Expected: `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Implement utils.py**

```python
# agents/in-progress/utils.py
import re


def average_from_hd(hd):
    """Compute average HP from a dice string like '10d12' or '2d8+4'."""
    match = re.match(r'(\d+)d(\d+)(?:\+(\d+))?', str(hd).strip())
    if not match:
        raise ValueError(f"Cannot parse HD string: {hd!r}")
    num, sides, bonus = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    return (num * (sides + 1) // 2) + bonus
```

- [ ] **Step 4: Run test — verify PASS**

```
python -m pytest tests/test_utils.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/utils.py tests/test_utils.py
git commit -m "feat: add utils.py with average_from_hd shared helper"
```

---

## Task 2: Update monster_gen.py to import from utils

**Files:**
- Modify: `agents/in-progress/monster_gen.py`
- Modify: `tests/test_monster_gen.py`

- [ ] **Step 1: Remove `average_from_hd` from monster_gen.py**

In `agents/in-progress/monster_gen.py`, delete the entire `average_from_hd` function (lines that read):

```python
def average_from_hd(hd):
    """Compute average HP from a dice string like '10d12' or '2d8+4'."""
    match = re.match(r'(\d+)d(\d+)(?:\+(\d+))?', str(hd).strip())
    if not match:
        raise ValueError(f"Cannot parse HD string: {hd!r}")
    num, sides, bonus = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    return (num * (sides + 1) // 2) + bonus
```

Add this import at the top of `monster_gen.py` (after the existing imports):

```python
from utils import average_from_hd
```

- [ ] **Step 2: Update test_monster_gen.py import**

In `tests/test_monster_gen.py`, change the import line from:

```python
from monster_gen import (
    strip_sign, alignment_to_words, sanitize_filename,
    build_description, build_hit_points, average_from_hd
)
```

To:

```python
from monster_gen import (
    strip_sign, alignment_to_words, sanitize_filename,
    build_description, build_hit_points
)
```

The `average_from_hd` tests are now in `test_utils.py` — no need to import here.

Also remove the `TestAverageFromHd` class from `test_monster_gen.py` entirely (it was:)
```python
class TestAverageFromHd:
    def test_basic_dice(self):
        assert average_from_hd('10d12') == 65
    def test_dice_with_bonus(self):
        assert average_from_hd('1d5+1') == 4
    def test_small_die(self):
        assert average_from_hd('2d8') == 9
```

- [ ] **Step 3: Run all tests — verify PASS**

```
python -m pytest tests/ -v
```
Expected: all tests pass (average_from_hd tests now in test_utils.py, monster_gen still works via import)

- [ ] **Step 4: Commit**

```bash
git add agents/in-progress/monster_gen.py tests/test_monster_gen.py
git commit -m "refactor: move average_from_hd to shared utils.py"
```

---

## Task 3: Update sheet CLI from subcommands to flags

**Files:**
- Modify: `run.py`
- Modify: `tests/test_cli.py`

The existing parser uses `sheet audit` / `sheet patch` subcommands. The spec requires `sheet --audit` / `sheet --patch` flags so both can be combined as `sheet --audit --patch`.

- [ ] **Step 1: Update test_cli.py — replace TestSheetCommand**

In `tests/test_cli.py`, replace the entire `TestSheetCommand` class:

```python
class TestSheetCommand:
    def test_sheet_audit_flag(self):
        args = parse_args(['sheet', '--audit'])
        assert args.command == 'sheet'
        assert args.audit is True

    def test_sheet_patch_flag(self):
        args = parse_args(['sheet', '--patch'])
        assert args.command == 'sheet'
        assert args.patch is True

    def test_sheet_audit_and_patch_together(self):
        args = parse_args(['sheet', '--audit', '--patch'])
        assert args.audit is True
        assert args.patch is True
```

- [ ] **Step 2: Run test — verify FAIL**

```
python -m pytest tests/test_cli.py::TestSheetCommand -v
```
Expected: FAIL — `sheet --audit` is not a valid argument under the current subparser setup.

- [ ] **Step 3: Update run.py sheet parser and handler**

In `run.py`, replace the sheet parser block:

```python
    # -------------------------------------------------------------------------
    # sheet command — has sub-actions: audit and patch
    # -------------------------------------------------------------------------
    sheet_parser = subparsers.add_parser(
        'sheet',
        help='Audit or patch the Roll20 DCC character sheet'
    )
    sheet_subparsers = sheet_parser.add_subparsers(dest='sheet_action')
    sheet_subparsers.required = True
    sheet_subparsers.add_parser('audit', help='Generate gap report between sheet and homebrew rules')
    sheet_subparsers.add_parser('patch', help='Generate annotated patch proposals for the sheet')
```

With:

```python
    # -------------------------------------------------------------------------
    # sheet command — flags: --audit and/or --patch (combinable)
    # -------------------------------------------------------------------------
    sheet_parser = subparsers.add_parser(
        'sheet',
        help='Audit or patch existing Roll20 NPC sheets'
    )
    sheet_parser.add_argument(
        '--audit', action='store_true',
        help='Audit all NPC sheets in the Roll20 export → audit_report.md + audit_report.json'
    )
    sheet_parser.add_argument(
        '--patch', action='store_true',
        help='Write replacement sheets for patchable NPCs → data/output/pending/ (requires prior --audit)'
    )
```

Also update the sheet handler in `handlers` inside `main()` — replace:

```python
        'sheet':     lambda a: print(f"[Sheet:{a.sheet_action}] Not yet implemented. Args: {vars(a)}"),
```

With:

```python
        'sheet':     lambda a: print(f"[Sheet] Not yet implemented. Args: {vars(a)}"),
```

This prevents an AttributeError: after the parser change, `a.sheet_action` no longer exists. The full handler is wired in Task 8.

- [ ] **Step 4: Run all CLI tests — verify PASS**

```
python -m pytest tests/test_cli.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_cli.py
git commit -m "feat: update sheet CLI to --audit/--patch flags (combinable)"
```

---

## Task 4: SheetAuditor — NPC filter and character loading

**Files:**
- Create: `agents/in-progress/sheet_auditor.py`
- Create: `tests/test_sheet_auditor.py`

- [ ] **Step 1: Write failing tests for filter logic**

```python
# tests/test_sheet_auditor.py
import json
import pytest
from pathlib import Path
from sheet_auditor import load_characters, is_npc


def make_char(name='Gnoll', is_npc_val='1', archived=False, extra_fields=None):
    """Helper: build a minimal character dict."""
    fields = {'is_npc': is_npc_val}
    if extra_fields:
        fields.update(extra_fields)
    return {'name': name, 'archived': archived, 'fields': fields}


class TestIsNpc:
    def test_string_one_is_npc(self):
        assert is_npc(make_char(is_npc_val='1')) is True

    def test_bool_true_is_npc(self):
        assert is_npc(make_char(is_npc_val=True)) is True

    def test_archived_npc_excluded(self):
        assert is_npc(make_char(archived=True)) is False

    def test_pc_excluded(self):
        assert is_npc(make_char(is_npc_val='0')) is False

    def test_no_is_npc_field_excluded(self):
        char = {'name': 'PC', 'archived': False, 'fields': {}}
        assert is_npc(char) is False


class TestLoadCharacters:
    def test_loads_list(self, tmp_path):
        data = [make_char('A'), make_char('B')]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        result = load_characters(str(f))
        assert len(result) == 2
        assert result[0]['name'] == 'A'
```

- [ ] **Step 2: Run — verify FAIL**

```
python -m pytest tests/test_sheet_auditor.py -v
```
Expected: `ModuleNotFoundError: No module named 'sheet_auditor'`

- [ ] **Step 3: Implement sheet_auditor.py (filter functions only)**

```python
# agents/in-progress/sheet_auditor.py
#
# Stage 1 of Plan 03: Audit all non-archived NPC sheets in the Roll20 export.
#
# Usage:
#   python run.py sheet --audit

import json
import re
from datetime import date
from pathlib import Path

from utils import average_from_hd

CHARACTERS_PATH = 'data/input/thracia-exports/thracia-characters.json'
AUDIT_REPORT_MD = 'data/output/audit_report.md'
AUDIT_REPORT_JSON = 'data/output/audit_report.json'

VALID_ALIGNMENTS = {'lawful', 'neutral', 'chaotic'}
NON_PATCHABLE_REQUIRED = ['hd', 'ac']
NUMERIC_FIELDS = ['ac', 'fort', 'ref', 'will', 'init']


def load_characters(path=CHARACTERS_PATH):
    """Load all characters from the Roll20 export JSON."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def is_npc(character):
    """Return True if character is a non-archived NPC."""
    if character.get('archived', False):
        return False
    npc_flag = character.get('fields', {}).get('is_npc')
    return npc_flag == '1' or npc_flag is True
```

- [ ] **Step 4: Run — verify PASS**

```
python -m pytest tests/test_sheet_auditor.py::TestIsNpc tests/test_sheet_auditor.py::TestLoadCharacters -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/sheet_auditor.py tests/test_sheet_auditor.py
git commit -m "feat: add sheet_auditor NPC filter and character loading"
```

---

## Task 5: SheetAuditor — quality checks (check_sheet)

**Files:**
- Modify: `agents/in-progress/sheet_auditor.py`
- Modify: `tests/test_sheet_auditor.py`

- [ ] **Step 1: Add a clean NPC fixture and check_sheet tests**

In `tests/test_sheet_auditor.py`, update the import line at the top to add `check_sheet`:

```python
from sheet_auditor import load_characters, is_npc, check_sheet


def make_npc(name='Gnoll', overrides=None, archived=False):
    """Build a fully valid NPC character. Use overrides to introduce specific issues."""
    fields = {
        'is_npc': '1',
        'hd': '2d8',
        'hit_points': {'current': 9, 'max': 9},
        'ac': '14',
        'fort': '2',
        'ref': '1',
        'will': '0',
        'init': '+1',
        'act': '1d20',
        'sp': '',
        'description': 'AC: P14/S14/B12.',
        'alignment': 'neutral',
        'repeating_attacks_-abc_name': 'Bite',
        'repeating_attacks_-abc_bonus': '+2',
        'repeating_attacks_-abc_damage': '1d6',
    }
    if overrides:
        for key, val in overrides.items():
            if val is None:
                fields.pop(key, None)  # None means "remove the field"
            else:
                fields[key] = val
    return {'name': name, 'archived': archived, 'fields': fields}


class TestCheckSheet:
    def test_clean_sheet_no_issues(self):
        issues, patchable, fixes = check_sheet(make_npc())
        assert issues == []
        assert patchable is False  # nothing to patch

    def test_zero_hit_points_is_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'hit_points': 0}))
        assert any('hit_points' in i for i in issues)
        assert patchable is True
        assert fixes['hit_points'] == {'current': 9, 'max': 9}  # 2d8 avg

    def test_dict_hit_points_zero_max_is_patchable(self):
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 0, 'max': 0}})
        )
        assert patchable is True
        assert fixes['hit_points']['max'] == 9

    def test_hit_points_consistency_recomputed(self):
        # hd=2d8 avg=9, max=3 is >20% drift
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 3, 'max': 3}})
        )
        assert any('hit_points' in i for i in issues)
        assert fixes['hit_points']['max'] == 9

    def test_hit_points_within_20pct_is_clean(self):
        # hd=2d8 avg=9, max=8 is <20% drift — acceptable
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 8, 'max': 8}})
        )
        assert not any('hit_points' in i for i in issues)

    def test_missing_hd_is_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'hd': None}))
        assert any('missing hd' in i for i in issues)
        assert patchable is False

    def test_missing_ac_is_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'ac': None}))
        assert any('missing ac' in i for i in issues)
        assert patchable is False

    def test_missing_act_defaults_to_1d20(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'act': ''}))
        assert any('act' in i for i in issues)
        assert fixes.get('act') == '1d20'
        assert patchable is True

    def test_special_act_value_not_flagged(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'act': 'special'}))
        assert not any('act' in i for i in issues)

    def test_missing_alignment_defaults_to_neutral(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'alignment': ''}))
        assert fixes.get('alignment') == 'neutral'
        assert patchable is True

    def test_invalid_alignment_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'alignment': 'evil'}))
        assert any('alignment' in i for i in issues)
        assert patchable is False

    def test_no_attacks_not_patchable(self):
        # Remove all repeating_attacks fields
        npc = make_npc()
        npc['fields'] = {k: v for k, v in npc['fields'].items()
                         if not k.startswith('repeating_attacks')}
        issues, patchable, fixes = check_sheet(npc)
        assert any('attack' in i for i in issues)
        assert patchable is False

    def test_unparseable_numeric_field_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'fort': 'X'}))
        assert any('fort' in i for i in issues)
        assert patchable is False

    def test_mixed_issues_one_non_patchable_means_manual(self):
        # hit_points=0 (patchable) + missing ac (not patchable) → not patchable overall
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': 0, 'ac': None})
        )
        assert patchable is False
```

- [ ] **Step 2: Run — verify FAIL**

```
python -m pytest tests/test_sheet_auditor.py::TestCheckSheet -v
```
Expected: `ImportError: cannot import name 'check_sheet'`

- [ ] **Step 3: Implement check_sheet in sheet_auditor.py**

Add after the `is_npc` function:

```python
def check_sheet(character):
    """
    Run all quality checks on a single NPC character.

    Returns:
        issues (list[str]): human-readable description of each problem found
        patchable (bool): True only if issues exist AND all are auto-fixable
        fixes (dict): field -> corrected value for each patchable issue
    """
    fields = character.get('fields', {})
    issues = []
    all_patchable = True
    fixes = {}

    # Non-patchable required fields: if absent, the sheet cannot be auto-patched
    for field in NON_PATCHABLE_REQUIRED:
        if not fields.get(field):
            issues.append(f"missing {field} — manual review")
            all_patchable = False

    # hit_points check
    hp = fields.get('hit_points')
    hd = fields.get('hd', '')
    hp_valid = isinstance(hp, dict) and hp.get('max', 0) > 0
    if not hp_valid:
        if hd:
            try:
                avg = average_from_hd(hd)
                issues.append(f"hit_points invalid — recomputed from hd ({avg})")
                fixes['hit_points'] = {'current': avg, 'max': avg}
            except ValueError:
                issues.append("hit_points invalid and hd unparseable — manual review")
                all_patchable = False
        else:
            issues.append("hit_points invalid and hd missing — manual review")
            all_patchable = False
    elif hd:
        # Consistency check: max vs hd average (>20% drift → recompute)
        try:
            avg = average_from_hd(hd)
            max_hp = hp.get('max', 0)
            if avg > 0 and abs(max_hp - avg) / avg > 0.20:
                issues.append(
                    f"hit_points.max ({max_hp}) differs >20% from hd average ({avg}) — recomputed"
                )
                fixes['hit_points'] = {'current': avg, 'max': avg}
        except ValueError:
            pass  # hd unparseable — skip consistency check

    # act: only flag if absent or blank (any non-empty value is valid)
    if not str(fields.get('act', '')).strip():
        issues.append("missing act — defaulting to '1d20'")
        fixes['act'] = '1d20'

    # alignment: missing → patchable default; present but invalid → manual
    alignment = str(fields.get('alignment', '')).strip().lower()
    if not alignment:
        issues.append("missing alignment — defaulting to 'neutral'")
        fixes['alignment'] = 'neutral'
    elif alignment not in VALID_ALIGNMENTS:
        issues.append(f"alignment {alignment!r} not valid — manual review")
        all_patchable = False

    # Numeric fields: unparseable → manual (can't derive correct value)
    for field in NUMERIC_FIELDS:
        val = fields.get(field, '')
        if val != '' and val is not None:
            try:
                int(str(val).strip().lstrip('+'))
            except (ValueError, TypeError):
                issues.append(f"{field} not parseable as int ({val!r}) — manual review")
                all_patchable = False

    # At least one attack entry required
    has_attack = any(
        fields[k] for k in fields
        if re.match(r'repeating_attacks_.+_name', k)
    )
    if not has_attack:
        issues.append("no attack entries — manual review")
        all_patchable = False

    patchable = bool(issues) and all_patchable
    return issues, patchable, fixes
```

- [ ] **Step 4: Run — verify PASS**

```
python -m pytest tests/test_sheet_auditor.py::TestCheckSheet -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/sheet_auditor.py tests/test_sheet_auditor.py
git commit -m "feat: add check_sheet with full quality check suite"
```

---

## Task 6: SheetAuditor — full_sheet assembly and audit_characters

**Files:**
- Modify: `agents/in-progress/sheet_auditor.py`
- Modify: `tests/test_sheet_auditor.py`

- [ ] **Step 1: Add tests**

In `tests/test_sheet_auditor.py`, update the import line at the top to add `assemble_full_sheet, audit_characters`:

```python
from sheet_auditor import load_characters, is_npc, check_sheet, assemble_full_sheet, audit_characters


class TestAssembleFullSheet:
    def test_carries_over_all_existing_fields(self):
        npc = make_npc()
        sheet = assemble_full_sheet(npc, {})
        assert sheet['hd'] == '2d8'
        assert sheet['name'] == 'Gnoll'
        assert sheet['is_npc'] == '1'

    def test_fixes_override_existing_fields(self):
        npc = make_npc(overrides={'hit_points': 0})
        fixes = {'hit_points': {'current': 9, 'max': 9}}
        sheet = assemble_full_sheet(npc, fixes)
        assert sheet['hit_points'] == {'current': 9, 'max': 9}

    def test_attack_fields_carried_over(self):
        npc = make_npc()
        sheet = assemble_full_sheet(npc, {})
        assert sheet['repeating_attacks_-abc_name'] == 'Bite'


class TestAuditCharacters:
    def test_filters_out_pcs(self, tmp_path):
        data = [
            make_char('PC', is_npc_val='0'),
            make_npc('Gnoll'),
        ]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert len(records) == 1
        assert records[0]['name'] == 'Gnoll'

    def test_clean_npc_has_empty_issues(self, tmp_path):
        data = [make_npc('Gnoll')]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['issues'] == []
        assert records[0]['patchable'] is False
        assert records[0]['full_sheet'] is None

    def test_patchable_npc_has_full_sheet(self, tmp_path):
        data = [make_npc('Gnoll', overrides={'hit_points': 0})]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['patchable'] is True
        assert records[0]['full_sheet'] is not None
        assert records[0]['full_sheet']['hit_points']['max'] == 9

    def test_non_patchable_npc_has_no_full_sheet(self, tmp_path):
        data = [make_npc('Boss', overrides={'ac': None})]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['patchable'] is False
        assert records[0]['full_sheet'] is None
```

- [ ] **Step 2: Run — verify FAIL**

```
python -m pytest tests/test_sheet_auditor.py::TestAssembleFullSheet tests/test_sheet_auditor.py::TestAuditCharacters -v
```
Expected: `ImportError: cannot import name 'assemble_full_sheet'`

- [ ] **Step 3: Implement assemble_full_sheet and audit_characters**

Add after `check_sheet` in `sheet_auditor.py`:

```python
def assemble_full_sheet(character, fixes):
    """
    Build a complete Roll20-ready sheet from character fields with fixes applied.
    All existing fields are carried over unchanged except where fixes override them.
    """
    fields = dict(character.get('fields', {}))
    fields.update(fixes)
    return {'name': character['name'], **fields}


def audit_characters(characters_path=CHARACTERS_PATH):
    """
    Run audit on all active NPCs. Returns list of audit records:
        [{'name', 'patchable', 'issues', 'full_sheet'}, ...]
    full_sheet is set only for patchable records; None otherwise.
    """
    characters = load_characters(characters_path)
    records = []
    for character in characters:
        if not is_npc(character):
            continue
        issues, patchable, fixes = check_sheet(character)
        full_sheet = assemble_full_sheet(character, fixes) if patchable else None
        records.append({
            'name': character['name'],
            'patchable': patchable,
            'issues': issues,
            'full_sheet': full_sheet,
        })
    return records
```

- [ ] **Step 4: Run — verify PASS**

```
python -m pytest tests/test_sheet_auditor.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/sheet_auditor.py tests/test_sheet_auditor.py
git commit -m "feat: add assemble_full_sheet and audit_characters"
```

---

## Task 7: SheetAuditor — report generation

**Files:**
- Modify: `agents/in-progress/sheet_auditor.py`
- Modify: `tests/test_sheet_auditor.py`

- [ ] **Step 1: Add report tests**

In `tests/test_sheet_auditor.py`, update the import line at the top to add the report writers:

```python
from sheet_auditor import (
    load_characters, is_npc, check_sheet, assemble_full_sheet,
    audit_characters, write_audit_report_md, write_audit_report_json
)


class TestWriteAuditReportMd:
    def _make_records(self):
        return [
            {'name': 'Clean Gnoll', 'patchable': False, 'issues': [], 'full_sheet': None},
            {'name': 'Broken Gnoll', 'patchable': True,
             'issues': ['hit_points: 0 — recomputed from hd (9)'], 'full_sheet': {'name': 'Broken Gnoll'}},
            {'name': 'Bad Boss', 'patchable': False,
             'issues': ['missing ac — manual review'], 'full_sheet': None},
        ]

    def test_creates_file(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        assert path.exists()

    def test_summary_counts_correct(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        content = path.read_text()
        assert 'NPCs audited: 3' in content
        assert 'Clean sheets: 1' in content
        assert 'Patchable issues: 1' in content
        assert 'Manual review needed: 1' in content

    def test_sections_present(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        content = path.read_text()
        assert '## Patchable' in content
        assert '## Manual Review Needed' in content
        assert '## Clean' in content
        assert 'Broken Gnoll' in content
        assert 'Bad Boss' in content
        assert 'Clean Gnoll' in content


class TestWriteAuditReportJson:
    def test_creates_valid_json(self, tmp_path):
        records = [{'name': 'Gnoll', 'patchable': False, 'issues': [], 'full_sheet': None}]
        path = tmp_path / 'report.json'
        write_audit_report_json(records, path=str(path))
        data = json.loads(path.read_text())
        assert data[0]['name'] == 'Gnoll'

    def test_preserves_all_records(self, tmp_path):
        records = [
            {'name': 'A', 'patchable': True, 'issues': ['x'], 'full_sheet': {'name': 'A'}},
            {'name': 'B', 'patchable': False, 'issues': [], 'full_sheet': None},
        ]
        path = tmp_path / 'report.json'
        write_audit_report_json(records, path=str(path))
        data = json.loads(path.read_text())
        assert len(data) == 2
```

- [ ] **Step 2: Run — verify FAIL**

```
python -m pytest tests/test_sheet_auditor.py::TestWriteAuditReportMd tests/test_sheet_auditor.py::TestWriteAuditReportJson -v
```
Expected: `ImportError: cannot import name 'write_audit_report_md'`

- [ ] **Step 3: Implement report writers**

Add after `audit_characters` in `sheet_auditor.py`:

```python
def write_audit_report_md(records, path=AUDIT_REPORT_MD):
    """Write human-readable audit summary to path."""
    today = date.today().isoformat()
    clean = [r for r in records if not r['issues']]
    patchable = [r for r in records if r['patchable']]
    manual = [r for r in records if r['issues'] and not r['patchable']]

    lines = [
        f"# Sheet Audit Report — {today}",
        "",
        "## Summary",
        f"- NPCs audited: {len(records)}",
        f"- Clean sheets: {len(clean)}",
        f"- Patchable issues: {len(patchable)}",
        f"- Manual review needed: {len(manual)}",
        "",
    ]

    if patchable:
        lines += ["## Patchable", "| NPC | Issues |", "|---|---|"]
        for r in patchable:
            lines.append(f"| {r['name']} | {'; '.join(r['issues'])} |")
        lines.append("")

    if manual:
        lines += ["## Manual Review Needed", "| NPC | Issues |", "|---|---|"]
        for r in manual:
            lines.append(f"| {r['name']} | {'; '.join(r['issues'])} |")
        lines.append("")

    if clean:
        lines += ["## Clean", ""]
        lines += [f"- {r['name']}" for r in clean]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(lines), encoding='utf-8')
    print(f"  Wrote {path}")


def write_audit_report_json(records, path=AUDIT_REPORT_JSON):
    """Write machine-readable audit records to path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f"  Wrote {path}")
```

- [ ] **Step 4: Run — verify PASS**

```
python -m pytest tests/test_sheet_auditor.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/sheet_auditor.py tests/test_sheet_auditor.py
git commit -m "feat: add audit report generation (md + json)"
```

---

## Task 8: SheetAuditor — run() and wire --audit in run.py

**Files:**
- Modify: `agents/in-progress/sheet_auditor.py`
- Modify: `run.py`

- [ ] **Step 1: Add run() to sheet_auditor.py**

Add at the end of `sheet_auditor.py`:

```python
def run(characters_path=CHARACTERS_PATH):
    """Main entry point: audit all NPCs and write both report files."""
    print(f"Reading {characters_path}...")
    records = audit_characters(characters_path)
    write_audit_report_md(records)
    write_audit_report_json(records)
    clean = sum(1 for r in records if not r['issues'])
    patchable = sum(1 for r in records if r['patchable'])
    manual = sum(1 for r in records if r['issues'] and not r['patchable'])
    print(f"  {len(records)} NPCs: {clean} clean, {patchable} patchable, {manual} manual review needed")
```

- [ ] **Step 2: Wire handle_sheet in run.py**

In `run.py`, inside `main()`, add `import sheet_auditor` alongside the other agent imports:

```python
    import parse_statblocks
    import gap_analysis
    import monster_gen
    import qa_checker
    import sheet_auditor
```

Then replace the sheet handler in `handlers`:

```python
        'sheet':     lambda a: print(f"[Sheet:{a.sheet_action}] Not yet implemented. Args: {vars(a)}"),
```

With:

```python
        'sheet':     handle_sheet,
```

And add the `handle_sheet` function alongside `handle_monster`:

```python
    def handle_sheet(a):
        if a.audit:
            sheet_auditor.run()
        if a.patch:
            print("[SheetPatcher] Not yet implemented.")
        if not a.audit and not a.patch:
            print("Specify --audit, --patch, or both. See --help.")
```

- [ ] **Step 3: Smoke test**

```
python run.py sheet --audit
```
Expected: reads the export, prints NPC counts, writes `data/output/audit_report.md` and `data/output/audit_report.json`.

- [ ] **Step 4: Run all tests — verify nothing broken**

```
python -m pytest tests/ -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/in-progress/sheet_auditor.py run.py
git commit -m "feat: wire SheetAuditor into run.py sheet --audit command"
```

---

## Task 9: SheetPatcher and wire --patch

**Files:**
- Create: `agents/in-progress/sheet_patcher.py`
- Create: `tests/test_sheet_patcher.py`
- Modify: `run.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sheet_patcher.py
import json
import pytest
from pathlib import Path
from sheet_patcher import sanitize_filename, run_patch


class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert sanitize_filename('Gnoll Alpha') == 'gnoll_alpha.json'

    def test_lowercase(self):
        assert sanitize_filename('GNOLL') == 'gnoll.json'

    def test_special_chars_removed(self):
        assert sanitize_filename("G'ruk") == 'gruk.json'


class TestRunPatch:
    def _make_audit(self, patchable=True):
        return [
            {
                'name': 'Gnoll',
                'patchable': patchable,
                'issues': ['hit_points: 0 — recomputed from hd (9)'],
                'full_sheet': {'name': 'Gnoll', 'is_npc': '1', 'hd': '2d8'} if patchable else None,
            }
        ]

    def test_writes_patchable_sheet_to_pending(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=True)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        assert (pending / 'gnoll.json').exists()

    def test_written_file_contains_full_sheet(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=True)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        data = json.loads((pending / 'gnoll.json').read_text())
        assert data['name'] == 'Gnoll'
        assert data['hd'] == '2d8'

    def test_skips_non_patchable_records(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=False)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        assert not (pending / 'gnoll.json').exists()

    def test_missing_audit_file_prints_message(self, tmp_path, capsys):
        run_patch(
            audit_path=str(tmp_path / 'nonexistent.json'),
            pending_dir=str(tmp_path / 'pending')
        )
        assert 'No audit report' in capsys.readouterr().out
```

- [ ] **Step 2: Run — verify FAIL**

```
python -m pytest tests/test_sheet_patcher.py -v
```
Expected: `ModuleNotFoundError: No module named 'sheet_patcher'`

- [ ] **Step 3: Implement sheet_patcher.py**

```python
# agents/in-progress/sheet_patcher.py
#
# Stage 2 of Plan 03: Write full replacement sheets for patchable NPCs.
# Reads audit_report.json produced by SheetAuditor.
#
# Usage:
#   python run.py sheet --patch

import json
import re
from pathlib import Path

AUDIT_REPORT_JSON = 'data/output/audit_report.json'
PENDING_DIR = 'data/output/pending'


def sanitize_filename(name):
    """Convert monster name to a safe filename: lowercase, spaces→underscores."""
    safe = re.sub(r'[^\w\s-]', '', name.lower())
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe + '.json'


def run_patch(audit_path=AUDIT_REPORT_JSON, pending_dir=PENDING_DIR):
    """Read audit_report.json and write full replacement sheets to pending/."""
    if not Path(audit_path).exists():
        print(f"No audit report found at {audit_path}. Run 'python run.py sheet --audit' first.")
        return

    records = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    patchable = [r for r in records if r.get('patchable') and r.get('full_sheet')]

    if not patchable:
        print("No patchable NPCs in audit report.")
        return

    Path(pending_dir).mkdir(parents=True, exist_ok=True)
    for record in patchable:
        filename = sanitize_filename(record['name'])
        path = Path(pending_dir) / filename
        path.write_text(json.dumps(record['full_sheet'], indent=2), encoding='utf-8')
        print(f"  Wrote {path}")

    print(f"  {len(patchable)} patch file(s) written to {pending_dir}/")
```

- [ ] **Step 4: Run — verify PASS**

```
python -m pytest tests/test_sheet_patcher.py -v
```
Expected: all pass

- [ ] **Step 5: Wire --patch in run.py**

In `run.py`, add `import sheet_patcher` alongside other agent imports:

```python
    import parse_statblocks
    import gap_analysis
    import monster_gen
    import qa_checker
    import sheet_auditor
    import sheet_patcher
```

Update `handle_sheet`:

```python
    def handle_sheet(a):
        if a.audit:
            sheet_auditor.run()
        if a.patch:
            sheet_patcher.run_patch()
        if not a.audit and not a.patch:
            print("Specify --audit, --patch, or both. See --help.")
```

- [ ] **Step 6: Run all tests — verify PASS**

```
python -m pytest tests/ -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add agents/in-progress/sheet_patcher.py tests/test_sheet_patcher.py run.py
git commit -m "feat: add SheetPatcher and wire sheet --patch command"
```

---

## Task 10: End-to-end smoke test and final commit

- [ ] **Step 1: Run the full audit against the real export**

```
python run.py sheet --audit
```

Expected output (numbers will vary):
```
Reading data/input/thracia-exports/thracia-characters.json...
  Wrote data/output/audit_report.md
  Wrote data/output/audit_report.json
  N NPCs: X clean, Y patchable, Z manual review needed
```

- [ ] **Step 2: Review audit_report.md**

Open `data/output/audit_report.md`. Verify:
- Summary numbers look reasonable (not 0 NPCs audited)
- Patchable and manual review sections list specific NPC names with readable issue descriptions

- [ ] **Step 3: Run patch**

```
python run.py sheet --patch
```

Expected: writes `.json` files to `data/output/pending/` for each patchable NPC.

- [ ] **Step 4: Run QA check on output**

```
python run.py qa
```

Expected: patch files validated and moved to `data/output/ready/` or `data/output/flagged/`.

- [ ] **Step 5: Run all tests one final time**

```
python -m pytest tests/ -v
```
Expected: all pass

- [ ] **Step 6: Update PROGRESS.md**

In `PROGRESS.md`, update Current Sprint to:
```
- **Phase:** Phase 1 — Plan 03 complete
- **Active task:** None
- **Next session goal:** Plan 04 — RoomGen + EncounterGen
```

Add to Completed:
```
- 2026-04-11 — Plan 03 complete: sheet_auditor, sheet_patcher, utils
```

- [ ] **Step 7: Final commit**

```bash
git add PROGRESS.md
git commit -m "chore: mark Plan 03 complete in PROGRESS.md"
```
