#!/usr/bin/env python3
"""
Create SQLite database and load all homily data.

This script:
1. Creates the database schema
2. Loads metadata from homilies_metadata.json
3. Loads extracted text from data/homilies/{year}/{month}/{day}/{language}.txt
4. Stores everything in a single SQLite database file

SQLite Concepts Used:
- Tables: Structured data storage (like a spreadsheet)
- Data types: TEXT, DATE, INTEGER, TIMESTAMP
- Primary key: Unique identifier for each row (auto-incrementing)
- Indexes: Speed up lookups on specific columns (like date)
- Transactions: Group changes together (all-or-nothing)
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


def create_schema(conn):
    """
    Create the database schema.

    SQLite Data Types:
    - INTEGER: Whole numbers (id, counts)
    - TEXT: Strings of any length (titles, URLs, extracted text)
    - DATE: Dates stored as TEXT in ISO format (YYYY-MM-DD)
    - TIMESTAMP: Date+time stored as TEXT in ISO format

    PRIMARY KEY: Unique identifier for each row, auto-increments
    UNIQUE: Enforces that no two rows can have the same value
    NOT NULL: Column must have a value (can't be empty)
    """
    cursor = conn.cursor()

    # Create the main homilies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homilies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Basic metadata (from index page)
            date DATE NOT NULL,
            occasion TEXT,
            english_title TEXT,
            spanish_title TEXT,
            detail_url TEXT UNIQUE,
            biblical_references TEXT,

            -- PDF information
            spanish_pdf_url TEXT,
            spanish_pdf_path TEXT,
            english_pdf_url TEXT,
            english_pdf_path TEXT,

            -- Extracted text (the actual homily content)
            spanish_text TEXT,
            english_text TEXT,

            -- Audio (optional)
            audio_url TEXT,

            -- Tracking timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for fast lookups
    # Index on date: We'll query by date range frequently for time-series
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_date ON homilies(date)
    ''')

    # Why indexes?
    # Without index: SQLite scans every row to find matches (slow)
    # With index: SQLite uses a sorted lookup structure (fast)
    # Think of it like a book index vs. reading every page

    conn.commit()
    print("✓ Database schema created")


def load_metadata(conn):
    """
    Load metadata from homilies_metadata.json into database.

    Transactions:
    - BEGIN: Start a transaction
    - COMMIT: Save all changes (if no errors)
    - ROLLBACK: Undo all changes (if error occurs)

    Why use transactions?
    - All 195 rows load successfully, or none do (atomic)
    - Much faster: One commit at end vs. 195 commits
    - Data integrity: No partial/corrupt state
    """
    # Load JSON metadata
    with open('data/homilies_metadata.json', 'r') as f:
        homilies = json.load(f)

    print(f"Loading {len(homilies)} homilies from metadata...")

    cursor = conn.cursor()

    # Start transaction (automatic in Python, but explicit is clearer)
    # All inserts happen in memory until we commit
    for homily in homilies:
        cursor.execute('''
            INSERT INTO homilies (
                date, occasion, english_title, spanish_title,
                detail_url, biblical_references,
                spanish_pdf_url, english_pdf_url, audio_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            homily['date'],
            homily.get('occasion'),
            homily.get('english_title'),
            homily.get('spanish_title'),
            homily.get('detail_url'),
            homily.get('biblical_references'),
            homily.get('spanish_pdf_url'),
            homily.get('english_pdf_url'),
            homily.get('audio_url')
        ))

        # Why parameterized queries (the ? placeholders)?
        # - Prevents SQL injection attacks
        # - SQLite handles escaping/quoting automatically
        # - Cleaner than string concatenation

    # Commit transaction: Write all changes to disk
    conn.commit()

    print(f"✓ Loaded {len(homilies)} homilies metadata")
    return len(homilies)


def load_text_files(conn):
    """
    Load extracted text from .txt files and update database.

    UPDATE vs INSERT:
    - INSERT: Create new row
    - UPDATE: Modify existing row
    We're updating rows that were created by load_metadata()
    """
    cursor = conn.cursor()

    # Find all text files
    text_files = list(Path('data/homilies').rglob('*.txt'))
    print(f"Found {len(text_files)} text files")

    spanish_count = 0
    english_count = 0

    for text_path in text_files:
        # Parse path: data/homilies/1977/03/14/spanish.txt
        parts = text_path.parts
        year = parts[-4]
        month = parts[-3]
        day = parts[-2]
        language = text_path.stem  # 'spanish' or 'english'

        # Construct date in ISO format (YYYY-MM-DD)
        date = f"{year}-{month}-{day}"

        # Read text file
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Update the database row for this date
        if language == 'spanish':
            cursor.execute('''
                UPDATE homilies
                SET spanish_text = ?,
                    spanish_pdf_path = ?
                WHERE date = ?
            ''', (text, str(text_path.with_suffix('.pdf')), date))
            spanish_count += 1

        elif language == 'english':
            cursor.execute('''
                UPDATE homilies
                SET english_text = ?,
                    english_pdf_path = ?
                WHERE date = ?
            ''', (text, str(text_path.with_suffix('.pdf')), date))
            english_count += 1

    # Commit all text updates
    conn.commit()

    print(f"✓ Loaded {spanish_count} Spanish texts")
    print(f"✓ Loaded {english_count} English texts")

    return spanish_count, english_count


def verify_data(conn):
    """
    Verify data integrity after loading.

    Aggregate queries:
    - COUNT(*): Count rows
    - COUNT(column): Count non-NULL values in column
    - WHERE: Filter rows
    """
    cursor = conn.cursor()

    # Total homilies
    cursor.execute('SELECT COUNT(*) FROM homilies')
    total = cursor.fetchone()[0]
    print(f"\nDatabase contains {total} homilies")

    # How many have Spanish text?
    cursor.execute('SELECT COUNT(*) FROM homilies WHERE spanish_text IS NOT NULL')
    spanish_count = cursor.fetchone()[0]
    print(f"  {spanish_count} with Spanish text ({spanish_count/total*100:.1f}%)")

    # How many have English text?
    cursor.execute('SELECT COUNT(*) FROM homilies WHERE english_text IS NOT NULL')
    english_count = cursor.fetchone()[0]
    print(f"  {english_count} with English text ({english_count/total*100:.1f}%)")

    # Date range
    cursor.execute('SELECT MIN(date), MAX(date) FROM homilies')
    min_date, max_date = cursor.fetchone()
    print(f"  Date range: {min_date} to {max_date}")

    # Average text length (as a sanity check)
    cursor.execute('''
        SELECT AVG(LENGTH(spanish_text))
        FROM homilies
        WHERE spanish_text IS NOT NULL
    ''')
    avg_length = cursor.fetchone()[0]
    print(f"  Average Spanish text length: {avg_length:,.0f} characters")

    # Show a sample homily
    cursor.execute('''
        SELECT date, occasion, english_title,
               LENGTH(spanish_text) as spanish_len,
               LENGTH(english_text) as english_len
        FROM homilies
        WHERE spanish_text IS NOT NULL
        LIMIT 1
    ''')
    sample = cursor.fetchone()
    print(f"\nSample homily:")
    print(f"  Date: {sample[0]}")
    print(f"  Occasion: {sample[1]}")
    print(f"  Title: {sample[2]}")
    print(f"  Spanish: {sample[3]:,} chars")
    print(f"  English: {sample[4]:,} chars" if sample[4] else "  English: (not available)")


def main():
    """
    Main script execution.

    Context manager (with statement):
    - Automatically commits on success
    - Automatically rolls back on error
    - Automatically closes connection
    """
    db_path = 'data/romero.db'

    print("Creating Romero Homilies Database")
    print("=" * 60)
    print(f"Database location: {db_path}")
    print()

    # Connect to database (creates file if doesn't exist)
    with sqlite3.connect(db_path) as conn:
        # Enable foreign key support (not used yet, but good practice)
        conn.execute('PRAGMA foreign_keys = ON')

        # Create schema
        create_schema(conn)

        # Load metadata
        metadata_count = load_metadata(conn)

        # Load text files
        spanish_count, english_count = load_text_files(conn)

        # Verify everything loaded correctly
        verify_data(conn)

    print()
    print("=" * 60)
    print("✓ Database creation complete!")
    print(f"  Location: {db_path}")
    print(f"  Size: {Path(db_path).stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == '__main__':
    main()
