"""
Role: Media player controls bar HUD.
Responsibility: Displays playback progress slider, time labels, play/pause, seek, 90s OP skip, volume, and speed.
Details: Handles user slider scrubbing, button clicks, and visual state updates.
"""

from typing import Callable, Optional
import customtkinter as ctk  # type: ignore


def format_time(ms: int) -> str:
    """Formats milliseconds into MM:SS or HH:MM:SS format."""
    total_sec = max(0, ms // 1000)
    m, s = divmod(total_sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class ControlsBar(ctk.CTkFrame):
    """Bottom playback control bar with timeline scrubber and action buttons."""

    def __init__(
        self,
        master,
        on_play_pause: Callable[[], None],
        on_seek_relative: Callable[[int], None],
        on_seek_position: Callable[[float], None],
        on_skip_90s: Callable[[], None],
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_volume_change: Callable[[int], None],
        on_boost_toggle: Callable[[], None],
        on_speed_change: Callable[[float], None],
        on_toggle_playlist: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="#181818", corner_radius=0, height=88, **kwargs)
        self.on_play_pause = on_play_pause
        self.on_seek_relative = on_seek_relative
        self.on_seek_position = on_seek_position
        self.on_skip_90s = on_skip_90s
        self.on_next = on_next
        self.on_prev = on_prev
        self.on_volume_change = on_volume_change
        self.on_boost_toggle = on_boost_toggle
        self.on_speed_change = on_speed_change
        self.on_toggle_playlist = on_toggle_playlist

        self.is_dragging = False
        self._build_ui()

    def _build_ui(self) -> None:
        # Timeline scrubber row
        self.timeline_row = ctk.CTkFrame(self, fg_color="transparent")
        self.timeline_row.pack(fill="x", padx=14, pady=(6, 2))

        self.time_current = ctk.CTkLabel(self.timeline_row, text="00:00", font=("Segoe UI", 12), text_color="#E0E0E0", width=48)
        self.time_current.pack(side="left")

        self.progress_slider = ctk.CTkSlider(
            self.timeline_row,
            from_=0.0,
            to=1.0,
            number_of_steps=1000,
            progress_color="#FF8C00",
            button_color="#FFA500",
            button_hover_color="#FF7F00",
            command=self._on_slider_moved
        )
        self.progress_slider.set(0.0)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=8)

        self.progress_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_dragging", True))
        self.progress_slider.bind("<ButtonRelease-1>", self._on_slider_released)

        self.time_total = ctk.CTkLabel(self.timeline_row, text="00:00", font=("Segoe UI", 12), text_color="#A0A0A0", width=48)
        self.time_total.pack(side="right")

        # Buttons row
        self.buttons_row = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_row.pack(fill="x", padx=14, pady=(2, 6))

        # Left controls: Volume & Audio Boost
        self.left_box = ctk.CTkFrame(self.buttons_row, fg_color="transparent")
        self.left_box.pack(side="left")

        self.vol_icon = ctk.CTkLabel(self.left_box, text="🔊", font=("Segoe UI", 14), text_color="#E0E0E0")
        self.vol_icon.pack(side="left", padx=(0, 4))

        self.vol_slider = ctk.CTkSlider(
            self.left_box,
            from_=0,
            to=100,
            width=80,
            progress_color="#00ADB5",
            button_color="#00ADB5",
            command=lambda v: self.on_volume_change(int(v))
        )
        self.vol_slider.set(100)
        self.vol_slider.pack(side="left", padx=4)

        self.boost_btn = ctk.CTkButton(
            self.left_box,
            text="Boost 200%",
            width=76,
            height=26,
            font=("Segoe UI", 11, "bold"),
            fg_color="#333333",
            hover_color="#555555",
            command=self._handle_boost_toggle
        )
        self.boost_btn.pack(side="left", padx=4)

        # Center playback controls
        self.center_box = ctk.CTkFrame(self.buttons_row, fg_color="transparent")
        self.center_box.pack(side="left", expand=True)

        self.btn_rewind = ctk.CTkButton(
            self.center_box, text="⟲ 5s", width=46, height=30, fg_color="#2A2A2A", hover_color="#3D3D3D",
            command=lambda: self.on_seek_relative(-5000)
        )
        self.btn_rewind.pack(side="left", padx=3)

        self.btn_prev = ctk.CTkButton(
            self.center_box, text="⏮", width=40, height=30, fg_color="#2A2A2A", hover_color="#3D3D3D",
            command=self.on_prev
        )
        self.btn_prev.pack(side="left", padx=3)

        self.btn_play_pause = ctk.CTkButton(
            self.center_box, text="▶", width=50, height=34, font=("Segoe UI", 16, "bold"),
            fg_color="#FF8C00", hover_color="#FF7F00", text_color="#FFFFFF",
            command=self.on_play_pause
        )
        self.btn_play_pause.pack(side="left", padx=6)

        self.btn_next = ctk.CTkButton(
            self.center_box, text="⏭", width=40, height=30, fg_color="#2A2A2A", hover_color="#3D3D3D",
            command=self.on_next
        )
        self.btn_next.pack(side="left", padx=3)

        self.btn_forward = ctk.CTkButton(
            self.center_box, text="5s ⟳", width=46, height=30, fg_color="#2A2A2A", hover_color="#3D3D3D",
            command=lambda: self.on_seek_relative(5000)
        )
        self.btn_forward.pack(side="left", padx=3)

        # Dedicated Anime OP Skip (+90s) button
        self.btn_skip90 = ctk.CTkButton(
            self.center_box, text="⏭ +90s OP", width=86, height=30, font=("Segoe UI", 12, "bold"),
            fg_color="#8A2BE2", hover_color="#9932CC", text_color="#FFFFFF",
            command=self.on_skip_90s
        )
        self.btn_skip90.pack(side="left", padx=8)

        # Right playback options: Speed & Playlist
        self.right_box = ctk.CTkFrame(self.buttons_row, fg_color="transparent")
        self.right_box.pack(side="right")

        self.speed_menu = ctk.CTkOptionMenu(
            self.right_box,
            values=["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x", "2.5x", "3.0x", "4.0x", "5.0x", "6.0x", "7.0x", "8.0x"],
            width=76,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#2A2A2A",
            button_color="#3D3D3D",
            command=self._on_speed_selected
        )
        self.speed_menu.set("1.0x")
        self.speed_menu.pack(side="left", padx=4)

        self.btn_playlist = ctk.CTkButton(
            self.right_box, text="📑 List", width=60, height=28, fg_color="#2A2A2A", hover_color="#3D3D3D",
            command=self.on_toggle_playlist
        )
        self.btn_playlist.pack(side="left", padx=4)

    def _on_slider_moved(self, value: float) -> None:
        self.is_dragging = True

    def _on_slider_released(self, event) -> None:
        self.is_dragging = False
        val = self.progress_slider.get()
        self.on_seek_position(float(val))

    def _handle_boost_toggle(self) -> None:
        self.on_boost_toggle()

    def set_boost_active(self, active: bool) -> None:
        if active:
            self.boost_btn.configure(fg_color="#E50914", hover_color="#FF2424", text="Boost: ON")
            self.vol_slider.configure(to=200, progress_color="#FF2424", button_color="#FF2424")
        else:
            self.boost_btn.configure(fg_color="#333333", hover_color="#555555", text="Boost 200%")
            self.vol_slider.configure(to=100, progress_color="#00ADB5", button_color="#00ADB5")

    def _on_speed_selected(self, choice: str) -> None:
        try:
            val = float(choice.replace("x", ""))
            self.on_speed_change(val)
        except Exception:
            pass

    def set_speed_display(self, speed: float) -> None:
        """Updates the speed menu label to reflect current speed multiplier."""
        text = f"{speed:g}x"
        self.speed_menu.set(text)

    def update_progress(self, current_ms: int, total_ms: int, is_playing: bool) -> None:
        """Updates progress bar and time labels from player clock."""
        self.btn_play_pause.configure(text="⏸" if is_playing else "▶")
        self.time_current.configure(text=format_time(current_ms))
        self.time_total.configure(text=format_time(total_ms))

        if not self.is_dragging and total_ms > 0:
            fraction = max(0.0, min(1.0, current_ms / total_ms))
            self.progress_slider.set(fraction)
