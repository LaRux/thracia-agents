# tests/test_gap_analysis.py
import csv
import json
import pytest
from pathlib import Path
from gap_analysis import find_gaps, run


def make_csv(tmp_path, rows):
    """Write a minimal master_monsters.csv to tmp_path."""
    path = tmp_path / 'master_monsters.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name'])
        writer.writeheader()
        for name in rows:
            writer.writerow({'name': name})
    return path


def make_roll20(tmp_path, names):
    """Write a minimal thracia-characters.json to tmp_path."""
    path = tmp_path / 'thracia-characters.json'
    chars = [{'name': n} for n in names]
    path.write_text(json.dumps(chars), encoding='utf-8')
    return path


class TestFindGaps:
    def test_monster_in_csv_not_in_roll20_is_a_gap(self):
        gaps = find_gaps(['Stirge', 'Gnoll'], ['Gnoll'])
        assert 'Stirge' in gaps

    def test_monster_in_both_is_not_a_gap(self):
        gaps = find_gaps(['Gnoll'], ['Gnoll'])
        assert 'Gnoll' not in gaps

    def test_matching_is_case_insensitive(self):
        gaps = find_gaps(['Cave Fisher'], ['cave fisher'])
        assert 'Cave Fisher' not in gaps

    def test_matching_strips_whitespace(self):
        gaps = find_gaps(['Stirge'], ['  Stirge  '])
        assert 'Stirge' not in gaps

    def test_returns_csv_casing(self):
        gaps = find_gaps(['Cave Fisher'], ['gnoll'])
        assert 'Cave Fisher' in gaps

    def test_empty_csv_returns_no_gaps(self):
        gaps = find_gaps([], ['Gnoll'])
        assert gaps == []


class TestRun:
    def test_gap_report_is_one_name_per_line(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Cave Fisher', 'Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        lines = report_path.read_text().strip().split('\n')
        assert lines == ['Cave Fisher']

    def test_gap_report_has_no_headers(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Stirge'])
        roll20_path = make_roll20(tmp_path, [])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        content = report_path.read_text()
        assert 'name' not in content.lower()

    def test_no_gaps_writes_empty_file(self, tmp_path):
        csv_path = make_csv(tmp_path, ['Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        assert report_path.read_text().strip() == ''

    def test_no_gaps_prints_message(self, tmp_path, capsys):
        csv_path = make_csv(tmp_path, ['Gnoll'])
        roll20_path = make_roll20(tmp_path, ['Gnoll'])
        report_path = tmp_path / 'gap_report.txt'
        run(csv_path=str(csv_path), roll20_path=str(roll20_path),
            report_path=str(report_path))
        captured = capsys.readouterr()
        assert 'No gaps found' in captured.out
