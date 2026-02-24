"""Shared path-resolution utility for batch story processing.

Used by both the CLI (batch_stories.py) and the TUI (tui.py).
"""
from __future__ import annotations

import glob as _glob
from pathlib import Path


def resolve_md_paths(raw: str, sep: str = ",") -> list[Path]:
    """Expand a string of paths into a deduplicated, sorted list of .md files.

    *raw* may contain any combination of:
    - A directory path            → all ``*.md`` files inside are collected
    - A specific ``.md`` file     → added directly
    - A glob pattern              → expanded (e.g. ``~/stories/*.md``)
    - Multiple entries separated by *sep* (default ``","``).

    All paths are shell-expanded (``~`` and env vars) and resolved to
    absolute paths.  Non-existent paths emit a warning but are not fatal.
    Duplicates are removed while preserving discovery order.
    """
    files: list[Path] = []

    for entry in raw.split(sep):
        token = entry.strip()
        if not token:
            continue

        # Expand ~ and $VAR before anything else
        expanded_token = str(Path(token).expanduser())

        # Try glob expansion (handles wildcards; also matches plain paths)
        matches = sorted(_glob.glob(expanded_token, recursive=True))
        if matches:
            for m in matches:
                p = Path(m).resolve()
                if p.is_dir():
                    files.extend(sorted(p.glob("*.md")))
                elif p.is_file() and p.suffix.lower() == ".md":
                    files.append(p)
        else:
            # No matches — give a useful warning
            p = Path(expanded_token).resolve()
            if p.is_dir():
                # Directory exists but contains no .md files
                files.extend(sorted(p.glob("*.md")))
            elif p.suffix.lower() == ".md":
                print(f"  WARNING: file not found: {p}")
            else:
                print(f"  WARNING: skipping unrecognised path: {token}")

    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique
