# Romero Ngram Viewer

A work-in-progress text analysis tool for Oscar Romero's homilies (1977-1980), modeled after Google's Ngram Viewer.

## Project Status

I've set up a script pipeline that extracts and organizes the data on the Romero Trust website in a SQLite database. You can run it yourself:

```bash
# 1. Clone repository
git clone https://github.com/bdhamilton/romero.git
cd romero

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run data collection pipeline (takes ~20 minutes)
python ./build_database.py

# Result: romero.db (SQLite database with full corpus)
```

I've also set up an index to manually review the data. Run it with:

```bash
python app.py
```

Once the data is reviewed and confirmed, I'll start building the ngram index and visualization tools.

## Data Source

All homilies sourced from [The Romero Trust](https://www.romerotrust.org.uk/homilies-and-writing/homilies/), which provides PDFs and audio recordings of Romero's preaching. When complete, this site will just act as a window back to the Romero Trust website--a different way of viewing their data, rather than a duplication of their data.

**Coverage:**
- **195 homilies** from March 14, 1977 (his first homily as Archbishop) to March 24, 1980 (day of assassination)
- **Spanish originals** (185 available, ~95%)
- **English translations** (189 available, ~97%)
- **Audio recordings** for 172 homilies (~88%)