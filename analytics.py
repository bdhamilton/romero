"""
Lightweight traffic tracking for the Romero Text Explorer.

Stores page views and searches in the same SQLite DB as the rest of the
app. No cookies, no client-side JS, no IPs, no third parties. User-Agent
strings are kept so we can (a) filter crawlers and (b) spot-check the
filter against real traffic. Distinct visitors can be counted roughly as
COUNT(DISTINCT user_agent).

Usage:
    import analytics
    analytics.init(DB_PATH)                    # on startup

    @app.route('/')
    @analytics.track_pageview                  # <-- @app.route must be outermost
    def home(): ...

    analytics.log_search(term, lang, n, ua)    # from the search route
"""

import functools
import sqlite3
import sys

from flask import request


_BOT_UA_SUBSTRINGS = (
    'bot', 'crawl', 'spider', 'slurp', 'bingpreview', 'mediapartners',
    'headless', 'monitor', 'pingdom', 'uptimerobot', 'ahrefs', 'semrush',
    'facebookexternalhit', 'python-requests', 'curl/', 'wget/',
)

_db_path = None


def init(db_path: str) -> None:
    """Set up analytics against the given SQLite database.

    Creates the pageviews and searches tables if they don't exist.
    Errors are logged to stderr rather than raised so analytics can
    never break startup.
    """
    global _db_path
    _db_path = db_path
    try:
        conn = sqlite3.connect(db_path)
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
    except Exception as e:
        print(f"analytics: init failed: {e}", file=sys.stderr)


def track_pageview(view_func):
    """Decorator that logs a page view for a Flask route.

    Apply BELOW @app.route so @app.route stays outermost — otherwise
    Flask registers the un-wrapped view and the decorator never runs:

        @app.route('/')
        @analytics.track_pageview
        def home(): ...

    Only logs GET requests. Bot UAs are skipped. Non-fatal on error.
    """
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        if request.method == 'GET':
            ua = request.headers.get('User-Agent', '')
            if not _is_bot(ua):
                try:
                    conn = sqlite3.connect(_db_path)
                    conn.execute(
                        'INSERT INTO pageviews (path, user_agent) VALUES (?, ?)',
                        (request.path, ua),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"analytics: pageview log failed: {e}", file=sys.stderr)
        return view_func(*args, **kwargs)
    return wrapper


def log_search(term: str, lang: str, results: int, user_agent: str) -> None:
    """Log a search. Non-fatal on error, skipped for bot UAs."""
    if _is_bot(user_agent):
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
