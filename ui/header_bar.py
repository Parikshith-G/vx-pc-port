"""
Role: Window top bar and video title display.
Responsibility: Displays currently playing filename, aspect ratio switcher, audio/subtitle track selectors.
Details: Provides fullscreen toggle, back-to-library button, and clean VX Player style header.
"""

from typing import Callable, List, Optional, Tuple
import customtkinter as ctk  # type: ignore


class HeaderBar(ctk.CTkFrame):
    """Top bar displaying current media title, track selectors, and window controls."""

    def __init__(
        self,
        master,
        on_back_to_library: Callable[[], None],
        on_cycle_aspect: Callable[[], str],
        on_select_audio: Callable[[], None],
        on_select_sub: Callable[[], None],
        on_toggle_fullscreen: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="#181818", corner_radius=0, height=44, **kwargs)
        self.on_back_to_library = on_back_to_library
        self.on_cycle_aspect = on_cycle_aspect
        self.on_select_audio = on_select_audio
        self.on_select_sub = on_select_sub
        self.on_toggle_fullscreen = on_toggle_fullscreen

        self._build_ui()

    def _build_ui(self) -> None:
        self.btn_back = ctk.CTkButton(
            self, text="← Library", width=75, height=28, font=("Segoe UI", 12),
            fg_color="#2A2A2A", hover_color="#3D3D3D", command=self.on_back_to_library
        )
        self.btn_back.pack(side="left", padx=10, pady=8)

        self.title_label = ctk.CTkLabel(
            self, text="No video playing", font=("Segoe UI", 13, "bold"),
            text_color="#FFFFFF", anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=8)

        self.btn_aspect = ctk.CTkButton(
            self, text="Aspect: Auto", width=90, height=28, font=("Segoe UI", 11),
            fg_color="#2A2A2A", hover_color="#3D3D3D", command=self._handle_aspect
        )
        self.btn_aspect.pack(side="right", padx=6)

        self.btn_sub = ctk.CTkButton(
            self, text="💬 Sub", width=58, height=28, font=("Segoe UI", 11),
            fg_color="#2A2A2A", hover_color="#3D3D3D", command=self.on_select_sub
        )
        self.btn_sub.pack(side="right", padx=4)

        self.btn_audio = ctk.CTkButton(
            self, text="🎧 Audio", width=64, height=28, font=("Segoe UI", 11),
            fg_color="#2A2A2A", hover_color="#3D3D3D", command=self.on_select_audio
        )
        self.btn_audio.pack(side="right", padx=4)

        self.btn_fullscreen = ctk.CTkButton(
            self, text="⛶", width=36, height=28, font=("Segoe UI", 14),
            fg_color="#2A2A2A", hover_color="#3D3D3D", command=self.on_toggle_fullscreen
        )
        self.btn_fullscreen.pack(side="right", padx=(4, 10))

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)

    def _handle_aspect(self) -> None:
        aspect = self.on_cycle_aspect()
        self.btn_aspect.configure(text=f"Aspect: {aspect.capitalize()}")
