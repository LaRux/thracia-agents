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
    def test_monster_parse_flag(self):
        args = parse_args(['monster', '--parse'])
        assert args.command == 'monster'
        assert args.parse is True

    def test_monster_gap_analysis_flag(self):
        args = parse_args(['monster', '--gap-analysis'])
        assert args.gap_analysis is True

    def test_monster_generate_with_name(self):
        args = parse_args(['monster', '--generate', '--name', 'Stirge'])
        assert args.generate is True
        assert args.name == 'Stirge'

    def test_monster_generate_with_all(self):
        args = parse_args(['monster', '--generate', '--all'])
        assert args.generate is True
        assert args.all is True

    def test_monster_generate_no_subarg_allowed(self):
        # --generate with no --name or --all is allowed (treated as --all in handler)
        args = parse_args(['monster', '--generate'])
        assert args.generate is True

    def test_monster_requires_action_flag(self):
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
    def test_qa_no_args(self):
        args = parse_args(['qa'])
        assert args.command == 'qa'


class TestSheetCommand:
    def test_sheet_audit_flag(self):
        args = parse_args(['sheet', '--audit'])
        assert args.command == 'sheet'
        assert args.audit is True

    def test_sheet_patch_flag(self):
        args = parse_args(['sheet', '--patch'])
        assert args.command == 'sheet'
        assert args.patch is True

    def test_sheet_audit_and_patch_together(self):
        args = parse_args(['sheet', '--audit', '--patch'])
        assert args.audit is True
        assert args.patch is True


class TestSessionCommand:
    def test_session_commit(self):
        args = parse_args(['session', 'commit'])
        assert args.command == 'session'
        assert args.session_action == 'commit'
