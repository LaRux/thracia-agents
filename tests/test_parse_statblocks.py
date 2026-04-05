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


from parse_statblocks import parse_5e_block, split_5e_blocks, _cr_to_hd

CAVE_FISHER_BLOCK = """Cave Fisher
Large monstrosity, unaligned

Armor Class 16 (natural armor)
Hit Points 58 (9d10 + 9)
Speed 20 ft., climb 20 ft.

STR  DEX  CON  INT  WIS  CHA
16   13   12   1    10   3
(+3) (+1) (+1) (-5) (0)  (-4)

Saving Throws CON +3, WIS +2
Challenge 3 (700 XP)"""

ZOMBIE_BLOCK = """Zombie
Medium undead, neutral evil

Armor Class 8
Hit Points 22 (3d8 + 9)
Speed 20 ft.

STR  DEX  CON  INT  WIS  CHA
13   6    16   3    6    5
(+1) (-2) (+3) (-4) (-2) (-3)

Saving Throws WIS +0
Challenge 1/4 (50 XP)"""

GHOUL_BLOCK = """Ghoul
Medium undead, chaotic evil

Armor Class 12
Hit Points 22 (5d8)
Speed 30 ft.

STR  DEX  CON  INT  WIS  CHA
13   15   10   7    10   6
(+1) (+2) (0)  (-2) (0)  (-2)

Challenge 1 (200 XP)"""

SPIDER_BLOCK = """Giant Spider
Large beast, unaligned

Armor Class 14 (natural armor)
Hit Points 26 (4d10 + 4)
Speed 30 ft., climb 30 ft.

STR  DEX  CON  INT  WIS  CHA
14   16   12   2    11   4
(+2) (+3) (+1) (-4) (0)  (-3)

Challenge 1 (200 XP)

Spider Climb. The spider can climb difficult surfaces, including upside down on ceilings, without needing to make an ability check.

Web Sense. While in contact with a web, the spider knows the exact location of any other creature in contact with the same web.

Actions
Bite. Melee Weapon Attack: +5 to hit, reach 5 ft., one creature. Hit: 7 (1d8 + 3) piercing damage, and the target must make a DC 11 Constitution saving throw, taking 9 (2d8) poison damage on a failed save, or half as much damage on a successful one. If the poison damage reduces the target to 0 hit points, the target is stable but poisoned for 1 hour, even after regaining hit points, and is paralyzed while poisoned this way.

Web (Recharge 5–6). Ranged Weapon Attack: +5 to hit, range 30/60 ft., one creature. Hit: The target is restrained by webbing. As an action, the restrained target can make a DC 12 Strength check, bursting the webbing on a success. The webbing can also be attacked and destroyed (AC 10; hp 5; vulnerability to fire damage; immunity to bludgeoning, poison, and psychic damage)."""


class TestParse5eBlock:
    def test_name(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['name'] == 'Cave Fisher'

    def test_ac(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['ac'] == '16'

    def test_hp_avg(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['hp_avg'] == '58'

    def test_cr3_maps_to_3d8(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['hd'] == '3d8'

    def test_fort_from_con_save(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['fort'] == '+3'

    def test_ref_absent_defaults_to_zero(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['ref'] == '+0'

    def test_will_from_wis_save(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['will'] == '+2'

    def test_init_from_dex_modifier(self):
        # DEX modifier (+1) → init = "+1"
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['init'] == '+1'

    def test_speed(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['speed'] == '20'

    def test_alignment_unaligned_maps_to_N(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['alignment'] == 'N'

    def test_alignment_neutral_evil_maps_to_N(self):
        # NE is on the neutral axis — maps to N, not C
        row = parse_5e_block('Zombie', ZOMBIE_BLOCK)
        assert row['alignment'] == 'N'

    def test_alignment_chaotic_evil_maps_to_C(self):
        row = parse_5e_block('Ghoul', GHOUL_BLOCK)
        assert row['alignment'] == 'C'

    def test_source_is_5e(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['source'] == '5e'

    def test_default_quantity(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['quantity'] == '1'

    def test_default_act(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['act'] == '1d20'

    def test_default_crit(self):
        row = parse_5e_block('Cave Fisher', CAVE_FISHER_BLOCK)
        assert row['crit'] == 'M/d6'

    def test_sp_raw_contains_special_ability(self):
        row = parse_5e_block('Giant Spider', SPIDER_BLOCK)
        assert 'Spider Climb' in row['sp_raw']

    def test_attacks_raw_contains_all_attacks(self):
        row = parse_5e_block('Giant Spider', SPIDER_BLOCK)
        assert 'Bite' in row['attacks_raw']
        assert 'Web' in row['attacks_raw']

    def test_attacks_raw_does_not_include_special_abilities(self):
        row = parse_5e_block('Giant Spider', SPIDER_BLOCK)
        assert 'Spider Climb' not in row['attacks_raw']


class TestCRToHD:
    def test_cr_quarter(self):
        assert _cr_to_hd(0.25) == '1d6'

    def test_cr_half(self):
        assert _cr_to_hd(0.5) == '1d6'

    def test_cr_1(self):
        assert _cr_to_hd(1) == '1d8'

    def test_cr_2(self):
        assert _cr_to_hd(2) == '2d8'

    def test_cr_3(self):
        assert _cr_to_hd(3) == '3d8'

    def test_cr_6(self):
        assert _cr_to_hd(6) == '6d8'

    def test_cr_less_than_quarter(self):
        assert _cr_to_hd(0) == '1d4'


class TestSplit5eBlocks:
    def test_extract_by_name(self):
        text = CAVE_FISHER_BLOCK + "\n\n" + ZOMBIE_BLOCK
        blocks = split_5e_blocks(text)
        assert 'cave fisher' in blocks
        assert 'zombie' in blocks

    def test_name_lookup_is_case_insensitive(self):
        blocks = split_5e_blocks(CAVE_FISHER_BLOCK)
        assert 'cave fisher' in blocks

    def test_unknown_name_not_in_dict(self):
        blocks = split_5e_blocks(CAVE_FISHER_BLOCK)
        assert 'phase spider' not in blocks


from parse_statblocks import merge_rows, run
import csv
import io

STIRGE_ROW = parse_dcc_block(STIRGE_BLOCK)
STIRGE_5E_ROW = {
    'name': 'Stirge', 'quantity': '1', 'hd': '1d8', 'hp_avg': '100',
    'ac': '99', 'init': '+1', 'speed': '5', 'fly': '', 'act': '1d20',
    'fort': '+99', 'ref': '+99', 'will': '+99', 'alignment': 'L',
    'attacks_raw': '5e_attack', 'sp_raw': '5e_sp', 'crit': 'M/d12',
    'source': '5e', 'notes': ''
}


class TestMergeRows:
    def test_dcc_authoritative_for_ac(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['ac'] == '10'  # DCC value, not 5e's '99'

    def test_dcc_authoritative_for_init(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['init'] == '+6'

    def test_source_becomes_both(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['source'] == 'both'

    def test_name_preserved(self):
        merged = merge_rows(STIRGE_ROW, STIRGE_5E_ROW)
        assert merged['name'] == 'Stirge'


class TestRunLorePreservation:
    """When source='both', the 5e lore block must remain in the lore index
    (accessible via split_5e_blocks) for Stage 3 flavor text lookup.
    The merge only affects the CSV fields — the lore index is separate.
    """
    def test_both_source_lore_block_still_in_5e_index(self, tmp_path):
        from parse_statblocks import split_5e_blocks, run as parse_run

        dcc_path = tmp_path / 'dcc_statblocks.txt'
        dcc_path.write_text(STIRGE_BLOCK, encoding='utf-8')

        # A minimal 5e block for Stirge
        stirge_5e = (
            "Stirge\n"
            "Tiny beast, unaligned\n\n"
            "Armor Class 10\n"
            "Hit Points 2 (1d4)\n"
            "Speed 10 ft., fly 40 ft.\n\n"
            "STR  DEX  CON  INT  WIS  CHA\n"
            "4    16   11   2    8    6\n"
            "(-3) (+3) (0)  (-4) (-1) (-2)\n\n"
            "Challenge 1/8 (25 XP)\n"
        )
        lore_path = tmp_path / 'lore_5e_sections.txt'
        lore_path.write_text(stirge_5e, encoding='utf-8')
        csv_path = tmp_path / 'master_monsters.csv'

        parse_run(
            dcc_path=str(dcc_path),
            lore_path=str(lore_path),
            csv_path=str(csv_path)
        )

        # The lore index must still contain 'stirge' so Stage 3 can retrieve it
        lore_blocks = split_5e_blocks(lore_path.read_text(encoding='utf-8'))
        assert 'stirge' in lore_blocks
