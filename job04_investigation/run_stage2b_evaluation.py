"""JOB-04 Stage 2b: development-set evaluation of discover_sound_groups() with comparison controls.

Run from the project root:  python job04_investigation/run_stage2b_evaluation.py
Writes job04_investigation/results/stage2b_evaluation.json and stage2b_examples.txt.
Exit code: 0 when every asserted expectation holds, 1 if any fails, 2 on a harness error.

Asserted expectations come from the CONSTRUCTION of the 13 frozen development passages (fixtures.py),
not from engine output.  Everything else (incidental, nested, ambiguous, control results) is reported.

Counting policy
  * A ground-truth relation (type, instances) is FOUND by a method when one family of that method has
    occurrence windows that include every instance window; 'exact match' when the sets are equal.
  * Primary method per relation type: exact -> exact, transposed -> transposition, rhythm -> rhythm,
    contour -> contour.  Stricter relations also satisfy weaker methods ('implied'), reported separately.
  * Maximal families are classified as intended_primary (occurrence set equals an intended relation of
    that method's type), intended_implied (equals an intended relation of a stricter type),
    contains_intended (every occurrence contains an intended instance; e.g. 'X Y' containing X),
    overlaps_intended, or incidental (touches no intended instance).  Nested families are counted
    separately and never as independent confirmations.
  * The ground truth lists intended phrases only; it does not exhaust mathematically valid matches.
    Incidental matches are reported, not counted as defects.
Controls
  * fixed-width (400 ms, legacy Control 1) and seeded random slices (count-matched): instance
    delimitation within +/- 60 ms, compared with discovered occurrences of the primary method.
  * shuffled surrogates, 100 seeds each, per stream:
      S1 pitch_shuffle   - permutes pitches among pitched notes; PRESERVES every onset/duration and the
                           pitch multiset; DESTROYS pitch order (affects exact/transposition/contour).
      S2 rhythm_shuffle  - permutes (duration, following-gap) units and rebuilds onsets from the stream
                           start; PRESERVES the pitch sequence, the duration and gap multisets and the
                           total span; DESTROYS rhythmic order (affects exact/transposition/rhythm).
      S3 note_shuffle    - permutes whole (pitch, duration, gap) units; PRESERVES the note multiset;
                           DESTROYS both orders.
    Reported: observed maximal-family count, surrogate mean/max, and the fraction of surrogates with a
    count >= observed.  This is a descriptive comparison on tiny passages, NOT a significance test.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import traceback
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from music_model import group_discovery as gd                     # noqa: E402
from music_model.group_discovery import discover_sound_groups       # noqa: E402
from job04_investigation.fixtures import Note, all_passages          # noqa: E402

TOL = 60.0
SEEDS = 100
METHODS_ALL = ("exact", "transposition", "interval_only", "rhythm", "rhythm_proportional", "contour")
PRIMARY = {"exact": "exact", "transposed": "transposition", "rhythm": "rhythm", "contour": "contour"}
STRENGTH = {"exact": 0, "transposed": 1, "rhythm": 2, "contour": 2}
MSTRENGTH = {"exact": 0, "transposition": 1, "interval_only": 2, "rhythm": 2, "rhythm_proportional": 3, "contour": 3}


def instance_window(passage, inst):
    row = sorted(passage.notes_by_row[inst.row], key=lambda n: (n.start_ms, n.end_ms, n.event_id))
    s = [k for k, n in enumerate(row) if n.start_ms == inst.start_ms]
    e = [k for k, n in enumerate(row) if n.end_ms == inst.end_ms]
    assert s and e, f"instance not aligned with notes: {inst}"
    return (inst.row, s[0], e[-1] + 1)


def wset(f):
    return frozenset((o.row_id, o.start_index, o.end_index) for o in f.occurrences)


def contains(big, small):
    return big[0] == small[0] and big[1] <= small[1] and small[2] <= big[2]


def evaluate_passage(p, res):
    inst_w = [instance_window(p, i) for i in p.instances]
    relations = []
    for rtype, idxs in p.recurrences:
        want = frozenset(inst_w[i] for i in idxs)
        entry = {"type": rtype, "instances": sorted(want), "primary_method": PRIMARY[rtype], "found_by": {}}
        for m in METHODS_ALL:
            hits = [f for f in res.all_families if f.method == m and want <= wset(f)]
            if hits:
                best = sorted(hits, key=lambda f: (wset(f) != want, not f.is_maximal, f.family_key))[0]
                entry["found_by"][m] = {"family_key": best.family_key, "is_maximal": best.is_maximal,
                                        "exact_set_match": wset(best) == want, "length": best.length}
        relations.append(entry)
    intended_sets = [(frozenset(r["instances"]), r["type"]) for r in relations]
    all_inst = set(inst_w)

    per_method = {}
    for m in METHODS_ALL:
        fams = [f for f in res.all_families if f.method == m]
        maxi = [f for f in fams if f.is_maximal]
        cls = {}
        for f in maxi:
            ws = wset(f)
            c = "incidental"
            for iset, rtype in intended_sets:
                if ws == iset:
                    c = "intended_primary" if PRIMARY[rtype] == m else "intended_implied"
                    break
            else:
                if inst_w and all(any(contains(w, i) for i in all_inst) for w in ws):
                    c = "contains_intended"
                elif any(w[0] == i[0] and w[1] < i[2] and i[1] < w[2] for w in ws for i in all_inst):
                    c = "overlaps_intended"
            cls[c] = cls.get(c, 0) + 1
        ambiguous = sum(1 for i in all_inst if sum(1 for f in maxi if any(contains(w, i) or contains(i, w) for w in wset(f))) >= 2)
        per_method[m] = {"families": len(fams), "maximal": len(maxi), "nested": len(fams) - len(maxi),
                         "classification_of_maximal": cls, "instances_with_alternative_maximal_candidates": ambiguous}
    return relations, per_method


def delimitation_controls(p, res, rng_seed=0):
    """Fraction of truth instances delimited (both ends within TOL) by discovery vs fixed/random slices."""
    if not p.instances:
        return None
    inst = [(i.row, i.start_ms, i.end_ms) for i in p.instances]
    primary = {PRIMARY[t] for t, _ in p.recurrences}
    occ = [(o.row_id, o.start_ms, o.end_ms) for f in res.all_families if f.method in primary for o in f.occurrences]

    def hit(cands):
        return sum(1 for r, s, e in inst if any(r == cr and abs(s - cs) <= TOL and abs(e - ce) <= TOL for cr, cs, ce in cands))
    fixed = gd.control_fixed_width(p.notes_by_row, width_ms=400.0)
    fx = [(g.row_id, g.start_ms, g.end_ms) for gs in fixed.groups_by_row.values() for g in gs]
    k = max(1, len({(r, s, e) for r, s, e in occ}))
    rnd_hits = []
    for seed in range(SEEDS):
        rng = random.Random(seed)
        c = []
        for _ in range(k):
            row = rng.choice(sorted(p.notes_by_row))
            notes = p.notes_by_row[row]
            lo, hi = min(n.start_ms for n in notes), max(n.end_ms for n in notes)
            a, b = sorted((lo + rng.random() * (hi - lo), lo + rng.random() * (hi - lo)))
            c.append((row, a, b))
        rnd_hits.append(hit(c))
    return {"instances": len(inst), "discovery_primary_occurrences": len(set(occ)), "discovery_delimited": hit(occ),
            "fixed400_delimited": hit(fx), "random_count_matched_mean_delimited": sum(rnd_hits) / SEEDS,
            "random_slices_per_seed": k}


def _units(notes):
    notes = sorted(notes, key=lambda n: (n.start_ms, n.end_ms, n.event_id))
    gaps = [notes[k + 1].start_ms - notes[k].end_ms for k in range(len(notes) - 1)] + [0.0]
    return notes, [(n.pitch, n.end_ms - n.start_ms, g) for n, g in zip(notes, gaps)]


def surrogate(p, kind, seed):
    rng = random.Random(seed)
    out = {}
    for row, notes in sorted(p.notes_by_row.items()):
        notes, units = _units(notes)
        if not notes:
            out[row] = []
            continue
        if kind == "pitch_shuffle":
            ps = [u[0] for u in units]; rng.shuffle(ps)
            units = [(ps[k], d, g) for k, (_, d, g) in enumerate(units)]
        elif kind == "rhythm_shuffle":
            dg = [(d, g) for _, d, g in units]; rng.shuffle(dg)
            units = [(units[k][0], d, g) for k, (d, g) in enumerate(dg)]
        else:
            rng.shuffle(units)
        t = notes[0].start_ms
        new = []
        for k, (pitch, d, g) in enumerate(units):
            new.append(Note(t, t + d, pitch, f"P{pitch}", f"{row}_s{k}"))
            t += d + g
        out[row] = new
    return out


def shuffle_controls(p, res):
    obs = {m: sum(1 for f in res.all_families if f.method == m and f.is_maximal) for m in METHODS_ALL}
    out = {}
    for kind in ("pitch_shuffle", "rhythm_shuffle", "note_shuffle"):
        counts = {m: [] for m in METHODS_ALL}
        for seed in range(SEEDS):
            r = discover_sound_groups(surrogate(p, kind, seed), methods=METHODS_ALL)
            for m in METHODS_ALL:
                counts[m].append(sum(1 for f in r.all_families if f.method == m and f.is_maximal))
        out[kind] = {m: {"observed": obs[m], "surrogate_mean": round(sum(v) / SEEDS, 3), "surrogate_max": max(v),
                         "fraction_surrogates_ge_observed": round(sum(1 for x in v if x >= obs[m]) / SEEDS, 3)}
                     for m, v in counts.items()}
    return out


def describe(res, limit=12):
    lines = []
    for s in res.streams:
        lines.append(f"  stream row={s.row_id!r} voice={s.voice_id!r} notes={s.note_count} status={s.status} unpitched={s.unpitched_count}")
    for f in [f for f in res.all_families if f.is_maximal][:limit]:
        lines.append(f"  [{f.method}] n={f.length} maximal independent={f.independent_occurrence_count} "
                     f"same_as={list(f.same_occurrences_as)} params={dict(f.parameters)}")
        lines.append(f"     key: {f.family_key[:150]}")
        for o in f.occurrences:
            extra = f" transp={o.transposition_semitones}" if o.transposition_semitones is not None else ""
            extra += f" scale={o.scale_factor}" if o.scale_factor is not None else ""
            lines.append(f"     occ {o.row_id}/{o.voice_id} [{o.start_index},{o.end_index}) {float(o.exact_start_ms):.3f}-"
                         f"{float(o.exact_end_ms):.3f} ms ids={list(o.event_ids)}{extra}")
    nested = [f for f in res.all_families if not f.is_maximal]
    lines.append(f"  ... {len(nested)} nested families (each linked to its parent via nested_in)")
    if res.rejected_candidates:
        lines.append(f"  ... {len(res.rejected_candidates)} rejected candidates (overlapping-only), e.g. {res.rejected_candidates[0].family_key[:90]}")
    return lines


def main() -> int:
    passages = all_passages()
    report = {"methods": METHODS_ALL, "tolerance_ms": TOL, "seeds": SEEDS, "passages": []}
    checks = []
    examples = []
    for p in passages:
        t0 = time.perf_counter()
        res = discover_sound_groups(p.notes_by_row, methods=METHODS_ALL)
        dt = time.perf_counter() - t0
        res2 = discover_sound_groups(p.notes_by_row, methods=METHODS_ALL)
        relations, per_method = evaluate_passage(p, res)
        entry = {"passage": p.name, "category": p.category, "seconds": round(dt, 4), "search_complete": res.search_complete,
                 "windows_examined": dict(res.windows_examined), "relations": relations, "per_method": per_method,
                 "delimitation_controls": delimitation_controls(p, res),
                 "shuffle_controls": shuffle_controls(p, res) if p.notes_by_row and any(p.notes_by_row.values()) else None}
        report["passages"].append(entry)
        checks.append((f"{p.name}: deterministic (two runs identical)", res.all_families == res2.all_families, ""))
        checks.append((f"{p.name}: search complete", res.search_complete, str(res.search_notes)))
        for r in relations:
            fb = r["found_by"].get(r["primary_method"])
            checks.append((f"{p.name}: intended {r['type']} relation found by {r['primary_method']}", fb is not None,
                           json.dumps(fb) if fb else "MISSING"))
        if p.category in ("non_repeating", "misleading_similarity"):
            for m in ("exact", "transposition", "rhythm"):
                checks.append((f"{p.name}: no {m} family (constructed: no repeated 3-note pattern)",
                               per_method[m]["families"] == 0, f"families={per_method[m]['families']}"))
        if p.category in ("empty", "very_short"):
            checks.append((f"{p.name}: no families", res.all_families == (), f"{len(res.all_families)}"))
        if p.name in ("transposed", "different_lengths", "cross_row", "exact_legato"):
            examples.append(f"=== {p.name}: {p.description}")
            examples.extend(describe(res))
    # Qualitative example on real MIDI (no ground truth): the legacy calibration passage.
    try:
        import verify_group_discovery as vg
        notes_by_row, _, desc, _ = vg.load_calibration_passage()
        res = discover_sound_groups(notes_by_row, methods=("exact", "transposition", "rhythm", "contour"))
        examples.append(f"=== legacy calibration passage (real MIDI; NO ground truth; qualitative only): {desc}")
        examples.extend(describe(res, limit=6))
        report["midi_calibration_streams"] = [(s.row_id, s.status, s.note_count) for s in res.streams]
    except Exception as ex:                                   # reported, not hidden
        examples.append(f"=== legacy calibration passage: ERROR {type(ex).__name__}: {ex}")

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "stage2b_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str)
    with open(os.path.join(HERE, "results", "stage2b_examples.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(examples) + "\n")

    # Human-readable summary
    print(f"{'passage':<22}{'relations found (primary)':<28}{'maximal fams e/t/r/c':<24}{'incidental e/t/r/c':<22}{'nested e/t/r/c':<20}{'delim disc/fix/rnd'}")
    for e in report["passages"]:
        rel = e["relations"]
        found = f"{sum(1 for r in rel if r['primary_method'] in r['found_by'])}/{len(rel)}"
        pm = e["per_method"]
        mx = "/".join(str(pm[m]["maximal"]) for m in ("exact", "transposition", "rhythm", "contour"))
        inc = "/".join(str(pm[m]["classification_of_maximal"].get("incidental", 0)) for m in ("exact", "transposition", "rhythm", "contour"))
        nst = "/".join(str(pm[m]["nested"]) for m in ("exact", "transposition", "rhythm", "contour"))
        dc = e["delimitation_controls"]
        dl = f"{dc['discovery_delimited']}/{dc['fixed400_delimited']}/{dc['random_count_matched_mean_delimited']:.2f} of {dc['instances']}" if dc else "-"
        print(f"{e['passage']:<22}{found:<28}{mx:<24}{inc:<22}{nst:<20}{dl}")
    print("\nShuffle controls (maximal-family counts; observed vs surrogate mean, fraction of 100 surrogates >= observed):")
    for e in report["passages"]:
        sc = e["shuffle_controls"]
        if not sc or not e["relations"] and e["category"] not in ("non_repeating", "misleading_similarity"):
            continue
        parts = []
        for kind in ("pitch_shuffle", "rhythm_shuffle", "note_shuffle"):
            v = sc[kind]
            parts.append(f"{kind[:5]}: " + " ".join(f"{m[:4]}={v[m]['observed']}/{v[m]['surrogate_mean']}({v[m]['fraction_surrogates_ge_observed']})"
                                                     for m in ("exact", "transposition", "rhythm", "contour")))
        print(f"  {e['passage']:<22} " + " | ".join(parts))
    failed = [c for c in checks if not c[1]]
    print("\nEXPECTATION CHECKS (from fixture construction)")
    for name, ok, obs in checks:
        if not ok or "intended" in name:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {obs[:110] if not ok else ''}")
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
