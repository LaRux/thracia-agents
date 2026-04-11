# tests/test_sheet_auditor.py
import json
import pytest
from pathlib import Path
from sheet_auditor import (
    load_characters, is_npc, check_sheet, assemble_full_sheet,
    audit_characters, write_audit_report_md, write_audit_report_json
)


def make_char(name='Gnoll', is_npc_val='1', archived=False, extra_fields=None):
    """Helper: build a minimal character dict."""
    fields = {'is_npc': is_npc_val}
    if extra_fields:
        fields.update(extra_fields)
    return {'name': name, 'archived': archived, 'fields': fields}


class TestIsNpc:
    def test_string_one_is_npc(self):
        assert is_npc(make_char(is_npc_val='1')) is True

    def test_bool_true_is_npc(self):
        assert is_npc(make_char(is_npc_val=True)) is True

    def test_archived_npc_excluded(self):
        assert is_npc(make_char(archived=True)) is False

    def test_pc_excluded(self):
        assert is_npc(make_char(is_npc_val='0')) is False

    def test_no_is_npc_field_excluded(self):
        char = {'name': 'PC', 'archived': False, 'fields': {}}
        assert is_npc(char) is False


class TestLoadCharacters:
    def test_loads_list(self, tmp_path):
        data = [make_char('A'), make_char('B')]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        result = load_characters(str(f))
        assert len(result) == 2
        assert result[0]['name'] == 'A'


def make_npc(name='Gnoll', overrides=None, archived=False):
    """Build a fully valid NPC character. Use overrides to introduce specific issues.
    Pass None as a value to remove that field entirely."""
    fields = {
        'is_npc': '1',
        'hd': '2d8',
        'hit_points': {'current': 9, 'max': 9},
        'ac': '14',
        'fort': '2',
        'ref': '1',
        'will': '0',
        'init': '+1',
        'act': '1d20',
        'sp': '',
        'description': 'AC: P14/S14/B12.',
        'alignment': 'neutral',
        'repeating_attacks_-abc_name': 'Bite',
        'repeating_attacks_-abc_bonus': '+2',
        'repeating_attacks_-abc_damage': '1d6',
    }
    if overrides:
        for key, val in overrides.items():
            if val is None:
                fields.pop(key, None)  # None means "remove the field entirely"
            else:
                fields[key] = val
    return {'name': name, 'archived': archived, 'fields': fields}


class TestCheckSheet:
    def test_clean_sheet_no_issues(self):
        issues, patchable, fixes = check_sheet(make_npc())
        assert issues == []
        assert patchable is False  # nothing to patch on a clean sheet

    def test_zero_hit_points_is_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'hit_points': 0}))
        assert any('hit_points' in i for i in issues)
        assert patchable is True
        assert fixes['hit_points'] == {'current': 9, 'max': 9}  # 2d8 avg = 9

    def test_dict_hit_points_zero_max_is_patchable(self):
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 0, 'max': 0}})
        )
        assert patchable is True
        assert fixes['hit_points']['max'] == 9

    def test_hit_points_consistency_recomputed(self):
        # hd=2d8 avg=9, max=3 is >20% drift
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 3, 'max': 3}})
        )
        assert any('hit_points' in i for i in issues)
        assert fixes['hit_points']['max'] == 9

    def test_hit_points_within_20pct_is_clean(self):
        # hd=2d8 avg=9, max=8 is <20% drift — acceptable
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': {'current': 8, 'max': 8}})
        )
        assert not any('hit_points' in i for i in issues)

    def test_missing_hd_is_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'hd': None}))
        assert any('missing hd' in i for i in issues)
        assert patchable is False

    def test_missing_ac_is_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'ac': None}))
        assert any('missing ac' in i for i in issues)
        assert patchable is False

    def test_missing_act_defaults_to_1d20(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'act': ''}))
        assert any('act' in i for i in issues)
        assert fixes.get('act') == '1d20'
        assert patchable is True

    def test_special_act_value_not_flagged(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'act': 'special'}))
        assert not any('act' in i for i in issues)

    def test_missing_alignment_defaults_to_neutral(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'alignment': ''}))
        assert fixes.get('alignment') == 'neutral'
        assert patchable is True

    def test_invalid_alignment_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'alignment': 'evil'}))
        assert any('alignment' in i for i in issues)
        assert patchable is False

    def test_no_attacks_not_patchable(self):
        npc = make_npc()
        npc['fields'] = {k: v for k, v in npc['fields'].items()
                         if not k.startswith('repeating_attacks')}
        issues, patchable, fixes = check_sheet(npc)
        assert any('attack' in i for i in issues)
        assert patchable is False

    def test_unparseable_numeric_field_not_patchable(self):
        issues, patchable, fixes = check_sheet(make_npc(overrides={'fort': 'X'}))
        assert any('fort' in i for i in issues)
        assert patchable is False

    def test_mixed_issues_one_non_patchable_means_manual(self):
        # hit_points=0 (patchable) + missing ac (not patchable) → overall not patchable
        issues, patchable, fixes = check_sheet(
            make_npc(overrides={'hit_points': 0, 'ac': None})
        )
        assert patchable is False


class TestAssembleFullSheet:
    def test_carries_over_all_existing_fields(self):
        npc = make_npc()
        sheet = assemble_full_sheet(npc, {})
        assert sheet['hd'] == '2d8'
        assert sheet['name'] == 'Gnoll'
        assert sheet['is_npc'] == '1'

    def test_fixes_override_existing_fields(self):
        npc = make_npc(overrides={'hit_points': 0})
        fixes = {'hit_points': {'current': 9, 'max': 9}}
        sheet = assemble_full_sheet(npc, fixes)
        assert sheet['hit_points'] == {'current': 9, 'max': 9}

    def test_attack_fields_carried_over(self):
        npc = make_npc()
        sheet = assemble_full_sheet(npc, {})
        assert sheet['repeating_attacks_-abc_name'] == 'Bite'


class TestAuditCharacters:
    def test_filters_out_pcs(self, tmp_path):
        data = [
            make_char('PC', is_npc_val='0'),
            make_npc('Gnoll'),
        ]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert len(records) == 1
        assert records[0]['name'] == 'Gnoll'

    def test_clean_npc_has_empty_issues(self, tmp_path):
        data = [make_npc('Gnoll')]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['issues'] == []
        assert records[0]['patchable'] is False
        assert records[0]['full_sheet'] is None

    def test_patchable_npc_has_full_sheet(self, tmp_path):
        data = [make_npc('Gnoll', overrides={'hit_points': 0})]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['patchable'] is True
        assert records[0]['full_sheet'] is not None
        assert records[0]['full_sheet']['hit_points']['max'] == 9

    def test_non_patchable_npc_has_no_full_sheet(self, tmp_path):
        data = [make_npc('Boss', overrides={'ac': None})]
        f = tmp_path / 'chars.json'
        f.write_text(json.dumps(data))
        records = audit_characters(str(f))
        assert records[0]['patchable'] is False
        assert records[0]['full_sheet'] is None


class TestWriteAuditReportMd:
    def _make_records(self):
        return [
            {'name': 'Clean Gnoll', 'patchable': False, 'issues': [], 'full_sheet': None},
            {'name': 'Broken Gnoll', 'patchable': True,
             'issues': ['hit_points: 0 — recomputed from hd (9)'], 'full_sheet': {'name': 'Broken Gnoll'}},
            {'name': 'Bad Boss', 'patchable': False,
             'issues': ['missing ac — manual review'], 'full_sheet': None},
        ]

    def test_creates_file(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        assert path.exists()

    def test_summary_counts_correct(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        content = path.read_text()
        assert 'NPCs audited: 3' in content
        assert 'Clean sheets: 1' in content
        assert 'Patchable issues: 1' in content
        assert 'Manual review needed: 1' in content

    def test_sections_present(self, tmp_path):
        path = tmp_path / 'report.md'
        write_audit_report_md(self._make_records(), path=str(path))
        content = path.read_text()
        assert '## Patchable' in content
        assert '## Manual Review Needed' in content
        assert '## Clean' in content
        assert 'Broken Gnoll' in content
        assert 'Bad Boss' in content
        assert 'Clean Gnoll' in content


class TestWriteAuditReportJson:
    def test_creates_valid_json(self, tmp_path):
        records = [{'name': 'Gnoll', 'patchable': False, 'issues': [], 'full_sheet': None}]
        path = tmp_path / 'report.json'
        write_audit_report_json(records, path=str(path))
        data = json.loads(path.read_text())
        assert data[0]['name'] == 'Gnoll'

    def test_preserves_all_records(self, tmp_path):
        records = [
            {'name': 'A', 'patchable': True, 'issues': ['x'], 'full_sheet': {'name': 'A'}},
            {'name': 'B', 'patchable': False, 'issues': [], 'full_sheet': None},
        ]
        path = tmp_path / 'report.json'
        write_audit_report_json(records, path=str(path))
        data = json.loads(path.read_text())
        assert len(data) == 2
