#!/usr/bin/env python3
"""
Database health check for the Romero homilies corpus.

Checks:
  1. Coverage — text, PDFs, search index completeness
  2. Consistency — DB text vs disk files, word counts, folded index
  3. Integrity — date range, monthly distribution, suspicious outliers
  4. Flags — open data issue reports

Usage:
    python scripts/db_health.py
"""

import os
import re
import sqlite3
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'romero.db'

RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
DIM = '\033[2m'
RESET = '\033[0m'

problems = []
warnings = []


def ok(msg):
    print(f"  {GREEN}OK{RESET}  {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  {YELLOW}WARN{RESET}  {msg}")


def fail(msg):
    problems.append(msg)
    print(f"  {RED}FAIL{RESET}  {msg}")


def fold_accents(text):
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ── 1. COVERAGE ──────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("1. COVERAGE")
    print(f"{'='*60}")

    total = conn.execute("SELECT COUNT(*) as n FROM homilies").fetchone()['n']
    es_text = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE spanish_text IS NOT NULL AND spanish_text != ''").fetchone()['n']
    en_text = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE english_text IS NOT NULL AND english_text != ''").fetchone()['n']
    both_text = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE (spanish_text IS NOT NULL AND spanish_text != '') AND (english_text IS NOT NULL AND english_text != '')").fetchone()['n']
    neither_text = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE (spanish_text IS NULL OR spanish_text = '') AND (english_text IS NULL OR english_text = '')").fetchone()['n']

    es_pdf = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE spanish_pdf_url IS NOT NULL AND spanish_pdf_url != ''").fetchone()['n']
    en_pdf = conn.execute("SELECT COUNT(*) as n FROM homilies WHERE english_pdf_url IS NOT NULL AND english_pdf_url != ''").fetchone()['n']

    print(f"  Total homilies:    {total}")
    print(f"  Spanish text:      {es_text}/{total}  ({total - es_text} missing)")
    print(f"  English text:      {en_text}/{total}  ({total - en_text} missing)")
    print(f"  Both languages:    {both_text}")
    print(f"  Neither language:  {neither_text}")
    print(f"  Spanish PDF URLs:  {es_pdf}")
    print(f"  English PDF URLs:  {en_pdf}")
    print()

    # Homilies with PDF URL but no text (extraction failures)
    es_pdf_no_text = conn.execute(
        "SELECT id, date, occasion FROM homilies "
        "WHERE spanish_pdf_url IS NOT NULL AND spanish_pdf_url != '' "
        "AND (spanish_text IS NULL OR spanish_text = '')"
    ).fetchall()
    en_pdf_no_text = conn.execute(
        "SELECT id, date, occasion FROM homilies "
        "WHERE english_pdf_url IS NOT NULL AND english_pdf_url != '' "
        "AND (english_text IS NULL OR english_text = '')"
    ).fetchall()

    if es_pdf_no_text:
        warn(f"{len(es_pdf_no_text)} homilies have Spanish PDF URL but no text:")
        for r in es_pdf_no_text:
            print(f"        id={r['id']}  {r['date']}  {r['occasion']}")
    else:
        ok("Every Spanish PDF URL has corresponding text")

    if en_pdf_no_text:
        warn(f"{len(en_pdf_no_text)} homilies have English PDF URL but no text:")
        for r in en_pdf_no_text:
            print(f"        id={r['id']}  {r['date']}  {r['occasion']}")
    else:
        ok("Every English PDF URL has corresponding text")

    # Homilies with no text and no PDF URL (expected gaps)
    no_anything = conn.execute(
        "SELECT id, date, occasion FROM homilies "
        "WHERE (spanish_pdf_url IS NULL OR spanish_pdf_url = '') "
        "AND (spanish_text IS NULL OR spanish_text = '') "
        "AND (english_pdf_url IS NULL OR english_pdf_url = '') "
        "AND (english_text IS NULL OR english_text = '')"
    ).fetchall()
    if no_anything:
        print(f"\n  {DIM}{len(no_anything)} homilies have no PDFs or text at all (audio-only or missing):{RESET}")
        for r in no_anything:
            print(f"        id={r['id']}  {r['date']}  {r['occasion']}")

    # ── 2. SEARCH INDEX ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("2. SEARCH INDEX")
    print(f"{'='*60}")

    # Every Spanish text should have a folded version
    missing_fold = conn.execute(
        "SELECT id, date FROM homilies "
        "WHERE spanish_text IS NOT NULL AND spanish_text != '' "
        "AND (spanish_text_folded IS NULL OR spanish_text_folded = '')"
    ).fetchall()
    if missing_fold:
        fail(f"{len(missing_fold)} Spanish texts missing folded index:")
        for r in missing_fold:
            print(f"        id={r['id']}  {r['date']}")
    else:
        ok(f"All {es_text} Spanish texts have folded index")

    # Every Spanish text should have a word count
    missing_wc = conn.execute(
        "SELECT id, date FROM homilies "
        "WHERE spanish_text IS NOT NULL AND spanish_text != '' "
        "AND (spanish_word_count IS NULL OR spanish_word_count = 0)"
    ).fetchall()
    if missing_wc:
        fail(f"{len(missing_wc)} Spanish texts missing word count:")
        for r in missing_wc:
            print(f"        id={r['id']}  {r['date']}")
    else:
        ok(f"All {es_text} Spanish texts have word counts")

    # Verify word counts match actual text
    print()
    wc_mismatches = []
    rows = conn.execute(
        "SELECT id, date, spanish_text, spanish_word_count FROM homilies "
        "WHERE spanish_text IS NOT NULL AND spanish_text != '' AND spanish_word_count IS NOT NULL"
    ).fetchall()
    for r in rows:
        actual = len(re.findall(r'\w+', r['spanish_text'].lower(), re.UNICODE))
        if actual != r['spanish_word_count']:
            wc_mismatches.append((r['id'], r['date'], r['spanish_word_count'], actual))
    if wc_mismatches:
        fail(f"{len(wc_mismatches)} word count mismatches (stored vs actual):")
        for hid, date, stored, actual in wc_mismatches[:5]:
            print(f"        id={hid}  {date}  stored={stored}  actual={actual}")
        if len(wc_mismatches) > 5:
            print(f"        ... and {len(wc_mismatches) - 5} more")
    else:
        ok(f"All {len(rows)} word counts verified correct")

    # Verify folded text matches re-folding
    fold_mismatches = []
    rows = conn.execute(
        "SELECT id, date, spanish_text, spanish_text_folded FROM homilies "
        "WHERE spanish_text IS NOT NULL AND spanish_text != '' AND spanish_text_folded IS NOT NULL"
    ).fetchall()
    for r in rows:
        expected = fold_accents(r['spanish_text']).lower()
        if expected != r['spanish_text_folded']:
            fold_mismatches.append((r['id'], r['date']))
    if fold_mismatches:
        fail(f"{len(fold_mismatches)} folded text mismatches:")
        for hid, date in fold_mismatches[:5]:
            print(f"        id={hid}  {date}")
    else:
        ok(f"All {len(rows)} folded texts verified correct")

    # ── 3. FILE SYSTEM CONSISTENCY ───────────────────────────────
    print(f"\n{'='*60}")
    print("3. FILE SYSTEM CONSISTENCY")
    print(f"{'='*60}")

    # Check PDF paths in DB point to real files
    pdf_missing = []
    for col in ('spanish_pdf_path', 'english_pdf_path'):
        lang = col.split('_')[0]
        rows = conn.execute(f"SELECT id, date, {col} as path FROM homilies WHERE {col} IS NOT NULL AND {col} != ''").fetchall()
        for r in rows:
            full = PROJECT_ROOT / r['path']
            if not full.exists():
                pdf_missing.append((r['id'], r['date'], lang, r['path']))

    if pdf_missing:
        fail(f"{len(pdf_missing)} PDF paths in DB point to missing files:")
        for hid, date, lang, path in pdf_missing:
            print(f"        id={hid}  {date}  {lang}  {path}")
    else:
        ok("All PDF paths in DB point to existing files")

    # Check text files on disk match DB text
    # Match via pdf_path column, which stores the exact relative path
    txt_files = sorted(PROJECT_ROOT.glob('homilies/**/*.txt'))
    disk_mismatches = []
    disk_orphans = []
    for txt in txt_files:
        rel_txt = str(txt.relative_to(PROJECT_ROOT))
        lang = 'spanish' if 'spanish' in txt.stem else 'english'

        # Find DB row by matching the pdf_path (same name, .pdf instead of .txt)
        rel_pdf = rel_txt.replace('.txt', '.pdf')
        pdf_col = f"{lang}_pdf_path"
        text_col = f"{lang}_text"
        row = conn.execute(
            f"SELECT id, date, {text_col} as text FROM homilies WHERE {pdf_col} = ?",
            (rel_pdf,)
        ).fetchone()

        if row is None:
            disk_orphans.append(rel_txt)
            continue

        disk_text = txt.read_text(encoding='utf-8')
        if row['text'] is None or row['text'] == '':
            disk_mismatches.append((row['id'], row['date'], lang, 'on disk but not in DB'))
        elif disk_text.strip() != row['text'].strip():
            disk_mismatches.append((row['id'], row['date'], lang, 'content differs'))

    if disk_orphans:
        warn(f"{len(disk_orphans)} text files on disk with no matching DB row:")
        for p in disk_orphans:
            print(f"        {p}")
    if disk_mismatches:
        warn(f"{len(disk_mismatches)} text file/DB mismatches:")
        for hid, date, lang, reason in disk_mismatches:
            print(f"        id={hid}  {date}  {lang}  ({reason})")
    if not disk_orphans and not disk_mismatches:
        ok(f"All {len(txt_files)} text files on disk match DB content")

    # ── 4. DATE INTEGRITY ────────────────────────────────────────
    print(f"\n{'='*60}")
    print("4. DATE INTEGRITY")
    print(f"{'='*60}")

    date_range = conn.execute("SELECT MIN(date) as first, MAX(date) as last FROM homilies").fetchone()
    print(f"  Date range: {date_range['first']} to {date_range['last']}")

    out_of_range = conn.execute(
        "SELECT id, date FROM homilies WHERE date < '1977-01-01' OR date > '1980-04-01'"
    ).fetchall()
    if out_of_range:
        warn(f"{len(out_of_range)} homilies outside expected range (1977-01 to 1980-03):")
        for r in out_of_range:
            print(f"        id={r['id']}  {r['date']}")
    else:
        ok("All dates within expected range (1977–1980)")

    # Monthly distribution
    months = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, COUNT(*) as n "
        "FROM homilies GROUP BY month ORDER BY month"
    ).fetchall()
    month_counts = {r['month']: r['n'] for r in months}
    print(f"  Months covered: {len(months)}")

    sparse = [(m, n) for m, n in month_counts.items() if n < 2]
    dense = [(m, n) for m, n in month_counts.items() if n > 12]
    if sparse:
        print(f"  {DIM}Sparse months (< 2 homilies): {', '.join(f'{m}({n})' for m, n in sparse)}{RESET}")
    if dense:
        warn(f"Unusually dense months (> 12): {', '.join(f'{m}({n})' for m, n in dense)}")

    # Duplicate dates (expected for some — multiple homilies on same day)
    dupes = conn.execute(
        "SELECT date, COUNT(*) as n FROM homilies GROUP BY date HAVING n > 1 ORDER BY date"
    ).fetchall()
    if dupes:
        dupe_strs = ', '.join(f"{r['date']}({r['n']})" for r in dupes)
        print(f"  {DIM}Dates with multiple homilies: {len(dupes)} ({dupe_strs}){RESET}")

    # ── 5. TEXT QUALITY ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("5. TEXT QUALITY")
    print(f"{'='*60}")

    # Spanish text stats
    es_stats = conn.execute(
        "SELECT MIN(spanish_word_count) as min_wc, MAX(spanish_word_count) as max_wc, "
        "AVG(spanish_word_count) as avg_wc, SUM(spanish_word_count) as total_wc "
        "FROM homilies WHERE spanish_word_count IS NOT NULL"
    ).fetchone()
    print(f"  Spanish corpus: {es_stats['total_wc']:,} total words")
    print(f"  Word counts:    min={es_stats['min_wc']:,}  avg={int(es_stats['avg_wc']):,}  max={es_stats['max_wc']:,}")

    # Suspiciously short texts (< 500 words)
    short = conn.execute(
        "SELECT id, date, occasion, spanish_word_count FROM homilies "
        "WHERE spanish_word_count IS NOT NULL AND spanish_word_count < 500 "
        "ORDER BY spanish_word_count"
    ).fetchall()
    if short:
        warn(f"{len(short)} Spanish texts under 500 words (possible extraction issues):")
        for r in short:
            print(f"        id={r['id']}  {r['date']}  {r['spanish_word_count']} words  {r['occasion']}")
    else:
        ok("No suspiciously short Spanish texts")

    # Suspiciously short English texts (< 200 chars)
    short_en = conn.execute(
        "SELECT id, date, occasion, LENGTH(english_text) as len FROM homilies "
        "WHERE english_text IS NOT NULL AND english_text != '' AND LENGTH(english_text) < 1000 "
        "ORDER BY len"
    ).fetchall()
    if short_en:
        warn(f"{len(short_en)} English texts under 1000 chars:")
        for r in short_en:
            print(f"        id={r['id']}  {r['date']}  {r['len']} chars  {r['occasion']}")
    else:
        ok("No suspiciously short English texts")

    # ── 6. FLAGS ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("6. DATA FLAGS")
    print(f"{'='*60}")

    flag_stats = conn.execute(
        "SELECT status, COUNT(*) as n FROM flags GROUP BY status"
    ).fetchall()
    if flag_stats:
        for r in flag_stats:
            print(f"  {r['status']}: {r['n']}")
        open_flags = conn.execute(
            "SELECT f.id, f.homily_id, h.date, f.comment FROM flags f "
            "JOIN homilies h ON f.homily_id = h.id WHERE f.status = 'open' ORDER BY h.date"
        ).fetchall()
        if open_flags:
            print()
            warn(f"{len(open_flags)} open flags:")
            for f in open_flags:
                comment = f['comment'][:80] + ('...' if len(f['comment']) > 80 else '')
                print(f"        flag={f['id']}  homily={f['homily_id']}  {f['date']}  {comment}")
    else:
        ok("No flags in database")

    # ── SUMMARY ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if problems:
        print(f"  {RED}{len(problems)} problem(s){RESET}")
        for p in problems:
            print(f"    - {p}")
    if warnings:
        print(f"  {YELLOW}{len(warnings)} warning(s){RESET}")
    if not problems and not warnings:
        print(f"  {GREEN}All checks passed{RESET}")
    print()

    conn.close()
    return 1 if problems else 0


if __name__ == '__main__':
    exit(main())
