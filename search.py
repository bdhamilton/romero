"""
Search module for Romero homilies corpus.

Provides word/phrase frequency search across Spanish texts,
with accent-insensitive matching and monthly aggregation.
"""

import sqlite3
import time
import unicodedata
import re
from collections import OrderedDict


def fold_accents(text):
    """Strip diacritical marks (á→a, ñ→n, etc.) for accent-insensitive matching."""
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')


def tokenize(text):
    """Split text into lowercase word tokens."""
    return re.findall(r'\w+', text.lower(), re.UNICODE)


def search_corpus(term, db_path='romero.db', accent_sensitive=False):
    """
    Search all Spanish homily texts for a word or phrase.

    Returns a dict with:
      term: the original search term
      tokens: the normalized search tokens
      elapsed: search time in seconds
      total_count: total occurrences across corpus
      total_homilies: number of homilies with at least one match
      months: OrderedDict of YYYY-MM -> {count, total_words, rate, homilies}
    """
    start = time.time()

    normalize = fold_accents if not accent_sensitive else lambda t: t
    search_tokens = tokenize(normalize(term))

    if not search_tokens:
        return {'term': term, 'tokens': [], 'elapsed': 0,
                'total_count': 0, 'total_homilies': 0, 'months': OrderedDict()}

    n = len(search_tokens)

    # Fetch all Spanish texts
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT id, date, occasion, spanish_title, spanish_text, detail_url '
        'FROM homilies WHERE spanish_text IS NOT NULL ORDER BY date'
    ).fetchall()
    conn.close()

    # Search each homily, aggregate by month
    months = OrderedDict()
    total_count = 0
    total_homilies = 0

    for row in rows:
        text = row['spanish_text']
        month = row['date'][:7]
        tokens = tokenize(normalize(text))
        word_count = len(tokens)

        # Count phrase matches (works for single words too)
        count = 0
        for i in range(len(tokens) - n + 1):
            if tokens[i:i + n] == search_tokens:
                count += 1

        if month not in months:
            months[month] = {'count': 0, 'total_words': 0, 'num_homilies': 0, 'homilies': []}
        months[month]['total_words'] += word_count
        months[month]['num_homilies'] += 1

        if count > 0:
            months[month]['count'] += count
            months[month]['homilies'].append({
                'id': row['id'],
                'date': row['date'],
                'title': row['spanish_title'] or row['occasion'] or '(untitled)',
                'detail_url': row['detail_url'],
                'count': count,
            })
            total_count += count
            total_homilies += 1

    # Compute normalized rates for each month
    for data in months.values():
        if data['total_words'] > 0:
            data['per_10k_words'] = (data['count'] / data['total_words']) * 10_000
        else:
            data['per_10k_words'] = 0.0
        if data['num_homilies'] > 0:
            data['per_homily'] = data['count'] / data['num_homilies']
        else:
            data['per_homily'] = 0.0

    elapsed = time.time() - start

    return {
        'term': term,
        'tokens': search_tokens,
        'elapsed': elapsed,
        'total_count': total_count,
        'total_homilies': total_homilies,
        'months': months,
    }
