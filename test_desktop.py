"""
Role: Test suite for VX Player PC core modules.
Responsibility: Validates natural alphanumeric sorting and playback history persistence.
Details: Tests user-reported bug cases and resume tracking in Python.
"""

import os
import shutil
import tempfile
import unittest

from core.history_manager import HistoryManager
from core.natural_sort import natural_sort_key, sort_filenames
from ui.controls_bar import format_time
from ui.library_view import format_file_size


class TestVxPlayerDesktop(unittest.TestCase):

    def test_anime_sorting_user_issue(self):
        input_list = ["animename_1000.mkv", "animename_2.mkv"]
        expected = ["animename_2.mkv", "animename_1000.mkv"]
        self.assertEqual(sort_filenames(input_list), expected)

    def test_natural_sorting_episodes(self):
        episodes = [
            "Episode 100",
            "Episode 2",
            "Episode 1",
            "Episode 1000",
            "Episode 20",
            "Episode 10"
        ]
        expected = [
            "Episode 1",
            "Episode 2",
            "Episode 10",
            "Episode 20",
            "Episode 100",
            "Episode 1000"
        ]
        self.assertEqual(sort_filenames(episodes), expected)

    def test_leading_zeros(self):
        files = ["002", "10", "01", "2", "000"]
        expected = ["000", "01", "002", "2", "10"]
        self.assertEqual(sort_filenames(files), expected)

    def test_history_persistence(self):
        temp_dir = tempfile.mkdtemp()
        try:
            history = HistoryManager(storage_dir=temp_dir)
            video_path = os.path.join(temp_dir, "anime_ep1.mkv")

            # Initially 0
            self.assertEqual(history.get_resume_position(video_path), 0)
            self.assertFalse(history.is_seen(video_path))

            # Save partial progress (15 minutes in)
            history.save_position(video_path, 900000, 1440000)
            self.assertEqual(history.get_resume_position(video_path), 900000)
            self.assertFalse(history.is_seen(video_path))

            # Watched past 95% -> auto-marked as seen and cleared resume
            history.save_position(video_path, 1400000, 1440000)
            self.assertTrue(history.is_seen(video_path))
            self.assertEqual(history.get_resume_position(video_path), 0)

            # Reload from disk
            history_reloaded = HistoryManager(storage_dir=temp_dir)
            self.assertTrue(history_reloaded.is_seen(video_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_time_and_size_format(self):
        self.assertEqual(format_time(0), "00:00")
        self.assertEqual(format_time(65000), "01:05")
        self.assertEqual(format_time(3665000), "01:01:05")
        self.assertEqual(format_file_size(1024 * 1024 * 500), "500.0 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 1024 * 2), "2.00 GB")

    def test_player_speed_controls(self):
        from player.vlc_player import VlcPlayer
        player = VlcPlayer()
        self.assertEqual(player.get_speed(), 1.0)
        player.set_speed(1.25)
        self.assertAlmostEqual(player.get_speed(), 1.25, places=2)
        player.set_speed(5.0)
        self.assertAlmostEqual(player.get_speed(), 5.0, places=2)
        player.set_speed(8.0)
        self.assertAlmostEqual(player.get_speed(), 8.0, places=2)
        player.set_speed(10.0)  # Should clamp to 8.0
        self.assertAlmostEqual(player.get_speed(), 8.0, places=2)
        player.set_speed(0.1)
        self.assertAlmostEqual(player.get_speed(), 0.1, places=2)
        player.set_speed(0.02)  # Should clamp to 0.1
        self.assertAlmostEqual(player.get_speed(), 0.1, places=2)

    def test_hold_target_and_immediate_speed_logic(self):
        from main import VxPlayerApp
        app = VxPlayerApp()
        try:
            # 1. Hold target preset adjusts with E (+0.1) and W (-0.1) without immediately affecting playback
            app.player.set_speed(1.0)
            self.assertEqual(app.hold_speed_target, 2.0)
            self.assertAlmostEqual(app.player.get_speed(), 1.0, places=2)

            # Press E -> +0.1x target
            app.increase_hold_speed_target()
            self.assertAlmostEqual(app.hold_speed_target, 2.1, places=2)
            self.assertAlmostEqual(app.player.get_speed(), 1.0, places=2)  # Normal speed unchanged!

            # Press W x 2 -> -0.2x target
            app.decrease_hold_speed_target()
            app.decrease_hold_speed_target()
            self.assertAlmostEqual(app.hold_speed_target, 1.9, places=2)
            self.assertAlmostEqual(app.player.get_speed(), 1.0, places=2)

            # 2. Hold 'A' applies the target
            app.on_speed_hold_press()
            self.assertTrue(app._is_holding_speed)
            self.assertAlmostEqual(app.player.get_speed(), 1.9, places=2)

            # Release 'A' restores normal speed
            app._do_end_speed_hold()
            self.assertFalse(app._is_holding_speed)
            self.assertAlmostEqual(app.player.get_speed(), 1.0, places=2)

            # 3. D (speed up) and S (speed down) immediately affect playback
            app.speed_up()
            self.assertAlmostEqual(app.player.get_speed(), 1.1, places=2)
            app.speed_down()
            self.assertAlmostEqual(app.player.get_speed(), 1.0, places=2)
            app.speed_down()
            self.assertAlmostEqual(app.player.get_speed(), 0.9, places=2)
        finally:
            app.destroy()

    def test_media_scanner_grouping(self):
        from core.media_scanner import ProgressiveMediaScanner
        temp_dir = tempfile.mkdtemp()
        try:
            folder1 = os.path.join(temp_dir, "Folder A")
            folder2 = os.path.join(temp_dir, "Folder B")
            os.makedirs(folder1, exist_ok=True)
            os.makedirs(folder2, exist_ok=True)

            # Create test dummy videos
            open(os.path.join(folder1, "animename_1000.mkv"), "w").close()
            open(os.path.join(folder1, "animename_2.mkv"), "w").close()
            open(os.path.join(folder2, "movie.mp4"), "w").close()
            open(os.path.join(folder2, "readme.txt"), "w").close()  # Non-video

            scanner = ProgressiveMediaScanner()
            scanner.roots = [temp_dir]

            found_folders = {}
            status_updates = []
            
            def on_status(path):
                status_updates.append(path)

            def on_folder_found(folder, videos):
                found_folders[folder] = videos

            def on_finished(tf, tv):
                pass

            scanner.scan(on_status, on_folder_found, on_finished)

            self.assertIn(os.path.normpath(folder1), [os.path.normpath(k) for k in found_folders.keys()])
            self.assertIn(os.path.normpath(folder2), [os.path.normpath(k) for k in found_folders.keys()])

            # Ensure natural sorting in folder1 (animename_2 before animename_1000)
            f1_vids = [os.path.basename(v) for v in found_folders[os.path.normpath(folder1)]]
            self.assertEqual(f1_vids, ["animename_2.mkv", "animename_1000.mkv"])

            # Ensure non-video is ignored in folder2
            f2_vids = [os.path.basename(v) for v in found_folders[os.path.normpath(folder2)]]
            self.assertEqual(f2_vids, ["movie.mp4"])
            self.assertTrue(len(status_updates) > 0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

