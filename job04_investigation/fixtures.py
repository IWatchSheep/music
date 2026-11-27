"""JOB-04 baseline investigation: controlled passages with ground truth fixed at construction.

Every passage is a concatenation of DESIGNED SEGMENTS (phrase instances, fillers, rests).  The ground
truth is written down while the passage is built and is never derived from any sifter:

  * boundaries_ms  - start/end of every designed sounding segment (the designer's segmentation);
  * instances      - phrase instances (row, start, end, phrase label, transformation);
  * recurrences    - which instances are recurrences of the same phrase, and how
                     (exact, transposed, rhythm-only, contour-only).

Ground-truth conventions (these are definitions of the benchmark, stated explicitly):
  * A "recurring phrase" has at least 3 notes.  Two-note coincidences are NOT recurrences (category
    'accidental').  I guess this threshold is reasonable for melodic phrases; it is a benchmark
    convention, not an Author requirement, and later reviewers may change it.
  * Pitches are MIDI numbers; times are exact integer milliseconds (no rounding anywhere).

Deterministic: the only randomness (category 'non_repeating') uses a fixed, recorded seed, and the
fixture is checked for its defining property by a brute-force check that is independent of the engine.
Standard library only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class Note:
    start_ms: float
    end_ms: float
    pitch: int
    note_name: str = ""
    event_id: str = ""


@dataclass(frozen=True)
class Instance:
    row: str
    start_ms: float
    end_ms: float
    phrase: str
    transform: str          # 'original', 'exact', 'transposed+7', 'rhythm', 'contour'
    n_notes: int


@dataclass
class Passage:
    name: str
    category: str
    description: str
    notes_by_row: Dict[str, List[Note]]
    boundaries_ms: List[float]
    instances: List[Instance] = field(default_factory=list)
    recurrences: List[Tuple[str, Tuple[int, ...]]] = field(default_factory=list)   # (relation, instance indices)
    span_ms: Tuple[float, float] = (0.0, 0.0)
    notes: str = ""


class _Builder:
    """Appends designed segments to rows and records the ground truth while doing so."""

    def __init__(self) -> None:
        self.rows: Dict[str, List[Note]] = {}
        self.t: Dict[str, float] = {}
        self.bounds: set = set()
        self.instances: List[Instance] = []
        self._eid = 0

    def segment(self, row: str, pitches: Sequence[int], durs: Sequence[float],
                phrase: Optional[str] = None, transform: str = "original") -> Optional[int]:
        assert len(pitches) == len(durs)
        t0 = self.t.get(row, 0.0)
        t = t0
        lst = self.rows.setdefault(row, [])
        for p, d in zip(pitches, durs):
            self._eid += 1
            lst.append(Note(t, t + d, p, f"P{p}", f"e{self._eid:03d}"))
            t += d
        self.t[row] = t
        self.bounds.update((t0, t))
        if phrase is not None:
            self.instances.append(Instance(row, t0, t, phrase, transform, len(pitches)))
            return len(self.instances) - 1
        return None

    def rest(self, row: str, d: float) -> None:
        self.t[row] = self.t.get(row, 0.0) + d

    def build(self, name, category, description, recurrences=(), notes="") -> Passage:
        all_notes = [n for r in self.rows.values() for n in r]
        span = (min(n.start_ms for n in all_notes), max(n.end_ms for n in all_notes)) if all_notes else (0.0, 0.0)
        return Passage(name, category, description, self.rows, sorted(self.bounds), self.instances,
                       list(recurrences), span, notes)


# Designed material (fixed in advance; not chosen by looking at any sifter output)
A_P, A_D = [60, 62, 64, 60], [250, 250, 250, 500]          # phrase A: 4 notes, 1250 ms
B_P, B_D = [67, 65, 69, 71], [250, 250, 500, 250]          # filler B (non-recurring)
C_P, C_D = [57, 53, 55, 50], [500, 250, 250, 250]          # filler C (non-recurring)
X_P, X_D = [72, 74, 76], [250, 250, 500]                   # phrase X: 3 notes
Y_P, Y_D = [48, 52, 55, 53, 50], [125, 125, 250, 250, 500]  # phrase Y: 5 notes


def exact_with_rests() -> Passage:
    b = _Builder()
    i0 = b.segment("melody", A_P, A_D, "A"); b.rest("melody", 250)
    b.segment("melody", B_P, B_D); b.rest("melody", 250)
    i1 = b.segment("melody", A_P, A_D, "A", "exact")
    return b.build("exact_with_rests", "exact_recurrence",
                   "Phrase A, rest, filler B, rest, phrase A again (rests of 250 ms between segments).",
                   [("exact", (i0, i1))])


def exact_legato() -> Passage:
    b = _Builder()
    i0 = b.segment("melody", A_P, A_D, "A")
    b.segment("melody", B_P, B_D)
    i1 = b.segment("melody", A_P, A_D, "A", "exact")
    b.segment("melody", C_P, C_D)
    i2 = b.segment("melody", A_P, A_D, "A", "exact")
    return b.build("exact_legato", "exact_recurrence",
                   "A B A C A with no silences: recurrence must be found from content, not from rests.",
                   [("exact", (i0, i1, i2))])


def transposed() -> Passage:
    b = _Builder()
    i0 = b.segment("melody", A_P, A_D, "A")
    b.segment("melody", B_P, B_D)
    i1 = b.segment("melody", [p + 7 for p in A_P], A_D, "A", "transposed+7")
    return b.build("transposed", "transposed_recurrence",
                   "A, filler B, A transposed up 7 semitones (identical intervals and rhythm), legato.",
                   [("transposed", (i0, i1))])


def rhythm_only() -> Passage:
    b = _Builder()
    r = [125, 125, 250, 500]
    i0 = b.segment("melody", [60, 64, 67, 72], r, "R")
    b.segment("melody", C_P, C_D)
    i1 = b.segment("melody", [65, 62, 69, 60], r, "R", "rhythm")
    return b.build("rhythm_only", "rhythmic_recurrence",
                   "Same duration pattern (125,125,250,500) with unrelated pitches, separated by filler C, legato.",
                   [("rhythm", (i0, i1))])


def contour_only() -> Passage:
    b = _Builder()
    d = [250, 250, 250, 250]
    i0 = b.segment("melody", [60, 62, 65, 63], d, "K")     # up, up, down
    b.segment("melody", C_P, C_D)
    i1 = b.segment("melody", [55, 60, 67, 62], d, "K", "contour")   # up, up, down; different intervals
    return b.build("contour_only", "contour_recurrence",
                   "Same up-up-down contour with different interval sizes, separated by filler C, legato.",
                   [("contour", (i0, i1))])


def different_lengths() -> Passage:
    b = _Builder()
    x0 = b.segment("melody", X_P, X_D, "X")
    y0 = b.segment("melody", Y_P, Y_D, "Y")
    x1 = b.segment("melody", X_P, X_D, "X", "exact")
    y1 = b.segment("melody", Y_P, Y_D, "Y", "exact")
    return b.build("different_lengths", "different_lengths",
                   "X (3 notes, 1000 ms) Y (5 notes, 1250 ms) X Y, legato: two recurring groups of different "
                   "duration and event count.", [("exact", (x0, x1)), ("exact", (y0, y1))])


def _has_repeated_interval_ngram(pitches: Sequence[int], n: int) -> bool:
    """Brute-force fixture property check (independent of the engine)."""
    iv = [b - a for a, b in zip(pitches, pitches[1:])]
    seen = set()
    for k in range(len(iv) - n + 1):
        g = tuple(iv[k:k + n])
        if g in seen:
            return True
        seen.add(g)
    return False


def _has_repeated_ngram(seq: Sequence[float], n: int) -> bool:
    """Brute-force check: does any run of n consecutive values occur twice?"""
    seen = set()
    for k in range(len(seq) - n + 1):
        g = tuple(seq[k:k + n])
        if g in seen:
            return True
        seen.add(g)
    return False


NON_REPEATING_SEED_START = 2026


def non_repeating() -> Passage:
    """Seeded random melody with no repeated 3-note interval pattern (exact or transposed) and no repeated 3-duration rhythm."""
    seed = NON_REPEATING_SEED_START
    while True:
        rng = random.Random(seed)
        pitches = [60]
        for _ in range(15):
            pitches.append(max(40, min(84, pitches[-1] + rng.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 7]))))
        durs = [rng.choice([125, 250, 375, 500]) for _ in pitches]
        if not _has_repeated_interval_ngram(pitches, 2) and not _has_repeated_ngram(durs, 3):
            break
        seed += 1
    b = _Builder()
    b.segment("melody", pitches, durs)
    p = b.build("non_repeating", "non_repeating",
                f"16 notes, seeded random walk (seed={seed}); verified: no repeated 3-note interval pattern and no repeated 3-duration rhythm.")
    p.notes = f"seed={seed}"
    return p


def accidental_similarity() -> Passage:
    """Two-note coincidences (+2 step twice, equal durations twice) but no 3-note recurrence."""
    b = _Builder()
    pitches = [60, 62, 67, 59, 64, 66, 61, 57, 65]       # +2 occurs twice (60->62, 64->66)
    durs = [250, 250, 500, 375, 250, 250, 625, 125, 500]
    assert not _has_repeated_interval_ngram(pitches, 2)
    b.segment("melody", pitches, durs)
    return b.build("accidental_similarity", "misleading_similarity",
                   "Contains a repeated single interval (+2) and repeated equal durations, but no phrase "
                   "of >= 3 notes recurs; ground truth: no recurrence.")


def cross_row() -> Passage:
    b = _Builder()
    i0 = b.segment("upper", A_P, A_D, "A")
    b.segment("upper", B_P, B_D)
    b.segment("lower", [36], [1250])                     # held bass under the first statement
    i1 = b.segment("lower", [p - 24 for p in A_P], A_D, "A", "transposed-24")
    return b.build("cross_row", "cross_row_recurrence",
                   "Phrase A in the upper row, answered by A two octaves lower in the lower row while the "
                   "upper row plays filler B.", [("transposed", (i0, i1))])


def empty_and_short() -> List[Passage]:
    out = []
    p = Passage("empty_dict", "empty", "No rows at all.", {}, [], span_ms=(0.0, 0.0)); out.append(p)
    p = Passage("empty_row", "empty", "One row with no notes.", {"melody": []}, [], span_ms=(0.0, 0.0)); out.append(p)
    b = _Builder(); b.segment("melody", [60], [500]); out.append(b.build("one_note", "very_short", "A single note."))
    b = _Builder(); b.segment("melody", [60, 67], [250, 250]); out.append(b.build("two_notes", "very_short", "Two notes."))
    return out


def all_passages() -> List[Passage]:
    return [exact_with_rests(), exact_legato(), transposed(), rhythm_only(), contour_only(),
            different_lengths(), non_repeating(), accidental_similarity(), cross_row()] + empty_and_short()
