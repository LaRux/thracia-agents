# tests/test_parse_pdf.py
from pathlib import Path
import pytest

from parse_pdf import split_rooms, ROOMS_DELIMITER


class TestSplitRooms:
    def test_primary_header_splits_two_rooms(self):
        text = (
            "Area 1-1 - Entry Hall\nBats fill the ceiling.\n\n"
            "Area 1-2 - Hall of the Bats\nMore bats here."
        )
        blocks = split_rooms(text)
        assert len(blocks) == 2
        assert "Entry Hall" in blocks[0]
        assert "Hall of the Bats" in blocks[1]

    def test_fallback_header_splits_correctly(self):
        text = (
            "Bat Infested Hallway:\nDescription here.\n\n"
            "Area 1-2 - Normal Room\nAnother room."
        )
        blocks = split_rooms(text)
        assert len(blocks) == 2
        assert "Bat Infested Hallway" in blocks[0]

    def test_single_room_returns_one_block(self):
        text = "Area 1-1 - Entry Hall\nJust one room."
        blocks = split_rooms(text)
        assert len(blocks) == 1

    def test_empty_blocks_are_excluded(self):
        text = "\n\n\nArea 1-1 - Entry Hall\nContent here."
        blocks = split_rooms(text)
        assert all(b.strip() for b in blocks)
        assert len(blocks) == 1

    def test_delimiter_appears_in_joined_output(self):
        text = "Area 1-1 - Entry Hall\nA.\n\nArea 1-2 - Next\nB."
        blocks = split_rooms(text)
        joined = f"\n{ROOMS_DELIMITER}\n".join(blocks)
        assert ROOMS_DELIMITER in joined
        assert joined.count(ROOMS_DELIMITER) == 1


class TestExtractRooms:
    def test_skips_extraction_if_staged_file_exists(self, tmp_path, monkeypatch):
        (tmp_path / "data" / "input").mkdir(parents=True)
        staged = tmp_path / "data" / "input" / "rooms_level_1.txt"
        staged.write_text("existing content")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: (_ for _ in ()).throw(AssertionError("should not call _extract_text")))

        result = parse_pdf.extract_rooms("level_1", (120, 125), reextract=False)
        assert result.read_text() == "existing content"

    def test_reextract_overwrites_existing_file(self, tmp_path, monkeypatch):
        (tmp_path / "data" / "input").mkdir(parents=True)
        staged = tmp_path / "data" / "input" / "rooms_level_1.txt"
        staged.write_text("old content")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: "Area 1-1 - Room\nNew content.")

        result = parse_pdf.extract_rooms("level_1", (120, 125), reextract=True)
        assert "New content" in result.read_text()

    def test_extract_wandering_skips_if_staged_exists(self, tmp_path, monkeypatch):
        (tmp_path / "data" / "input").mkdir(parents=True)
        staged = tmp_path / "data" / "input" / "wandering_level_1.txt"
        staged.write_text("existing table")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: (_ for _ in ()).throw(AssertionError("should not be called")))

        result = parse_pdf.extract_wandering("level_1", (115, 120), reextract=False)
        assert result.read_text() == "existing table"

    def test_reextract_wandering_overwrites_existing_file(self, tmp_path, monkeypatch):
        (tmp_path / "data" / "input").mkdir(parents=True)
        staged = tmp_path / "data" / "input" / "wandering_level_1.txt"
        staged.write_text("old table content")
        monkeypatch.chdir(tmp_path)

        import parse_pdf
        monkeypatch.setattr(parse_pdf, "_extract_text", lambda pages: "New wandering table content.")

        result = parse_pdf.extract_wandering("level_1", (115, 120), reextract=True)
        assert "New wandering" in result.read_text()
