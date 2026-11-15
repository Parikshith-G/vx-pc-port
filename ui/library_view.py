"""
Role: Progressive media library, folder discovery navigator, and watch history manager.
Responsibility: Incrementally discovers and displays video folders and files without freezing or high CPU usage.
Details: Provides Folders, All Videos, Recent, and Seen tabs with deletion, right-click context menu, and mobile v2.23 styling.
"""

import os
import subprocess
import sys
import threading
import time
from tkinter import filedialog, messagebox, Menu
from typing import Callable, Dict, List, Optional
import customtkinter as ctk  # type: ignore

from core.media_scanner import ProgressiveMediaScanner
from core.natural_sort import natural_sort_key

BATCH_PAGE_SIZE = 40  # Render videos in batches to keep UI responsive and prevent high CPU usage


def format_file_size(size_bytes: int) -> str:
    """Formats bytes into KB, MB, or GB."""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class LibraryView(ctk.CTkFrame):
    """Media library browser with 4 tabs (Folders, All Videos, Recent, Seen) and mobile v2.23 design."""

    def __init__(
        self,
        master,
        on_play_video: Callable[[str, List[str]], None],
        get_resume_pos: Callable[[str], int],
        is_seen_checker: Callable[[str], bool],
        recent_folders_getter: Callable[[], List[str]],
        on_folder_selected: Callable[[str], None],
        on_generate_ai_subtitles: Optional[Callable[[List[str]], None]] = None,
        history_manager=None,
        **kwargs
    ):
        super().__init__(master, fg_color="#0B0E14", corner_radius=0, **kwargs)
        self.on_play_video = on_play_video
        self.get_resume_pos = get_resume_pos
        self.is_seen_checker = is_seen_checker
        self.recent_folders_getter = recent_folders_getter
        self.on_folder_selected = on_folder_selected
        self.on_generate_ai_subtitles = on_generate_ai_subtitles or (lambda v: None)
        self.history = history_manager

        # State
        self.active_tab: str = "Folders"  # "Folders" | "All Videos" | "Recent" | "Seen"
        self.current_folder: Optional[str] = None  # None = root folder list; str = inside folder
        self.folders_dict: Dict[str, List[str]] = {}  # folder_path -> [video_paths]
        self.visible_video_limit: int = BATCH_PAGE_SIZE

        self.scanner = ProgressiveMediaScanner(additional_roots=self.recent_folders_getter())
        self.scan_thread: Optional[threading.Thread] = None

        self._build_ui()
        self.start_rescan()

    def _build_ui(self) -> None:
        # 1. Top main toolbar (dark cyan palette #10131A)
        toolbar = ctk.CTkFrame(self, fg_color="#10131A", height=60, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=0)

        # Brand Title Block with VX rounded badge & version pill
        brand_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        brand_frame.pack(side="left", padx=(16, 12), pady=10)

        badge = ctk.CTkLabel(
            brand_frame, text="VX", font=("Segoe UI", 11, "bold"),
            fg_color="#0099FF", text_color="#FFFFFF", corner_radius=6,
            width=30, height=22
        )
        badge.pack(side="left", padx=(0, 6))

        title_lbl = ctk.CTkLabel(
            brand_frame, text="VX Player", font=("Segoe UI", 16, "bold"), text_color="#FFFFFF"
        )
        title_lbl.pack(side="left", padx=(0, 6))

        version_pill = ctk.CTkLabel(
            brand_frame, text="v2.23", font=("Segoe UI", 10, "bold"),
            fg_color="#18283E", text_color="#38BDF8", corner_radius=10,
            padx=8, height=20
        )
        version_pill.pack(side="left", padx=(0, 8))

        sub_tag = ctk.CTkLabel(
            brand_frame, text="OFFLINE MEDIA", font=("Segoe UI", 8, "bold"),
            text_color="#64748B"
        )
        sub_tag.pack(side="left")

        # 4-Tab Segmented Switcher (Mobile parity: Folders, All Videos, Recent, Seen)
        self.tab_segmented = ctk.CTkSegmentedButton(
            toolbar,
            values=["Folders", "All Videos", "Recent", "Seen"],
            command=self._on_tab_changed,
            selected_color="#0099FF",
            selected_hover_color="#0088EE",
            unselected_color="#161B26",
            unselected_hover_color="#1E293B",
            font=("Segoe UI", 11, "bold"),
            height=32
        )
        self.tab_segmented.set("Folders")
        self.tab_segmented.pack(side="left", padx=10)

        # Scan & Action Buttons
        self.btn_scan_toggle = ctk.CTkButton(
            toolbar, text="Rescan", width=75, height=30,
            fg_color="#161B26", hover_color="#1E293B", text_color="#E0E6ED",
            font=("Segoe UI", 11),
            command=self._toggle_scan
        )
        self.btn_scan_toggle.pack(side="left", padx=4)

        btn_folder = ctk.CTkButton(
            toolbar, text="+ Folder", width=75, height=30,
            fg_color="#161B26", hover_color="#1E293B", text_color="#E0E6ED",
            font=("Segoe UI", 11),
            command=self._browse_folder
        )
        btn_folder.pack(side="left", padx=4)

        btn_file = ctk.CTkButton(
            toolbar, text="Open File", width=75, height=30,
            fg_color="#161B26", hover_color="#1E293B", text_color="#E0E6ED",
            font=("Segoe UI", 11),
            command=self._browse_file
        )
        btn_file.pack(side="left", padx=4)

        # Search Bar
        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="Search videos or folders...", width=180, height=30,
            fg_color="#161B26", border_color="#242B3B"
        )
        self.search_entry.pack(side="right", padx=(4, 16))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_updated())

        # Sort Dropdown
        self.sort_option = ctk.CTkOptionMenu(
            toolbar,
            values=[
                "Name (A-Z)",
                "Name (Z-A)",
                "Date (Newest)",
                "Date (Oldest)",
                "Size (Largest)",
                "Size (Smallest)"
            ],
            width=125,
            height=30,
            fg_color="#161B26",
            button_color="#1E293B",
            button_hover_color="#27354A",
            dropdown_fg_color="#161B26",
            dropdown_hover_color="#1E293B",
            font=("Segoe UI", 11),
            dropdown_font=("Segoe UI", 11),
            command=self._on_sort_changed
        )
        self.sort_option.set("Name (A-Z)")
        self.sort_option.pack(side="right", padx=(4, 4))

        lbl_sort = ctk.CTkLabel(
            toolbar, text="Sort:", font=("Segoe UI", 11), text_color="#64748B"
        )
        lbl_sort.pack(side="right", padx=(6, 2))

        # 2. Real-time Live Scan Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color="#141822", height=38, corner_radius=0)
        self.status_bar.pack(fill="x")

        self.btn_back_folder = ctk.CTkButton(
            self.status_bar, text="‹ Back to Folders", width=120, height=26,
            fg_color="#182030", hover_color="#222C42", text_color="#38BDF8",
            font=("Segoe UI", 11, "bold"),
            command=self._exit_folder_detail
        )

        self.lbl_path = ctk.CTkLabel(
            self.status_bar, text="Ready",
            font=("Segoe UI", 11), text_color="#8B98A5"
        )
        self.lbl_path.pack(side="left", padx=14)

        self.lbl_count = ctk.CTkLabel(
            self.status_bar, text="", font=("Segoe UI", 11, "bold"), text_color="#38BDF8"
        )
        self.lbl_count.pack(side="right", padx=14)

        # 3. Content scroll area
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=14, pady=10)

    # --------------------------------------------------------------------------
    # Incremental Scanning & Live UI Feedback
    # --------------------------------------------------------------------------

    def _toggle_scan(self) -> None:
        if self.scanner.is_scanning:
            self.scanner.stop()
            self.btn_scan_toggle.configure(text="Rescan", fg_color="#161B26")
            self.lbl_path.configure(text="Scan stopped by user")
            self._render_current_view()
        else:
            self.start_rescan()

    def start_rescan(self) -> None:
        """Starts an incremental background scan showing real-time scanning paths."""
        if self.scanner.is_scanning:
            return

        self.btn_scan_toggle.configure(text="Stop Scan", fg_color="#7F1D1D", hover_color="#991B1B")
        self.lbl_path.configure(text="Scanning device library...")
        self._last_status_update = 0.0

        def _on_status_thread(current_path: str):
            now = time.time()
            if now - self._last_status_update >= 0.1:
                self._last_status_update = now
                short_p = current_path if len(current_path) < 65 else "..." + current_path[-62:]
                self.after(0, self._update_scan_status, short_p)

        def _on_folder_found_thread(folder_path: str, videos: List[str]):
            self.after(0, self._add_discovered_folder, folder_path, videos)

        def _on_finished_thread(total_f: int, total_v: int):
            self.after(0, self._on_scan_finished, total_f, total_v)

        def _worker():
            self.scanner.scan(
                on_status=_on_status_thread,
                on_folder_found=_on_folder_found_thread,
                on_finished=_on_finished_thread
            )

        self.scan_thread = threading.Thread(target=_worker, daemon=True)
        self.scan_thread.start()

    def _update_scan_status(self, short_path: str) -> None:
        if self.scanner.is_scanning:
            total_f = len(self.folders_dict)
            total_v = sum(len(v) for v in self.folders_dict.values())
            self.lbl_path.configure(text=f"Scanning: {short_path}")
            self.lbl_count.configure(text=f"{total_f} folders · {total_v} videos")

    def _add_discovered_folder(self, folder_path: str, videos: List[str]) -> None:
        self.folders_dict[folder_path] = videos

    def _on_scan_finished(self, total_folders: int, total_videos: int) -> None:
        self.btn_scan_toggle.configure(text="Rescan", fg_color="#161B26", hover_color="#1E293B")
        total_f = len(self.folders_dict)
        total_v = sum(len(v) for v in self.folders_dict.values())
        self.lbl_path.configure(text=f"Library scan complete · {total_f} folders discovered")
        self.lbl_count.configure(text=f"{total_f} folders · {total_v} videos")
        self._render_current_view()

    # --------------------------------------------------------------------------
    # Navigation & Interaction
    # --------------------------------------------------------------------------

    def _on_tab_changed(self, value: str) -> None:
        self.visible_video_limit = BATCH_PAGE_SIZE
        self.active_tab = value
        self.current_folder = None
        self._render_current_view()

    def _on_search_updated(self) -> None:
        self.visible_video_limit = BATCH_PAGE_SIZE
        self._render_current_view()

    def _on_sort_changed(self, _choice: str = "") -> None:
        self.visible_video_limit = BATCH_PAGE_SIZE
        self._render_current_view()

    def _safe_mtime(self, path: str) -> float:
        try:
            return os.path.getmtime(path)
        except Exception:
            return 0.0

    def _safe_size(self, path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    def _safe_folder_size(self, folder_path: str) -> int:
        vids = self.folders_dict.get(folder_path, [])
        total = 0
        for v in vids:
            try:
                total += os.path.getsize(v)
            except Exception:
                pass
        return total

    def _sort_folders(self, folder_items: List[tuple]) -> List[tuple]:
        mode = self.sort_option.get()
        if mode == "Name (A-Z)":
            return sorted(folder_items, key=lambda it: natural_sort_key(it[0]))
        elif mode == "Name (Z-A)":
            return sorted(folder_items, key=lambda it: natural_sort_key(it[0]), reverse=True)
        elif mode == "Date (Newest)":
            return sorted(folder_items, key=lambda it: self._safe_mtime(it[1]), reverse=True)
        elif mode == "Date (Oldest)":
            return sorted(folder_items, key=lambda it: self._safe_mtime(it[1]))
        elif mode == "Size (Largest)":
            return sorted(folder_items, key=lambda it: (it[2], self._safe_folder_size(it[1])), reverse=True)
        elif mode == "Size (Smallest)":
            return sorted(folder_items, key=lambda it: (it[2], self._safe_folder_size(it[1])))
        return sorted(folder_items, key=lambda it: natural_sort_key(it[0]))

    def _sort_videos(self, videos: List[str]) -> List[str]:
        mode = self.sort_option.get()
        if mode == "Name (A-Z)":
            return sorted(videos, key=lambda p: natural_sort_key(os.path.basename(p)))
        elif mode == "Name (Z-A)":
            return sorted(videos, key=lambda p: natural_sort_key(os.path.basename(p)), reverse=True)
        elif mode == "Date (Newest)":
            return sorted(videos, key=lambda p: self._safe_mtime(p), reverse=True)
        elif mode == "Date (Oldest)":
            return sorted(videos, key=lambda p: self._safe_mtime(p))
        elif mode == "Size (Largest)":
            return sorted(videos, key=lambda p: self._safe_size(p), reverse=True)
        elif mode == "Size (Smallest)":
            return sorted(videos, key=lambda p: self._safe_size(p))
        return sorted(videos, key=lambda p: natural_sort_key(os.path.basename(p)))

    def _exit_folder_detail(self) -> None:
        self.current_folder = None
        self.visible_video_limit = BATCH_PAGE_SIZE
        self._render_current_view()

    def _browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Add Video Folder to Library")
        if chosen and os.path.isdir(chosen):
            self.scanner.add_custom_folder(chosen)
            self.start_rescan()

    def _browse_file(self) -> None:
        filetypes = [("Video files", "*.mp4 *.mkv *.webm *.avi *.mov *.m4v *.m2ts *.mts *.flv"), ("All files", "*.*")]
        chosen = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if chosen and os.path.isfile(chosen):
            folder = os.path.dirname(chosen)
            self.scanner.add_custom_folder(folder)
            self.current_folder = os.path.normpath(folder)
            self.active_tab = "Folders"
            self.tab_segmented.set("Folders")
            self.load_folder(folder, play_target=chosen)

    def load_folder(self, folder_path: str, play_target: Optional[str] = None) -> None:
        """Loads a specific folder directly into view."""
        norm = os.path.normpath(folder_path)
        if not os.path.isdir(norm):
            return
        self.current_folder = norm
        self.active_tab = "Folders"
        self.tab_segmented.set("Folders")
        self.visible_video_limit = BATCH_PAGE_SIZE
        self.on_folder_selected(norm)

        # Quick scan if not present
        if norm not in self.folders_dict:
            try:
                exts = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".flv", ".wmv", ".3gp", ".ogv", ".vob", ".mpg", ".mpeg", ".m2ts", ".mts"}
                vids = [
                    entry.path for entry in os.scandir(norm)
                    if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts
                ]
                vids.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
                self.folders_dict[norm] = vids
            except Exception:
                pass

        self._render_current_view()

        if play_target and norm in self.folders_dict:
            self.on_play_video(play_target, self.folders_dict[norm])

    # --------------------------------------------------------------------------
    # Rendering Orchestration
    # --------------------------------------------------------------------------

    def _render_current_view(self) -> None:
        for w in self.scroll_list.winfo_children():
            w.destroy()

        query = self.search_entry.get().strip().lower()

        if self.active_tab == "Folders":
            if self.current_folder:
                self._render_folder_detail_view(query)
            else:
                self._render_folders_list_view(query)
        elif self.active_tab == "All Videos":
            self._render_all_videos_view(query)
        elif self.active_tab == "Recent":
            self._render_recent_view(query)
        elif self.active_tab == "Seen":
            self._render_seen_view(query)

    # --------------------------------------------------------------------------
    # 1. Folders List View
    # --------------------------------------------------------------------------

    def _render_folders_list_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        if not self.scanner.is_scanning:
            self.lbl_path.configure(text="Discovered Media Folders")

        folder_items = []
        for fpath, vids in self.folders_dict.items():
            name = os.path.basename(fpath) or fpath
            if query and query not in name.lower() and query not in fpath.lower():
                continue
            folder_items.append((name, fpath, len(vids)))

        folder_items = self._sort_folders(folder_items)

        total_vids = sum(len(v) for v in self.folders_dict.values())
        self.lbl_count.configure(text=f"{len(folder_items)} folders · {total_vids} videos")

        if not folder_items:
            msg = "Searching for video folders..." if self.scanner.is_scanning else "No video folders discovered yet."
            if query:
                msg = f"No folders matching '{query}'"
            frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
            frame.pack(pady=50)
            ctk.CTkLabel(frame, text=msg, font=("Segoe UI", 13), text_color="#64748B").pack()
            if not query and not self.scanner.is_scanning:
                ctk.CTkButton(
                    frame, text="Add Folder to Scan", fg_color="#161B26", hover_color="#1E293B",
                    command=self._browse_folder
                ).pack(pady=10)
            return

        for name, fpath, count in folder_items:
            self._create_folder_card(name, fpath, count)

    def _create_folder_card(self, name: str, fpath: str, count: int) -> None:
        card = ctk.CTkFrame(self.scroll_list, fg_color="#161B26", corner_radius=8, height=60)
        card.pack(fill="x", pady=4)

        icon_lbl = ctk.CTkLabel(card, text="📁", font=("Segoe UI", 16), text_color="#38BDF8")
        icon_lbl.pack(side="left", padx=(14, 10))

        info_box = ctk.CTkFrame(card, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True, pady=8)

        title_row = ctk.CTkFrame(info_box, fg_color="transparent")
        title_row.pack(fill="x")

        lbl_title = ctk.CTkLabel(title_row, text=name, font=("Segoe UI", 13, "bold"), text_color="#FFFFFF", anchor="w")
        lbl_title.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            title_row, text=f" {count} {'video' if count == 1 else 'videos'} ",
            font=("Segoe UI", 10, "bold"), text_color="#38BDF8", fg_color="#18283E", corner_radius=4
        )
        lbl_badge.pack(side="left", padx=8)

        lbl_path = ctk.CTkLabel(info_box, text=fpath, font=("Segoe UI", 10), text_color="#64748B", anchor="w")
        lbl_path.pack(fill="x")

        btn_open = ctk.CTkButton(
            card, text="Open >", width=75, height=28,
            fg_color="#1E293B", hover_color="#0099FF", font=("Segoe UI", 10, "bold"),
            command=lambda p=fpath: self._enter_folder(p)
        )
        btn_open.pack(side="right", padx=14)

        click_cmd = lambda e=None, p=fpath: self._enter_folder(p)
        card.bind("<Button-1>", click_cmd)
        icon_lbl.bind("<Button-1>", click_cmd)
        info_box.bind("<Button-1>", click_cmd)
        lbl_title.bind("<Button-1>", click_cmd)
        lbl_badge.bind("<Button-1>", click_cmd)
        lbl_path.bind("<Button-1>", click_cmd)

    def _enter_folder(self, fpath: str) -> None:
        self.current_folder = fpath
        self.visible_video_limit = BATCH_PAGE_SIZE
        self._render_current_view()

    # --------------------------------------------------------------------------
    # 2. Folder Detail View (Inside a specific folder)
    # --------------------------------------------------------------------------

    def _render_folder_detail_view(self, query: str) -> None:
        self.btn_back_folder.pack(side="left", padx=(10, 4))
        self.lbl_path.configure(text=f"Folder: {self.current_folder}")

        all_in_folder = self.folders_dict.get(self.current_folder, [])
        sorted_all = self._sort_videos(all_in_folder)
        videos = sorted_all
        if query:
            videos = [v for v in videos if query in os.path.basename(v).lower()]

        total_count = len(videos)
        self.lbl_count.configure(text=f"{total_count} videos")

        if not videos:
            msg = "No videos in this folder" if not query else "No matching videos found"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#64748B").pack(pady=40)
            return

        # Folder batch action header
        batch_header = ctk.CTkFrame(self.scroll_list, fg_color="#161B26", corner_radius=6, height=40)
        batch_header.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            batch_header,
            text=f"Batch Actions ({total_count} videos):",
            font=("Segoe UI", 11, "bold"),
            text_color="#8B98A5"
        ).pack(side="left", padx=12, pady=6)

        btn_batch_play = ctk.CTkButton(
            batch_header,
            text="▶ Play All",
            width=80,
            height=28,
            fg_color="#0099FF",
            hover_color="#0088EE",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.on_play_video(sorted_all[0], sorted_all) if sorted_all else None
        )
        btn_batch_play.pack(side="right", padx=(4, 10))

        btn_batch_sub = ctk.CTkButton(
            batch_header,
            text="AI Sub (Folder)",
            width=110,
            height=28,
            fg_color="#1E293B",
            hover_color="#27354A",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.on_generate_ai_subtitles(sorted_all)
        )
        btn_batch_sub.pack(side="right", padx=4)

        showing_vids = videos[:self.visible_video_limit]
        for vid in showing_vids:
            self._create_video_row(vid, context_videos=sorted_all)

        if total_count > self.visible_video_limit:
            self._create_load_more_button(total_count)

    # --------------------------------------------------------------------------
    # 3. All Videos View (Unified flat library)
    # --------------------------------------------------------------------------

    def _render_all_videos_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        self.lbl_path.configure(text="All Videos (Device Library)")

        all_vids = []
        for vids in self.folders_dict.values():
            all_vids.extend(vids)
        all_vids = list(dict.fromkeys(all_vids))
        all_vids = self._sort_videos(all_vids)

        videos = all_vids
        if query:
            videos = [v for v in videos if query in os.path.basename(v).lower()]

        total_count = len(videos)
        self.lbl_count.configure(text=f"{total_count} videos")

        if not videos:
            msg = "Scanning device for videos..." if self.scanner.is_scanning else "No videos discovered."
            if query:
                msg = f"No videos matching '{query}'"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#64748B").pack(pady=40)
            return

        showing_vids = videos[:self.visible_video_limit]
        for vid in showing_vids:
            self._create_video_row(vid, context_videos=videos, show_folder_tag=True)

        if total_count > self.visible_video_limit:
            self._create_load_more_button(total_count)

    # --------------------------------------------------------------------------
    # 4. Recent Videos View
    # --------------------------------------------------------------------------

    def _render_recent_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        self.lbl_path.configure(text="Recently Watched Videos")

        recent_entries = self.history.get_recent_videos() if self.history else []
        recent_paths = [e["path"] for e in recent_entries if os.path.isfile(e["path"])]

        if query:
            recent_paths = [p for p in recent_paths if query in os.path.basename(p).lower()]

        total_count = len(recent_paths)
        self.lbl_count.configure(text=f"{total_count} recent videos")

        # Action header for Recent tab
        if recent_paths:
            header_bar = ctk.CTkFrame(self.scroll_list, fg_color="#161B26", corner_radius=6, height=40)
            header_bar.pack(fill="x", pady=(0, 6))

            ctk.CTkLabel(
                header_bar,
                text="Resume where you left off:",
                font=("Segoe UI", 11, "bold"),
                text_color="#8B98A5"
            ).pack(side="left", padx=12, pady=6)

            btn_clear_recent = ctk.CTkButton(
                header_bar,
                text="Clear Recent",
                width=100,
                height=28,
                fg_color="#1E293B",
                hover_color="#7F1D1D",
                font=("Segoe UI", 11, "bold"),
                command=self._confirm_clear_recent
            )
            btn_clear_recent.pack(side="right", padx=(4, 10))

        if not recent_paths:
            ctk.CTkLabel(
                self.scroll_list,
                text="No recently watched videos.",
                font=("Segoe UI", 13),
                text_color="#64748B"
            ).pack(pady=40)
            return

        showing_vids = recent_paths[:self.visible_video_limit]
        for vid in showing_vids:
            self._create_video_row(vid, context_videos=recent_paths, show_folder_tag=True)

        if total_count > self.visible_video_limit:
            self._create_load_more_button(total_count)

    def _confirm_clear_recent(self) -> None:
        if messagebox.askyesno("Clear Recent History", "Clear all recent watch progress?"):
            if self.history:
                self.history.clear_recent_history()
            self._render_current_view()

    # --------------------------------------------------------------------------
    # 5. Seen Videos View (Completed / Marked as Seen)
    # --------------------------------------------------------------------------

    def _render_seen_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        self.lbl_path.configure(text="Completed & Marked as Seen Videos")

        seen_paths = self.history.get_seen_videos() if self.history else []
        seen_paths = [p for p in seen_paths if os.path.isfile(p)]

        if query:
            seen_paths = [p for p in seen_paths if query in os.path.basename(p).lower()]

        total_count = len(seen_paths)
        self.lbl_count.configure(text=f"{total_count} seen videos")

        # Seen Action Header with "Delete All Seen" and "Clear History"
        if seen_paths:
            header_bar = ctk.CTkFrame(self.scroll_list, fg_color="#161B26", corner_radius=6, height=40)
            header_bar.pack(fill="x", pady=(0, 6))

            ctk.CTkLabel(
                header_bar,
                text=f"Seen videos ({total_count}):",
                font=("Segoe UI", 11, "bold"),
                text_color="#8B98A5"
            ).pack(side="left", padx=12, pady=6)

            btn_del_all = ctk.CTkButton(
                header_bar,
                text="🗑 Delete All Seen",
                width=120,
                height=28,
                fg_color="#7F1D1D",
                hover_color="#991B1B",
                font=("Segoe UI", 11, "bold"),
                command=self._confirm_delete_all_seen
            )
            btn_del_all.pack(side="right", padx=(4, 10))

            btn_clear_seen = ctk.CTkButton(
                header_bar,
                text="Clear History",
                width=100,
                height=28,
                fg_color="#1E293B",
                hover_color="#27354A",
                font=("Segoe UI", 11, "bold"),
                command=self._confirm_clear_seen_history
            )
            btn_clear_seen.pack(side="right", padx=4)

        if not seen_paths:
            ctk.CTkLabel(
                self.scroll_list,
                text="No completed videos marked as seen yet.",
                font=("Segoe UI", 13),
                text_color="#64748B"
            ).pack(pady=40)
            return

        showing_vids = seen_paths[:self.visible_video_limit]
        for vid in showing_vids:
            self._create_video_row(vid, context_videos=seen_paths, show_folder_tag=True)

        if total_count > self.visible_video_limit:
            self._create_load_more_button(total_count)

    def _confirm_delete_all_seen(self) -> None:
        if not self.history:
            return
        seen_count = len(self.history.get_seen_videos())
        if seen_count == 0:
            return
        if messagebox.askyesno(
            "Delete All Seen Videos",
            f"Permanently delete all {seen_count} seen videos from disk and remove them from library?"
        ):
            del_count, freed_bytes = self.history.delete_all_seen()
            freed_str = format_file_size(freed_bytes)
            # Remove deleted files from folders_dict
            self._prune_missing_files()
            messagebox.showinfo("Seen Videos Deleted", f"Deleted {del_count} videos ({freed_str} freed).")
            self._render_current_view()

    def _confirm_clear_seen_history(self) -> None:
        if not self.history:
            return
        if messagebox.askyesno(
            "Clear Seen History",
            "Clear all seen video marks from history? (Files will NOT be deleted from disk)"
        ):
            self.history.clear_seen_history()
            self._render_current_view()

    def _prune_missing_files(self) -> None:
        """Removes deleted or non-existent files from folders_dict."""
        for fpath in list(self.folders_dict.keys()):
            self.folders_dict[fpath] = [v for v in self.folders_dict[fpath] if os.path.isfile(v)]
            if not self.folders_dict[fpath] and not os.path.isdir(fpath):
                del self.folders_dict[fpath]

    def _create_load_more_button(self, total_count: int) -> None:
        remaining = total_count - self.visible_video_limit
        next_count = min(BATCH_PAGE_SIZE, remaining)
        btn_more = ctk.CTkButton(
            self.scroll_list,
            text=f"Load {next_count} More Videos ({self.visible_video_limit} of {total_count})",
            height=36, fg_color="#161B26", hover_color="#1E293B",
            font=("Segoe UI", 11, "bold"), text_color="#38BDF8",
            command=self._load_more_videos
        )
        btn_more.pack(fill="x", pady=10)

    def _load_more_videos(self) -> None:
        self.visible_video_limit += BATCH_PAGE_SIZE
        self._render_current_view()

    def refresh_display(self) -> None:
        """Re-renders current view to reflect new subtitles or updated progress."""
        self._render_current_view()

    # --------------------------------------------------------------------------
    # Video Row Card with Context Menu & Mobile v2.23 Styling
    # --------------------------------------------------------------------------

    def _create_video_row(self, vid_path: str, context_videos: List[str], show_folder_tag: bool = False) -> None:
        filename = os.path.basename(vid_path)
        resume_pos = self.get_resume_pos(vid_path)
        is_seen = self.is_seen_checker(vid_path)

        try:
            size_str = format_file_size(os.path.getsize(vid_path))
        except Exception:
            size_str = ""

        # Check for existing SRT subtitle file
        stem = os.path.splitext(vid_path)[0]
        has_srt = os.path.isfile(f"{stem}.srt")

        row = ctk.CTkFrame(self.scroll_list, fg_color="#161B26", corner_radius=6, height=54)
        row.pack(fill="x", pady=3)

        # Icon box (Green checkmark if seen, else play arrow)
        icon_text = "✓" if is_seen else "▶"
        icon_color = "#00E676" if is_seen else "#0099FF"
        icon_lbl = ctk.CTkLabel(row, text=icon_text, font=("Segoe UI", 13, "bold"), text_color=icon_color, width=28)
        icon_lbl.pack(side="left", padx=(10, 4))

        info_box = ctk.CTkFrame(row, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True, pady=6)

        title = ctk.CTkLabel(info_box, text=filename, font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", anchor="w")
        title.pack(fill="x")

        status_text = ""
        if has_srt:
            status_text = "[CC Sub]  "

        if resume_pos > 3000:
            sec = resume_pos // 1000
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            t_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            status_text += f"Resume at {t_str} · {size_str}"
        elif is_seen:
            status_text += f"Completed · {size_str}"
        else:
            status_text += size_str

        if show_folder_tag:
            folder_name = os.path.basename(os.path.dirname(vid_path))
            status_text = f"[{folder_name}]  |  {status_text}"

        sub_label = ctk.CTkLabel(info_box, text=status_text, font=("Segoe UI", 10), text_color="#8B98A5", anchor="w")
        sub_label.pack(fill="x")

        # Click to play
        play_cmd = lambda e=None, p=vid_path: self.on_play_video(p, context_videos)
        row.bind("<Button-1>", play_cmd)
        icon_lbl.bind("<Button-1>", play_cmd)
        info_box.bind("<Button-1>", play_cmd)
        title.bind("<Button-1>", play_cmd)
        sub_label.bind("<Button-1>", play_cmd)

        # Right-click context menu binding
        ctx_cmd = lambda e, p=vid_path: self._show_context_menu(e, p, context_videos)
        row.bind("<Button-3>", ctx_cmd)
        icon_lbl.bind("<Button-3>", ctx_cmd)
        info_box.bind("<Button-3>", ctx_cmd)
        title.bind("<Button-3>", ctx_cmd)
        sub_label.bind("<Button-3>", ctx_cmd)

        btn_play = ctk.CTkButton(
            row, text="Play", width=62, height=30, fg_color="#0099FF", hover_color="#0088EE",
            font=("Segoe UI", 11, "bold"),
            command=lambda p=vid_path: self.on_play_video(p, context_videos)
        )
        btn_play.pack(side="right", padx=(4, 10))

        btn_ai_sub = ctk.CTkButton(
            row, text="AI Sub", width=58, height=30, fg_color="#1E293B", hover_color="#27354A",
            font=("Segoe UI", 10, "bold"),
            command=lambda p=vid_path: self.on_generate_ai_subtitles([p])
        )
        btn_ai_sub.pack(side="right", padx=(4, 4))

    def _show_context_menu(self, event, vid_path: str, context_videos: List[str]) -> None:
        """Displays rich right-click context menu for a video card."""
        menu = Menu(self, tearoff=0, bg="#161B26", fg="#E0E6ED", activebackground="#0099FF", activeforeground="#FFFFFF")
        menu.add_command(label="▶ Play Video", command=lambda: self.on_play_video(vid_path, context_videos))

        is_seen = self.is_seen_checker(vid_path)
        if is_seen:
            menu.add_command(label="Mark as Unseen", command=lambda: self._mark_unseen(vid_path))
        else:
            menu.add_command(label="✓ Mark as Seen", command=lambda: self._mark_seen(vid_path))

        menu.add_separator()
        menu.add_command(label="📁 Show in File Explorer", command=lambda: self._open_in_explorer(vid_path))
        menu.add_command(label="⚡ Generate AI Subtitles", command=lambda: self.on_generate_ai_subtitles([vid_path]))
        menu.add_separator()
        menu.add_command(label="🗑 Delete Video", command=lambda: self._delete_single_video(vid_path))

        menu.tk_popup(event.x_root, event.y_root)

    def _mark_seen(self, vid_path: str) -> None:
        if self.history:
            self.history.toggle_seen(vid_path)
        self._render_current_view()

    def _mark_unseen(self, vid_path: str) -> None:
        if self.history:
            self.history.mark_as_unseen(vid_path)
        self._render_current_view()

    def _open_in_explorer(self, vid_path: str) -> None:
        try:
            folder = os.path.dirname(os.path.abspath(vid_path))
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.abspath(vid_path)}"')
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _delete_single_video(self, vid_path: str) -> None:
        filename = os.path.basename(vid_path)
        if messagebox.askyesno("Delete Video", f"Are you sure you want to permanently delete '{filename}' from disk?"):
            if self.history:
                self.history.delete_video(vid_path)
            elif os.path.isfile(vid_path):
                try:
                    os.remove(vid_path)
                except Exception:
                    pass
            self._prune_missing_files()
            self._render_current_view()
