# tests/test_monster_gen.py
import pytest
from monster_gen import (
    strip_sign, alignment_to_words, sanitize_filename,
    build_description, build_hit_points
)

STIRGE_ROW = {
    'name': 'Stirge', 'quantity': '1d4', 'hd': '1d5+1', 'hp_avg': '4',
    'ac': '10', 'init': '+6', 'speed': '30', 'fly': '60', 'act': '1d20',
    'fort': '+2', 'ref': '+6', 'will': '+0', 'alignment': 'C',
    'attacks_raw': 'bite +0 melee (1d3+1 plus blood drain)',
    'sp_raw': 'blood drain (1 Stamina, DC 7 Fort save negates)',
    'crit': 'M/d4', 'source': 'dcc', 'notes': ''
}

FISHER_ROW = {
    'name': 'Cave Fisher', 'quantity': '1', 'hd': '3d8', 'hp_avg': '58',
    'ac': '16', 'init': '+1', 'speed': '20', 'fly': '', 'act': '1d20',
    'fort': '+3', 'ref': '+0', 'will': '+2', 'alignment': 'N',
    'attacks_raw': 'filament +5 melee (grapple)',
    'sp_raw': '', 'crit': 'M/d6', 'source': '5e', 'notes': ''
}


class TestStripSign:
    def test_positive_drops_plus(self):
        assert strip_sign('+6') == 6

    def test_zero_drops_plus(self):
        assert strip_sign('+0') == 0

    def test_negative_preserved(self):
        assert strip_sign('-1') == -1

    def test_returns_int(self):
        assert isinstance(strip_sign('+3'), int)


class TestAlignmentToWords:
    def test_C_is_chaotic(self):
        assert alignment_to_words('C') == 'chaotic'

    def test_L_is_lawful(self):
        assert alignment_to_words('L') == 'lawful'

    def test_N_is_neutral(self):
        assert alignment_to_words('N') == 'neutral'


class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert sanitize_filename('Cave Fisher') == 'cave_fisher.json'

    def test_lowercase(self):
        assert sanitize_filename('Stirge') == 'stirge.json'


class TestBuildHitPoints:
    def test_current_equals_max(self):
        hp = build_hit_points('4')
        assert hp['current'] == hp['max']

    def test_value_is_from_hp_avg(self):
        hp = build_hit_points('58')
        assert hp['max'] == 58

    def test_values_are_integers(self):
        hp = build_hit_points('4')
        assert isinstance(hp['max'], int)


class TestBuildDescription:
    def test_contains_qty(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Qty: 1d4' in desc

    def test_contains_crit(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Crit: M/d4' in desc

    def test_contains_fly_when_present(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Fly: 60' in desc

    def test_no_fly_when_absent(self):
        desc = build_description(FISHER_ROW, armor_str='AC: P16/S16/B16')
        assert 'Fly:' not in desc

    def test_contains_armor_str(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'AC: P10/S10/B10' in desc

    def test_contains_faction(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Faction: none' in desc

    def test_contains_morale(self):
        desc = build_description(STIRGE_ROW, armor_str='AC: P10/S10/B10')
        assert 'Morale DC:' in desc
