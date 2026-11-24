"""Automated GUI smoke tests and coordinate verification for Stage 2.

Tests:
1. Exact linear timestamp-to-pixel coordinate mapping.
2. Invariant column duration-to-pixel proportionality.
3. Sound event continuous bar screen span verification.
4. Tkinter MusicGUI smoke test (startup, widget population, clean destruction).
5. Dynamic dataset switching (Stage 1 Proof, Variable-Width Proof, Continuity Proof).
6. Zoom magnification scaling.
"""

from __future__ import annotations

import unittest
from music_gui.coordinates import TimelineCoordinates
from music_gui.main_window import MusicGUI
from music_model.datasets import (
    create_continuity_timeline,
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
)
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline


class TestTimelineCoordinates(unittest.TestCase):
    """Unit tests for layout coordinate calculations."""

    def setUp(self) -> None:
        self.timeline = create_stage_1_proof_timeline()
        self.coords = TimelineCoordinates(self.timeline, base_pixels_per_ms=0.2)

    def test_linear_timestamp_mapping(self) -> None:
        """Verify strict linear 1-to-1 mapping x(t) = x0 + t * s."""
        scale = self.coords.pixels_per_ms
        x0 = self.coords.time_to_x(0)
        x1000 = self.coords.time_to_x(1000)
        x3000 = self.coords.time_to_x(3000)

        self.assertAlmostEqual(x1000 - x0, 1000 * scale, places=4)
        self.assertAlmostEqual(x3000 - x0, 3000 * scale, places=4)

        # Inverse mapping
        self.assertAlmostEqual(self.coords.x_to_time(x0), 0.0, places=4)
        self.assertAlmostEqual(self.coords.x_to_time(x1000), 1000.0, places=4)
        self.assertAlmostEqual(self.coords.x_to_time(x3000), 3000.0, places=4)

    def test_column_proportionality(self) -> None:
        """Verify column pixel widths strictly reflect millisecond durations."""
        var_timeline = create_variable_width_timeline()
        coords = TimelineCoordinates(var_timeline, base_pixels_per_ms=0.1)
        columns = var_timeline.build_columns()

        # Durations are [250, 750, 500, 1000, 500, 1000] ms
        col0_w = coords.column_width(columns[0])  # 250 ms
        col1_w = coords.column_width(columns[1])  # 750 ms
        col2_w = coords.column_width(columns[2])  # 500 ms

        # Proportions: Col 1 should be exactly 3x Col 0; Col 2 should be exactly 2x Col 0
        self.assertAlmostEqual(col1_w / col0_w, 750.0 / 250.0, places=4)
        self.assertAlmostEqual(col2_w / col0_w, 500.0 / 250.0, places=4)

    def test_sound_event_span_matches_duration(self) -> None:
        """Verify sound event bar pixel width matches (end - start) * scale."""
        scale = self.coords.pixels_per_ms
        sound_a = self.timeline.get_event("Sound A")
        self.assertIsNotNone(sound_a)
        assert sound_a is not None

        ex0, ex1 = self.coords.event_x_bounds(sound_a)
        event_w = self.coords.event_width(sound_a)

        self.assertAlmostEqual(ex1 - ex0, event_w, places=4)
        self.assertAlmostEqual(event_w, 3000 * scale, places=4)

    def test_zoom_scaling(self) -> None:
        """Verify zoom scaling scales pixels_per_ms uniformly without altering proportions."""
        orig_scale = self.coords.pixels_per_ms
        self.coords.zoom_in(factor=1.5)
        self.assertAlmostEqual(self.coords.pixels_per_ms, orig_scale * 1.5, places=4)

        self.coords.zoom_out(factor=1.5)
        self.assertAlmostEqual(self.coords.pixels_per_ms, orig_scale, places=4)

        self.coords.reset_zoom()
        self.assertAlmostEqual(self.coords.zoom_level, 1.0, places=4)


class TestGUISmoke(unittest.TestCase):
    """Smoke test running MusicGUI in Tkinter (with window hidden/withdrawn)."""

    def setUp(self) -> None:
        # Create hidden window for headless test execution
        self.app = MusicGUI()
        self.app.withdraw()

    def tearDown(self) -> None:
        self.app.destroy()

    def test_gui_renders_stage_1_proof(self) -> None:
        """Verify canvas elements for Stage 1 Proof (Events A, B, C)."""
        self.app.load_stage_1_proof()
        self.app.update_idletasks()

        view = self.app.timeline_view
        canvas = view.canvas

        # Verify 5 column header boxes exist on canvas
        for j in range(5):
            items = view.find_col_header(j)
            self.assertEqual(len(items), 1, f"Missing canvas item for col_header_{j}")

        # Verify Sound A, B, C bars exist
        for eid in ("Sound A", "Sound B", "Sound C"):
            items = view.find_sound_bar(eid)
            self.assertEqual(len(items), 1, f"Missing canvas item for sound_bar_{eid}")

        # Verify constant row cells and values [1, 2, 3, 2, 1]
        expected_values = ["1", "2", "3", "2", "1"]
        for j, exp_val in enumerate(expected_values):
            items = view.find_const_val(j)
            self.assertEqual(len(items), 1, f"Missing canvas item for const_val_{j}")
            text = canvas.itemcget(items[0], "text")
            self.assertEqual(text, exp_val, f"Col {j} expected {exp_val}, got {text}")

    def test_sound_bar_spans_multiple_columns_continuously(self) -> None:
        """Verify Sound A [0, 3000) renders as a continuous rectangle spanning Col 0, 1, 2."""
        self.app.load_stage_1_proof()
        self.app.update_idletasks()

        view = self.app.timeline_view
        canvas = view.canvas
        coords = view.coords

        # Get Sound A bar bounds
        items = view.find_sound_bar("Sound A")
        self.assertEqual(len(items), 1)
        bar_coords = canvas.coords(items[0])  # [x0, y0, x1, y1]

        expected_x0 = coords.time_to_x(0)
        expected_x1 = coords.time_to_x(3000)

        self.assertAlmostEqual(bar_coords[0], expected_x0, places=2)
        self.assertAlmostEqual(bar_coords[2], expected_x1, places=2)

        # Confirm Sound A spans across the end of Col 0, Col 1, and Col 2
        columns = self.app.timeline.build_columns()
        col0_x1 = coords.column_x_bounds(columns[0])[1]
        col1_x1 = coords.column_x_bounds(columns[1])[1]
        col2_x1 = coords.column_x_bounds(columns[2])[1]

        # bar_coords[0] starts at Col 0 start, bar_coords[2] reaches Col 2 end
        self.assertLess(bar_coords[0], col0_x1)
        self.assertGreater(bar_coords[2], col1_x1)
        self.assertAlmostEqual(bar_coords[2], col2_x1, places=2)

    def test_dynamic_dataset_switching(self) -> None:
        """Verify switching between datasets dynamically updates columns and constant values."""
        view = self.app.timeline_view
        canvas = view.canvas

        # 1. Switch to Variable-Width Proof
        self.app.load_variable_width_proof()
        self.app.update_idletasks()

        # Variable-width proof has 6 columns
        for j in range(6):
            items = view.find_col_header(j)
            self.assertEqual(len(items), 1)

        # Expected constant values: [1, 1, 2, 1, 2, 1]
        expected_var_vals = ["1", "1", "2", "1", "2", "1"]
        for j, exp_val in enumerate(expected_var_vals):
            items = view.find_const_val(j)
            self.assertEqual(len(items), 1)
            self.assertEqual(canvas.itemcget(items[0], "text"), exp_val)

        # 2. Switch to Continuity Proof
        self.app.load_continuity_proof()
        self.app.update_idletasks()

        # Continuity proof has 7 columns and LongSound spanning all 7 columns
        for j in range(7):
            items = view.find_col_header(j)
            self.assertEqual(len(items), 1)

        long_sound_items = view.find_sound_bar("LongSound")
        self.assertEqual(len(long_sound_items), 1)


if __name__ == "__main__":
    unittest.main()
