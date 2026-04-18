# agents/in-progress/room_gen.py
#
# Stage: Generate Roll20 handout JSONs from staged room text.
# Reads rooms_{section_key}.txt, batches 5 rooms per Claude call,
# writes one handout JSON per room to data/output/pending/.
#
# Usage: python run.py room --level 1

import json
import re
from pathlib import Path

import anthropic

PROMPT_PATH = 'prompts/room_gen.txt'
PENDING_DIR = 'data/output/pending'
BATCH_SIZE = 5
ROOMS_DELIMITER = '---ROOM---'


def sanitize_filename(section_key, room_name):
    """Convert section key + room name to a safe output filename."""
    safe = re.sub(r'[^\w\s-]', '', room_name.lower())
    safe = re.sub(r'\s+', '_', safe.strip())
    return f'room_{section_key}_{safe}.json'


def read_room_blocks(staged_path):
    """Read room blocks from a staged file. Returns list of non-empty block strings."""
    text = Path(staged_path).read_text(encoding='utf-8')
    return [b.strip() for b in text.split(ROOMS_DELIMITER) if b.strip()]


def parse_claude_response(response_text):
    """Parse Claude JSON array response, stripping markdown fences if present."""
    text = response_text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text.strip())
    return json.loads(text)


def validate_handout(handout):
    """Validate handout dict structure. Returns list of error strings (empty = valid)."""
    errors = []
    for field in ('type', 'name', 'notes', 'gmnotes', 'folder'):
        if field not in handout:
            errors.append(f"Missing field: {field}")
    if errors:
        return errors
    if handout.get('type') != 'handout':
        errors.append(f"type must be 'handout', got '{handout.get('type')}'")
    if not isinstance(handout.get('notes'), str) or not handout['notes'].strip():
        errors.append("notes must be a non-empty string")
    if not isinstance(handout.get('gmnotes'), str) or not handout['gmnotes'].strip():
        errors.append("gmnotes must be a non-empty string")
    return errors


def _build_prompt(blocks, prompt_template):
    """Combine prompt template with a batch of room blocks."""
    rooms_text = '\n\n'.join(f'[Room {i + 1}]\n{b}' for i, b in enumerate(blocks))
    return prompt_template + '\n\n' + rooms_text


def generate_handouts(section_key, staged_path, client=None):
    """Call Claude to generate handout dicts for all rooms in staged file.

    Returns:
        list[tuple[str, dict]]: (filename, handout_dict) pairs
    """
    if client is None:
        client = anthropic.Anthropic()

    prompt_template = Path(PROMPT_PATH).read_text(encoding='utf-8')
    blocks = read_room_blocks(staged_path)
    results = []

    for i in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[i:i + BATCH_SIZE]
        prompt = _build_prompt(batch, prompt_template)
        message = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': prompt}]
        )
        handouts = parse_claude_response(message.content[0].text)
        for handout in handouts:
            filename = sanitize_filename(section_key, handout.get('name', f'room_{i}'))
            results.append((filename, handout))

    return results


def run(section_key, staged_path):
    """Write handout JSONs to data/output/pending/."""
    Path(PENDING_DIR).mkdir(parents=True, exist_ok=True)
    results = generate_handouts(section_key, staged_path)
    for filename, handout in results:
        out_path = Path(PENDING_DIR) / filename
        out_path.write_text(json.dumps(handout, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"RoomGen: {len(results)} handouts written to {PENDING_DIR}/")
