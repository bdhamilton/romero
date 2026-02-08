#!/usr/bin/env python3
"""
Test header/footer patterns across different time periods.
Extract 10-12 sample homilies from across the corpus to verify header patterns.
"""

from pathlib import Path
import pdfplumber
import re


def extract_first_and_last_pages(pdf_path):
    """Extract first and last page to show headers/footers."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []

            # First page
            if len(pdf.pages) > 0:
                pages.append(pdf.pages[0].extract_text())

            # Last page
            if len(pdf.pages) > 1:
                pages.append(pdf.pages[-1].extract_text())

            return pages
    except Exception as e:
        return None


# Sample homilies from different periods
samples = [
    # 1977 (early)
    'data/homilies/1977/03/14/spanish.pdf',
    'data/homilies/1977/03/14/english.pdf',
    'data/homilies/1977/05/22/spanish.pdf',
    'data/homilies/1977/05/22/english.pdf',

    # 1978 (mid)
    'data/homilies/1978/06/18/spanish.pdf',
    'data/homilies/1978/06/18/english.pdf',
    'data/homilies/1978/11/26/spanish.pdf',
    'data/homilies/1978/11/26/english.pdf',

    # 1979
    'data/homilies/1979/04/01/spanish.pdf',
    'data/homilies/1979/04/01/english.pdf',
    'data/homilies/1979/09/16/spanish.pdf',
    'data/homilies/1979/09/16/english.pdf',

    # 1980 (late)
    'data/homilies/1980/01/27/spanish.pdf',
    'data/homilies/1980/01/27/english.pdf',
    'data/homilies/1980/03/23/spanish.pdf',
    'data/homilies/1980/03/23/english.pdf',
]

for pdf_path in samples:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"MISSING: {pdf_path}")
        continue

    print(f"\n{'='*70}")
    print(f"{pdf_path}")
    print('='*70)

    pages = extract_first_and_last_pages(pdf_path)
    if not pages:
        print("ERROR extracting")
        continue

    # Show first 500 chars of first page
    print("\n--- FIRST PAGE (first 500 chars) ---")
    print(pages[0][:500] if pages[0] else "(empty)")

    # Show last 500 chars of last page
    if len(pages) > 1:
        print("\n--- LAST PAGE (last 500 chars) ---")
        print(pages[1][-500:] if pages[1] else "(empty)")

    print()
