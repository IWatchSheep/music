"""JOB-04 Stage 2a regression tests: input handling, timing preservation, diagnostics, evaluation controls.

Each test pins a corrected behaviour of music_model/group_discovery.py.  Every test in this file was run
against the pre-Stage-2a engine (backup SHA-256 baa07247f1a4...) and failed there; that negative-baseline
run is recorded in the Stage 2a evidence.  The 15 original tests (tests/test_group_discovery.py) are
unchanged.  Probe ids refer to job04_investigation/defect_probes.py.
"""

from __future__ import annotations

import math
import unittest
from fractions import Fraction

from music_model import group_discovery as gd
from music_model.sound_event import SoundEvent


class N:
    """Minimal note: start_ms/end_ms in milliseconds, optional pitch."""

    def __init__(self, s, e, pitch=60, name=""):
        self.start_ms, self.end_ms, self.pitch = s, e, pitch
        self.note_name = name or f"N{pitch}"


class NoPitch:
    def __init__(self, s, e):
        self.start_ms, self.end_ms = s, e


class TickOnly:
    def __init__(self, s, e, p=60):
        self.start_tick, self.end_tick, self.pitch = s, e, p


class TestPitchHandling(unittest.TestCase):
    def test_p01_missing_pitch_is_unpitched_not_60(self):
        n = gd.normalize_note(NoPitch(0, 100), "r", 0)
        self.assertIsNone(n.pitch)
        self.assertEqual(n.pitch_source, "none")
        self.assertIsNone(gd.extract_note_timing(NoPitch(0, 100))[2])

    def test_p03_fractional_pitch_preserved(self):
        self.assertEqual(gd.normalize_note(N(0, 100, 60.4), "r", 0).pitch, 60.4)
        self.assertEqual(gd.extract_note_timing(N(0, 100, 60.4))[2], 60.4)

    def test_p14_unpitched_soundevent_does_not_crash_any_method(self):
        ev = SoundEvent("w2", "Row 2", 0, 500)                 # height None (JOB-02 unpitched WAV event)
        ev2 = SoundEvent("w3", "Row 2", 700, 900, height=64.0)
        rows = {"Row 2": [ev, ev2]}
        for fn in (gd.sift_breath_rests, gd.sift_motoric_rhythm, gd.sift_melodic_contour,
                   gd.sift_cross_row_handoffs, gd.control_fixed_width):
            res = fn(rows)
            self.assertEqual(res.diagnostics.unpitched_notes_count, 1, fn.__name__)
        gd.control_random_grouping(rows, target_boundary_count=3)

    def test_unpitched_event_breaks_contour_sequence(self):
        # 60 -> [unpitched] -> 72: without the break, 60->72 would be a 12-semitone leap inside one sequence.
        rows = {"v": [N(0, 100, 60), NoPitch(100, 200), N(200, 300, 72), N(300, 400, 74)]}
        res = gd.sift_melodic_contour(rows, min_leap_semitones=5)
        groups = [(g.start_ms, g.end_ms, g.method) for g in res.groups_by_row["v"]]
        self.assertEqual(groups, [(0.0, 100.0, "Sifter_C_Contour"), (100.0, 200.0, "Sifter_C_Unpitched"),
                                  (200.0, 400.0, "Sifter_C_Contour")])


class TestTimingHandling(unittest.TestCase):
    def test_p02_tick_only_timing_is_rejected(self):
        with self.assertRaises(gd.AmbiguousTimingError):
            gd.normalize_note(TickOnly(480, 960), "r", 0)
        with self.assertRaises(gd.AmbiguousTimingError):
            gd.sift_breath_rests({"r": [TickOnly(480, 960)]})

    def test_p04_authoritative_exact_timing_used_with_provenance(self):
        ev = SoundEvent("w1", "Row 2", 0, 1, height=60.0,
                        attributes={"exact_start_sec_rational": "1/44100", "exact_end_sec_rational": "45/44100"})
        n = gd.normalize_note(ev, "Row 2", 0)
        self.assertEqual(n.start, Fraction(1000, 44100))
        self.assertEqual(n.end, Fraction(45000, 44100))
        self.assertEqual(n.timing_source, "audio_exact_rational")
        res = gd.sift_breath_rests({"Row 2": [ev]})
        g = res.groups_by_row["Row 2"][0]
        self.assertEqual((g.exact_start_ms, g.exact_end_ms), (Fraction(1000, 44100), Fraction(45000, 44100)))
        self.assertEqual(res.diagnostics.timing_source_counts, {"audio_exact_rational": 1})

    def test_integer_fallback_is_labelled_not_exact(self):
        n = gd.normalize_note(SoundEvent("m1", "r", 10, 20, height=60.0), "r", 0)
        self.assertEqual(n.timing_source, "integer_ms_fallback")

    def test_malformed_and_non_finite_timing_rejected_by_sifters(self):
        for bad in (N(100, 100), N(200, 100), N(float("nan"), 100), N(0, float("inf")), N(True, 5)):
            with self.assertRaises(gd.NoteTimingError):
                gd.sift_breath_rests({"r": [bad]})
        diag = gd.diagnose_passage_timing({"r": [N(0, 100), N(200, 100)]})
        self.assertEqual(diag.malformed_notes_count, 1)               # diagnostics count, never raise


class TestPolyphonyAndEndpoints(unittest.TestCase):
    def test_p05_no_false_rest_under_sustained_note_and_true_group_end(self):
        rows = {"r": [N(0, 1000, 48), N(0, 200, 60), N(400, 600, 62), N(1200, 1300, 64)]}
        res = gd.sift_breath_rests(rows, min_gap_ms=100.0)
        self.assertEqual([(g.start_ms, g.end_ms) for g in res.groups_by_row["r"]], [(0.0, 1000.0), (1200.0, 1300.0)])
        diag = gd.diagnose_passage_timing(rows)
        self.assertEqual(diag.silence_intervals_ms, ((1000.0, 1200.0),))

    def test_overlapping_group_end_is_latest_end_in_contour_and_crossrow(self):
        rows = {"r": [N(0, 900, 60), N(100, 200, 64)]}
        self.assertEqual(gd.sift_cross_row_handoffs(rows).groups_by_row["r"][0].end_ms, 900.0)

    def test_contour_sifter_refuses_to_invent_order_for_polyphonic_row(self):
        rows = {"r": [N(0, 500, 60), N(0, 500, 64), N(500, 1000, 67)]}       # a chord, then a note
        res = gd.sift_melodic_contour(rows)
        self.assertEqual([g.method for g in res.groups_by_row["r"]], ["Sifter_C_PolyphonicUnsupported"])
        self.assertEqual(res.diagnostics.polyphonic_rows, ("r",))
        self.assertTrue(any("polyphonic" in w for w in res.warnings))


class TestIdentityAndRowAttribution(unittest.TestCase):
    def test_event_identity_and_indices_preserved(self):
        a = SoundEvent("e1", "r", 0, 100, height=60.0)
        b = SoundEvent("e2", "r", 300, 400, height=62.0)
        res = gd.sift_breath_rests({"r": [b, a]})                       # unsorted input
        g1, g2 = res.groups_by_row["r"]
        self.assertIs(g1.notes[0], a)
        self.assertEqual((g1.event_ids, g1.event_indices), (("e1",), (0,)))
        self.assertEqual((g2.event_ids, g2.event_indices), (("e2",), (1,)))

    def test_p11_boundaries_keep_row_attribution(self):
        res = gd.sift_breath_rests({"a": [N(0, 100), N(300, 400)], "b": [N(0, 400)]})
        self.assertEqual(res.boundaries_by_row, {"a": [0.0, 100.0, 300.0, 400.0], "b": [0.0, 400.0]})
        self.assertEqual(res.diagnostics.silence_intervals_by_row, {"a": ((100.0, 300.0),), "b": ()})


class TestEvaluationControls(unittest.TestCase):
    def test_p09_internal_random_baseline_requires_span(self):
        with self.assertRaises(ValueError):
            gd.evaluate_monte_carlo_random_baseline({"r": [N(0, 5000)]}, 2, [0.0, 2500.0, 5000.0],
                                                    num_seeds=3, passage_span_ms=None, internal_only=True)

    def test_p10_empty_reference_and_legacy_specificity_are_explicit(self):
        m = gd.evaluate_boundaries([], [], 60.0)
        self.assertTrue(m.empty_reference and m.vacuous)
        self.assertEqual(m.f1_score, 1.0)                                 # legacy value kept, now flagged vacuous
        m2 = gd.evaluate_boundaries([100.0, 200.0, 300.0], [100.0, 200.0, 900.0], 60.0)
        self.assertFalse(m2.zero_false_positives)
        self.assertFalse(m2.empty_reference or m2.vacuous)

    def test_periodic_grid_and_controls_are_labelled(self):
        rows = {"r": [N(0, 400), N(400, 800), N(800, 1200)]}
        self.assertEqual(gd.sift_motoric_rhythm(rows).segmentation_kind, "periodic_grid_experiment")
        self.assertEqual(gd.control_fixed_width(rows).segmentation_kind, "fixed_width_control")
        self.assertEqual(gd.sift_breath_rests(rows).segmentation_kind, "boundary_candidate")


if __name__ == "__main__":
    unittest.main()
