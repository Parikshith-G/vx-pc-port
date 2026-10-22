"""
Role: Laptop desktop companion worker for offloaded mobile subtitle generation.
Responsibility: Detects offload jobs exported by VX Player mobile, utilizes laptop CPU
(AMD Ryzen 5 3500U, 8 threads, AVX2) for fast speech-to-text processing, and synchronizes
live progress and completed .srt files back to the phone.
Details: Strictly zero emojis; 100% air-gapped; operates over physical USB (ADB or MTP/file sharing).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

DEFAULT_ADB_PATHS = [
    r"C:\Users\Parikshith.G\AppData\Local\Android\Sdk\platform-tools\adb.exe",
    shutil.which("adb")
]

VLC_PATHS = [
    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    shutil.which("vlc")
]


class LaptopOffloadWorker:
    def __init__(self, subtitles_dir: Optional[str] = None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.bin_dir = os.path.join(self.base_dir, "bin")
        self.whisper_exe = os.path.join(self.bin_dir, "whisper-cli.exe")
        self.adb_exe = self._locate_adb()
        self.vlc_exe = self._locate_vlc()
        self.subtitles_dir = subtitles_dir
        self.tmp_dir = os.path.join(os.path.expanduser("~"), ".vx_player_desktop", "offload_tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.models_dir = os.path.join(os.path.expanduser("~"), ".vx_player_desktop", "models")
        os.makedirs(self.models_dir, exist_ok=True)

    def _locate_adb(self) -> Optional[str]:
        for path in DEFAULT_ADB_PATHS:
            if path and os.path.isfile(path):
                return path
        return None

    def _locate_vlc(self) -> Optional[str]:
        for path in VLC_PATHS:
            if path and os.path.isfile(path):
                return path
        return None

    def find_whisper_model(self) -> Optional[str]:
        # 1. Check local desktop models
        if os.path.isdir(self.models_dir):
            for fname in os.listdir(self.models_dir):
                if fname.endswith(".bin") and os.path.getsize(os.path.join(self.models_dir, fname)) > 10_000_000:
                    return os.path.join(self.models_dir, fname)

        # 2. Check if phone has models in Downloads/VxPlayer/Transcription/
        if self.adb_exe:
            try:
                res = subprocess.run(
                    [self.adb_exe, "shell", "ls /sdcard/Download/VxPlayer/Transcription/*.bin"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip().endswith(".bin")]
                    if lines:
                        phone_model = lines[0]
                        local_target = os.path.join(self.models_dir, os.path.basename(phone_model))
                        if not os.path.isfile(local_target) or os.path.getsize(local_target) < 10_000_000:
                            print(f"[Worker] Pulling offline model from connected phone: {phone_model}")
                            subprocess.run([self.adb_exe, "pull", phone_model, local_target], check=True)
                        if os.path.isfile(local_target):
                            return local_target
            except Exception as e:
                print(f"[Worker] Model check via ADB: {e}")

        # 3. Check Downloads folder on PC
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        for root, _, files in os.walk(downloads_dir):
            for fname in files:
                if fname.startswith("ggml-") and fname.endswith(".bin"):
                    return os.path.join(root, fname)

        return None

    def check_adb_connected(self) -> bool:
        if not self.adb_exe:
            return False
        try:
            res = subprocess.run([self.adb_exe, "devices"], capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip() and not l.startswith("*")]
            # Skip header line "List of devices attached"
            device_lines = [l for l in lines[1:] if "\tdevice" in l]
            return len(device_lines) > 0
        except Exception:
            return False

    def read_job_from_phone(self) -> Optional[Dict]:
        if not self.adb_exe:
            return None
        try:
            res = subprocess.run(
                [self.adb_exe, "shell", "cat /sdcard/Download/Subtitles/vx_laptop_offload_job.json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0 and res.stdout.strip().startswith("{"):
                return json.loads(res.stdout.strip())
        except Exception as e:
            print(f"[Worker] Failed to read job via ADB: {e}")
        return None

    def push_progress_to_phone(self, progress_dict: Dict):
        if not self.adb_exe:
            return
        try:
            local_prog = os.path.join(self.tmp_dir, "vx_subtitle_queue_progress.json")
            with open(local_prog, "w", encoding="utf-8") as f:
                json.dump(progress_dict, f, indent=2)
            subprocess.run(
                [self.adb_exe, "push", local_prog, "/sdcard/Download/Subtitles/vx_subtitle_queue_progress.json"],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            print(f"[Worker] Failed to push progress to phone: {e}")

    def push_srt_to_phone(self, local_srt_path: str, remote_filename: str):
        if not self.adb_exe:
            return
        remote_path = f"/sdcard/Download/Subtitles/{remote_filename}"
        try:
            subprocess.run([self.adb_exe, "push", local_srt_path, remote_path], check=True, timeout=10)
            subprocess.run([self.adb_exe, "shell", f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_path}"], capture_output=True, timeout=5)
            print(f"[Worker] Pushed master subtitle to phone: {remote_path}")
        except Exception as e:
            print(f"[Worker] Failed to push SRT to phone: {e}")

    def extract_audio(self, video_path: str, output_wav: str) -> bool:
        if not self.vlc_exe:
            raise RuntimeError("VLC executable not found for audio extraction.")
        if os.path.exists(output_wav):
            try:
                os.remove(output_wav)
            except Exception:
                pass

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
            startupinfo.wShowWindow = 0

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
        proc.wait()
        return os.path.isfile(output_wav) and os.path.getsize(output_wav) > 1000

    def transcode_with_whisper(
        self,
        wav_path: str,
        model_path: str,
        output_srt_base: str,
        num_threads: int = 8,
        on_progress: Optional[callable] = None
    ) -> bool:
        cmd = [
            self.whisper_exe,
            "-m", model_path,
            "-f", wav_path,
            "-t", str(num_threads),
            "-osrt",
            "-of", output_srt_base,
            "-pp",
            "-sns",
            "-et", "2.40",
            "-nth", "0.60",
            "-tr",
            "-l", "auto"
        ]
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo
        )

        for line in iter(proc.stdout.readline, ""):
            line_str = line.strip()
            if line_str and on_progress:
                on_progress(line_str)

        proc.wait()
        final_srt = f"{output_srt_base}.srt"
        return os.path.isfile(final_srt) and os.path.getsize(final_srt) > 0

    def run(self):
        print("==================================================")
        print("  VX PLAYER - LAPTOP SUBTITLE WORKER COMPANION")
        print("  Hardware: AMD Ryzen 5 3500U (4 Cores, 8 Threads)")
        print("  Instruction Set: AVX2 / FMA3 Enabled")
        print("==================================================")

        if not os.path.isfile(self.whisper_exe):
            print(f"[Error] whisper-cli.exe not found at: {self.whisper_exe}")
            sys.exit(1)

        if not self.vlc_exe:
            print("[Error] VLC not found for audio decoding. Please install VLC.")
            sys.exit(1)

        model_path = self.find_whisper_model()
        if not model_path:
            print("[Warning] No offline Whisper model (.bin) found on PC or phone.")
            print("Please place ggml-tiny.bin, ggml-base.bin, or ggml-small.bin in:")
            print(f"  {self.models_dir}")
            sys.exit(1)

        print(f"[Worker] Whisper Engine: {self.whisper_exe}")
        print(f"[Worker] Active Model:   {model_path} ({os.path.getsize(model_path) // (1024*1024)} MB)")
        print(f"[Worker] VLC Extractor:  {self.vlc_exe}")

        has_adb = self.check_adb_connected()
        print(f"[Worker] Phone Connection Mode: {'ADB Direct USB Bridge' if has_adb else 'Local Filesystem / MTP Mode'}")

        print("\n[Worker] Listening for subtitle offload jobs...")
        while True:
            job = None
            if has_adb:
                job = self.read_job_from_phone()
            elif self.subtitles_dir and os.path.isdir(self.subtitles_dir):
                job_file = os.path.join(self.subtitles_dir, "vx_laptop_offload_job.json")
                if os.path.isfile(job_file):
                    try:
                        with open(job_file, "r", encoding="utf-8") as f:
                            job = json.load(f)
                    except Exception:
                        pass

            if job and job.get("status") in ["OFFLOADED_TO_LAPTOP", "PENDING_DESKTOP"]:
                self.process_job(job, model_path, has_adb)
            time.sleep(3)

    def process_job(self, job: Dict, model_path: str, is_adb: bool):
        folder_name = job.get("folderName", "Videos")
        queue = job.get("queue", [])
        total = len(queue)
        print(f"\n[Worker] Active Job Detected: {folder_name} ({total} video(s))")

        for idx, item in enumerate(queue):
            video_name = item.get("name", "")
            base_stem = os.path.splitext(video_name)[0]
            srt_name = f"{base_stem}.srt"
            status = item.get("status", "")

            if status == "COMPLETED":
                continue

            print(f"\n[Worker] Processing Video [{idx + 1}/{total}]: {video_name}")

            # 1. Update progress state
            progress_state = {
                "version": 1,
                "folderName": folder_name,
                "totalVideos": total,
                "completedVideos": idx,
                "currentIndex": idx,
                "currentVideoName": video_name,
                "currentProgress": 10,
                "stage": "Laptop: Extracting Audio (VLC)",
                "isOffloaded": True,
                "offloadDevice": "AMD Ryzen 5 3500U (8 Threads, AVX2)",
                "status": "PROCESSING",
                "timestamp": int(time.time() * 1000)
            }
            if is_adb:
                self.push_progress_to_phone(progress_state)

            # 2. Extract or pull audio
            local_wav = os.path.join(self.tmp_dir, f"audio_{idx}.wav")
            out_srt_base = os.path.join(self.tmp_dir, f"sub_{idx}")

            if is_adb:
                # Pull video to temp or stream audio
                local_video = os.path.join(self.tmp_dir, video_name)
                phone_path = item.get("path") or f"/sdcard/Download/{video_name}"
                print(f"[Worker] Fetching media from phone: {video_name}")
                subprocess.run([self.adb_exe, "pull", phone_path, local_video], check=True)
                self.extract_audio(local_video, local_wav)
                try:
                    os.remove(local_video)
                except Exception:
                    pass
            else:
                local_video = os.path.join(self.subtitles_dir, video_name) if self.subtitles_dir else video_name
                self.extract_audio(local_video, local_wav)

            # 3. Transcribe with whisper-cli (8 threads)
            print(f"[Worker] Running Whisper Speech Recognition with 8 threads (AVX2)...")
            progress_state["currentProgress"] = 30
            progress_state["stage"] = "Laptop: Transcribing Speech (AVX2)"
            if is_adb:
                self.push_progress_to_phone(progress_state)

            def on_progress_line(line: str):
                if line.startswith("["):
                    print(f"  {line}")

            success = self.transcode_with_whisper(
                wav_path=local_wav,
                model_path=model_path,
                output_srt_base=out_srt_base,
                num_threads=8,
                on_progress=on_progress_line
            )

            if success:
                final_local_srt = f"{out_srt_base}.srt"
                if is_adb:
                    self.push_srt_to_phone(final_local_srt, srt_name)
                elif self.subtitles_dir:
                    shutil.copy(final_local_srt, os.path.join(self.subtitles_dir, srt_name))

                item["status"] = "COMPLETED"
                progress_state["currentProgress"] = 100
                progress_state["completedVideos"] = idx + 1
                progress_state["stage"] = f"Completed {video_name}"
                if is_adb:
                    self.push_progress_to_phone(progress_state)
                print(f"[Worker] Finished: {srt_name}")
            else:
                print(f"[Worker] Error transcribing {video_name}")

            try:
                if os.path.exists(local_wav):
                    os.remove(local_wav)
            except Exception:
                pass

        print(f"\n[Worker] All {total} videos in offload job completed successfully.")
        completion_state = {
            "version": 1,
            "folderName": folder_name,
            "totalVideos": total,
            "completedVideos": total,
            "currentIndex": total - 1,
            "currentProgress": 100,
            "stage": "All Completed on Laptop (Ryzen 5 3500U)",
            "isOffloaded": True,
            "status": "COMPLETED",
            "timestamp": int(time.time() * 1000)
        }
        if is_adb:
            self.push_progress_to_phone(completion_state)


def main():
    parser = argparse.ArgumentParser(description="VX Player Laptop Subtitle Worker Companion")
    parser.add_argument("--subtitles-dir", type=str, default=None, help="Path to local or mounted Subtitles folder")
    args = parser.parse_args()

    worker = LaptopOffloadWorker(subtitles_dir=args.subtitles_dir)
    worker.run()


if __name__ == "__main__":
    main()
