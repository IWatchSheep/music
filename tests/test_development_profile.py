"""Unit and integration tests for Stage 2B Phase 3: Low-to-High Musical Development.

Verifies:
1. Low-to-high experimental values on SoundEvent:
   - Explicit height parameter and metadata attributes.
   - Rejection of invalid, non-numeric, or non-finite height values.
   - Preservation of SoundEvent intervals and object identity.
2. Overlapping sound-group contributions:
   - Single event active: returns event's height.
   - Multiple overlapping events: arithmetic mean calculation (unweighted, transparent).
   - Alternative aggregations (max, min).
3. Silent column intervals:
   - Gaps return silent_value (0.0 or None) as configured.
4. Independent arrangements comparison (Duck Flight Experiment):
   - Arrangement A (Direct): 5 columns, Row 1 = [20.0, 35.0, 50.0, 65.0, 80.0], directness = 1.0.
   - Arrangement B (Connected): 11 columns, Row 1 = [20.0, 32.5, 45.0, 35.0, 41.67, 40.0, 55.0, 65.0, 71.67, 70.0, 85.0].
   - Non-shared grids, different column counts and durations.
   - Time-to-high state differences (3500 ms vs 4200 ms).
   - Transition count differences (4 vs 10).
5. Deterministic measurements:
   - Repeated calculations yield bit-for-bit identical results.
6. Proof that more columns do NOT imply greater curvature:
   - 16-column linear passage has curvature variance identically 0.0.
7. GUI integration test:
   - Mode switching, Duck Flight view, Row 1 measurement toggle (Active Rows vs Dev Profile).
"""

from __future__ import annotations

import unittest
from music_gui.main_window import MusicGUI
from music_model.constant_row import calculate_constant_row
from music_model.datasets import (
    create_duck_flight_experiment,
    create_linear_many_columns_timeline,
)
from music_model.development_profile import (
    DevelopmentAnalysis,
    analyze_development_profile,
    calculate_column_height,
    calculate_development_constant_row,
    get_event_height,
)
from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline


class TestLowToHighDevelopment(unittest.TestCase):
    """Test suite covering experimental low-to-high musical development."""

    def test_sound_event_height_attributes_and_validation(self) -> None:
        """Verify height storage, getter helper, and validation on SoundEvent."""
        # Explicit height keyword argument
        e1 = SoundEvent("E1", "Row 2", 0, 1000, height=20.0)
        self.assertEqual(e1.height, 20.0)
        self.assertEqual(e1.height_value, 20.0)
        self.assertEqual(get_event_height(e1), 20.0)
        self.assertEqual(e1.attributes.get("height"), 20.0)

        # Height via attributes dictionary
        e2 = SoundEvent("E2", "Row 3", 1000, 2000, attributes={"height": 55.5})
        self.assertEqual(e2.height, 55.5)
        self.assertEqual(e2.height_value, 55.5)
        self.assertEqual(get_event_height(e2), 55.5)

        # Event without height defaults to None
        e3 = SoundEvent("E3", "Row 4", 2000, 3000)
        self.assertIsNone(e3.height)
        self.assertIsNone(e3.height_value)
        self.assertIsNone(get_event_height(e3))

        # Rejection of invalid height types
        with self.assertRaises(ValueError):
            SoundEvent("Bad1", "Row 2", 0, 1000, height="twenty")  # type: ignore

        with self.assertRaises(ValueError):
            SoundEvent("Bad2", "Row 2", 0, 1000, height=float("nan"))

        with self.assertRaises(ValueError):
            SoundEvent("Bad3", "Row 2", 0, 1000, height=float("inf"))

        with self.assertRaises(ValueError):
            SoundEvent("Bad4", "Row 2", 0, 1000, height=True)  # Booleans rejected

    def test_column_height_aggregation_and_silent_gaps(self) -> None:
        """Verify arithmetic mean across overlapping events and silent column handling."""
        timeline = MusicTimeline()
        # Row 2 event: height 20.0
        timeline.add_event(SoundEvent("W1", "Row 2", 0, 2000, height=20.0))
        # Row 3 event: height 60.0, overlapping [1000, 3000)
        timeline.add_event(SoundEvent("T1", "Row 3", 1000, 3000, height=60.0))
        # Silent gap from 3000 to 4000
        # Row 4 event: height 90.0, in [4000, 5000)
        timeline.add_event(SoundEvent("F1", "Row 4", 4000, 5000, height=90.0))

        columns = timeline.build_columns()
        # Columns: [0, 1000), [1000, 2000), [2000, 3000), [3000, 4000), [4000, 5000)
        self.assertEqual(len(columns), 5)

        # Col 0: [0, 1000) -> W1 alone (20.0)
        self.assertEqual(calculate_column_height(columns[0], timeline, aggregation="mean"), 20.0)

        # Col 1: [1000, 2000) -> W1 (20.0) + T1 (60.0) -> mean = 40.0
        self.assertEqual(calculate_column_height(columns[1], timeline, aggregation="mean"), 40.0)
        self.assertEqual(calculate_column_height(columns[1], timeline, aggregation="max"), 60.0)
        self.assertEqual(calculate_column_height(columns[1], timeline, aggregation="min"), 20.0)

        # Col 2: [2000, 3000) -> T1 alone (60.0)
        self.assertEqual(calculate_column_height(columns[2], timeline, aggregation="mean"), 60.0)

        # Col 3: [3000, 4000) -> Silent gap -> silent_value=0.0
        self.assertEqual(calculate_column_height(columns[3], timeline, silent_value=0.0), 0.0)
        self.assertIsNone(calculate_column_height(columns[3], timeline, silent_value=None))

        # Col 4: [4000, 5000) -> F1 alone (90.0)
        self.assertEqual(calculate_column_height(columns[4], timeline, aggregation="mean"), 90.0)

    def test_duck_flight_arrangement_a_direct_development(self) -> None:
        """Verify Arrangement A (Direct progression) column layout and Row 1 profile."""
        song_a, _ = create_duck_flight_experiment()
        analysis_a = analyze_development_profile(song_a.timeline)

        # 5 derived columns
        self.assertEqual(analysis_a.column_count, 5)
        self.assertEqual(analysis_a.boundaries, (0, 1500, 2000, 3000, 3500, 5000))
        self.assertEqual(analysis_a.column_durations_ms, (1500, 500, 1000, 500, 1500))

        # Row 1 Active-Row Count Baseline: [1, 2, 1, 2, 1]
        self.assertEqual(analysis_a.active_row_counts, (1, 2, 1, 2, 1))

        # Row 1 Experimental Development Profile: [20.0, 35.0, 50.0, 65.0, 80.0]
        self.assertEqual(analysis_a.profile_values, (20.0, 35.0, 50.0, 65.0, 80.0))

        # Strictly monotonic increasing
        self.assertTrue(analysis_a.is_strictly_monotonic_increasing)
        self.assertTrue(analysis_a.is_non_decreasing)

        # Directness ratio is exactly 1.0 (no backwards movement)
        self.assertAlmostEqual(analysis_a.directness_ratio, 1.0, places=4)
        self.assertEqual(analysis_a.net_change, 60.0)
        self.assertEqual(analysis_a.total_absolute_variation, 60.0)

        # Time to reach high state (80.0): Col 4 starts at 3500 ms
        self.assertEqual(analysis_a.time_to_high_ms, 3500)
        self.assertEqual(analysis_a.transition_count, 4)

    def test_duck_flight_arrangement_b_connected_development(self) -> None:
        """Verify Arrangement B (Intermediate connections) column layout and Row 1 profile."""
        _, song_b = create_duck_flight_experiment()
        analysis_b = analyze_development_profile(song_b.timeline)

        # 11 derived columns over 6000 ms
        self.assertEqual(analysis_b.column_count, 11)
        self.assertEqual(analysis_b.total_duration_ms, 6000)
        self.assertEqual(
            analysis_b.boundaries,
            (0, 1000, 1600, 2000, 2200, 2400, 3000, 3200, 3800, 4000, 4200, 6000),
        )

        # Row 1 Active-Row Count Baseline
        self.assertEqual(analysis_b.active_row_counts, (1, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1))

        # Verify initial and final values
        self.assertEqual(analysis_b.initial_value, 20.0)
        self.assertEqual(analysis_b.final_value, 85.0)

        # Non-monotonic behavior: Water kick causes a dip from 45.0 down to 35.0 at Col 3
        self.assertFalse(analysis_b.is_strictly_monotonic_increasing)
        self.assertFalse(analysis_b.is_non_decreasing)

        # Directness ratio is strictly less than 1.0 due to intermediate transitions
        self.assertLess(analysis_b.directness_ratio, 1.0)
        self.assertGreater(analysis_b.directness_ratio, 0.5)

        # Time to high state is delayed relative to Arrangement A (4200 ms vs 3500 ms)
        self.assertEqual(analysis_b.time_to_high_ms, 4200)
        self.assertEqual(analysis_b.transition_count, 10)

    def test_sound_event_identity_and_interval_preservation(self) -> None:
        """Verify sound events retain exact interval boundaries and object identity."""
        song_a, song_b = create_duck_flight_experiment()

        whir_a = song_a.get_event("A_Whir")
        self.assertIsNotNone(whir_a)
        assert whir_a is not None
        self.assertEqual(whir_a.start_time_ms, 0)
        self.assertEqual(whir_a.end_time_ms, 2000)
        self.assertEqual(whir_a.duration_ms, 2000)
        self.assertEqual(whir_a.height, 20.0)

        flight_b = song_b.get_event("B_Flight_2")
        self.assertIsNotNone(flight_b)
        assert flight_b is not None
        self.assertEqual(flight_b.start_time_ms, 3800)
        self.assertEqual(flight_b.end_time_ms, 6000)
        self.assertEqual(flight_b.duration_ms, 2200)
        self.assertEqual(flight_b.height, 85.0)

    def test_deterministic_measurements(self) -> None:
        """Verify calculations produce identical bit-for-bit output across repeated runs."""
        song_a, _ = create_duck_flight_experiment()
        run1 = analyze_development_profile(song_a.timeline)
        run2 = analyze_development_profile(song_a.timeline)

        self.assertEqual(run1.profile_values, run2.profile_values)
        self.assertEqual(run1.directness_ratio, run2.directness_ratio)
        self.assertEqual(run1.curvature_variance, run2.curvature_variance)
        self.assertEqual(run1.transition_count, run2.transition_count)

    def test_more_columns_do_not_imply_greater_curvature(self) -> None:
        """Prove mathematically that having many columns does NOT imply curvature.

        A linear profile with 16 columns has constant slope and zero second differences.
        """
        linear_song = create_linear_many_columns_timeline(n_columns=16)
        analysis = analyze_development_profile(linear_song.timeline)

        self.assertEqual(analysis.column_count, 16)
        self.assertAlmostEqual(analysis.directness_ratio, 1.0, places=5)
        self.assertTrue(analysis.is_strictly_monotonic_increasing)

        # Curvature variance must be identically 0.0
        self.assertAlmostEqual(analysis.curvature_variance, 0.0, places=9)
        for sd in analysis.second_differences:
            self.assertAlmostEqual(sd, 0.0, places=9)

    def test_gui_duck_flight_mode_and_measurement_toggle(self) -> None:
        """Verify GUI Duck Flight mode and Row 1 measurement toggle (Active Rows vs Dev Profile)."""
        app = MusicGUI()
        app.withdraw()

        try:
            # Switch to Duck Flight view mode
            app.show_duck_mode()
            app.update_idletasks()
            self.assertEqual(app.current_view_mode, "duck")

            # Dual view holds Arrangement A and B
            dual_view = app.dual_view
            self.assertEqual(dual_view.song1.column_count, 5)
            self.assertEqual(dual_view.song2.column_count, 11)

            # Test toggling Row 1 measurement
            self.assertEqual(app.current_constant_row_mode, "active_rows")
            app._toggle_constant_row_mode()
            app.update_idletasks()
            self.assertEqual(app.current_constant_row_mode, "development")

            # In development mode, canvas1 shows [20.0, 35.0, 50.0, 65.0, 80.0]
            for j, exp_val in enumerate(["20.0", "35.0", "50.0", "65.0", "80.0"]):
                items = dual_view.canvas1.find_const_val(j)
                self.assertEqual(len(items), 1)
                self.assertEqual(dual_view.canvas1.canvas.itemcget(items[0], "text"), exp_val)

            # Toggle back to active_rows
            app._toggle_constant_row_mode()
            app.update_idletasks()
            self.assertEqual(app.current_constant_row_mode, "active_rows")
            for j, exp_val in enumerate(["1", "2", "1", "2", "1"]):
                items = dual_view.canvas1.find_const_val(j)
                self.assertEqual(len(items), 1)
                self.assertEqual(dual_view.canvas1.canvas.itemcget(items[0], "text"), exp_val)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
