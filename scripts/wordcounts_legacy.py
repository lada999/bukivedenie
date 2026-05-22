#!/usr/bin/env python3
"""Shim: call src/legacy_scripts/wordcounts_legacy.py with same args."""
import sys
from pathlib import Path
import subprocess

src = Path(__file__).resolve().parent.parent / 'src' / 'legacy_scripts' / 'wordcounts_legacy.py'
if not src.exists():
    print(f"Legacy script not found: {src}")
    sys.exit(2)
cmd = [sys.executable, str(src)] + sys.argv[1:]
proc = subprocess.run(cmd)
sys.exit(proc.returncode)
