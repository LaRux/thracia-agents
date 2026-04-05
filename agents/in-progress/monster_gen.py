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


def load_csv_by_name(name, csv_path=CSV_PATH):
    """Load a single monster row from master_monsters.csv by name.

    Args:
        name: monster name to look up (case-insensitive)
        csv_path: path to the CSV file

    Returns:
        dict: row matching the name, or None if not found
    """
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'].lower() == name.lower():
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
