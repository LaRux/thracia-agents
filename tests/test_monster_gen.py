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

    def test_empty_string_returns_zero(self):
        assert strip_sign('') == 0


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

    def test_falls_back_to_hd_when_hp_avg_empty(self):
        hp = build_hit_points('', hd='10d12')
        assert hp['max'] == 65
        assert hp['current'] == hp['max']


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


import csv
import json
from unittest.mock import patch, MagicMock
from monster_gen import generate_sheet, load_csv_by_name, write_sheet, run_generate_all, run_generate_name

MOCK_CLAUDE_RESPONSE = json.dumps({
    "armor_str": "AC: P10/S10/B10",
    "sp": "Blood drain: on hit, target loses 1 Stamina (DC 7 Fort negates).",
    "attacks": [
        {"name": "Bite", "attack": "+0", "damage": "1d3+1", "type": "piercing"}
    ],
    "morale_dc": 11
})

SCHEMA_CONTENT = "# Roll20 NPC Schema\nField reference."


class TestGenerateSheet:
    def _mock_claude(self, response_text):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=response_text)]
        mock_client.messages.create.return_value = mock_msg
        return mock_client

    def test_output_contains_is_npc(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['is_npc'] == 1

    def test_output_name_preserved(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['name'] == 'Stirge'

    def test_alignment_converted_to_words(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['alignment'] == 'chaotic'

    def test_fort_is_int_without_plus(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['fort'] == 2
        assert isinstance(sheet['fort'], int)

    def test_init_is_int_without_plus(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['init'] == 6

    def test_hit_points_structure(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['hit_points'] == {'current': 4, 'max': 4}

    def test_attack_1_keys_present(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'repeating_attacks_-npc_attack_1_name' in sheet
        assert 'repeating_attacks_-npc_attack_1_attack' in sheet
        assert 'repeating_attacks_-npc_attack_1_damage' in sheet
        assert 'repeating_attacks_-npc_attack_1_type' in sheet

    def test_attack_1_name_value(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['repeating_attacks_-npc_attack_1_name'] == 'Bite'

    def test_sp_field_populated(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'Blood drain' in sheet['sp']

    def test_description_contains_armor_str(self):
        client = self._mock_claude(MOCK_CLAUDE_RESPONSE)
        sheet = generate_sheet(STIRGE_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'AC: P10/S10/B10' in sheet['description']

    def test_multi_attack_generates_multiple_keys(self):
        multi_row = dict(STIRGE_ROW)
        multi_row['attacks_raw'] = 'claw +2 melee (1d4) / claw +2 melee (1d4) / bite +4 melee (1d8)'
        multi_response = json.dumps({
            "armor_str": "AC: P10/S10/B10",
            "sp": "",
            "attacks": [
                {"name": "Claw", "attack": "+2", "damage": "1d4", "type": "slashing"},
                {"name": "Claw", "attack": "+2", "damage": "1d4", "type": "slashing"},
                {"name": "Bite", "attack": "+4", "damage": "1d8", "type": "piercing"},
            ],
            "morale_dc": 11
        })
        client = self._mock_claude(multi_response)
        sheet = generate_sheet(multi_row, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert 'repeating_attacks_-npc_attack_3_name' in sheet

    def test_empty_attacks_raw_generates_unarmed_strike(self):
        no_attack_row = dict(FISHER_ROW)
        no_attack_row['attacks_raw'] = ''
        unarmed_response = json.dumps({
            "armor_str": "AC: P16/S16/B16",
            "sp": "",
            "attacks": [
                {"name": "Unarmed Strike", "attack": "+0", "damage": "1d3",
                 "type": "bludgeoning"}
            ],
            "morale_dc": 11
        })
        client = self._mock_claude(unarmed_response)
        sheet = generate_sheet(no_attack_row, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['repeating_attacks_-npc_attack_1_name'] == 'Unarmed Strike'

    def test_empty_sp_raw_gives_empty_sp(self):
        client = self._mock_claude(json.dumps({
            "armor_str": "AC: P16/S16/B16",
            "sp": "",
            "attacks": [{"name": "Filament", "attack": "+5", "damage": "special",
                         "type": "piercing"}],
            "morale_dc": 11
        }))
        sheet = generate_sheet(FISHER_ROW, schema=SCHEMA_CONTENT,
                               lore_block='', client=client)
        assert sheet['sp'] == ''


class TestLoadCSVByName:
    def test_finds_monster_by_name(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'hp_avg'])
            writer.writeheader()
            writer.writerow({'name': 'Stirge', 'hp_avg': '4'})
        row = load_csv_by_name('Stirge', str(csv_path))
        assert row['hp_avg'] == '4'

    def test_returns_none_for_missing_monster(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name'])
            writer.writeheader()
        row = load_csv_by_name('Stirge', str(csv_path))
        assert row is None


class TestWriteSheet:
    def test_writes_json_file(self, tmp_path):
        pending = tmp_path / 'pending'
        pending.mkdir()
        sheet = {'name': 'Stirge', 'is_npc': 1}
        write_sheet(sheet, str(pending))
        assert (pending / 'stirge.json').exists()

    def test_overwrites_existing_file(self, tmp_path):
        pending = tmp_path / 'pending'
        pending.mkdir()
        (pending / 'stirge.json').write_text('{"old": true}')
        sheet = {'name': 'Stirge', 'is_npc': 1}
        write_sheet(sheet, str(pending))
        data = json.loads((pending / 'stirge.json').read_text())
        assert 'old' not in data

    def test_empty_gap_report_prints_no_gaps(self, tmp_path, capsys):
        report = tmp_path / 'gap_report.txt'
        report.write_text('')
        csv_path = tmp_path / 'master_monsters.csv'
        csv_path.write_text('name\n')
        run_generate_all(
            gap_report_path=str(report),
            csv_path=str(csv_path),
            pending_dir=str(tmp_path / 'pending')
        )
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out

    def test_missing_gap_report_prints_no_gaps(self, tmp_path, capsys):
        csv_path = tmp_path / 'master_monsters.csv'
        csv_path.write_text('name\n')
        run_generate_all(
            gap_report_path=str(tmp_path / 'nonexistent_gap_report.txt'),
            csv_path=str(csv_path),
            pending_dir=str(tmp_path / 'pending')
        )
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out


class TestRunGenerateName:
    def test_missing_monster_exits_nonzero(self, tmp_path):
        csv_path = tmp_path / 'master_monsters.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name'])
            writer.writeheader()
        with pytest.raises(SystemExit) as exc:
            run_generate_name('Nonexistent', csv_path=str(csv_path))
        assert exc.value.code != 0

    def test_generate_name_bypasses_gap_report(self, tmp_path):
        """--name should generate even if monster is not in gap_report.txt."""
        from unittest.mock import patch, MagicMock
        # CSV has Stirge; gap_report is empty (Stirge already in Roll20)
        csv_path = tmp_path / 'master_monsters.csv'
        from parse_statblocks import CSV_COLUMNS
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerow({col: STIRGE_ROW.get(col, '') for col in CSV_COLUMNS})
        pending = tmp_path / 'pending'
        mock_sheet = {'name': 'Stirge', 'is_npc': 1}
        with patch('monster_gen.generate_sheet', return_value=mock_sheet):
            run_generate_name(
                'Stirge',
                csv_path=str(csv_path),
                pending_dir=str(pending)
            )
        assert (pending / 'stirge.json').exists()
