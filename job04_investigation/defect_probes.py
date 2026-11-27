"""JOB-04 baseline: concrete probes for defects identified by reading music_model/group_discovery.py.

Run from the project root:  python job04_investigation/defect_probes.py
Each probe prints CONFIRMED / NOT CONFIRMED with the observed values.  The engine is not modified.
Exit code 0 when every probe ran (confirmation is data); 2 on a harness error.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from music_model import group_discovery as gd          # noqa: E402
from music_model.sound_event import SoundEvent          # noqa: E402
from job04_investigation.fixtures import Note           # noqa: E402

RESULTS = []


def probe(pid, claim):
    def deco(fn):
        try:
            confirmed, observed = fn()
        except Exception as ex:
            confirmed, observed = None, f"probe raised {type(ex).__name__}: {ex}"
        RESULTS.append({"id": pid, "claim": claim, "confirmed": confirmed, "observed": observed})
        tag = {True: "CONFIRMED", False: "NOT CONFIRMED", None: "PROBE ERROR"}[confirmed]
        print(f"[{pid}] {tag}: {claim}\n      observed: {observed}")
        return fn
    return deco


class NoPitch:
    def __init__(self, s, e):
        self.start_ms, self.end_ms = s, e


class TickOnly:
    def __init__(self, s, e, p):
        self.start_tick, self.end_tick, self.pitch = s, e, p


@probe("P01", "A note without any pitch attribute is silently given pitch 60 (no error, no flag).")
def _():
    _, _, p, _ = gd.extract_note_timing(NoPitch(0, 100))
    return p == 60, f"pitch={p}"


@probe("P02", "A tick-only object's MIDI ticks are used as milliseconds without conversion.")
def _():
    try:
        s, e, _, _ = gd.extract_note_timing(TickOnly(480, 960, 60))
    except ValueError as ex:                          # Stage 2a: AmbiguousTimingError (a ValueError)
        return False, f"rejected: {type(ex).__name__}: {ex}"
    return (s, e) == (480.0, 960.0), f"start={s}, end={e} (ticks 480/960 returned as ms)"


@probe("P03", "Fractional pitch (e.g. a WAV-estimated height 60.4) is rounded to an integer before analysis.")
def _():
    _, _, p, _ = gd.extract_note_timing(Note(0, 100, 60.4))   # type: ignore[arg-type]
    return p == 60, f"pitch={p}"


@probe("P04", "Exact rational source timing on a SoundEvent (attributes exact_*_sec_rational) is ignored; "
              "only integer-ms start_time_ms/end_time_ms are read.")
def _():
    ev = SoundEvent("w1", "Row 2", 0, 1, height=60.0,
                    attributes={"exact_start_sec_rational": "1/44100", "exact_end_sec_rational": "45/44100"})
    s, e, _, _ = gd.extract_note_timing(ev)
    exact_end_ms = 45 / 44100 * 1000
    return (s, e) == (0.0, 1.0), f"read start={s} end={e}; exact source end = {exact_end_ms:.6f} ms"


@probe("P05", "Sifter A, polyphony inside one row: a rest is reported while an earlier long note is still "
              "sounding, and the group end is the LAST-STARTED note's end, not the latest end.")
def _():
    row = {"r": [Note(0, 1000, 48), Note(0, 200, 60), Note(400, 600, 62)]}   # bass held 0-1000
    res = gd.sift_breath_rests(row, min_gap_ms=100.0)
    groups = [(g.start_ms, g.end_ms) for g in res.groups_by_row["r"]]
    split = len(groups) > 1
    return split, f"groups={groups} (bass sounds throughout 0-1000 ms, so no silence exists)"


@probe("P06", "Sifter B only tests three hard-coded spans (300/400/200 ms); a clean 500 ms periodic pattern "
              "is reported as non-repeating.")
def _():
    notes = [Note(k * 500, k * 500 + 250, 60 + (k % 2) * 7) for k in range(8)]
    notes += [Note(k * 500 + 250, k * 500 + 500, 64) for k in range(8)]
    res = gd.sift_motoric_rhythm({"r": notes}, u_ms=100.0)
    methods = sorted({g.method for g in res.groups_by_row["r"]})
    return methods == ["Sifter_B_NoRepetition"], f"methods={methods}"


@probe("P07", "Sifter B output groups are all equal-width slices of the chosen span (a periodic grid), "
              "not musically delimited groups.")
def _():
    notes = [Note(0, 300, 60), Note(300, 600, 62), Note(600, 900, 64), Note(900, 1500, 65), Note(1500, 1800, 67)]
    res = gd.sift_motoric_rhythm({"r": notes}, u_ms=100.0)
    widths = sorted({g.duration_ms for g in res.groups_by_row["r"]})
    return len(widths) == 1 and res.groups_by_row["r"][0].method.startswith("Sifter_B_Motoric"), \
        f"group widths={widths}, method={res.groups_by_row['r'][0].method}, note 900-1500 straddles slices"


@probe("P08", "Sifter D in dense two-row polyphony places a boundary between almost every pair of notes.")
def _():
    upper = [Note(k * 250, k * 250 + 250, 72 + k % 3) for k in range(8)]
    lower = [Note(k * 250 + 125, k * 250 + 375, 48) for k in range(7)]
    res = gd.sift_cross_row_handoffs({"u": upper, "l": lower}, window_ms=60.0)
    n_groups = len(res.groups_by_row["u"])
    return n_groups >= 7, f"upper row: {len(upper)} notes split into {n_groups} groups"


@probe("P09", "Monte Carlo baseline silently assumes the span (0, 1000) ms when passage_span_ms is omitted.")
def _():
    notes = {"r": [Note(0, 5000, 60)]}
    try:
        a = gd.evaluate_monte_carlo_random_baseline(notes, 2, [0.0, 2500.0, 5000.0], num_seeds=5,
                                                    tolerance_ms=60.0, passage_span_ms=None, internal_only=True)
    except ValueError as ex:                          # Stage 2a: span required
        return False, f"rejected: {ex}"
    src = open(os.path.join(ROOT, "music_model", "group_discovery.py"), encoding="utf-8").read()
    return "else (0.0, 1000.0)" in src, f"default present in source; result without span = {[round(x, 3) for x in a]}"


@probe("P10", "EvaluationMetrics.specificity is 1.0/0.0 by 'no false positive' rather than a true-negative "
              "rate, and F1 = 1.0 is reported when nothing exists and nothing is found.")
def _():
    m1 = gd.evaluate_boundaries([], [], 60.0)
    m2 = gd.evaluate_boundaries([100.0, 200.0, 300.0], [100.0, 200.0, 900.0], 60.0)
    return (m1.f1_score == 1.0 and m2.specificity == 0.0), \
        f"empty/empty F1={m1.f1_score}; 2 of 3 correct + 1 FP -> specificity={m2.specificity}"


@probe("P11", "Discovered boundaries are a union across rows: row attribution is lost in "
              "discovered_boundaries_ms (only recoverable from groups_by_row).")
def _():
    # Stage 2a revision: the baseline version of this probe checked only isinstance(float), which could
    # never fail; it now checks whether per-row boundaries are available.
    res = gd.sift_breath_rests({"a": [Note(0, 100, 60), Note(300, 400, 62)], "b": [Note(0, 400, 48)]})
    by_row = getattr(res, "boundaries_by_row", None)
    return not by_row, f"discovered_boundaries_ms={res.discovered_boundaries_ms}; boundaries_by_row={by_row}"


@probe("P12", "Every sifter result also derives Row 1 segments (derive_row1_from_discovered_groups), which "
              "belongs to later jobs (merger / transfer to Row 1).")
def _():
    res = gd.sift_breath_rests({"r": [Note(0, 100, 60), Note(300, 400, 62)]})
    return len(res.row1_segments) > 0, f"row1_segments={len(res.row1_segments)}"


@probe("P13", "verify_group_discovery.py prints hard-coded summary figures that differ from the values it "
              "computes, has no assertions, and always exits 0.")
def _():
    src = open(os.path.join(ROOT, "verify_group_discovery.py"), encoding="utf-8").read()
    hard = "0.571 vs 0.125 +/- 0.119" in src and "0.222 +/- 0.141" in src
    no_assert = "assert" not in src and "sys.exit(1)" not in src
    return hard and no_assert, "summary strings '0.125 +/- 0.119' and '0.222 +/- 0.141' are literals; " \
                               "computed values are 0.089 +/- 0.150 and 0.217 +/- 0.158 (see verify output)"


@probe("P14", "A SoundEvent with height=None (what the JOB-02 WAV importer emits for unpitched events) "
              "crashes extract_note_timing and therefore every sifter.")
def _():
    ev = SoundEvent("w2", "Row 2", 0, 500)                      # height defaults to None
    try:
        gd.sift_breath_rests({"Row 2": [ev]})
    except TypeError as ex:
        return True, f"TypeError: {ex}"
    return False, "no exception"


def main() -> int:
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "defect_probes.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=1)
    c = sum(r["confirmed"] is True for r in RESULTS)
    print(f"\n{c}/{len(RESULTS)} probes confirmed; errors: {sum(r['confirmed'] is None for r in RESULTS)}")
    return 0 if all(r["confirmed"] is not None for r in RESULTS) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
