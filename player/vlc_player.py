"""
Role: LibVLC media player engine wrapper for high-performance offline playback.
Responsibility: Manages VLC instance, media player, HWND rendering, track switching, speed, and volume.
Details: Binds LibVLC to window HWND, provides 200% audio boost, and handles anime MKV/ASS subtitles.
"""

import os
import sys
from typing import Any, Callable, List, Optional, Tuple


def _init_vlc_dll_path() -> None:
    """Ensures libvlc.dll can be loaded on Windows platforms."""
    candidates = [
        getattr(sys, "_MEIPASS", ""),
        os.path.join(getattr(sys, "_MEIPASS", ""), "vlc"),
        os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else "",
        os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else "", "vlc"),
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC"
    ]
    for path in candidates:
        if path and os.path.isdir(path) and os.path.isfile(os.path.join(path, "libvlc.dll")):
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(path)
                except Exception:
                    pass
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            break


_init_vlc_dll_path()
import vlc  # type: ignore


class VlcPlayer:
    """Encapsulates LibVLC player state, events, and controls."""

    def __init__(self, hwnd: Optional[int] = None):
        # Clean VLC parameters: suppress verbose logs, disable title OSD, and allow mouse passthrough
        vlc_args = ["--no-video-title-show", "--quiet", "--no-mouse-events"]
        try:
            self.instance = vlc.Instance(vlc_args)
            if self.instance is None:
                self.instance = vlc.Instance()
        except Exception:
            self.instance = vlc.Instance()

        if self.instance is None:
            raise RuntimeError("Could not initialize LibVLC engine. Please verify VLC installation.")

        self.player = self.instance.media_player_new()
        self.current_file: Optional[str] = None
        self.boost_enabled: bool = False
        self.base_volume: int = 100
        self.current_speed: float = 1.0
        self.aspect_ratios = ["default", "16:9", "4:3", "16:10", "21:9"]
        self.current_aspect_idx: int = 0

        if hwnd is not None:
            self.set_hwnd(hwnd)

    def set_hwnd(self, hwnd: int) -> None:
        """Binds VLC video output to the specified Windows window handle."""
        if sys.platform.startswith("win"):
            self.player.set_hwnd(hwnd)
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(hwnd)
        elif sys.platform.startswith("darwin"):
            self.player.set_nsobject(hwnd)

    def load_and_play(self, filepath: str, start_time_ms: int = 0) -> bool:
        """Loads media file and starts playback, optionally seeking to start time."""
        if not os.path.isfile(filepath):
            return False

        self.current_file = filepath
        media = self.instance.media_new(filepath)
        self.player.set_media(media)
        self.player.play()

        if start_time_ms > 0 or self.current_speed != 1.0:
            # Short deferred seek and speed application after playback begins
            def delayed_setup():
                import time
                time.sleep(0.15)
                if start_time_ms > 0:
                    self.player.set_time(start_time_ms)
                if self.current_speed != 1.0:
                    self.player.set_rate(self.current_speed)
            import threading
            threading.Thread(target=delayed_setup, daemon=True).start()

        return True

    def play(self) -> None:
        self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def toggle_play_pause(self) -> bool:
        """Toggles play/pause state and returns new playing status."""
        if self.is_playing():
            self.player.pause()
            return False
        else:
            self.player.play()
            return True

    def stop(self) -> None:
        self.player.stop()

    def is_playing(self) -> bool:
        return bool(self.player.is_playing())

    def get_time(self) -> int:
        """Returns current playback position in milliseconds."""
        t = self.player.get_time()
        return max(0, t)

    def get_length(self) -> int:
        """Returns total media duration in milliseconds."""
        length = self.player.get_length()
        return max(0, length)

    def get_position(self) -> float:
        """Returns playback fraction between 0.0 and 1.0."""
        pos = self.player.get_position()
        return max(0.0, min(1.0, float(pos)))

    def seek_to_position(self, fraction: float) -> None:
        """Seeks to relative fractional position (0.0 to 1.0)."""
        clamped = max(0.0, min(1.0, float(fraction)))
        self.player.set_position(clamped)

    def seek_to_time(self, time_ms: int) -> None:
        """Seeks directly to given millisecond position."""
        target = max(0, min(self.get_length(), time_ms))
        self.player.set_time(target)

    def seek_delta(self, delta_ms: int) -> int:
        """Seeks forward or backward by delta_ms and returns new position."""
        curr = self.get_time()
        total = self.get_length()
        new_time = max(0, curr + delta_ms)
        if total > 0:
            new_time = min(total, new_time)
        self.player.set_time(new_time)
        return new_time

    def skip_90s_op(self) -> int:
        """Fast-forwards exactly 90 seconds (standard anime opening duration)."""
        return self.seek_delta(90 * 1000)

    def rewind_5s(self) -> int:
        """Rewinds exactly 5 seconds."""
        return self.seek_delta(-5 * 1000)

    def forward_5s(self) -> int:
        """Fast-forwards exactly 5 seconds."""
        return self.seek_delta(5 * 1000)

    def set_volume(self, volume: int) -> int:
        """Sets volume with support for up to 200% audio boost."""
        max_vol = 200 if self.boost_enabled else 100
        vol = max(0, min(max_vol, volume))
        self.base_volume = vol
        self.player.audio_set_volume(vol)
        return vol

    def get_volume(self) -> int:
        vol = self.player.audio_get_volume()
        return vol if vol >= 0 else self.base_volume

    def toggle_audio_boost(self) -> bool:
        """Toggles audio boost mode (enabling volume up to 200%)."""
        self.boost_enabled = not self.boost_enabled
        if not self.boost_enabled and self.base_volume > 100:
            self.set_volume(100)
        return self.boost_enabled

    def set_speed(self, speed: float) -> None:
        """Sets playback speed multiplier (0.1x to 8.0x)."""
        rate = max(0.1, min(8.0, float(speed)))
        self.current_speed = rate
        self.player.set_rate(rate)

    def get_speed(self) -> float:
        try:
            rate = float(self.player.get_rate())
            if rate > 0.05:
                self.current_speed = rate
                return rate
        except Exception:
            pass
        return getattr(self, "current_speed", 1.0)

    def cycle_aspect_ratio(self) -> str:
        """Cycles through aspect ratios: default, 16:9, 4:3, 16:10, 21:9."""
        self.current_aspect_idx = (self.current_aspect_idx + 1) % len(self.aspect_ratios)
        aspect = self.aspect_ratios[self.current_aspect_idx]
        if aspect == "default":
            self.player.video_set_aspect_ratio(None)
        else:
            self.player.video_set_aspect_ratio(aspect)
        return aspect

    def get_audio_tracks(self) -> List[Tuple[int, str]]:
        """Returns list of available audio tracks as (track_id, name) tuples."""
        tracks = self.player.audio_get_track_description() or []
        return [(t[0], t[1].decode("utf-8") if isinstance(t[1], bytes) else str(t[1])) for t in tracks]

    def set_audio_track(self, track_id: int) -> None:
        self.player.audio_set_track(track_id)

    def get_subtitle_tracks(self) -> List[Tuple[int, str]]:
        """Returns list of available subtitle tracks as (sub_id, name) tuples."""
        tracks = self.player.video_get_spu_description() or []
        return [(t[0], t[1].decode("utf-8") if isinstance(t[1], bytes) else str(t[1])) for t in tracks]

    def set_subtitle_track(self, sub_id: int) -> None:
        self.player.video_set_spu(sub_id)
