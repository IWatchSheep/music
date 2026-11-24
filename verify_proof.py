"""Verification script for the Music Project Stage 1 mathematical proofs.

Demonstrates:
1. Stage 0 Proof: Events A, B, C generating variable-width columns and constant row [1, 2, 3, 2, 1].
2. Variable-width column demonstration with non-uniform durations.
3. Multi-column sound event continuity (single event spanning multiple derived columns).
"""

from __future__ import annotations

import sys
from music_model.constant_row import calculate_constant_row
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline


def run_stage_0_proof() -> bool:
    print("=" * 80)
    print("PROOFS PART 1: STAGE 0 MATHEMATICAL PROOF (Events A, B, C)")
    print("=" * 80)

    # 1. Setup events
    events = [
        SoundEvent(event_id="Sound A", row_id="Row A", start_time_ms=0, end_time_ms=3000, label="Low sustained sound"),
        SoundEvent(event_id="Sound B", row_id="Row B", start_time_ms=1000, end_time_ms=5000, label="Second layer"),
        SoundEvent(event_id="Sound C", row_id="Row C", start_time_ms=2000, end_time_ms=4000, label="Higher layer"),
    ]

    timeline = MusicTimeline()
    for e in events:
        timeline.add_event(e)

    boundaries = timeline.extract_boundaries()
    expected_boundaries = (0, 1000, 2000, 3000, 4000, 5000)

    print("\nSound Events Input:")
    for e in events:
        print(f"  - {e.event_id} ({e.row_id}): [{e.start_time_ms}, {e.end_time_ms}) ms ({e.duration_ms} ms)")

    print(f"\nExtracted Boundaries: {list(boundaries)} ms")
    assert boundaries == expected_boundaries, f"Boundaries mismatch: {boundaries} != {expected_boundaries}"
    print("  -> Boundary Extraction: PASSED")

    columns = timeline.build_columns()
    constant_row = calculate_constant_row(timeline)
    expected_constant_values = (1, 2, 3, 2, 1)

    print("\nDerived Time Columns & Active Rows:")
    print(f"{'Col':<5} | {'Interval (ms)':<16} | {'Duration':<10} | {'Active Events':<18} | {'Active Rows':<22} | {'Constant Value'}")
    print("-" * 90)

    for col in columns:
        events_str = ", ".join(col.active_event_ids)
        rows_str = ", ".join(col.active_row_ids)
        val = constant_row[col.index]
        print(
            f"{col.index:<5} | [{col.start_time_ms:>4}, {col.end_time_ms:>4}) ms  | "
            f"{col.duration_ms:>5} ms   | {events_str:<18} | {rows_str:<22} | {val}"
        )

    print("-" * 90)
    print(f"Calculated Constant Row: {list(constant_row.values)}")
    print(f"Expected Constant Row:   {list(expected_constant_values)}")

    assert constant_row.values == expected_constant_values, (
        f"Constant row mismatch: {constant_row.values} != {expected_constant_values}"
    )
    print("  -> Stage 0 Proof Verification: PASSED\n")
    return True


def run_variable_width_proof() -> bool:
    print("=" * 80)
    print("PROOFS PART 2: VARIABLE-WIDTH COLUMNS DEMONSTRATION")
    print("=" * 80)
    print("Demonstrating that time-column widths are naturally dictated by sound boundaries,")
    print("not by a pre-fixed artificial grid.\n")

    events = [
        SoundEvent(event_id="E1", row_id="Row 1", start_time_ms=0, end_time_ms=250, label="Short accent"),
        SoundEvent(event_id="E2", row_id="Row 2", start_time_ms=250, end_time_ms=1500, label="Medium phrase"),
        SoundEvent(event_id="E3", row_id="Row 3", start_time_ms=1000, end_time_ms=3000, label="Long sustained sound"),
        SoundEvent(event_id="E4", row_id="Row 4", start_time_ms=2500, end_time_ms=4000, label="Cadence tail"),
    ]

    timeline = MusicTimeline()
    for e in events:
        timeline.add_event(e)

    boundaries = timeline.extract_boundaries()
    columns = timeline.build_columns()
    constant_row = calculate_constant_row(timeline)

    print("Sound Events Input:")
    for e in events:
        print(f"  - {e.event_id} ({e.row_id}): [{e.start_time_ms:>4}, {e.end_time_ms:>4}) ms (duration: {e.duration_ms} ms)")

    print(f"\nDerived Boundaries ({len(boundaries)} points): {list(boundaries)} ms")
    print("\nVariable-Width Time Columns:")
    print(f"{'Col':<5} | {'Interval (ms)':<16} | {'Duration':<10} | {'Active Events':<18} | {'Active Rows':<20} | {'Active Row Count'}")
    print("-" * 88)

    durations = []
    for col in columns:
        durations.append(col.duration_ms)
        events_str = ", ".join(col.active_event_ids)
        rows_str = ", ".join(col.active_row_ids)
        print(
            f"{col.index:<5} | [{col.start_time_ms:>4}, {col.end_time_ms:>4}) ms  | "
            f"{col.duration_ms:>5} ms   | {events_str:<18} | {rows_str:<20} | {constant_row[col.index]}"
        )

    print("-" * 88)
    print(f"Resulting Column Durations: {durations} ms")
    assert len(set(durations)) > 1, "Durations must be non-uniform to prove variable width."
    print("  -> Variable-Width Verification: PASSED (Non-uniform column widths confirmed)\n")
    return True


def run_multi_column_continuity_proof() -> bool:
    print("=" * 80)
    print("PROOFS PART 3: SOUND EVENT CONTINUITY ACROSS COLUMNS")
    print("=" * 80)
    print("Demonstrating that a sound event spanning multiple columns remains ONE continuous object")
    print("and is not duplicated or split in the data model.\n")

    timeline = MusicTimeline()
    long_sound = SoundEvent("LongSound", "PadRow", 0, 5000, label="Continuous Ambient Pad")
    timeline.add_event(long_sound)

    # Add shorter punctuating sounds on another row that subdivide the timeline into 5 columns
    timeline.add_event(SoundEvent("Punc1", "LeadRow", 1000, 1500))
    timeline.add_event(SoundEvent("Punc2", "LeadRow", 2000, 2500))
    timeline.add_event(SoundEvent("Punc3", "LeadRow", 3000, 3500))

    columns = timeline.build_columns()
    print(f"Total Columns Derived: {len(columns)}")
    print(f"Total SoundEvent Objects in Timeline: {timeline.event_count}")

    # Verify that PadRow holds exactly ONE SoundEvent instance
    pad_row = timeline.get_row("PadRow")
    assert pad_row is not None
    assert len(pad_row) == 1, f"Expected 1 event in PadRow, got {len(pad_row)}"
    assert pad_row.events[0] is long_sound, "The event instance in the row must be the exact original object"

    # Count columns in which LongSound is active
    columns_spanning_long_sound = [c for c in columns if "LongSound" in c.active_event_ids]
    print(f"LongSound [0, 5000) ms is active in {len(columns_spanning_long_sound)} out of {len(columns)} derived columns.")
    assert len(columns_spanning_long_sound) == len(columns), "LongSound should be active in all columns from 0 to 5000 ms"

    print("  -> Continuity & Non-Duplication: PASSED\n")
    return True


if __name__ == "__main__":
    success = True
    success &= run_stage_0_proof()
    success &= run_variable_width_proof()
    success &= run_multi_column_continuity_proof()

    if success:
        print("=" * 80)
        print("ALL MATHEMATICAL PROOFS PASSED SUCCESSFULLY!")
        print("=" * 80)
        sys.exit(0)
    else:
        sys.exit(1)
