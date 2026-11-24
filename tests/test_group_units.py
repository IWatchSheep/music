"""
tests/test_group_units.py - Automated Unit Tests for Milestone 4A (Statement 18).

Verifies:
1. FundamentalGrid cyclic 0-9 indexing and cell uniformity.
2. Group spans across fundamental units (4-unit and 3-unit).
3. Exact row boundaries and combined boundary derivation.
4. Row 1 composite segment widths [3, 1, 2, 2, 1, 3].
5. Non-destruction: 12 fundamental cells remain unchanged.
6. Multi-dimensional development: ascending vs. flat control comparison.
7. Sound preservation: float input preservation and exact rational precision.
8. Two-song independence: different u and cell counts without cross-talk.
9. Meeting points: boundary hand-offs where sound groups transition.
"""

from fractions import Fraction
import unittest
from verify_group_units import (
    FundamentalGrid,
    SoundGroup,
    NoteEvent,
    GroupTimeline,
    build_ascending_passage,
    build_flat_control_passage,
    build_song_2_independent,
)


class TestFundamentalGridAndGroupUnits(unittest.TestCase):
    def test_fundamental_grid_cyclic_labels(self):
        """Verify fundamental grid has uniform duration and cyclic 0-9 labels."""
        grid = FundamentalGrid(u_ms=100, total_cells=12)
        expected_labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1]
        actual_labels = [grid.cell_label(i) for i in range(12)]
        self.assertEqual(actual_labels, expected_labels)
        for i in range(12):
            start, end = grid.cell_span_ms(i)
            self.assertEqual(end - start, 100)

    def test_statement_18_group_widths(self):
        """Verify Row 2 has 4-unit groups and Row 3 has 3-unit groups."""
        song = build_ascending_passage(u_ms=100)
        r2_groups = song.groups_by_row["Row 2 (Low Whirring)"]
        r3_groups = song.groups_by_row["Row 3 (Ascending Flight)"]

        self.assertEqual(len(r2_groups), 3)
        for g in r2_groups:
            self.assertEqual(g.width_units, 4)
            self.assertEqual(g.end_time_ms(100) - g.start_time_ms(100), 400.0)

        self.assertEqual(len(r3_groups), 4)
        for g in r3_groups:
            self.assertEqual(g.width_units, 3)
            self.assertEqual(g.end_time_ms(100) - g.start_time_ms(100), 300.0)

    def test_row_boundaries_derivation(self):
        """Verify row boundaries match Statement 18 specification."""
        song = build_ascending_passage(u_ms=100)
        r2_bounds = song.row_boundaries("Row 2 (Low Whirring)")
        r3_bounds = song.row_boundaries("Row 3 (Ascending Flight)")

        self.assertEqual(r2_bounds, [0, 4, 8, 12])
        self.assertEqual(r3_bounds, [0, 3, 6, 9, 12])

    def test_combined_boundaries_and_row1_segments(self):
        """Verify combined boundary set and Row 1 segment widths [3, 1, 2, 2, 1, 3]."""
        song = build_ascending_passage(u_ms=100)
        comb_bounds = song.combined_boundaries()
        self.assertEqual(comb_bounds, [0, 3, 4, 6, 8, 9, 12])

        segments = song.derive_row1_segments()
        self.assertEqual(len(segments), 6)
        widths = [s.width_units for s in segments]
        self.assertEqual(widths, [3, 1, 2, 2, 1, 3])
        self.assertEqual(sum(widths), 12)

        # Underlying 12 cells check
        self.assertEqual(song.grid.total_cells, 12)

    def test_ascending_vs_flat_control_comparison(self):
        """Verify algorithm distinguishes ascending passage from flat control passage."""
        asc_song = build_ascending_passage(u_ms=100)
        flat_song = build_flat_control_passage(u_ms=100)

        asc_segs = asc_song.derive_row1_segments()
        flat_segs = flat_song.derive_row1_segments()

        asc_pitches = [s.mean_pitch for s in asc_segs]
        flat_pitches = [s.mean_pitch for s in flat_segs]

        # Ascending passage rises monotonically
        self.assertGreater(asc_pitches[-1], asc_pitches[0])
        self.assertEqual(asc_pitches, [48.0, 51.5, 55.0, 59.5, 62.0, 66.0])

        # Flat control passage remains steady throughout
        self.assertEqual(flat_pitches, [49.0, 49.0, 49.0, 49.0, 49.0, 49.0])
        self.assertEqual(flat_pitches[0], flat_pitches[-1])

    def test_sound_preservation_and_off_grid_precision(self):
        """Verify float input preservation and exact rational precision."""
        song = build_ascending_passage(u_ms=100)
        # Float preservation
        float_note = NoteEvent("float_1", pitch=60, note_name="C4", start_ms=145.2, end_ms=387.6)
        song.add_off_grid_note(float_note)

        retrieved = song.off_grid_events[0]
        self.assertEqual(retrieved.start_ms, 145.2)
        self.assertEqual(retrieved.end_ms, 387.6)
        self.assertAlmostEqual(retrieved.duration_ms, 242.4, places=5)

        # Exact rational precision
        rat_note = NoteEvent("rat_1", pitch=60, note_name="C4", start_ms=Fraction(726, 5), end_ms=Fraction(1938, 5))
        self.assertEqual(rat_note.start_ms, Fraction(726, 5))
        self.assertEqual(rat_note.end_ms, Fraction(1938, 5))
        self.assertEqual(rat_note.duration_ms, Fraction(1212, 5))

    def test_two_song_independence(self):
        """Verify two songs can have different fundamental units, cell counts, and boundaries."""
        song1 = build_ascending_passage(u_ms=100)
        song2 = build_song_2_independent(u_ms=250)

        self.assertEqual(song1.grid.u_ms, 100)
        self.assertEqual(song2.grid.u_ms, 250)
        self.assertEqual(song1.grid.total_cells, 12)
        self.assertEqual(song2.grid.total_cells, 10)

        s1_bounds = song1.combined_boundaries()
        s2_bounds = song2.combined_boundaries()
        self.assertNotEqual(s1_bounds, s2_bounds)
        self.assertEqual(s1_bounds, [0, 3, 4, 6, 8, 9, 12])
        self.assertEqual(s2_bounds, [0, 2, 4, 5, 6, 8, 10])

    def test_meeting_points_and_boundary_handoffs(self):
        """Verify Guess C: specific meeting points where sound groups transition."""
        song = build_ascending_passage(u_ms=100)
        segs = song.derive_row1_segments()

        # At unit 0: Entry of R2_LowWhirr_1 and R3_Flap_A
        self.assertIn("Entry", segs[0].left_boundary_handoff)
        # At unit 3: Hand-off in Row 3 (Flap_A -> Flap_B)
        self.assertIn("Hand-off", segs[1].left_boundary_handoff)
        self.assertIn("R3_Flap_A -> R3_Flap_B", segs[1].left_boundary_handoff)
        # At unit 4: Hand-off in Row 2 (LowWhirr_1 -> LowWhirr_2)
        self.assertIn("Hand-off", segs[2].left_boundary_handoff)
        self.assertIn("R2_LowWhirr_1 -> R2_LowWhirr_2", segs[2].left_boundary_handoff)


if __name__ == "__main__":
    unittest.main()
