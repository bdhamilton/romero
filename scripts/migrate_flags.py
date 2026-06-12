#!/usr/bin/env python3
"""
Move the flags table out of the corpus DB into a separate flags DB.

Why: romero.db is versioned in git and deployed; flags are written live on
the server. Two writers on one git-tracked binary file made every deploy a
conflict. After this migration, romero.db is corpus-only (read-only on the
server) and flags.db is server-local and gitignored.

Usage:
    python scripts/migrate_flags.py                  # full migration: copy + drop + vacuum
    python scripts/migrate_flags.py --no-drop        # copy only, leave source untouched
    python scripts/migrate_flags.py --source X --flags Y

Idempotent: exits cleanly if the source has no flags table, and refuses to
copy into a flags DB that already has rows.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Same schema the app ensures on every connection (see app.py). The
# homily_id column refers to homilies(id) in romero.db; SQLite can't enforce
# foreign keys across attached databases, so it's a plain column.
FLAGS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS flagdb.flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        homily_id INTEGER,
        comment TEXT NOT NULL,
        status TEXT DEFAULT 'open',  -- 'open', 'resolved', 'wontfix'
        resolution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''


def main():
    parser = argparse.ArgumentParser(
        description='Move the flags table from the corpus DB into flags.db')
    parser.add_argument('--source', default='romero.db',
                        help='DB containing the flags table (default: romero.db)')
    parser.add_argument('--flags', default='flags.db',
                        help='destination flags DB (default: flags.db)')
    parser.add_argument('--no-drop', action='store_true',
                        help='copy flags but leave the source table in place')
    args = parser.parse_args()

    if not Path(args.source).exists():
        sys.exit(f"Source database not found: {args.source}")

    conn = sqlite3.connect(args.source)

    has_flags = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='flags'"
    ).fetchone()
    if not has_flags:
        print(f"Nothing to migrate: no flags table in {args.source}")
        return

    conn.execute('ATTACH DATABASE ? AS flagdb', (args.flags,))
    conn.execute(FLAGS_SCHEMA)

    existing = conn.execute('SELECT COUNT(*) FROM flagdb.flags').fetchone()[0]
    if existing:
        sys.exit(f"Refusing to copy: {args.flags} already has {existing} flags")

    # Copying rows with their original ids also advances the AUTOINCREMENT
    # sequence, so new flags continue numbering where the old table left off.
    conn.execute('INSERT INTO flagdb.flags SELECT * FROM main.flags')
    conn.commit()
    copied = conn.execute('SELECT COUNT(*) FROM flagdb.flags').fetchone()[0]
    print(f"Copied {copied} flags from {args.source} to {args.flags}")

    if args.no_drop:
        print(f"--no-drop: flags table left in place in {args.source}")
    else:
        conn.execute('DROP TABLE main.flags')
        conn.commit()
        # VACUUM rewrites the file compactly — dropping a table only marks
        # its pages reusable, it doesn't shrink the file. VACUUM can't run
        # with another database attached or inside a transaction.
        conn.execute('DETACH DATABASE flagdb')
        conn.execute('VACUUM')
        print(f"Dropped flags table from {args.source} and vacuumed")

    conn.close()


if __name__ == '__main__':
    main()
