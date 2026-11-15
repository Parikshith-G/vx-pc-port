"""
Role: Window top bar and video title display.
Responsibility: Displays currently playing filename, aspect ratio switcher, audio/subtitle track selectors.
Details: Provides fullscreen toggle, back-to-library button, voice clarity, sleep timer, and persistent speed indicator.
"""

from typing import Callable, List, Optional, Tuple
import customtkinter as ctk  # type: ignore


class HeaderBar(ctk.CTkFrame):
    """Top bar displaying current media title, track selectors, voice clarity, and window controls."""

    def __init__(
        self,
        master,
        on_back_to_library: Callable[[], None],
        on_cycle_aspect: Callable[[], str],
        on_select_audio: Callable[[], None],
        on_select_sub: Callable[[], None],
        on_toggle_fullscreen: Callable[[], None],
        on_toggle_voice_clarity: Optional[Callable[[], None]] = None,
        on_sleep_timer: Optional[Callable[[], None]] = None,
        on_toggle_seen: Optional[Callable[[], None]] = None,
        on_generate_ai_sub: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="#10131A", corner_radius=0, height=44, **kwargs)
        self.on_back_to_library = on_back_to_library
        self.on_cycle_aspect = on_cycle_aspect
        self.on_select_audio = on_select_audio
        self.on_select_sub = on_select_sub
        self.on_toggle_fullscreen = on_toggle_fullscreen
        self.on_toggle_voice_clarity = on_toggle_voice_clarity or (lambda: None)
        self.on_sleep_timer = on_sleep_timer or (lambda: None)
        self.on_toggle_seen = on_toggle_seen or (lambda: None)
        self.on_generate_ai_sub = on_generate_ai_sub or (lambda: None)

        self._build_ui()

    def _build_ui(self) -> None:
        # Back to library button with clean arrow
        self.btn_back = ctk.CTkButton(
            self, text="‹ Library", width=80, height=28, font=("Segoe UI", 12, "bold"),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self.on_back_to_library
        )
        self.btn_back.pack(side="left", padx=8, pady=8)

        # Persistent speed status badge (matches mobile persistent speed header)
        self.speed_badge = ctk.CTkLabel(
            self, text="1.0x", font=("Segoe UI", 11, "bold"),
            text_color="#0099FF", fg_color="#162032", corner_radius=6,
            width=50, height=24
        )
        self.speed_badge.pack(side="left", padx=(0, 8))

        # Media title label
        self.title_label = ctk.CTkLabel(
            self, text="No video playing", font=("Segoe UI", 12, "bold"),
            text_color="#FFFFFF", anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=4)

        # Right side action buttons
        # 1. Fullscreen toggle
        self.btn_fullscreen = ctk.CTkButton(
            self, text="🗖", width=36, height=28, font=("Segoe UI", 13, "bold"),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self.on_toggle_fullscreen
        )
        self.btn_fullscreen.pack(side="right", padx=(4, 10))

        # 2. Aspect ratio
        self.btn_aspect = ctk.CTkButton(
            self, text="⛶ Fit", width=68, height=28, font=("Segoe UI", 11),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self._handle_aspect
        )
        self.btn_aspect.pack(side="right", padx=4)

        # 3. Voice Clarity / ClearVoice toggle button
        self.btn_voice_clarity = ctk.CTkButton(
            self, text="🎙 ClearVoice", width=95, height=28, font=("Segoe UI", 11, "bold"),
            fg_color="#181C26", hover_color="#242B3B", text_color="#8A92A6",
            command=self.on_toggle_voice_clarity
        )
        self.btn_voice_clarity.pack(side="right", padx=4)

        # 4. Sleep Timer
        self.btn_sleep = ctk.CTkButton(
            self, text="🌙", width=36, height=28, font=("Segoe UI", 12),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self.on_sleep_timer
        )
        self.btn_sleep.pack(side="right", padx=4)

        # 5. Mark Seen Toggle
        self.btn_seen = ctk.CTkButton(
            self, text="✓ Seen", width=64, height=28, font=("Segoe UI", 11, "bold"),
            fg_color="#181C26", hover_color="#242B3B", text_color="#8A92A6",
            command=self.on_toggle_seen
        )
        self.btn_seen.pack(side="right", padx=4)

        # 6. Audio Tracks
        self.btn_audio = ctk.CTkButton(
            self, text="🎵 Audio", width=68, height=28, font=("Segoe UI", 11),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self.on_select_audio
        )
        self.btn_audio.pack(side="right", padx=4)

        # 7. Subtitles
        self.btn_sub = ctk.CTkButton(
            self, text="💬 Subs", width=64, height=28, font=("Segoe UI", 11),
            fg_color="#181C26", hover_color="#242B3B", text_color="#E0E6ED",
            command=self.on_select_sub
        )
        self.btn_sub.pack(side="right", padx=4)

        # 8. AI Subtitles
        self.btn_ai_sub = ctk.CTkButton(
            self, text="⚡ AI Sub", width=68, height=28, font=("Segoe UI", 11, "bold"),
            fg_color="#0066CC", hover_color="#0080FF", text_color="#FFFFFF",
            command=self.on_generate_ai_sub
        )
        self.btn_ai_sub.pack(side="right", padx=4)

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)

    def set_speed_badge(self, speed: float, is_holding: bool = False) -> None:
        """Updates persistent top-left speed status indicator."""
        if is_holding:
            self.speed_badge.configure(text=f"⚡ {speed:g}x", text_color="#38BDF8", fg_color="#0E2838")
        elif abs(speed - 1.0) > 0.05:
            self.speed_badge.configure(text=f"{speed:g}x", text_color="#0099FF", fg_color="#162032")
        else:
            self.speed_badge.configure(text="1.0x", text_color="#8A92A6", fg_color="#181C26")

    def set_voice_clarity_state(self, active: bool) -> None:
        if active:
            self.btn_voice_clarity.configure(
                text="🎙 ClearVoice: ON", fg_color="#0077CC", hover_color="#0099FF", text_color="#FFFFFF"
            )
        else:
            self.btn_voice_clarity.configure(
                text="🎙 ClearVoice", fg_color="#181C26", hover_color="#242B3B", text_color="#8A92A6"
            )

    def set_seen_state(self, is_seen: bool) -> None:
        if is_seen:
            self.btn_seen.configure(
                text="✓ Seen", fg_color="#0D3820", hover_color="#13522F", text_color="#00E676"
            )
        else:
            self.btn_seen.configure(
                text="○ Seen", fg_color="#181C26", hover_color="#242B3B", text_color="#8A92A6"
            )

    def _handle_aspect(self) -> None:
        aspect = self.on_cycle_aspect()
        self.btn_aspect.configure(text=f"⛶ {aspect.capitalize()}")

