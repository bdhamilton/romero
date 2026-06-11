#!/usr/bin/env python3
"""Combine all English homily PDFs into a single bookmarked PDF.

The PDFs are already on disk (downloaded during Phase 0); this script just
gathers the ones referenced by the database and merges them in chronological
order, adding one bookmark per homily so the ~1,900-page result is navigable.

Usage:
    python scripts/combine_english_pdfs.py                 # -> combined_english.pdf
    python scripts/combine_english_pdfs.py out.pdf         # custom output path
"""
import logging
import os
import sqlite3
import sys

from pypdf import PdfReader, PdfWriter

# Source PDFs have minor structural quirks that make pypdf emit a flood of
# harmless "Ignoring wrong pointing object" warnings. Quiet them.
logging.getLogger("pypdf").setLevel(logging.ERROR)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "romero.db")


def resolve(path):
    """DB paths are mostly repo-relative, a few are absolute. Normalize both."""
    if os.path.isabs(path):
        return path
    return os.path.join(REPO_ROOT, path)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "combined_english.pdf")

    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        """
        SELECT id, date, occasion, english_title, english_pdf_path
        FROM homilies
        WHERE english_pdf_path IS NOT NULL
        ORDER BY date, id
        """
    ).fetchall()
    con.close()

    writer = PdfWriter()
    merged = skipped = total_pages = 0

    for hid, date, occasion, title, rel_path in rows:
        path = resolve(rel_path)
        if not os.path.isfile(path):
            print(f"  SKIP (missing): {date} -> {rel_path}")
            skipped += 1
            continue
        try:
            reader = PdfReader(path)
        except Exception as exc:
            print(f"  SKIP (unreadable): {date} -> {rel_path}: {exc}")
            skipped += 1
            continue

        page_at = len(writer.pages)  # bookmark target = first page of this homily
        for page in reader.pages:
            writer.add_page(page)

        label = (title or occasion or "Homily").strip()
        writer.add_outline_item(f"{date} — {label}", page_at)

        merged += 1
        total_pages += len(reader.pages)

    with open(out_path, "wb") as fh:
        writer.write(fh)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nMerged {merged} English PDFs ({total_pages} pages), skipped {skipped}.")
    print(f"Output: {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
