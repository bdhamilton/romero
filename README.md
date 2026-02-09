# Romero Ngram Viewer

A text analysis tool for Oscar Romero's homilies (1977-1980), modeled after Google's Ngram Viewer. Search for any word or phrase in Spanish and see how its frequency changed over the three years of Romero's preaching.

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/bdhamilton/romero.git
cd romero

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run the web app
python app.py
# Open http://localhost:5000
```

The ngram viewer is the main page. Browse all homilies at `/browse` (includes known data issues and links to PDFs on the Romero Trust site).

There's also a CLI tool for terminal use:

```bash
python ngram.py pueblo                         # raw count
python ngram.py "pueblo de dios" --norm words  # per 10k words
python ngram.py justicia --norm homilies       # per homily
```

To rebuild the database from scratch (downloads from Romero Trust, ~20 minutes):

```bash
python build_database.py
```

## Data Source

All homilies sourced from [The Romero Trust](https://www.romerotrust.org.uk/homilies-and-writing/homilies/), which provides PDFs and audio recordings of Romero's preaching. When complete, this site will just act as a window back to the Romero Trust website--a different way of viewing their data, rather than a duplication of their data.

**Coverage:**
- **195 homilies** from March 14, 1977 (his first homily as Archbishop) to March 24, 1980 (day of assassination)
- **Spanish text** extracted for 186 homilies (9 missing — mostly audio-only or special events)
- **English text** extracted for 188 homilies (7 missing)
- **Audio recordings** for 172 homilies (~88%)