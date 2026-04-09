"""
Lightweight traffic tracking for the Romero Text Explorer.

Stores page views and searches in the same SQLite DB as the rest of the
app. No cookies, no client-side JS, no IPs, no third parties. User-Agent
strings are kept so we can (a) filter crawlers and (b) spot-check the
filter against real traffic. Distinct visitors can be counted roughly as
COUNT(DISTINCT user_agent).

Usage:
    import analytics
    analytics.init(app, DB_PATH)           # on startup
    analytics.log_search(term, lang, n, ua)  # from the search route
"""

import sqlite3
import sys

from flask import request


_BOT_UA_SUBSTRINGS = (
    'bot', 'crawl', 'spider', 'slurp', 'bingpreview', 'mediapartners',
    'headless', 'monitor', 'pingdom', 'uptimerobot', 'ahrefs', 'semrush',
    'facebookexternalhit', 'python-requests', 'curl/', 'wget/',
)

_PAGEVIEW_SKIP_PREFIXES = ('/static/', '/api/')
_PAGEVIEW_SKIP_EXACT = ('/favicon.ico', '/robots.txt')

_db_path = None


def init(app, db_path: str) -> None:
    """Set up analytics against the given Flask app and SQLite database.

    Creates the tables (migrating from the earlier hashed-visitor schema
    on this branch if present) and registers a before_request handler
    that logs page views. Safe to call more than once; errors are logged
    to stderr rather than raised so analytics can never break startup.
    """
    global _db_path
    _db_path = db_path
    try:
        _create_tables(db_path)
    except Exception as e:
        print(f"analytics: init failed: {e}", file=sys.stderr)
        return
    app.before_request(_log_pageview)


def log_search(term: str, lang: str, results: int, user_agent: str) -> None:
    """Log a search. Non-fatal on error, skipped for bot UAs."""
    if _db_path is None or _is_bot(user_agent):
        return
    try:
        conn = sqlite3.connect(_db_path)
        conn.execute(
            'INSERT INTO searches (term, lang, results, user_agent) VALUES (?, ?, ?, ?)',
            (term, lang, results, user_agent),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"analytics: search log failed: {e}", file=sys.stderr)


def _is_bot(user_agent: str) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(s in ua for s in _BOT_UA_SUBSTRINGS)


def _create_tables(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    # One-time migration from the earlier version of this branch, which
    # stored a salted hash in visitor_hash plus a salt in analytics_meta.
    # If we find old-schema tables, drop them and recreate.
    for table in ('pageviews', 'searches'):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if exists:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()]
            if 'user_agent' not in cols:
                conn.execute(f'DROP TABLE {table}')
    conn.execute('DROP TABLE IF EXISTS analytics_meta')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS pageviews (
          ts         TEXT NOT NULL DEFAULT (datetime('now')),
          path       TEXT NOT NULL,
          user_agent TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS searches (
          ts         TEXT NOT NULL DEFAULT (datetime('now')),
          term       TEXT NOT NULL,
          lang       TEXT NOT NULL,
          results    INTEGER,
          user_agent TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_pageviews_ts ON pageviews(ts);
        CREATE INDEX IF NOT EXISTS idx_searches_ts ON searches(ts);
    ''')
    conn.commit()
    conn.close()


def _log_pageview() -> None:
    if request.method != 'GET':
        return
    path = request.path
    if path in _PAGEVIEW_SKIP_EXACT:
        return
    if any(path.startswith(p) for p in _PAGEVIEW_SKIP_PREFIXES):
        return
    ua = request.headers.get('User-Agent', '')
    if _is_bot(ua):
        return
    try:
        conn = sqlite3.connect(_db_path)
        conn.execute(
            'INSERT INTO pageviews (path, user_agent) VALUES (?, ?)',
            (path, ua),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"analytics: pageview log failed: {e}", file=sys.stderr)
