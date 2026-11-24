"""Automated unit tests for Music Project Stage 1 data model.

Verifies:
1. One event creating one time column.
2. The full A/B/C mathematical proof.
3. Multiple sounds beginning simultaneously.
4. Multiple sounds ending simultaneously.
5. Two sounds touching without overlapping.
6. A silent gap between sounds.
7. Multiple events in the same temporary row.
8. Overlapping events within the same row.
9. Duplicate event IDs.
10. Negative start time.
11. Zero-duration sound.
12. End time before start time.
13. Invalid or non-finite timestamps.
14. Variable-width columns.
15. Sound events spanning multiple columns without being duplicated.
16. Reproducible output ordering.
17. Empty timeline behavior.
18. Distinct active row count vs. active event count.
19. Mismatched row IDs rejected by TemporaryRow.
"""

from __future__ import annotations

import unittest
from music_model.constant_row import (
    calculate_constant_row,
    count_active_events,
    count_distinct_active_rows,
)
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow
from music_model.timeline import MusicTimeline, TimeColumn


class TestMusicTimelineModel(unittest.TestCase):
    """Test suite covering sound events, temporary rows, timeline, and constant rows."""

    def test_01_one_event_one_column(self) -> None:
        """1. One event creates exactly one time column covering its interval."""
        timeline = MusicTimeline()
        event = SoundEvent("E1", "Row1", 500, 1500, label="Single Sound")
        timeline.add_event(event)

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (500, 1500))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 1)

        col = columns[0]
        self.assertEqual(col.index, 0)
        self.assertEqual(col.start_time_ms, 500)
        self.assertEqual(col.end_time_ms, 1500)
        self.assertEqual(col.duration_ms, 1000)
        self.assertEqual(col.active_event_ids, ("E1",))
        self.assertEqual(col.active_row_ids, ("Row1",))

        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1,))

    def test_02_full_abc_mathematical_proof(self) -> None:
        """2. Full A/B/C mathematical proof from Stage 0.

        Sound A: [0, 3000) on Row A
        Sound B: [1000, 5000) on Row B
        Sound C: [2000, 4000) on Row C
        Expected boundaries: [0, 1000, 2000, 3000, 4000, 5000]
        Expected constant row: [1, 2, 3, 2, 1]
        """
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("A", "Row A", 0, 3000))
        timeline.add_event(SoundEvent("B", "Row B", 1000, 5000))
        timeline.add_event(SoundEvent("C", "Row C", 2000, 4000))

        self.assertEqual(timeline.extract_boundaries(), (0, 1000, 2000, 3000, 4000, 5000))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 5)

        expected_data = [
            (0, 0, 1000, ("A",), ("Row A",)),
            (1, 1000, 2000, ("A", "B"), ("Row A", "Row B")),
            (2, 2000, 3000, ("A", "B", "C"), ("Row A", "Row B", "Row C")),
            (3, 3000, 4000, ("B", "C"), ("Row B", "Row C")),
            (4, 4000, 5000, ("B",), ("Row B",)),
        ]

        for col, (idx, start, end, exp_events, exp_rows) in zip(columns, expected_data):
            self.assertEqual(col.index, idx)
            self.assertEqual(col.start_time_ms, start)
            self.assertEqual(col.end_time_ms, end)
            self.assertEqual(col.active_event_ids, exp_events)
            self.assertEqual(col.active_row_ids, exp_rows)

        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1, 2, 3, 2, 1))

    def test_03_multiple_sounds_simultaneous_starts(self) -> None:
        """3. Multiple sounds beginning simultaneously create one shared start boundary."""
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("E1", "Row1", 1000, 2000))
        timeline.add_event(SoundEvent("E2", "Row2", 1000, 3000))
        timeline.add_event(SoundEvent("E3", "Row3", 1000, 4000))

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (1000, 2000, 3000, 4000))
        self.assertEqual(len(boundaries), 4)

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)
        self.assertEqual(columns[0].active_event_ids, ("E1", "E2", "E3"))
        self.assertEqual(columns[1].active_event_ids, ("E2", "E3"))
        self.assertEqual(columns[2].active_event_ids, ("E3",))

    def test_04_multiple_sounds_simultaneous_ends(self) -> None:
        """4. Multiple sounds ending simultaneously create one shared end boundary."""
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("E1", "Row1", 1000, 5000))
        timeline.add_event(SoundEvent("E2", "Row2", 2000, 5000))
        timeline.add_event(SoundEvent("E3", "Row3", 3000, 5000))

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (1000, 2000, 3000, 5000))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)
        self.assertEqual(columns[0].active_event_ids, ("E1",))
        self.assertEqual(columns[1].active_event_ids, ("E1", "E2"))
        self.assertEqual(columns[2].active_event_ids, ("E1", "E2", "E3"))

    def test_05_two_sounds_touching_without_overlapping(self) -> None:
        """5. Two sounds touching at a boundary [0, 1000) and [1000, 2000) do not overlap."""
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("A", "Row1", 0, 1000))
        timeline.add_event(SoundEvent("B", "Row2", 1000, 2000))

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (0, 1000, 2000))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 2)

        # Col 0: only A is active
        self.assertEqual(columns[0].active_event_ids, ("A",))
        # Col 1: only B is active
        self.assertEqual(columns[1].active_event_ids, ("B",))

        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1, 1))

    def test_06_silent_gap_between_sounds(self) -> None:
        """6. A gap between sounds creates a valid column with zero active rows."""
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("A", "Row1", 0, 1000))
        timeline.add_event(SoundEvent("B", "Row2", 2000, 3000))

        boundaries = timeline.extract_boundaries()
        self.assertEqual(boundaries, (0, 1000, 2000, 3000))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)

        # Col 1 is the gap [1000, 2000)
        gap_col = columns[1]
        self.assertEqual(gap_col.start_time_ms, 1000)
        self.assertEqual(gap_col.end_time_ms, 2000)
        self.assertEqual(gap_col.duration_ms, 1000)
        self.assertEqual(gap_col.active_event_ids, ())
        self.assertEqual(gap_col.active_row_ids, ())
        self.assertTrue(gap_col.is_silent_gap)
        self.assertFalse(gap_col.has_active_sounds)

        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1, 0, 1))

    def test_07_multiple_events_same_temporary_row(self) -> None:
        """7. Multiple sequential sound events can reside in the same temporary row."""
        timeline = MusicTimeline()
        row = TemporaryRow("RhythmRow", label="Percussion Track")
        row.add_event(SoundEvent("Hit1", "RhythmRow", 0, 500))
        row.add_event(SoundEvent("Hit2", "RhythmRow", 1000, 1500))
        row.add_event(SoundEvent("Hit3", "RhythmRow", 2000, 2500))
        timeline.add_row(row)

        self.assertEqual(len(row), 3)
        self.assertEqual(row.earliest_start_ms, 0)
        self.assertEqual(row.latest_end_ms, 2500)

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 5)
        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1, 0, 1, 0, 1))

    def test_08_overlapping_events_within_same_row(self) -> None:
        """8. Multiple events within the same row may overlap without error."""
        row = TemporaryRow("PadRow")
        row.add_event(SoundEvent("Note1", "PadRow", 0, 2000))
        row.add_event(SoundEvent("Note2", "PadRow", 1000, 3000))
        self.assertEqual(len(row), 2)

        timeline = MusicTimeline()
        timeline.add_row(row)

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)

        # In interval [1000, 2000), both Note1 and Note2 are active, but they belong to 1 row
        self.assertEqual(columns[1].active_event_ids, ("Note1", "Note2"))
        self.assertEqual(columns[1].active_row_ids, ("PadRow",))

        # Active row count must be 1, not 2
        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, (1, 1, 1))

        # Event count measurement yields 2 in middle column
        event_count_row = calculate_constant_row(
            timeline, measurement_fn=count_active_events, measurement_name="Active Event Count"
        )
        self.assertEqual(event_count_row.values, (1, 2, 1))

    def test_09_duplicate_event_ids_rejected(self) -> None:
        """9. Duplicate event IDs are rejected both in TemporaryRow and in MusicTimeline."""
        row = TemporaryRow("Row1")
        row.add_event(SoundEvent("E1", "Row1", 0, 1000))
        with self.assertRaises(ValueError):
            row.add_event(SoundEvent("E1", "Row1", 2000, 3000))

        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("GlobalID", "RowA", 0, 1000))
        # Adding same event_id on different row must be rejected
        with self.assertRaises(ValueError):
            timeline.add_event(SoundEvent("GlobalID", "RowB", 2000, 3000))

    def test_10_negative_start_time_rejected(self) -> None:
        """10. Negative start time raises ValueError."""
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", -100, 1000)

    def test_11_zero_duration_sound_rejected(self) -> None:
        """11. Zero-duration sound (start == end) raises ValueError."""
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", 1000, 1000)

    def test_12_end_time_before_start_time_rejected(self) -> None:
        """12. End time before start time raises ValueError."""
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", 2000, 1000)

    def test_13_invalid_or_non_finite_timestamps_rejected(self) -> None:
        """13. Non-finite or non-integer timestamps raise ValueError."""
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", float("nan"), 1000)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", 0, float("inf"))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", 0.5, 1000)  # Fractional milliseconds rejected
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", True, 1000)  # Booleans rejected
        with self.assertRaises(ValueError):
            SoundEvent("E1", "Row1", "0", 1000)  # type: ignore[arg-type]

    def test_14_variable_width_columns(self) -> None:
        """14. Variable-width columns reflect event boundaries with different durations."""
        timeline = MusicTimeline()
        timeline.add_event(SoundEvent("E1", "R1", 0, 250))
        timeline.add_event(SoundEvent("E2", "R2", 250, 1500))
        timeline.add_event(SoundEvent("E3", "R3", 1500, 3500))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 3)

        durations = [c.duration_ms for c in columns]
        self.assertEqual(durations, [250, 1250, 2000])

    def test_15_sound_spanning_multiple_columns_not_duplicated(self) -> None:
        """15. A long sound spanning several columns remains a single object in the row."""
        timeline = MusicTimeline()
        long_event = SoundEvent("Long", "R1", 0, 4000)
        timeline.add_event(long_event)

        # Boundaries created: {0, 4000} U {1000, 2000} U {2500, 3000} -> {0, 1000, 2000, 2500, 3000, 4000} (6 boundaries, 5 columns)
        timeline.add_event(SoundEvent("Short1", "R2", 1000, 2000))
        timeline.add_event(SoundEvent("Short2", "R3", 2500, 3000))

        columns = timeline.build_columns()
        self.assertEqual(len(columns), 5)

        # Verify event presence across all 5 columns covering [0, 4000)
        for col in columns:
            self.assertIn("Long", col.active_event_ids)

        # Verify object identity in row: exactly one event object
        row1 = timeline.get_row("R1")
        self.assertIsNotNone(row1)
        self.assertEqual(len(row1), 1)
        self.assertIs(row1.events[0], long_event)

    def test_16_reproducible_output_ordering(self) -> None:
        """16. Output ordering is deterministic and independent of insertion order."""
        events = [
            SoundEvent("C", "RowC", 2000, 4000),
            SoundEvent("A", "RowA", 0, 3000),
            SoundEvent("B", "RowB", 1000, 5000),
        ]

        t1 = MusicTimeline()
        for e in events:
            t1.add_event(e)

        t2 = MusicTimeline()
        for e in reversed(events):
            t2.add_event(e)

        self.assertEqual(t1.extract_boundaries(), t2.extract_boundaries())
        c1 = calculate_constant_row(t1)
        c2 = calculate_constant_row(t2)
        self.assertEqual(c1.values, c2.values)

        for col1, col2 in zip(t1.build_columns(), t2.build_columns()):
            self.assertEqual(col1.active_event_ids, col2.active_event_ids)
            self.assertEqual(col1.active_row_ids, col2.active_row_ids)

    def test_17_empty_timeline_behavior(self) -> None:
        """17. Empty timeline returns empty boundaries, columns, and constant row without error."""
        timeline = MusicTimeline()
        self.assertEqual(timeline.extract_boundaries(), ())
        self.assertEqual(timeline.build_columns(), ())
        self.assertEqual(timeline.total_duration_ms, 0)

        constant_row = calculate_constant_row(timeline)
        self.assertEqual(constant_row.values, ())
        self.assertEqual(constant_row.column_count, 0)
        self.assertTrue(constant_row.is_empty)

    def test_18_distinct_active_row_count_vs_active_event_count(self) -> None:
        """18. Explicitly verify distinct active row count vs event count."""
        timeline = MusicTimeline()
        # Row 1 has 3 overlapping sounds
        timeline.add_event(SoundEvent("R1_E1", "Row1", 0, 3000))
        timeline.add_event(SoundEvent("R1_E2", "Row1", 500, 2500))
        timeline.add_event(SoundEvent("R1_E3", "Row1", 1000, 2000))
        # Row 2 has 1 sound
        timeline.add_event(SoundEvent("R2_E1", "Row2", 500, 2500))

        # At interval [1000, 2000), there are 4 active events (3 on Row 1, 1 on Row 2),
        # but exactly 2 distinct active rows (Row1, Row2).
        columns = timeline.build_columns()
        col_1000_2000 = [c for c in columns if c.start_time_ms == 1000 and c.end_time_ms == 2000][0]

        self.assertEqual(col_1000_2000.active_event_count, 4)
        self.assertEqual(col_1000_2000.active_row_count, 2)

        # Stage 1 default constant row must count rows:
        constant_row = calculate_constant_row(timeline)
        idx = col_1000_2000.index
        self.assertEqual(constant_row[idx], 2)

    def test_19_mismatched_row_id_rejected(self) -> None:
        """19. TemporaryRow rejects sound event with mismatched row_id."""
        row = TemporaryRow("GuitarRow")
        event = SoundEvent("E1", "BassRow", 0, 1000)
        with self.assertRaises(ValueError):
            row.add_event(event)


if __name__ == "__main__":
    unittest.main()
