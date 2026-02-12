#!/usr/bin/env python3
"""
Text quality check for the Romero homilies corpus.

Scans all extracted texts for common PDF extraction artifacts:
  1. Residual headers/footers that survived cleaning
  2. Concatenated words (missing spaces)
  3. Encoding artifacts and unusual characters
  4. Suspicious short lines or fragments
  5. Duplicate passages within a single text
  6. Footnote number density

Usage:
    python scripts/text_quality.py
    python scripts/text_quality.py --verbose     # show all flagged lines
    python scripts/text_quality.py --id 47       # check a single homily
"""

import argparse
import re
import sqlite3
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'romero.db'

RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def check_residual_headers(text, lang):
    """Find lines that look like running headers or footers."""
    issues = []

    for pattern, desc in [
        (r'‡\s*Ciclo\s+[ABC].*?‡', 'Spanish running header (‡ Ciclo...)'),
        (r'‡\s*Homilías\s+de\s+Monseñor\s+Romero\s*‡', 'Spanish running header (‡ Homilías...)'),
        (r'St Oscar Romero,', 'English running header (St Oscar Romero)'),
        (r'Read or listen to the homilies', 'English running footer'),
        (r'romerotrust\.org\.uk', 'Romero Trust URL (footer artifact)'),
    ]:
        for m in re.finditer(pattern, text):
            # Get the line containing the match
            start = text.rfind('\n', 0, m.start()) + 1
            end = text.find('\n', m.end())
            if end == -1:
                end = len(text)
            line = text[start:end].strip()
            issues.append(('header', desc, line[:120]))

    return issues


def check_long_tokens(text):
    """Find suspiciously long tokens (likely concatenated words)."""
    issues = []
    tokens = re.findall(r'\S+', text)
    for token in tokens:
        # Strip punctuation for length check
        clean = re.sub(r'[^\w]', '', token)
        if len(clean) > 30:
            # Skip URLs
            if token.startswith('http') or token.startswith('www'):
                continue
            issues.append(('concat', f'Long token ({len(clean)} chars)', token[:80]))
    return issues


def check_encoding(text):
    """Find encoding artifacts and unusual characters."""
    issues = []

    # Unicode replacement character
    if '\ufffd' in text:
        count = text.count('\ufffd')
        issues.append(('encoding', f'Unicode replacement char (U+FFFD) x{count}', ''))

    # Control characters (except newline, tab)
    for i, ch in enumerate(text):
        if ord(ch) < 32 and ch not in '\n\t\r':
            context = text[max(0, i-20):i+20].replace('\n', '\\n')
            issues.append(('encoding', f'Control char U+{ord(ch):04X}', context))
            break  # one is enough to flag

    # Sequences of special chars that suggest garbled text
    garbled = re.findall(r'[^\w\s.,;:!?¡¿\'\"()\-–—\[\]/&@#%°ª…«»\n]{3,}', text)
    for g in garbled[:3]:
        issues.append(('encoding', 'Unusual character sequence', repr(g)))

    return issues


def check_short_lines(text):
    """Find suspicious short lines that might be artifacts."""
    issues = []
    lines = text.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            continue
        # Single characters (not paragraph markers or list items)
        if len(stripped) == 1 and stripped not in '—–-•·':
            issues.append(('fragment', 'Single-character line', f'Line {i+1}: {repr(stripped)}'))
        # Bare numbers that look like page numbers (not at start/end)
        if re.match(r'^\d{1,3}$', stripped) and 5 < i < len(lines) - 5:
            issues.append(('fragment', 'Possible page number', f'Line {i+1}: "{stripped}"'))

    return issues


def check_duplicate_passages(text):
    """Find repeated passages (extraction artifacts)."""
    issues = []
    # Split into sentences (roughly)
    sentences = re.split(r'[.!?]\s+', text)
    # Only check substantial sentences
    sentences = [s.strip() for s in sentences if len(s.strip()) > 80]

    seen = Counter(sentences)
    for sent, count in seen.items():
        if count > 1:
            issues.append(('duplicate', f'Passage repeated {count}x', sent[:100] + '...'))

    return issues


def check_footnote_noise(text):
    """Check for high density of bare footnote numbers embedded in text."""
    issues = []
    # Bare digits surrounded by word characters: "salvación1 del"
    footnotes = re.findall(r'[a-záéíóúñü][,.]?\d{1,2}(?:\s|[A-ZÁÉÍÓÚÑÜ])', text)
    if len(footnotes) > 20:
        issues.append(('footnotes', f'{len(footnotes)} likely inline footnote markers',
                       ', '.join(footnotes[:5]) + '...'))
    return issues


def check_homily(hid, date, text, lang, verbose=False):
    """Run all checks on a single homily text. Returns list of issues."""
    all_issues = []
    all_issues.extend(check_residual_headers(text, lang))
    all_issues.extend(check_long_tokens(text))
    all_issues.extend(check_encoding(text))
    all_issues.extend(check_short_lines(text))
    all_issues.extend(check_duplicate_passages(text))
    all_issues.extend(check_footnote_noise(text))
    return all_issues


def main():
    parser = argparse.ArgumentParser(description='Text quality check for Romero corpus')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show all flagged lines')
    parser.add_argument('--id', type=int, help='Check a single homily by ID')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    results = {}  # category -> list of (id, date, lang, issues)

    for lang, col in [('spanish', 'spanish_text'), ('english', 'english_text')]:
        if args.id:
            query = f"SELECT id, date, {col} as text FROM homilies WHERE id = ? AND {col} IS NOT NULL AND {col} != ''"
            rows = conn.execute(query, (args.id,)).fetchall()
        else:
            query = f"SELECT id, date, {col} as text FROM homilies WHERE {col} IS NOT NULL AND {col} != ''"
            rows = conn.execute(query).fetchall()

        for row in rows:
            issues = check_homily(row['id'], row['date'], row['text'], lang, args.verbose)
            if issues:
                results.setdefault(row['id'], []).append((lang, row['date'], issues))

    conn.close()

    # ── Report ───────────────────────────────────────────────────
    # Aggregate by category
    category_counts = Counter()
    category_homilies = {}
    for hid, lang_issues in results.items():
        for lang, date, issues in lang_issues:
            for cat, desc, detail in issues:
                category_counts[cat] += 1
                category_homilies.setdefault(cat, set()).add(hid)

    print(f"\n{'='*60}")
    print("TEXT QUALITY REPORT")
    print(f"{'='*60}\n")

    if not category_counts:
        print(f"  {GREEN}No issues found.{RESET}\n")
        return

    # Summary by category
    cat_labels = {
        'header': 'Residual headers/footers',
        'concat': 'Concatenated words (long tokens)',
        'encoding': 'Encoding artifacts',
        'fragment': 'Suspicious fragments',
        'duplicate': 'Duplicate passages',
        'footnotes': 'Footnote marker noise',
    }
    print(f"{BOLD}Issue summary:{RESET}")
    for cat in ['header', 'concat', 'encoding', 'fragment', 'duplicate', 'footnotes']:
        if cat in category_counts:
            n_issues = category_counts[cat]
            n_homilies = len(category_homilies[cat])
            print(f"  {YELLOW}{cat_labels.get(cat, cat)}{RESET}: {n_issues} instances across {n_homilies} homilies")
    print()

    # Detail by homily
    print(f"{BOLD}Detail by homily:{RESET}\n")
    for hid in sorted(results.keys()):
        for lang, date, issues in results[hid]:
            # Group issues by category
            by_cat = {}
            for cat, desc, detail in issues:
                by_cat.setdefault(cat, []).append((desc, detail))

            print(f"  {BOLD}id={hid}  {date}  ({lang}){RESET}")
            for cat in ['header', 'concat', 'encoding', 'fragment', 'duplicate', 'footnotes']:
                if cat not in by_cat:
                    continue
                items = by_cat[cat]
                label = cat_labels.get(cat, cat)
                if len(items) <= 3 or args.verbose:
                    for desc, detail in items:
                        if detail:
                            print(f"    {YELLOW}{label}{RESET}: {desc}")
                            print(f"      {DIM}{detail}{RESET}")
                        else:
                            print(f"    {YELLOW}{label}{RESET}: {desc}")
                else:
                    # Summarize
                    for desc, detail in items[:2]:
                        if detail:
                            print(f"    {YELLOW}{label}{RESET}: {desc}")
                            print(f"      {DIM}{detail}{RESET}")
                        else:
                            print(f"    {YELLOW}{label}{RESET}: {desc}")
                    print(f"    {DIM}... and {len(items) - 2} more {label.lower()}{RESET}")
            print()

    total_homilies = len(results)
    total_issues = sum(category_counts.values())
    print(f"{'='*60}")
    print(f"Total: {total_issues} issues across {total_homilies} homilies")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
