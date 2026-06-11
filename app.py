#!/usr/bin/env python3
"""
Flask web app for Romero Text Explorer and homily browsing.
"""

from flask import Flask, render_template, abort, request, jsonify, redirect, url_for
import sqlite3
from pathlib import Path
from search import (search_corpus, extract_snippets, fold_accents,
                    tokenize_query, _build_pattern)

app = Flask(__name__)

DB_PATH = 'romero.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def ngram_viewer():
    """Ngram viewer — main page."""
    return render_template('ngram.html')


@app.route('/browse')
def browse():
    """Show all homilies in a table."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            id,
            date,
            occasion,
            english_title,
            spanish_title,
            biblical_references,
            spanish_pdf_url,
            english_pdf_url,
            detail_url
        FROM homilies
        ORDER BY date ASC
    ''')
    homilies = cursor.fetchall()

    flag_rows = cursor.execute('''
        SELECT f.homily_id, f.comment,
               h.date, h.spanish_title, h.english_title, h.occasion
        FROM flags f
        JOIN homilies h ON h.id = f.homily_id
        WHERE f.status = 'open'
        ORDER BY h.date ASC
    ''').fetchall()

    conn.close()

    # Group flags by homily
    flagged = {}
    for row in flag_rows:
        hid = row['homily_id']
        if hid not in flagged:
            flagged[hid] = {
                'homily_id': hid,
                'date': row['date'],
                'title': row['spanish_title'] or row['english_title'] or row['occasion'],
                'comments': [],
            }
        flagged[hid]['comments'].append(row['comment'])
    flags = list(flagged.values())

    return render_template('index.html', homilies=homilies, flags=flags)


@app.route('/api/search')
def api_search():
    """JSON API for ngram search."""
    term = request.args.get('term', '').strip()
    accent_sensitive = request.args.get('accent_sensitive', '0') == '1'
    lang = request.args.get('lang', 'es')
    if lang not in ('es', 'en'):
        lang = 'es'

    if not term:
        return jsonify({'error': 'No search term provided'}), 400

    result = search_corpus(term, db_path=DB_PATH, accent_sensitive=accent_sensitive, language=lang)

    if 'error' in result:
        return jsonify({'error': result['error']}), 400

    # Convert OrderedDict to list for JSON serialization
    months = []
    for month, data in result['months'].items():
        months.append({
            'month': month,
            'count': data['count'],
            'total_words': data['total_words'],
            'num_homilies': data['num_homilies'],
            'per_10k_words': round(data['per_10k_words'], 2),
            'per_homily': round(data['per_homily'], 2),
            'homilies': data['homilies'],
        })

    return jsonify({
        'term': result['term'],
        'tokens': result['tokens'],
        'elapsed': round(result['elapsed'], 3),
        'total_count': result['total_count'],
        'total_homilies': result['total_homilies'],
        'months': months,
    })


@app.route('/api/snippets')
def api_snippets():
    """JSON API for keyword-in-context snippets from a single homily."""
    homily_id = request.args.get('homily_id', type=int)
    term = request.args.get('term', '').strip()
    accent_sensitive = request.args.get('accent_sensitive', '0') == '1'
    lang = request.args.get('lang', 'es')
    if lang not in ('es', 'en'):
        lang = 'es'

    if homily_id is None:
        return jsonify({'error': 'No homily_id provided'}), 400
    if not term:
        return jsonify({'error': 'No search term provided'}), 400

    # Normalize and validate the term exactly as search_corpus does, so
    # snippet counts always agree with the chart's counts.
    normalize = fold_accents if not accent_sensitive else lambda t: t
    tokens = tokenize_query(normalize(term))
    if not tokens:
        return jsonify({'error': 'No search term provided'}), 400
    for tok in tokens:
        if tok.replace('*', '') == '':
            return jsonify(
                {'error': 'Wildcard * must be combined with letters (e.g. liber*)'}), 400
    pattern = _build_pattern(tokens)

    lang_prefix = 'spanish' if lang == 'es' else 'english'
    conn = get_db()
    row = conn.execute(
        f'SELECT {lang_prefix}_text AS text, {lang_prefix}_text_folded AS folded '
        'FROM homilies WHERE id = ?', (homily_id,)
    ).fetchone()
    conn.close()

    if row is None or not row['text'] or not row['folded']:
        return jsonify({'error': 'Homily not found or has no text in this language'}), 404

    snippets = extract_snippets(row['text'], row['folded'], pattern)
    return jsonify({
        'homily_id': homily_id,
        'term': term,
        'count': sum(len(s['highlights']) for s in snippets),
        'snippets': snippets,
    })


@app.route('/homily/<int:homily_id>/flag', methods=['GET', 'POST'])
def flag_homily(homily_id):
    """Flag a data issue on a homily."""
    conn = get_db()

    homily = conn.execute(
        'SELECT * FROM homilies WHERE id = ?', (homily_id,)
    ).fetchone()
    if not homily:
        conn.close()
        abort(404)

    if request.method == 'POST':
        comment = request.form.get('comment', '').strip()
        if comment:
            conn.execute(
                'INSERT INTO flags (homily_id, comment) VALUES (?, ?)',
                (homily_id, comment)
            )
            conn.commit()
        conn.close()
        return redirect(url_for('flag_homily', homily_id=homily_id))

    flags = conn.execute(
        'SELECT * FROM flags WHERE homily_id = ? ORDER BY created_at DESC',
        (homily_id,)
    ).fetchall()

    conn.close()
    return render_template('flag.html', homily=homily, flags=flags)


if __name__ == '__main__':
    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        print("Run build_database.py first")
        exit(1)

    print("Starting Romero Text Explorer")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=False, port=5000)
