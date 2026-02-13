#!/usr/bin/env python3
"""
Command-line ngram search tool for Romero homilies.

Usage:
    python ngram.py pueblo
    python ngram.py "pueblo de dios"
    python ngram.py iglesia --accent-sensitive
    python ngram.py violencia --top 10
    python ngram.py pueblo --norm words
    python ngram.py justicia --norm homilies
    python ngram.py justice --lang en
"""

import argparse
import sys
from search import search_corpus


def bar(value, max_value, width=40):
    """Render a proportional bar using block characters."""
    if max_value == 0:
        return ''
    filled = round((value / max_value) * width)
    return '\u2588' * filled


def main():
    parser = argparse.ArgumentParser(
        description='Search Romero homilies for word/phrase frequency over time.'
    )
    parser.add_argument('term', help='Word or phrase to search for')
    parser.add_argument('--accent-sensitive', action='store_true',
                        help='Match accents exactly (default: accent-insensitive)')
    parser.add_argument('--top', type=int, default=5,
                        help='Number of top homilies to show (default: 5)')
    parser.add_argument('--norm', choices=['words', 'homilies'], default=None,
                        help='Normalize: "words" = per 10k words, "homilies" = per homily')
    parser.add_argument('--lang', choices=['es', 'en'], default='es',
                        help='Language: "es" = Spanish (default), "en" = English')
    parser.add_argument('--db', default='romero.db',
                        help='Path to database (default: romero.db)')
    args = parser.parse_args()

    result = search_corpus(args.term, db_path=args.db,
                           accent_sensitive=args.accent_sensitive,
                           language=args.lang)

    if not result['tokens']:
        print(f'No valid search tokens in: "{args.term}"')
        sys.exit(1)

    # Header
    token_str = ' '.join(result['tokens'])
    mode = 'accent-sensitive' if args.accent_sensitive else 'accent-insensitive'
    lang_label = 'Spanish' if args.lang == 'es' else 'English'
    print(f'\nSearching {lang_label} corpus for: "{args.term}" [{token_str}] ({mode})')
    print(f'Found {result["total_count"]} occurrences in '
          f'{result["total_homilies"]} homilies ({result["elapsed"]:.2f}s)\n')

    if result['total_count'] == 0:
        print('No matches found.')
        return

    # Monthly chart
    months = result['months']

    if args.norm == 'words':
        values = {m: d['per_10k_words'] for m, d in months.items()}
        label = 'per 10k words'
        fmt = lambda val, count: f'{val:>6.1f}  ({count:>3d})'
    elif args.norm == 'homilies':
        values = {m: d['per_homily'] for m, d in months.items()}
        label = 'per homily'
        fmt = lambda val, count: f'{val:>6.1f}  ({count:>3d})'
    else:
        values = {m: d['count'] for m, d in months.items()}
        label = 'raw count'
        fmt = lambda val, count: f'{count:>4d}'

    max_val = max(values.values()) if values else 0

    print(f'Monthly distribution ({label}):')
    for month, data in months.items():
        val = values[month]
        b = bar(val, max_val)
        print(f'  {month}  {b:<40s}  {fmt(val, data["count"])}')

    # Top homilies
    all_homilies = []
    for data in months.values():
        all_homilies.extend(data['homilies'])
    all_homilies.sort(key=lambda h: h['count'], reverse=True)

    print(f'\nTop {args.top} homilies:')
    for h in all_homilies[:args.top]:
        print(f'  {h["date"]}  {h["count"]:>3d}x  {h["title"]}')

    print()


if __name__ == '__main__':
    main()
