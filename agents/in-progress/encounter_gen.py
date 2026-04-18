# agents/in-progress/encounter_gen.py
#
# Stage: Generate a Roll20 API script from a staged wandering monster table.
# Calls Claude to parse the raw table text, then writes a .js file that
# creates the rollable table and GM-whisper macro in Roll20.
#
# Usage: python run.py encounter --level 1

import json
import re
from pathlib import Path

import anthropic

_ROOT = Path(__file__).resolve().parent.parent.parent  # agents/in-progress → project root
PROMPT_PATH = _ROOT / 'prompts' / 'encounter_gen.txt'
READY_DIR = _ROOT / 'data' / 'output' / 'ready'


def parse_claude_response(response_text):
    """Parse Claude JSON array response, stripping markdown fences if present."""
    text = response_text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text.strip())
    return json.loads(text)


def validate_entries(entries):
    """Validate list of table entry dicts. Returns list of error strings."""
    errors = []
    for i, e in enumerate(entries):
        if 'name' not in e:
            errors.append(f"Entry {i}: missing 'name'")
        if 'weight' not in e:
            errors.append(f"Entry {i}: missing 'weight'")
        elif not isinstance(e['weight'], int):
            errors.append(f"Entry {i}: 'weight' must be int, got {type(e['weight']).__name__}")
    return errors


def build_js(section_key, entries):
    """Build Roll20 API script string from parsed table entries.

    The script uses on('ready') so it executes once when pasted into the
    API sandbox. Creates a GM-only rollable table and a macro whisper button.
    """
    table_name = f'wandering-{section_key.replace("_", "-")}'
    macro_name = f'Wandering-{section_key.replace("_", "-").title()}'
    display_name = section_key.replace('_', ' ').title()
    action = (
        f"/w gm &{{template:default}} {{{{name={display_name} Wandering Monster}}}}"
        f" {{{{result=[[1t[{table_name}]]]}}}}"
    )

    entry_lines = '\n'.join(
        f"    createObj('tableitem', {{rollabletableid: table.id, "
        f"name: {json.dumps(e['name'])}, weight: {e['weight']}}});"
        for e in entries
    )

    return (
        f"// Wandering Monster Table — {display_name}\n"
        f"// Paste into Roll20 API sandbox and run once.\n\n"
        f"on('ready', function() {{\n"
        f"    var table = createObj('rollabletable', {{\n"
        f"        name: '{table_name}',\n"
        f"        showplayers: false\n"
        f"    }});\n\n"
        f"{entry_lines}\n\n"
        f"    createObj('macro', {{\n"
        f"        name: '{macro_name}',\n"
        f"        action: '{action}',\n"
        f"        visibleto: ''\n"
        f"    }});\n\n"
        f"    log('{table_name} table and macro created.');\n"
        f"}});\n"
    )


def parse_wandering_table(staged_path, client=None):
    """Call Claude to parse staged wandering table text. Returns list of entry dicts."""
    if client is None:
        client = anthropic.Anthropic()

    raw_text = Path(staged_path).read_text(encoding='utf-8')
    prompt_template = Path(PROMPT_PATH).read_text(encoding='utf-8')
    prompt = prompt_template + '\n\n' + raw_text

    message = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2048,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return parse_claude_response(message.content[0].text)


def run(section_key, staged_path):
    """Parse wandering table and write .js script to data/output/ready/."""
    entries = parse_wandering_table(staged_path)
    errors = validate_entries(entries)
    if errors:
        raise ValueError(f"[EncounterGen] Validation errors: {errors}")

    js_content = build_js(section_key, entries)
    Path(READY_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(READY_DIR) / f'wandering_{section_key}.js'
    out_path.write_text(js_content, encoding='utf-8')
    print(f"EncounterGen: {len(entries)} entries → {out_path}")
