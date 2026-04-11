import json
import pytest
from pathlib import Path
from sheet_patcher import sanitize_filename, run_patch


class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert sanitize_filename('Gnoll Alpha') == 'gnoll_alpha.json'

    def test_lowercase(self):
        assert sanitize_filename('GNOLL') == 'gnoll.json'

    def test_special_chars_removed(self):
        assert sanitize_filename("G'ruk") == 'gruk.json'


class TestRunPatch:
    def _make_audit(self, patchable=True):
        return [
            {
                'name': 'Gnoll',
                'patchable': patchable,
                'issues': ['hit_points: 0 — recomputed from hd (9)'],
                'full_sheet': {'name': 'Gnoll', 'is_npc': '1', 'hd': '2d8'} if patchable else None,
            }
        ]

    def test_writes_patchable_sheet_to_pending(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=True)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        assert (pending / 'gnoll.json').exists()

    def test_written_file_contains_full_sheet(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=True)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        data = json.loads((pending / 'gnoll.json').read_text())
        assert data['name'] == 'Gnoll'
        assert data['hd'] == '2d8'

    def test_skips_non_patchable_records(self, tmp_path):
        audit_path = tmp_path / 'audit_report.json'
        audit_path.write_text(json.dumps(self._make_audit(patchable=False)))
        pending = tmp_path / 'pending'
        run_patch(audit_path=str(audit_path), pending_dir=str(pending))
        assert not (pending / 'gnoll.json').exists()

    def test_missing_audit_file_prints_message(self, tmp_path, capsys):
        run_patch(
            audit_path=str(tmp_path / 'nonexistent.json'),
            pending_dir=str(tmp_path / 'pending')
        )
        assert 'No audit report' in capsys.readouterr().out
