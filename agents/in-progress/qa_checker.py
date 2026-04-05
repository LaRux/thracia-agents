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
