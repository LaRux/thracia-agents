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
