#!/usr/bin/env python3
"""
Flask web app for browsing Romero homilies.
"""

from flask import Flask, render_template, send_file, abort
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = 'romero.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


@app.route('/')
def index():
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
            spanish_text IS NOT NULL as has_spanish,
            english_text IS NOT NULL as has_english,
            spanish_pdf_path,
            english_pdf_path,
            detail_url
        FROM homilies
        ORDER BY date ASC
    ''')

    homilies = cursor.fetchall()
    conn.close()

    return render_template('index.html', homilies=homilies)


@app.route('/pdf/<path:pdf_path>')
def serve_pdf(pdf_path):
    """Serve a PDF file. Path already includes 'homilies/' prefix."""
    file_path = Path(pdf_path)

    # Security: ensure the path doesn't escape directories
    if '..' in str(file_path) or file_path.is_absolute():
        abort(404)

    # Path from database already includes "homilies/" prefix
    if not file_path.exists() or not file_path.is_file():
        abort(404)

    return send_file(file_path, mimetype='application/pdf')


if __name__ == '__main__':
    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        print("Run build_database.py first")
        exit(1)

    print("Starting Romero Homilies Viewer")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
