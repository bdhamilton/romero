# Scripts Directory

This directory contains all scripts for data collection and processing (Phase 0).

## Quick Start: Reproduce the Database

To rebuild the entire database from scratch:

```bash
# 1. Scrape metadata from Romero Trust website
python scripts/scrape_all_metadata.py

# 2. Download all PDFs directly into hierarchical structure (takes ~12 minutes)
python scripts/download_pdfs.py

# 3. Extract text from all PDFs
python scripts/extract_text.py

# 4. Create SQLite database and load all data
python scripts/create_database.py
```

**Result:** `romero.db` - SQLite database with 195 homilies, metadata, and extracted text.

---

## Script Reference

### Data Collection Scripts (run in order)

#### 1. `scrape_all_metadata.py`
**What it does:** Scrapes Romero Trust website for all homily metadata
- Fetches index page with 195 homilies
- Visits each detail page to get Spanish titles and PDF URLs
- Saves to `data/homilies_metadata.json`

**Output:**
- `archive/homilies_metadata.json` - Complete metadata for all homilies

**Rate limiting:** 1 second between requests

---

#### 2. `download_pdfs.py`
**What it does:** Downloads all PDFs from Romero Trust directly into hierarchical structure
- Reads metadata from `archive/homilies_metadata.json`
- Downloads ~371 PDFs (184 Spanish + 187 English)
- Saves to `homilies/{year}/{month}/{day}/{prefix}{language}.pdf`
- Prefix is "1_", "2_", etc. ONLY for the 8 dates with multiple homilies

**Features:**
- Resume capability (skips existing files)
- 2-second rate limiting between downloads
- Stops after 3 consecutive failures
- Progress tracking and summary
- Smart filename prefixing (only when needed)

**Output:**
- `homilies/{year}/{month}/{day}/{language}.pdf` - Most homilies (no prefix)
- `homilies/{year}/{month}/{day}/{seq}_{language}.pdf` - 8 dates with duplicates

**Time:** ~12 minutes

---

#### 3. `extract_text.py`
**What it does:** Extracts text from all PDFs using pdfplumber
- Reads PDFs from hierarchical structure
- Comprehensive text cleaning:
  - Fixes hyphenated words across line breaks
  - Adds proper spacing at newlines
  - Removes headers, footers, page numbers
  - Normalizes whitespace
- Saves text files alongside PDFs

**Output:**
- `homilies/{year}/{month}/{day}/{language}.txt` - Cleaned text files (358 files)

**Library:** Uses pdfplumber (not PyPDF2) for perfect multi-column handling

**Time:** ~2-3 minutes

---

#### 5. `create_database.py`
**What it does:** Creates SQLite database and loads all data
- Creates schema (homilies table)
- Loads metadata from JSON
- Loads extracted text from .txt files
- Creates indexes for fast lookups
- Verifies data integrity

**Output:**
- `romero.db` - SQLite database (12.76 MB)

**Contains:**
- 195 homilies
- 185 Spanish texts (94.9% coverage)
- 189 English texts (96.9% coverage)
- All metadata (dates, titles, URLs, biblical references)

---

### Testing & Development Scripts

#### `extract_samples.py`
**What it does:** Extracts text from just 4 sample PDFs for testing
- Same cleaning logic as `extract_text.py`
- Fast iteration during development
- Verifies extraction quality

**Samples:**
- 1977-03-14 (Spanish + English)
- 1977-04-17 (Spanish + English)

---

#### `test_headers.py`
**What it does:** Tests header/footer patterns across different time periods
- Extracts first and last pages from sample homilies
- Verifies header patterns are consistent across years
- Used to design header removal regex

**Coverage:** Tests 1977, 1978, 1979, 1980

---

#### `debug_cleaning.py`
**What it does:** Debug tool for testing text cleaning regex patterns
- Tests individual cleaning steps in isolation
- Shows before/after for each regex
- Used during development to verify cleaning logic

---

### Deprecated Scripts

#### `collect-homilies.py`
**Status:** Superseded by `scrape_all_metadata.py`
- Original exploration script
- Contains `get_homilies_from_index()` and `add_detail_page_data()` functions
- Kept for reference but not used in workflow

---

## Data Flow Diagram

```
Romero Trust Website
        ↓
[scrape_all_metadata.py]
        ↓
archive/homilies_metadata.json
        ↓
[download_pdfs.py]
        ↓
homilies/{year}/{month}/{day}/*.pdf
        ↓
[extract_text.py]
        ↓
homilies/{year}/{month}/{day}/*.txt
        ↓
[create_database.py]
        ↓
romero.db (SQLite)
```

---

## Dependencies

All scripts require Python 3.7+ and these packages:

```bash
# Install via pip
pip install requests beautifulsoup4 pdfplumber

# Or use the project's virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

---

## Notes

### Why This Order?

1. **Metadata first**: Get complete list before downloading (prevents partial downloads)
2. **Download once**: PDFs are cached, no need to re-download for testing
3. **Reorganize**: Makes file structure easier to navigate
4. **Extract text**: Separate from download so we can re-run with different cleaning strategies
5. **Database last**: All data collected, now structure it for querying

### Idempotency

All scripts are **idempotent** (safe to run multiple times):
- `scrape_all_metadata.py`: Overwrites JSON (latest data wins)
- `download_pdfs.py`: Skips existing files
- `reorganize_pdfs.py`: Skips existing files
- `extract_text.py`: Skips existing .txt files
- `create_database.py`: Drops and recreates database

### Rate Limiting

Scripts respect Romero Trust's nonprofit server:
- Metadata scraping: 1 second between requests
- PDF downloads: 2 seconds between requests
- Total impact: ~15 minutes of light traffic

### Data Quality

See `PHASE0_NOTES.md` for detailed documentation of:
- Text cleaning strategy
- Known limitations
- Library selection rationale (pdfplumber vs PyPDF2)
- Header/footer removal patterns
