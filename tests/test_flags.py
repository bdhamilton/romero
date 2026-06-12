"""
Tests for the flags.db split: attached flags database and migration script.

Run from the project root: python -m pytest tests/
The flags DB is pointed at a pytest temp file, so these tests never touch
real flag data. Homily reads use the real romero.db, same as the app.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import app as app_module

MIGRATE = Path(__file__).resolve().parent.parent / 'scripts' / 'migrate_flags.py'


@pytest.fixture
def flags_path(tmp_path, monkeypatch):
    """Point the app at a temp flags DB that doesn't exist yet."""
    path = tmp_path / 'flags.db'
    monkeypatch.setattr(app_module, 'FLAGS_DB_PATH', str(path))
    return path


@pytest.fixture
def client(flags_path):
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def some_homily_id():
    conn = sqlite3.connect(app_module.DB_PATH)
    hid = conn.execute('SELECT id FROM homilies LIMIT 1').fetchone()[0]
    conn.close()
    return hid


def test_flags_db_autocreated_on_connect(flags_path):
    assert not flags_path.exists()
    conn = app_module.get_db()
    assert conn.execute('SELECT COUNT(*) FROM flagdb.flags').fetchone()[0] == 0
    conn.close()
    assert flags_path.exists()


def test_post_flag_lands_in_flags_db(client, flags_path):
    hid = some_homily_id()
    resp = client.post(f'/homily/{hid}/flag', data={'comment': 'test comment xyz'})
    assert resp.status_code == 302

    rows = sqlite3.connect(flags_path).execute(
        'SELECT homily_id, comment, status FROM flags').fetchall()
    assert rows == [(hid, 'test comment xyz', 'open')]


def test_flag_page_shows_submitted_flag(client, flags_path):
    hid = some_homily_id()
    client.post(f'/homily/{hid}/flag', data={'comment': 'visible on page'})
    resp = client.get(f'/homily/{hid}/flag')
    assert b'visible on page' in resp.data


def test_browse_shows_open_flag_via_cross_db_join(client, flags_path):
    hid = some_homily_id()
    client.post(f'/homily/{hid}/flag', data={'comment': 'browse join works'})
    resp = client.get('/browse')
    assert b'browse join works' in resp.data


def run_migrate(*args):
    return subprocess.run(
        [sys.executable, str(MIGRATE), *args],
        capture_output=True, text=True)


def make_source_db(path, flag_rows):
    """Create a minimal source DB with a flags table (ids may have gaps)."""
    conn = sqlite3.connect(path)
    conn.execute('''
        CREATE TABLE flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            homily_id INTEGER,
            comment TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            resolution TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    conn.executemany(
        'INSERT INTO flags (id, homily_id, comment) VALUES (?, ?, ?)', flag_rows)
    conn.commit()
    conn.close()


def test_migration_moves_rows_and_drops_table(tmp_path):
    src = tmp_path / 'source.db'
    dst = tmp_path / 'flags.db'
    make_source_db(src, [(1, 10, 'first'), (3, 11, 'second'), (5, 12, 'third')])

    result = run_migrate('--source', str(src), '--flags', str(dst))
    assert result.returncode == 0, result.stderr

    moved = sqlite3.connect(dst).execute(
        'SELECT id, comment FROM flags ORDER BY id').fetchall()
    assert moved == [(1, 'first'), (3, 'second'), (5, 'third')]

    src_conn = sqlite3.connect(src)
    assert src_conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='flags'").fetchone() is None

    # AUTOINCREMENT continues past the highest migrated id
    dst_conn = sqlite3.connect(dst)
    dst_conn.execute("INSERT INTO flags (homily_id, comment) VALUES (1, 'new')")
    assert dst_conn.execute('SELECT MAX(id) FROM flags').fetchone()[0] == 6


def test_migration_is_idempotent(tmp_path):
    src = tmp_path / 'source.db'
    dst = tmp_path / 'flags.db'
    make_source_db(src, [(1, 10, 'only')])

    assert run_migrate('--source', str(src), '--flags', str(dst)).returncode == 0
    second = run_migrate('--source', str(src), '--flags', str(dst))
    assert second.returncode == 0
    assert 'Nothing to migrate' in second.stdout
    # Still exactly one row
    assert sqlite3.connect(dst).execute(
        'SELECT COUNT(*) FROM flags').fetchone()[0] == 1


def test_migration_no_drop_leaves_source(tmp_path):
    src = tmp_path / 'source.db'
    dst = tmp_path / 'flags.db'
    make_source_db(src, [(1, 10, 'kept')])

    result = run_migrate('--source', str(src), '--flags', str(dst), '--no-drop')
    assert result.returncode == 0
    assert sqlite3.connect(src).execute(
        'SELECT COUNT(*) FROM flags').fetchone()[0] == 1
    assert sqlite3.connect(dst).execute(
        'SELECT COUNT(*) FROM flags').fetchone()[0] == 1


def test_migration_refuses_populated_destination(tmp_path):
    src = tmp_path / 'source.db'
    dst = tmp_path / 'flags.db'
    make_source_db(src, [(1, 10, 'a')])
    assert run_migrate('--source', str(src), '--flags', str(dst), '--no-drop').returncode == 0

    result = run_migrate('--source', str(src), '--flags', str(dst))
    assert result.returncode != 0
    assert 'Refusing' in result.stderr
    # No double insert happened
    assert sqlite3.connect(dst).execute(
        'SELECT COUNT(*) FROM flags').fetchone()[0] == 1
