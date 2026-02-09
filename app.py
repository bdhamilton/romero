#!/usr/bin/env python3
"""
Flask web app for Romero Ngram Viewer and homily browsing.
"""

from flask import Flask, render_template, abort, request, jsonify
import sqlite3
from pathlib import Path
from search import search_corpus

app = Flask(__name__)

DB_PATH = 'romero.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def ngram_viewer():
    """Ngram viewer — main page."""
    return render_template('ngram.html')


@app.route('/browse')
def browse():
    """Show all homilies in a table."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            id,
            date,
            occasion,
            english_title,
            spanish_title,
            biblical_references,
            spanish_pdf_url,
            english_pdf_url,
            detail_url,
            spanish_text IS NULL as missing_spanish,
            english_text IS NULL as missing_english
        FROM homilies
        ORDER BY date ASC
    ''')

    homilies = cursor.fetchall()
    conn.close()

    return render_template('index.html', homilies=homilies)


@app.route('/api/search')
def api_search():
    """JSON API for ngram search."""
    term = request.args.get('term', '').strip()
    accent_sensitive = request.args.get('accent_sensitive', '0') == '1'

    if not term:
        return jsonify({'error': 'No search term provided'}), 400

    result = search_corpus(term, db_path=DB_PATH, accent_sensitive=accent_sensitive)

    # Convert OrderedDict to list for JSON serialization
    months = []
    for month, data in result['months'].items():
        months.append({
            'month': month,
            'count': data['count'],
            'total_words': data['total_words'],
            'num_homilies': data['num_homilies'],
            'per_10k_words': round(data['per_10k_words'], 2),
            'per_homily': round(data['per_homily'], 2),
            'homilies': data['homilies'],
        })

    return jsonify({
        'term': result['term'],
        'tokens': result['tokens'],
        'elapsed': round(result['elapsed'], 3),
        'total_count': result['total_count'],
        'total_homilies': result['total_homilies'],
        'months': months,
    })



if __name__ == '__main__':
    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        print("Run build_database.py first")
        exit(1)

    print("Starting Romero Ngram Viewer")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
