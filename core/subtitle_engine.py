"""
Role: Desktop offline AI subtitle generation coordinator and speech-to-text pipeline.
Responsibility: Extracts 16kHz audio from videos via VLC, runs whisper-cli.exe, and writes .srt files.
Details: Supports auto-language detection, English translation (Kannada, etc.), multi-threading (8 threads),
and real-time progress callbacks without blocking the UI.
"""

import os
import re
import shutil
import subprocess
import threading
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple


WHISPER_MODELS: Dict[str, Dict[str, str]] = {
    "small": {
        "name": "ggml-small.bin",
        "size": "~466 MB",
        "desc": "Recommended for Kannada / Indian languages & translation",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
    },
    "base": {
        "name": "ggml-base.bin",
        "size": "~140 MB",
        "desc": "Balanced speed and accuracy",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
    },
    "tiny": {
        "name": "ggml-tiny.bin",
        "size": "~75 MB",
        "desc": "Fastest, lowest memory usage",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
    }
}


class SubtitleEngine:
    """Manages offline speech-to-text processing for VX Player PC."""

    def __init__(self, base_dir: Optional[str] = None):
        if not base_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir

        self.bin_dir = os.path.join(self.base_dir, "bin")
        self.whisper_exe = os.path.join(self.bin_dir, "whisper-cli.exe")

        user_home = os.path.expanduser("~")
        self.models_dir = os.path.join(user_home, ".vx_player_desktop", "models")
        os.makedirs(self.models_dir, exist_ok=True)

        self.tmp_dir = os.path.join(user_home, ".vx_player_desktop", "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.vlc_exe = self._locate_vlc()
        self.active_process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def _locate_vlc(self) -> Optional[str]:
        """Locates VLC executable for high-performance audio extraction."""
        candidates = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            shutil.which("vlc")
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def is_engine_ready(self) -> bool:
        """Returns True if whisper-cli executable and VLC are available."""
        return os.path.isfile(self.whisper_exe) and (self.vlc_exe is not None)

    def get_available_models(self) -> List[Tuple[str, str, str]]:
        """Returns list of (model_key, filename, absolute_path) for models found locally."""
        found = []
        for key, info in WHISPER_MODELS.items():
            path = os.path.join(self.models_dir, info["name"])
            if os.path.isfile(path) and os.path.getsize(path) > 10_000_000:
                found.append((key, info["name"], path))
        # Also check for any custom ggml-*.bin files in models_dir
        for fname in os.listdir(self.models_dir):
            if fname.endswith(".bin") and fname not in [m[1] for m in found]:
                fpath = os.path.join(self.models_dir, fname)
                found.append(("custom", fname, fpath))
        return found

    def download_model(
        self,
        model_key: str,
        on_progress: Callable[[float, str], None],
        is_cancelled: Callable[[], bool] = lambda: False
    ) -> Optional[str]:
        """Downloads a GGML model from Hugging Face with progress reporting."""
        info = WHISPER_MODELS.get(model_key)
        if not info:
            return None

        target_path = os.path.join(self.models_dir, info["name"])
        temp_path = target_path + ".part"

        try:
            req = urllib.request.Request(info["url"], headers={"User-Agent": "VXPlayerDesktop"})
            with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as out_file:
                total_bytes = int(resp.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB chunks

                while True:
                    if is_cancelled():
                        out_file.close()
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        return None

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)

                    if total_bytes > 0:
                        pct = downloaded / total_bytes
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_bytes / (1024 * 1024)
                        on_progress(pct, f"Downloading {info['name']}: {mb_done:.1f} MB / {mb_total:.1f} MB ({int(pct * 100)}%)")
                    else:
                        on_progress(0.5, f"Downloading {info['name']}...")

            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(temp_path, target_path)
            return target_path
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise e

    def extract_audio(
        self,
        video_path: str,
        output_wav: str,
        on_status: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Extracts 16kHz 16-bit mono WAV audio from any video format using VLC."""
        if not self.vlc_exe:
            raise RuntimeError("VLC executable not found for audio extraction.")

        if on_status:
            on_status("Extracting 16kHz audio via VLC...")

        if os.path.exists(output_wav):
            try:
                os.remove(output_wav)
            except Exception:
                pass

        # VLC transcode command for 16kHz mono 16-bit audio
        sout_arg = f":sout=#transcode{{acodec=s16l,channels=1,samplerate=16000}}:std{{access=file,mux=wav,dst={output_wav}}}"
        cmd = [
            self.vlc_exe,
            "-I", "dummy",
            "--no-video",
            "--no-sub-autodetect-file",
            video_path,
            sout_arg,
            "vlc://quit"
        ]

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

        self.active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )
        self.active_process.wait()
        self.active_process = None

        return os.path.isfile(output_wav) and os.path.getsize(output_wav) > 1000

    def generate_subtitles(
        self,
        video_path: str,
        model_path: str,
        translate_to_english: bool = True,
        num_threads: int = 8,
        on_progress: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """Transcribes and translates speech in video_path, saving <video_name>.srt alongside."""
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Whisper model not found: {model_path}")
        if not os.path.isfile(self.whisper_exe):
            raise FileNotFoundError(f"whisper-cli.exe not found at: {self.whisper_exe}")

        self._is_cancelled = False
        video_dir = os.path.dirname(video_path)
        video_stem = os.path.splitext(os.path.basename(video_path))[0]
        final_srt = os.path.join(video_dir, f"{video_stem}.srt")

        wav_path = os.path.join(self.tmp_dir, f"sub_tmp_{os.getpid()}_{hash(video_path) & 0xffffffff}.wav")
        srt_temp_base = os.path.join(self.tmp_dir, f"sub_out_{os.getpid()}_{hash(video_path) & 0xffffffff}")

        try:
            # 1. Audio extraction
            if on_progress:
                on_progress(0.05, "Extracting audio from video...")
            success = self.extract_audio(video_path, wav_path)
            if not success or self._is_cancelled:
                raise RuntimeError("Failed to extract audio or operation was cancelled.")

            # 2. Whisper transcription
            if on_progress:
                on_progress(0.10, "Initializing Whisper neural network...")

            cmd = [
                self.whisper_exe,
                "-m", model_path,
                "-f", wav_path,
                "-t", str(num_threads),
                "-osrt",
                "-of", srt_temp_base,
                "-pp",
                "-sns",
                "-et", "2.40",
                "-nth", "0.60"
            ]

            if translate_to_english:
                cmd.extend(["-tr", "-l", "auto"])
            else:
                cmd.extend(["-l", "auto"])

            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            self.active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo
            )

            progress_pattern = re.compile(r"progress\s*=\s*(\d+)%", re.IGNORECASE)

            if self.active_process.stdout:
                for line in self.active_process.stdout:
                    if self._is_cancelled:
                        self.cancel()
                        break
                    m = progress_pattern.search(line)
                    if m and on_progress:
                        pct = int(m.group(1))
                        # Scale 10% -> 95%
                        scaled = 0.10 + (pct / 100.0) * 0.85
                        on_progress(scaled, f"Transcribing & Translating speech: {pct}%")

            self.active_process.wait()
            self.active_process = None

            if self._is_cancelled:
                raise RuntimeError("Subtitle generation was cancelled.")

            generated_srt = srt_temp_base + ".srt"
            if not os.path.isfile(generated_srt) or os.path.getsize(generated_srt) == 0:
                raise RuntimeError("Whisper finished but no subtitles were generated.")

            # 3. Post-processing & placement
            shutil.copyfile(generated_srt, final_srt)

            if on_progress:
                on_progress(1.0, "Subtitles generated successfully!")

            return final_srt

        finally:
            # Cleanup temporary artifacts
            for p in [wav_path, srt_temp_base + ".srt", srt_temp_base + ".txt"]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    def cancel(self) -> None:
        """Terminates active processing."""
        self._is_cancelled = True
        if self.active_process:
            try:
                self.active_process.terminate()
            except Exception:
                pass
            self.active_process = None
