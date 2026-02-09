# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Vision

**Romero Ngram Viewer** - A quantitative text analysis tool for Archbishop Oscar Romero's homilies (1977-1980), modeled after Google's Ngram Viewer.

### Purpose

This is a research tool and proof-of-concept for theological and philosophical research. The specific research question: Can quantitative analysis demonstrate what's actually "important" in Romero's thought versus what just gets mentioned once? Given that Romero talked about virtually everything at some point, frequency analysis over time can reveal what themes were sustained, what intensified during the crisis, and what patterns emerged in his preaching.

### Audience

- Primary: Academic researchers working on Romero, liberation theology, and Latin American church history
- Secondary: Broader public interested in Romero's thought and development

### Key Features

- Time-series visualization of word/phrase frequency in Romero's homilies
- Monthly granularity (1977-1980 = ~36 months of data)
- Drill-down capability: click any data point to see the actual homilies and context
- Eventually: cross-language analysis comparing Spanish originals to English translations

## Current Status

**Phase:** 1 (MVP - Spanish Ngram Viewer)
**Current State:** Core search and visualization working. Ngram viewer is the main page.

**What exists:**
- ✓ All 195 homilies scraped, 371 PDFs downloaded, 374 text files extracted
- ✓ SQLite database (`romero.db`) with all data: 186 Spanish texts, 188 English texts
- ✓ Full data pipeline (`build_database.py`) that can rebuild everything from scratch
- ✓ Search module (`search.py`) — case/accent-insensitive, phrase matching, monthly aggregation
- ✓ CLI search tool (`ngram.py`) — terminal-based frequency charts
- ✓ Web ngram viewer (`/`) — Google Ngram-style UI with Chart.js line chart
- ✓ Homily browser (`/browse`) — table of all homilies with PDF links to Romero Trust, known data issues section
- ✓ Search API (`/api/search`) — JSON endpoint for ngram queries
- ✓ Three normalization modes: raw count, per 10K words, per homily
- ✓ Smoothing (0-3 month moving average)
- ✓ Drill-down: click data point → see matching homilies with links to Romero Trust

**Next steps:**
1. Data curation system (see Phase 1.5 below)
2. Deploy as public web app
3. Context snippets in drill-down (show surrounding text for each match)
4. Multi-term comparison (plot multiple words on same chart)

## Project Structure

```
romero/
├── romero.db                    # SQLite database (13 MB, all data)
├── app.py                       # Flask web app (ngram viewer + browse + API)
├── search.py                    # Search module (accent folding, tokenization, monthly aggregation)
├── ngram.py                     # CLI search tool (terminal frequency charts)
├── build_database.py            # Master pipeline: runs all 4 scripts (will move to scripts/)
├── requirements.txt             # Python deps: requests, bs4, pdfplumber, flask
├── scripts/
│   ├── 01_scrape_all_metadata.py   # Scrape Romero Trust website
│   ├── 02_download_pdfs.py         # Download PDFs (rate-limited)
│   ├── 03_extract_text.py          # Extract text with pdfplumber
│   ├── 04_create_database.py       # Create & populate SQLite DB
│   └── README.md
├── homilies/                    # Date-structured content (69 MB)
│   └── {YYYY}/{MM}/{DD}/
│       ├── spanish.pdf / english.pdf
│       └── spanish.txt / english.txt
├── archive/
│   ├── homilies_metadata.json   # Raw scraped metadata (195 homilies)
│   └── PHASE0_NOTES.md          # Detailed extraction documentation
├── templates/                   # Flask templates
│   ├── index.html               # Homily browse table (/browse)
│   └── ngram.html               # Ngram viewer (/)
```

## Database Schema

```sql
CREATE TABLE homilies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    occasion TEXT,
    english_title TEXT,
    spanish_title TEXT,
    detail_url TEXT UNIQUE,
    biblical_references TEXT,
    spanish_pdf_url TEXT,
    spanish_pdf_path TEXT,       -- Relative path: homilies/YYYY/MM/DD/spanish.pdf
    english_pdf_url TEXT,
    english_pdf_path TEXT,
    spanish_text TEXT,           -- Cleaned extracted text
    english_text TEXT,
    audio_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_date ON homilies(date);
```

- 195 rows, date range: 1977-03-14 to 1980-03-24
- 186 with Spanish text, 188 with English text (9 missing Spanish, 7 missing English)
- Flat structure (one row per homily) — always exactly 1 English + 1 Spanish PDF per homily

## Development Phases

### Phase 0: Data Collection & Processing (COMPLETE)

All data collected from the Romero Trust website and stored locally. No further server requests needed.

**Summary of what was built:**
- Web scraper for index + detail pages (BeautifulSoup, 1s rate limiting)
- PDF downloader with resume capability (2s rate limiting, consecutive failure detection)
- Text extraction pipeline using pdfplumber (handles multi-column PDFs correctly)
- Text cleaning: hyphen rejoining, header/footer removal, whitespace normalization
- SQLite database creation with all metadata and extracted text

**Key learnings from Phase 0:**
- PDFs are text-based (not scanned) — no OCR needed
- pdfplumber handles column boundaries correctly; PyPDF2 does not (caused word concatenation)
- Date formatting is perfectly consistent: "DD Month YYYY"
- 195 homilies total, 172 with audio recordings
- 4 homilies are audio-only (no PDFs) — legitimate edge cases
- Regex order matters in text cleaning: fix hyphens before adding spaces at newlines
- Inline footnote markers (bare digits) are acceptable noise — too hard to distinguish from real numbers

### Phase 1: MVP - Spanish Ngram Viewer (CURRENT — mostly complete)

**Goal:** Build a working Ngram viewer for Spanish text only.

**Completed:**
1. ✓ Search module — no pre-built index needed; scanning 186 texts (~6 MB) takes ~0.6s
2. ✓ Case-insensitive, accent-insensitive (via NFD decomposition), exact phrase matching
3. ✓ CLI tool (`ngram.py`) with ASCII bar charts and top-homily listings
4. ✓ Web interface — Google Ngram Viewer-inspired design with Chart.js
5. ✓ Drill-down: click chart data point → see matching homilies with links to Romero Trust

**Remaining:**
- Deploy as public web app

**Technology Stack:**
- Backend: Python + Flask
- Database: SQLite (sufficient for corpus size)
- Frontend: HTML/JS with Chart.js (loaded from CDN)
- No heavy frameworks — prioritize simplicity

**Key decisions made:**
- No pre-built ngram index — brute-force tokenize+scan is fast enough at this corpus size
- Y-axis: three modes available (raw count, per 10K words, per homily). Default is raw count.
- Smoothing: 0-3 month moving average, user-selectable
- All 37 months have at least 1 homily, so no gap-handling needed

### Phase 1.5: Data Curation System (NEXT)

**Goal:** Treat the database as the source of truth (not the scrape pipeline). Build tools for ongoing data correction with full audit trail.

**Key decision:** The scraping/extraction pipeline was a one-time bootstrap. From here forward, the database is the canonical dataset. Manual corrections are expected and should be tracked, not avoided.

**Database changes:**

1. Add `status` column to `homilies` table (default `'active'`). Values: `'active'`, `'not_a_homily'`, `'placeholder'`. The search module and ngram viewer filter on `status = 'active'`. Browse page shows all rows but marks non-active ones visually.

2. New `changelog` table — tracks all editorial changes to homily records:
   ```sql
   CREATE TABLE changelog (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       homily_id INTEGER REFERENCES homilies(id),
       field TEXT,          -- column name changed, or NULL for general note
       old_value TEXT,
       new_value TEXT,
       comment TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. New `flags` table — crowdsourced data issue reports (no auth required):
   ```sql
   CREATE TABLE flags (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       homily_id INTEGER REFERENCES homilies(id),
       comment TEXT NOT NULL,
       status TEXT DEFAULT 'open',  -- 'open', 'resolved', 'wontfix'
       resolution TEXT,             -- filled in when resolved
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

**Build pipeline changes:**

4. Move `build_database.py` into `scripts/` (alongside the other pipeline scripts). It becomes a historical artifact documenting how the initial database was created.

5. Before any destructive operation, `build_database.py` backs up the existing database with a timestamp (e.g., `romero.db.backup.2026-02-08T1430`) instead of silently overwriting.

**Web UI — Browse page (`/browse`):**

6. Each homily row gets two links:
   - **Edit** (pencil icon or similar) — links to `/homily/<id>/edit` (requires auth)
   - **Flag** (flag icon) — links to `/homily/<id>/flag` (public, no auth)

7. "Known data issues" section at the top of browse page reads from the `flags` table (open flags) instead of computing missing texts from the database. This makes it a living list that users contribute to.

**Web UI — Flag page (`/homily/<id>/flag`):**

8. Read-only display of all homily fields (date, titles, occasion, biblical refs, text preview, links to PDFs on Romero Trust).

9. Comment box (required) + submit button. Creates a row in the `flags` table. No auth needed — anyone can flag an issue.

10. Below the comment box: list of existing flags for this homily (so users can see what's already been reported).

**Web UI — Edit page (`/homily/<id>/edit`):**

11. Requires auth (simple approach: a shared password or environment variable, not a full user system). Could be as simple as a `?key=SECRET` parameter or a session cookie from a `/login` page.

12. Displays all editable fields for the homily. Each field shows current value in an editable input.

13. Required "reason for change" comment box at the bottom.

14. On save: for each changed field, write a `changelog` row (old value, new value, comment), then update the homily record. All in one transaction.

15. Below the edit form: full changelog history for this homily, and list of flags (with ability to resolve/close them).

**Auth approach:**

16. Minimal: a single admin password set via environment variable (`ROMERO_ADMIN_KEY`). The `/login` page sets a session cookie. Edit pages check for the cookie. Flag pages don't require auth. This is a research tool, not a bank — simple is fine.

**Implementation order:**
1. Database schema changes (add `status`, create `changelog` and `flags` tables)
2. Move `build_database.py` to `scripts/`, add backup behavior
3. Flag page + flags table (public, no auth — simplest useful piece)
4. Update browse page to show flags instead of computed missing texts
5. Edit page + changelog table (requires auth)
6. Add auth (login page, session cookie, env var)
7. Update search module to filter on `status = 'active'`

### Phase 2: Enhancements

1. Add English corpus with language toggle
2. Cross-language comparison features
3. Advanced search: wildcards ("liber*"), stemming/lemmatization
4. UI polish and user experience improvements

### Phase 3: Research Features

1. Multi-term comparison (plot multiple words on same graph)
2. Export functionality (CSV, JSON)
3. Historical event overlay (key dates in Salvadoran history 1977-1980)
4. Biblical reference integration
5. Audio integration

## Technical Decisions

### Text Processing

- **Accents:** Preserve exactly in corpus; search is accent-insensitive by default (toggle for strict mode)
- **Case:** Case-insensitive by default
- **Phrases:** Exact phrase matching initially; wildcards in Phase 2
- **Granularity:** Store exact dates; visualize monthly

### Architecture Principles

1. **Simple over complex:** No frameworks unless necessary
2. **Educational:** Code should be readable and teach text analysis concepts
3. **Incremental:** Complete each phase before starting the next
4. **Data-driven:** Make decisions based on actual corpus characteristics, not assumptions

## Work Cycle

Each development session follows this pattern:

1. **Plan** - Discuss and agree on the next bite-sized piece of work
2. **Execute** - Build the planned feature or investigate the question
3. **Record** - Document learnings and decisions back into CLAUDE.md

## Development Guidelines

**For Future Claude Instances:**

- The user wants to learn about each phase of development — explain what you're doing and why
- Follow the work cycle: plan, execute, record
- Respect the Romero Trust's servers: always include rate-limiting in scraping/downloading
- Preserve all granular data even when aggregating for visualization
- Prioritize simplicity and clarity over cleverness
- Test with small samples before processing the full corpus
- Document assumptions and decisions — this is a research project

**Running the project:**
```bash
# First time: build database from scratch
python build_database.py --skip-scrape --skip-download  # if PDFs already downloaded

# Run web app
python app.py  # http://localhost:5000 (ngram viewer), /browse (homily table)

# CLI search
python ngram.py pueblo                    # raw count (default)
python ngram.py "pueblo de dios" --norm words   # per 10k words
python ngram.py justicia --norm homilies  # per homily
```

**Date Context:**
- Romero was Archbishop of San Salvador: February 1977 - March 1980
- Assassinated: March 24, 1980 (while celebrating Mass)
- ~3 years of homilies, roughly 36 months of data

**Language Note:**
- Spanish is the original language and primary focus
- English translations exist but may vary in quality/style
- Cross-language analysis is a secondary goal (Phase 2+)
