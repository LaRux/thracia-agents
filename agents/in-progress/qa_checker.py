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
        errors.append(f"Invalid hd notation: '{hd}' (expected e.g. '2d8+3')")

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
