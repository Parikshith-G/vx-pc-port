"""
Role: Natural alphanumeric sorting utility for video library and playlists.
Responsibility: Sorts strings and file items treating multi-digit numeric blocks naturally.
Details: Guarantees that animename_2 appears before animename_1000 and Episode 2 before Episode 10.
"""

import os
import re
from typing import Any, List, Tuple


def natural_sort_key(text: str) -> List[Tuple[int, Any, Any]]:
    """Generates an alphanumeric comparison key for natural sorting.
    
    Splits text into alternating string and numeric chunks. Numeric chunks are
    parsed into integers so that 2 < 10 < 1000, with raw string lengths acting as
    tie-breakers for leading zeros.
    """
    if not text:
        return []

    tokens = re.split(r"(\d+)", text)
    key: List[Tuple[int, Any, Any]] = []

    for token in tokens:
        if not token:
            continue
        if token.isdigit():
            # (0 for numbers, integer value, raw token for leading-zero tie-breaker e.g. "002" < "2")
            key.append((0, int(token), token))
        else:
            # (1 for text, case-insensitive comparison, original case tie-breaker)
            key.append((1, token.lower(), token))

    return key


def sort_filenames(filenames: List[str]) -> List[str]:
    """Returns a newly sorted list of filename strings using natural sorting."""
    return sorted(filenames, key=natural_sort_key)


def sort_filepaths(filepaths: List[str]) -> List[str]:
    """Sorts full filepaths based on the natural sort order of their basenames."""
    return sorted(filepaths, key=lambda path: natural_sort_key(os.path.basename(path)))
