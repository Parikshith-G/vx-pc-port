"""
Role: Mobile-style media library and folder discovery navigator.
Responsibility: Automatically discovers, groups, and lists video folders and files without manual folder picking.
Details: Provides 2-tab navigation (Folders / All Videos), natural sorting, search filtering, and background scanning.
"""

import os
import threading
from tkinter import filedialog
from typing import Callable, Dict, List, Optional
import customtkinter as ctk  # type: ignore

from core.media_scanner import MediaScanner
from core.natural_sort import natural_sort_key


def format_file_size(size_bytes: int) -> str:
    """Formats bytes into KB, MB, or GB."""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class LibraryView(ctk.CTkFrame):
    """Media library browser with mobile-style automatic folder discovery, Folders/All Videos tabs, and search."""

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

        # State
        self.active_tab: str = "folders"  # "folders" | "all_videos"
        self.current_folder: Optional[str] = None  # None = root folder list; str = inside specific folder
        self.folders_dict: Dict[str, List[str]] = {}  # folder_path -> [video_paths]
        self.all_videos_list: List[str] = []
        self.is_scanning: bool = False

        self.scanner = MediaScanner(additional_roots=self.recent_folders_getter())
        self._build_ui()
        self.start_rescan()

    def _build_ui(self) -> None:
        # 1. Top main toolbar
        toolbar = ctk.CTkFrame(self, fg_color="#181818", height=54, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=0)

        # Brand Title
        ctk.CTkLabel(
            toolbar, text="VX Player PC", font=("Segoe UI", 16, "bold"), text_color="#FF8C00"
        ).pack(side="left", padx=(16, 12))

        # 2-Tab Segmented Switcher (Mobile style: Folders vs All Videos)
        self.tab_segmented = ctk.CTkSegmentedButton(
            toolbar,
            values=["📁 Folders", "🎬 All Videos"],
            command=self._on_tab_changed,
            selected_color="#FF8C00",
            selected_hover_color="#E07B00",
            unselected_color="#262626",
            unselected_hover_color="#333333",
            font=("Segoe UI", 11, "bold"),
            height=30
        )
        self.tab_segmented.set("📁 Folders")
        self.tab_segmented.pack(side="left", padx=10)

        # Action Buttons
        self.btn_rescan = ctk.CTkButton(
            toolbar, text="🔄 Rescan", width=85, height=30,
            fg_color="#262626", hover_color="#383838",
            font=("Segoe UI", 11),
            command=self.start_rescan
        )
        self.btn_rescan.pack(side="left", padx=4)

        btn_folder = ctk.CTkButton(
            toolbar, text="📁 Add Folder", width=95, height=30,
            fg_color="#262626", hover_color="#383838",
            font=("Segoe UI", 11),
            command=self._browse_folder
        )
        btn_folder.pack(side="left", padx=4)

        btn_file = ctk.CTkButton(
            toolbar, text="🎬 Open File", width=85, height=30,
            fg_color="#262626", hover_color="#383838",
            font=("Segoe UI", 11),
            command=self._browse_file
        )
        btn_file.pack(side="left", padx=4)

        # Search Bar
        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="Search videos or folders...", width=220, height=30
        )
        self.search_entry.pack(side="right", padx=16)
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_current_view())

        # 2. Sub-navigation / Breadcrumb status bar
        self.status_bar = ctk.CTkFrame(self, fg_color="#1A1A1A", height=36, corner_radius=0)
        self.status_bar.pack(fill="x")

        self.btn_back_folder = ctk.CTkButton(
            self.status_bar, text="⬅ Back to Folders", width=120, height=26,
            fg_color="#2E2E2E", hover_color="#404040",
            font=("Segoe UI", 11, "bold"),
            command=self._exit_folder_detail
        )

        self.lbl_path = ctk.CTkLabel(
            self.status_bar, text="Scanning for device video folders...",
            font=("Segoe UI", 11), text_color="#A0A0A0"
        )
        self.lbl_path.pack(side="left", padx=14)

        self.lbl_count = ctk.CTkLabel(
            self.status_bar, text="", font=("Segoe UI", 11, "bold"), text_color="#FF8C00"
        )
        self.lbl_count.pack(side="right", padx=14)

        # 3. Content scroll area
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=14, pady=10)

    # --------------------------------------------------------------------------
    # Scanning & Data Management
    # --------------------------------------------------------------------------

    def start_rescan(self) -> None:
        """Runs the media scanner asynchronously in a background thread."""
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_rescan.configure(text="Scanning...", state="disabled")
        self.lbl_path.configure(text="Scanning drives and library folders for videos...")

        def _worker():
            try:
                results = self.scanner.scan_all()
                all_vids = MediaScanner.get_all_videos_list(results)
            except Exception:
                results = {}
                all_vids = []

            # Post results back to Tkinter main thread
            self.after(0, self._on_scan_completed, results, all_vids)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _on_scan_completed(self, results: Dict[str, List[str]], all_vids: List[str]) -> None:
        self.is_scanning = False
        self.btn_rescan.configure(text="🔄 Rescan", state="normal")
        self.folders_dict = results
        self.all_videos_list = all_vids

        # Notify recent folders manager
        for folder in self.folders_dict.keys():
            self.on_folder_selected(folder)

        self._render_current_view()

    def _on_tab_changed(self, value: str) -> None:
        if "Folders" in value:
            self.active_tab = "folders"
            self.current_folder = None  # Reset to root folders list
        else:
            self.active_tab = "all_videos"
            self.current_folder = None
        self._render_current_view()

    def _exit_folder_detail(self) -> None:
        self.current_folder = None
        self._render_current_view()

    def _browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Add Video Folder to Library")
        if chosen and os.path.isdir(chosen):
            self.scanner.add_root(chosen)
            self.start_rescan()

    def _browse_file(self) -> None:
        filetypes = [("Video files", "*.mp4 *.mkv *.webm *.avi *.mov *.m4v *.ts *.flv"), ("All files", "*.*")]
        chosen = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if chosen and os.path.isfile(chosen):
            folder = os.path.dirname(chosen)
            self.scanner.add_root(folder)
            self.current_folder = os.path.normpath(folder)
            self.active_tab = "folders"
            self.tab_segmented.set("📁 Folders")
            self.load_folder(folder, play_target=chosen)

    def load_folder(self, folder_path: str, play_target: Optional[str] = None) -> None:
        """Loads a specific folder directly into view."""
        norm = os.path.normpath(folder_path)
        if not os.path.isdir(norm):
            return
        self.current_folder = norm
        self.active_tab = "folders"
        self.tab_segmented.set("📁 Folders")
        self.on_folder_selected(norm)

        # Quick scan if not present
        if norm not in self.folders_dict:
            try:
                exts = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".flv", ".wmv", ".ts", ".3gp", ".ogv", ".vob", ".mpg", ".mpeg"}
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

        if self.active_tab == "folders":
            if self.current_folder:
                self._render_folder_detail_view(query)
            else:
                self._render_folders_list_view(query)
        else:
            self._render_all_videos_view(query)

    # --------------------------------------------------------------------------
    # 1. Folders List View
    # --------------------------------------------------------------------------

    def _render_folders_list_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        self.lbl_path.configure(text="📁 Discovered Device Video Folders")

        folder_items = []
        for fpath, vids in self.folders_dict.items():
            name = os.path.basename(fpath) or fpath
            if query and query not in name.lower() and query not in fpath.lower():
                continue
            folder_items.append((name, fpath, len(vids)))

        folder_items.sort(key=lambda item: natural_sort_key(item[0]))

        total_vids = sum(len(v) for v in self.folders_dict.values())
        self.lbl_count.configure(text=f"{len(folder_items)} folders · {total_vids} videos")

        if not folder_items:
            msg = "No video folders discovered yet." if not query else f"No folders matching '{query}'"
            frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
            frame.pack(pady=50)
            ctk.CTkLabel(frame, text=msg, font=("Segoe UI", 13), text_color="#707070").pack()
            if not query:
                ctk.CTkButton(
                    frame, text="📁 Add Folder to Scan", fg_color="#262626", hover_color="#383838",
                    command=self._browse_folder
                ).pack(pady=10)
            return

        for name, fpath, count in folder_items:
            self._create_folder_card(name, fpath, count)

    def _create_folder_card(self, name: str, fpath: str, count: int) -> None:
        card = ctk.CTkFrame(self.scroll_list, fg_color="#1E1E1E", hover_color="#252525", corner_radius=8, height=60)
        card.pack(fill="x", pady=4)

        icon = ctk.CTkLabel(card, text="📁", font=("Segoe UI", 20))
        icon.pack(side="left", padx=(14, 10))

        info_box = ctk.CTkFrame(card, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True, pady=8)

        title_row = ctk.CTkFrame(info_box, fg_color="transparent")
        title_row.pack(fill="x")

        lbl_title = ctk.CTkLabel(title_row, text=name, font=("Segoe UI", 13, "bold"), text_color="#FFFFFF", anchor="w")
        lbl_title.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            title_row, text=f" {count} {'video' if count == 1 else 'videos'} ",
            font=("Segoe UI", 10, "bold"), text_color="#FF8C00", fg_color="#2D1F0E", corner_radius=4
        )
        lbl_badge.pack(side="left", padx=8)

        lbl_path = ctk.CTkLabel(info_box, text=fpath, font=("Segoe UI", 10), text_color="#808080", anchor="w")
        lbl_path.pack(fill="x")

        # Open action button
        btn_open = ctk.CTkButton(
            card, text="Open ➔", width=75, height=28,
            fg_color="#282828", hover_color="#FF8C00", font=("Segoe UI", 10, "bold"),
            command=lambda p=fpath: self._enter_folder(p)
        )
        btn_open.pack(side="right", padx=14)

        # Entire card is clickable
        click_cmd = lambda e=None, p=fpath: self._enter_folder(p)
        card.bind("<Button-1>", click_cmd)
        icon.bind("<Button-1>", click_cmd)
        info_box.bind("<Button-1>", click_cmd)
        lbl_title.bind("<Button-1>", click_cmd)
        lbl_badge.bind("<Button-1>", click_cmd)
        lbl_path.bind("<Button-1>", click_cmd)

    def _enter_folder(self, fpath: str) -> None:
        self.current_folder = fpath
        self._render_current_view()

    # --------------------------------------------------------------------------
    # 2. Folder Detail View (Inside a specific folder)
    # --------------------------------------------------------------------------

    def _render_folder_detail_view(self, query: str) -> None:
        folder_name = os.path.basename(self.current_folder) if self.current_folder else "Folder"
        self.btn_back_folder.pack(side="left", padx=(10, 4))
        self.lbl_path.configure(text=f"📂 {self.current_folder}")

        videos = self.folders_dict.get(self.current_folder, [])
        if query:
            videos = [v for v in videos if query in os.path.basename(v).lower()]

        self.lbl_count.configure(text=f"{len(videos)} videos")

        if not videos:
            msg = "No videos in this folder" if not query else "No matching videos found"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#707070").pack(pady=40)
            return

        for vid in videos:
            self._create_video_row(vid, context_videos=self.folders_dict.get(self.current_folder, []))

    # --------------------------------------------------------------------------
    # 3. All Videos View (Unified flat library)
    # --------------------------------------------------------------------------

    def _render_all_videos_view(self, query: str) -> None:
        self.btn_back_folder.pack_forget()
        self.lbl_path.configure(text="🎬 All Videos (Device Library)")

        videos = self.all_videos_list
        if query:
            videos = [v for v in videos if query in os.path.basename(v).lower()]

        self.lbl_count.configure(text=f"{len(videos)} videos")

        if not videos:
            msg = "No videos discovered on device." if not query else f"No videos matching '{query}'"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#707070").pack(pady=40)
            return

        for vid in videos:
            self._create_video_row(vid, context_videos=videos, show_folder_tag=True)

    # --------------------------------------------------------------------------
    # Video Row Card
    # --------------------------------------------------------------------------

    def _create_video_row(self, vid_path: str, context_videos: List[str], show_folder_tag: bool = False) -> None:
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

        if show_folder_tag:
            folder_name = os.path.basename(os.path.dirname(vid_path))
            status_text = f"📁 {folder_name}  |  {status_text}"

        sub_label = ctk.CTkLabel(info_box, text=status_text, font=("Segoe UI", 10), text_color="#A0A0A0", anchor="w")
        sub_label.pack(fill="x")

        play_cmd = lambda e=None, p=vid_path: self.on_play_video(p, context_videos)
        row.bind("<Button-1>", play_cmd)
        icon.bind("<Button-1>", play_cmd)
        info_box.bind("<Button-1>", play_cmd)
        title.bind("<Button-1>", play_cmd)
        sub_label.bind("<Button-1>", play_cmd)

        btn_play = ctk.CTkButton(
            row, text="▶ Play", width=68, height=30, fg_color="#FF8C00", hover_color="#FF7F00",
            font=("Segoe UI", 11, "bold"),
            command=lambda p=vid_path: self.on_play_video(p, context_videos)
        )
        btn_play.pack(side="right", padx=10)
