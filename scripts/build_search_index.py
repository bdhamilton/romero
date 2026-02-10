#!/usr/bin/env python3
"""
Add pre-folded search columns to the Romero database.

Adds two columns to the homilies table:
  - spanish_text_folded: accent-folded, lowercased text for fast regex search
  - spanish_word_count: pre-computed token count for normalization

This eliminates expensive per-request text processing. The folding and
tokenization happen once here instead of on every search query.

Safe to run multiple times — skips if columns already exist and are populated.

Usage:
    python scripts/build_search_index.py
"""

import sqlite3
import sys
import time
import unicodedata
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == 'scripts':
    PROJECT_ROOT = PROJECT_ROOT.parent

DB_PATH = PROJECT_ROOT / 'romero.db'


def fold_accents(text):
    """Strip diacritical marks (á→a, ñ→n, etc.) for accent-insensitive matching."""
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')


def tokenize(text):
    """Split text into lowercase word tokens."""
    return re.findall(r'\w+', text.lower(), re.UNICODE)


def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Add columns if they don't exist
    existing_cols = {row[1] for row in cursor.execute('PRAGMA table_info(homilies)')}

    if 'spanish_text_folded' not in existing_cols:
        print("Adding spanish_text_folded column...")
        cursor.execute('ALTER TABLE homilies ADD COLUMN spanish_text_folded TEXT')
    if 'spanish_word_count' not in existing_cols:
        print("Adding spanish_word_count column...")
        cursor.execute('ALTER TABLE homilies ADD COLUMN spanish_word_count INTEGER')

    # Check how many need populating
    cursor.execute(
        'SELECT COUNT(*) FROM homilies '
        'WHERE spanish_text IS NOT NULL AND spanish_text_folded IS NULL'
    )
    to_fold = cursor.fetchone()[0]

    cursor.execute(
        'SELECT COUNT(*) FROM homilies '
        'WHERE spanish_text IS NOT NULL AND spanish_word_count IS NULL'
    )
    to_count = cursor.fetchone()[0]

    if to_fold == 0 and to_count == 0:
        print("✓ Search index already up to date")
        conn.close()
        return

    # Fetch rows that need processing
    rows = cursor.execute(
        'SELECT id, spanish_text FROM homilies WHERE spanish_text IS NOT NULL'
    ).fetchall()

    print(f"Processing {len(rows)} homilies...")
    start = time.time()

    for homily_id, text in rows:
        folded = fold_accents(text).lower()
        word_count = len(tokenize(text))
        cursor.execute(
            'UPDATE homilies SET spanish_text_folded = ?, spanish_word_count = ? WHERE id = ?',
            (folded, word_count, homily_id)
        )

    conn.commit()
    elapsed = time.time() - start
    print(f"✓ Processed {len(rows)} homilies in {elapsed:.1f}s")

    # Verify
    cursor.execute('SELECT COUNT(*) FROM homilies WHERE spanish_text_folded IS NOT NULL')
    folded_count = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(spanish_word_count) FROM homilies WHERE spanish_word_count IS NOT NULL')
    total_words = cursor.fetchone()[0]
    print(f"  {folded_count} texts folded, {total_words:,} total words indexed")

    conn.close()


if __name__ == '__main__':
    main()
