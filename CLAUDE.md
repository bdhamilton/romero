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

## Development Phases

### Phase 0: Data Collection & Processing (CURRENT PHASE)

**Goal:** Acquire and structure all source material for analysis.

**Workflow:**
1. Scrape index page → collect basic metadata (occasion, English title, date, biblical references, detail URL)
2. Visit each detail page → collect Spanish title, PDF URLs (English + Spanish), audio URL if present
3. Store all metadata in SQLite database
4. Download all PDFs using database to track progress (AFTER THIS: no more requests to Romero Trust needed)
5. Extract text from PDFs and store in database

**Database Schema (SQLite):**
```sql
CREATE TABLE homilies (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    occasion TEXT,
    english_title TEXT,
    spanish_title TEXT,        -- Only available from detail page
    detail_url TEXT UNIQUE,
    biblical_references TEXT,   -- Stored as raw string (unparsed)

    -- PDFs (always exactly 1 English + 1 Spanish per homily)
    spanish_pdf_url TEXT,
    spanish_pdf_path TEXT,      -- Local file path after download
    spanish_text TEXT,           -- Extracted text

    english_pdf_url TEXT,
    english_pdf_path TEXT,
    english_text TEXT,

    -- Audio (optional, only some homilies have audio)
    audio_url TEXT,

    -- Tracking timestamps
    scraped_at TIMESTAMP,
    pdfs_downloaded_at TIMESTAMP,
    text_extracted_at TIMESTAMP
);
```

**Key Design Decisions:**

*Schema: Flat vs. Normalized*
- Chose flat structure (one row per homily) because there's always exactly one English and one Spanish PDF per homily
- Simpler queries, no joins needed
- Corpus size (~400 documents) is small enough that denormalization doesn't matter

*Text Storage: Database vs. Files*
- Store text in database (not separate .txt files)
- Rationale: Need text for context display when users drill down, easier to query, simpler deployment
- The inverted index for searching will be built separately from this raw text storage

*Biblical References: Parsed vs. Raw*
- Store as unparsed strings for now
- Rationale: Uncertain if formatting is consistent, no immediate use case
- Can parse later if needed (data-driven decision making)

**Website Structure (Discovered):**

From index page (`/homilies-and-writing/homilies/`):
- Occasion (e.g., "Funeral Mass for Fr Rutilio Grande, SJ")
- English title
- Date (format: "14 March 1977")
- Detail URL
- Biblical references with audio indicator (e.g., "(+ AUDIO) John 20:19-31; Acts 5:12-16...")

From detail pages (e.g., `/1977-homilies/motivation-of-love/`):
- Spanish title (only appears as PDF link text)
- English PDF URL
- Spanish PDF URL
- Audio URL (MP3, when available)

**Learning Goals:** Understand web scraping, PDF processing, text extraction, and data normalization.

**Open Questions (to be answered during execution):**
- What's the quality of PDF text extraction? Will we need OCR for scanned images?
- How consistent is the date formatting across all homilies?
- Are there any missing homilies or gaps in coverage?
- What's the actual text structure like (headers, footers, formatting)?
- How should we handle rate limiting? (1-2 seconds between requests)

### Phase 1: MVP - Spanish Ngram Viewer

**Goal:** Build a working Ngram viewer for Spanish text only.

**Tasks:**
1. Build corpus index
   - Word/phrase → [date, homily_id, occurrence_count, context] mappings
   - Efficient querying for time-series data
2. Implement search
   - Case-insensitive by default
   - Accent-insensitive by default (configurable)
   - Exact phrase matching
   - Aggregate by month for visualization
3. Create command-line query tool for testing
4. Build minimal web interface
   - Input box for word/phrase search
   - Line chart showing frequency over time (monthly resolution)
   - Click data point → see list of matching homilies with context
5. Deploy as public web app

**Technology Stack:**
- Backend: Python (Flask or FastAPI - keep it simple)
- Database: TBD based on Phase 0 learnings (SQLite, PostgreSQL, or specialized text search)
- Frontend: Simple HTML/JS with charting library (Chart.js or similar)
- No heavy frameworks needed - prioritize simplicity

**Decisions Deferred Until We See Data:**
- Y-axis metric: Raw count vs. normalized frequency (per 10,000 words)?
- Smoothing/averaging options?
- How to handle months with no homilies?

### Phase 2: Enhancements

1. Add English corpus with language toggle
2. Cross-language comparison features
   - How does word usage differ between Spanish original and English translation?
   - Translation quality/consistency analysis
3. Advanced search options
   - Wildcards ("liber*" matches "liberación", "libertad", etc.)
   - Stemming/lemmatization (group word forms together)
4. UI polish and user experience improvements

### Phase 3: Research Features

1. Multi-term comparison (plot multiple words on same graph)
2. Export functionality (CSV, JSON for further analysis)
3. Historical event overlay
   - Key dates in Salvadoran history (1977-1980)
   - Priest assassinations, political events
   - Show correlations between events and language shifts
4. Biblical reference integration
   - Show which passages were referenced during high-frequency periods
5. Audio integration (for homilies with audio recordings)

## Technical Decisions

### Text Processing (Decided)

**Accent handling:** Preserve accents exactly in corpus, but search is accent-insensitive by default (with option to toggle strict mode). Rationale:
- OCR may be inconsistent with accents
- Researchers typing queries may not use proper accents
- Can still offer strict mode for linguistic analysis

**Case handling:** Case-insensitive by default, matching Google Ngrams behavior.

**Phrase matching:** Exact phrase matching initially. Wildcards and variations in Phase 2.

**Time granularity:**
- Store exact dates in database
- Visualize at monthly resolution (to avoid excessive noise)
- May need to tune based on actual data patterns

### Architecture Principles

1. **Simple over complex:** No frameworks unless necessary
2. **Educational:** Code should be readable and teach text analysis concepts
3. **Incremental:** Get Phase 0 fully working before moving to Phase 1
4. **Data-driven:** Make decisions based on actual corpus characteristics, not assumptions

## Current Status

**Phase:** 0 (Data Collection)
**Current State:** Metadata collection complete (191/195 Spanish PDFs collected). Ready to create database and download PDFs.

**Completed:**
- ✓ Index page scraping (`get_homilies_from_index()`)
- ✓ Database schema design
- ✓ Detail page scraping (`add_detail_page_data()`)
- ✓ Full metadata collection with manual fixes
- ✓ Metadata saved to `data/homilies_metadata.json`

**Next Steps:**
1. Create SQLite database and load metadata
2. Download all PDFs (191 Spanish + 192 English = ~383 PDFs)
3. Extract text from PDFs
4. Store text in database

---

## Phase 0 Work Log

### Session 1: Index Page Scraping & Schema Design

**What We Built:**
- Implemented `get_homilies_from_index()` in `scripts/collect-homilies.py`
- Scrapes main index page for basic metadata
- Returns list of dictionaries with: occasion, title (English), date, detail URL, has_audio flag, biblical references

**What We Learned:**

*Data Coverage:*
- **195 homilies total** from March 14, 1977 → March 24, 1980 (his final homily before assassination)
- **172 have audio recordings** (88% - excellent coverage!)
- Date formatting is perfectly consistent: "DD Month YYYY" format
- Complete coverage of Romero's tenure as Archbishop

*Biblical References:*
- Formatting is inconsistent - cannot reliably split on punctuation
- Commas appear both as separators AND within verse ranges (e.g., "Isaiah 61:1-3a, 6a, 8b-9")
- Semicolons appear to be the primary separator between different passages
- Audio indicators appear as "(+AUDIO)", "(+ AUDIO)", or just "AUDIO"

*Website Structure:*
- Index page uses sibling-based DOM traversal (occasion → title → date → references paragraph)
- References are in `<p>` tags between homilies
- Audio indicators are embedded in the references text, not separate fields

**Decisions Made:**

1. **Biblical References Storage:** Store as unparsed strings
   - Rationale: Inconsistent formatting makes reliable parsing difficult
   - Can parse later if needed
   - References are cleaned of audio markers but otherwise preserved exactly

2. **Audio Detection:** Simple string search for "AUDIO" in references text
   - Remove markers with multiple patterns: "(+AUDIO)", "(+ AUDIO)", "AUDIO"
   - Clean approach that handles variations

3. **Data Structure:** Keep using dictionaries for now, will convert to database schema in next step

**Code Status:**
- `get_homilies_from_index()` working and tested
- Correctly extracts all 195 homilies
- Audio detection 100% clean (no markers left in references)
- Ready for detail page scraping

### Session 2: Detail Page Scraping Implementation

**What We Built:**
- Implemented `add_detail_page_data()` in `scripts/collect-homilies.py`
- Created `scripts/scrape_all_metadata.py` wrapper script for running full collection
- Scrapes each homily's detail page for: Spanish title, English PDF URL, Spanish PDF URL, audio URL

**What We Learned:**

*PDF Filename Patterns:*
- English PDFs: Start with `ART_` prefix (e.g., `ART_Homilies_Vol1_1_Motivation_Love.pdf`)
- Spanish PDFs: Start with date `YYYY-MM-DD` (e.g., `1977-03-14-Una-motivacion-de-amor.pdf`)
- Pattern holds for ~97% of homilies
- Consistent ordering: English PDF listed first, Spanish PDF second
- Edge case: "Easter Triduum" homily has only 1 PDF

*Audio Files:*
- Audio URLs found in `<source>` tags or audio links
- MP3 format hosted on CDN: `romerotrust.b-cdn.net`
- Only need to look for audio when `has_audio == True` flag is set

*Spanish Titles:*
- Only available on detail pages (not on index)
- Extracted from the link text of Spanish PDF

**Decisions Made:**

1. **PDF Categorization Logic:**
   - Primary: Check filename patterns (`ART_` = English, starts with digits = Spanish)
   - Fallback: Use order (first = English, second = Spanish)
   - Graceful degradation: If only 1 PDF found, assign to English slot

2. **Rate Limiting:** 1 second delay between detail page requests
   - Total time: ~195 seconds (~3 minutes) for all homilies
   - Respectful of nonprofit server resources

3. **Error Handling:**
   - Wrap each page fetch in try/except
   - On error, set fields to None and continue
   - Log errors but don't stop entire process

4. **Progress Tracking:**
   - Print progress every 10 homilies
   - Show first and last homily being processed
   - Created separate runner script with summary statistics

**Code Status:**
- `add_detail_page_data()` implemented and tested on 5 homilies
- 4/5 test cases perfect, 1 edge case (missing Spanish PDF) handled gracefully
- Audio detection working
- Ready to run on all 195 homilies

### Session 2 (continued): Full Scrape and Manual Fixes

**Execution Results:**
- Successfully scraped all 195 homilies
- Initial run had 4 connection errors (connection reset by peer)
- Retried failed connections successfully

**Final Coverage:**
- **191/195 Spanish titles and PDFs (98%)**
- **192/195 English PDFs (98%)**
- **171/172 Audio URLs (99%)** - 1 with flag but no URL found

**Missing PDFs (4 homilies):**
1. "Easter Triduum radio message" - English-only (special radio broadcast)
2. "Teachers in the Model of Vatican II" - Audio-only
3. "Georgetown University Doctorate" - Audio-only (ceremony, not homily)
4. "Archbishop Romero was in Rome" - Audio-only (special event)

These are legitimate edge cases - not regular homilies or have audio-only format.

**Manual Fixes Applied:**
- Retried 4 homilies that had connection errors during initial scrape
- All 4 successfully retrieved on retry
- Updated metadata file manually rather than re-running full script

**Key Learning:** Connection errors are transient - retry logic would be useful for production but manual fixes work fine for one-time data collection.

**Status:** Metadata collection complete. Ready for next step (database creation and PDF downloads).

## Work Cycle

Each development session follows this pattern:

1. **Plan** - Discuss and agree on the next bite-sized piece of work
   - Define clear, achievable scope for this session
   - Identify what we'll learn or decide
   - Add the plan to CLAUDE.md before starting

2. **Execute** - Build the planned feature or investigate the question
   - Explain what you're doing and why (educational focus)
   - Test with small samples before scaling up
   - Keep it simple and working

3. **Record** - Document learnings and decisions back into CLAUDE.md
   - What did we learn about the data/problem?
   - What decisions did we make and why?
   - What questions emerged for next time?
   - Update current status and next steps

This ensures continuity across sessions and builds institutional knowledge in the documentation.

## Development Guidelines

**For Future Claude Instances:**

- The user wants to learn about each phase of development - explain what you're doing and why
- Follow the work cycle above: plan, execute, record
- Respect the Romero Trust's servers: always include rate-limiting in scraping/downloading
- Preserve all granular data even when aggregating for visualization
- Prioritize simplicity and clarity over cleverness
- Test with small samples before processing the full corpus
- Document assumptions and decisions - this is a research project

**Date Context:**
- Romero was Archbishop of San Salvador: February 1977 - March 1980
- Assassinated: March 24, 1980 (while celebrating Mass)
- This gives us ~3 years of homilies, roughly 36 months of data

**Language Note:**
- Spanish is the original language and primary focus
- English translations exist but may vary in quality/style
- Cross-language analysis is explicitly a secondary goal (Phase 2+)
