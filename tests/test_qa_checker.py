# tests/test_qa_checker.py
import json
import pytest
from qa_checker import pass1_check

VALID_SHEET = {
    'is_npc': 1,
    'name': 'Stirge',
    'hd': '1d5+1',
    'hit_points': {'current': 4, 'max': 4},
    'ac': 10,
    'fort': 2,
    'ref': 6,
    'will': 0,
    'init': 6,
    'act': '1d20',
    'speed': '30',
    'alignment': 'chaotic',
    'sp': 'Blood drain: on hit, target loses 1 Stamina.',
    'description': 'AC: P10/S10/B10. Crit: M/d4. Qty: 1d4. Faction: none. Morale DC: 11.',
    'repeating_attacks_-npc_attack_1_name': 'Bite',
    'repeating_attacks_-npc_attack_1_attack': '+0',
    'repeating_attacks_-npc_attack_1_damage': '1d3+1',
    'repeating_attacks_-npc_attack_1_type': 'piercing',
}


class TestPass1Check:
    def test_valid_sheet_passes(self):
        errors = pass1_check(VALID_SHEET)
        assert errors == []

    def test_missing_required_field_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['hd']
        errors = pass1_check(sheet)
        assert any('hd' in e for e in errors)

    def test_missing_sp_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['sp']
        errors = pass1_check(sheet)
        assert any('sp' in e for e in errors)

    def test_hit_points_mismatch_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['hit_points'] = {'current': 3, 'max': 4}
        errors = pass1_check(sheet)
        assert any('hit_points' in e for e in errors)

    def test_invalid_hd_notation_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['hd'] = 'five dice'
        errors = pass1_check(sheet)
        assert any('hd' in e for e in errors)

    def test_invalid_alignment_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['alignment'] = 'evil'
        errors = pass1_check(sheet)
        assert any('alignment' in e for e in errors)

    def test_description_missing_armor_vector_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['description'] = 'No armor info here.'
        errors = pass1_check(sheet)
        assert any('description' in e for e in errors)

    def test_attack_group_missing_damage_key_fails(self):
        sheet = dict(VALID_SHEET)
        del sheet['repeating_attacks_-npc_attack_1_damage']
        errors = pass1_check(sheet)
        assert any('attack' in e.lower() for e in errors)

    def test_attack_value_as_number_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['repeating_attacks_-npc_attack_1_attack'] = 0  # should be "+0" string
        errors = pass1_check(sheet)
        assert any('attack' in e.lower() for e in errors)

    def test_ac_as_string_fails(self):
        sheet = dict(VALID_SHEET)
        sheet['ac'] = '10'  # should be int
        errors = pass1_check(sheet)
        assert any('ac' in e for e in errors)


import shutil
from unittest.mock import MagicMock, patch
from qa_checker import pass2_check, route_sheet, run


def make_mock_client(response_text):
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


class TestPass2Check:
    def test_pass_response_returns_pass(self):
        client = make_mock_client("PASS Stats look appropriate for a small insect.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'PASS'

    def test_flag_response_returns_flag(self):
        client = make_mock_client("FLAG will save of 10 is implausible for a mindless creature.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'FLAG'
        assert 'will save' in reason

    def test_malformed_response_treated_as_flag(self):
        client = make_mock_client("This sheet looks reasonable to me.")
        result, reason = pass2_check(VALID_SHEET, client=client)
        assert result == 'FLAG'
        assert 'malformed' in reason


class TestRouteSheet:
    def test_passing_sheet_goes_to_ready(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=[],
            pass2_result='PASS',
            pass2_reason='',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (ready / 'stirge.json').exists()
        assert not (flagged / 'stirge.json').exists()

    def test_failing_sheet_goes_to_flagged_with_report(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=['Missing field: hd'],
            pass2_result='PASS',
            pass2_reason='',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (flagged / 'stirge.json').exists()
        assert (flagged / 'stirge_qa_report.txt').exists()
        assert not (ready / 'stirge.json').exists()

    def test_pass2_flag_goes_to_flagged_with_report(self, tmp_path):
        pending = tmp_path / 'pending'
        ready = tmp_path / 'ready'
        flagged = tmp_path / 'flagged'
        for d in [pending, ready, flagged]:
            d.mkdir()
        sheet_path = pending / 'stirge.json'
        sheet_path.write_text(json.dumps(VALID_SHEET))

        route_sheet(
            sheet_path=str(sheet_path),
            pass1_errors=[],
            pass2_result='FLAG',
            pass2_reason='will save too high for an insect',
            ready_dir=str(ready),
            flagged_dir=str(flagged)
        )
        assert (flagged / 'stirge.json').exists()
        report = (flagged / 'stirge_qa_report.txt').read_text()
        assert 'will save' in report
