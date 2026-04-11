# SheetAuditor + SheetPatcher — Design Spec
**Date:** 2026-04-11
**Plan:** 03
**Phase:** Phase 1 — Content Generation

---

## Overview

Two agents that form a sequential pipeline: SheetAuditor reads the Roll20 character export, identifies quality issues across all active NPC sheets, and produces both a human-readable report and a machine-readable audit JSON. After human review, SheetPatcher reads the audit JSON and generates full replacement sheets for any NPC with patchable issues.

---

## Pipeline

```
data/input/thracia-exports/thracia-characters.json
        ↓
  SheetAuditor
        ↓
data/output/audit_report.md     (human review)
data/output/audit_report.json   (machine input)
        ↓
  [human reviews audit_report.md]
        ↓
  SheetPatcher
        ↓
data/output/pending/<name>.json  (one per NPC with patchable issues)
        ↓
  QAChecker → data/output/ready/ or data/output/flagged/
```

---

## CLI

```bash
python run.py sheet --audit            # SheetAuditor only
python run.py sheet --patch            # SheetPatcher only (requires audit_report.json)
python run.py sheet --audit --patch    # Both in sequence
```

---

## SheetAuditor

### Input
- `data/input/thracia-exports/thracia-characters.json`

### NPC Filter
Include a character if:
- `fields.is_npc == "1"` (string or boolean `true`)
- `archived == false`

### Quality Checks

| Check | Condition | Patchable |
|---|---|---|
| Required fields present | Any of `hd`, `ac`, `fort`, `ref`, `will`, `init`, `alignment`, `sp`, `description`, `hit_points` absent | Partial (see below) |
| `hit_points` valid | `hit_points` is `0`, not an object, or `current`/`max` is 0 | Yes — recompute from `hd` |
| `hit_points` consistent | `hit_points.max` differs from `hd` average by >20% | Yes — recompute from `hd` |
| Numeric fields parseable | `ac`, `fort`, `ref`, `will`, `init` cannot be cast to int | No — manual review |
| At least one attack | No `repeating_attacks_*_name` entries present | No — manual review |
| Alignment valid | Not one of "lawful", "neutral", "chaotic" | No — manual review |
| `act` present and non-empty | `act` is absent or blank | Yes — default to `"1d20"` |

**Notes:**
- `act` accepts any non-empty value — dice patterns and special text alike are valid. Only absent/blank is flagged.
- Patchable missing fields: `sp` → `""`, `description` → `""`, `alignment` → `"neutral"`, `act` → `"1d20"`.
- Non-patchable missing fields: `hd`, `ac` — cannot derive these from other export data. Flag for manual review.

### Output — audit_report.md

```markdown
# Sheet Audit Report — YYYY-MM-DD

## Summary
- NPCs audited: N
- Clean sheets: N
- Patchable issues: N
- Manual review needed: N

## Patchable
| NPC | Issues |
|---|---|
| Acolyte of Thanatos | hit_points: 0 → recomputed from hd (4) |

## Manual Review Needed
| NPC | Issues |
|---|---|
| Some Monster | missing ac; missing attacks |

## Clean
(listed by name)
```

### Output — audit_report.json

```json
[
  {
    "name": "Acolyte of Thanatos",
    "patchable": true,
    "issues": ["hit_points: 0 — recomputed from hd"],
    "full_sheet": {
      "is_npc": 1,
      "name": "Acolyte of Thanatos",
      "hd": "1d8",
      "hit_points": {"current": 4, "max": 4},
      "ac": 13,
      ...
    }
  },
  {
    "name": "Some Monster",
    "patchable": false,
    "issues": ["missing ac", "missing attacks"],
    "full_sheet": null
  }
]
```

Only patchable NPCs get a `full_sheet`. Non-patchable entries have `full_sheet: null`.

`full_sheet` is assembled by SheetAuditor: take all NPC fields from the export, apply corrected/default values for any flagged fields, and output the result as a complete Roll20-ready sheet. Attack fields and all other non-flagged fields are carried over from the export unchanged.

---

## SheetPatcher

### Input
- `data/output/audit_report.json`

### Behavior
- Reads audit JSON
- For each record where `patchable: true`, writes `full_sheet` to `data/output/pending/<sanitized_name>.json`
- Skips records where `patchable: false` (already flagged in the report)
- Prints a summary of files written

### Output
- `data/output/pending/<name>.json` — one per patchable NPC
- These feed directly into the existing QAChecker pipeline

---

## Shared Utilities

`average_from_hd` currently lives in `monster_gen.py`. Both SheetPatcher and MonsterGen need it. As part of Plan 03, move it to `agents/in-progress/utils.py` and update both agents to import from there.

---

## Testing

### test_sheet_auditor.py
- NPC filter: is_npc + archived logic
- Each individual quality check (one test per check)
- Patchable vs non-patchable classification
- Report generation (md and json structure)

### test_sheet_patcher.py
- Full sheet assembly from export fields
- `hit_points` recompute from `hd`
- Default value filling (sp, description, alignment, act)
- File output to pending/

### test_utils.py
- `average_from_hd` tests (moved from test_monster_gen.py)

---

## File Changes

| File | Action |
|---|---|
| `agents/in-progress/sheet_auditor.py` | New |
| `agents/in-progress/sheet_patcher.py` | New |
| `agents/in-progress/utils.py` | New — shared utilities |
| `agents/in-progress/monster_gen.py` | Update import to use utils.py |
| `tests/test_sheet_auditor.py` | New |
| `tests/test_sheet_patcher.py` | New |
| `tests/test_utils.py` | New |
| `tests/test_monster_gen.py` | Update import for average_from_hd |
| `run.py` | Add `sheet` command handler |
| `data/output/audit_report.md` | Generated (gitignored) |
| `data/output/audit_report.json` | Generated (gitignored) |
