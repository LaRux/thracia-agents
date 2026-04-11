#
# Plan 03: Write full replacement sheets for patchable NPCs.
# Reads audit_report.json produced by SheetAuditor.
#
# Usage:
#   python run.py sheet --patch

import json
import re
from pathlib import Path

AUDIT_REPORT_JSON = 'data/output/audit_report.json'
PENDING_DIR = 'data/output/pending'


def sanitize_filename(name):
    """Convert monster name to a safe filename: lowercase, spaces→underscores."""
    safe = re.sub(r'[^\w\s-]', '', name.lower())
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe + '.json'


def run_patch(audit_path=AUDIT_REPORT_JSON, pending_dir=PENDING_DIR):
    """Read audit_report.json and write full replacement sheets to pending/."""
    if not Path(audit_path).exists():
        print(f"No audit report found at {audit_path}. Run 'python run.py sheet --audit' first.")
        return

    records = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    patchable = [r for r in records if r.get('patchable') and r.get('full_sheet')]

    if not patchable:
        print("No patchable NPCs in audit report.")
        return

    Path(pending_dir).mkdir(parents=True, exist_ok=True)
    for record in patchable:
        filename = sanitize_filename(record['name'])
        path = Path(pending_dir) / filename
        path.write_text(json.dumps(record['full_sheet'], indent=2), encoding='utf-8')
        print(f"  Wrote {path}")

    print(f"  {len(patchable)} patch file(s) written to {pending_dir}/")
