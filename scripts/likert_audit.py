#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".toml"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "data"}

PATTERNS = [
    r"Likert",
    r"1–5",
    r"1-5",
    r"scale_min",
    r"scale_max",
    r"min_value\s*=\s*1",
    r"max_value\s*=\s*5",
    r"between 1 and 5",
    r"\[1,\s*5\]",
    r"/\s*4\.0",
]
COMPILED = [re.compile(p) for p in PATTERNS]


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in INCLUDE_SUFFIXES:
            continue
        yield path


def main() -> int:
    hits = 0
    for file_path in iter_files(ROOT):
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line_no, line in enumerate(lines, start=1):
            matched = [pattern.pattern for pattern in COMPILED if pattern.search(line)]
            if matched:
                rel = file_path.relative_to(ROOT)
                print(f"{rel}:{line_no}: {line.strip()}  ## matches={matched}")
                hits += 1

    print(f"\nTotal matching lines: {hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
