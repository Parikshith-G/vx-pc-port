"""
Role: Playback resume and watch history persistence coordinator.
Responsibility: Stores and retrieves video playback positions, seen states, and folder history in local JSON.
Details: Automatically saves timestamps, auto-detects finished videos (>95%), and supports backup/restore.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional


class HistoryManager:
    """Manages persistence of video playback positions and seen states."""

    def __init__(self, storage_dir: Optional[str] = None):
        if not storage_dir:
            user_home = os.path.expanduser("~")
            storage_dir = os.path.join(user_home, ".vx_player_desktop")
            legacy_dir = os.path.join(user_home, ".mx_player_desktop")
            if not os.path.exists(storage_dir) and os.path.exists(legacy_dir):
                try:
                    import shutil
                    shutil.copytree(legacy_dir, storage_dir)
                except Exception:
                    pass
        
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.history_file = os.path.join(self.storage_dir, "playback_history.json")
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Loads data from JSON file or returns default state."""
        default_data = {
            "resume_positions": {},  # filepath -> {"position_ms": int, "duration_ms": int, "updated_at": int}
            "seen_videos": {},       # filepath -> {"seen_at": int, "filename": str}
            "recent_folders": [],    # list of folder paths
            "last_folder": "",
            "volume": 100,
            "boost_enabled": False
        }
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    default_data.update(loaded)
            except Exception:
                pass
        return default_data

    def save(self) -> None:
        """Saves current state to JSON file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def save_position(self, filepath: str, position_ms: int, duration_ms: int) -> None:
        """Saves current playback position and marks completed if near end."""
        if not filepath:
            return
        
        norm_path = os.path.normpath(filepath)
        now = int(time.time())

        # If watched >= 95% or within 10s of the end of a video > 30s, mark as seen
        if duration_ms > 30000 and (position_ms >= duration_ms * 0.95 or duration_ms - position_ms <= 10000):
            self.mark_as_seen(norm_path)
            # Clear resume position once finished
            self.data["resume_positions"].pop(norm_path, None)
        elif position_ms > 3000:  # Only save if watched past 3 seconds
            self.data["resume_positions"][norm_path] = {
                "position_ms": position_ms,
                "duration_ms": duration_ms,
                "updated_at": now
            }
        else:
            self.data["resume_positions"].pop(norm_path, None)

        self.save()

    def get_resume_position(self, filepath: str) -> int:
        """Returns saved playback position in milliseconds or 0."""
        norm_path = os.path.normpath(filepath)
        entry = self.data["resume_positions"].get(norm_path)
        if entry and isinstance(entry, dict):
            return int(entry.get("position_ms", 0))
        return 0

    def clear_position(self, filepath: str) -> None:
        """Removes resume position for given file."""
        norm_path = os.path.normpath(filepath)
        if norm_path in self.data["resume_positions"]:
            del self.data["resume_positions"][norm_path]
            self.save()

    def mark_as_seen(self, filepath: str) -> None:
        """Marks video as seen in history."""
        norm_path = os.path.normpath(filepath)
        self.data["seen_videos"][norm_path] = {
            "seen_at": int(time.time()),
            "filename": os.path.basename(filepath)
        }
        self.save()

    def is_seen(self, filepath: str) -> bool:
        """Checks if video was completed or marked as seen."""
        norm_path = os.path.normpath(filepath)
        return norm_path in self.data["seen_videos"]

    def add_recent_folder(self, folder_path: str) -> None:
        """Adds folder path to recent history list."""
        if not folder_path or not os.path.isdir(folder_path):
            return
        norm_dir = os.path.normpath(folder_path)
        recents: List[str] = self.data.get("recent_folders", [])
        if norm_dir in recents:
            recents.remove(norm_dir)
        recents.insert(0, norm_dir)
        self.data["recent_folders"] = recents[:20]  # Keep up to 20 folders
        self.data["last_folder"] = norm_dir
        self.save()

    def get_last_folder(self) -> str:
        """Gets most recently opened directory path."""
        last = self.data.get("last_folder", "")
        if last and os.path.isdir(last):
            return last
        return ""

    def export_backup(self, dest_path: str) -> bool:
        """Exports history and resume data to a backup JSON file."""
        try:
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def import_backup(self, source_path: str) -> bool:
        """Imports and merges history from a backup file."""
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if isinstance(imported, dict):
                self.data.update(imported)
                self.save()
                return True
        except Exception:
            pass
        return False
