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
**Current State:** Initial exploration. Basic scraping code exists in `scripts/collect-homilies.py` but is incomplete.

**Immediate Next Steps:**
1. Complete the data collection pipeline
2. Examine the extracted text to understand quality and structure
3. Design database schema based on actual data characteristics
4. Document learnings about PDF quality, date consistency, coverage gaps

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
