"""verify_group_discovery.py - Milestone 5A Verification & Sifter Benchmark.

Demonstrates and evaluates the "Mining-for-Gold" research principle on real MIDI
and controlled passages (Stage 1 Corrected Verification):
1. Passage 1: Calibration Passage (Synthetic Orchestral Duck Flight from real MIDI parser).
2. Passage 2: Held-Out Generalization Passage (Contrapuntal Non-Symmetric Phrasing).
3. Passage 3: Negative Control Passage (Continuous Irregular Non-Periodic Stream).

Evaluates 4 candidate sifters + 2 controls:
- Sifter A: Breath / Articulation Rest Sifter
- Sifter B: Motoric Rhythm Sifter
- Sifter C: Melodic Contour Sifter
- Sifter D: Cross-Row Hand-off Sifter (evaluated strictly without circular credit)
- Control 1: Fixed-Width Slicing
- Control 2: Fair Monte Carlo Random Baseline (100 reproducible seeds)

Evaluation Corrections & Integrity:
1. Evaluates Strictly Internal Boundaries (0 < t < T) separately from total coverage ([0, T]).
2. References accurately labeled as "Designer-Specified Analytical Score References".
3. Fractional units reported precisely without 0u rounding artifacts.
4. Exact source timing maintained without destructive grid snapping.
5. Maximum-cardinality one-to-one bipartite matching (augmenting path algorithm).
6. Transparent empty-reference scoring (Negative Control Specificity).
7. Fair random control matching exact internal boundary counts per sifter over 100 seeds.
8. Clearly reports limitations of small synthetic benchmarks.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Sequence, Tuple

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
from music_model.midi_fixture import create_synthetic_orchestral_midi_bytes
from music_model.midi_importer import MidiImporter, MidiParser


# ---------------------------------------------------------------------------
# Benchmark Passage Construction
# ---------------------------------------------------------------------------

class BenchmarkNote:
    """Explicit note container for benchmark passages."""

    def __init__(self, start_ms: float, end_ms: float, pitch: int, note_name: str = ""):
        self.start_ms = float(start_ms)
        self.end_ms = float(end_ms)
        self.pitch = int(pitch)
        self.note_name = note_name or f"Note_{pitch}"

    def __repr__(self) -> str:
        return f"{self.note_name}({self.pitch})[{self.start_ms:.1f}-{self.end_ms:.1f}ms]"


def load_calibration_passage() -> Tuple[Dict[str, List[Any]], List[float], str, Tuple[float, float]]:
    """Passage 1: Calibration Passage (Synthetic Orchestral Duck Flight).

    Loaded from real Type 1 MIDI bytes parsed through MidiParser and MidiImporter.
    Contains 4 tracks/rows with 21 notes over 4114 ms.

    Reference Documentation:
    - Status: Designer-Specified Analytical Score References.
    - Identification criteria:
        * 0.0 ms: Passage start
        * 840.0 ms: Horn breathing pause before next arpeggio gesture
        * 1200.0 ms: End of Measure 1 exposition (Low Bass pedal shift)
        * 2400.0 ms: End of Measure 2 & tempo transition point
        * 3257.0 ms: Climax transition (Woodwinds and Trumpets takeoff)
        * 4114.0 ms: Passage finale
    """
    midi_bytes = create_synthetic_orchestral_midi_bytes()
    parser = MidiParser()
    importer = MidiImporter(parser=parser)
    song = importer.import_bytes(
        midi_bytes,
        song_id="calib_duck_flight",
        title="Calibration Duck Flight",
        group_by="track",
    )

    notes_by_row: Dict[str, List[Any]] = {}
    for row in song.rows:
        notes_by_row[row.row_id] = list(row.events)

    reference_boundaries = [0.0, 840.0, 1200.0, 2400.0, 3257.0, 4114.0]
    description = (
        "Passage 1: Calibration Passage (Real SMF Type 1 MIDI Duck Flight, 4 rows, 21 notes, 4114ms)"
    )
    span = (0.0, 4114.0)
    return notes_by_row, reference_boundaries, description, span


def load_held_out_passage() -> Tuple[Dict[str, List[Any]], List[float], str, Tuple[float, float]]:
    """Passage 2: Held-Out Generalization Passage (Contrapuntal Non-Symmetric Phrasing).

    Used strictly for validation without re-tuning parameters.
    Contains 2 rows with contrasting phrase lengths and articulation pauses.

    Reference Documentation:
    - Status: Designer-Specified Analytical Score References.
    - Identification criteria:
        * 0.0 ms: Simultaneous entrance
        * 800.0 ms: Descant Phrase 1 conclusion (followed by 100ms rest)
        * 900.0 ms: Descant Phrase 2 entrance
        * 1500.0 ms: Bass Phrase 1 conclusion (followed by 300ms rest)
        * 1800.0 ms: Bass Phrase 2 entrance
        * 2000.0 ms: Descant Phrase 2 conclusion (followed by 200ms rest)
        * 2200.0 ms: Descant Phrase 3 entrance
        * 3200.0 ms: Final cadence
    """
    bass_notes = [
        BenchmarkNote(0.0, 750.0, 36, "C2"),
        BenchmarkNote(750.0, 1500.0, 43, "G2"),
        # 300ms silence [1500, 1800)
        BenchmarkNote(1800.0, 2500.0, 41, "F2"),
        BenchmarkNote(2500.0, 3200.0, 36, "C2"),
    ]
    descant_notes = [
        BenchmarkNote(0.0, 400.0, 60, "C4"),
        BenchmarkNote(400.0, 800.0, 64, "E4"),
        # 100ms silence [800, 900)
        BenchmarkNote(900.0, 1400.0, 67, "G4"),
        BenchmarkNote(1400.0, 2000.0, 72, "C5"),
        # 200ms silence [2000, 2200)
        BenchmarkNote(2200.0, 2700.0, 71, "B4"),
        BenchmarkNote(2700.0, 3200.0, 72, "C5"),
    ]
    notes_by_row = {
        "Row Bass": bass_notes,
        "Row Descant": descant_notes,
    }
    reference_boundaries = [0.0, 800.0, 900.0, 1500.0, 1800.0, 2000.0, 2200.0, 3200.0]
    description = (
        "Passage 2: Held-Out Generalization Passage (Contrapuntal Non-Symmetric Phrasing, 2 rows, 10 notes, 3200ms)"
    )
    span = (0.0, 3200.0)
    return notes_by_row, reference_boundaries, description, span


def load_negative_control_passage() -> Tuple[Dict[str, List[Any]], List[float], str, Tuple[float, float]]:
    """Passage 3: Negative Control Passage (Continuous Irregular Non-Periodic Stream).

    Contains no recurring motifs, no rests, no turning peaks, and no cross-row handoffs.
    Purpose: Verify that sifters do NOT hallucinate false groupings where no structure exists.

    Reference Documentation:
    - Status: Designer-Specified Analytical Score References.
    - Ground truth: Only passage boundaries [0.0, 1500.0] exist; ZERO valid internal boundaries.
    """
    durations = [110.0, 170.0, 230.0, 290.0, 310.0, 390.0]
    notes: List[BenchmarkNote] = []
    curr_t = 0.0
    for i, d in enumerate(durations):
        notes.append(BenchmarkNote(curr_t, curr_t + d, 60 + i, f"Chromatic_{60+i}"))
        curr_t += d

    notes_by_row = {"Row Unstructured": notes}
    reference_boundaries = [0.0, curr_t]
    description = (
        f"Passage 3: Negative Control Passage (Continuous Irregular Stream, 1 row, 6 notes, {int(curr_t)}ms)"
    )
    span = (0.0, curr_t)
    return notes_by_row, reference_boundaries, description, span


# ---------------------------------------------------------------------------
# Sifter Runner & Benchmark Evaluation
# ---------------------------------------------------------------------------

def run_sifter_benchmark_on_passage(
    notes_by_row: Dict[str, List[Any]],
    reference_boundaries: List[float],
    title: str,
    span: Tuple[float, float],
    u_ms: float = 100.0,
    tolerance_ms: float = 60.0,
) -> Dict[str, Any]:
    """Runs all 4 sifters + 2 controls on a passage, prints the evaluation and RETURNS the computed values."""
    computed: Dict[str, Any] = {"internal": {}, "random": {}, "results": {}}
    print("=" * 80)
    print(f"BENCHMARK EVALUATION: {title}")
    print("=" * 80)

    # 1. Timing Diagnostics
    diag = diagnose_passage_timing(notes_by_row, u_ms=u_ms)
    print(f"[Timing Diagnostics & Sanity Audit]")
    print(f"  Notes Analyzed:            {diag.notes_analyzed_count}")
    print(f"  Silence / Rest Intervals:  {len(diag.silence_intervals_ms)} detected")
    for s_i, e_i in diag.silence_intervals_ms[:3]:
        print(f"    - Silence interval: [{s_i:.1f}, {e_i:.1f}) ms (duration {e_i - s_i:.1f} ms)")
    if len(diag.silence_intervals_ms) > 3:
        print(f"    - ... and {len(diag.silence_intervals_ms) - 3} more silence interval(s)")

    print(f"  Polyphonic Overlaps:       {len(diag.overlapping_intervals_ms)} detected")
    for s_o, e_o, r_o in diag.overlapping_intervals_ms[:2]:
        print(f"    - Overlap in {r_o}: [{s_o:.1f}, {e_o:.1f}) ms")

    print(f"  Off-Grid Note Timings:     {diag.off_grid_notes_count} (Preserved without snapping)")
    print(f"  Malformed / Zero-dur notes:{diag.malformed_notes_count} (Defect count)")
    print()

    # 2. Reference Documentation
    internal_refs = [
        b for b in reference_boundaries
        if abs(b - span[0]) > tolerance_ms and abs(b - span[1]) > tolerance_ms
    ]
    print(f"[Reference Standards — Designer-Specified Analytical Score References]")
    print(f"  Total Reference Count (inc edges):    {len(reference_boundaries)} {[round(b, 1) for b in reference_boundaries]}")
    print(f"  Strictly Internal Reference Count:     {len(internal_refs)} {[round(b, 1) for b in internal_refs]}")
    print(f"  Maximum Cardinality Bipartite Matching Tolerance: +/- {tolerance_ms:.1f} ms")
    print(f"  Passage Interval:                     [{span[0]:.1f}, {span[1]:.1f}) ms")
    print()

    # 3. Run Candidate Sifters
    res_a = sift_breath_rests(notes_by_row, min_gap_ms=80.0, u_ms=u_ms)
    res_b = sift_motoric_rhythm(notes_by_row, u_ms=u_ms, min_repeats=2)
    res_c = sift_melodic_contour(notes_by_row, min_leap_semitones=5, u_ms=u_ms)
    res_d = sift_cross_row_handoffs(notes_by_row, window_ms=60.0, u_ms=u_ms)

    # 4. Run Control 1 (Fixed-Width Slicing)
    res_ctrl1 = control_fixed_width(notes_by_row, width_ms=400.0, u_ms=u_ms)

    all_candidate_results = [res_a, res_b, res_c, res_d, res_ctrl1]

    # -----------------------------------------------------------------------
    # Primary Table: Strictly Internal Boundaries (0 < t < T)
    # -----------------------------------------------------------------------
    print(f"[PRIMARY BENCHMARK: STRICTLY INTERNAL BOUNDARIES (0 < t < T)]")
    print(f"Evaluates phrase discovery without trivial start/end boundary inflation.")
    header = f"{'Method / Candidate':<36} | {'Discovered':<10} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<9} | {'Recall':<8} | {'F1 Score':<8} | {'Random F1 (100 runs)':<20}"
    print(header)
    print("-" * len(header))

    for r in all_candidate_results:
        m = evaluate_boundaries(
            r.discovered_boundaries_ms,
            reference_boundaries,
            tolerance_ms=tolerance_ms,
            passage_span_ms=span,
            internal_only=True,
        )
        # Compute fair matched Monte Carlo random baseline for this exact internal count
        m_p, s_p, m_r, s_r, m_f, s_f = evaluate_monte_carlo_random_baseline(
            notes_by_row,
            target_boundary_count=m.discovered_count,
            reference_boundaries_ms=reference_boundaries,
            num_seeds=100,
            tolerance_ms=tolerance_ms,
            passage_span_ms=span,
            internal_only=True,
            u_ms=u_ms,
        )
        computed["internal"][r.sifter_name] = m
        computed["random"][r.sifter_name] = (m_f, s_f)
        computed["results"][r.sifter_name] = r
        rand_str = f"{m_f:.3f} +/- {s_f:.3f}" if len(internal_refs) > 0 else "n/a (no internal refs)"
        print(
            f"{r.sifter_name:<36} | "
            f"{m.discovered_count:<10} | "
            f"{m.true_positives:<4} | "
            f"{m.false_positives:<4} | "
            f"{m.false_negatives:<4} | "
            f"{m.precision * 100:>8.1f}% | "
            f"{m.recall * 100:>7.1f}% | "
            f"{m.f1_score:>8.3f} | "
            f"{rand_str:<20}"
        )

    print()

    # -----------------------------------------------------------------------
    # Secondary Table: Total Boundary Coverage ([0, T]) — Milestone 5A Baseline
    # -----------------------------------------------------------------------
    print(f"[SECONDARY CHECK: TOTAL BOUNDARY COVERAGE ([0, T]) — Milestone 5A Baseline]")
    sec_header = f"{'Method / Candidate':<36} | {'Discovered':<10} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<9} | {'Recall':<8} | {'F1 Score':<8}"
    print(sec_header)
    print("-" * len(sec_header))

    target_count = max(len(res_d.discovered_boundaries_ms), len(reference_boundaries))
    res_ctrl2_single = control_random_grouping(
        notes_by_row, target_boundary_count=target_count, seed=42, u_ms=u_ms
    )
    all_results_with_ctrl2 = all_candidate_results + [res_ctrl2_single]

    for r in all_results_with_ctrl2:
        m = evaluate_boundaries(
            r.discovered_boundaries_ms,
            reference_boundaries,
            tolerance_ms=tolerance_ms,
            internal_only=False,
        )
        print(
            f"{r.sifter_name:<36} | "
            f"{m.discovered_count:<10} | "
            f"{m.true_positives:<4} | "
            f"{m.false_positives:<4} | "
            f"{m.false_negatives:<4} | "
            f"{m.precision * 100:>8.1f}% | "
            f"{m.recall * 100:>7.1f}% | "
            f"{m.f1_score:>8.3f}"
        )
    print()

    computed["diagnostics"] = diag
    # 5. LEGACY composite Row 1 segments (compatibility display only; Row 1 belongs to later jobs)
    for highlight_res in [res_d, res_a]:
        if highlight_res.row1_segments:
            print(f"[{highlight_res.sifter_name} — Row 1 Structural Segments]")
            print(f"  Total Composite Segments Derived: {len(highlight_res.row1_segments)}")
            for idx, seg in enumerate(highlight_res.row1_segments[:6]):
                u_str = f"({seg.formatted_units})" if seg.formatted_units else ""
                sub_flag = " [Sub-Unit < 1u]" if seg.is_sub_unit else ""
                print(
                    f"    Seg {idx+1}: [{seg.start_ms:.1f}, {seg.end_ms:.1f}) ms {u_str}{sub_flag} "
                    f"| Active Rows: {seg.active_row_count} | Active Grps: {seg.active_group_count} "
                    f"| Mean Pitch: {seg.mean_pitch:.1f}"
                )
            if len(highlight_res.row1_segments) > 6:
                print(f"    ... and {len(highlight_res.row1_segments) - 6} additional segment(s)")
            print()
    return computed


# ---------------------------------------------------------------------------
# Main Verification Execution
# ---------------------------------------------------------------------------

# Documented expectations (Stage 2a).  These pin the CORRECTED engine's behaviour on the three legacy
# passages as regression evidence; they are not proof of general discovery (README JOB-04 criteria).
# Passage 2 references are defined at rests, so Sifter A's score there follows from the reference
# definition.  Sifter C on Passage 1 changed in Stage 2a (a polyphonic track is no longer given an
# invented melodic order): 11 -> 10 internal boundaries, F1 0.400 -> 0.429.
SIFTERS = ("Sifter A: Breath / Articulation Rest Sifter", "Sifter B: Motoric Rhythm Sifter",
           "Sifter C: Melodic Contour / Gestural Sifter", "Sifter D: Cross-Row Hand-off Sifter")
FIXED = "Control 1: Fixed-Width (400ms)"


def _close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def check_expectations(p1: Dict[str, Any], p2: Dict[str, Any], p3: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    checks: List[Tuple[str, bool, str]] = []

    def add(name: str, ok: bool, observed: str) -> None:
        checks.append((name, bool(ok), observed))

    b1 = p1["internal"][SIFTERS[1]]
    add("P1 Sifter B internal: TP=2 FP=1 FN=2 (precision 2/3, recall 1/2, F1 4/7)",
        (b1.true_positives, b1.false_positives, b1.false_negatives) == (2, 1, 2) and _close(b1.f1_score, 4 / 7),
        f"TP={b1.true_positives} FP={b1.false_positives} FN={b1.false_negatives} "
        f"P={b1.precision:.4f} R={b1.recall:.4f} F1={b1.f1_score:.4f}")
    c1 = p1["internal"][SIFTERS[2]]
    add("P1 Sifter C internal: 10 discovered, TP=3 (Stage 2a polyphony correction)",
        (c1.discovered_count, c1.true_positives) == (10, 3), f"discovered={c1.discovered_count} TP={c1.true_positives}")
    add("P1 diagnostics: polyphonic rows reported", len(p1["diagnostics"].polyphonic_rows) >= 1,
        f"polyphonic_rows={p1['diagnostics'].polyphonic_rows}")
    a2 = p2["internal"][SIFTERS[0]]
    add("P2 Sifter A internal: P=R=F1=1 (references defined at rests)",
        _close(a2.precision, 1) and _close(a2.recall, 1) and _close(a2.f1_score, 1),
        f"P={a2.precision} R={a2.recall} F1={a2.f1_score}")
    for name in SIFTERS:
        m = p3["internal"][name]
        add(f"P3 negative control {name.split(':')[0]}: 0 internal false positives", m.false_positives == 0,
            f"FP={m.false_positives}")
    add("P3 negative control fixed-width: 3 internal false positives", p3["internal"][FIXED].false_positives == 3,
        f"FP={p3['internal'][FIXED].false_positives}")
    d2 = p2["results"][SIFTERS[3]]
    sub = [g for g in d2.row1_segments if _close(g.start_ms, 750.0) and _close(g.end_ms, 800.0)]
    add("P2 legacy Row 1 segment [750, 800) is 0.50u (no 0u collapse)",
        len(sub) == 1 and sub[0].formatted_units == "0.50u" and sub[0].is_sub_unit,
        f"{[(g.start_ms, g.end_ms, g.formatted_units) for g in sub]}")
    for label, pc in (("P1", p1), ("P2", p2), ("P3", p3)):
        for name in SIFTERS:
            r = pc["results"][name]
            union = sorted({b for bs in r.boundaries_by_row.values() for b in bs})
            add(f"{label} {name.split(':')[0]}: boundaries_by_row union equals discovered_boundaries_ms",
                union == r.discovered_boundaries_ms, f"{len(union)} vs {len(r.discovered_boundaries_ms)}")
    return checks


def main() -> int:
    print("================================================================================")
    print("MUSIC PROJECT - JOB-04 STAGE 2a: GROUP BOUNDARY CANDIDATE BENCHMARK (LEGACY PASSAGES)")
    print("================================================================================")
    print("All summary figures below are COMPUTED in this run; expectations are asserted and the exit")
    print("code is 1 if any fails.  These are boundary candidates, not recurrence discovery.")
    print()
    p1 = run_sifter_benchmark_on_passage(*load_calibration_passage(), u_ms=100.0, tolerance_ms=60.0)
    p2 = run_sifter_benchmark_on_passage(*load_held_out_passage(), u_ms=100.0, tolerance_ms=60.0)
    p3 = run_sifter_benchmark_on_passage(*load_negative_control_passage(), u_ms=100.0, tolerance_ms=60.0)

    print("================================================================================")
    print("COMPUTED SUMMARY (strictly internal boundaries, tolerance +/- 60 ms)")
    print("================================================================================")
    for label, pc in (("Passage 1", p1), ("Passage 2", p2), ("Passage 3", p3)):
        for name, m in pc["internal"].items():
            mf, sf = pc["random"][name]
            rnd = f"random count-matched F1 {mf:.3f} +/- {sf:.3f}" if m.reference_count else "no internal references"
            print(f"  {label} | {name:<45} | F1 {m.f1_score:.3f} | FP {m.false_positives} | {rnd}")
    print()
    checks = check_expectations(p1, p2, p3)
    failed = [c for c in checks if not c[1]]
    print("EXPECTATION CHECKS")
    for name, ok, observed in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({observed})")
    print()
    print(f"{len(checks) - len(failed)}/{len(checks)} expectation checks passed.")
    if failed:
        print("VERIFICATION FAILED (exit code 1)")
        return 1
    print("VERIFICATION PASSED (exit code 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
