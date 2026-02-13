#!/usr/bin/env python3
"""
Add pre-folded search columns to the Romero database.

Adds columns to the homilies table for each language:
  - {lang}_text_folded: accent-folded, lowercased text for fast regex search
  - {lang}_word_count: pre-computed token count for normalization

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


def build_index_for_language(cursor, lang):
    """Build folded text and word count columns for a given language (spanish/english)."""
    text_col = f'{lang}_text'
    folded_col = f'{lang}_text_folded'
    count_col = f'{lang}_word_count'

    # Add columns if they don't exist
    existing_cols = {row[1] for row in cursor.execute('PRAGMA table_info(homilies)')}

    if folded_col not in existing_cols:
        print(f"Adding {folded_col} column...")
        cursor.execute(f'ALTER TABLE homilies ADD COLUMN {folded_col} TEXT')
    if count_col not in existing_cols:
        print(f"Adding {count_col} column...")
        cursor.execute(f'ALTER TABLE homilies ADD COLUMN {count_col} INTEGER')

    # Check how many need populating
    cursor.execute(
        f'SELECT COUNT(*) FROM homilies '
        f'WHERE {text_col} IS NOT NULL AND {folded_col} IS NULL'
    )
    to_fold = cursor.fetchone()[0]

    cursor.execute(
        f'SELECT COUNT(*) FROM homilies '
        f'WHERE {text_col} IS NOT NULL AND {count_col} IS NULL'
    )
    to_count = cursor.fetchone()[0]

    if to_fold == 0 and to_count == 0:
        print(f"✓ {lang.title()} search index already up to date")
        return

    # Fetch rows that need processing
    rows = cursor.execute(
        f'SELECT id, {text_col} FROM homilies WHERE {text_col} IS NOT NULL'
    ).fetchall()

    print(f"Processing {len(rows)} {lang} texts...")
    start = time.time()

    for homily_id, text in rows:
        folded = fold_accents(text).lower()
        word_count = len(tokenize(text))
        cursor.execute(
            f'UPDATE homilies SET {folded_col} = ?, {count_col} = ? WHERE id = ?',
            (folded, word_count, homily_id)
        )

    elapsed = time.time() - start
    print(f"✓ Processed {len(rows)} {lang} texts in {elapsed:.1f}s")

    # Verify
    cursor.execute(f'SELECT COUNT(*) FROM homilies WHERE {folded_col} IS NOT NULL')
    folded_count = cursor.fetchone()[0]
    cursor.execute(f'SELECT SUM({count_col}) FROM homilies WHERE {count_col} IS NOT NULL')
    total_words = cursor.fetchone()[0]
    print(f"  {folded_count} texts folded, {total_words:,} total words indexed")


def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    build_index_for_language(cursor, 'spanish')
    build_index_for_language(cursor, 'english')

    conn.commit()
    conn.close()


if __name__ == '__main__':
    main()
