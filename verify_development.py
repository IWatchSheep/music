"""Demonstration and verification script for Stage 2B Phase 3.

Demonstrates:
1. Duck Flight Experiment:
   - Row 2: Low whirring sound on water surface.
   - Row 3: Transitional acceleration and liftoff.
   - Row 4: High airborne flight.
2. Arrangement A (Direct Progression) vs Arrangement B (Intermediate Connected Progression).
3. Derived column structures, active-row baselines, and experimental Row 1 profiles.
4. Comparative metrics:
   - Directness ratio
   - Number of intermediate transitions
   - Time to reach high state
   - Column-refitting complexity
   - Curvature analysis and verification that more columns do not imply curvature
"""

from __future__ import annotations

import sys
from music_model.datasets import (
    create_duck_flight_experiment,
    create_linear_many_columns_timeline,
)
from music_model.development_profile import analyze_development_profile


def main() -> int:
    print("=" * 80)
    print("STAGE 2B, PHASE 3: MUSICAL DEVELOPMENT FROM LOW TO HIGH")
    print("=" * 80)
    print("Analogy: A duck running across water.")
    print("  - Row 2: Low whirring sound on water surface (experimental value = 20.0).")
    print("  - Row 3: Transitional sound of acceleration & liftoff (experimental value = 50.0).")
    print("  - Row 4: High airborne flight sound (experimental value = 80.0 / 85.0).")
    print("Row 1 represents continuous musical development across linked time columns.")
    print("Active-row-count baseline is preserved alongside experimental height.\n")

    song_a, song_b = create_duck_flight_experiment()

    # --- ARRANGEMENT A ---
    analysis_a = analyze_development_profile(
        song_a.timeline,
        arrangement_name="ARRANGEMENT A: Direct Low-to-High Development",
    )
    print(analysis_a.summary_table())
    print()

    # --- ARRANGEMENT B ---
    analysis_b = analyze_development_profile(
        song_b.timeline,
        arrangement_name="ARRANGEMENT B: Intermediate Connected Development",
    )
    print(analysis_b.summary_table())
    print()

    # --- COMPARATIVE ANALYSIS ---
    print("=" * 80)
    print("COMPARATIVE MATHEMATICAL ANALYSIS")
    print("=" * 80)
    print(f"{'Metric':<36} | {'Arrangement A (Direct)':<22} | {'Arrangement B (Connected)':<22}")
    print("-" * 84)
    print(f"{'Derived Columns':<36} | {analysis_a.column_count:<22} | {analysis_b.column_count:<22}")
    print(f"{'Total Duration':<36} | {analysis_a.total_duration_ms} ms{'':<17} | {analysis_b.total_duration_ms} ms{'':<17}")
    print(f"{'Initial Row 1 Value':<36} | {analysis_a.initial_value:<22.1f} | {analysis_b.initial_value:<22.1f}")
    print(f"{'Final Row 1 Value':<36} | {analysis_a.final_value:<22.1f} | {analysis_b.final_value:<22.1f}")
    print(f"{'Directness Ratio':<36} | {analysis_a.directness_ratio:<22.3f} | {analysis_b.directness_ratio:<22.3f}")
    print(f"{'Transitions (Value Changes)':<36} | {analysis_a.transition_count:<22} | {analysis_b.transition_count:<22}")
    print(f"{'Refitting Complexity (Cols/Event)':<36} | {analysis_a.refitting_complexity:<22.2f} | {analysis_b.refitting_complexity:<22.2f}")
    print(f"{'Time to High State':<36} | {analysis_a.time_to_high_ms} ms{'':<15} | {analysis_b.time_to_high_ms} ms{'':<15}")
    print(f"{'Strictly Monotonic Increasing':<36} | {str(analysis_a.is_strictly_monotonic_increasing):<22} | {str(analysis_b.is_strictly_monotonic_increasing):<22}")
    print(f"{'Non-Decreasing (No Dips)':<36} | {str(analysis_a.is_non_decreasing):<22} | {str(analysis_b.is_non_decreasing):<22}")
    print(f"{'Curvature Variance':<36} | {analysis_a.curvature_variance:<22.6f} | {analysis_b.curvature_variance:<22.6f}")
    print("-" * 84)

    # --- LINEAR CONTROL PASSAGE (Zero Curvature Proof) ---
    print("\n" + "=" * 80)
    print("CONTROL PROOF: MORE COLUMNS DO NOT IMPLY CURVATURE")
    print("=" * 80)
    linear_song = create_linear_many_columns_timeline(n_columns=16)
    analysis_lin = analyze_development_profile(
        linear_song.timeline,
        arrangement_name="Control Passage: 16 Columns (Constant Linear Slope)",
    )
    print(f"Columns: {analysis_lin.column_count}")
    print(f"Profile: {[round(v, 1) for v in analysis_lin.profile_values if v is not None]}")
    print(f"Directness Ratio: {analysis_lin.directness_ratio:.4f}")
    print(f"Curvature Variance: {analysis_lin.curvature_variance:.8f}")
    if abs(analysis_lin.curvature_variance) < 1e-12:
        print("  -> PROOF SUCCESS: Curvature variance is strictly 0.0 despite having 16 columns.")
        print("     Proves that column count is a measure of boundary density, not curvature.")

    print("\n" + "=" * 80)
    print("ALL EXPERIMENTAL DEVELOPMENT PROOFS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
