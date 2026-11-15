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

        # Outer border frame for sleek pill look with VX Player blue accent
        border_frame = tk.Frame(self.top, bg="#0099FF", padx=1, pady=1)
        border_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(border_frame, bg="#0D1117", padx=18, pady=8)
        inner_frame.pack(fill="both", expand=True)

        self.label = tk.Label(
            inner_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            fg="#FFFFFF",
            bg="#0D1117"
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


class ErrorBanner:
    """Floating 10-second non-fatal error banner matching mobile VX Player AppErrorManager."""

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
        self.top.configure(bg="#000000")

        # Crimson danger border frame
        border = tk.Frame(self.top, bg="#FF453A", padx=1, pady=1)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg="#2A0F13", padx=14, pady=8)
        inner.pack(fill="both", expand=True)

        # Warning icon
        icon = tk.Label(inner, text="⚠", font=("Segoe UI", 12, "bold"), fg="#FF453A", bg="#2A0F13")
        icon.pack(side="left", padx=(0, 8))

        self.label = tk.Label(
            inner,
            text="",
            font=("Segoe UI", 10),
            fg="#FFFFFF",
            bg="#2A0F13",
            wraplength=480,
            justify="left"
        )
        self.label.pack(side="left", fill="both", expand=True)

        # Close button
        close_btn = tk.Label(inner, text="✕", font=("Segoe UI", 11, "bold"), fg="#A0A0A0", bg="#2A0F13", cursor="hand2")
        close_btn.pack(side="right", padx=(8, 0))
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#FFFFFF"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#A0A0A0"))

        self.top.withdraw()

    def show(self, message: str, duration_ms: int = 10000) -> None:
        """Displays error banner for 10 seconds (matches mobile AppErrorManager)."""
        if not self.parent.winfo_ismapped():
            return

        if self._hide_timer:
            self.parent.after_cancel(self._hide_timer)
            self._hide_timer = None

        self._ensure_widget()
        if self.label is not None:
            self.label.configure(text=message)

        if self.top is None or not self.top.winfo_exists():
            return

        self.top.deiconify()
        self.top.update_idletasks()

        pw = self.parent.winfo_width()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        tw = self.top.winfo_reqwidth()
        th = self.top.winfo_reqheight()

        x = px + max(10, (pw - tw) // 2)
        y = py + 24
        self.top.geometry(f"{tw}x{th}+{x}+{y}")

        if duration_ms > 0:
            self._hide_timer = self.parent.after(duration_ms, self.hide)

    def hide(self) -> None:
        if self._hide_timer:
            self.parent.after_cancel(self._hide_timer)
            self._hide_timer = None

        if self.top is not None and self.top.winfo_exists():
            self.top.withdraw()
