# tests/test_sheet_auditor.py
import json
import pytest
from pathlib import Path
from sheet_auditor import load_characters, is_npc


def make_char(name='Gnoll', is_npc_val='1', archived=False, extra_fields=None):
    """Helper: build a minimal character dict."""
    fields = {'is_npc': is_npc_val}
    if extra_fields:
        fields.update(extra_fields)
    return {'name': name, 'archived': archived, 'fields': fields}


class TestIsNpc:
    def test_string_one_is_npc(self):
        assert is_npc(make_char(is_npc_val='1')) is True

    def test_bool_true_is_npc(self):
        assert is_npc(make_char(is_npc_val=True)) is True

    def test_archived_npc_excluded(self):
        assert is_npc(make_char(archived=True)) is False

    def test_pc_excluded(self):
        assert is_npc(make_char(is_npc_val='0')) is False

    def test_no_is_npc_field_excluded(self):
        char = {'name': 'PC', 'archived': False, 'fields': {}}
        assert is_npc(char) is False


class TestLoadCharacters:
    def test_loads_list(self, tmp_path):
        data = [make_char('A'), make_char('B')]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        result = load_characters(str(f))
        assert len(result) == 2
        assert result[0]['name'] == 'A'
