# VX Player

A high-performance, distraction-free, 100% offline media player ecosystem engineered for mobile (**Android**) and desktop (**Windows PC**). Focused entirely on local playback, visual elegance, audio clarity, and privacy-respecting architecture with **zero network tracking, zero internet permissions, and zero ads**.

---

## Table of Contents
1. [Core Architectural Principles](#core-architectural-principles)
2. [5 Calibrated Psychological Dark Themes](#5-calibrated-psychological-dark-themes)
3. [Android Mobile Port (`v2.23`)](#android-mobile-port-v223)
   - [Media Library & Discovery](#1-media-library--discovery)
   - [Seen Tracking & Batch Management](#2-seen-tracking--batch-management)
   - [Playback & Gesture Controls](#3-playback--gesture-controls)
   - [ClearVoice (Offline Dialogue Isolation)](#4-clearvoice-offline-dialogue-isolation)
   - [On-Device Whisper AI Subtitles](#5-on-device-whisper-ai-subtitles)
   - [Global Error Supervisor & 10s Banner](#6-global-error-supervisor--10s-banner)
   - [Privacy & Air-Gapped Security](#7-privacy--air-gapped-security)
4. [Desktop PC Port (`v2.23`)](#desktop-pc-port-v223)
   - [Desktop Playback Engine](#1-desktop-playback-engine)
   - [Progressive Library & 4-Tab Navigation](#2-progressive-library--4-tab-navigation)
   - [Desktop ClearVoice Equalizer](#3-desktop-clearvoice-equalizer)
   - [Keyboard & Mouse Gesture Shortcuts](#4-keyboard--mouse-gesture-shortcuts)
   - [Right-Click Context Menu](#5-right-click-context-menu)
5. [Hotspot Direct Stream & Wireless Install](#hotspot-direct-stream--wireless-install)
6. [Supported Media Formats & Codecs](#supported-media-formats--codecs)
7. [Installation & Quick Start](#installation--quick-start)

---

## Core Architectural Principles

- **100% Air-Gapped & Offline**: `android.permission.INTERNET` is completely stripped from the Android manifest and all dependencies. No background telemetry, no listening sockets, no analytics, and zero cloud calls.
- **Zero Ads & Zero Bloat**: No banners, no interstitial popups, no online feed recommendations, and no tracking libraries.
- **Identical Mobile & Desktop Parity**: Controls, symbols, gestures, audio filters, history engines, and color themes are unified across Android and Windows.
- **Crash-Resistant Reliability**: Global error supervisors catch unexpected runtime exceptions, displaying clean 10-second banners rather than crashing or terminating playback.

---

## 5 Calibrated Psychological Dark Themes

Both the Mobile and Desktop apps feature a unified theme engine with 5 distinct dark modes grounded in human visual ergonomics:

| # | Theme Name | Visual Philosophy | Palette Profile |
|---|---|---|---|
| **1** | **Stealth Obsidian** *(Default)* | **OLED True Dark**: Replaces harsh blue light with deep charcoal surfaces. Drops glare by 85% for zero ocular fatigue in pitch-black rooms. | Surface: `#090B0E`<br>Cards: `#101318`<br>Logo: `#181D26`<br>Accent: `#60A5FA` (Soft Ice) |
| **2** | **Monochrome Titanium** | **Apple Pro Studio**: Completely desaturated, neutral palette. Eliminates color cast so movie posters and video thumbnails remain color-accurate. | Surface: `#09090B`<br>Cards: `#111114`<br>Logo: `#222226`<br>Accent: `#FFFFFF` (Pure White) |
| **3** | **Emerald Studio** | **Acoustic Restfulness**: Calibrated to the human eye's peak spectral sensitivity (~555nm). Reduces eye strain during marathon binge sessions. | Surface: `#060A08`<br>Cards: `#0B120E`<br>Logo: `#064E3B`<br>Accent: `#10B981` (Emerald) |
| **4** | **Sunset Cinema** | **Warm Filmstrip**: Replaces blue light with warm amber and bronze hues. Prevents melatonin suppression for comfortable late-night viewing. | Surface: `#0C0A09`<br>Cards: `#14110F`<br>Logo: `#78350F`<br>Accent: `#F59E0B` (Amber) |
| **5** | **Refined Cyber Cyan** | **Controlled Neon**: Deep jet-black carbon background. Preserves the iconic cyan brand identity as delicate point-accents rather than large solid blocks. | Surface: `#080C10`<br>Cards: `#0C131D`<br>Logo: `#0369A1`<br>Accent: `#38BDF8` (Cyan) |

### Theme Switching Controls
- **One-Tap Quick Rotation**: Tap the theme pill in the top header (`Obsidian` &rarr; `Titanium` &rarr; `Emerald` &rarr; `Amber` &rarr; `Cyber`) to immediately cycle through them.
- **Theme Picker Dialog**: Long-press the theme button, or tap `⋮` (More) &rarr; **Theme: [Current] (Switch/Select)** to open a radio-button dialog and jump directly to any theme.
- **Automatic Persistence**: Saves to local preferences and applies dynamically across all views, cards, and dialogs.

---

## Android Mobile Port (`v2.23`)

Built with Kotlin, Jetpack Media3 (ExoPlayer), Room/SQLite, C++ whisper.cpp, and Android Scoped Storage.

### 1. Media Library & Discovery
- **Automatic MediaStore Indexing**: Discovers and indexes local video files across internal memory and external SD cards without background CPU drain.
- **Storage Access Framework (SAF)**: Add and persist access to custom directories and isolated USB/OTG storage trees.
- **Direct File Picker**: Quick-open individual video files directly via the system document browser.
- **Horizontal Recently Played Carousel**: Smooth horizontal card carousel at the top of the Folders tab featuring thumbnail previews, resume progress bars, and duration badges. Seamlessly tracks videos opened from device storage, SAF folders, and external file pickers.
- **Real-Time Search & Natural Sorting**: Filter folders and files in real-time. Sort by:
  - Name (A-Z and Z-A with natural numerical sorting: `Episode 2` precedes `Episode 10`)
  - Date Modified (Newest / Oldest)
  - File Size (Largest / Smallest)
  - Duration (Longest / Shortest)
- **Multi-Selection Mode**: Long-press any video to enter batch selection:
  - Batch Mark as Seen / Unseen
  - Batch Hide to Private Vault
  - Batch Delete via MediaStore / SAF contracts
  - Batch AI Subtitle Generation
- **Hidden Videos Vault**: Hide sensitive videos from the library into an encrypted private vault. Access anytime via `⋮` (More) &rarr; **Hidden Videos**.
- **Unified Header**: Displays the rounded "VX" logo badge, bold title, and single version badge (**`v2.23`**) with dynamic theme accent tinting.

### 2. Seen Tracking & Batch Management
- **Automatic 90% TV Credit Threshold**: Automatically marks videos as completed when playback reaches 90% duration or enters the final 30 seconds.
- **Seen Tab**: Dedicated view listing all completed videos with green checkmark indicators (`✓`).
- **Batch Delete All Seen**: Single-tap action to permanently delete all completed videos from disk with confirmation dialog and disk space freed calculation.
- **Clear Seen History**: Removes seen badges from history without touching files on disk.
- **Async MediaStore Deletion Blacklist**: Synchronized blacklist prevents deleted video files from momentarily resurfacing during MediaStore rescans.

### 3. Playback & Gesture Controls
- **Always-Visible Top Status Header**:
  - **Left**: Real-time elapsed / remaining time (`04:15 / 1:20:00` or `04:15 (-1:15:45)`). Tap to toggle. Visible even during touch lock or auto-hidden controls.
  - **Right**: Live battery percentage (`🔋 85%`) and wall-clock time (`10:30 PM`).
- **Customizable Circular Quick Action Bar**:
  - Horizontal scrolling row of customizable quick actions:
    - **Playback Speed**: `0.25×` to `4.0×` with Sonic pitch preservation.
    - **Skip 90s OP**: Instant anime opening / intro skip with seek feedback.
    - **Orientation Lock**: Auto, Landscape, Portrait, or match Source Video.
    - **Aspect Ratio**: Fit, Fill, Zoom, 16:9, 4:3, or Stretch.
    - **In-Player Playlist**: Slide-up drawer to browse episodes with Repeat All, Repeat One, and Shuffle.
    - **ClearVoice Dialogue Booster**: Real-time speech clarity toggle and slider.
    - **Delete Video**: 4-tap safety deletion directly from player with auto-progression to next video.
    - **Audio Track Selector**: Multi-channel switcher and instant mute toggle.
    - **Subtitle Selector**: Internal track switcher and external subtitle loader (`.srt`, `.vtt`, `.ass`, `.ssa`).
    - **HW / SW Decoder Switcher**: Hardware-accelerated decoding vs. software fallback.
    - **Sleep Timer**: Auto-pause after 15m, 30m, 45m, 60m, or at End of Current Video.
- **Touch Gestures**:
  - **Left Vertical Swipe**: Brightness adjustment (0% to 100%) with visual HUD indicator. Top 35dp excluded to prevent accidental notification pull-downs.
  - **Right Vertical Swipe**: Volume control (0% to 100%) plus **200% Audio Volume Boost** powered by Android's `LoudnessEnhancer`.
  - **Horizontal Swipe**: Precision scrub seeking with timestamp preview.
  - **Double-Tap Left / Right**: 5-second relative seek backward / forward.
  - **Double-Tap Center**: Play / Pause toggle.
  - **Long-Press (Hold to Boost)**: Temporarily boosts speed to 2.0× while finger is held down; release smoothly restores original speed.
  - **Screen Touch Lock**: Locks touch inputs with auto-hiding unlock button to prevent accidental touches.
- **Picture-in-Picture (PiP)**: Smooth PiP transition with system media controls (Play/Pause, Rewind, Fast-Forward) and auto-PiP on home gesture.
- **Bluetooth & AVRCP Integration**: Full headset button control (play, pause, next, previous) with configurable double-tap play/pause toggle.

### 4. ClearVoice (Offline Dialogue Isolation)
- **Problem Solved**: Muffled voices and unintelligible dialogue caused by loud background music or explosive action sound effects.
- **Real-Time EQ Filter**:
  - Attenuates low-frequency rumble and boom (-6.0 dB at 31.25 Hz up to -1.5 dB at 250 Hz).
  - Boosts vocal presence and speech clarity (+5.0 dB to +6.0 dB across 1 kHz, 2 kHz, and 4 kHz).
- **ClearVoice Video Export**: Offline background processing engine that applies speech isolation and exports a remastered video file with crystal-clear dialogue.

### 5. On-Device Whisper AI Subtitles
- **Embedded C++ whisper.cpp Engine**: Generates subtitles completely locally on your phone with zero internet access.
- **Model Support**: Supports official GGML Whisper models (`tiny`, `base`, `small`).
- **Multilingual Translation**: Automatically transcribes foreign speech (Kannada, Hindi, Japanese, Spanish, etc.) and translates it directly into English subtitles (`.srt`).
- **Offline Audio Staging & PC Offload**: Extract audio locally on Android and offload transcription to your PC companion if preferred.

### 6. Global Error Supervisor & 10s Banner
- **Crash Protection**: Traps uncaught exceptions across all background threads, coroutines, and UI event loops.
- **10-Second Floating Banner**: Displays an animated danger banner (`#250D11`, border `#FF453A`, warning symbol `⚠`, clean `e.message`, and `✕` close button) anchored to the top of the screen.
- **Zero Disruptive Crashes**: Automatically dismisses after 10 seconds without killing playback or terminating the app.

### 7. Privacy & Air-Gapped Security
- **No Internet Permission**: `android.permission.INTERNET` is completely absent.
- **No Analytics / Telemetry**: No Firebase, no Google Analytics, no crash reporters sending data home.
- **Local Data Only**: All playback history, resume positions, and settings stay strictly on your device.

---

## Desktop PC Port (`v2.23`)

Built with Python 3.10+, LibVLC 3.x, and CustomTkinter. Packaged into a standalone single-binary executable (`VXPlayerPC.exe`).

### 1. Desktop Playback Engine
- **LibVLC 3.x Backend**: Native hardware decoding for 10-bit Hi10P MKV, HEVC/H.265, AV1, VP9, WebM, FLV, and styled ASS/SSA anime subtitles.
- **Zero-Resize Overlay HUD**: Header and controls float directly over the video canvas without twitching, jittering, or resizing the video surface.
- **Auto-Hiding HUD**: Overlay bars and mouse cursor automatically hide after 2.5 seconds of inactivity and reveal upon mouse movement.
- **200% Audio Amplification**: Boost quiet videos past 100% up to 200% with hardware-level loudness gain.
- **Sleep Timer**: Configure auto-pause after 15m, 30m, 45m, 60m, or at End of Current Video.

### 2. Progressive Library & 4-Tab Navigation
- **4 Segmented Tabs**: `Folders`, `All Videos`, `Recent`, `Seen`.
- **Progressive Background Crawler**: Discovers media folders and files in a non-blocking background thread with live path feedback and batch rendering.
- **Recent Tab**: Displays recently played videos with progress bars and "Clear Recent" action.
- **Seen Tab**: Displays completed videos with "Delete All Seen" (with freed disk space calculation) and "Clear History".
- **Batch Actions**: "Play All" and "AI Sub (Folder)" directly from folder detail views.

### 3. Desktop ClearVoice Equalizer
- **10-Band Audio Equalizer**: Powered by LibVLC's native `vlc.AudioEqualizer()`.
- **Dialogue Frequency Curve**: Subtractive rumble suppression below 250 Hz combined with speech presence boost (+5dB to +6dB) across 1 kHz–4 kHz.
- **Toggles**: Toggle via header button, controls bar button, or keyboard shortcut **`V`**.

### 4. Keyboard & Mouse Gesture Shortcuts

| Key / Gesture | Action | Description |
|---|---|---|
| `Space` | **Play / Pause** | Toggle video playback |
| `Right` / `Left` | **Seek ±5s** | Relative seek backward / forward |
| `Double-Click Left 25%` | **Seek -5s** | Touch edge seek backward |
| `Double-Click Right 25%` | **Seek +5s** | Touch edge seek forward |
| `Double-Click Center` | **Toggle Fullscreen** | Expand to borderless fullscreen |
| `F` / `F11` | **Fullscreen** | Enter / exit fullscreen mode |
| `Escape` | **Exit Fullscreen** | Return to windowed playback |
| `Up` / `Down` | **Volume ±5%** | Adjust playback volume (up to 200%) |
| `V` | **ClearVoice** | Toggle dialogue clarity isolation filter |
| `O` | **Skip 90s OP** | Jump 90-second anime opening theme |
| `A` *(Hold)* | **Hold to Fast-Forward** | Accelerate playback to preset boost speed (e.g. 2.0×); release restores normal speed |
| `E` / `W` | **Hold Target Speed ±0.1×** | Adjust hold speed target preset (up to 8.0×) without interrupting playback |
| `D` / `S` | **Immediate Speed ±0.1×** | Adjust immediate playback speed |
| `N` / `P` | **Next / Prev Video** | Progress to next / previous video in playlist |
| `L` | **Playlist Sidebar** | Toggle slide-out playlist episode drawer |

### 5. Right-Click Context Menu
Right-clicking any video card in the desktop library provides:
- `▶ Play Video`
- `✓ Mark as Seen` / `Mark as Unseen`
- `📁 Show in File Explorer` (opens Windows Explorer with the video file highlighted)
- `⚡ Generate AI Subtitles` (opens Whisper AI generator modal)
- `🗑 Delete Video` (confirmation dialog, permanently removes file from disk and library)

---

## Hotspot Direct Stream & Wireless Install

When your laptop is connected to your phone's mobile Wi-Fi Hotspot, you can stream and update the app wirelessly in seconds with **zero cables and zero internet access**:

1. Run the local hotspot stream server on your laptop:
   ```cmd
   python hotspot_server.py
   ```
2. On your phone, open Chrome and visit:
   ```
   http://10.69.115.191:8888
   ```
3. The APK streams directly over the local hotspot at full Wi-Fi speed (~2 seconds). Tap **Open &rarr; Update** to install!

---

## Supported Media Formats & Codecs

| Category | Formats & Codecs |
|---|---|
| **Video Containers** | `.mp4`, `.mkv`, `.webm`, `.avi`, `.mov`, `.m4v`, `.flv`, `.wmv`, `.3gp`, `.ts`, `.m2ts`, `.mts`, `.vob`, `.ogv` |
| **Video Codecs** | H.264 (AVC), H.265 (HEVC, 8-bit & 10-bit), VP8, VP9, AV1, MPEG-4, MPEG-2 |
| **Audio Codecs** | AAC, MP3, Opus, FLAC, Vorbis, AC-3 (Dolby Digital), E-AC-3, DTS, ALAC, PCM |
| **Subtitle Formats** | SubRip (`.srt`), WebVTT (`.vtt`), Advanced SubStation Alpha (`.ass`), SubStation Alpha (`.ssa`), SubViewer (`.sub`) |

---

## Installation & Quick Start

### Android Mobile
- **Direct APK**: Install [VX-Player-v2.23.apk](file:///C:/Users/Parikshith.G/OneDrive/Desktop/VX-Player-v2.23.apk).
- **1-Click ADB Script**: Connect your phone via USB with USB debugging enabled and double-click [install_vx_player.bat](file:///C:/Users/Parikshith.G/OneDrive/Desktop/install_vx_player.bat).
- **Manual ADB Command**:
  ```powershell
  & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r -d "C:\Users\Parikshith.G\OneDrive\Desktop\VX-Player-v2.23.apk"
  ```

### Desktop PC
- **Standalone Binary**: Launch [VXPlayerPC.exe](file:///C:/Users/Parikshith.G/OneDrive/Desktop/VXPlayerPC.exe).
- **From Source**:
  ```powershell
  cd desktop
  python -m pip install -r requirements.txt
  python main.py
  ```

---

## License & Privacy

Built for personal, private, and air-gapped media consumption. All code, playback metadata, and watch histories remain strictly local to your devices. Zero data is ever collected or transmitted.
