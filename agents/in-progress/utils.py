# agents/in-progress/utils.py
import re


def average_from_hd(hd):
    """Compute average HP from a dice string like '10d12' or '2d8+4'."""
    match = re.match(r'(\d+)d(\d+)(?:\+(\d+))?', str(hd).strip())
    if not match:
        raise ValueError(f"Cannot parse HD string: {hd!r}")
    num, sides, bonus = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    return (num * (sides + 1) // 2) + bonus
