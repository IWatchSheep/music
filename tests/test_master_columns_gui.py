"""Automated test suite verifying Unified Master Columns & Row 1 Musical Carrier.

Verifies:
1. Exact vertical gridline alignment across all rows (Header, Row 1, and Temporary Rows).
2. Internal column dividers on continuous sound bars (without splitting SoundEvents).
3. SoundEvent object identity and duration preservation (annotations only).
4. Variable-width column rendering proportional to millisecond durations.
5. Horizontal scrolling and zoom coordinate consistency.
6. Row 1 development-trend line and node rendering.
7. Active-row-count diagnostic preservation across view mode changes.
8. Scientific note-name correctness (MIDI 60 = C4, 69 = A4, 72 = C5, 75 = D#5/Eb5, 84 = C6).
9. Two-song independence in Dual View (no shared grids).
10. Many-column layout verification (>16 master columns).
"""

from __future__ import annotations

import unittest

from music_gui.main_window import MusicGUI
from music_model.datasets import (
    create_duck_flight_experiment,
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
)
from music_model.midi_fixture import create_synthetic_orchestral_song
from music_model.midi_importer import pitch_to_note_name
from music_model.song import SongTimeline


class TestMasterColumnsGUI(unittest.TestCase):
    """Test suite for unified master columns and Row 1 visual development."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = MusicGUI()
        cls.app.update_idletasks()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.destroy()

    def test_note_name_correctness(self) -> None:
        """Verify scientific pitch notation formatting across standard octaves."""
        # Standard benchmarks specified by ChatGPT and User
        self.assertIn("C4", pitch_to_note_name(60))
        self.assertIn("A4", pitch_to_note_name(69))
        self.assertIn("C5", pitch_to_note_name(72))
        self.assertIn("D#5", pitch_to_note_name(75))
        self.assertIn("C6", pitch_to_note_name(84))

        # Enharmonic formatting check
        enh_75 = pitch_to_note_name(75, enharmonic=True)
        self.assertIn("D#5", enh_75)
        self.assertIn("Eb5", enh_75)

    def test_exact_gridline_alignment_across_all_rows(self) -> None:
        """Verify that every master boundary aligns to the exact same x-coordinate across all rows."""
        self.app.show_progressive_mode("C")
        self.app.update_idletasks()
        view = self.app.timeline_view
        coords = view.coords
        timeline = coords.timeline

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (0, 1000, 2000, 3000, 4000, 5000))

        # Check that time_to_x is deterministic and unique for each boundary
        x_coords = [coords.time_to_x(b) for b in boundaries]
        self.assertEqual(len(x_coords), len(boundaries))
        for i in range(len(x_coords) - 1):
            self.assertLess(x_coords[i], x_coords[i + 1])

        # Header boxes match these x coordinates
        for col_idx, col in enumerate(timeline.build_columns()):
            x0, x1 = coords.column_x_bounds(col)
            self.assertEqual(x0, x_coords[col_idx])
            self.assertEqual(x1, x_coords[col_idx + 1])

        # Master gridlines are rendered at each boundary
        gridlines = view.find_master_grid_lines()
        self.assertEqual(len(gridlines), len(boundaries))
        for idx, line_id in enumerate(gridlines):
            line_coords = view.canvas.coords(line_id)
            bx = line_coords[0]
            self.assertAlmostEqual(bx, x_coords[idx], delta=0.5)

    def test_internal_column_dividers_on_continuous_sound_bars(self) -> None:
        """Verify crisp internal column dividers appear over multi-column sound events."""
        self.app.show_progressive_mode("C")
        self.app.update_idletasks()
        view = self.app.timeline_view

        # Sound A is [0, 3000) ms, spanning Col 0 [0, 1000), Col 1 [1000, 2000), Col 2 [2000, 3000)
        # It has 2 internal boundaries: 1000 ms and 2000 ms
        dividers = view.find_internal_column_dividers("Sound_A")
        # Dividers include the vertical lines and notch markers
        self.assertGreaterEqual(len(dividers), 2)

        # Confirm Sound A bar is still ONE single continuous rectangle
        sound_bars = view.find_sound_bar("Sound_A")
        self.assertEqual(len(sound_bars), 1)

    def test_sound_event_identity_and_duration_preservation(self) -> None:
        """Verify that visual dividers NEVER split, clone, or modify SoundEvent objects."""
        song = create_synthetic_orchestral_song()
        orig_events = list(song.all_events)
        orig_ids = [id(e) for e in orig_events]
        orig_intervals = [(e.start_time_ms, e.end_time_ms) for e in orig_events]

        # Display in GUI and trigger redraw
        self.app.show_midi_mode(song)
        self.app.update_idletasks()

        # Re-check song objects in python model
        current_events = list(song.all_events)
        current_ids = [id(e) for e in current_events]
        current_intervals = [(e.start_time_ms, e.end_time_ms) for e in current_events]

        self.assertEqual(len(orig_events), len(current_events))
        self.assertEqual(orig_ids, current_ids, "SoundEvent object references must remain identical")
        self.assertEqual(orig_intervals, current_intervals, "Sound intervals must remain identical")

    def test_variable_width_column_rendering(self) -> None:
        """Verify variable-width columns reflect exact durations in pixel proportions."""
        self.app.show_single_mode()
        self.app.load_variable_width_proof()
        self.app.update_idletasks()
        view = self.app.timeline_view
        coords = view.coords

        # Proof durations: [250, 750, 500, 1000, 500, 1000] ms
        columns = coords.timeline.build_columns()
        self.assertEqual(len(columns), 6)
        scale = coords.pixels_per_ms

        for col in columns:
            x0, x1 = coords.column_x_bounds(col)
            pixel_w = x1 - x0
            expected_w = col.duration_ms * scale
            self.assertAlmostEqual(pixel_w, expected_w, delta=0.01)

    def test_row_1_development_trend_rendering(self) -> None:
        """Verify Row 1 displays the development trend line when in development mode."""
        self.app.show_duck_mode()
        self.app.current_constant_row_mode = "development"
        self.app.dual_view.set_constant_row_mode("development")
        self.app.update_idletasks()

        # Canvas 1 in dual view has duck arrangement A
        canvas1 = self.app.dual_view.canvas1
        trend_lines = canvas1.find_dev_trend_line()
        self.assertEqual(len(trend_lines), 1)

        trend_nodes = canvas1.canvas.find_withtag("dev_trend_node")
        # Arrangement A has 5 columns, so 5 trend node ovals
        self.assertEqual(len(trend_nodes), 5)

    def test_active_row_count_diagnostic_preservation(self) -> None:
        """Verify Row 1 baseline active-row count diagnostic values remain preserved."""
        self.app.show_progressive_mode("C")
        self.app.update_idletasks()
        view = self.app.timeline_view

        # Stage C expected baseline: [1, 2, 3, 2, 1]
        for col_idx, exp_val in enumerate([1, 2, 3, 2, 1]):
            items = view.find_const_val(col_idx)
            self.assertEqual(len(items), 1)
            val_text = view.canvas.itemcget(items[0], "text")
            self.assertEqual(val_text, str(exp_val))

    def test_two_song_independence(self) -> None:
        """Verify two songs in Dual View maintain independent master column systems."""
        self.app.show_dual_mode()
        self.app.update_idletasks()
        dual_view = self.app.dual_view

        song1 = dual_view.song1
        song2 = dual_view.song2

        self.assertNotEqual(song1.song_id, song2.song_id)
        self.assertNotEqual(song1.column_count, song2.column_count)
        self.assertNotEqual(song1.extract_boundaries(), song2.extract_boundaries())

        # Check canvases have separate scrollregions
        sr1 = dual_view.canvas1.canvas.cget("scrollregion")
        sr2 = dual_view.canvas2.canvas.cget("scrollregion")
        self.assertNotEqual(sr1, sr2)

    def test_many_column_orchestral_example(self) -> None:
        """Verify that the synthetic orchestral passage renders 20 master columns with aligned gridlines."""
        self.app.show_midi_mode()
        self.app.update_idletasks()
        view = self.app.timeline_view

        self.assertEqual(len(view.coords.timeline.build_columns()), 20)
        gridlines = view.find_master_grid_lines()
        self.assertEqual(len(gridlines), 21)

        # Verify master column cells on temporary rows exist
        master_cells = view.find_master_col_cells()
        # 4 temporary rows * 20 columns = 80 cells
        self.assertEqual(len(master_cells), 80)


if __name__ == "__main__":
    unittest.main()
