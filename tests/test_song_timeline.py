"""Unit tests for SongTimeline and ProgressiveRefitter.

Verifies:
1. Sequential progressive column refitting across Stage A, Stage B, and Stage C.
2. Intermediate boundaries, column counts, and column intervals at each step.
3. SoundEvent identity and duration preservation throughout refitting.
4. Constant row (Row 1) dynamic recalculation at each progressive stage.
5. Strict isolation between independent SongTimeline instances (no shared state/grid).
6. ID collision isolation between independent songs (same row_id or event_id allowed across songs).
7. Duplicate event/row rejection within a single song.
8. Empty song behavior.
9. Deterministic boundary and column derivation.
"""

from __future__ import annotations

import unittest
from music_model.song import ProgressiveRefitter, SongTimeline
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow


class TestSongTimelineAndProgressiveRefitting(unittest.TestCase):
    """Test suite covering SongTimeline and ProgressiveRefitter."""

    def test_progressive_refitting_sequence(self) -> None:
        """Verify the exact 3-stage progressive refitting sequence from the specification."""
        song = SongTimeline("song_1", "Progressive Refitting Song")
        refitter = ProgressiveRefitter(song)

        sound_a = SoundEvent("Sound A", "Row 2", 0, 3000, label="Low sound")
        sound_b = SoundEvent("Sound B", "Row 3", 1000, 5000, label="Second layer")
        sound_c = SoundEvent("Sound C", "Row 4", 2000, 4000, label="Higher layer")

        # Stage A: Add Row 2 only
        step_a = refitter.add_temporary_row_with_events("Row 2", [sound_a], row_label="Bass Group")
        self.assertEqual(step_a.step_index, 0)
        self.assertEqual(step_a.boundaries, (0, 3000))
        self.assertEqual(step_a.column_count, 1)
        self.assertEqual(step_a.constant_row.values, (1,))
        self.assertEqual(step_a.columns[0].active_event_ids, ("Sound A",))
        self.assertEqual(step_a.columns[0].active_row_ids, ("Row 2",))

        # Stage B: Add Row 3 -> Causes columns to refit
        step_b = refitter.add_temporary_row_with_events("Row 3", [sound_b], row_label="Melody Group")
        self.assertEqual(step_b.step_index, 1)
        self.assertEqual(step_b.boundaries, (0, 1000, 3000, 5000))
        self.assertEqual(step_b.column_count, 3)
        self.assertEqual(step_b.constant_row.values, (1, 2, 1))

        # Check the 3 refitted intervals: [0, 1000), [1000, 3000), [3000, 5000)
        self.assertEqual(step_b.columns[0].start_time_ms, 0)
        self.assertEqual(step_b.columns[0].end_time_ms, 1000)
        self.assertEqual(step_b.columns[0].active_event_ids, ("Sound A",))
        self.assertEqual(step_b.columns[0].active_row_ids, ("Row 2",))

        self.assertEqual(step_b.columns[1].start_time_ms, 1000)
        self.assertEqual(step_b.columns[1].end_time_ms, 3000)
        self.assertEqual(step_b.columns[1].active_event_ids, ("Sound A", "Sound B"))
        self.assertEqual(step_b.columns[1].active_row_ids, ("Row 2", "Row 3"))

        self.assertEqual(step_b.columns[2].start_time_ms, 3000)
        self.assertEqual(step_b.columns[2].end_time_ms, 5000)
        self.assertEqual(step_b.columns[2].active_event_ids, ("Sound B",))
        self.assertEqual(step_b.columns[2].active_row_ids, ("Row 3",))

        # Stage C: Add Row 4 -> Causes columns to refit again
        step_c = refitter.add_temporary_row_with_events("Row 4", [sound_c], row_label="Harmony Group")
        self.assertEqual(step_c.step_index, 2)
        self.assertEqual(step_c.boundaries, (0, 1000, 2000, 3000, 4000, 5000))
        self.assertEqual(step_c.column_count, 5)
        self.assertEqual(step_c.constant_row.values, (1, 2, 3, 2, 1))

        # Verify all 5 columns in final state
        expected_intervals = [(0, 1000), (1000, 2000), (2000, 3000), (3000, 4000), (4000, 5000)]
        expected_counts = (1, 2, 3, 2, 1)
        for col, (start, end), exp_count in zip(step_c.columns, expected_intervals, expected_counts):
            self.assertEqual(col.start_time_ms, start)
            self.assertEqual(col.end_time_ms, end)
            self.assertEqual(col.duration_ms, end - start)
            self.assertEqual(step_c.constant_row[col.index], exp_count)

    def test_sound_event_identity_and_duration_preservation(self) -> None:
        """Verify Sound A retains its exact interval and object identity throughout all refits."""
        song = SongTimeline("song_id_test", "Identity Preservation Test")
        refitter = ProgressiveRefitter(song)

        sound_a = SoundEvent("Sound A", "Row 2", 0, 3000, label="Low sound")
        sound_b = SoundEvent("Sound B", "Row 3", 1000, 5000, label="Second layer")
        sound_c = SoundEvent("Sound C", "Row 4", 2000, 4000, label="Higher layer")

        # Step 1
        refitter.add_temporary_row_with_events("Row 2", [sound_a])
        self.assertEqual(sound_a.start_time_ms, 0)
        self.assertEqual(sound_a.end_time_ms, 3000)
        self.assertEqual(sound_a.duration_ms, 3000)

        # Step 2
        refitter.add_temporary_row_with_events("Row 3", [sound_b])
        # Sound A must be identical
        self.assertEqual(sound_a.start_time_ms, 0)
        self.assertEqual(sound_a.end_time_ms, 3000)
        self.assertEqual(sound_a.duration_ms, 3000)
        stored_a = song.get_event("Sound A")
        self.assertIs(stored_a, sound_a)

        # Step 3
        refitter.add_temporary_row_with_events("Row 4", [sound_c])
        self.assertEqual(sound_a.start_time_ms, 0)
        self.assertEqual(sound_a.end_time_ms, 3000)
        self.assertEqual(sound_a.duration_ms, 3000)
        self.assertIs(song.get_event("Sound A"), sound_a)
        self.assertIs(song.get_event("Sound B"), sound_b)
        self.assertIs(song.get_event("Sound C"), sound_c)

    def test_independent_song_timelines_no_grid_sharing(self) -> None:
        """Verify two songs calculate columns independently without sharing grids or state."""
        song1 = SongTimeline("song_classical", "Classical Excerpt (Wagner)", tempo_bpm=120.0)
        song2 = SongTimeline("song_modern", "Modern Excerpt (Multi-Style)", tempo_bpm=95.0)

        # Song 1: 3 boundaries -> 2 columns
        song1.add_event(SoundEvent("E1", "Row 2", 0, 2000))
        song1.add_event(SoundEvent("E2", "Row 3", 1000, 2000))

        # Song 2: 5 boundaries -> 4 columns with completely different timestamps
        song2.add_event(SoundEvent("M1", "Row 2", 250, 1500))
        song2.add_event(SoundEvent("M2", "Row 3", 500, 2500))
        song2.add_event(SoundEvent("M3", "Row 4", 1000, 1750))

        # Check boundaries are completely independent
        self.assertEqual(song1.extract_boundaries(), (0, 1000, 2000))
        self.assertEqual(song1.column_count, 2)
        self.assertEqual(song1.constant_row.values, (1, 2))

        self.assertEqual(song2.extract_boundaries(), (250, 500, 1000, 1500, 1750, 2500))
        self.assertEqual(song2.column_count, 5)
        self.assertEqual(song2.constant_row.values, (1, 2, 3, 2, 1))

        # Modifying Song 2 must have zero effect on Song 1
        song2.add_event(SoundEvent("M4", "Row 5", 3000, 4000))
        self.assertEqual(song2.column_count, 7)
        self.assertEqual(song1.extract_boundaries(), (0, 1000, 2000))
        self.assertEqual(song1.column_count, 2)
        self.assertEqual(song1.constant_row.values, (1, 2))

    def test_id_isolation_between_songs(self) -> None:
        """Verify identical row_ids and event_ids in different songs do not collide."""
        song1 = SongTimeline("s1", "Song 1")
        song2 = SongTimeline("s2", "Song 2")

        # Both songs have 'Row 2' and 'Sound A' with different timings
        song1.add_event(SoundEvent("Sound A", "Row 2", 0, 1000))
        song2.add_event(SoundEvent("Sound A", "Row 2", 500, 2500))

        self.assertEqual(song1.get_event("Sound A").duration_ms, 1000)  # type: ignore[union-attr]
        self.assertEqual(song2.get_event("Sound A").duration_ms, 2000)  # type: ignore[union-attr]

    def test_duplicate_ids_rejected_within_same_song(self) -> None:
        """Verify duplicate event IDs inside the same song raise ValueError."""
        song = SongTimeline("s1", "Song 1")
        song.add_event(SoundEvent("E1", "Row 2", 0, 1000))
        with self.assertRaises(ValueError):
            song.add_event(SoundEvent("E1", "Row 3", 1000, 2000))

    def test_empty_song_behavior(self) -> None:
        """Verify empty song returns empty boundaries and 0 columns without crashing."""
        song = SongTimeline("empty_song", "Empty Song")
        self.assertEqual(song.extract_boundaries(), ())
        self.assertEqual(song.build_columns(), ())
        self.assertEqual(song.column_count, 0)
        self.assertEqual(song.constant_row.values, ())
        self.assertEqual(song.total_duration_ms, 0)

    def test_refitter_intermediate_inspection(self) -> None:
        """Verify every intermediate refitting state can be inspected individually."""
        refitter = ProgressiveRefitter()
        refitter.add_temporary_row_with_events("Row 2", [SoundEvent("A", "Row 2", 0, 1000)])
        refitter.add_temporary_row_with_events("Row 3", [SoundEvent("B", "Row 3", 500, 1500)])
        refitter.add_temporary_row_with_events("Row 4", [SoundEvent("C", "Row 4", 1000, 2000)])

        self.assertEqual(refitter.step_count, 3)

        # Inspect Step 0 (1 column)
        step0 = refitter.get_step(0)
        self.assertEqual(step0.column_count, 1)
        self.assertEqual(step0.boundaries, (0, 1000))

        # Inspect Step 1 (3 columns: [0, 500), [500, 1000), [1000, 1500))
        step1 = refitter.get_step(1)
        self.assertEqual(step1.column_count, 3)
        self.assertEqual(step1.boundaries, (0, 500, 1000, 1500))

        # Inspect Step 2 (4 columns: [0, 500), [500, 1000), [1000, 1500), [1500, 2000))
        step2 = refitter.get_step(2)
        self.assertEqual(step2.column_count, 4)
        self.assertEqual(step2.boundaries, (0, 500, 1000, 1500, 2000))

    def test_deterministic_boundary_derivation(self) -> None:
        """Verify boundary derivation produces identical output regardless of run count."""
        song = SongTimeline("det_song", "Deterministic Song")
        song.add_event(SoundEvent("E3", "Row 4", 2000, 4000))
        song.add_event(SoundEvent("E1", "Row 2", 0, 3000))
        song.add_event(SoundEvent("E2", "Row 3", 1000, 5000))

        for _ in range(5):
            self.assertEqual(song.extract_boundaries(), (0, 1000, 2000, 3000, 4000, 5000))
            self.assertEqual(song.constant_row.values, (1, 2, 3, 2, 1))


if __name__ == "__main__":
    unittest.main()
