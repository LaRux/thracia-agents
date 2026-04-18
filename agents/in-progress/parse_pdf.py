# agents/in-progress/parse_pdf.py
#
# Shared PDF extraction module used by room_gen.py and encounter_gen.py.
# Extracts text from targeted page ranges of the Thracia PDF and writes
# staged text files to data/input/. Re-extraction is skipped if staged
# files already exist (use reextract=True to force).

import re
from pathlib import Path

import pdfplumber

PDF_PATH = 'C:/Users/lheur/Documents/Obsidian Vault/Adventures/Caverns_of_Thracia_-_DCC_v2.pdf'
ROOMS_DELIMITER = '---ROOM---'

# Primary: "Area 1-2" or "Area 1-2 - Name"
PRIMARY_HEADER_RE = re.compile(r'^Area\s+\d+-\d+', re.IGNORECASE)
# Fallback: "Bat Infested Hallway:" (Title Case ending in colon)
FALLBACK_HEADER_RE = re.compile(r"^[A-Z][A-Za-z\s\'-]{3,}:$")


def split_rooms(text):
    """Split raw PDF text into room blocks by header pattern.

    Tries the primary 'Area X-Y' pattern first, falls back to title-case
    lines ending in a colon for irregular headers like 'Bat Infested Hallway:'.

    Returns:
        list[str]: non-empty room text blocks
    """
    lines = text.splitlines()
    blocks = []
    current_lines = []

    for line in lines:
        stripped = line.strip()
        is_header = PRIMARY_HEADER_RE.match(stripped) or FALLBACK_HEADER_RE.match(stripped)
        if is_header:
            if current_lines:
                block = '\n'.join(current_lines).strip()
                if block:
                    blocks.append(block)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        block = '\n'.join(current_lines).strip()
        if block:
            blocks.append(block)

    return blocks


def _extract_text(pages):
    """Extract and concatenate text from PDF pages (1-based range, inclusive)."""
    start, end = pages
    chunks = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i in range(start - 1, end):  # pdfplumber is 0-indexed
            page = pdf.pages[i]
            chunks.append(page.extract_text() or '')
    return '\n'.join(chunks)


def extract_rooms(section_key, pages, reextract=False):
    """Extract and stage room blocks for a PDF section.

    Args:
        section_key: e.g. 'level_1'
        pages: (start, end) tuple of 1-based page numbers (inclusive)
        reextract: if True, re-extract even if staged file exists

    Returns:
        Path to staged rooms_{section_key}.txt file
    """
    out_path = Path(f'data/input/rooms_{section_key}.txt')
    if out_path.exists() and not reextract:
        return out_path

    text = _extract_text(pages)
    blocks = split_rooms(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f'\n{ROOMS_DELIMITER}\n'.join(blocks), encoding='utf-8')
    print(f"parse_pdf: {len(blocks)} rooms extracted → {out_path}")
    return out_path


def extract_wandering(section_key, pages, reextract=False):
    """Extract and stage wandering table text for a PDF section.

    Args:
        section_key: e.g. 'level_1'
        pages: (start, end) tuple of 1-based page numbers (inclusive)
        reextract: if True, re-extract even if staged file exists

    Returns:
        Path to staged wandering_{section_key}.txt file
    """
    out_path = Path(f'data/input/wandering_{section_key}.txt')
    if out_path.exists() and not reextract:
        return out_path

    text = _extract_text(pages)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding='utf-8')
    print(f"parse_pdf: wandering table extracted → {out_path}")
    return out_path
