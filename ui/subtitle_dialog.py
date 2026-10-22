"""
Role: Desktop subtitle generation and model management modal dialog.
Responsibility: Displays model selection, download options, progress tracking, and batch processing controls.
Details: Completely emoji-free interface matching the dark CustomTkinter theme of VX Player PC.
"""

import os
import threading
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional
import customtkinter as ctk  # type: ignore

from core.subtitle_engine import SubtitleEngine, WHISPER_MODELS


class SubtitleDialog(ctk.CTkToplevel):
    """Modal dialog for generating offline subtitles with progress bar and model controls."""

    def __init__(
        self,
        master,
        video_paths: List[str],
        subtitle_engine: SubtitleEngine,
        on_completed: Optional[Callable[[List[str]], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.video_paths = video_paths
        self.engine = subtitle_engine
        self.on_completed = on_completed

        self.title("AI Subtitle Generator (Offline)")
        self.geometry("560x420")
        self.minsize(500, 360)
        self.resizable(False, False)
        self.configure(fg_color="#181818")

        # Keep on top of main window
        self.transient(master)
        self.grab_set()

        self._is_running = False
        self._current_worker: Optional[threading.Thread] = None

        self._build_ui()
        self._refresh_models()

    def _build_ui(self) -> None:
        pad_x = 24

        # Title Header
        title_text = "Generate Subtitles with Whisper AI"
        if len(self.video_paths) == 1:
            sub_text = os.path.basename(self.video_paths[0])
        else:
            sub_text = f"Batch: {len(self.video_paths)} videos in queue"

        lbl_title = ctk.CTkLabel(
            self,
            text=title_text,
            font=("Segoe UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(anchor="w", padx=pad_x, pady=(18, 2))

        self.lbl_target = ctk.CTkLabel(
            self,
            text=sub_text,
            font=("Segoe UI", 12),
            text_color="#AAB0BC"
        )
        self.lbl_target.pack(anchor="w", padx=pad_x, pady=(0, 14))

        # Divider
        ctk.CTkFrame(self, fg_color="#262626", height=1).pack(fill="x", padx=pad_x, pady=(0, 14))

        # Model Selection Row
        lbl_model_title = ctk.CTkLabel(
            self,
            text="Speech Model:",
            font=("Segoe UI", 12, "bold"),
            text_color="#FFFFFF"
        )
        lbl_model_title.pack(anchor="w", padx=pad_x, pady=(0, 4))

        model_row = ctk.CTkFrame(self, fg_color="transparent")
        model_row.pack(fill="x", padx=pad_x, pady=(0, 10))

        self.model_combo = ctk.CTkComboBox(
            model_row,
            values=["Checking models..."],
            width=350,
            height=32,
            font=("Segoe UI", 12),
            dropdown_font=("Segoe UI", 11),
            fg_color="#262626",
            border_color="#383838",
            button_color="#383838",
            button_hover_color="#484848"
        )
        self.model_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse_model = ctk.CTkButton(
            model_row,
            text="Browse...",
            width=80,
            height=32,
            fg_color="#262626",
            hover_color="#383838",
            font=("Segoe UI", 11),
            command=self._browse_custom_model
        )
        btn_browse_model.pack(side="right")

        # Quick Model Download Buttons Frame
        self.download_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=6)
        self.download_frame.pack(fill="x", padx=pad_x, pady=(0, 14))

        ctk.CTkLabel(
            self.download_frame,
            text="Download official models (saves locally):",
            font=("Segoe UI", 11, "bold"),
            text_color="#AAB0BC"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        dl_btn_row = ctk.CTkFrame(self.download_frame, fg_color="transparent")
        dl_btn_row.pack(fill="x", padx=12, pady=(0, 8))

        btn_dl_small = ctk.CTkButton(
            dl_btn_row,
            text="Small (~466 MB - Best for Kannada)",
            height=28,
            fg_color="#262626",
            hover_color="#383838",
            font=("Segoe UI", 10),
            command=lambda: self._start_model_download("small")
        )
        btn_dl_small.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_dl_base = ctk.CTkButton(
            dl_btn_row,
            text="Base (~140 MB)",
            height=28,
            fg_color="#262626",
            hover_color="#383838",
            font=("Segoe UI", 10),
            command=lambda: self._start_model_download("base")
        )
        btn_dl_base.pack(side="left", fill="x", expand=True, padx=4)

        btn_dl_tiny = ctk.CTkButton(
            dl_btn_row,
            text="Tiny (~75 MB)",
            height=28,
            fg_color="#262626",
            hover_color="#383838",
            font=("Segoe UI", 10),
            command=lambda: self._start_model_download("tiny")
        )
        btn_dl_tiny.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Translation check
        self.translate_var = ctk.BooleanVar(value=True)
        self.chk_translate = ctk.CTkCheckBox(
            self,
            text="Translate foreign languages (Kannada, Hindi, etc.) directly to English subtitles",
            variable=self.translate_var,
            font=("Segoe UI", 11),
            text_color="#FFFFFF",
            fg_color="#1F6AA5",
            hover_color="#144870"
        )
        self.chk_translate.pack(anchor="w", padx=pad_x, pady=(0, 14))

        # Status and Progress Bar
        self.lbl_status = ctk.CTkLabel(
            self,
            text="Ready to generate subtitles",
            font=("Segoe UI", 11),
            text_color="#AAB0BC"
        )
        self.lbl_status.pack(anchor="w", padx=pad_x, pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=8,
            progress_color="#1F6AA5",
            fg_color="#262626"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=pad_x, pady=(0, 16))

        # Bottom Action Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad_x, pady=(0, 14))

        self.btn_cancel = ctk.CTkButton(
            btn_row,
            text="Close",
            width=80,
            height=34,
            fg_color="#262626",
            hover_color="#383838",
            font=("Segoe UI", 12),
            command=self._on_close_clicked
        )
        self.btn_cancel.pack(side="right")

        self.btn_generate = ctk.CTkButton(
            btn_row,
            text="Generate Subtitles",
            width=160,
            height=34,
            fg_color="#1F6AA5",
            hover_color="#144870",
            font=("Segoe UI", 12, "bold"),
            command=self._start_generation
        )
        self.btn_generate.pack(side="right", padx=(0, 10))

    def _refresh_models(self) -> None:
        models = self.engine.get_available_models()
        self.model_map = {}
        values = []
        for key, fname, fpath in models:
            label = f"{fname} ({key})" if key != "custom" else fname
            self.model_map[label] = fpath
            values.append(label)

        if values:
            self.model_combo.configure(values=values)
            # Prefer small or base if available
            default_choice = values[0]
            for v in values:
                if "small" in v.lower():
                    default_choice = v
                    break
            self.model_combo.set(default_choice)
            self.btn_generate.configure(state="normal")
            self.lbl_status.configure(text=f"Ready. Selected model: {default_choice}")
        else:
            self.model_combo.configure(values=["No models found. Please download one below."])
            self.model_combo.set("No models found. Please download one below.")
            self.btn_generate.configure(state="disabled")
            self.lbl_status.configure(text="Please download a model below to begin.")

    def _browse_custom_model(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select GGML Whisper Model (*.bin)",
            filetypes=[("Whisper Model", "*.bin"), ("All Files", "*.*")]
        )
        if path and os.path.isfile(path):
            fname = os.path.basename(path)
            self.model_map[fname] = path
            current_vals = list(self.model_combo.cget("values"))
            if fname not in current_vals:
                current_vals.append(fname)
            self.model_combo.configure(values=current_vals)
            self.model_combo.set(fname)
            self.btn_generate.configure(state="normal")
            self.lbl_status.configure(text=f"Selected custom model: {fname}")

    def _start_model_download(self, key: str) -> None:
        if self._is_running:
            return

        self._is_running = True
        self.btn_generate.configure(state="disabled")
        self.btn_cancel.configure(text="Cancel Download")

        def worker():
            try:
                def on_dl_progress(pct: float, msg: str):
                    self.after(0, lambda: self._update_ui_progress(pct, msg))

                self.engine.download_model(key, on_dl_progress)
                self.after(0, self._on_download_complete)
            except Exception as e:
                self.after(0, lambda: self._on_error(f"Download failed: {str(e)}"))

        self._current_worker = threading.Thread(target=worker, daemon=True)
        self._current_worker.start()

    def _on_download_complete(self) -> None:
        self._is_running = False
        self.btn_cancel.configure(text="Close")
        self._refresh_models()
        self.progress_bar.set(1.0)
        self.lbl_status.configure(text="Model downloaded and ready!")

    def _start_generation(self) -> None:
        if self._is_running:
            return

        selected_label = self.model_combo.get()
        model_path = self.model_map.get(selected_label)
        if not model_path or not os.path.isfile(model_path):
            messagebox.showerror("Error", "Please select a valid Whisper model file.", parent=self)
            return

        self._is_running = True
        self.btn_generate.configure(state="disabled")
        self.btn_cancel.configure(text="Cancel")
        self.progress_bar.set(0.0)

        translate = self.translate_var.get()
        completed_srts: List[str] = []

        def worker():
            try:
                total_vids = len(self.video_paths)
                for idx, v_path in enumerate(self.video_paths):
                    if not self._is_running:
                        break

                    v_name = os.path.basename(v_path)
                    base_progress = idx / total_vids
                    weight = 1.0 / total_vids

                    def on_prog(pct: float, msg: str):
                        overall = base_progress + (pct * weight)
                        status_msg = f"[{idx + 1}/{total_vids}] {v_name}: {msg}"
                        self.after(0, lambda: self._update_ui_progress(overall, status_msg))

                    srt_path = self.engine.generate_subtitles(
                        v_path,
                        model_path,
                        translate_to_english=translate,
                        num_threads=8,
                        on_progress=on_prog
                    )
                    completed_srts.append(srt_path)

                self.after(0, lambda: self._on_generation_finished(completed_srts))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        self._current_worker = threading.Thread(target=worker, daemon=True)
        self._current_worker.start()

    def _update_ui_progress(self, pct: float, msg: str) -> None:
        self.progress_bar.set(pct)
        self.lbl_status.configure(text=msg)

    def _on_generation_finished(self, srts: List[str]) -> None:
        self._is_running = False
        self.btn_cancel.configure(text="Close")
        self.btn_generate.configure(state="normal")
        self.progress_bar.set(1.0)
        self.lbl_status.configure(text=f"Generated {len(srts)} subtitle file(s) successfully!")

        if self.on_completed:
            self.on_completed(srts)

    def _on_error(self, err_msg: str) -> None:
        self._is_running = False
        self.btn_cancel.configure(text="Close")
        self.btn_generate.configure(state="normal")
        self.lbl_status.configure(text=f"Error: {err_msg}")
        messagebox.showerror("Subtitle Generation Error", err_msg, parent=self)

    def _on_close_clicked(self) -> None:
        if self._is_running:
            self._is_running = False
            self.engine.cancel()
        self.destroy()
