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
