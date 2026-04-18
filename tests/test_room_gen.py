# tests/test_room_gen.py
import json
import pytest

from room_gen import (
    sanitize_filename,
    read_room_blocks,
    validate_handout,
    parse_claude_response,
)

VALID_HANDOUT = {
    "type": "handout",
    "name": "Area 1-2 - Hall of the Bats",
    "notes": "<p>The air is thick with bat guano.</p>",
    "gmnotes": "<p><strong>Encounter:</strong> 3d6 bats. DC 8 Reflex or prone.</p>",
    "folder": "Level 1",
}


class TestSanitizeFilename:
    def test_produces_valid_filename(self):
        name = sanitize_filename("level_1", "Area 1-2 - Hall of the Bats")
        assert name.startswith("room_level_1_")
        assert name.endswith(".json")
        assert " " not in name

    def test_special_chars_removed(self):
        name = sanitize_filename("level_1", "Area 1-2: Room (Special)")
        assert "(" not in name
        assert ")" not in name
        assert ":" not in name


class TestReadRoomBlocks:
    def test_reads_blocks_split_by_delimiter(self, tmp_path):
        f = tmp_path / "rooms_level_1.txt"
        f.write_text("Block one content\n---ROOM---\nBlock two content", encoding="utf-8")
        blocks = read_room_blocks(str(f))
        assert len(blocks) == 2
        assert "Block one" in blocks[0]
        assert "Block two" in blocks[1]

    def test_empty_blocks_excluded(self, tmp_path):
        f = tmp_path / "rooms_level_1.txt"
        f.write_text("Block one\n---ROOM---\n   \n---ROOM---\nBlock two", encoding="utf-8")
        blocks = read_room_blocks(str(f))
        assert len(blocks) == 2


class TestValidateHandout:
    def test_valid_handout_passes(self):
        assert validate_handout(VALID_HANDOUT) == []

    def test_missing_type_fails(self):
        h = dict(VALID_HANDOUT)
        del h["type"]
        errors = validate_handout(h)
        assert any("type" in e for e in errors)

    def test_wrong_type_fails(self):
        h = dict(VALID_HANDOUT, type="monster")
        errors = validate_handout(h)
        assert any("type" in e for e in errors)

    def test_missing_notes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["notes"]
        errors = validate_handout(h)
        assert any("notes" in e for e in errors)

    def test_empty_notes_fails(self):
        h = dict(VALID_HANDOUT, notes="")
        errors = validate_handout(h)
        assert any("notes" in e for e in errors)

    def test_missing_gmnotes_fails(self):
        h = dict(VALID_HANDOUT)
        del h["gmnotes"]
        errors = validate_handout(h)
        assert any("gmnotes" in e for e in errors)


class TestParseClaudeResponse:
    def test_bare_json_parses(self):
        raw = json.dumps([VALID_HANDOUT])
        result = parse_claude_response(raw)
        assert isinstance(result, list)
        assert result[0]["name"] == VALID_HANDOUT["name"]

    def test_markdown_fenced_json_parses(self):
        raw = "```json\n" + json.dumps([VALID_HANDOUT]) + "\n```"
        result = parse_claude_response(raw)
        assert result[0]["type"] == "handout"
