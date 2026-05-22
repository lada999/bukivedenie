#!/usr/bin/env python3
"""
Plot token frequency across chapters for a book.
Usage:
  python src/scripts/plot_token_by_chapter.py --csv outputs/<book>/token_freq_by_chapter.csv --book <book> --top 20 --outdir outputs/<book>/plots

Generates PNG files per token (for top N tokens by total count) and a combined heatmap image 'heatmap_topN.png'.
"""
import argparse
from pathlib import Path
import csv
from collections import defaultdict, Counter
import math


def try_import_matplotlib():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        return plt, np
    except Exception:
        return None, None


def load_csv(path: Path):
    # returns dict: chapter_idx -> {token_lower: count}
    per_ch = defaultdict(lambda: defaultdict(int))
    tokens_total = Counter()
    with path.open('r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            token = r.get('token') or ''
            token_lower = r.get('token_lower') or token.lower()
            try:
                ch = int(r.get('chapter_idx', 0))
            except Exception:
                ch = 0
            try:
                cnt = int(r.get('count', 0))
            except Exception:
                cnt = 0
            per_ch[ch][token_lower] += cnt
            tokens_total[token_lower] += cnt
    # normalize to continuous chapter indices
    if per_ch:
        max_ch = max(per_ch.keys())
    else:
        max_ch = -1
    chapters = list(range(0, max_ch + 1))
    return per_ch, tokens_total, chapters


def plot_token_line(per_ch, token, chapters, out_path, plt):
    counts = [per_ch.get(ch, {}).get(token, 0) for ch in chapters]
    fig, ax = plt.subplots(figsize=(8,3))
    ax.plot(chapters, counts, marker='o')
    ax.set_title(f"'{token}' by chapter")
    ax.set_xlabel('chapter')
    ax.set_ylabel('count')
    ax.grid(True, linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_heatmap(per_ch, tokens, chapters, out_path, plt, np):
    # tokens: list of token strings
    data = []
    for t in tokens:
        row = [per_ch.get(ch, {}).get(t, 0) for ch in chapters]
        data.append(row)
    arr = np.array(data)
    # log scale for better visibility
    arr_log = np.log1p(arr)
    fig, ax = plt.subplots(figsize=(max(6, len(chapters)*0.3), max(4, len(tokens)*0.25)))
    im = ax.imshow(arr_log, aspect='auto', cmap='viridis')
    ax.set_yticks(range(len(tokens)))
    ax.set_yticklabels(tokens)
    ax.set_xticks(range(len(chapters)))
    ax.set_xticklabels([str(c) for c in chapters], rotation=90)
    ax.set_xlabel('chapter')
    fig.colorbar(im, ax=ax, label='log(count+1)')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--book', required=False)
    p.add_argument('--top', type=int, default=20)
    p.add_argument('--outdir', required=False)
    args = p.parse_args()

    csvp = Path(args.csv)
    if not csvp.exists():
        raise SystemExit(f'CSV not found: {csvp}')
    per_ch, totals, chapters = load_csv(csvp)
    if not chapters:
        print('No chapters found in CSV')
        return
    plt, np = try_import_matplotlib()
    if plt is None:
        print('matplotlib not available, skipping plots')
        return
    tokens_top = [t for t, _ in totals.most_common(args.top)]
    outdir = Path(args.outdir) if args.outdir else csvp.parent / 'plots'
    outdir.mkdir(parents=True, exist_ok=True)
    # plot individual lines
    for t in tokens_top:
        safe = ''.join(c if c.isalnum() else '_' for c in t)[:80]
        out_path = outdir / f"{safe}.png"
        plot_token_line(per_ch, t, chapters, out_path, plt)
    # heatmap
    heat_path = outdir / f'heatmap_top{len(tokens_top)}.png'
    plot_heatmap(per_ch, tokens_top, chapters, heat_path, plt, np)
    print('Wrote plots to', outdir)

if __name__ == '__main__':
    main()
