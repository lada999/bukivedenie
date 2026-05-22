#!/usr/bin/env python3
"""
Простой скрипт: по нормализованному тексту и сводке глав (chapters_summary.json)
собирает частоты токенов по главам и сохраняет CSV вида:

  token,token_lower,chapter_idx,count

Назначение: максимально простой "fallback" для widget'а token_by_chapter.

Использование:
  python src/scripts/token_freq_by_chapter.py \
      --text outputs/processed/<book>_normalized.txt \
      --chapters outputs/<book>/chapters_summary.json \
      --output outputs/<book>/token_freq_by_chapter.csv

Если chapters_summary.json содержит объект {"chapters": [...]}, то берём вложенный список.
Если chapters — список простых строк, попытаемся определить диапазоны по длине текста (равномерно),
но в нормальном случае chapters_summary.json — список dict с start_offset/end_offset.
"""

import argparse
import json
import csv
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

WORD_RE = re.compile(r"\w+", re.UNICODE)


def load_chapters(path: Path) -> List[Dict[str, Any]]:
    txt = path.read_text(encoding='utf-8')
    parsed = json.loads(txt)
    if isinstance(parsed, dict) and 'chapters' in parsed:
        parsed = parsed.get('chapters') or []
    if not isinstance(parsed, list):
        raise RuntimeError('chapters file does not contain list')
    # Normalize entries to dicts with start_offset,end_offset,title,chapter_idx
    out = []
    for i, ch in enumerate(parsed):
        if isinstance(ch, dict):
            start = ch.get('start_offset') or ch.get('start') or ch.get('start_pos') or 0
            end = ch.get('end_offset') or ch.get('end') or ch.get('end_pos') or 0
            title = ch.get('title') or ch.get('name') or f'chapter_{i}'
        else:
            # fallback: simple string title — we cannot infer offsets here
            start = None
            end = None
            title = str(ch)
        out.append({'chapter_idx': i, 'title': title, 'start': start, 'end': end})
    return out


def compute_counts(text: str, chapters: List[Dict[str, Any]]) -> List[Tuple[str,str,int,int]]:
    """Возвращает список кортежей (token, token_lower, chapter_idx, count)"""
    total_len = len(text)
    # If chapters have None offsets, try to split evenly
    need_infer = any(ch['start'] is None or ch['end'] is None or ch['end'] == 0 for ch in chapters)
    if need_infer:
        n = len(chapters)
        if n == 0:
            return []
        chunk = total_len // n
        for i, ch in enumerate(chapters):
            ch['start'] = i * chunk
            ch['end'] = (i + 1) * chunk if i < n - 1 else total_len

    results = []
    for ch in chapters:
        s = int(ch.get('start') or 0)
        e = int(ch.get('end') or 0)
        if s < 0: s = 0
        if e > total_len: e = total_len
        if s >= e:
            # empty chapter — skip
            results.append(({}, ch['chapter_idx']))
            continue
        chunk_text = text[s:e]
        counter: Dict[str, int] = {}
        for m in WORD_RE.finditer(chunk_text):
            tok = m.group(0)
            tl = tok.lower()
            counter[tl] = counter.get(tl, 0) + 1
        results.append((counter, ch['chapter_idx']))

    # Flatten to list of rows
    rows: List[Tuple[str,str,int,int]] = []
    for counter, idx in results:
        if not counter:
            continue
        for tok_lower, cnt in counter.items():
            rows.append((tok_lower, tok_lower, idx, cnt))
    return rows


def write_csv(rows: List[Tuple[str,str,int,int]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['token','token_lower','chapter_idx','count'])
        for token, token_lower, idx, cnt in rows:
            writer.writerow([token, token_lower, idx, cnt])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--text', required=True, help='Path to normalized text (canonical)')
    p.add_argument('--chapters', required=True, help='Path to chapters_summary.json')
    p.add_argument('--output', required=True, help='Output CSV path')
    args = p.parse_args()

    text_path = Path(args.text)
    chapters_path = Path(args.chapters)
    out_path = Path(args.output)

    if not text_path.exists():
        raise SystemExit(f'Text file not found: {text_path}')
    if not chapters_path.exists():
        raise SystemExit(f'Chapters file not found: {chapters_path}')

    text = text_path.read_text(encoding='utf-8')
    chapters = load_chapters(chapters_path)

    rows = compute_counts(text, chapters)
    write_csv(rows, out_path)
    print(f'Wrote {len(rows)} rows to {out_path}')


if __name__ == '__main__':
    main()
