"""Loads data-driven content (JSON) from the project ``data/`` directory.

All tuning lives in data, not code (DESIGN.md R5). Files are cached after first read.
"""
import json
import os

# project_root/data  (this file is src/core/data_loader.py -> up two levels)
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_cache = {}


def load_json(filename):
    """Load and cache a JSON file from the data directory by filename."""
    if filename not in _cache:
        path = os.path.normpath(os.path.join(_DATA_DIR, filename))
        with open(path, "r", encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]
