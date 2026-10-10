"""
Role: Local media discovery and folder aggregation scanner for PC.
Responsibility: Scans common user locations, drives, and custom folders for video files.
Details: Groups videos by containing directory, extracts counts and metadata, sorted with natural alphanumeric ordering.
"""

import os
from typing import Any, Dict, List, Optional, Set
from core.natural_sort import natural_sort_key

VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".flv",
    ".wmv", ".ts", ".3gp", ".ogv", ".vob", ".mpg", ".mpeg"
}

IGNORED_DIRS: Set[str] = {
    "windows", "program files", "program files (x86)", "appdata",
    "$recycle.bin", "system volume information", "node_modules",
    ".git", "venv", ".venv", "__pycache__", ".gradle", ".android",
    "site-packages", "dist", "build", ".idea", ".vscode"
}


def get_standard_scan_locations() -> List[str]:
    """Returns standard user directories likely to contain videos."""
    user_home = os.path.expanduser("~")
    candidates = [
        os.path.join(user_home, "Videos"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Movies"),
        os.path.join(user_home, "Pictures")
    ]
    # Check drive roots (e.g., D:\, E:\) for common media folders
    for drive_letter in ["D", "E", "F", "G"]:
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            candidates.append(drive_path)

    existing = []
    for c in candidates:
        if os.path.isdir(c) and os.path.normpath(c) not in [os.path.normpath(x) for x in existing]:
            existing.append(os.path.normpath(c))
    return existing


def scan_directory(path: str, max_depth: int = 3) -> Dict[str, List[str]]:
    """Scans a directory recursively up to max_depth and returns a dict of folder -> [videos]."""
    results: Dict[str, List[str]] = {}
    norm_root = os.path.normpath(path)
    if not os.path.isdir(norm_root):
        return results

    def _walk(current: str, depth: int) -> None:
        if depth > max_depth or not os.path.isdir(current):
            return
        try:
            with os.scandir(current) as it:
                videos: List[str] = []
                subdirs: List[str] = []
                for entry in it:
                    try:
                        if entry.is_file():
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in VIDEO_EXTENSIONS:
                                videos.append(entry.path)
                        elif entry.is_dir():
                            name_lower = entry.name.lower()
                            if name_lower not in IGNORED_DIRS and not entry.name.startswith("."):
                                subdirs.append(entry.path)
                    except (PermissionError, OSError):
                        continue

                if videos:
                    # Sort naturally
                    videos.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
                    results[current] = videos

                for sd in subdirs:
                    _walk(sd, depth + 1)
        except (PermissionError, OSError):
            pass

    _walk(norm_root, 1)
    return results


class MediaScanner:
    """Manages aggregated media scanning and folder grouping."""

    def __init__(self, additional_roots: Optional[List[str]] = None):
        self.roots: List[str] = get_standard_scan_locations()
        if additional_roots:
            for r in additional_roots:
                if r and os.path.isdir(r) and r not in self.roots:
                    self.roots.append(os.path.normpath(r))

    def add_root(self, folder_path: str) -> None:
        """Adds a custom folder path to the scanner roots."""
        norm = os.path.normpath(folder_path)
        if os.path.isdir(norm) and norm not in self.roots:
            self.roots.append(norm)

    def scan_all(self) -> Dict[str, List[str]]:
        """Scans all roots and returns folder_path -> sorted video file list."""
        all_folders: Dict[str, List[str]] = {}
        for r in self.roots:
            # Depth 2 for drive roots to prevent long scans, depth 3 for user folders
            depth = 2 if len(r) <= 3 else 3
            found = scan_directory(r, max_depth=depth)
            for folder, vids in found.items():
                if folder in all_folders:
                    combined = list(set(all_folders[folder] + vids))
                    combined.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
                    all_folders[folder] = combined
                else:
                    all_folders[folder] = vids
        return all_folders

    @staticmethod
    def get_all_videos_list(folders_dict: Dict[str, List[str]]) -> List[str]:
        """Flattens all videos from all folders into a naturally sorted list."""
        all_vids: List[str] = []
        for vids in folders_dict.values():
            all_vids.extend(vids)
        # Unique and naturally sorted
        unique_vids = list(dict.fromkeys(all_vids))
        unique_vids.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
        return unique_vids
