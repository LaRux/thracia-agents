# agents/in-progress/parse_statblocks.py
#
# Stage 1: Parse DCC and 5e stat block text into master_monsters.csv.
#
# Usage: python run.py monster --parse
# Input:  data/input/monster-source/dcc_statblocks.txt
#         data/input/monster-source/lore_5e_sections.txt
# Output: data/input/master_monsters.csv

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
    crit = get(r'Crit\s+([^\s;]+)')  # [^\s;]+ avoids capturing trailing semicolon
    ac = get(r'AC\s+(\d+)')
    hd = get(r'HD\s+(\d+d\d+(?:[+-]\d+)?)')
    hp_avg = get(r'HD\s+\S+\s*\(hp\s+(\d+)')
    mv_text = get(r'MV\s+(.*?)\s*;')
    speed, fly = _parse_movement(mv_text)
    act = get(r'Act\s+([^\s;]+)')  # [^\s;]+ avoids capturing trailing semicolon
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
