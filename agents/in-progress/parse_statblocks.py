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


# ---------------------------------------------------------------------------
# 5e parsing
# ---------------------------------------------------------------------------

def _5e_alignment_to_dcc(alignment_text):
    """Map 5e alignment string to DCC single character.

    Mapping: lawful* → L, chaotic* → C, everything else (neutral, NE, NG, unaligned) → N.
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
        try:
            num, denom = cr_text.split('/', 1)
            return int(num.strip()) / int(denom.strip())
        except (ValueError, ZeroDivisionError):
            return 0.0
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

    The modifier line has parenthesized values. DEX is the 2nd entry.
    Returns the modifier as a signed string like '+1' or '-2'.
    """
    mod_line_re = re.compile(r'^\s*\([+-]?\d+\)(?:\s+\([+-]?\d+\)){1,}', re.MULTILINE)
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

    Maps: CON → fort, DEX → ref, WIS → will.
    Any save not mentioned defaults to '+0'.
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
    actions_m = re.search(
        r'\bActions\b\s*\n(.*?)(?=\n(?:Reactions|Legendary Actions|Bonus Actions|Lair Actions)\b|\Z)',
        block_text, re.DOTALL | re.IGNORECASE
    )
    attacks_raw = actions_m.group(1).strip() if actions_m else ''

    # Special abilities: named trait paragraphs before the Actions section.
    # We look for text between the last blank line after the stat block metadata
    # and the first recognized section header.
    sp_section_re = re.search(
        r'Challenge.*?\n\n(.*?)(?=\n(?:Actions|Reactions|Legendary Actions|Bonus Actions|Lair Actions)\b|\Z)',
        block_text, re.DOTALL | re.IGNORECASE
    )
    sp_raw = sp_section_re.group(1).strip() if sp_section_re else ''

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
