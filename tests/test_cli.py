# tests/test_cli.py
#
# Tests for run.py's CLI argument parsing.
#
# Why test argument parsing? Because run.py is the entry point for everything —
# if its argument parsing is wrong, every agent breaks. These tests lock in the
# expected command interface so future changes don't silently break it.
#
# WHY TDD HERE?
# We write these tests BEFORE run.py exists. When you run them now, they will
# fail with an ImportError. That's correct — that's what TDD means. The tests
# define what the code should do; then we write the code to make them pass.

import pytest
import sys


def parse_args(args):
    """Import and call the parser from run.py.

    Kept as a separate helper so we can test argument parsing without
    triggering run.py's main() function (which would try to run agents).
    """
    from run import build_parser
    parser = build_parser()
    return parser.parse_args(args)


class TestMonsterCommand:
    def test_monster_with_level(self):
        """'python run.py monster --level 1' should parse correctly."""
        args = parse_args(['monster', '--level', '1'])
        assert args.command == 'monster'
        assert args.level == 1

    def test_monster_with_input_file(self):
        """'python run.py monster --input path/to/file.md' should parse correctly."""
        args = parse_args(['monster', '--input', 'data/input/gnoll.md'])
        assert args.command == 'monster'
        assert args.input == 'data/input/gnoll.md'

    def test_monster_requires_level_or_input(self):
        """'python run.py monster' with no flags should fail with a usage error."""
        with pytest.raises(SystemExit):
            parse_args(['monster'])


class TestRoomCommand:
    def test_room_with_input_file(self):
        args = parse_args(['room', '--input', 'data/input/1-1-entry-hall.md'])
        assert args.command == 'room'
        assert args.input == 'data/input/1-1-entry-hall.md'


class TestEncounterCommand:
    def test_encounter_with_level(self):
        args = parse_args(['encounter', '--level', '1'])
        assert args.command == 'encounter'
        assert args.level == 1


class TestQACommand:
    def test_qa_with_input_dir(self):
        args = parse_args(['qa', '--input', 'data/output/pending/'])
        assert args.command == 'qa'
        assert args.input == 'data/output/pending/'


class TestSheetCommand:
    def test_sheet_audit(self):
        args = parse_args(['sheet', 'audit'])
        assert args.command == 'sheet'
        assert args.sheet_action == 'audit'

    def test_sheet_patch(self):
        args = parse_args(['sheet', 'patch'])
        assert args.command == 'sheet'
        assert args.sheet_action == 'patch'


class TestSessionCommand:
    def test_session_commit(self):
        args = parse_args(['session', 'commit'])
        assert args.command == 'session'
        assert args.session_action == 'commit'
