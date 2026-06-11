"""
Tests for keyword-in-context snippet extraction and the /api/snippets endpoint.

Run from the project root: python -m pytest tests/
The API tests use the real romero.db, same as the app.
"""

import sqlite3

import pytest

import app as app_module
from search import (fold_accents, tokenize_query, _build_pattern,
                    extract_snippets, search_corpus)


def fold(text):
    """Same folding as scripts/build_search_index.py."""
    return fold_accents(text).lower()


def make_pattern(term):
    return _build_pattern(tokenize_query(fold(term)))


def snips(text, term):
    return extract_snippets(text, fold(text), make_pattern(term))


SAMPLE = (
    "La iglesia vive. ¿Dónde está la justicia? "
    "La liberación del pueblo es obra de Dios. "
    "El pueblo sufre y el pueblo espera.\n"
    "El pueblo de Dios camina en la historia."
)


def assert_highlights_match(snippets, term):
    """Every highlight range, applied to the snippet text, matches the pattern."""
    pattern = make_pattern(term)
    for sn in snippets:
        for start, end in sn['highlights']:
            piece = sn['text'][start:end]
            m = pattern.search(fold(piece))
            assert m and m.group(0) == fold(piece), (
                f"highlight {piece!r} does not match pattern for {term!r}")


def test_accented_original_is_highlighted():
    result = snips(SAMPLE, 'liberacion')
    assert len(result) == 1
    assert result[0]['text'] == 'La liberación del pueblo es obra de Dios.'
    s, e = result[0]['highlights'][0]
    assert result[0]['text'][s:e] == 'liberación'


def test_inverted_question_mark_kept_with_sentence():
    result = snips(SAMPLE, 'justicia')
    assert len(result) == 1
    assert result[0]['text'] == '¿Dónde está la justicia?'


def test_matches_in_same_sentence_merge():
    result = snips(SAMPLE, 'pueblo')
    # 4 matches in 3 sentences: the double-"pueblo" sentence merges
    assert len(result) == 3
    counts = [len(sn['highlights']) for sn in result]
    assert counts == [1, 2, 1]
    assert result[1]['text'] == 'El pueblo sufre y el pueblo espera.'
    assert_highlights_match(result, 'pueblo')


def test_total_highlights_equal_corpus_count():
    pattern = make_pattern('pueblo')
    expected = len(pattern.findall(fold(SAMPLE)))
    result = snips(SAMPLE, 'pueblo')
    assert sum(len(sn['highlights']) for sn in result) == expected == 4


def test_newline_is_sentence_boundary():
    # Last sentence sits after a paragraph break with no preceding period
    result = snips(SAMPLE, 'camina')
    assert result[0]['text'] == 'El pueblo de Dios camina en la historia.'


def test_long_sentence_is_capped_at_word_boundaries():
    words = 'palabra ' * 100
    text = words + 'pueblo ' + words  # ~1,600 chars, no punctuation
    result = snips(text, 'pueblo')
    assert len(result) == 1
    sn = result[0]
    assert sn['text'].startswith('…') and sn['text'].endswith('…')
    # 200-char cap per side, plus the match and two ellipses
    assert len(sn['text']) <= 200 * 2 + len('pueblo') + 2
    # Cut at word boundaries: no partial 'palabra' fragments at the edges
    inner = sn['text'].strip('…').strip()
    assert inner.split(' ')[0] == 'palabra'
    assert inner.split(' ')[-1] == 'palabra'
    s, e = sn['highlights'][0]
    assert sn['text'][s:e] == 'pueblo'


def test_phrase_highlight_bounds():
    result = snips(SAMPLE, 'pueblo de dios')
    assert len(result) == 1
    s, e = result[0]['highlights'][0]
    assert result[0]['text'][s:e] == 'pueblo de Dios'


def test_wildcard_highlight_bounds():
    text = 'La liberación y la libertad son del Señor.'
    result = snips(text, 'liber*')
    assert len(result) == 1
    pieces = [result[0]['text'][s:e] for s, e in result[0]['highlights']]
    assert pieces == ['liberación', 'libertad']


def test_no_matches_returns_empty():
    assert snips(SAMPLE, 'inexistente') == []


# ---------------------------------------------------------------------------
# API tests (against the real romero.db)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def db():
    conn = sqlite3.connect(app_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def test_api_unknown_homily_404(client):
    r = client.get('/api/snippets?homily_id=999999&term=pueblo')
    assert r.status_code == 404


def test_api_missing_language_404(client):
    conn = db()
    row = conn.execute(
        'SELECT id FROM homilies WHERE spanish_text IS NULL LIMIT 1').fetchone()
    conn.close()
    assert row is not None, 'expected a homily without Spanish text'
    r = client.get(f'/api/snippets?homily_id={row["id"]}&term=pueblo&lang=es')
    assert r.status_code == 404


def test_api_empty_term_400(client):
    r = client.get('/api/snippets?homily_id=1&term=')
    assert r.status_code == 400


def test_api_bare_wildcard_400(client):
    r = client.get('/api/snippets?homily_id=1&term=*')
    assert r.status_code == 400


def test_api_count_matches_search_api(client):
    """The snippet count for a homily equals the chart's per-homily count."""
    result = search_corpus('pueblo', db_path=app_module.DB_PATH)
    # Find a homily with a healthy number of matches
    homily = max(
        (h for m in result['months'].values() for h in m['homilies']),
        key=lambda h: h['count'])
    r = client.get(f'/api/snippets?homily_id={homily["id"]}&term=pueblo')
    assert r.status_code == 200
    data = r.get_json()
    assert data['count'] == homily['count']
    assert sum(len(sn['highlights']) for sn in data['snippets']) == homily['count']
    # Spot-check highlight integrity on real text
    for sn in data['snippets'][:10]:
        for s, e in sn['highlights']:
            assert fold(sn['text'][s:e]) == 'pueblo'
