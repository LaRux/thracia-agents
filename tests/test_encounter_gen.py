# tests/test_encounter_gen.py
import json
import pytest

from encounter_gen import validate_entries, build_js, parse_claude_response

SAMPLE_ENTRIES = [
    {"name": "Gnoll (1d3)", "weight": 2, "notes": "negotiate on morale failure"},
    {"name": "Lizardman mercenary (1d2)", "weight": 1, "notes": ""},
    {"name": "Giant Bat (1d6)", "weight": 1, "notes": ""},
]


class TestValidateEntries:
    def test_valid_entries_pass(self):
        assert validate_entries(SAMPLE_ENTRIES) == []

    def test_missing_name_fails(self):
        entries = [{"weight": 2, "notes": ""}]
        errors = validate_entries(entries)
        assert any("name" in e for e in errors)

    def test_missing_weight_fails(self):
        entries = [{"name": "Gnoll (1d3)", "notes": ""}]
        errors = validate_entries(entries)
        assert any("weight" in e for e in errors)

    def test_string_weight_fails(self):
        entries = [{"name": "Gnoll (1d3)", "weight": "2", "notes": ""}]
        errors = validate_entries(entries)
        assert any("weight" in e for e in errors)

    def test_empty_list_passes(self):
        assert validate_entries([]) == []


class TestBuildJs:
    def test_contains_createobj_rollabletable(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "createObj('rollabletable'" in js

    def test_tableitem_count_matches_entries(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert js.count("createObj('tableitem'") == len(SAMPLE_ENTRIES)

    def test_contains_gm_whisper_macro(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "/w gm" in js

    def test_table_name_uses_section_key(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "wandering-level-1" in js

    def test_macro_name_uses_section_key(self):
        js = build_js("level_1", SAMPLE_ENTRIES)
        assert "Wandering-Level-1" in js


class TestParseClaudeResponse:
    def test_bare_json_array_parses(self):
        raw = json.dumps(SAMPLE_ENTRIES)
        result = parse_claude_response(raw)
        assert len(result) == 3
        assert result[0]["name"] == "Gnoll (1d3)"

    def test_markdown_fenced_json_parses(self):
        raw = "```json\n" + json.dumps(SAMPLE_ENTRIES) + "\n```"
        result = parse_claude_response(raw)
        assert result[0]["weight"] == 2
