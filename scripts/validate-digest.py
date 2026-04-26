#!/usr/bin/env python3
from pathlib import Path
import sys

# Allow this hyphenated wrapper to run directly from scripts/ while importing
# repository-root modules such as schema.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_digest import main

if __name__ == "__main__":
    raise SystemExit(main())
