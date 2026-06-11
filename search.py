"""
Search module for Romero homilies corpus.

Provides word/phrase frequency search across Spanish and English texts,
with accent-insensitive matching and monthly aggregation.

Uses pre-folded text and pre-computed word counts from the database for
fast regex-based search. Run scripts/build_search_index.py to populate
the index columns for both languages.
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


def tokenize_query(text):
    """Split query text into lowercase tokens, preserving * wildcards."""
    return re.findall(r'[\w*]+', text.lower(), re.UNICODE)


def _token_pattern(token):
    """Convert a single search token to a regex fragment.

    Plain token:  re.escape('violencia') -> 'violencia'
    Wildcard:     'liber*' -> 'liber\\w*', '*cion' -> '\\w*cion'
    """
    if '*' in token:
        parts = token.split('*')
        return r'\w*'.join(re.escape(p) for p in parts)
    return re.escape(token)


def _build_pattern(search_tokens):
    """Build a compiled regex pattern from search tokens.

    Single word: r'\\bviolencia\\b'
    Phrase:      r'\\bpueblo\\W+de\\W+dios\\b'
    Wildcard:    r'\\bliber\\w*\\b'
    """
    parts = [_token_pattern(t) for t in search_tokens]
    return re.compile(r'\b' + r'\W+'.join(parts) + r'\b', re.UNICODE)


# Sentence terminators for snippet extraction. Newlines count as boundaries
# because text cleaning left them only at paragraph breaks.
_SENTENCE_ENDS = '.!?\n'

# Max characters kept on each side of a match within its sentence; beyond
# this the snippet is cut at a word boundary and ellipsized.
SNIPPET_CAP = 200


def _sentence_bounds(text, start, end):
    """Find the boundaries of the sentence containing text[start:end].

    Returns (s, e) where s is the first character of the sentence (after any
    whitespace following the previous terminator — leading ¿/¡ are kept) and
    e is just past the sentence's own terminator (or at the newline/text end).
    """
    s = start
    while s > 0 and text[s - 1] not in _SENTENCE_ENDS:
        s -= 1
    while s < start and text[s].isspace():
        s += 1

    e = end
    while e < len(text) and text[e] not in _SENTENCE_ENDS:
        e += 1
    if e < len(text) and text[e] != '\n':
        e += 1  # include the . ! ? itself
    return s, e


def extract_snippets(original_text, folded_text, pattern, cap=SNIPPET_CAP):
    """
    Extract sentence snippets for every pattern match, with highlight offsets.

    The pattern is matched against folded_text; offsets are applied to
    original_text to recover the accented original. This relies on the folded
    text being character-for-character the same length as the original (true
    for the NFD accent-strip + lowercase folding in build_search_index.py).

    Matches that fall in the same sentence are merged into one snippet with
    multiple highlight ranges. Sentences longer than `cap` characters on
    either side of their matches are cut at a word boundary and ellipsized.

    Returns a list of {'text': str, 'highlights': [[start, end], ...]} in
    document order, with highlight offsets relative to the snippet text.
    """
    groups = []
    for m in pattern.finditer(folded_text):
        ss, se = _sentence_bounds(original_text, m.start(), m.end())
        if groups and ss < groups[-1]['end']:
            groups[-1]['matches'].append((m.start(), m.end()))
            groups[-1]['end'] = max(groups[-1]['end'], se)
        else:
            groups.append({'start': ss, 'end': se, 'matches': [(m.start(), m.end())]})

    snippets = []
    for g in groups:
        s, e = g['start'], g['end']
        first_start = g['matches'][0][0]
        last_end = g['matches'][-1][1]

        prefix = suffix = ''
        if first_start - s > cap:
            s = first_start - cap
            while s < first_start and not original_text[s - 1].isspace():
                s += 1
            prefix = '…'
        if e - last_end > cap:
            e = last_end + cap
            while e > last_end and not original_text[e - 1].isspace():
                e -= 1
            suffix = '…'

        # Trim whitespace at the snippet edges
        while s < first_start and original_text[s].isspace():
            s += 1
        while e > last_end and original_text[e - 1].isspace():
            e -= 1

        snippets.append({
            'text': prefix + original_text[s:e] + suffix,
            'highlights': [[ms - s + len(prefix), me - s + len(prefix)]
                           for ms, me in g['matches']],
        })

    return snippets


def search_corpus(term, db_path='romero.db', accent_sensitive=False, language='es'):
    """
    Search homily texts for a word or phrase.

    Args:
        language: 'es' for Spanish (default), 'en' for English

    Returns a dict with:
      term: the original search term
      tokens: the normalized search tokens
      elapsed: search time in seconds
      total_count: total occurrences across corpus
      total_homilies: number of homilies with at least one match
      months: OrderedDict of YYYY-MM -> {count, total_words, rate, homilies}
    """
    start = time.time()

    # Map language code to column names
    lang_prefix = 'spanish' if language == 'es' else 'english'
    folded_col = f'{lang_prefix}_text_folded'
    count_col = f'{lang_prefix}_word_count'
    title_col = f'{lang_prefix}_title'

    normalize = fold_accents if not accent_sensitive else lambda t: t
    search_tokens = tokenize_query(normalize(term))

    if not search_tokens:
        return {'term': term, 'tokens': [], 'elapsed': 0,
                'total_count': 0, 'total_homilies': 0, 'months': OrderedDict()}

    # Reject bare wildcards (e.g. just "*") — they'd match every word
    for tok in search_tokens:
        if tok.replace('*', '') == '':
            return {'term': term, 'tokens': search_tokens, 'elapsed': 0,
                    'error': 'Wildcard * must be combined with letters (e.g. liber*)',
                    'total_count': 0, 'total_homilies': 0, 'months': OrderedDict()}

    pattern = _build_pattern(search_tokens)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f'SELECT id, date, occasion, {title_col}, {folded_col}, '
        f'{count_col}, detail_url '
        f'FROM homilies WHERE {folded_col} IS NOT NULL ORDER BY date'
    ).fetchall()
    conn.close()

    # Search each homily, aggregate by month
    months = OrderedDict()
    total_count = 0
    total_homilies = 0

    for row in rows:
        month = row['date'][:7]

        # Count matches using pre-folded text and compiled regex
        matches = pattern.findall(row[folded_col])
        count = len(matches)

        if month not in months:
            months[month] = {'count': 0, 'total_words': 0, 'num_homilies': 0, 'homilies': []}
        months[month]['total_words'] += row[count_col]
        months[month]['num_homilies'] += 1

        if count > 0:
            months[month]['count'] += count
            months[month]['homilies'].append({
                'id': row['id'],
                'date': row['date'],
                'title': row[title_col] or row['occasion'] or '(untitled)',
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
