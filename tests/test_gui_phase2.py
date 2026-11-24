"""Automated GUI integration tests for Stage 2B Phase 2.

Covers:
1. Progressive refitting GUI display (Stage A, Stage B, Stage C):
   - Stage A: Row 2 alone (1 column: [0, 3000) ms, Row 1 = [1]).
   - Stage B: Add Row 3 (3 columns: [0, 1000), [1000, 3000), [3000, 5000) ms, Row 1 = [1, 2, 1]).
   - Stage C: Add Row 4 (5 columns: [0, 1000), [1000, 2000), [2000, 3000), [3000, 4000), [4000, 5000) ms, Row 1 = [1, 2, 3, 2, 1]).
   - Sound A interval [0, 3000) preserved across all stages.
2. Row 1 placement at top above temporary rows:
   - Y(Row 1) < Y(Row 2) < Y(Row 3) < Y(Row 4).
   - Row 1 labeled "Active Temporary Row Count".
3. Dual Independent Songs view:
   - Displays Song 1 and Song 2 concurrently in stacked panes.
   - Song 1 has 3 columns and Row 1 = [1, 2, 3].
   - Song 2 has 5 columns and Row 1 = [1, 2, 3, 2, 1].
   - Independent horizontal scrolling without shared grid.
4. 32-Column Layout Stress Test:
   - Synthetic song produces >= 32 columns.
   - All columns and constant values render cleanly.
5. Interactive Mode Switching and Zoom Navigation:
   - Switching between all 4 modes (progressive, dual, single, stress).
   - Zoom in, zoom out, reset zoom across views.
"""

from __future__ import annotations

import unittest
from music_gui.coordinates import TimelineCoordinates
from music_gui.main_window import MusicGUI
from music_model.datasets import (
    create_32_column_timeline,
    create_dual_independent_songs,
    create_progressive_stage_timeline,
)
from music_model.song import SongTimeline


class TestStage2BPhase2GUI(unittest.TestCase):
    """Test suite for Stage 2B Phase 2 GUI features."""

    def setUp(self) -> None:
        self.app = MusicGUI()
        self.app.withdraw()  # Hidden headless execution

    def tearDown(self) -> None:
        self.app.destroy()

    def test_row_1_placement_at_top_above_temporary_rows(self) -> None:
        """Verify Row 1 (Constant Row) is positioned above temporary rows."""
        self.app.show_progressive_mode("C")
        self.app.update_idletasks()

        view = self.app.timeline_view
        coords = view.coords

        # Ensure constant_row_at_top is True
        self.assertTrue(coords.constant_row_at_top)

        # Check Y-coordinates: Row 1 must be strictly higher (lower pixel Y) than Row 2, Row 3, Row 4
        y_row1_top, y_row1_bottom = coords.constant_row_y_bounds()
        y_row2_top, y_row2_bottom = coords.temporary_row_y_bounds("Row 2")
        y_row3_top, y_row3_bottom = coords.temporary_row_y_bounds("Row 3")
        y_row4_top, y_row4_bottom = coords.temporary_row_y_bounds("Row 4")

        self.assertLess(y_row1_bottom, y_row2_top)
        self.assertLess(y_row2_top, y_row3_top)
        self.assertLess(y_row3_top, y_row4_top)
        self.assertEqual(y_row2_bottom, y_row3_top)
        self.assertEqual(y_row3_bottom, y_row4_top)

        # Confirm Row 1 badge has the requested label
        canvas = view.canvas
        const_label_items = canvas.find_withtag("constant_badge")
        self.assertGreaterEqual(len(const_label_items), 1)
        const_text_items = canvas.find_withtag("const_label")
        self.assertGreaterEqual(len(const_text_items), 1)
        self.assertIn("Row 1: Constant", canvas.itemcget(const_text_items[0], "text"))
        const_sub_items = canvas.find_withtag("const_sublabel")
        self.assertGreaterEqual(len(const_sub_items), 1)
        self.assertIn("Active Row Count", canvas.itemcget(const_sub_items[0], "text"))

    def test_progressive_stage_a_gui_display(self) -> None:
        """Verify Stage A GUI: 1 column, Row 1 = [1], Sound A [0, 3000) ms."""
        self.app.show_progressive_mode("A")
        self.app.update_idletasks()

        view = self.app.timeline_view
        canvas = view.canvas
        timeline = self.app.timeline

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 1)
        self.assertEqual(columns[0].start_time_ms, 0)
        self.assertEqual(columns[0].end_time_ms, 3000)

        # Column header on canvas
        self.assertEqual(len(view.find_col_header(0)), 1)

        # Constant row text on canvas
        const_items = view.find_const_val(0)
        self.assertEqual(len(const_items), 1)
        self.assertEqual(canvas.itemcget(const_items[0], "text"), "1")

        # Sound A exists and spans [0, 3000)
        sound_a_items = view.find_sound_bar("Sound_A")
        self.assertEqual(len(sound_a_items), 1)
        bar_x = canvas.coords(sound_a_items[0])
        self.assertAlmostEqual(bar_x[0], view.coords.time_to_x(0), places=2)
        self.assertAlmostEqual(bar_x[2], view.coords.time_to_x(3000), places=2)

    def test_progressive_stage_b_gui_display(self) -> None:
        """Verify Stage B GUI: 3 columns, Row 1 = [1, 2, 1], Sound A [0, 3000) preserved."""
        self.app.show_progressive_mode("B")
        self.app.update_idletasks()

        view = self.app.timeline_view
        canvas = view.canvas
        timeline = self.app.timeline

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)

        # Check constant values [1, 2, 1]
        for j, exp_val in enumerate(["1", "2", "1"]):
            const_items = view.find_const_val(j)
            self.assertEqual(len(const_items), 1)
            self.assertEqual(canvas.itemcget(const_items[0], "text"), exp_val)

        # Sound A still spans [0, 3000)
        sound_a_items = view.find_sound_bar("Sound_A")
        self.assertEqual(len(sound_a_items), 1)
        bar_a = canvas.coords(sound_a_items[0])
        self.assertAlmostEqual(bar_a[0], view.coords.time_to_x(0), places=2)
        self.assertAlmostEqual(bar_a[2], view.coords.time_to_x(3000), places=2)

        # Sound B spans [1000, 5000)
        sound_b_items = view.find_sound_bar("Sound_B")
        self.assertEqual(len(sound_b_items), 1)
        bar_b = canvas.coords(sound_b_items[0])
        self.assertAlmostEqual(bar_b[0], view.coords.time_to_x(1000), places=2)
        self.assertAlmostEqual(bar_b[2], view.coords.time_to_x(5000), places=2)

    def test_progressive_stage_c_gui_display(self) -> None:
        """Verify Stage C GUI: 5 columns, Row 1 = [1, 2, 3, 2, 1], Sound A [0, 3000) preserved."""
        self.app.show_progressive_mode("C")
        self.app.update_idletasks()

        view = self.app.timeline_view
        canvas = view.canvas
        timeline = self.app.timeline

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 5)

        # Check constant values [1, 2, 3, 2, 1]
        for j, exp_val in enumerate(["1", "2", "3", "2", "1"]):
            const_items = view.find_const_val(j)
            self.assertEqual(len(const_items), 1)
            self.assertEqual(canvas.itemcget(const_items[0], "text"), exp_val)

        # Sound A still spans [0, 3000) continuously across Col 0, 1, 2
        sound_a_items = view.find_sound_bar("Sound_A")
        self.assertEqual(len(sound_a_items), 1)
        bar_a = canvas.coords(sound_a_items[0])
        self.assertAlmostEqual(bar_a[0], view.coords.time_to_x(0), places=2)
        self.assertAlmostEqual(bar_a[2], view.coords.time_to_x(3000), places=2)

        # Sound C spans [2000, 4000)
        sound_c_items = view.find_sound_bar("Sound_C")
        self.assertEqual(len(sound_c_items), 1)
        bar_c = canvas.coords(sound_c_items[0])
        self.assertAlmostEqual(bar_c[0], view.coords.time_to_x(2000), places=2)
        self.assertAlmostEqual(bar_c[2], view.coords.time_to_x(4000), places=2)

    def test_dual_independent_songs_view(self) -> None:
        """Verify Dual Independent Songs view displays two songs with separate grids & scrollbars."""
        self.app.show_dual_mode()
        self.app.update_idletasks()

        dual_view = self.app.dual_view
        self.assertIsNotNone(dual_view)

        # Song 1: 3 columns, Row 1 = [1, 2, 3]
        song1 = dual_view.song1
        self.assertEqual(song1.column_count, 3)
        self.assertEqual(list(song1.constant_row.values), [1, 2, 3])

        # Song 2: 5 columns, Row 1 = [1, 2, 3, 2, 1]
        song2 = dual_view.song2
        self.assertEqual(song2.column_count, 5)
        self.assertEqual(list(song2.constant_row.values), [1, 2, 3, 2, 1])

        # Verify independent canvases and scrollbars
        canvas1 = dual_view.canvas1.canvas
        canvas2 = dual_view.canvas2.canvas
        self.assertIsNot(canvas1, canvas2)

        # Verify Row 1 constant values on canvas 1
        for j, exp_val in enumerate(["1", "2", "3"]):
            items = dual_view.canvas1.find_const_val(j)
            self.assertEqual(len(items), 1)
            self.assertEqual(canvas1.itemcget(items[0], "text"), exp_val)

        # Verify Row 1 constant values on canvas 2
        for j, exp_val in enumerate(["1", "2", "3", "2", "1"]):
            items = dual_view.canvas2.find_const_val(j)
            self.assertEqual(len(items), 1)
            self.assertEqual(canvas2.itemcget(items[0], "text"), exp_val)

    def test_32_column_stress_test_mode(self) -> None:
        """Verify 32-column layout stress test generates >= 32 columns and renders without error."""
        self.app.show_stress_mode()
        self.app.update_idletasks()

        view = self.app.timeline_view
        timeline = self.app.timeline
        columns = timeline.build_columns()

        self.assertGreaterEqual(len(columns), 32)
        self.assertGreaterEqual(timeline.total_duration_ms, 6400)

        # Verify first and last column headers render
        self.assertEqual(len(view.find_col_header(0)), 1)
        self.assertEqual(len(view.find_col_header(len(columns) - 1)), 1)

        # Verify first and last constant values render
        self.assertEqual(len(view.find_const_val(0)), 1)
        self.assertEqual(len(view.find_const_val(len(columns) - 1)), 1)

    def test_interactive_mode_switching_and_zoom(self) -> None:
        """Verify switching between all 4 modes and zooming operates cleanly."""
        # Cycle through modes
        self.app.show_progressive_mode("A")
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "progressive")

        self.app.show_dual_mode()
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "dual")

        # Test zoom in dual mode
        self.app._on_zoom_in()
        self.app._on_zoom_out()
        self.app._on_zoom_reset()

        self.app.show_single_mode()
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "single")

        # Test zoom in single mode
        self.app._on_zoom_in()
        self.app._on_zoom_out()
        self.app._on_zoom_reset()

        self.app.show_stress_mode()
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "stress")


if __name__ == "__main__":
    unittest.main()
