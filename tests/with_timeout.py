"""Fallback timeout runner: with_timeout.py SECONDS CMD ARGS... Exits 124 on timeout, else the command's code."""
import subprocess
import sys

try:
    code = subprocess.run(sys.argv[2:], timeout=float(sys.argv[1])).returncode
except subprocess.TimeoutExpired:
    print(f"TIMEOUT after {sys.argv[1]} s: {' '.join(sys.argv[2:])}", file=sys.stderr)
    code = 124
sys.exit(code)
