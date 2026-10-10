"""
Role: Folder and media library navigator.
Responsibility: Allows user to browse video folders, view recent history, and pick files or directories.
Details: Scans folders for video extensions (.mp4, .mkv, .avi, etc.) and presents them sorted naturally.
"""

import os
from tkinter import filedialog
from typing import Callable, List, Optional
import customtkinter as ctk  # type: ignore

from core.natural_sort import natural_sort_key

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".flv",
    ".wmv", ".ts", ".3gp", ".ogv", ".vob", ".mpg", ".mpeg"
}


def format_file_size(size_bytes: int) -> str:
    """Formats bytes into KB, MB, or GB."""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class LibraryView(ctk.CTkFrame):
    """Media library browser with folder selection, search, and natural sorting."""

    def __init__(
        self,
        master,
        on_play_video: Callable[[str, List[str]], None],
        get_resume_pos: Callable[[str], int],
        is_seen_checker: Callable[[str], bool],
        recent_folders_getter: Callable[[], List[str]],
        on_folder_selected: Callable[[str], None],
        **kwargs
    ):
        super().__init__(master, fg_color="#121212", corner_radius=0, **kwargs)
        self.on_play_video = on_play_video
        self.get_resume_pos = get_resume_pos
        self.is_seen_checker = is_seen_checker
        self.recent_folders_getter = recent_folders_getter
        self.on_folder_selected = on_folder_selected

        self.current_folder: str = ""
        self.current_videos: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        # Top toolbar
        toolbar = ctk.CTkFrame(self, fg_color="#181818", height=50, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(toolbar, text="VX Player PC", font=("Segoe UI", 16, "bold"), text_color="#FF8C00").pack(side="left", padx=14)

        btn_folder = ctk.CTkButton(toolbar, text="📁 Open Folder", width=105, height=30, fg_color="#282828", hover_color="#383838", command=self._browse_folder)
        btn_folder.pack(side="left", padx=6)

        btn_file = ctk.CTkButton(toolbar, text="🎬 Open File", width=95, height=30, fg_color="#282828", hover_color="#383838", command=self._browse_file)
        btn_file.pack(side="left", padx=6)

        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="Search videos...", width=200, height=30)
        self.search_entry.pack(side="right", padx=14)
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_list())

        # Folder breadcrumb & status
        self.status_bar = ctk.CTkFrame(self, fg_color="#1E1E1E", height=32, corner_radius=0)
        self.status_bar.pack(fill="x")

        self.lbl_path = ctk.CTkLabel(self.status_bar, text="No folder selected", font=("Segoe UI", 11), text_color="#A0A0A0")
        self.lbl_path.pack(side="left", padx=14)

        self.lbl_count = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11), text_color="#FF8C00")
        self.lbl_count.pack(side="right", padx=14)

        # Video items scroll frame
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=12, pady=10)

    def _browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Select Video Folder")
        if chosen and os.path.isdir(chosen):
            self.load_folder(chosen)

    def _browse_file(self) -> None:
        filetypes = [("Video files", "*.mp4 *.mkv *.webm *.avi *.mov *.m4v *.ts *.flv"), ("All files", "*.*")]
        chosen = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if chosen and os.path.isfile(chosen):
            folder = os.path.dirname(chosen)
            self.load_folder(folder, play_target=chosen)

    def load_folder(self, folder_path: str, play_target: Optional[str] = None) -> None:
        """Scans folder for videos, applies natural alphanumeric sort, and displays items."""
        if not os.path.isdir(folder_path):
            return

        self.current_folder = os.path.normpath(folder_path)
        self.on_folder_selected(self.current_folder)

        videos: List[str] = []
        try:
            for entry in os.scandir(self.current_folder):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in VIDEO_EXTENSIONS:
                    videos.append(entry.path)
        except Exception:
            pass

        # Apply natural alphanumeric sort (animename_2 before animename_1000)
        self.current_videos = sorted(videos, key=lambda p: natural_sort_key(os.path.basename(p)))
        self.lbl_path.configure(text=f"📂 {self.current_folder}")
        self._render_list()

        if play_target:
            self.on_play_video(play_target, self.current_videos)

    def _render_list(self) -> None:
        for w in self.scroll_list.winfo_children():
            w.destroy()

        query = self.search_entry.get().strip().lower()
        filtered = [v for v in self.current_videos if query in os.path.basename(v).lower()] if query else self.current_videos

        self.lbl_count.configure(text=f"{len(filtered)} videos")

        if not filtered:
            msg = "No video files found in folder" if not query else "No matching videos found"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#707070").pack(pady=40)
            return

        for vid in filtered:
            self._create_video_row(vid)

    def _create_video_row(self, vid_path: str) -> None:
        filename = os.path.basename(vid_path)
        resume_pos = self.get_resume_pos(vid_path)
        is_seen = self.is_seen_checker(vid_path)

        try:
            size_str = format_file_size(os.path.getsize(vid_path))
        except Exception:
            size_str = ""

        row = ctk.CTkFrame(self.scroll_list, fg_color="#1E1E1E", corner_radius=6, height=52)
        row.pack(fill="x", pady=3)

        icon = ctk.CTkLabel(row, text="🎬", font=("Segoe UI", 16))
        icon.pack(side="left", padx=(10, 8))

        info_box = ctk.CTkFrame(row, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True, pady=6)

        title = ctk.CTkLabel(info_box, text=filename, font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", anchor="w")
        title.pack(fill="x")

        status_text = ""
        if resume_pos > 3000:
            sec = resume_pos // 1000
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            t_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            status_text = f"Resume at {t_str} · {size_str}"
        elif is_seen:
            status_text = f"✓ Completed · {size_str}"
        else:
            status_text = size_str

        sub_label = ctk.CTkLabel(info_box, text=status_text, font=("Segoe UI", 10), text_color="#A0A0A0", anchor="w")
        sub_label.pack(fill="x")

        play_cmd = lambda e=None, p=vid_path: self.on_play_video(p, self.current_videos)
        row.bind("<Button-1>", play_cmd)
        icon.bind("<Button-1>", play_cmd)
        info_box.bind("<Button-1>", play_cmd)
        title.bind("<Button-1>", play_cmd)
        sub_label.bind("<Button-1>", play_cmd)

        btn_play = ctk.CTkButton(
            row, text="▶ Play", width=68, height=30, fg_color="#FF8C00", hover_color="#FF7F00",
            font=("Segoe UI", 11, "bold"),
            command=lambda p=vid_path: self.on_play_video(p, self.current_videos)
        )
        btn_play.pack(side="right", padx=10)
