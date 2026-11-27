"""JOB-04 Stage 2c coverage addition: strict transposition must compare inter-onset intervals.

Found during publication preparation: a mutant whose ``transposition`` signature ignored inter-onset
intervals passed the independent held-out verifier and all 79 earlier JOB-04 tests.  This test closes
that gap.  The expected answers are written from the construction of the input, never from engine output.

Construction (one row, unspecified voice, every duration 1 ms, pitches exact integers):
  Phrase A: pitches 60, 62, 64 at onsets 0, 1, 2 ms   -> intervals (+2, +2), inter-onset intervals (1, 1)
  Phrase B: pitches 67, 69, 71 at onsets 10, 13, 16 ms -> intervals (+2, +2), inter-onset intervals (3, 3)
Hence:
  exact          : no recurrence (absolute pitches differ, and so do the onsets)
  transposition  : no recurrence (equal intervals and durations, but the relative onsets differ)
  interval_only  : recurrence at the half-open event ranges [0, 3) and [3, 6) (pitches displaced by +7 semitones)
"""

from __future__ import annotations

import unittest
from fractions import Fraction

from music_model.recurrence_discovery import discover_sound_groups


class _Note:
    def __init__(self, start, pitch, eid):
        self.start_ms, self.end_ms, self.pitch, self.event_id = Fraction(start), Fraction(start + 1), pitch, eid


PHRASE_A = [_Note(0, 60, "a0"), _Note(1, 62, "a1"), _Note(2, 64, "a2")]
PHRASE_B = [_Note(10, 67, "b0"), _Note(13, 69, "b1"), _Note(16, 71, "b2")]


class TestStrictTranspositionComparesInterOnsetIntervals(unittest.TestCase):
    def test_equal_intervals_and_durations_with_different_onset_spacing(self):
        result = discover_sound_groups({"r": PHRASE_A + PHRASE_B},
                                       methods=("exact", "transposition", "interval_only"), max_length=3)

        def families(method):
            return [f for f in result.all_families if f.method == method]

        # Absent: exact and strict transposition.
        self.assertEqual(families("exact"), [], "different absolute pitches and onsets are not an exact recurrence")
        self.assertEqual(families("transposition"), [],
                         "equal intervals and durations but different inter-onset intervals are NOT a strict transposition")

        # Present: interval_only, exactly the two constructed occurrences.
        iv = families("interval_only")
        self.assertEqual(len(iv), 1)
        f = iv[0]
        self.assertEqual(f.length, 3)
        self.assertEqual(sorted((o.row_id, o.start_index, o.end_index) for o in f.occurrences),
                         [("r", 0, 3), ("r", 3, 6)])
        by_start = {o.start_index: o for o in f.occurrences}
        self.assertEqual(by_start[0].event_ids, ("a0", "a1", "a2"))
        self.assertEqual(by_start[3].event_ids, ("b0", "b1", "b2"))
        # Absolute pitches are kept per occurrence; the constructed displacement is +7 semitones on every note.
        # (The displacement field transposition_semitones is specified only for strict transposition.)
        self.assertEqual(by_start[0].pitches, (60, 62, 64))
        self.assertEqual(by_start[3].pitches, (67, 69, 71))
        self.assertEqual({b - a for a, b in zip(by_start[0].pitches, by_start[3].pitches)}, {7})


if __name__ == "__main__":
    unittest.main()
