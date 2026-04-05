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
