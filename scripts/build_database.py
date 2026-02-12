#!/usr/bin/env python3
"""
Master orchestration script to build the complete Romero database from scratch.

This script runs the entire data collection pipeline:
1. Scrape metadata from Romero Trust website
2. Download all PDFs into hierarchical structure
3. Extract text from PDFs
4. Create SQLite database and load all data

Usage:
    python build_database.py [--skip-scrape] [--skip-download]

Options:
    --skip-scrape    Skip metadata scraping (use existing homilies_metadata.json)
    --skip-download  Skip PDF downloads (use existing PDFs)

Time estimate:
    Full run: ~15-20 minutes
    With --skip-download: ~3-5 minutes
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import shutil
import time

# Ensure we run from the project root regardless of where the script lives
PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == 'scripts':
    PROJECT_ROOT = PROJECT_ROOT.parent


def run_script(script_path, description, auto_yes=False):
    """
    Run a Python script and check for errors.

    Args:
        script_path: Path to the script to run
        description: Human-readable description for logging
        auto_yes: If True, pipe 'y' to stdin for interactive prompts

    Returns:
        True if successful, False if error occurred
    """
    print("\n" + "="*70)
    print(f"STEP: {description}")
    print("="*70)

    cmd = [sys.executable, script_path]

    if auto_yes:
        # Pipe 'y\n' to stdin for interactive prompts
        result = subprocess.run(
            cmd,
            input='y\n',
            text=True,
            capture_output=False  # Show output in real-time
        )
    else:
        result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ ERROR: {description} failed with exit code {result.returncode}")
        return False

    print(f"\n✓ {description} completed successfully")
    return True


def check_dependencies():
    """Verify all required Python packages are installed."""
    print("Checking dependencies...")

    required = ['requests', 'bs4', 'pdfplumber']
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"\n❌ Missing required packages: {', '.join(missing)}")
        print("\nInstall them with:")
        print("    pip install -r requirements.txt")
        return False

    print("✓ All dependencies installed")
    return True


def main():
    """Main orchestration logic."""
    start_time = time.time()

    # Parse command-line arguments
    skip_scrape = '--skip-scrape' in sys.argv
    skip_download = '--skip-download' in sys.argv

    print("""
╔═══════════════════════════════════════════════════════════════════╗
║            Romero Text Explorer - Data Collection                  ║
║          Builds database from Romero Trust website                ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Track which steps to run
    steps = []

    if not skip_scrape:
        steps.append((str(PROJECT_ROOT / 'scripts/01_scrape_all_metadata.py'), 'Scrape metadata from Romero Trust', False))
    else:
        print("\n⏭  Skipping metadata scraping (using existing data)")
        if not (PROJECT_ROOT / 'archive/homilies_metadata.json').exists():
            print("❌ ERROR: archive/homilies_metadata.json not found")
            print("   Cannot skip scraping without existing metadata file")
            sys.exit(1)

    if not skip_download:
        steps.append((str(PROJECT_ROOT / 'scripts/02_download_pdfs.py'), 'Download all PDFs into date hierarchy (~12 min)', True))
    else:
        print("\n⏭  Skipping PDF downloads (using existing PDFs)")
        if not (PROJECT_ROOT / 'homilies').exists():
            print("❌ ERROR: homilies/ directory not found")
            print("   Cannot skip downloads without existing PDFs")
            sys.exit(1)

    # These steps always run
    steps.append((str(PROJECT_ROOT / 'scripts/03_extract_text.py'), 'Extract text from all PDFs', True))
    steps.append((str(PROJECT_ROOT / 'scripts/04_create_database.py'), 'Create SQLite database and load data', False))
    steps.append((str(PROJECT_ROOT / 'scripts/build_search_index.py'), 'Build search index (pre-fold text)', False))

    # Summary
    print(f"\nPipeline: {len(steps)} steps to execute")
    print(f"Estimated time: {'~3-5 minutes' if skip_download else '~15-20 minutes'}")
    print()

    # Confirm before starting (unless running non-interactively)
    if sys.stdin.isatty():
        response = input("Continue? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    # Backup existing database before doing anything destructive
    db_path = PROJECT_ROOT / 'romero.db'
    if db_path.exists():
        timestamp = datetime.now().strftime('%Y-%m-%dT%H%M')
        backup_path = PROJECT_ROOT / f'romero.db.backup.{timestamp}'
        shutil.copy2(db_path, backup_path)
        print(f"\n✓ Backed up existing database to {backup_path.name}")

    # Execute pipeline
    for i, (script, description, auto_yes) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] Starting: {description}")

        if not run_script(script, description, auto_yes):
            print("\n" + "="*70)
            print("PIPELINE FAILED")
            print("="*70)
            print(f"\nFailed at step {i}/{len(steps)}: {description}")
            print("\nThe pipeline is resumable. Fix the error and run again.")
            print("Most scripts skip already-completed work.")
            sys.exit(1)

    # Success!
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n" + "="*70)
    print("✓ PIPELINE COMPLETE!")
    print("="*70)
    print(f"\nTotal time: {minutes}m {seconds}s")
    print(f"\nDatabase location: romero.db")

    # Show database stats
    try:
        import sqlite3
        conn = sqlite3.connect(str(PROJECT_ROOT / 'romero.db'))
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM homilies')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM homilies WHERE spanish_text IS NOT NULL')
        spanish_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM homilies WHERE english_text IS NOT NULL')
        english_count = cursor.fetchone()[0]

        print(f"\nDatabase contains:")
        print(f"  {total} homilies")
        print(f"  {spanish_count} Spanish texts ({spanish_count/total*100:.1f}%)")
        print(f"  {english_count} English texts ({english_count/total*100:.1f}%)")

        cursor.execute('SELECT MIN(date), MAX(date) FROM homilies')
        min_date, max_date = cursor.fetchone()
        print(f"  Date range: {min_date} to {max_date}")

        db_size = (PROJECT_ROOT / 'romero.db').stat().st_size / 1024 / 1024
        print(f"  File size: {db_size:.2f} MB")

        conn.close()
    except Exception as e:
        print(f"\n(Could not read database stats: {e})")

    print("\n✓ Ready for Phase 1: Ngram indexing and search")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        print("Run again to resume from where you left off")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
