"""
Role: On-Screen Display (OSD) notification pill for desktop playback.
Responsibility: Displays temporary translucent overlay badges for speed, volume, and OP skip on top of video.
Details: Uses a borderless topmost Tkinter Toplevel window to render clearly over native VLC HWND surface.
"""

import tkinter as tk
from typing import Optional


class OsdNotification:
    """Floating borderless OSD pill displaying real-time feedback over VLC video surface."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.top: Optional[tk.Toplevel] = None
        self.label: Optional[tk.Label] = None
        self._hide_timer: Optional[str] = None

    def _ensure_widget(self) -> None:
        if self.top is not None and self.top.winfo_exists():
            return

        self.top = tk.Toplevel(self.parent)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="#0F0F0F")

        # Outer border frame for sleek pill look
        border_frame = tk.Frame(self.top, bg="#FF8C00", padx=1, pady=1)
        border_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(border_frame, bg="#161616", padx=18, pady=8)
        inner_frame.pack(fill="both", expand=True)

        self.label = tk.Label(
            inner_frame,
            text="",
            font=("Segoe UI", 13, "bold"),
            fg="#FFFFFF",
            bg="#161616"
        )
        self.label.pack()
        self.top.withdraw()

    def show(self, text: str, duration_ms: int = 1200) -> None:
        """Displays OSD badge with specified text. If duration_ms is 0, badge remains visible."""
        if not self.parent.winfo_ismapped():
            return

        if self._hide_timer:
            self.parent.after_cancel(self._hide_timer)
            self._hide_timer = None

        self._ensure_widget()
        if self.label is not None:
            self.label.configure(text=text)

        if self.top is None or not self.top.winfo_exists():
            return

        self.top.deiconify()
        self.top.update_idletasks()

        # Center horizontally at top quarter of the parent window
        pw = self.parent.winfo_width()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        tw = self.top.winfo_reqwidth()
        th = self.top.winfo_reqheight()

        x = px + max(10, (pw - tw) // 2)
        y = py + 52
        self.top.geometry(f"{tw}x{th}+{x}+{y}")

        if duration_ms > 0:
            self._hide_timer = self.parent.after(duration_ms, self.hide)

    def hide(self) -> None:
        """Hides the OSD badge immediately."""
        if self._hide_timer:
            self.parent.after_cancel(self._hide_timer)
            self._hide_timer = None

        if self.top is not None and self.top.winfo_exists():
            self.top.withdraw()
