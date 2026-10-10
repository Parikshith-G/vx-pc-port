"""
Role: Application bootstrap and desktop media player coordinator.
Responsibility: Integrates LibVLC engine, CustomTkinter UI, shortcuts, auto-hiding HUD, and watch history.
Details: Provides VX Player experience on PC with speed shortcuts (E/W/A/D/S), OP skip, audio boost, and overlay controls.
"""

import os
import sys
import time
import tkinter as tk
from typing import List, Optional, Tuple
import customtkinter as ctk  # type: ignore

from core.history_manager import HistoryManager
from core.natural_sort import sort_filepaths
from player.vlc_player import VlcPlayer
from ui.controls_bar import ControlsBar
from ui.header_bar import HeaderBar
from ui.library_view import LibraryView
from ui.osd import OsdNotification
from ui.playlist_panel import PlaylistPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class VxPlayerApp(ctk.CTk):
    """Main desktop application window managing views, VLC rendering, and shortcuts."""

    def __init__(self):
        super().__init__()
        self.title("VX Player PC (Offline)")
        self.geometry("1120x720")
        self.minsize(800, 500)
        self.configure(fg_color="#0D0D0D")

        self.history = HistoryManager()
        self.player = VlcPlayer()
        self.osd = OsdNotification(self)

        self.playlist: List[str] = []
        self.current_index: int = -1
        self.is_fullscreen: bool = False
        self.playlist_visible: bool = False

        # Inactivity auto-hide state
        self.controls_visible: bool = True
        self._hide_controls_timer: Optional[str] = None
        self._last_pointer_pos: Tuple[int, int] = (0, 0)
        self._last_activity_time: float = time.time()

        # Hold-to-boost state (preset target configurable via W/Q, applied via A)
        self.hold_speed_target: float = 2.0
        self._is_holding_speed: bool = False
        self._saved_speed: float = 1.0
        self._hold_release_timer: Optional[str] = None

        self._build_ui()
        self._bind_shortcuts()
        self._start_progress_loop()

        # If CLI file argument was provided, launch it directly; otherwise show mobile-style discovery library
        if len(sys.argv) > 1:
            arg_path = os.path.normpath(sys.argv[1])
            if os.path.isfile(arg_path):
                folder = os.path.dirname(arg_path)
                self.library_view.load_folder(folder, play_target=arg_path)
            elif os.path.isdir(arg_path):
                self.library_view.load_folder(arg_path)

    def _build_ui(self) -> None:
        self.container = ctk.CTkFrame(self, fg_color="#0D0D0D", corner_radius=0)
        self.container.pack(fill="both", expand=True)

        # 1. Library View
        self.library_view = LibraryView(
            self.container,
            on_play_video=self.start_playback,
            get_resume_pos=self.history.get_resume_position,
            is_seen_checker=self.history.is_seen,
            recent_folders_getter=lambda: self.history.data.get("recent_folders", []),
            on_folder_selected=self.history.add_recent_folder
        )
        self.library_view.pack(fill="both", expand=True)

        # 2. Player View Container (hidden initially)
        self.player_frame = ctk.CTkFrame(self.container, fg_color="#000000", corner_radius=0)

        # Native video rendering container: fills 100% of player_frame so video never resizes
        self.video_center = ctk.CTkFrame(self.player_frame, fg_color="#000000", corner_radius=0)
        self.video_center.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

        # Native video rendering canvas for VLC HWND
        self.video_canvas = tk.Canvas(self.video_center, bg="black", highlightthickness=0)
        self.video_canvas.pack(side="left", fill="both", expand=True)
        self.video_canvas.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.video_canvas.bind("<Button-1>", lambda e: self.player.toggle_play_pause())

        # In-player playlist sidebar (overlaid on the right side)
        self.playlist_panel = PlaylistPanel(
            self.player_frame,
            on_video_selected=self._play_from_playlist,
            is_seen_checker=self.history.is_seen,
            on_close=self.toggle_playlist
        )

        # Overlaid Header bar (top overlay, height 44)
        self.header = HeaderBar(
            self.player_frame,
            on_back_to_library=self.stop_and_show_library,
            on_cycle_aspect=self.player.cycle_aspect_ratio,
            on_select_audio=self._show_audio_dialog,
            on_select_sub=self._show_subtitle_dialog,
            on_toggle_fullscreen=self.toggle_fullscreen
        )
        self.header.place(relx=0, rely=0, relwidth=1.0, anchor="nw")
        self.header.lift()

        # Overlaid Controls bar (bottom overlay, height 88)
        self.controls = ControlsBar(
            self.player_frame,
            on_play_pause=self.player.toggle_play_pause,
            on_seek_relative=self.player.seek_delta,
            on_seek_position=self.player.seek_to_position,
            on_skip_90s=self.skip_90s_anime_op,
            on_next=self.play_next,
            on_prev=self.play_prev,
            on_volume_change=self.player.set_volume,
            on_boost_toggle=self._toggle_audio_boost,
            on_speed_change=self._on_speed_menu_changed,
            on_toggle_playlist=self.toggle_playlist
        )
        self.controls.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self.controls.lift()

    def _bind_shortcuts(self) -> None:
        self.bind("<space>", lambda e: self.player.toggle_play_pause())
        self.bind("<Right>", lambda e: (self.player.seek_delta(5000), self.osd.show("5s ⟳")))
        self.bind("<Left>", lambda e: (self.player.seek_delta(-5000), self.osd.show("⟲ 5s")))
        self.bind("<Up>", lambda e: self._volume_up())
        self.bind("<Down>", lambda e: self._volume_down())

        # Speed hold target adjustment (W for decrease, E for increase) - changes preset without immediately applying
        self.bind("<e>", lambda e: self.increase_hold_speed_target())
        self.bind("<E>", lambda e: self.increase_hold_speed_target())
        self.bind("<w>", lambda e: self.decrease_hold_speed_target())
        self.bind("<W>", lambda e: self.decrease_hold_speed_target())

        # Immediate playback speed adjustment (D/S)
        self.bind("<d>", lambda e: self.speed_up())
        self.bind("<D>", lambda e: self.speed_up())
        self.bind("<s>", lambda e: self.speed_down())
        self.bind("<S>", lambda e: self.speed_down())

        # Speed Hold (A) - applies target speed while held down, smoothly restores on release
        self.bind("<KeyPress-a>", lambda e: self.on_speed_hold_press())
        self.bind("<KeyPress-A>", lambda e: self.on_speed_hold_press())
        self.bind("<KeyRelease-a>", lambda e: self.on_speed_hold_release())
        self.bind("<KeyRelease-A>", lambda e: self.on_speed_hold_release())

        # OP Skip shortcut (O only)
        self.bind("<o>", lambda e: self.skip_90s_anime_op())
        self.bind("<O>", lambda e: self.skip_90s_anime_op())

        # Navigation & window shortcuts
        self.bind("<n>", lambda e: self.play_next())
        self.bind("<N>", lambda e: self.play_next())
        self.bind("<p>", lambda e: self.play_prev())
        self.bind("<P>", lambda e: self.play_prev())
        self.bind("<f>", lambda e: self.toggle_fullscreen())
        self.bind("<F>", lambda e: self.toggle_fullscreen())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<l>", lambda e: self.toggle_playlist())
        self.bind("<L>", lambda e: self.toggle_playlist())
        self.bind("<Escape>", lambda e: self.exit_fullscreen())

        # Global activity tracking for auto-hide (mouse movement/click reveals HUD; shortcuts keep it clean)
        self.bind_all("<Motion>", self._on_user_activity)
        self.bind_all("<ButtonPress>", self._on_user_activity)

    def _volume_up(self) -> None:
        new_vol = self.player.set_volume(self.player.get_volume() + 5)
        self.controls.vol_slider.set(new_vol)
        self.osd.show(f"Volume: {new_vol}%")

    def _volume_down(self) -> None:
        new_vol = self.player.set_volume(self.player.get_volume() - 5)
        self.controls.vol_slider.set(new_vol)
        self.osd.show(f"Volume: {new_vol}%")

    def increase_hold_speed_target(self) -> None:
        """Increases hold speed target by +0.1x (Shortcut: E, up to 8.0x, applied on holding 'A')."""
        self.hold_speed_target = min(8.0, round(self.hold_speed_target + 0.1, 2))
        self.osd.show(f"Hold Speed Target: {self.hold_speed_target:g}x")
        if self._is_holding_speed:
            self.player.set_speed(self.hold_speed_target)
            self.controls.set_speed_display(self.hold_speed_target)
        if self.controls_visible and self.player.is_playing() and not self.playlist_visible:
            self.hide_controls(force=True)

    def decrease_hold_speed_target(self) -> None:
        """Decreases hold speed target by -0.1x (Shortcut: W, down to 0.1x, applied on holding 'A')."""
        self.hold_speed_target = max(0.1, round(self.hold_speed_target - 0.1, 2))
        self.osd.show(f"Hold Speed Target: {self.hold_speed_target:g}x")
        if self._is_holding_speed:
            self.player.set_speed(self.hold_speed_target)
            self.controls.set_speed_display(self.hold_speed_target)
        if self.controls_visible and self.player.is_playing() and not self.playlist_visible:
            self.hide_controls(force=True)

    def speed_up(self) -> None:
        """Increases immediate playback speed by +0.1x (Shortcut: D, up to 8.0x)."""
        curr = round(self.player.get_speed(), 2)
        new_speed = min(8.0, round(curr + 0.1, 2))
        self.player.set_speed(new_speed)
        self.controls.set_speed_display(new_speed)
        self.osd.show(f"Speed: {new_speed:g}x")
        if not self._is_holding_speed:
            self._saved_speed = new_speed
        if self.controls_visible and self.player.is_playing() and not self.playlist_visible:
            self.hide_controls(force=True)

    def speed_down(self) -> None:
        """Decreases immediate playback speed by -0.1x (Shortcut: S, down to 0.1x)."""
        curr = round(self.player.get_speed(), 2)
        new_speed = max(0.1, round(curr - 0.1, 2))
        self.player.set_speed(new_speed)
        self.controls.set_speed_display(new_speed)
        self.osd.show(f"Speed: {new_speed:g}x")
        if not self._is_holding_speed:
            self._saved_speed = new_speed
        if self.controls_visible and self.player.is_playing() and not self.playlist_visible:
            self.hide_controls(force=True)

    def _on_speed_menu_changed(self, speed: float) -> None:
        """Updates playback speed when selected from controls dropdown."""
        self.player.set_speed(speed)
        self.controls.set_speed_display(speed)
        if not self._is_holding_speed:
            self._saved_speed = speed
        self.osd.show(f"Speed: {speed:g}x")

    def on_speed_hold_press(self, event=None) -> None:
        """Temporarily applies hold speed target while holding 'A' key (up to 8.0x)."""
        if self._hold_release_timer:
            self.after_cancel(self._hold_release_timer)
            self._hold_release_timer = None

        if not self._is_holding_speed:
            self._is_holding_speed = True
            self._saved_speed = self.player.get_speed()
            target = self.hold_speed_target
            self.player.set_speed(target)
            self.controls.set_speed_display(target)
            self.osd.show(f"Fast Forward {target:g}x »»", duration_ms=0)
            if self.controls_visible and self.player.is_playing() and not self.playlist_visible:
                self.hide_controls(force=True)

    def on_speed_hold_release(self, event=None) -> None:
        """Restores speed when releasing 'A' key (debounced for Windows key-repeat)."""
        if self._hold_release_timer:
            self.after_cancel(self._hold_release_timer)
        self._hold_release_timer = self.after(80, self._do_end_speed_hold)

    def _do_end_speed_hold(self) -> None:
        self._hold_release_timer = None
        if self._is_holding_speed:
            self._is_holding_speed = False
            restored = getattr(self, "_saved_speed", 1.0)
            self.player.set_speed(restored)
            self.controls.set_speed_display(restored)
            self.osd.show(f"{restored:g}x", duration_ms=1000)

    # -------------------------------------------------------------------------
    # Auto-Hide Controls on Mouse Inactivity
    # -------------------------------------------------------------------------

    def _is_pointer_inside_window(self) -> bool:
        try:
            x, y = self.winfo_pointerxy()
            wx, wy = self.winfo_rootx(), self.winfo_rooty()
            ww, wh = self.winfo_width(), self.winfo_height()
            return (wx <= x <= wx + ww) and (wy <= y <= wy + wh)
        except Exception:
            return True

    def _is_pointer_over_controls(self) -> bool:
        try:
            if not self.controls_visible:
                return False
            mx, my = self.winfo_pointerxy()
            if self.header.winfo_ismapped():
                hy = self.header.winfo_rooty()
                hh = self.header.winfo_height()
                hx = self.header.winfo_rootx()
                hw = self.header.winfo_width()
                if (hx <= mx <= hx + hw) and (hy <= my <= hy + hh):
                    return True
            if self.controls.winfo_ismapped():
                cy = self.controls.winfo_rooty()
                ch = self.controls.winfo_height()
                cx = self.controls.winfo_rootx()
                cw = self.controls.winfo_width()
                if (cx <= mx <= cx + cw) and (cy <= my <= cy + ch):
                    return True
        except Exception:
            pass
        return False

    def hide_controls(self, force: bool = False) -> None:
        """Hides header, bottom controls, and mouse cursor during inactive playback."""
        if not self.controls_visible:
            return
        if not self.player_frame.winfo_ismapped():
            return
        if not self.player.current_file:
            return
        if not force and (self.playlist_visible or self.controls.is_dragging):
            return
        if not force and self._is_pointer_over_controls():
            return

        self.header.place_forget()
        self.controls.place_forget()
        self.config(cursor="none")
        self.video_canvas.config(cursor="none")
        self.controls_visible = False
        if self._hide_controls_timer:
            self.after_cancel(self._hide_controls_timer)
            self._hide_controls_timer = None

    def show_controls(self, reset_timer: bool = True) -> None:
        """Reveals header, controls, and mouse cursor overlaid on the video without resizing."""
        if not self.controls_visible:
            self.header.place(relx=0, rely=0, relwidth=1.0, anchor="nw")
            self.header.lift()
            self.controls.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
            self.controls.lift()
            if self.playlist_visible:
                self.playlist_panel.lift()
            self.config(cursor="")
            self.video_canvas.config(cursor="")
            self.controls_visible = True

        if self._hide_controls_timer:
            self.after_cancel(self._hide_controls_timer)
            self._hide_controls_timer = None

        if reset_timer and self.player.is_playing() and not self.controls.is_dragging and not self.playlist_visible:
            self._hide_controls_timer = self.after(2500, self.hide_controls)

    def _on_user_activity(self, event=None) -> None:
        """Called on mouse movement, click, or key press."""
        self._last_activity_time = time.time()
        if self.player_frame.winfo_ismapped():
            self.show_controls(reset_timer=True)

    # -------------------------------------------------------------------------
    # Playback Lifecycle
    # -------------------------------------------------------------------------

    def start_playback(self, filepath: str, video_list: List[str]) -> None:
        self.playlist = sort_filepaths(video_list)
        try:
            self.current_index = self.playlist.index(filepath)
        except ValueError:
            self.current_index = 0

        self.library_view.pack_forget()
        self.player_frame.pack(fill="both", expand=True)
        self.show_controls(reset_timer=True)
        self.update_idletasks()

        # Bind VLC to video canvas HWND
        hwnd = self.video_canvas.winfo_id()
        self.player.set_hwnd(hwnd)

        # Check resume position (> 3s)
        resume_ms = self.history.get_resume_position(filepath)
        self.player.load_and_play(filepath, start_time_ms=resume_ms)

        self.header.set_title(os.path.basename(filepath))
        self.playlist_panel.set_playlist(self.playlist, current=filepath)

    def _play_from_playlist(self, filepath: str) -> None:
        self._save_current_position()
        self.start_playback(filepath, self.playlist)

    def play_next(self) -> None:
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self._save_current_position()
            self.current_index += 1
            next_vid = self.playlist[self.current_index]
            self.start_playback(next_vid, self.playlist)

    def play_prev(self) -> None:
        if self.player.get_time() > 3500:
            self.player.seek_to_time(0)
        elif self.playlist and self.current_index > 0:
            self._save_current_position()
            self.current_index -= 1
            prev_vid = self.playlist[self.current_index]
            self.start_playback(prev_vid, self.playlist)

    def skip_90s_anime_op(self) -> None:
        """Fast-forwards exactly 90 seconds (anime opening skip)."""
        self.player.skip_90s_op()
        self.osd.show("⏭ +90s OP")

    def _toggle_audio_boost(self) -> None:
        active = self.player.toggle_audio_boost()
        self.controls.set_boost_active(active)
        self.osd.show(f"Audio Boost: {'ON (200%)' if active else 'OFF'}")

    def toggle_playlist(self) -> None:
        if self.playlist_visible:
            self.playlist_panel.place_forget()
            self.playlist_visible = False
            self.show_controls(reset_timer=True)
        else:
            self.playlist_panel.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
            self.playlist_panel.lift()
            self.playlist_visible = True
            self.show_controls(reset_timer=False)

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        self.show_controls(reset_timer=True)

    def exit_fullscreen(self) -> None:
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            self.show_controls(reset_timer=True)

    def stop_and_show_library(self) -> None:
        self._save_current_position()
        self.player.stop()
        if self._hide_controls_timer:
            self.after_cancel(self._hide_controls_timer)
            self._hide_controls_timer = None
        if self.playlist_visible:
            self.playlist_panel.place_forget()
            self.playlist_visible = False
        self.show_controls(reset_timer=False)
        self.config(cursor="")
        self.osd.hide()
        self.player_frame.pack_forget()
        self.library_view.pack(fill="both", expand=True)
        self.library_view._render_list()

    def _save_current_position(self) -> None:
        if self.player.current_file:
            curr = self.player.get_time()
            total = self.player.get_length()
            self.history.save_position(self.player.current_file, curr, total)

    def _start_progress_loop(self) -> None:
        curr = self.player.get_time()
        total = self.player.get_length()
        is_playing = self.player.is_playing()

        self.controls.update_progress(curr, total, is_playing)

        # Inactivity auto-hide check
        if self.player_frame.winfo_ismapped():
            try:
                cur_pos = self.winfo_pointerxy()
                if cur_pos != self._last_pointer_pos:
                    if self._is_pointer_inside_window():
                        self._last_pointer_pos = cur_pos
                        self._on_user_activity()
                else:
                    if self.controls_visible and is_playing:
                        if (time.time() - self._last_activity_time) >= 2.5:
                            self.hide_controls()
            except Exception:
                pass

        # Check if playback ended
        import vlc  # type: ignore
        if self.player.player.get_state() == vlc.State.Ended:
            self.play_next()
        elif is_playing:
            self._save_current_position()

        self.after(200, self._start_progress_loop)

    def _show_audio_dialog(self) -> None:
        tracks = self.player.get_audio_tracks()
        if not tracks:
            return
        self._show_track_menu("Audio Tracks", tracks, self.player.set_audio_track)

    def _show_subtitle_dialog(self) -> None:
        tracks = self.player.get_subtitle_tracks()
        if not tracks:
            return
        self._show_track_menu("Subtitle Tracks", tracks, self.player.set_subtitle_track)

    def _show_track_menu(self, title: str, tracks, on_select) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("320x280")
        dialog.attributes("-topmost", True)
        ctk.CTkLabel(dialog, text=title, font=("Segoe UI", 13, "bold")).pack(pady=8)
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=8, pady=4)
        for tid, name in tracks:
            ctk.CTkButton(
                scroll, text=name, anchor="w", fg_color="#282828", hover_color="#383838",
                command=lambda t=tid: (on_select(t), dialog.destroy())
            ).pack(fill="x", pady=2)


# Backward compatibility alias
MxPlayerApp = VxPlayerApp


if __name__ == "__main__":
    app = VxPlayerApp()
    app.mainloop()
