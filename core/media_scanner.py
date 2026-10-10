"""
Role: Incremental and lightweight media scanner for PC.
Responsibility: Scans folders progressively without high CPU or disk freezing.
Details: Discovers folders one-by-one, reports real-time scanning path to UI, and yields results immediately.
"""

import os
import threading
import time
from typing import Callable, Dict, List, Optional, Set
from core.natural_sort import natural_sort_key

VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".flv",
    ".wmv", ".3gp", ".ogv", ".vob", ".mpg", ".mpeg", ".m2ts", ".mts"
}

IGNORED_DIR_NAMES: Set[str] = {
    "windows", "program files", "program files (x86)", "appdata",
    "$recycle.bin", "system volume information", "node_modules",
    ".git", "venv", ".venv", "__pycache__", ".gradle", ".android",
    "site-packages", "dist", "build", ".idea", ".vscode", "temp", "tmp",
    "recovery", "recoverybin", "cache", "sources", "src", "bin", "obj",
    "target", "vendor"
}


def get_default_scan_directories() -> List[str]:
    """Returns prioritized candidate directories for media scanning."""
    user_home = os.path.expanduser("~")
    # 1. Primary personal media directories (scanned first)
    dirs = [
        os.path.join(user_home, "Videos"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Movies"),
    ]

    valid = []
    for d in dirs:
        if os.path.isdir(d):
            norm = os.path.normpath(d)
            if norm not in valid:
                valid.append(norm)

    # 2. Top-level folders of other drives (D:\, E:\, etc.)
    for drive in ["D", "E", "F", "G"]:
        drive_root = f"{drive}:\\"
        if os.path.exists(drive_root) and os.path.isdir(drive_root):
            try:
                with os.scandir(drive_root) as it:
                    for entry in it:
                        try:
                            if entry.is_dir():
                                name_lower = entry.name.lower()
                                if name_lower not in IGNORED_DIR_NAMES and not entry.name.startswith("."):
                                    norm_p = os.path.normpath(entry.path)
                                    if norm_p not in valid:
                                        valid.append(norm_p)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                pass

    return valid


class ProgressiveMediaScanner:
    """Incrementally scans directories folder-by-folder with UI feedback and low CPU impact."""

    def __init__(self, additional_roots: Optional[List[str]] = None):
        self.roots: List[str] = get_default_scan_directories()
        if additional_roots:
            for r in additional_roots:
                if r and os.path.isdir(r):
                    norm = os.path.normpath(r)
                    if norm not in self.roots:
                        self.roots.insert(0, norm)  # User's custom/recent folders first

        self.stop_event = threading.Event()
        self.is_scanning = False

    def add_custom_folder(self, folder_path: str) -> None:
        """Adds a folder to the top of scan queue."""
        norm = os.path.normpath(folder_path)
        if os.path.isdir(norm) and norm not in self.roots:
            self.roots.insert(0, norm)

    def stop(self) -> None:
        """Signals the scanner to halt immediately."""
        self.stop_event.set()

    def scan(
        self,
        on_status: Callable[[str], None],
        on_folder_found: Callable[[str, List[str]], None],
        on_finished: Callable[[int, int], None]
    ) -> None:
        """Scans folder-by-folder, yielding progress and throttling to maintain low CPU & disk usage."""
        self.stop_event.clear()
        self.is_scanning = True
        total_folders_found = 0
        total_videos_found = 0

        try:
            for root_dir in self.roots:
                if self.stop_event.is_set():
                    break
                if not os.path.isdir(root_dir):
                    continue

                # Scan root_dir and its subfolders up to depth 2
                for current_path, subdirs, files in os.walk(root_dir):
                    if self.stop_event.is_set():
                        break

                    # Prune ignored directory trees in-place
                    subdirs[:] = [
                        d for d in subdirs
                        if not d.startswith(".") and d.lower() not in IGNORED_DIR_NAMES
                    ]

                    # Notify status bar of currently scanned directory
                    on_status(current_path)

                    # Check for video files in current directory
                    videos = []
                    for f in files:
                        try:
                            ext = os.path.splitext(f)[1].lower()
                            if ext in VIDEO_EXTENSIONS:
                                videos.append(os.path.join(current_path, f))
                        except Exception:
                            continue

                    if videos:
                        videos.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
                        total_folders_found += 1
                        total_videos_found += len(videos)
                        on_folder_found(os.path.normpath(current_path), videos)

                    # Gentle throttle (10ms) so disk I/O and CPU stay calm and cool
                    time.sleep(0.01)

        finally:
            self.is_scanning = False
            on_finished(total_folders_found, total_videos_found)


# Alias for backward compatibility
MediaScanner = ProgressiveMediaScanner
