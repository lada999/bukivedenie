#!/usr/bin/env python3
"""
Простой HTTP сервер для просмотра исходного текста и результатов анализа через localhost.
Запуск:
    python -m src.webapp --host 127.0.0.1 --port 8000

Откройте в браузере: http://127.0.0.1:8000/
"""

import argparse
import html
import json
import os
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote_plus
import json as _json
import subprocess
import sys

_BOOK_SUMMARY_CACHE = {}

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUTPUTS_DIR = PROJECT_ROOT / 'outputs'
RAW_DIR = PROJECT_ROOT / 'data' / 'raw'
WEB_ROOT = PROJECT_ROOT / 'frontend'

# Known external raw path for Chekhov sample (if present on device)
ALT_CHEKHOV_PATH = Path('/storage/emulated/0/Documents/чехов-письмо.txt')


def _raw_books_index():
    """Return {book_id: raw_relative_path} derived from data/raw."""
    if not RAW_DIR.exists():
        return {}
    items = {}
    for p in sorted(RAW_DIR.rglob('*.txt')):
        try:
            rel = p.relative_to(RAW_DIR).as_posix()
        except Exception:
            rel = p.name
        book_id = p.stem
        if book_id not in items:
            items[book_id] = rel
    return items


def _book_ready(book: str) -> bool:
    return bool(list_files(book))


def list_books():
    index = _raw_books_index()
    return sorted(index.keys())


def list_book_states():
    index = _raw_books_index()
    items = []
    for book in sorted(index.keys()):
        raw = index[book]
        items.append({
            'book': book,
            'raw': raw,
            'ready': _book_ready(book),
            'analysis': f'/api/run_analysis?raw={raw}',
        })
    return items


def list_files(book: str):
    """
    List files for a book. Primary source is outputs/<book> directory.
    If that directory does not exist, also search common output folders (outputs/tables)
    for files that include the book id as prefix (e.g. test_book_tokens.csv) and return
    them as relative paths (e.g. 'tables/test_book_tokens.csv') so frontend can request
    /api/file?book=tables&name=test_book_tokens.csv.
    """
    book_dir = OUTPUTS_DIR / book
    files = []
    # collect files from book directory if present
    if book_dir.exists() and book_dir.is_dir():
        for p in book_dir.iterdir():
            if p.is_file():
                files.append(p.name)

    # Fallback: search in OUTPUTS_DIR/tables and OUTPUTS_DIR/processed for files named with book prefix
    tables_dir = OUTPUTS_DIR / 'tables'
    if tables_dir.exists() and tables_dir.is_dir():
        for p in tables_dir.iterdir():
            if p.is_file() and p.name.lower().startswith(book.lower() + '_'):
                files.append(str(Path('tables') / p.name))

    processed_dir = OUTPUTS_DIR / 'processed'
    if processed_dir.exists() and processed_dir.is_dir():
        for p in processed_dir.iterdir():
            if p.is_file() and p.name.lower().startswith(book.lower() + '_'):
                files.append(str(Path('processed') / p.name))

    # also search top-level outputs for files starting with book_
    for p in OUTPUTS_DIR.iterdir():
        if p.is_file() and p.name.lower().startswith(book.lower() + '_'):
            files.append(p.name)
    # dedupe and sort
    uniq = sorted(dict.fromkeys(files))
    return uniq


def ensure_log_dir():
    logdir = PROJECT_ROOT / 'logs'
    try:
        logdir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return logdir

LOG_DIR = ensure_log_dir()
LOG_PATH = LOG_DIR / 'webapp.log'

def slog(msg):
    try:
        from datetime import datetime
        s = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ') + ' ' + str(msg) + '\n'
        with open(LOG_PATH, 'a', encoding='utf-8') as fh:
            fh.write(s)
    except Exception:
        pass


def list_raw_files():
    """Return raw files; include ALT_CHEKHOV_PATH if present (adds it as 'чехов-письмо.txt' logical name).
    If RAW_DIR contains a file with the same name, prefer that one.
    """
    files = []
    if RAW_DIR.exists():
        files = sorted([p.name for p in RAW_DIR.iterdir() if p.is_file() and p.suffix.lower() in ('.txt',)])
    # If an external Chekhov file exists, ensure it's listed (logical name)
    try:
        if ALT_CHEKHOV_PATH.exists():
            logical = 'чехов-письмо.txt'
            if logical not in files:
                files = [logical] + files
    except Exception:
        pass
    return files


def _read_csv_rows(path: Path, limit: int | None = None):
    import csv
    rows = []
    with open(path, 'r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            normalized = {}
            for key, value in row.items():
                if value is None:
                    normalized[key] = value
                    continue
                text = value.strip()
                if key in ('count', 'rank', 'chapters', 'tokens', 'words', 'punctuation_marks'):
                    try:
                        normalized[key] = int(float(text))
                        continue
                    except Exception:
                        pass
                if key == 'per_1k':
                    try:
                        normalized[key] = float(text)
                        continue
                    except Exception:
                        pass
                normalized[key] = value
            rows.append(normalized)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _load_chapters_summary(book_dir: Path):
    path = book_dir / 'chapters_summary.json'
    if not path.exists():
        return []
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    if isinstance(parsed, dict):
        parsed = parsed.get('chapters') or []
    return parsed if isinstance(parsed, list) else []


def _load_book_summary(book: str):
    book_dir = OUTPUTS_DIR / book
    tokens_path = book_dir / 'tokens.csv'
    chapters_path = book_dir / 'chapters_summary.json'
    punct_path = book_dir / 'punctuation_counts.csv'
    cache_key = (
        book,
        str(book_dir),
        str(tokens_path.stat().st_mtime_ns) if tokens_path.exists() else 'missing',
        str(chapters_path.stat().st_mtime_ns) if chapters_path.exists() else 'missing',
        str(punct_path.stat().st_mtime_ns) if punct_path.exists() else 'missing',
    )
    cached = _BOOK_SUMMARY_CACHE.get(book)
    if cached and cached[0] == cache_key:
        return cached[1]

    chapters = _load_chapters_summary(book_dir)

    text_index = _read_csv_rows(tokens_path, limit=1000) if tokens_path.exists() else []
    punctuation_timeline = _read_csv_rows(punct_path, limit=1000) if punct_path.exists() else []

    summary = {
        'chapters': len(chapters),
        'words': sum(int(ch.get('total_words') or 0) for ch in chapters if isinstance(ch, dict)),
        'tokens': len(text_index),
        'punctuation_marks': len(punctuation_timeline),
    }
    payload = {
        'book': book,
        'ready': bool(text_index or chapters or punctuation_timeline),
        'summary': summary,
        'text_index': text_index,
        'fragments': chapters,
        'punctuation_timeline': punctuation_timeline,
    }
    _BOOK_SUMMARY_CACHE[book] = (cache_key, payload)
    return payload


def safe_join(base: Path, name: str) -> Path:
    # Prevent path traversal
    target = (base / name).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError('Invalid path')
    return target


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Allow frontend dev server / browser access from 5173 and other local origins.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Origin, X-Requested-With')
        self.send_header('Access-Control-Max-Age', '86400')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _text(self, text, status=200, content_type='text/plain; charset=utf-8'):
        data = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path in ('/', '/index.html'):
                # serve the SPA from frontend/index.html
                idx = WEB_ROOT / 'index.html'
                if not idx.exists():
                    fallback = (
                        '<!doctype html><html><head><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>Frontend not found</title></head>'
                        '<body style="font-family:system-ui, sans-serif; padding:16px;">'
                        '<h1>Frontend index not found</h1>'
                        '<p>Expected file at frontend/index.html.</p>'
                        '<p>Please rebuild frontend or ensure the file exists.</p>'
                        '</body></html>'
                    )
                    return self._text(fallback, status=200, content_type='text/html; charset=utf-8')
                with open(idx, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self._text(content, content_type='text/html; charset=utf-8')

            if path.startswith('/dist/') or path.startswith('/static/js/'):
                rel = path.lstrip('/')
                if rel.startswith('static/js/'):
                    rel = rel.replace('static/js/', 'dist/', 1)
                file_path = PROJECT_ROOT / 'frontend' / rel
                if file_path.exists() and file_path.is_file():
                    return self._text(file_path.read_text(encoding='utf-8'), content_type='application/javascript; charset=utf-8')
                return self._json({'error': 'file not found'}, status=404)

            if path == '/api/books':
                books = list_books()
                slog(f'books endpoint: count={len(books)} sample={books[:10]}')
                return self._json({'books': books, 'items': list_book_states()})

            if path == '/api/book_summary':
                book = qs.get('book', [''])[0]
                if not book:
                    return self._json({'error': 'book param required'}, status=400)
                if not (OUTPUTS_DIR / book).exists() and not _load_chapters_summary(OUTPUTS_DIR / book):
                    return self._json({'error': 'book not found'}, status=404)
                return self._json(_load_book_summary(book))

            if path == '/api/files':
                book = qs.get('book', [''])[0]
                if not book:
                    return self._json({'error': 'book param required'}, status=400)
                files = list_files(book)
                slog(f"list_files: book={book} files_count={len(files)} sample={files[:10]}")
                return self._json({'book': book, 'files': files})

            if path == '/api/file_parsed':
                # return parsed CSV/JSONL/JSON for safer client rendering
                book = qs.get('book', [''])[0]
                name = qs.get('name', [''])[0]
                if not book or not name:
                    return self._json({'error': 'book and name params required'}, status=400)
                # support paths like 'tables/filename.csv' or 'processed/filename.jsonl'
                parts = name.split('/') if '/' in name else [name]
                if len(parts) > 1:
                    sub = parts[0]
                    real_name = '/'.join(parts[1:])
                    candidate = OUTPUTS_DIR / sub / real_name
                else:
                    candidate = OUTPUTS_DIR / book / name
                # fallback: if candidate not exists, try alternative locations
                if not candidate.exists():
                    # try outputs/tables/<book>_name
                    alt1 = OUTPUTS_DIR / 'tables' / f"{book}_{name}"
                    alt2 = OUTPUTS_DIR / 'processed' / f"{book}_{name}"
                    alt3 = OUTPUTS_DIR / name
                    chosen = None
                    for c in (alt1, alt2, alt3):
                        if c.exists():
                            chosen = c; break
                    if chosen:
                        candidate = chosen
                if not candidate.exists():
                    # final fallback: attempt safe_join with provided book/name (may raise)
                    try:
                        candidate = safe_join(OUTPUTS_DIR / book, unquote_plus(name))
                    except Exception:
                        return self._json({'error': 'file not found'}, status=404)
                file_path = candidate
                try:
                    slog(f"file_parsed: serving {file_path}")
                    if file_path.suffix.lower() == '.csv':
                        import csv
                        headers = None
                        rows = []
                        with open(file_path, 'r', encoding='utf-8', newline='') as fh:
                            reader = csv.reader(fh)
                            for i, row in enumerate(reader):
                                if i == 0:
                                    headers = row
                                else:
                                    rows.append(row)
                                if len(rows) >= 1000:
                                    break
                        return self._json({'type': 'csv', 'headers': headers or [], 'rows': rows})
                    elif file_path.suffix.lower() in ('.json',):
                        txt = file_path.read_text(encoding='utf-8')
                        try:
                            data = json.loads(txt)
                        except Exception:
                            data = txt
                        return self._json({'type': 'json', 'data': data})
                    elif file_path.suffix.lower() in ('.jsonl', '.ndjson'):
                        data = []
                        with open(file_path, 'r', encoding='utf-8') as fh:
                            for i, line in enumerate(fh):
                                if i >= 1000: break
                                line = line.strip()
                                if not line: continue
                                try:
                                    data.append(json.loads(line))
                                except Exception:
                                    data.append({'_raw': line})
                        return self._json({'type': 'jsonl', 'data': data})
                    else:
                        # fallback: return raw content
                        text = file_path.read_text(encoding='utf-8')
                        return self._json({'type': 'text', 'content': text})
                except Exception as e:
                    slog(f"file_parsed: error {e} while reading {file_path}")
                    return self._json({'error': f'cannot parse file: {e}'}, status=500)

            if path == '/api/find_file':
                # search outputs recursively for candidate files matching logical name
                logical = qs.get('logical', [''])[0]
                book = qs.get('book', [''])[0]
                if not logical:
                    return self._json({'error': 'logical param required'}, status=400)
                matches = []
                low = logical.lower()
                # walk outputs dir
                for root, dirs, files in os.walk(OUTPUTS_DIR):
                    for fn in files:
                        if low in fn.lower() or fn.lower().endswith('_' + low) or fn.lower().endswith(low):
                            rel = os.path.relpath(os.path.join(root, fn), str(OUTPUTS_DIR))
                            matches.append(rel.replace('\\', '/'))
                matches = sorted(list(dict.fromkeys(matches)))
                slog(f"find_file: logical={logical} book={book} matches={matches[:10]}")
                return self._json({'logical': logical, 'book': book, 'matches': matches})

            if path == '/api/file':
                book = qs.get('book', [''])[0]
                name = qs.get('name', [''])[0]
                if not book or not name:
                    return self._json({'error': 'book and name params required'}, status=400)
                # safe join
                file_path = safe_join(OUTPUTS_DIR / book, unquote_plus(name))
                if not file_path.exists():
                    return self._json({'error': 'file not found'}, status=404)
                # read text
                try:
                    text = file_path.read_text(encoding='utf-8')
                except Exception as e:
                    return self._json({'error': f'cannot read file: {e}'}, status=500)
                # Return as JSON with metadata and content
                return self._json({'book': book, 'name': name, 'content': text})

            # Figures endpoints: list and download generated wordclouds
            if path == '/api/figures':
                book = qs.get('book', [''])[0]
                if not book:
                    return self._json({'error': 'book param required'}, status=400)
                figures_dir = OUTPUTS_DIR / 'figures' / 'wordclouds' / book
                if not figures_dir.exists():
                    return self._json({'book': book, 'files': []})
                files = [p.name for p in sorted(figures_dir.iterdir()) if p.is_file()]
                return self._json({'book': book, 'files': files})

            if path == '/api/figure_download':
                book = qs.get('book', [''])[0]
                name = qs.get('name', [''])[0]
                if not book or not name:
                    return self._json({'error': 'book and name params required'}, status=400)
                file_path = safe_join(OUTPUTS_DIR / 'figures' / 'wordclouds' / book, unquote_plus(name))
                if not file_path.exists():
                    return self._json({'error': 'file not found'}, status=404)
                try:
                    data = file_path.read_bytes()
                except Exception as e:
                    return self._json({'error': f'cannot read file: {e}'}, status=500)
                # determine content-type
                ct = 'application/octet-stream'
                if name.lower().endswith('.png'):
                    ct = 'image/png'
                elif name.lower().endswith('.svg'):
                    ct = 'image/svg+xml'
                elif name.lower().endswith('.json'):
                    ct = 'application/json; charset=utf-8'
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', ct)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    return self._json({'error': f'cannot send file: {e}'}, status=500)

            # New: provide a simple HTML cloud built from tokens.csv for quick preview
            if path == '/api/cloud_html':
                book = qs.get('book', [''])[0]
                if not book:
                    return self._json({'error': 'book param required'}, status=400)
                # try to find tokens.csv in outputs/<book>/tokens.csv or outputs/tables/<book>_tokens.csv
                candidates = [OUTPUTS_DIR / book / 'tokens.csv', OUTPUTS_DIR / 'tables' / f"{book}_tokens.csv", OUTPUTS_DIR / book / 'tokens.csv']
                found = None
                for c in candidates:
                    if c.exists():
                        found = c; break
                if not found:
                    return self._json({'error': 'tokens.csv not found for book'}, status=404)
                try:
                    import csv
                    rows = []
                    with open(found, 'r', encoding='utf-8', newline='') as fh:
                        reader = csv.reader(fh)
                        headers = next(reader, [])
                        for r in reader:
                            if not r: continue
                            rows.append(r)
                    # find token/count indices
                    token_idx = None
                    count_idx = None
                    for i,h in enumerate(headers):
                        lh = h.lower()
                        if lh in ('token','word') and token_idx is None: token_idx = i
                        if lh in ('count','frequency') and count_idx is None: count_idx = i
                    if token_idx is None:
                        return self._json({'error': 'tokens.csv does not contain token column'}, status=500)
                    # build simple HTML
                    spans = []
                    values = []
                    for r in rows:
                        tok = r[token_idx] if token_idx < len(r) else ''
                        if not tok: continue
                        c = 1
                        if count_idx is not None and count_idx < len(r):
                            try:
                                c = int(float(r[count_idx]))
                            except Exception:
                                try:
                                    c = int(r[count_idx])
                                except Exception:
                                    c = 1
                        values.append(c)
                        spans.append((tok, c))
                    if not spans:
                        return self._json({'error': 'no tokens found'}, status=500)
                    maxc = max(values); minc = min(values)
                    palette = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']
                    parts = ['<div style="padding:12px; background:#fff;">']
                    for tok,c in spans[:200]:
                        if maxc == minc:
                            size = 20
                        else:
                            size = int(12 + (c - minc) / (maxc - minc) * 56)
                        color = palette[hash(tok) % len(palette)]
                        parts.append(f'<span style="font-size:{size}px; margin:6px; display:inline-block; color:{color};">{html.escape(tok)}</span>')
                    parts.append('</div>')
                    html_out = '\n'.join(parts)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(html_out.encode('utf-8'))))
                    self.end_headers()
                    self.wfile.write(html_out.encode('utf-8'))
                    return
                except Exception as e:
                    slog(f'cloud_html error: {e}')
                    return self._json({'error': str(e)}, status=500)

            if path == '/api/file_download':
                book = qs.get('book', [''])[0]
                name = qs.get('name', [''])[0]
                if not book or not name:
                    return self._json({'error': 'book and name params required'}, status=400)
                file_path = safe_join(OUTPUTS_DIR / book, unquote_plus(name))
                if not file_path.exists():
                    return self._json({'error': 'file not found'}, status=404)
                try:
                    data = file_path.read_bytes()
                except Exception as e:
                    return self._json({'error': f'cannot read file: {e}'}, status=500)
                # serve as attachment
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{name}"')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    return self._json({'error': f'cannot send file: {e}'}, status=500)

            if path == '/api/cloud_generate':
                # Simple wrapper to run plotting script for a given book
                # Accepts POST JSON {"book": "<book_id>"} or query param book=
                book = qs.get('book', [''])[0] if qs.get('book') else ''
                if not book and self.command == 'POST':
                    # try to read JSON body
                    try:
                        length = int(self.headers.get('Content-Length', 0))
                        raw = self.rfile.read(length) if length else b''
                        if raw:
                            j = json.loads(raw.decode('utf-8'))
                            book = j.get('book', '')
                    except Exception:
                        book = ''
                if not book:
                    return self._json({'error': 'book param required'}, status=400)
                # run script synchronously (blocking)
                try:
                    # Prefer internal pipeline or legacy script in src/legacy_scripts
                    legacy_script = PROJECT_ROOT / 'src' / 'legacy_scripts' / 'plot_wordcloud_counts_legacy.py'
                    if (PROJECT_ROOT / 'src' / 'cloud').exists():
                        cmd = [sys.executable, '-c', 'import src.cloud; print("delegated")']
                        proc = subprocess.run(cmd, capture_output=True)
                    elif legacy_script.exists():
                        cmd = [sys.executable, str(legacy_script), '--text-id', book]
                        proc = subprocess.run(cmd, capture_output=True)
                    else:
                        return self._json({'error': 'plot script not found'}, status=500)
                    stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
                    stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ''
                    if proc.returncode != 0:
                        return self._json({'error': 'plot failed', 'stdout': stdout, 'stderr': stderr}, status=500)
                    return self._json({'book': book, 'stdout': stdout, 'stderr': stderr})
                except Exception as e:
                    return self._json({'error': str(e)}, status=500)

            if path == '/api/run_analysis':
                # Trigger analysis for a selected raw file and return list of created files
                raw_name = qs.get('raw', [''])[0]
                if not raw_name:
                    return self._json({'error': 'raw param required'}, status=400)
                try:
                    # If raw is the logical 'чехов-письмо.txt' and physical ALT_CHEKHOV_PATH exists, use it
                    if raw_name == 'чехов-письмо.txt' and ALT_CHEKHOV_PATH.exists():
                        raw_path = ALT_CHEKHOV_PATH
                    else:
                        raw_path = safe_join(RAW_DIR, unquote_plus(raw_name))
                    if not raw_path.exists():
                        return self._json({'error': 'raw file not found'}, status=404)

                    # Run analyze_text.py script on this raw file
                    script = PROJECT_ROOT / 'src' / 'analyze_text.py'
                    cmd = [sys.executable, str(script), 'analyze', '--input', str(raw_path), '--output-dir', str(OUTPUTS_DIR), '--lang', 'ru']
                    # Run subprocess synchronously and capture output
                    proc = subprocess.run(cmd, capture_output=True)
                    # sanitize stdout/stderr to valid utf-8 strings
                    stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout is not None else ''
                    stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr is not None else ''
                    # cap outputs to reasonable size
                    MAX_OUT = 200000
                    if len(stdout) > MAX_OUT:
                        stdout = stdout[-MAX_OUT:]
                    if len(stderr) > MAX_OUT:
                        stderr = stderr[-MAX_OUT:]
                    if proc.returncode != 0:
                        # return sanitized stderr inside JSON
                        return self._json({'error': 'analysis failed', 'stderr': stderr, 'stdout': stdout}, status=500)
                    # After run, list created files for the book
                    # Book id is filename without extension
                    book_id = raw_path.stem
                    files = list_files(book_id)
                    return self._json({'book': book_id, 'files': files, 'stdout': stdout, 'stderr': stderr})
                except Exception as e:
                    return self._json({'error': str(e)}, status=500)

            if path == '/api/raw_files':
                raws = list_raw_files()
                return self._json({'files': raws})

            if path == '/api/token_by_chapter':
                book = qs.get('book', [''])[0]
                token = qs.get('token', [''])[0]
                if not book or not token:
                    return self._json({'error': 'book and token params required'}, status=400)
                slog(f"token_by_chapter: book={book} token={token}")
                # try to load chapters_summary.json
                chapters_path = OUTPUTS_DIR / book / 'chapters_summary.json'
                if not chapters_path.exists():
                    return self._json({'error': 'chapters_summary.json not found for book'}, status=404)
                try:
                    raw_ch = chapters_path.read_text(encoding='utf-8')
                    parsed = json.loads(raw_ch)
                    # support two formats: either a list of chapters or an object {"chapters": [...]}
                    if isinstance(parsed, dict) and 'chapters' in parsed:
                        chapters = parsed.get('chapters') or []
                    else:
                        chapters = parsed
                    try:
                        slog(f"token_by_chapter: parsed_type={type(parsed)} parsed_len={len(parsed) if hasattr(parsed,'__len__') else 'NA'} sample_parsed={str(parsed)[:200]}")
                    except Exception:
                        pass
                except Exception as e:
                    return self._json({'error': f'cannot read chapters file: {e}'}, status=500)
                # try sentences file in processed or book folder
                sent_path = OUTPUTS_DIR / 'processed' / f'{book}_sentences.jsonl'
                if not sent_path.exists():
                    alt = OUTPUTS_DIR / book / 'sentences.jsonl'
                    if alt.exists():
                        sent_path = alt
                if not sent_path.exists():
                    # try to search generically
                    # look for any file that endswith '_sentences.jsonl' or contains book + '_sentences'
                    found = None
                    for root, dirs, files in os.walk(OUTPUTS_DIR):
                        for fn in files:
                            if fn.lower().endswith('_sentences.jsonl') and fn.lower().startswith(book.lower()):
                                found = Path(root) / fn; break
                        if found: break
                    if found:
                        sent_path = found
                if not sent_path.exists():
                    return self._json({'error': 'sentences jsonl not found for book (processed/<book>_sentences.jsonl or <book>/sentences.jsonl required)'}, status=404)
                slog(f"token_by_chapter: using sentences file {sent_path}")
                # prepare chapter bins
                bins = []
                for i, ch in enumerate(chapters):
                    # chapters may be dicts or simple strings; be robust
                    if isinstance(ch, dict):
                        start = ch.get('start_offset', 0)
                        end = ch.get('end_offset', 0)
                        title = ch.get('title', f'chapter_{i}')
                    else:
                        # fallback: unknown structure — use defaults
                        try:
                            title = str(ch)
                        except Exception:
                            title = f'chapter_{i}'
                        start = 0
                        end = 0
                    bins.append({'idx': i, 'start': start, 'end': end, 'title': title, 'count': 0})
                try:
                    slog(f"token_by_chapter: bins={str(bins)[:400]}")
                except Exception:
                    pass
                # iterate sentences and count token occurrences (robust to malformed lines)
                tlower = token.lower()
                try:
                    with open(sent_path, 'r', encoding='utf-8') as fh:
                        for line in fh:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                            except Exception:
                                # skip malformed JSON lines
                                continue
                            # expect each line to be a JSON object; skip if not
                            if not isinstance(obj, dict):
                                continue
                            sent_start = obj.get('start_offset')
                            # normalize sent_start to int when possible
                            try:
                                sent_start = int(sent_start) if sent_start is not None else None
                            except Exception:
                                sent_start = None
                            tokens = obj.get('tokens') or []
                            # decide chapter by sent_start (first bin matching start<=sent_start<end)
                            chap_idx = None
                            if sent_start is not None:
                                for b in bins:
                                    try:
                                        if int(b.get('start', 0)) <= sent_start < int(b.get('end', 0)):
                                            chap_idx = b['idx']
                                            break
                                    except Exception:
                                        continue
                            if chap_idx is None:
                                # if sentence before first chapter or after last, skip
                                continue
                            # count occurrences in this sentence
                            for tok in tokens:
                                txt = ''
                                # token item may be a dict with 'text' or a plain string
                                if isinstance(tok, dict):
                                    txt = tok.get('text') or ''
                                elif isinstance(tok, str):
                                    txt = tok
                                else:
                                    try:
                                        # best-effort: stringify
                                        txt = str(tok)
                                    except Exception:
                                        txt = ''
                                if txt and txt.lower() == tlower:
                                    bins[chap_idx]['count'] += 1
                except Exception as e:
                    slog(f"token_by_chapter: error reading sentences file: {e}")
                    return self._json({'error': f'cannot read sentences file: {e}'}, status=500)
                # prepare response
                out = [{'chapter_idx': b['idx'], 'title': b['title'], 'count': b['count']} for b in bins]
                return self._json({'book': book, 'token': token, 'counts': out})

            if path == '/api/raw':
                name = qs.get('name', [''])[0]
                if not name:
                    return self._json({'error': 'name param required'}, status=400)
                # Prefer RAW_DIR copy if exists; else allow ALT_CHEKHOV_PATH for logical name
                candidate = RAW_DIR / unquote_plus(name)
                if candidate.exists():
                    file_path = candidate
                elif name == 'чехов-письмо.txt' and ALT_CHEKHOV_PATH.exists():
                    file_path = ALT_CHEKHOV_PATH
                else:
                    return self._json({'error': 'raw file not found'}, status=404)
                try:
                    text = file_path.read_text(encoding='utf-8')
                except Exception as e:
                    return self._json({'error': f'cannot read raw file: {e}'}, status=500)
                return self._json({'name': name, 'content': text})

            # static files for web_view
            if path.startswith('/static/'):
                rel = path[len('/static/'):] 
                rel = unquote_plus(rel)
                file_path = safe_join(WEB_ROOT, rel)
                if not file_path.exists():
                    try:
                        file_path = safe_join(WEB_ROOT / 'static', rel)
                    except Exception:
                        pass
                if not file_path.exists():
                    return self._text('Not found', status=404)
                # serve file
                mime = 'text/plain; charset=utf-8'
                if file_path.suffix == '.js':
                    mime = 'application/javascript; charset=utf-8'
                if file_path.suffix == '.css':
                    mime = 'text/css; charset=utf-8'
                with open(file_path, 'r', encoding='utf-8') as f:
                    return self._text(f.read(), content_type=mime)

            # otherwise 404
            return self._text('Not found', status=404)
        except ValueError:
            return self._json({'error': 'invalid path'}, status=400)
        except Exception as e:
            try:
                import traceback
                tb = traceback.format_exc()
                slog(tb)
            except Exception:
                pass
            return self._json({'error': str(e)}, status=500)

    def do_POST(self):
        # Minimal POST support: currently only /api/raw_save is expected from the frontend
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == '/api/raw_save':
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length else b''
                try:
                    data = json.loads(body.decode('utf-8'))
                except Exception:
                    return self._json({'error': 'invalid JSON'}, status=400)
                name = data.get('name')
                text = data.get('text', '')
                if not name:
                    return self._json({'error': 'name param required'}, status=400)
                try:
                    RAW_DIR.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                file_path = RAW_DIR / unquote_plus(name)
                try:
                    file_path.write_text(text, encoding='utf-8')
                except Exception as e:
                    return self._json({'error': f'cannot write raw file: {e}'}, status=500)
                return self._json({'name': name, 'saved': True})
            else:
                return self._text('Not found', status=404)
        except Exception as e:
            return self._json({'error': str(e)}, status=500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    addr = (args.host, args.port)
    server = ThreadingHTTPServer(addr, Handler)
    print(f"Serving on http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        server.server_close()


if __name__ == '__main__':
    main()
