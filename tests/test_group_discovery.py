"""test_group_discovery.py - Unit tests for Milestone 5A Group Discovery Engine.

Validates:
1. Sifter A (Breath/Rest) detection.
2. Sifter B (Motoric Rhythm) detection and negative non-repetition case.
3. Sifter C (Melodic Contour) turning-point detection.
4. Sifter D (Cross-Row Hand-off) detection.
5. Control 1 (Fixed-Width) and Control 2 (Random) baselines.
6. Evaluation metrics (Precision, Recall, F1) within tolerance.
7. Internal boundaries evaluation vs total boundary coverage.
8. Elimination of 0u anomalies via exact fractional units.
9. Monte Carlo random baseline with fair internal sampling.
10. Maximum-cardinality one-to-one bipartite matching (augmenting path).
11. Transparent empty-reference scoring (Negative Control specificity).
12. Diagnostic accounting of silence, overlap, and off-grid events.
13. Non-quantization timing preservation.
14. Composite Row 1 derivation.
15. Multi-song independence.
"""

import unittest
from fractions import Fraction
from typing import Dict, List

from music_model.group_discovery import (
    DiscoveredGroup,
    DiscoveredRow1Segment,
    EvaluationMetrics,
    GroupingDiagnostic,
    GroupingResult,
    control_fixed_width,
    control_random_grouping,
    derive_row1_from_discovered_groups,
    diagnose_passage_timing,
    evaluate_boundaries,
    evaluate_monte_carlo_random_baseline,
    extract_note_timing,
    generate_random_internal_boundaries,
    max_bipartite_matching,
    sift_breath_rests,
    sift_cross_row_handoffs,
    sift_melodic_contour,
    sift_motoric_rhythm,
)
from music_model.sound_event import SoundEvent


class MockNote:
    """Mock note event to test polymorphic timing extraction."""

    def __init__(self, start_ms: float, end_ms: float, pitch: int, note_name: str = ""):
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.pitch = pitch
        self.note_name = note_name or f"N_{pitch}"


class TestGroupDiscoveryEngine(unittest.TestCase):
    """Test suite for Milestone 5A note and musical group discovery."""

    def setUp(self):
        # Create standard test passage with 2 rows
        # Row 2: 3 events of 400ms each (0-400, 400-800, 800-1200)
        self.row2_notes = [
            MockNote(0.0, 400.0, 36, "C2"),
            MockNote(400.0, 800.0, 43, "G2"),
            MockNote(800.0, 1200.0, 48, "C3"),
        ]
        # Row 3: 4 events of 300ms each (0-300, 300-600, 600-900, 900-1200)
        self.row3_notes = [
            MockNote(0.0, 300.0, 60, "C4"),
            MockNote(300.0, 600.0, 67, "G4"),
            MockNote(600.0, 900.0, 76, "E5"),
            MockNote(900.0, 1200.0, 84, "C6"),
        ]
        self.two_row_passage = {
            "Row 2 (Low)": self.row2_notes,
            "Row 3 (High)": self.row3_notes,
        }

    def test_extract_note_timing_polymorphic(self):
        """Test extraction across SoundEvent, MockNote, and float timings."""
        n1 = MockNote(123.4, 567.8, 60, "C4")
        s, e, p, lbl = extract_note_timing(n1)
        self.assertAlmostEqual(s, 123.4)
        self.assertAlmostEqual(e, 567.8)
        self.assertEqual(p, 60)
        self.assertEqual(lbl, "C4")

        # Also test with SoundEvent
        se = SoundEvent("se1", "Row 2", 1000, 2500, label="Bass Tone", height=45.0)
        s2, e2, p2, lbl2 = extract_note_timing(se)
        self.assertEqual(s2, 1000.0)
        self.assertEqual(e2, 2500.0)
        self.assertEqual(p2, 45)
        self.assertEqual(lbl2, "Bass Tone")

    def test_sifter_a_breath_rests(self):
        """Test Sifter A identifies boundaries at rests >= threshold."""
        passage_with_rests = {
            "Lead": [
                MockNote(0.0, 300.0, 60),
                MockNote(300.0, 500.0, 62),
                # 200ms rest here [500, 700)
                MockNote(700.0, 1000.0, 65),
                MockNote(1000.0, 1200.0, 67),
            ]
        }
        res = sift_breath_rests(passage_with_rests, min_gap_ms=100.0, u_ms=100.0)
        groups = res.groups_by_row["Lead"]
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].start_ms, 0.0)
        self.assertEqual(groups[0].end_ms, 500.0)
        self.assertEqual(groups[1].start_ms, 700.0)
        self.assertEqual(groups[1].end_ms, 1200.0)
        self.assertEqual(res.discovered_boundaries_ms, [0.0, 500.0, 700.0, 1200.0])

    def test_sifter_b_motoric_rhythm_and_negative_case(self):
        """Test Sifter B identifies periodic spans and reports negative when non-repeating."""
        # 1. Positive case: repeating 400ms and 300ms spans
        res = sift_motoric_rhythm(self.two_row_passage, u_ms=100.0)
        r2_groups = res.groups_by_row["Row 2 (Low)"]
        r3_groups = res.groups_by_row["Row 3 (High)"]
        self.assertEqual(len(r2_groups), 3)
        self.assertEqual(len(r3_groups), 4)
        self.assertEqual(r2_groups[0].duration_ms, 400.0)
        self.assertEqual(r3_groups[0].duration_ms, 300.0)

        # 2. Negative case: irregular non-periodic passage
        irregular_passage = {
            "Solo": [
                MockNote(0.0, 137.0, 60),
                MockNote(137.0, 489.0, 61),
                MockNote(489.0, 612.0, 62),
                MockNote(612.0, 1150.0, 63),
            ]
        }
        res_neg = sift_motoric_rhythm(irregular_passage, u_ms=100.0)
        solo_groups = res_neg.groups_by_row["Solo"]
        self.assertEqual(len(solo_groups), 1)
        self.assertEqual(solo_groups[0].method, "Sifter_B_NoRepetition")
        self.assertEqual(solo_groups[0].duration_ms, 1150.0)

    def test_sifter_c_melodic_contour(self):
        """Test Sifter C identifies turning points in melodic contour."""
        # Melodic arch: rises C4(60) -> E4(64) -> G4(67) then falls to D4(62) -> C4(60)
        arch_passage = {
            "Voice": [
                MockNote(0.0, 200.0, 60),
                MockNote(200.0, 400.0, 64),
                MockNote(400.0, 600.0, 67),  # Peak turning point
                MockNote(600.0, 800.0, 62),
                MockNote(800.0, 1000.0, 60),
            ]
        }
        res = sift_melodic_contour(arch_passage, min_leap_semitones=5, u_ms=100.0)
        groups = res.groups_by_row["Voice"]
        self.assertGreaterEqual(len(groups), 2)
        # First group should end at peak (600ms)
        self.assertEqual(groups[0].end_ms, 600.0)
        self.assertEqual(groups[1].start_ms, 600.0)

    def test_sifter_d_cross_row_handoffs(self):
        """Test Sifter D identifies cross-row entry cues without circular credit."""
        res = sift_cross_row_handoffs(self.two_row_passage, window_ms=50.0, u_ms=100.0)
        r2_groups = res.groups_by_row["Row 2 (Low)"]
        r3_groups = res.groups_by_row["Row 3 (High)"]
        self.assertGreater(len(r2_groups), 0)
        self.assertGreater(len(r3_groups), 0)
        for b in res.discovered_boundaries_ms:
            self.assertIn(b, [0.0, 300.0, 400.0, 600.0, 800.0, 900.0, 1200.0])

    def test_controls_fixed_and_random(self):
        """Test Control 1 (Fixed-Width) and Control 2 (Random Baseline)."""
        ctrl1 = control_fixed_width(self.two_row_passage, width_ms=400.0, u_ms=100.0)
        self.assertEqual(ctrl1.discovered_boundaries_ms, [0.0, 400.0, 800.0, 1200.0])

        ctrl2 = control_random_grouping(
            self.two_row_passage, target_boundary_count=5, seed=42, u_ms=100.0
        )
        self.assertEqual(len(ctrl2.discovered_boundaries_ms), 5)
        self.assertEqual(ctrl2.discovered_boundaries_ms[0], 0.0)
        self.assertEqual(ctrl2.discovered_boundaries_ms[-1], 1200.0)

    def test_evaluation_metrics_precision_recall_f1(self):
        """Test evaluation metrics against reference ground truth."""
        ref = [0.0, 300.0, 600.0, 900.0, 1200.0]
        # Exact match
        metrics_exact = evaluate_boundaries(ref, ref, tolerance_ms=10.0)
        self.assertEqual(metrics_exact.precision, 1.0)
        self.assertEqual(metrics_exact.recall, 1.0)
        self.assertEqual(metrics_exact.f1_score, 1.0)
        self.assertEqual(metrics_exact.true_positives, 5)

        # Offsets within tolerance
        disc_near = [0.0, 305.0, 595.0, 902.0, 1200.0]
        metrics_near = evaluate_boundaries(disc_near, ref, tolerance_ms=10.0)
        self.assertEqual(metrics_near.f1_score, 1.0)

        # Spurious boundary (over-segmentation)
        disc_spurious = [0.0, 150.0, 300.0, 600.0, 900.0, 1200.0]
        metrics_spur = evaluate_boundaries(disc_spurious, ref, tolerance_ms=10.0)
        self.assertEqual(metrics_spur.true_positives, 5)
        self.assertEqual(metrics_spur.false_positives, 1)
        self.assertAlmostEqual(metrics_spur.precision, 5.0 / 6.0)
        self.assertEqual(metrics_spur.recall, 1.0)

    def test_internal_boundaries_evaluation(self):
        """Test evaluating internal boundaries separately from edge boundaries (0 < t < T)."""
        ref_all = [0.0, 300.0, 600.0, 900.0, 1200.0]
        disc_all = [0.0, 300.0, 600.0, 1200.0]  # missed 900.0

        m_total = evaluate_boundaries(disc_all, ref_all, tolerance_ms=10.0, internal_only=False)
        self.assertEqual(m_total.discovered_count, 4)
        self.assertEqual(m_total.reference_count, 5)

        m_internal = evaluate_boundaries(
            disc_all,
            ref_all,
            tolerance_ms=10.0,
            passage_span_ms=(0.0, 1200.0),
            internal_only=True,
        )
        self.assertEqual(m_internal.discovered_count, 2)
        self.assertEqual(m_internal.reference_count, 3)
        self.assertEqual(m_internal.true_positives, 2)
        self.assertEqual(m_internal.false_negatives, 1)
        self.assertEqual(m_internal.precision, 1.0)
        self.assertAlmostEqual(m_internal.recall, 2.0 / 3.0)
        self.assertTrue(m_internal.is_internal_only)

    def test_fractional_units_and_sub_unit_detection(self):
        """Test that sub-unit intervals (e.g. 50ms) are NOT rounded down to 0u."""
        passage = {
            "R1": [MockNote(0.0, 750.0, 60), MockNote(800.0, 1200.0, 64)],
            "R2": [MockNote(750.0, 800.0, 70)],  # 50ms event
        }
        res = sift_cross_row_handoffs(passage, u_ms=100.0)
        segs = res.row1_segments
        sub_seg = next(s for s in segs if abs(s.start_ms - 750.0) < 1e-4)
        self.assertEqual(sub_seg.duration_ms, 50.0)
        self.assertEqual(sub_seg.width_units, 0.5)
        self.assertEqual(sub_seg.formatted_units, "0.50u")
        self.assertTrue(sub_seg.is_sub_unit)
        self.assertNotEqual(sub_seg.formatted_units, "0u")

    def test_maximum_cardinality_bipartite_matching(self):
        """Test that bipartite matching finds maximum cardinality where greedy could block."""
        # R = [100.0, 120.0], D = [115.0, 126.0], tolerance = 15.0
        # R[0]=100 can only match D[0]=115 (dist 15)
        # R[1]=120 can match D[0]=115 (dist 5) or D[1]=126 (dist 6)
        # Greedy by distance would pick (R[1], D[0]) [dist 5], blocking R[0], yielding only 1 match.
        # Maximum cardinality matches (R[0], D[0]) and (R[1], D[1]), yielding 2 matches!
        ref = [100.0, 120.0]
        disc = [115.0, 126.0]
        matches = max_bipartite_matching(ref, disc, tolerance_ms=15.0)
        self.assertEqual(len(matches), 2)
        self.assertIn((0, 0), matches)
        self.assertIn((1, 1), matches)

    def test_empty_reference_scoring_transparency(self):
        """Test transparent handling of negative control where ground truth has 0 internal boundaries."""
        # Case A: Algorithm correctly finds 0 boundaries -> Specificity = 1.0, FP = 0
        m_perfect = evaluate_boundaries(
            discovered_boundaries_ms=[],
            reference_boundaries_ms=[],
            tolerance_ms=50.0,
            internal_only=True,
        )
        self.assertEqual(m_perfect.discovered_count, 0)
        self.assertEqual(m_perfect.reference_count, 0)
        self.assertEqual(m_perfect.false_positives, 0)
        self.assertEqual(m_perfect.specificity, 1.0)
        self.assertEqual(m_perfect.f1_score, 1.0)

        # Case B: Algorithm hallucinates 2 boundaries when reference has 0 -> FP = 2, Specificity = 0.0
        m_hallucinated = evaluate_boundaries(
            discovered_boundaries_ms=[300.0, 600.0],
            reference_boundaries_ms=[],
            tolerance_ms=50.0,
            internal_only=True,
        )
        self.assertEqual(m_hallucinated.discovered_count, 2)
        self.assertEqual(m_hallucinated.reference_count, 0)
        self.assertEqual(m_hallucinated.false_positives, 2)
        self.assertEqual(m_hallucinated.specificity, 0.0)
        self.assertEqual(m_hallucinated.precision, 0.0)
        self.assertEqual(m_hallucinated.f1_score, 0.0)

    def test_monte_carlo_random_baseline(self):
        """Test Monte Carlo baseline across multiple seeds."""
        ref = [0.0, 400.0, 800.0, 1200.0]
        mean_p, std_p, mean_r, std_r, mean_f, std_f = evaluate_monte_carlo_random_baseline(
            self.two_row_passage,
            target_boundary_count=2,
            reference_boundaries_ms=ref,
            num_seeds=20,
            tolerance_ms=50.0,
            passage_span_ms=(0.0, 1200.0),
            internal_only=True,
            u_ms=100.0,
        )
        self.assertGreaterEqual(mean_f, 0.0)
        self.assertLessEqual(mean_f, 1.0)
        self.assertGreaterEqual(std_f, 0.0)

    def test_timing_diagnostics_silence_overlap_offgrid(self):
        """Test diagnostic accounting of silence, overlap, and off-grid events."""
        passage_with_anomalies = {
            "PolyRow": [
                MockNote(0.0, 500.0, 60),
                MockNote(300.0, 700.0, 64),  # Overlaps [300, 500)
                # Silence [700, 950)
                MockNote(950.5, 1200.0, 67),  # Off-grid start 950.5
            ]
        }
        diag = diagnose_passage_timing(passage_with_anomalies, u_ms=100.0)
        self.assertEqual(len(diag.overlapping_intervals_ms), 1)
        self.assertEqual(diag.overlapping_intervals_ms[0], (300.0, 500.0, "PolyRow"))
        self.assertEqual(len(diag.silence_intervals_ms), 1)
        self.assertEqual(diag.silence_intervals_ms[0], (700.0, 950.5))
        self.assertGreater(diag.off_grid_notes_count, 0)
        self.assertEqual(diag.malformed_notes_count, 0)

    def test_derive_composite_row1_segments(self):
        """Test composite Row 1 segments derivation from discovered groups."""
        res = sift_motoric_rhythm(self.two_row_passage, u_ms=100.0)
        row1_segs = res.row1_segments
        widths = [int(round(s.width_units)) for s in row1_segs if s.width_units is not None]
        self.assertEqual(widths, [3, 1, 2, 2, 1, 3])
        self.assertEqual(sum(s.duration_ms for s in row1_segs), 1200.0)

        pitches = [s.mean_pitch for s in row1_segs]
        self.assertTrue(pitches[0] < pitches[-1])

    def test_two_song_isolation(self):
        """Test that two separate passages processed sequentially do not share state."""
        song1 = {"R": [MockNote(0.0, 400.0, 40)]}
        song2 = {"R": [MockNote(0.0, 900.0, 70)]}

        res1 = sift_motoric_rhythm(song1, u_ms=100.0)
        res2 = sift_motoric_rhythm(song2, u_ms=100.0)

        self.assertEqual(res1.discovered_boundaries_ms, [0.0, 400.0])
        self.assertEqual(res2.discovered_boundaries_ms, [0.0, 900.0])


if __name__ == "__main__":
    unittest.main()
