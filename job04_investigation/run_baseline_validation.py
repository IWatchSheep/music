"""JOB-04 baseline validation of the EXISTING experimental engine against independent ground truth.

Run from the project root:  python job04_investigation/run_baseline_validation.py
Writes job04_investigation/results/baseline_validation.json and prints a readable table.
Exit code 0 when the run completed (results are data, not pass/fail); 2 on a harness error.

Nothing here tunes the engine.  The sifter parameters are exactly those used by the existing
verify_group_discovery.py (A: min_gap 80 ms; B: defaults, min_repeats 2; C: leap 5; D: window 60 ms;
fixed-width control 400 ms; u = 100 ms; boundary tolerance 60 ms; random control: 100 seeds,
count-matched to each candidate's internal boundary count).  Standard library only.
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from music_model import group_discovery as gd          # noqa: E402  (engine under test, unmodified)
from job04_investigation.fixtures import all_passages   # noqa: E402

TOL = 60.0
U = 100.0
SEEDS = 100

SIFTERS = [
    ("A_rests", lambda nb: gd.sift_breath_rests(nb, min_gap_ms=80.0, u_ms=U)),
    ("B_motoric", lambda nb: gd.sift_motoric_rhythm(nb, u_ms=U, min_repeats=2)),
    ("C_contour", lambda nb: gd.sift_melodic_contour(nb, min_leap_semitones=5, u_ms=U)),
    ("D_crossrow", lambda nb: gd.sift_cross_row_handoffs(nb, window_ms=60.0, u_ms=U)),
    ("CTRL_fixed400", lambda nb: gd.control_fixed_width(nb, width_ms=400.0, u_ms=U)),
]


def internal(points, span):
    return sorted(b for b in set(points) if abs(b - span[0]) > TOL and abs(b - span[1]) > TOL)


def brute_force_tp(ref, disc):
    """Independent maximum one-to-one matching by exhaustive search (small inputs only)."""
    if not ref or not disc:
        return 0
    if len(ref) > 8 or len(disc) > 8:
        return None                                   # too large to brute-force; not checked
    best = 0
    small, large = (ref, disc) if len(ref) <= len(disc) else (disc, ref)
    for perm in itertools.permutations(range(len(large)), len(small)):
        best = max(best, sum(abs(small[i] - large[j]) <= TOL for i, j in enumerate(perm)))
    return best


def recurrence_capability():
    """Fields the engine returns: is there any representation of 'these groups recur'?"""
    fields = [f.name for f in dataclasses.fields(gd.GroupingResult)] + \
             [f.name for f in dataclasses.fields(gd.DiscoveredGroup)]
    words = ("recur", "repeat", "similar", "match", "pattern", "phrase_id", "cluster", "occurrence")
    hits = [f for f in fields if any(w in f.lower() for w in words)]
    return {"result_fields": fields, "recurrence_related_fields": hits}


def run_one(p):
    out = {"passage": p.name, "category": p.category, "description": p.description, "notes": p.notes,
           "span_ms": p.span_ms, "truth_boundaries_ms": p.boundaries_ms,
           "truth_internal_boundaries_ms": internal(p.boundaries_ms, p.span_ms),
           "truth_instances": [dataclasses.asdict(i) for i in p.instances],
           "truth_recurrences": p.recurrences, "methods": {}}
    ref_int = out["truth_internal_boundaries_ms"]
    for name, fn in SIFTERS:
        m_out = {}
        try:
            res = fn(p.notes_by_row)
        except Exception as ex:                        # recorded, never hidden
            m_out["error"] = f"{type(ex).__name__}: {ex}"
            m_out["traceback"] = traceback.format_exc()[-1500:]
            out["methods"][name] = m_out
            continue
        disc_int = internal(res.discovered_boundaries_ms, p.span_ms)
        m = gd.evaluate_boundaries(res.discovered_boundaries_ms, p.boundaries_ms, tolerance_ms=TOL,
                                   passage_span_ms=p.span_ms, internal_only=True)
        bf = brute_force_tp(ref_int, disc_int)
        # Group-level: is each truth phrase instance delimited by one discovered group (both ends within TOL)?
        inst_hits = []
        for inst in p.instances:
            groups = res.groups_by_row.get(inst.row, [])
            inst_hits.append(any(abs(g.start_ms - inst.start_ms) <= TOL and abs(g.end_ms - inst.end_ms) <= TOL
                                 for g in groups))
        m_out.update({
            "discovered_internal_ms": disc_int,
            "tp": m.true_positives, "fp": m.false_positives, "fn": m.false_negatives,
            "precision": round(m.precision, 4), "recall": round(m.recall, 4), "f1": round(m.f1_score, 4),
            "engine_vs_bruteforce_tp": ("agree" if bf is None or bf == m.true_positives else f"DISAGREE bf={bf}"),
            "groups_per_row": {r: [(g.start_ms, g.end_ms, len(g.notes)) for g in gs] for r, gs in res.groups_by_row.items()},
            "group_widths_ms": sorted({round(g.duration_ms, 3) for gs in res.groups_by_row.values() for g in gs}),
            "instances_delimited": inst_hits,
            "recurrences_reported": 0,                 # the engine has no recurrence output (see capability)
        })
        if ref_int and disc_int:
            mp, sp, mr, sr, mf, sf = gd.evaluate_monte_carlo_random_baseline(
                p.notes_by_row, target_boundary_count=len(disc_int), reference_boundaries_ms=p.boundaries_ms,
                num_seeds=SEEDS, tolerance_ms=TOL, passage_span_ms=p.span_ms, internal_only=True, u_ms=U)
            m_out["random_count_matched_f1"] = [round(mf, 4), round(sf, 4)]
        out["methods"][name] = m_out
    return out


def main() -> int:
    passages = all_passages()
    results = {"engine": "music_model/group_discovery.py (unmodified experimental prototype)",
               "tolerance_ms": TOL, "u_ms": U, "random_seeds": SEEDS,
               "capability": recurrence_capability(),
               "passages": [run_one(p) for p in passages]}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "baseline_validation.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)

    cap = results["capability"]
    print("Engine output fields:", ", ".join(cap["result_fields"]))
    print("Recurrence-related fields:", cap["recurrence_related_fields"] or "NONE")
    print()
    hdr = f"{'passage':<22}{'method':<15}{'disc':>5}{'TP':>4}{'FP':>4}{'FN':>4}{'P':>7}{'R':>7}{'F1':>7}  {'rand F1':<14}{'inst delimited':<16}{'widths':<14}{'bf'}"
    print(hdr); print("-" * len(hdr))
    for r in results["passages"]:
        for name, m in r["methods"].items():
            if "error" in m:
                print(f"{r['passage']:<22}{name:<15} ERROR {m['error']}")
                continue
            rnd = "%.3f+/-%.3f" % tuple(m["random_count_matched_f1"]) if "random_count_matched_f1" in m else "-"
            inst = f"{sum(m['instances_delimited'])}/{len(m['instances_delimited'])}" if m["instances_delimited"] else "-"
            widths = str(len(m["group_widths_ms"])) + (" (equal)" if len(m["group_widths_ms"]) == 1 else "")
            print(f"{r['passage']:<22}{name:<15}{len(m['discovered_internal_ms']):>5}{m['tp']:>4}{m['fp']:>4}{m['fn']:>4}"
                  f"{m['precision']:>7.3f}{m['recall']:>7.3f}{m['f1']:>7.3f}  {rnd:<14}{inst:<16}{widths:<14}{m['engine_vs_bruteforce_tp']}")
        print()
    total_rec = sum(len(r["truth_recurrences"]) for r in results["passages"])
    print(f"Ground-truth recurrence relations across all passages: {total_rec}; reported by the engine: 0 "
          f"(no recurrence output exists).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
