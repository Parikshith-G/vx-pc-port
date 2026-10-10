"""
Role: Progressive media library and folder discovery navigator.
Responsibility: Incrementally discovers and displays video folders and files without freezing or high CPU usage.
Details: Shows real-time scanning path in top status bar, supports cancellation, batched rendering, and natural sorting.
"""

import os
import threading
import time
from tkinter import filedialog
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
    """Media library browser with incremental folder discovery, live scan status, and batched rendering."""

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
        self.current_folder: Optional[str] = None  # None = root folder list; str = inside folder
        self.folders_dict: Dict[str, List[str]] = {}  # folder_path -> [video_paths]
        self.visible_video_limit: int = BATCH_PAGE_SIZE

        self.scanner = ProgressiveMediaScanner(additional_roots=self.recent_folders_getter())
        self.scan_thread: Optional[threading.Thread] = None

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

        # Scan & Action Buttons
        self.btn_scan_toggle = ctk.CTkButton(
            toolbar, text="🔄 Rescan", width=85, height=30,
            fg_color="#262626", hover_color="#383838",
            font=("Segoe UI", 11),
            command=self._toggle_scan
        )
        self.btn_scan_toggle.pack(side="left", padx=4)

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
            toolbar, placeholder_text="Search videos or folders...", width=190, height=30
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
            width=130,
            height=30,
            fg_color="#262626",
            button_color="#333333",
            button_hover_color="#404040",
            dropdown_fg_color="#222222",
            dropdown_hover_color="#383838",
            font=("Segoe UI", 11),
            dropdown_font=("Segoe UI", 11),
            command=self._on_sort_changed
        )
        self.sort_option.set("Name (A-Z)")
        self.sort_option.pack(side="right", padx=(4, 4))

        lbl_sort = ctk.CTkLabel(
            toolbar, text="Sort:", font=("Segoe UI", 11), text_color="#A0A0A0"
        )
        lbl_sort.pack(side="right", padx=(8, 2))

        # 2. Real-time Live Scan Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color="#1A1A1A", height=38, corner_radius=0)
        self.status_bar.pack(fill="x")

        self.btn_back_folder = ctk.CTkButton(
            self.status_bar, text="⬅ Back to Folders", width=120, height=26,
            fg_color="#2E2E2E", hover_color="#404040",
            font=("Segoe UI", 11, "bold"),
            command=self._exit_folder_detail
        )

        self.lbl_path = ctk.CTkLabel(
            self.status_bar, text="Ready",
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
    # Incremental Scanning & Live UI Feedback
    # --------------------------------------------------------------------------

    def _toggle_scan(self) -> None:
        if self.scanner.is_scanning:
            self.scanner.stop()
            self.btn_scan_toggle.configure(text="🔄 Rescan", fg_color="#262626")
            self.lbl_path.configure(text="⏹ Scan stopped by user")
            self._render_current_view()
        else:
            self.start_rescan()

    def start_rescan(self) -> None:
        """Starts an incremental background scan showing real-time scanning paths."""
        if self.scanner.is_scanning:
            return

        self.btn_scan_toggle.configure(text="⏹ Stop Scan", fg_color="#A02020", hover_color="#C02828")
        self.lbl_path.configure(text="🔍 Initializing scan...")
        self._last_status_update = 0.0

        def _on_status_thread(current_path: str):
            # Throttle status label updates to max ~10 per second to keep UI completely calm
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
            self.lbl_path.configure(text=f"🔍 Scanning: {short_path}")
            self.lbl_count.configure(text=f"{total_f} folders · {total_v} videos")

    def _add_discovered_folder(self, folder_path: str, videos: List[str]) -> None:
        # Accumulate folder quietly without refreshing UI list during scan
        self.folders_dict[folder_path] = videos

    def _on_scan_finished(self, total_folders: int, total_videos: int) -> None:
        self.btn_scan_toggle.configure(text="🔄 Rescan", fg_color="#262626", hover_color="#383838")
        total_f = len(self.folders_dict)
        total_v = sum(len(v) for v in self.folders_dict.values())
        self.lbl_path.configure(text=f"✓ Scan completed · {total_f} video folders found")
        self.lbl_count.configure(text=f"{total_f} folders · {total_v} videos")
        # Render the UI list once when scan completes
        self._render_current_view()

    # --------------------------------------------------------------------------
    # Navigation & Interaction
    # --------------------------------------------------------------------------

    def _on_tab_changed(self, value: str) -> None:
        self.visible_video_limit = BATCH_PAGE_SIZE
        if "Folders" in value:
            self.active_tab = "folders"
            self.current_folder = None
        else:
            self.active_tab = "all_videos"
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
        if not self.scanner.is_scanning:
            self.lbl_path.configure(text="📁 Discovered Device Video Folders")

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
            ctk.CTkLabel(frame, text=msg, font=("Segoe UI", 13), text_color="#707070").pack()
            if not query and not self.scanner.is_scanning:
                ctk.CTkButton(
                    frame, text="📁 Add Folder to Scan", fg_color="#262626", hover_color="#383838",
                    command=self._browse_folder
                ).pack(pady=10)
            return

        for name, fpath, count in folder_items:
            self._create_folder_card(name, fpath, count)

    def _create_folder_card(self, name: str, fpath: str, count: int) -> None:
        card = ctk.CTkFrame(self.scroll_list, fg_color="#1E1E1E", corner_radius=8, height=60)
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

        btn_open = ctk.CTkButton(
            card, text="Open ➔", width=75, height=28,
            fg_color="#282828", hover_color="#FF8C00", font=("Segoe UI", 10, "bold"),
            command=lambda p=fpath: self._enter_folder(p)
        )
        btn_open.pack(side="right", padx=14)

        # Card click handler
        click_cmd = lambda e=None, p=fpath: self._enter_folder(p)
        card.bind("<Button-1>", click_cmd)
        icon.bind("<Button-1>", click_cmd)
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
        self.lbl_path.configure(text=f"📂 {self.current_folder}")

        all_in_folder = self.folders_dict.get(self.current_folder, [])
        sorted_all = self._sort_videos(all_in_folder)
        videos = sorted_all
        if query:
            videos = [v for v in videos if query in os.path.basename(v).lower()]

        total_count = len(videos)
        self.lbl_count.configure(text=f"{total_count} videos")

        if not videos:
            msg = "No videos in this folder" if not query else "No matching videos found"
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#707070").pack(pady=40)
            return

        # Render up to visible_video_limit items to prevent Tkinter freezing
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
        self.lbl_path.configure(text="🎬 All Videos (Device Library)")

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
            ctk.CTkLabel(self.scroll_list, text=msg, font=("Segoe UI", 13), text_color="#707070").pack(pady=40)
            return

        showing_vids = videos[:self.visible_video_limit]
        for vid in showing_vids:
            self._create_video_row(vid, context_videos=videos, show_folder_tag=True)

        if total_count > self.visible_video_limit:
            self._create_load_more_button(total_count)

    def _create_load_more_button(self, total_count: int) -> None:
        remaining = total_count - self.visible_video_limit
        next_count = min(BATCH_PAGE_SIZE, remaining)
        btn_more = ctk.CTkButton(
            self.scroll_list,
            text=f"⬇ Load {next_count} More Videos ({self.visible_video_limit} of {total_count})",
            height=36, fg_color="#242424", hover_color="#333333",
            font=("Segoe UI", 11, "bold"),
            command=self._load_more_videos
        )
        btn_more.pack(fill="x", pady=10)

    def _load_more_videos(self) -> None:
        self.visible_video_limit += BATCH_PAGE_SIZE
        self._render_current_view()

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
