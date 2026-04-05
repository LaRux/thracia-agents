# agents/in-progress/gap_analysis.py
#
# Stage 2: Compare master_monsters.csv against Roll20 export.
# Writes gap_report.txt — one name per line — for missing monsters.
#
# Usage: python run.py monster --gap-analysis

import csv
import json
from pathlib import Path

CSV_PATH = 'data/input/master_monsters.csv'
ROLL20_PATH = 'data/input/thracia-exports/thracia-characters.json'
REPORT_PATH = 'data/output/gap_report.txt'


def find_gaps(csv_names, roll20_names):
    """Return list of csv_names that have no case-insensitive match in roll20_names."""
    roll20_lower = {n.strip().lower() for n in roll20_names}
    return [name for name in csv_names if name.strip().lower() not in roll20_lower]


def run(
    csv_path=CSV_PATH,
    roll20_path=ROLL20_PATH,
    report_path=REPORT_PATH
):
    """Compare CSV against Roll20 export, write gap_report.txt."""
    # Read monster names from CSV
    csv_names = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_names.append(row['name'])

    # Read NPC names from Roll20 export
    roll20_data = json.loads(Path(roll20_path).read_text(encoding='utf-8'))
    # Roll20 export: list of character objects, each with a 'name' key
    roll20_names = [char.get('name', '') for char in roll20_data]

    gaps = find_gaps(csv_names, roll20_names)

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(gaps))
        if gaps:
            f.write('\n')

    if gaps:
        print(f"{len(gaps)} monsters missing from Roll20. See {report_path}")
    else:
        print("No gaps found. Nothing to generate.")


if __name__ == '__main__':
    run()
