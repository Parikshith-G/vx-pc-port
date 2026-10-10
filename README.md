# VX Player (PC Port)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Engine](https://img.shields.io/badge/Engine-LibVLC%203.x-orange.svg)](https://www.videolan.org/vlc/)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-brightgreen.svg)]()
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg)]()

A high-performance, dark-themed offline desktop video player built for anime enthusiasts, multi-episode series bingers, and power users. Designed as the companion desktop port to **[VX Player for Android](https://github.com/Parikshith-G/vx-player)**.

---

## Key Highlights

- **Hold-to-Boost Speed (Up to 8.0x)**: Press and hold `A` for instant speed boost; smoothly returns to normal playback speed on release.
- **Configurable Speed Preset Target**: Adjust your hold boost target on-the-fly with `E` (+0.1x) and `W` (-0.1x) without cluttering the screen or interrupting playback.
- **Immediate Speed Control**: Tweak playback in real time with `D` (+0.1x) and `S` (-0.1x).
- **Anime OP Skip (+90s)**: Jump through 90-second anime opening themes in a single tap (`O`).
- **Zero-Resize Overlay HUD**: Controls and header float directly on top of the 100% video surface (`place` + `lift`). The video canvas never twitches, jitters, or resizes when controls appear or hide.
- **Natural Alphanumeric Sorting**: Correctly sequences files naturally (`Episode 2` before `Episode 1000`, `ep_02` before `ep_10`).
- **Complete Codec & Subtitle Compatibility**: Powered by LibVLC, natively plays 10-bit Hi10P MKV, HEVC/H.265, AV1, VP9, WebM, styled ASS/SSA anime subtitles, and embedded audio tracks.
- **200% Audio Volume Amplification**: Boost quiet dialogue and audio past 100% up to 200%.
- **Smart Watch History & Resume Engine**: Automatically saves playback timestamps and marks completed episodes (>95% watched) with visual checkmarks (`✓`).
- **In-Player Playlist Sidebar**: Slide open the episode drawer (`L`) to search, browse, and jump between files without stopping playback.
- **100% Offline & Private**: Zero telemetry, zero cloud tracking, zero network requests.

---

## Keyboard Shortcuts

| Key | Action | Description / OSD Feedback |
|---|---|---|
| `Space` | **Play / Pause** | Toggle playback |
| `Right` / `Left` | **Seek ±5 seconds** | Relative seek backward / forward |
| `E` | **Hold Target Speed (+0.1x)** | Increases hold boost target preset up to 8.0x (does not alter normal playback) |
| `W` | **Hold Target Speed (-0.1x)** | Decreases hold boost target preset down to 0.1x (does not alter normal playback) |
| `A` *(Hold)* | **Hold to Fast-Forward** | Activates instant target speed boost; releasing restores normal playback |
| `D` | **Immediate Speed Up (+0.1x)** | Increases current playback speed immediately up to 8.0x |
| `S` | **Immediate Speed Down (-0.1x)** | Decreases current playback speed immediately down to 0.1x |
| `O` | **Skip Anime OP (+90s)** | Instantly leaps forward 90 seconds |
| `Up` / `Down` | **Volume ±5%** | Volume adjustments with floating OSD |
| `N` / `P` | **Next / Prev Episode** | Jumps to next or previous file in active playlist |
| `F` / `F11` | **Toggle Fullscreen** | Expands to borderless fullscreen or restores windowed mode |
| `L` | **Playlist Sidebar** | Toggle collapsible in-player episode drawer |
| `Esc` | **Exit Fullscreen** | Exits fullscreen mode |

> **Note on Distraction-Free Playback**: During playback, the progress bar and header automatically hide after 2.5 seconds of mouse inactivity. Pressing speed shortcuts displays **only** the unobtrusive floating top OSD pill, leaving the bottom progress bar completely hidden. Moving or clicking the mouse instantly reveals the HUD.

---

## Project Architecture

```
vx-pc-port/
├── main.py                     # Application entry point, Tkinter/VLC coordinator, shortcuts
├── core/
│   ├── history_manager.py      # Watch history, resume positions, and seen status persistence
│   └── natural_sort.py         # Natural alphanumeric sorting algorithm for episode names
├── player/
│   └── vlc_player.py           # LibVLC wrapper: playback, speed (0.1x-8.0x), audio boost, HWND binding
├── ui/
│   ├── controls_bar.py         # Bottom playback HUD: scrubber timeline, volume, speed menu, OP skip
│   ├── header_bar.py           # Top overlay bar: back button, title, audio/sub selectors, aspect ratio
│   ├── library_view.py         # Folder/file browser with resume timestamps and seen badges
│   ├── osd.py                  # Borderless floating On-Screen Display pill for real-time visual feedback
│   └── playlist_panel.py       # Collapsible episode drawer with instant search filtering
├── test_desktop.py             # Comprehensive unit tests for sorting, resume tracking, and speed logic
├── run.bat                     # Windows one-click batch launcher
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## Installation & Setup

### Prerequisites
1. **Python 3.10 or higher**: [python.org](https://www.python.org/)
2. **VLC Media Player (64-bit)**: Ensure 64-bit VLC is installed on your system so LibVLC runtime libraries (`libvlc.dll`) are discoverable.

### 1. Clone Repository
```bash
git clone https://github.com/Parikshith-G/vx-pc-port.git
cd vx-pc-port
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
Run directly with Python:
```bash
python main.py
```
Or double-click `run.bat` on Windows.

---

## Building Standalone Executable & Installer

### 1. Compile Portable Executable (`.exe`)
To compile VX Player PC into a single portable `.exe` with PyInstaller:

```bash
pip install pyinstaller
python -m PyInstaller --noconsole --onefile --icon app_icon.ico --name "VXPlayerPC" --collect-all customtkinter --hidden-import vlc main.py
```

The output executable (`VXPlayerPC.exe`) will be placed in the `dist/` directory.

### 2. Build Windows Setup Installer (`VXPlayerSetup.exe`)
To generate a Windows Setup wizard with "Next -> Next -> Install" flow, Start Menu search integration, Desktop shortcut, and entry in Windows **Installed Apps** (Add or Remove Programs) with an uninstaller:

```bash
makensis installer.nsi
```

The installer wizard will be created at `dist/VXPlayerSetup.exe`.

---

## Running Test Suite

Verify all natural sorting, history persistence, and speed control logic:

```bash
python test_desktop.py
```

---

## Companion Mobile App

Looking for the native Android version with touch gestures, brightness/volume swipe, picture-in-picture, and circular quick actions? Check out **[VX Player for Android](https://github.com/Parikshith-G/vx-player)**.

---

## License

This project is licensed under the MIT License — see the repository for details.
