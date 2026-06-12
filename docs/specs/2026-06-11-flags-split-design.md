# Design: Split flags into a server-local flags.db

**Date:** 2026-06-11
**Status:** Approved

## Motivation

`romero.db` currently serves two masters: it is the *corpus* (homily texts and
search indexes — written locally, versioned in git, distributed by deploy) and
it holds the *flags* table (written live on the server by the public flag
form). Two writers on one git-tracked binary file means every deploy that
touches `romero.db` conflicts with the server's local changes. This bit us for
real on 2026-06-11: a `git stash` / `pull` / `pop` attempt on the server left
`romero.db` as a 0-byte file mid-merge and took the site down until the live
DB was rescued from the stash.

The fix: one file per writer.

- `romero.db` — corpus only. In git. **Read-only on the server.** Deploys are
  clean pulls forever.
- `flags.db` — flags only. Gitignored, server-local, never deployed.

Rejected alternatives: gitignoring `romero.db` entirely (corpus fixes would
then reach prod by scp, which overwrites server flags — same collision, and
the research corpus loses version history); manual flag reconciliation on
each deploy (fragile, as the incident proved).

## How it works: SQLite ATTACH

A SQLite database is a single ordinary file. One connection can see several
files at once via `ATTACH DATABASE 'flags.db' AS flagdb` — after which tables
are addressed as `main.homilies`, `flagdb.flags`, and **cross-file joins work
in a single query** (the browse page joins flags to homily titles). `ATTACH`
creates a missing file automatically, and `CREATE TABLE IF NOT EXISTS` is a
no-op when the table exists, so every connection can cheaply guarantee a
working flags DB — a fresh checkout needs zero setup.

## Components

### 1. `app.py`

- New constant `FLAGS_DB_PATH = 'flags.db'` beside `DB_PATH`.
- `get_db()` attaches `FLAGS_DB_PATH` as `flagdb` and ensures the schema:

  ```sql
  ATTACH DATABASE 'flags.db' AS flagdb;
  CREATE TABLE IF NOT EXISTS flagdb.flags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      homily_id INTEGER,            -- references homilies(id) in romero.db
      comment TEXT NOT NULL,
      status TEXT DEFAULT 'open',   -- 'open', 'resolved', 'wontfix'
      resolution TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

  Note: the cross-file foreign key becomes a comment — SQLite foreign keys
  cannot reference tables in another attached database. The app never relied
  on FK enforcement (SQLite leaves it off by default), so behavior is
  unchanged.
- The three flag queries gain a `flagdb.` prefix: the browse-page join, the
  flag-page select, and the insert. `search.py` is untouched.

### 2. `scripts/migrate_flags.py`

One-shot migration, run once locally; also used on the server (copy-only
mode) to seed `flags.db` from the rescued live database.

```
migrate_flags.py [--source romero.db] [--flags flags.db] [--no-drop]
```

1. Open `--source`; if it has no `flags` table, print "nothing to migrate"
   and exit 0 (idempotent).
2. Refuse to run if `--flags` already contains rows (no double-inserts).
3. Attach `--flags`, create the schema, copy all rows preserving ids
   (`INSERT INTO flagdb.flags SELECT * FROM main.flags`). Inserting explicit
   ids into an AUTOINCREMENT table advances SQLite's internal sequence, so
   new flags continue numbering correctly.
4. Unless `--no-drop`: `DROP TABLE main.flags`, then `VACUUM` (SQLite files
   don't shrink when data is deleted — pages are only marked reusable;
   VACUUM rewrites the file compactly).
5. Print rows copied and final counts.

### 3. `.gitignore`

Add `flags.db` and `flags.db-*` (the latter catches SQLite's transient
sidecar files: `-journal`, `-wal`, `-shm`).

### 4. Rollout

Current state going in: server tree is clean on origin/main; server and local
flags verified identical (17 rows); rescued live DB at
`/home/brian/romero-live-rescue.db`.

**Local:**
1. Implement app changes, script, gitignore, tests; run suite.
2. `python scripts/migrate_flags.py` — creates local `flags.db` (17 rows),
   drops flags table from `romero.db`, VACUUMs.
3. Commit code + corpus-only `romero.db`; push.

**Server (one-time cutover):**
1. `git pull` — clean swap of `romero.db` for the corpus-only version
   (the server copy is pristine, so no conflict).
2. Seed flags from the server's own last-live data:
   `.venv/bin/python scripts/migrate_flags.py --source /home/brian/romero-live-rescue.db --no-drop`
   → creates `/var/www/romero/flags.db` with the 17 flags.
3. User restarts: `sudo systemctl restart romero` (interactive password).
4. Verify: `/browse` shows the open flags; submit + resolve a test flag.
5. After verification, `/home/brian/romero-live-rescue.db` can be deleted.

After cutover, nothing on the server writes `romero.db`; every future deploy
is `git pull` + restart.

### 5. Documentation updates

- CLAUDE.md: schema section (flags table now in `flags.db`, attached as
  `flagdb`), project structure, "what exists" notes.
- Deploy skill: replace the romero.db-conflict reconciliation runbook with
  "romero.db is read-only on the server; flags live in flags.db (never in
  git); back up flags.db before risky operations."

## Testing

New `tests/test_flags.py`. The flags path is pointed at a pytest temp file by
patching `app_module.FLAGS_DB_PATH` (read at connection time), so tests never
touch real data. Guarantees:

- `get_db` — connecting when `flags.db` is missing auto-creates it with the
  flags schema (the fresh-checkout guarantee).
- `POST /homily/<id>/flag` — the flag row lands in `flags.db` (asserted by
  querying the file directly), `romero.db` is unchanged, and the response
  redirects back to the flag page.
- `GET /browse` — an open flag inserted into `flags.db` appears on the page
  with its homily's title (proves the cross-database join).
- `migrate_flags.py` — after one run: source has no flags table, dest has all
  original rows with ids preserved; a second run exits cleanly without
  changes; `--no-drop` leaves the source table in place; a dest that already
  has rows is refused.

No tests for the deploy runbook — it's a one-time operational procedure,
verified live during cutover.

## Out of scope

- Backups of the server's `flags.db` (recommend a cron'd
  `sqlite3 flags.db ".backup ..."` later — separate decision)
- The sudoers NOPASSWD rule for restarts (user-owned)
- The Phase 2 `changelog` table (corpus-side; goes in `romero.db` when built)
