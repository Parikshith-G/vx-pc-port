"""
Role: In-player playlist sidebar and episode selector.
Responsibility: Displays list of videos in active folder/playlist with currently playing indicator.
Details: Supports double-click/click to play, search filtering, and natural alphanumeric sorting.
"""

import os
from typing import Callable, List, Optional
import customtkinter as ctk  # type: ignore

from core.natural_sort import sort_filepaths


class PlaylistPanel(ctk.CTkFrame):
    """Collapsible playlist sidebar showing videos in current playlist."""

    def __init__(
        self,
        master,
        on_video_selected: Callable[[str], None],
        is_seen_checker: Callable[[str], bool],
        on_close: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="#1F1F1F", width=280, corner_radius=0, **kwargs)
        self.on_video_selected = on_video_selected
        self.is_seen_checker = is_seen_checker
        self.on_close = on_close

        self.all_videos: List[str] = []
        self.current_video: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        # Header row
        header = ctk.CTkFrame(self, fg_color="#181818", height=40, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        self.lbl_title = ctk.CTkLabel(
            header, text="Playlist", font=("Segoe UI", 13, "bold"), text_color="#FFFFFF"
        )
        self.lbl_title.pack(side="left", padx=10, pady=6)

        btn_close = ctk.CTkButton(
            header, text="✕", width=28, height=26, fg_color="transparent",
            hover_color="#333333", font=("Segoe UI", 12), command=self.on_close
        )
        btn_close.pack(side="right", padx=6, pady=6)

        # Search filter entry
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="Filter episodes...", height=28, font=("Segoe UI", 11)
        )
        self.search_entry.pack(fill="x", padx=8, pady=(8, 4))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_items())

        # Scrollable items frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def set_playlist(self, videos: List[str], current: Optional[str] = None) -> None:
        """Sets video list and sorts using natural alphanumeric ordering."""
        self.all_videos = sort_filepaths(videos)
        self.current_video = current
        self.lbl_title.configure(text=f"Playlist ({len(self.all_videos)})")
        self._render_items()

    def set_current(self, current: str) -> None:
        self.current_video = current
        self._render_items()

    def _render_items(self) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip().lower()
        filtered = [v for v in self.all_videos if query in os.path.basename(v).lower()] if query else self.all_videos

        for vid in filtered:
            is_active = (vid == self.current_video)
            is_seen = self.is_seen_checker(vid)
            filename = os.path.basename(vid)

            bg = "#FF8C00" if is_active else "#282828"
            hover = "#FFA500" if is_active else "#3A3A3A"
            txt_color = "#FFFFFF" if is_active else ("#A0A0A0" if is_seen else "#E0E0E0")
            prefix = "▶ " if is_active else ("✓ " if is_seen else "  ")

            btn = ctk.CTkButton(
                self.scroll_frame,
                text=f"{prefix}{filename}",
                anchor="w",
                font=("Segoe UI", 11, "bold" if is_active else "normal"),
                fg_color=bg,
                hover_color=hover,
                text_color=txt_color,
                height=32,
                corner_radius=4,
                command=lambda path=vid: self.on_video_selected(path)
            )
            btn.pack(fill="x", pady=2, padx=2)
