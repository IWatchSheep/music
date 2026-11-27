"""JOB-04 Stage 2b tests: input-contract safeguards and recurrence discovery (discover_sound_groups).

Expected answers are written from the construction of each input, never from engine output.
"""

from __future__ import annotations

import random
import unittest
from fractions import Fraction

from music_model import group_discovery as gd
from music_model.group_discovery import discover_sound_groups
from music_model.recurrence_discovery import DiscoveryConfig
from music_model.sound_event import SoundEvent


class N:
    def __init__(self, s, e, pitch=60, eid="", voice=None):
        self.start_ms, self.end_ms, self.pitch = s, e, pitch
        self.event_id = eid
        if voice is not None:
            self.voice = voice


def seq(pitches, durs, t0=0, prefix="e", gaps=None):
    out, t = [], t0
    for k, (p, d) in enumerate(zip(pitches, durs)):
        out.append(N(t, t + d, p, f"{prefix}{k}"))
        t += d + (gaps[k] if gaps else 0)
    return out


A_P, A_D = [60, 62, 64, 60], [250, 250, 250, 500]
F_P, F_D = [67, 65, 69, 71], [250, 250, 500, 250]


def fams(res, method, maximal=True):
    return [f for f in res.all_families if f.method == method and (f.is_maximal or not maximal)]


def windows(f):
    return sorted((o.row_id, o.start_index, o.end_index) for o in f.occurrences)


class TestInputContractSafeguards(unittest.TestCase):
    def test_fraction_pitch_preserved_exactly(self):
        n = gd.normalize_note(N(0, 1, Fraction(181, 3)), "r", 0)
        self.assertEqual(n.pitch, Fraction(181, 3))
        self.assertEqual(n.pitch_exact, Fraction(181, 3))
        self.assertEqual(n.pitch_kind, "rational")

    def test_distinct_rationals_do_not_collapse(self):
        a = gd.normalize_note(N(0, 1, Fraction(60) + Fraction(1, 10 ** 20)), "r", 0)
        b = gd.normalize_note(N(0, 1, 60), "r", 0)
        self.assertNotEqual(a.pitch_exact, b.pitch_exact)
        self.assertEqual((a.pitch_kind, b.pitch_kind), ("rational", "integer"))

    def test_float_pitch_compatibility(self):
        n = gd.normalize_note(N(0, 1, 60.4), "r", 0)
        self.assertEqual(n.pitch, 60.4)
        self.assertEqual(n.pitch_exact, Fraction(60.4))          # the exact binary value of the float
        self.assertEqual(n.pitch_kind, "binary_float")

    def test_negative_start_rejected_consistently(self):
        with self.assertRaises(gd.NoteTimingError):
            gd.normalize_note(N(-1, 1), "r", 0)
        with self.assertRaises(gd.NoteTimingError):
            discover_sound_groups({"r": [N(-1, 1)]})

    def test_huge_pitch_and_time_rejected_without_overflow(self):
        for bad in (N(0, 1, 10 ** 400), N(0, 1, -10 ** 400), N(0, 10 ** 13)):
            with self.assertRaises(gd.NoteTimingError):
                gd.normalize_note(bad, "r", 0)
        diag = gd.diagnose_passage_timing({"r": [N(0, 1, 10 ** 400), N(2, 3)]})   # counted, never raises
        self.assertEqual(diag.malformed_notes_count, 1)

    def test_audio_estimated_pitch_flagged(self):
        ev = SoundEvent("w", "Row 2", 0, 100, height=64.0, attributes={"source_type": "audio_wav"})
        self.assertTrue(gd.normalize_note(ev, "Row 2", 0).pitch_estimated)


class TestExactRecurrence(unittest.TestCase):
    def setUp(self):
        notes = seq(A_P, A_D) + seq(F_P, F_D, t0=1250, prefix="f") + seq(A_P, A_D, t0=2500, prefix="g")
        self.res = discover_sound_groups({"melody": notes})

    def test_time_displaced_exact_repetition_found(self):
        ex = fams(self.res, "exact")
        self.assertEqual(len(ex), 1)
        f = ex[0]
        self.assertEqual((f.length, windows(f)), (4, [("melody", 0, 4), ("melody", 8, 12)]))
        self.assertEqual(f.occurrences[1].event_ids, ("g0", "g1", "g2", "g3"))
        self.assertEqual((f.occurrences[1].exact_start_ms, f.occurrences[1].exact_end_ms), (Fraction(2500), Fraction(3750)))
        self.assertEqual(f.independent_occurrence_count, 2)
        self.assertIn("pitches=(60,62,64,60)", f.family_key)

    def test_nested_shorter_repeats_marked_not_maximal(self):
        nested = [f for f in self.res.all_families if f.method == "exact" and not f.is_maximal]
        self.assertEqual(sorted(f.length for f in nested), [3, 3])
        self.assertTrue(all(f.nested_in for f in nested))

    def test_configurable_minimum_length(self):
        self.assertEqual(fams(discover_sound_groups({"melody": seq(A_P, A_D) + seq(A_P, A_D, t0=2000, prefix="g")},
                                                    min_length=5), "exact"), [])
        r2 = discover_sound_groups({"melody": seq(A_P, A_D) + seq(A_P, A_D, t0=2000, prefix="g")}, min_length=2)
        self.assertEqual(sorted(f.length for f in r2.all_families if f.method == "exact"), [2, 2, 2, 3, 3, 4])

    def test_include_nested_false_hides_but_reports(self):
        r = discover_sound_groups({"melody": seq(A_P, A_D) + seq(A_P, A_D, t0=2000, prefix="g")}, include_nested=False)
        self.assertTrue(all(f.is_maximal for f in r.families))
        self.assertTrue(any(not f.is_maximal for f in r.all_families))
        self.assertTrue(any("nested families hidden" in n for n in r.search_notes))

    def test_no_row1_or_grid_in_result(self):
        for name in ("row1_segments", "columns", "row_assignment"):
            self.assertFalse(hasattr(self.res, name))


class TestTranspositionAndIntervals(unittest.TestCase):
    def test_transposition_displacement_preserved_and_identities_kept(self):
        notes = seq(A_P, A_D) + seq(F_P, F_D, t0=1250, prefix="f") + seq([p + 7 for p in A_P], A_D, t0=2500, prefix="g")
        r = discover_sound_groups({"melody": notes})
        self.assertEqual(fams(r, "exact"), [])                                 # different absolute pitches
        t = fams(r, "transposition")
        self.assertEqual(len(t), 1)
        self.assertEqual([o.transposition_semitones for o in t[0].occurrences], [Fraction(0), Fraction(7)])
        self.assertEqual(t[0].occurrences[1].pitches, tuple(Fraction(p + 7) for p in A_P))
        self.assertIn(("displacements_semitones", "0,7"), t[0].parameters)

    def test_interval_only_distinct_from_strict_transposition(self):
        notes = seq(A_P, A_D) + seq([p + 5 for p in A_P], [500, 125, 125, 250], t0=1500, prefix="g")
        r = discover_sound_groups({"m": notes}, methods=("transposition", "interval_only"))
        self.assertEqual(fams(r, "transposition"), [])
        io = fams(r, "interval_only")
        self.assertEqual([(f.length, windows(f)) for f in io], [(4, [("m", 0, 4), ("m", 4, 8)])])

    def test_cross_row_transposed_match(self):
        r = discover_sound_groups({"upper": seq(A_P, A_D), "lower": seq([p - 24 for p in A_P], A_D, t0=1250, prefix="L")})
        t = fams(r, "transposition")
        self.assertEqual(len(t), 1)
        self.assertEqual(sorted(o.row_id for o in t[0].occurrences), ["lower", "upper"])
        self.assertEqual(sorted(o.transposition_semitones for o in t[0].occurrences), [0, 24])


class TestRhythmAndContour(unittest.TestCase):
    def test_rhythm_independent_of_pitch(self):
        r_d = [125, 125, 250, 500]
        notes = seq([60, 64, 67, 72], r_d) + seq([57, 53, 55, 50], [500, 250, 375, 250], t0=1000, prefix="c") + \
            seq([65, 62, 69, 60], r_d, t0=2375, prefix="g")
        r = discover_sound_groups({"m": notes}, methods=("exact", "rhythm"))
        self.assertEqual(fams(r, "exact"), [])
        rh = [f for f in fams(r, "rhythm") if f.length == 4]
        self.assertEqual([windows(f) for f in rh], [[("m", 0, 4), ("m", 8, 12)]])

    def test_proportional_rhythm_is_separate_with_exact_scale(self):
        notes = seq([60, 62, 64], [100, 100, 200]) + seq([70, 75, 71], [200, 200, 400], t0=1000, prefix="g")
        r = discover_sound_groups({"m": notes}, methods=("rhythm", "rhythm_proportional"))
        self.assertEqual(fams(r, "rhythm"), [])
        pr = fams(r, "rhythm_proportional")
        self.assertEqual(len(pr), 1)
        self.assertEqual([o.scale_factor for o in pr[0].occurrences], [Fraction(1), Fraction(2)])

    def test_contour_includes_repeated_pitch_and_is_weak(self):
        notes = seq([60, 60, 62], [250, 250, 250]) + seq([70, 70, 75], [100, 300, 200], t0=1000, prefix="g")
        r = discover_sound_groups({"m": notes})
        self.assertEqual(fams(r, "exact"), [])
        c = fams(r, "contour")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].features, (("contour", ("0", "1")),))
        self.assertTrue(any("weak" in x for x in c[0].limitations))


class TestOverlapAmbiguityTiming(unittest.TestCase):
    def test_overlapping_only_repeat_is_rejected_and_reported(self):
        r = discover_sound_groups({"m": seq([60] * 5, [100] * 5)}, methods=("exact",))
        self.assertEqual([f for f in r.all_families if f.length == 3], [])
        rej = [c for c in r.rejected_candidates if c.length == 3]
        self.assertEqual([(c.raw_occurrences, c.independent_occurrences) for c in rej], [(3, 1)])

    def test_overlapping_occurrences_listed_and_flagged(self):
        r = discover_sound_groups({"m": seq([60] * 6, [100] * 6)}, methods=("exact",))
        f3 = [f for f in r.all_families if f.length == 3][0]
        self.assertEqual(len(f3.occurrences), 4)
        self.assertEqual(f3.independent_occurrence_count, 2)
        self.assertTrue(f3.occurrences[0].overlaps_with)
        self.assertTrue(any("overlap" in x for x in f3.limitations))

    def test_exact_fractional_timing_matches_without_tolerance(self):
        def ev(eid, s, e, p):
            return SoundEvent(eid, "r", int(s), int(s) + max(1, int(e - s)), height=float(p),
                              attributes={"exact_start_ms_rational": str(s), "exact_end_ms_rational": str(e)})
        third = Fraction(1000, 3)
        a = [ev(f"a{k}", k * third, (k + 1) * third, p) for k, p in enumerate([60, 62, 64])]
        b = [ev(f"b{k}", 2000 + k * third, 2000 + (k + 1) * third, p) for k, p in enumerate([60, 62, 64])]
        near = [ev(f"c{k}", 4000 + k * Fraction(333), 4000 + (k + 1) * Fraction(333), p) for k, p in enumerate([60, 62, 64])]
        r = discover_sound_groups({"r": a + b + near}, methods=("exact",))
        f = fams(r, "exact")
        self.assertEqual([windows(x) for x in f], [[("r", 0, 3), ("r", 3, 6)]])     # 333 ms != 1000/3 ms
        self.assertEqual(f[0].occurrences[0].exact_end_ms, Fraction(1000))
        self.assertEqual(f[0].occurrences[0].timing_sources, ("musicxml_exact_rational",))

    def test_non_repeating_passage_has_no_strict_families(self):
        notes = seq([60, 61, 63, 66, 70, 75, 81], [100, 200, 300, 400, 500, 600, 700])
        r = discover_sound_groups({"m": notes}, methods=("exact", "transposition", "rhythm"))
        self.assertEqual(r.all_families, ())

    def test_input_order_determinism(self):
        notes = seq(A_P, A_D) + seq(F_P, F_D, t0=1250, prefix="f") + seq([p + 7 for p in A_P], A_D, t0=2500, prefix="g")
        base = discover_sound_groups({"x": notes, "y": seq(A_P, A_D, t0=500, prefix="y")})
        rng = random.Random(7)
        for _ in range(5):
            shuffled = list(notes); rng.shuffle(shuffled)
            r = discover_sound_groups({"y": seq(A_P, A_D, t0=500, prefix="y"), "x": shuffled})
            self.assertEqual(r.all_families, base.all_families)
            self.assertEqual(r.streams, base.streams)


class TestPolyphonyVoicesUnpitched(unittest.TestCase):
    def test_polyphonic_stream_unsupported_and_reported(self):
        r = discover_sound_groups({"r": [N(0, 500, 60, "a"), N(0, 500, 64, "b")] + seq(A_P, A_D, t0=500)})
        self.assertEqual(r.streams[0].status, "polyphonic_unsupported")
        self.assertEqual(r.all_families, ())
        self.assertTrue(any(x.event_id == "a" and "polyphonic" in x.reason for x in r.exclusions))

    def test_explicit_voices_form_separate_monophonic_streams(self):
        v1 = [N(n.start_ms, n.end_ms, n.pitch, "v1_" + n.event_id, voice=1) for n in seq(A_P, A_D) + seq(A_P, A_D, t0=1250)]
        v2 = [N(n.start_ms, n.end_ms, n.pitch, "v2_" + n.event_id, voice=2) for n in seq([48, 50, 52, 55, 57], [500] * 5)]
        r = discover_sound_groups({"r": v1 + v2})
        self.assertEqual([(s.voice_id, s.status) for s in r.streams], [("1", "monophonic"), ("2", "monophonic")])
        ex = fams(r, "exact")
        self.assertEqual([[(o.voice_id, o.start_index) for o in f.occurrences] for f in ex], [[("1", 0), ("1", 4)]])

    def test_unpitched_breaks_pitch_methods_but_rhythm_supports_it(self):
        class U:
            def __init__(self, s, e, eid):
                self.start_ms, self.end_ms, self.event_id = s, e, eid
        notes = [N(0, 100, 60, "a"), U(100, 200, "u1"), N(200, 300, 62, "b"),
                 N(1000, 1100, 60, "c"), U(1100, 1200, "u2"), N(1200, 1300, 62, "d")]
        r = discover_sound_groups({"m": notes})
        self.assertEqual(fams(r, "exact"), [])                      # no 3-note pitched run exists
        self.assertEqual([windows(f) for f in fams(r, "rhythm")], [[("m", 0, 3), ("m", 3, 6)]])
        self.assertTrue(any(x.event_id == "u1" and x.method == "exact" for x in r.exclusions))
        self.assertFalse(any(x.method == "rhythm" for x in r.exclusions))


class TestSearchLimitsAndConfig(unittest.TestCase):
    def test_window_limit_reported_not_silent(self):
        r = discover_sound_groups({"m": seq([60] * 40, [100] * 40)}, methods=("exact",), max_windows=100)
        self.assertFalse(r.search_complete)
        self.assertTrue(any("NOT searched" in n for n in r.search_notes))

    def test_invalid_configuration_rejected(self):
        for bad in ({"min_length": 1}, {"methods": ("nonsense",)}, {"min_occurrences": 1}, {"max_length": 2}):
            with self.assertRaises(ValueError):
                discover_sound_groups({"m": []}, **bad)

    def test_empty_and_short_inputs(self):
        for rows in ({}, {"m": []}, {"m": [N(0, 1)]}, {"m": [N(0, 1), N(1, 2, 62)]}):
            r = discover_sound_groups(rows)
            self.assertEqual(r.all_families, ())
            self.assertTrue(r.search_complete)

    def test_config_object_and_group_discovery_entry_point(self):
        r = gd.discover_sound_groups({"m": seq(A_P, A_D) + seq(A_P, A_D, t0=2000)}, DiscoveryConfig(methods=("exact",)))
        self.assertEqual([f.method for f in r.all_families], ["exact", "exact", "exact"])


if __name__ == "__main__":
    unittest.main()
