#!/usr/bin/env python3
"""Shim: call src/legacy_scripts/plot_wordcloud_counts_legacy.py with same args."""
import sys
from pathlib import Path
import subprocess

src = Path(__file__).resolve().parent.parent / 'src' / 'legacy_scripts' / 'plot_wordcloud_counts_legacy.py'
if not src.exists():
    print(f"Legacy script not found: {src}")
    sys.exit(2)
cmd = [sys.executable, str(src)] + sys.argv[1:]
# ensure matplotlib/numpy available
try:
    import matplotlib
    import numpy
except Exception:
    print('Missing plotting dependencies')
    sys.exit(3)
proc = subprocess.run(cmd)
sys.exit(proc.returncode)
