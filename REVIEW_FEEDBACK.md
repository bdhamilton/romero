# Romero Ngram Viewer - Code Review Feedback

**Review Date:** February 9, 2026  
**Reviewer:** GitHub Copilot Code Review  
**Repository:** bdhamilton/romero  
**Commit:** b1085bd

---

## Executive Summary

This is a well-structured, educational research tool with clean architecture and thoughtful design. The project successfully demonstrates text analysis capabilities for Archbishop Romero's homilies with a Google Ngram-style interface. The code is readable, maintainable, and follows good security practices.

**Overall Assessment:** ⭐⭐⭐⭐ (4/5)

**Strengths:**
- Clean, minimal codebase (~1,500 lines total)
- Excellent documentation (CLAUDE.md is comprehensive)
- Good security practices (parameterized SQL queries)
- Thoughtful architecture decisions
- Educational value (well-commented, explains trade-offs)

**Key Areas for Improvement:**
1. Missing test coverage
2. No error handling for database failures
3. Missing CORS configuration for API
4. No rate limiting on API endpoints
5. Incomplete deployment documentation

---

## Detailed Findings

### 1. Code Quality ⭐⭐⭐⭐⭐

**Strengths:**
- **Readability**: Code is clean and well-organized with clear function names
- **Documentation**: Excellent inline comments and docstrings
- **Structure**: Logical separation of concerns (search.py, app.py, ngram.py)
- **Simplicity**: Follows "simple over complex" principle effectively
- **Consistency**: Consistent coding style throughout

**Examples of Good Practice:**
```python
# search.py - Clear function with descriptive docstring
def fold_accents(text):
    """Strip diacritical marks (á→a, ñ→n, etc.) for accent-insensitive matching."""
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
```

**Minor Suggestions:**
- Consider adding type hints for better IDE support (Python 3.5+)
- Could extract some magic numbers to constants (e.g., Chart.js color values)

### 2. Security ⭐⭐⭐⭐

**Strengths:**
- ✅ Parameterized SQL queries throughout (no SQL injection risk)
- ✅ Input sanitization with `.strip()` on user inputs
- ✅ Flask's `int` converter prevents injection in route parameters
- ✅ No hardcoded secrets or credentials
- ✅ Safe use of `__import__` (only for dependency checking)

**Vulnerabilities Found:** None critical

**Recommendations:**

#### a) Add CSRF Protection (Medium Priority)
The flag submission form is vulnerable to Cross-Site Request Forgery:

```python
# Current code (app.py, line 125)
if request.method == 'POST':
    comment = request.form.get('comment', '').strip()
```

**Fix:** Add Flask-WTF for CSRF protection:
```python
# Add to requirements.txt
flask-wtf>=1.2.0

# In app.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
```

#### b) Add Rate Limiting (Medium Priority)
The `/api/search` endpoint has no rate limiting, which could lead to abuse:

```python
# Recommendation: Add Flask-Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/search')
@limiter.limit("30 per minute")
def api_search():
    ...
```

#### c) Add Content Security Policy (Low Priority)
Consider adding CSP headers to prevent XSS:

```python
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

### 3. Error Handling ⭐⭐⭐

**Issues Found:**

#### a) Database Connection Failures Not Handled
```python
# app.py, line 16-20
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
```

**Problem:** If database is missing or corrupted, users get a cryptic error.

**Fix:**
```python
def get_db():
    """Get database connection."""
    if not Path(DB_PATH).exists():
        abort(500, description="Database not found. Please rebuild the database.")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
```

#### b) Search API Error Handling Incomplete
The `/api/search` endpoint doesn't catch exceptions from `search_corpus()`:

```python
# Add try-except in api_search()
@app.route('/api/search')
def api_search():
    term = request.args.get('term', '').strip()
    if not term:
        return jsonify({'error': 'No search term provided'}), 400
    
    try:
        result = search_corpus(term, db_path=DB_PATH)
        # ... rest of function
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500
```

#### c) No Custom Error Pages
Add custom error handlers for better UX:

```python
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message="Server error"), 500
```

### 4. Testing ⭐⭐

**Critical Gap:** No test suite exists.

**Impact:** Changes could break functionality without detection.

**Recommendations:**

#### a) Add Unit Tests for Core Logic
```python
# tests/test_search.py
import pytest
from search import fold_accents, tokenize, search_corpus

def test_fold_accents():
    assert fold_accents("ángel") == "angel"
    assert fold_accents("José") == "Jose"
    assert fold_accents("ñoño") == "nono"

def test_tokenize():
    assert tokenize("pueblo de dios") == ["pueblo", "de", "dios"]
    assert tokenize("Iglesia, universal") == ["iglesia", "universal"]

def test_phrase_search():
    # Requires test database
    result = search_corpus("pueblo", db_path="test_romero.db")
    assert 'term' in result
    assert 'months' in result
    assert result['total_count'] >= 0
```

#### b) Add Integration Tests for Flask App
```python
# tests/test_app.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_ngram_viewer_loads(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Romero Ngram Viewer' in rv.data

def test_api_search_requires_term(client):
    rv = client.get('/api/search')
    assert rv.status_code == 400
    data = rv.get_json()
    assert 'error' in data

def test_api_search_returns_results(client):
    rv = client.get('/api/search?term=pueblo')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'months' in data
```

#### c) Add Test Configuration
```python
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short

# requirements-dev.txt
pytest>=7.4.0
pytest-flask>=1.2.0
pytest-cov>=4.1.0
```

### 5. Performance ⭐⭐⭐⭐

**Current Performance:** Excellent for corpus size (186 texts, ~6MB)
- Search time: ~0.6 seconds (acceptable)
- No pre-built index needed (good trade-off)

**Scalability Concerns:**
- Linear scan doesn't scale beyond 10x corpus size
- Database loaded in memory on each request

**Recommendations for Future:**

#### a) Add Database Connection Pooling
When scaling beyond single-user:
```python
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()
```

#### b) Consider Caching for Common Queries
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def search_corpus_cached(term, db_path, accent_sensitive):
    return search_corpus(term, db_path, accent_sensitive)
```

#### c) Add Progress Indication for Long Searches
For multi-term searches (Phase 2), consider:
- Server-Sent Events (SSE) for progress updates
- Async task queue (Celery) for background processing

### 6. User Experience ⭐⭐⭐⭐

**Strengths:**
- Clean, Google-inspired UI
- Intuitive search interface
- Drill-down functionality works well
- Responsive design

**Improvements:**

#### a) Add Loading Spinner
```javascript
// In ngram.html
async function doSearch(term) {
    const status = document.getElementById('status');
    status.innerHTML = '<span class="spinner">⏳</span> Searching...';
    // ... rest of function
}
```

#### b) Add Keyboard Shortcuts
```javascript
// Escape to clear search
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.getElementById('term').value = '';
        document.getElementById('term').focus();
    }
});
```

#### c) Improve Mobile Experience
- Touch targets could be larger (especially example links)
- Consider collapsible controls on small screens

#### d) Add Context Snippets in Drill-down
Currently shows homily count but not the surrounding text:
```python
# In search.py, add context extraction:
def extract_context(text, term, context_chars=100):
    """Extract text surrounding first occurrence of term."""
    # Implementation needed
```

### 7. Documentation ⭐⭐⭐⭐⭐

**Strengths:**
- CLAUDE.md is exceptional (comprehensive, well-organized)
- README.md covers quick start perfectly
- Code comments explain "why" not just "what"
- Phase notes document decisions and learnings

**Minor Gaps:**

#### a) API Documentation
Add API docs for external consumers:
```markdown
## API Documentation

### GET /api/search

Search for a word or phrase in Spanish homilies.

**Parameters:**
- `term` (required): Word or phrase to search
- `accent_sensitive` (optional): '1' for exact accent matching

**Response:**
```json
{
  "term": "pueblo",
  "tokens": ["pueblo"],
  "elapsed": 0.612,
  "total_count": 543,
  "total_homilies": 89,
  "months": [...]
}
```
```

#### b) Deployment Guide
Add deployment documentation:
```markdown
# DEPLOYMENT.md

## Production Deployment

### Requirements
- Python 3.8+
- 512MB RAM minimum
- 500MB disk space

### Environment Variables
```bash
export FLASK_APP=app.py
export FLASK_ENV=production
export SECRET_KEY="your-secret-key-here"
```

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```
```

#### c) Contributing Guide
For Phase 2 collaborators:
```markdown
# CONTRIBUTING.md

## Development Setup
1. Fork and clone
2. Create virtual environment
3. Install dependencies
4. Run tests (when added)

## Code Style
- Follow PEP 8
- Use descriptive variable names
- Add docstrings to all functions
- Comment complex logic

## Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Reference issues when applicable
```

### 8. Dependencies ⭐⭐⭐⭐

**Current Dependencies:** Minimal and appropriate
- requests, beautifulsoup4 (scraping)
- pdfplumber (text extraction)
- flask (web framework)

**Security:**
- No known vulnerabilities in specified versions
- Versions are pinned with `>=` (good for security updates)

**Recommendations:**

#### a) Pin Exact Versions for Production
```txt
# requirements-prod.txt
requests==2.31.0
beautifulsoup4==4.12.0
pdfplumber==0.10.0
flask==3.0.0
```

#### b) Add Development Dependencies
```txt
# requirements-dev.txt
pytest>=7.4.0
pytest-flask>=1.2.0
pytest-cov>=4.1.0
black>=23.0.0  # Code formatting
flake8>=6.0.0  # Linting
mypy>=1.5.0    # Type checking
```

#### c) Add Dependency Security Scanning
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install safety
      - run: safety check -r requirements.txt
```

### 9. Architecture ⭐⭐⭐⭐⭐

**Strengths:**
- Appropriate technology choices for scale
- Clear separation of concerns
- SQLite is perfect for this use case
- No over-engineering

**Design Decisions Validated:**
- ✅ No pre-built ngram index (corpus small enough)
- ✅ Brute-force search (fast enough at ~0.6s)
- ✅ Monthly aggregation (appropriate granularity)
- ✅ Flat database structure (simple, effective)

**Future Considerations:**

#### a) Phase 1.5: Data Curation System
The plan for a `status` column is good. Consider:
```sql
ALTER TABLE homilies ADD COLUMN status TEXT DEFAULT 'active';
CREATE INDEX idx_status ON homilies(status);

-- Then filter in queries:
WHERE spanish_text IS NOT NULL AND status = 'active'
```

#### b) Phase 2: Cross-Language Analysis
Architecture supports this well. Suggested approach:
```python
def search_corpus_multilang(term, language='spanish', db_path='romero.db'):
    text_column = 'spanish_text' if language == 'spanish' else 'english_text'
    # ... rest of implementation
```

### 10. Accessibility ⭐⭐⭐

**Current State:**
- ✅ Semantic HTML structure
- ✅ Keyboard navigation works
- ⚠️ Missing ARIA labels on interactive elements
- ⚠️ No skip navigation link
- ⚠️ Color contrast needs verification

**Recommendations:**

#### a) Add ARIA Labels
```html
<input type="text" id="term" name="term"
       aria-label="Search term"
       placeholder="Enter a word or phrase in Spanish...">
```

#### b) Add Skip Navigation
```html
<a href="#main-content" class="skip-nav">Skip to main content</a>
```

#### c) Improve Chart Accessibility
```javascript
// Add data table fallback for screen readers
chartInstance = new Chart(document.getElementById('chart'), {
    options: {
        plugins: {
            legend: {
                labels: {
                    generateLabels: function(chart) {
                        // Ensure screen reader can access data
                    }
                }
            }
        }
    }
});
```

---

## Priority Recommendations

### Must Do (Before Public Launch)
1. ✅ **Add CSRF protection** - Security vulnerability
2. ✅ **Add error handling for database failures** - UX critical
3. ✅ **Add rate limiting to API** - Prevent abuse
4. ✅ **Create deployment documentation** - Needed for Phase 2

### Should Do (Next Sprint)
5. ✅ **Add basic test suite** - Prevent regressions
6. ✅ **Add custom error pages** - Better UX
7. ✅ **Add CORS configuration** - Enable external API use
8. ✅ **Add database connection pooling** - Performance

### Nice to Have (Future)
9. ✅ **Add loading indicators** - UX polish
10. ✅ **Add context snippets** - Research value
11. ✅ **Improve accessibility** - Reach wider audience
12. ✅ **Add keyboard shortcuts** - Power user features

---

## Specific Code Improvements

### 1. Add Configuration Management

**File: `config.py`** (new)
```python
import os
from pathlib import Path

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'romero.db')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    MAX_SEARCH_RESULTS = 1000
    API_RATE_LIMIT = "30 per minute"

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
```

**Update `app.py`:**
```python
from config import Config, DevelopmentConfig, ProductionConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig if os.environ.get('FLASK_DEBUG') else ProductionConfig)
```

### 2. Add Logging

**In `app.py`:**
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('romero.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Romero Ngram Viewer startup')
```

### 3. Add Health Check Endpoint

**In `app.py`:**
```python
@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM homilies')
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'status': 'healthy',
            'homilies': count,
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
```

### 4. Improve Search Performance

**In `search.py`:**
```python
def search_corpus(term, db_path='romero.db', accent_sensitive=False, max_results=None):
    """
    Search all Spanish homily texts for a word or phrase.
    
    Args:
        term: Search term
        db_path: Path to database
        accent_sensitive: Whether to match accents exactly
        max_results: Optional limit on number of homilies to return
    """
    # ... existing code ...
    
    # Add early termination if max_results reached
    if max_results and total_homilies >= max_results:
        break
```

---

## Potential Issues

### Issue 1: Memory Usage with Large Corpus
**Severity:** Low (current corpus is small)  
**Impact:** If corpus grows 10x, current approach may be slow

**Current Code:**
```python
# Loads all texts into memory
rows = conn.execute(
    'SELECT id, date, occasion, spanish_title, spanish_text, detail_url '
    'FROM homilies WHERE spanish_text IS NOT NULL ORDER BY date'
).fetchall()
```

**Recommendation:** Add pagination or streaming for Phase 3+
```python
# For future: stream results
cursor = conn.execute('...').cursor()
for row in cursor:
    # Process one row at a time
```

### Issue 2: Concurrent Flag Submissions
**Severity:** Low  
**Impact:** Race condition could cause duplicate flags

**Current Code:**
```python
# No transaction isolation
conn.execute('INSERT INTO flags (homily_id, comment) VALUES (?, ?)', ...)
conn.commit()
```

**Fix:**
```python
with conn:
    # Automatic transaction handling
    conn.execute('INSERT INTO flags (homily_id, comment) VALUES (?, ?)', ...)
```

### Issue 3: No Input Length Limits
**Severity:** Low  
**Impact:** Could submit very long comments

**Fix:**
```python
MAX_COMMENT_LENGTH = 1000

if request.method == 'POST':
    comment = request.form.get('comment', '').strip()
    if not comment:
        flash('Comment cannot be empty', 'error')
    elif len(comment) > MAX_COMMENT_LENGTH:
        flash(f'Comment too long (max {MAX_COMMENT_LENGTH} characters)', 'error')
    else:
        # Process comment
```

---

## Testing Checklist

### Manual Testing Needed
- [ ] Test search with special characters: `"pueblo!@#$%"`
- [ ] Test search with very long terms (>100 characters)
- [ ] Test empty search
- [ ] Test all example links
- [ ] Test drill-down on months with 0 results
- [ ] Test flag submission with empty comment
- [ ] Test flag submission with very long comment
- [ ] Test browse page with missing PDFs
- [ ] Test mobile responsiveness
- [ ] Test with screen reader
- [ ] Test with JavaScript disabled
- [ ] Test browser back button navigation
- [ ] Load test API endpoint (100 concurrent requests)

### Automated Testing Needed
- [ ] Unit tests for `fold_accents()`
- [ ] Unit tests for `tokenize()`
- [ ] Unit tests for `search_corpus()`
- [ ] Integration tests for all routes
- [ ] API endpoint tests
- [ ] Database constraint tests
- [ ] Performance benchmark tests

---

## Security Checklist

- [x] SQL injection prevention (parameterized queries)
- [x] No hardcoded secrets
- [x] Input sanitization (`.strip()` on user inputs)
- [ ] CSRF protection on forms
- [ ] Rate limiting on API endpoints
- [ ] Content Security Policy headers
- [ ] HTTPS enforcement (deployment)
- [ ] Secure session configuration
- [ ] Input length validation
- [ ] File upload validation (if added)
- [ ] XSS prevention (Flask auto-escapes, but verify)
- [ ] Dependency vulnerability scanning
- [ ] Security headers (CSP, X-Frame-Options, etc.)

---

## Performance Metrics

### Current Performance
- **Search Time:** ~0.6s for typical query
- **Database Size:** 13 MB (expected, not verified in review)
- **Memory Usage:** Unknown (needs profiling)
- **Page Load Time:** Unknown (needs measurement)

### Recommended Targets
- **Search Time:** <1s for 95th percentile
- **Page Load Time:** <2s (first contentful paint)
- **API Response Time:** <1s for 95th percentile
- **Memory Usage:** <100MB per process

### Monitoring Recommendations
```python
# Add timing decorator
import time
from functools import wraps

def timing(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        elapsed = time.time() - start
        app.logger.info(f'{f.__name__} took {elapsed:.3f}s')
        return result
    return wrap

@app.route('/api/search')
@timing
def api_search():
    ...
```

---

## Future Enhancements

### Phase 1.5: Data Curation (In Progress)
- ✅ Flag system implemented
- ⏳ Status column for homilies
- ⏳ Changelog table for audit trail
- ⏳ CLI tool for data corrections

### Phase 2: Enhancements
- [ ] English corpus with language toggle
- [ ] Multi-term comparison
- [ ] Wildcards and stemming
- [ ] Context snippets in drill-down

### Phase 3: Research Features
- [ ] Export functionality (CSV, JSON)
- [ ] Historical event overlay
- [ ] Biblical reference integration
- [ ] Audio integration

### Technical Debt
- [ ] Add comprehensive test suite
- [ ] Add type hints throughout
- [ ] Improve error handling
- [ ] Add monitoring/observability
- [ ] Document deployment process

---

## Conclusion

This is a **high-quality research project** with clear educational value. The code demonstrates thoughtful architecture decisions, clean implementation, and good documentation practices. The main gaps are in testing, error handling, and deployment readiness—all addressable issues.

The project is well-positioned for Phase 2 development. The architecture scales appropriately for the corpus size, and the codebase is maintainable enough for future collaborators.

### Key Strengths
1. **Clean Architecture** - Appropriate technology choices
2. **Excellent Documentation** - CLAUDE.md is exemplary
3. **Good Security Practices** - Parameterized queries throughout
4. **Educational Value** - Code teaches text analysis concepts
5. **User Experience** - Intuitive interface inspired by Google Ngrams

### Critical Next Steps
1. Add CSRF protection before public deployment
2. Implement comprehensive error handling
3. Add basic test suite for core functionality
4. Document deployment process
5. Add rate limiting to API

### Estimated Effort
- **Priority 1 (Must Do):** ~8 hours
- **Priority 2 (Should Do):** ~16 hours
- **Priority 3 (Nice to Have):** ~24 hours

**Overall:** This project is production-ready with the Priority 1 improvements implemented. Great work! 🎉

---

## Additional Resources

### Recommended Reading
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/3.0.x/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Web Content Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/WCAG21/quickref/)

### Tools to Consider
- **Black** - Code formatter
- **Flake8** - Linter
- **MyPy** - Type checker
- **Pytest** - Testing framework
- **Safety** - Dependency vulnerability scanner
- **Lighthouse** - Performance and accessibility audits
