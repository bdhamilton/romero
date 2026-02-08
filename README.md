# Romero Ngram Viewer

A quantitative text analysis tool for Archbishop Oscar Romero's homilies (1977-1980), modeled after Google's Ngram Viewer.

## What Is This?

This project enables researchers to track word and phrase frequency over time in Romero's preaching during the Salvadoran civil war. Instead of reading all 195 homilies to find patterns, you can search for terms like "liberación" or "pueblo de Dios" and see exactly when and how often they appear.

**Research Question:** Can quantitative analysis demonstrate what's actually "important" in Romero's thought versus what just gets mentioned once? Given that Romero talked about virtually everything at some point, frequency analysis over time reveals sustained themes, crisis-driven intensification, and evolving patterns.

## Project Status

**Current Phase:** Phase 0 Complete ✓

All data collected, processed, and stored in SQLite database. Ready for Phase 1 (ngram indexing and search).

### Completed
- ✓ Scraped metadata for 195 homilies from Romero Trust
- ✓ Downloaded 371 PDFs (Spanish and English)
- ✓ Extracted and cleaned text with pdfplumber
- ✓ Created SQLite database with full corpus
- ✓ Built web interface for browsing and reviewing homilies

### What Works Now
- Complete database of 195 homilies (1977-03-14 to 1980-03-24)
- 185 Spanish texts, 189 English texts
- Cleaned text (no headers, footers, page numbers)
- All metadata preserved (dates, occasions, biblical references)
- Flask web app with table-based index for easy browsing
- Direct access to local PDF files from web interface

### Next Steps (Phase 1)
- Build ngram search index
- Command-line query tool
- Time-series visualization

## Quick Start

### Reproduce the Database

```bash
# 1. Clone repository
git clone https://github.com/yourusername/romero.git
cd romero

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Run data collection pipeline (takes ~15 minutes)
python scripts/01_scrape_metadata.py
python scripts/02_download_pdfs.py
python scripts/03_extract_text.py
python scripts/04_create_database.py

# Result: romero.db (SQLite database with full corpus)
```

See individual scripts for detailed documentation (each script has extensive inline comments).

### Browse the Homilies

```bash
# Start the web interface
python app.py

# Open http://localhost:5000 in your browser
```

The web interface provides:
- Complete table of all 195 homilies with metadata
- Links to original detail pages on Romero Trust website
- Direct access to downloaded PDF files (both Spanish and English)
- Visual indicators for available/missing texts

### Explore the Database

```bash
sqlite3 romero.db

# Example queries:
SELECT COUNT(*) FROM homilies;
SELECT date, occasion FROM homilies WHERE date LIKE '1980%';
SELECT AVG(LENGTH(spanish_text)) FROM homilies WHERE spanish_text IS NOT NULL;
```

## Project Structure

```
romero/
├── romero.db                  # SQLite database (output)
├── archive/
│   └── homilies_metadata.json # Scraped metadata
│
├── homilies/                  # Hierarchical text & PDF storage
│   └── {year}/{month}/{day}/
│       ├── spanish.pdf
│       ├── spanish.txt
│       ├── english.pdf
│       └── english.txt
│
├── scripts/                   # Data collection pipeline
│   ├── 01_scrape_metadata.py
│   ├── 02_download_pdfs.py
│   ├── 03_extract_text.py
│   └── 04_create_database.py
│
├── templates/                 # Web interface templates
│   ├── base.html
│   ├── index.html            # Main table view
│   └── homily.html           # Detail page (not currently used)
│
├── static/
│   └── css/
│       └── style.css         # Web interface styling
│
├── app.py                     # Flask web application
├── requirements.txt           # Python dependencies
├── CLAUDE.md                  # Development log & decisions
├── PHASE0_PLAN.md            # Phase 0 implementation plan
└── README.md                  # This file
```

## Data Source

All homilies sourced from [The Romero Trust](https://www.romerotrust.org.uk/homilies-and-writing/homilies/), which provides PDFs and audio recordings of Romero's preaching.

**Coverage:**
- **195 homilies** from March 14, 1977 (his first homily as Archbishop) to March 24, 1980 (day of assassination)
- **Spanish originals** (185 available, ~95%)
- **English translations** (189 available, ~97%)
- **Audio recordings** for 172 homilies (~88%)

## Technology

- **Python 3.7+** - Data processing
- **SQLite** - Database (single file, ~13 MB)
- **pdfplumber** - PDF text extraction (handles multi-column layouts)
- **BeautifulSoup4** - Web scraping
- **Flask** - Web interface for browsing homilies
- **Chart.js** (Phase 1) - Time-series visualization (coming soon)

## Development Workflow

This project follows an incremental, educational approach documented in `CLAUDE.md`. Each phase builds on the previous:

- **Phase 0** (COMPLETE): Data collection & processing
- **Phase 1** (NEXT): Spanish ngram viewer MVP
- **Phase 2**: English corpus, cross-language analysis
- **Phase 3**: Advanced features (historical events, biblical references)

## Contributing

This is a research project with educational goals. The code prioritizes:
- **Clarity** over cleverness
- **Documentation** of decisions
- **Reproducibility** from source
- **Simplicity** over frameworks

See `CLAUDE.md` for development philosophy and architecture decisions.

## License

Code: MIT License

Data: Homily text and metadata sourced from The Romero Trust. Please respect their copyright and cite appropriately in academic work.

## Citation

If you use this tool in academic research, please cite:

```
[Your Name]. (2024). Romero Ngram Viewer: Quantitative Analysis of Archbishop
Oscar Romero's Homilies (1977-1980). https://github.com/yourusername/romero
```

And cite the original source:

```
The Romero Trust. "Homilies and Writings." https://www.romerotrust.org.uk/
homilies-and-writing/homilies/ (accessed [date]).
```

## Acknowledgments

- **The Romero Trust** for preserving and publishing Romero's homilies
- **Claude Code** (Anthropic) for development assistance
- All scholars and translators who have made Romero's work accessible

## About Oscar Romero

Archbishop Oscar Romero (1917-1980) was assassinated while celebrating Mass on March 24, 1980. His transformation from a conservative bishop to a prophetic voice for the poor during El Salvador's civil war makes his homilies a uniquely important historical and theological corpus.

This project helps researchers understand that transformation through the words Romero chose, week after week, as violence escalated around him.
