# agents/in-progress/sheet_auditor.py
#
# Plan 03: Audit all non-archived NPC sheets in the Roll20 export.
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
