#!/usr/bin/env python3
"""
Простой генератор: для каждой книги в outputs (папки с chapters_summary.json)
попытается взять normalized text из outputs/processed/<book>_normalized.txt или
если его нет — попробовать data/raw/<book>.txt (не нормализованный).
Затем запускает token_freq_by_chapter.py для каждой книги.
"""
import subprocess
from pathlib import Path
import sys

# Project root (two levels up from src/scripts -> repo root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUTS = PROJECT_ROOT / 'outputs'
PROCESSED = OUTPUTS / 'processed'
RAW = PROJECT_ROOT / 'data' / 'raw'
SCRIPT = PROJECT_ROOT / 'src' / 'scripts' / 'token_freq_by_chapter.py'


def find_books():
    books = []
    if OUTPUTS.exists():
        for p in OUTPUTS.iterdir():
            if p.is_dir():
                chap = p / 'chapters_summary.json'
                if chap.exists():
                    books.append(p.name)
    # Also include raw files not in outputs
    for p in RAW.rglob('*.txt'):
        name = p.stem
        if name not in books:
            books.append(name)
    return sorted(books)


def main():
    books = find_books()
    if not books:
        print('No books found')
        return
    for b in books:
        print('Processing', b)
        # choose text path
        norm = PROCESSED / f'{b}_normalized.txt'
        if norm.exists():
            text = norm
        else:
            raw_alt = RAW / f'{b}.txt'
            if raw_alt.exists():
                text = raw_alt
            else:
                print('  -> no text for', b, ', skipping')
                continue
        chapters = OUTPUTS / b / 'chapters_summary.json'
        if not chapters.exists():
            print('  -> no chapters_summary for', b, ', skipping')
            continue
        outp = OUTPUTS / b / 'token_freq_by_chapter.csv'
        cmd = [sys.executable, str(SCRIPT), '--text', str(text), '--chapters', str(chapters), '--output', str(outp)]
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print('  -> script failed for', b)


if __name__ == '__main__':
    main()
