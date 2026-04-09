#!/usr/bin/env python3
"""
Flask web app for Romero Text Explorer and homily browsing.
"""

import hashlib
import secrets
import sqlite3
import sys
from pathlib import Path

from flask import Flask, render_template, abort, request, jsonify, redirect, url_for
from search import search_corpus

app = Flask(__name__)

DB_PATH = 'romero.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- Analytics ---------------------------------------------------------------
# Lightweight, privacy-respecting traffic tracking. Stored in the same SQLite
# DB as the rest of the app. No cookies, no client-side JS, no third parties.
#
# Distinct users are counted via a salted hash of IP + User-Agent. The salt is
# generated once on first run and never rotates, so returning visitors collide
# on the same hash across time (which is what we want). Privacy relies on the
# DB staying on the server: the hash is not reversible without the salt.

_ANALYTICS_SALT = None

_BOT_UA_SUBSTRINGS = (
    'bot', 'crawl', 'spider', 'slurp', 'bingpreview', 'mediapartners',
    'headless', 'monitor', 'pingdom', 'uptimerobot', 'ahrefs', 'semrush',
    'facebookexternalhit', 'python-requests', 'curl/', 'wget/',
)


def _init_analytics():
    """Create analytics tables and generate a persistent salt on first run."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS analytics_meta (
          key   TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pageviews (
          ts           TEXT NOT NULL DEFAULT (datetime('now')),
          path         TEXT NOT NULL,
          visitor_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS searches (
          ts           TEXT NOT NULL DEFAULT (datetime('now')),
          term         TEXT NOT NULL,
          lang         TEXT NOT NULL,
          results      INTEGER,
          visitor_hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_pageviews_ts ON pageviews(ts);
        CREATE INDEX IF NOT EXISTS idx_pageviews_hash ON pageviews(visitor_hash);
        CREATE INDEX IF NOT EXISTS idx_searches_ts ON searches(ts);
        CREATE INDEX IF NOT EXISTS idx_searches_hash ON searches(visitor_hash);
    ''')
    row = conn.execute(
        "SELECT value FROM analytics_meta WHERE key = 'salt'"
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO analytics_meta (key, value) VALUES ('salt', ?)",
            (secrets.token_hex(32),),
        )
        conn.commit()
    conn.close()


def _get_salt():
    global _ANALYTICS_SALT
    if _ANALYTICS_SALT is None:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT value FROM analytics_meta WHERE key = 'salt'"
        ).fetchone()
        conn.close()
        _ANALYTICS_SALT = row[0] if row else ''
    return _ANALYTICS_SALT


def _is_bot(user_agent: str) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(s in ua for s in _BOT_UA_SUBSTRINGS)


def _visitor_hash():
    """Stable salted hash of IP + UA. Same visitor → same hash across time."""
    fwd = request.headers.get('X-Forwarded-For', '')
    ip = fwd.split(',')[0].strip() if fwd else (request.remote_addr or '')
    ua = request.headers.get('User-Agent', '')
    digest = hashlib.sha256((_get_salt() + ip + ua).encode('utf-8')).hexdigest()
    return digest[:16]


_PAGEVIEW_SKIP_PREFIXES = ('/static/', '/api/')
_PAGEVIEW_SKIP_EXACT = ('/favicon.ico', '/robots.txt')


@app.before_request
def _log_pageview():
    if request.method != 'GET':
        return
    path = request.path
    if path in _PAGEVIEW_SKIP_EXACT:
        return
    if any(path.startswith(p) for p in _PAGEVIEW_SKIP_PREFIXES):
        return
    if _is_bot(request.headers.get('User-Agent', '')):
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO pageviews (path, visitor_hash) VALUES (?, ?)',
            (path, _visitor_hash()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"analytics: pageview log failed: {e}", file=sys.stderr)


if Path(DB_PATH).exists():
    try:
        _init_analytics()
    except Exception as e:
        print(f"analytics: init failed: {e}", file=sys.stderr)
# --- end analytics -----------------------------------------------------------


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

    # Analytics: log the search (non-fatal on failure, skipped for bots).
    try:
        if not _is_bot(request.headers.get('User-Agent', '')):
            total = result.get('total_count', 0) if isinstance(result, dict) else 0
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                'INSERT INTO searches (term, lang, results, visitor_hash) VALUES (?, ?, ?, ?)',
                (term, lang, total, _visitor_hash()),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"analytics: search log failed: {e}", file=sys.stderr)

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
