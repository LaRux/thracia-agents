# tests/test_parse_statblocks.py
import pytest
from parse_statblocks import parse_dcc_block, split_dcc_blocks, _parse_movement

STIRGE_BLOCK = (
    "Stirge (1d4): Init +6; Atk bite +0 melee (1d3+1 plus blood drain); Crit M/d4; "
    "AC 10; HD 1d5+1 (hp 4 each); MV 30', fly 60'; Act 1d20; "
    "SP blood drain (1 Stamina, DC 7 Fort save negates); "
    "SV Fort +2, Ref +6, Will +0; AL C."
)

GNOLL_BLOCK = (
    "Gnoll (2d6): Init +1; Atk spear +3 melee (1d8+2) / bite +1 melee (1d4); "
    "Crit M/d6; AC 14; HD 2d8+2 (hp 11 each); MV 30'; Act 1d20; "
    "SV Fort +3, Ref +1, Will +0; AL C."
)


class TestParseDCCBlock:
    def test_name(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['name'] == 'Stirge'

    def test_quantity(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['quantity'] == '1d4'

    def test_init(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['init'] == '+6'

    def test_attacks_raw(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['attacks_raw'] == 'bite +0 melee (1d3+1 plus blood drain)'

    def test_crit(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['crit'] == 'M/d4'

    def test_ac(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['ac'] == '10'

    def test_hd(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['hd'] == '1d5+1'

    def test_hp_avg(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['hp_avg'] == '4'

    def test_speed(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['speed'] == '30'

    def test_fly(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['fly'] == '60'

    def test_no_fly(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert row['fly'] == ''

    def test_act(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['act'] == '1d20'

    def test_sp_raw(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['sp_raw'] == 'blood drain (1 Stamina, DC 7 Fort save negates)'

    def test_no_sp(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert row['sp_raw'] == ''

    def test_fort(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['fort'] == '+2'

    def test_ref(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['ref'] == '+6'

    def test_will(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['will'] == '+0'

    def test_alignment(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['alignment'] == 'C'

    def test_source_is_dcc(self):
        row = parse_dcc_block(STIRGE_BLOCK)
        assert row['source'] == 'dcc'

    def test_multi_attack(self):
        row = parse_dcc_block(GNOLL_BLOCK)
        assert 'spear +3 melee (1d8+2)' in row['attacks_raw']
        assert 'bite +1 melee (1d4)' in row['attacks_raw']
        assert '/' in row['attacks_raw']


class TestSplitDCCBlocks:
    def test_split_two_blocks(self):
        text = STIRGE_BLOCK + "\n\n" + GNOLL_BLOCK
        blocks = split_dcc_blocks(text)
        assert len(blocks) == 2

    def test_first_block_is_stirge(self):
        text = STIRGE_BLOCK + "\n\n" + GNOLL_BLOCK
        blocks = split_dcc_blocks(text)
        assert 'Stirge' in blocks[0]
