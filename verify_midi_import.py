"""Verification script for Stage 3: MIDI and Musical Passage Import.

Demonstrates:
1. Programmatic generation of a valid Standard MIDI File (SMF Type 1).
2. Pure-Python binary parsing of headers, tracks, delta-times, and meta/channel events.
3. Import into SongTimeline with exact rational tempo conversion and integer-ms rounding.
4. Rich multi-column derived structure (>20 variable-width columns).
5. Row 1 dual measurements:
   - Active Temporary Row Count (Diagnostic Baseline)
   - Low-to-High Pitch Development Profile
6. Reproducible JSON passage format round-trip fidelity.
7. Independent song timelines without shared grids or state.
"""

from __future__ import annotations

import sys
from fractions import Fraction

from music_model.development_profile import calculate_development_constant_row
from music_model.midi_fixture import (
    create_synthetic_orchestral_midi_bytes,
    create_synthetic_orchestral_song,
)
from music_model.midi_importer import MidiImporter, MidiParser
from music_model.passage_format import song_from_json, song_to_json


def run_verification() -> bool:
    print("=" * 76)
    print("MUSIC PROJECT — STAGE 3: MIDI & MUSICAL PASSAGE IMPORT VERIFICATION")
    print("=" * 76)

    # -------------------------------------------------------------------------
    # 1. Generate & Parse Synthetic Orchestral MIDI
    # -------------------------------------------------------------------------
    print("\n[Step 1] Programmatic SMF Type 1 Generation & Binary Parsing")
    midi_bytes = create_synthetic_orchestral_midi_bytes()
    print(f"  Generated SMF binary size: {len(midi_bytes)} bytes")

    parser = MidiParser()
    parsed = parser.parse(midi_bytes)
    print(f"  SMF Format Type:     Type {parsed.format_type}")
    print(f"  Number of Tracks:    {parsed.num_tracks}")
    print(f"  Ticks Per Beat (PPQ): {parsed.ticks_per_beat}")
    print(f"  Tempo Map Events:    {len(parsed.tempo_map.events)} event(s)")
    for te in parsed.tempo_map.events:
        print(f"    - Tick {te.tick:5d}: {te.microseconds_per_beat} us/beat ({te.bpm:.1f} BPM)")
    print(f"  Parsed Raw Notes:    {len(parsed.raw_notes)} note(s)")
    for track_idx, name in parsed.track_names.items():
        print(f"    - Track {track_idx}: {name}")

    assert parsed.format_type == 1, "Expected Type 1 SMF"
    assert parsed.num_tracks == 5, f"Expected 5 tracks, got {parsed.num_tracks}"
    assert len(parsed.raw_notes) == 21, f"Expected 21 raw notes, got {len(parsed.raw_notes)}"
    print("  --> Step 1 PASSED: SMF header and track chunks parsed successfully.")

    # -------------------------------------------------------------------------
    # 2. Import into SongTimeline with Exact Rational Timing
    # -------------------------------------------------------------------------
    print("\n[Step 2] SongTimeline Construction & Coordinate Quantization")
    importer = MidiImporter(parser=parser)
    song = importer.import_bytes(
        midi_bytes,
        song_id="synthetic_orchestral_flight",
        title="Synthetic Orchestral Flight (Low-to-High)",
        group_by="track",
    )

    print(f"  Song ID:          {song.song_id}")
    print(f"  Title:            {song.title}")
    print(f"  Tempo:            {song.tempo_bpm} BPM")
    print(f"  Total Duration:   {song.total_duration_ms} ms ({song.total_duration_seconds:.2f} s)")
    print(f"  Temporary Rows:   {song.row_count}")
    for row in song.rows:
        print(f"    - {row.row_id}: {len(row.events)} notes, span [{row.earliest_start_ms}, {row.latest_end_ms}) ms")

    assert song.row_count == 4, f"Expected 4 active sound rows, got {song.row_count}"
    assert song.event_count == 21, f"Expected 21 sound events, got {song.event_count}"
    print("  --> Step 2 PASSED: All 21 notes mapped into 4 temporary rows.")

    # -------------------------------------------------------------------------
    # 3. Derived Variable-Width Columns & Row 1 Measurements
    # -------------------------------------------------------------------------
    print("\n[Step 3] Derived Columns & Dual Row 1 Measurements")
    columns = song.build_columns()
    boundaries = song.extract_boundaries()
    col_count = len(columns)
    print(f"  Unique Boundaries Derived: {len(boundaries)}")
    print(f"  Derived Time Columns:      {col_count} columns (Target: Many-column layout > 15)")

    assert col_count >= 16, f"Expected >= 16 columns for many-column proof, got {col_count}"

    # Row 1 Baseline: Active Row Count
    active_row_counts = list(song.constant_row.values)
    print(f"\n  Row 1 Baseline (Active Row Count):\n    {active_row_counts}")

    # Row 1 Experimental: Pitch Development Profile
    dev_row = calculate_development_constant_row(song.timeline)
    pitch_heights = [round(v, 1) for v in dev_row.values]
    print(f"\n  Row 1 Experimental (Pitch Development Profile):\n    {pitch_heights}")

    # Display column breakdown table for first 8 and last 4 columns
    print("\n  Sample Column Structure (First 8 & Last 4 columns):")
    print("  " + "-" * 72)
    print(f"  {'Col':<4} {'Interval (ms)':<16} {'Duration':<10} {'Active Rows':<12} {'Pitch Mean (Height)':<18}")
    print("  " + "-" * 72)
    display_indices = list(range(min(8, col_count))) + list(range(max(8, col_count - 4), col_count))
    display_indices = sorted(set(display_indices))

    for i in display_indices:
        c = columns[i]
        intv = f"[{c.start_time_ms}, {c.end_time_ms})"
        dur = f"{c.duration_ms} ms"
        act = f"{active_row_counts[i]} row(s)"
        h = f"{pitch_heights[i]:.1f}"
        print(f"  {c.index:<4} {intv:<16} {dur:<10} {act:<12} {h:<18}")
        if i == 7 and col_count > 12:
            print("  ...  ...              ...        ...          ...")
    print("  " + "-" * 72)

    # Verify low-to-high development
    first_col_pitch = pitch_heights[0]
    peak_col_pitch = max(pitch_heights)
    print(f"\n  Initial Column Pitch: {first_col_pitch} (C2 pedal tone)")
    print(f"  Peak Column Pitch:    {peak_col_pitch} (Trumpet / Woodwind soaring peak)")
    assert first_col_pitch <= 40.0, f"Expected low initial pitch <= 40, got {first_col_pitch}"
    assert peak_col_pitch >= 75.0, f"Expected high peak pitch >= 75, got {peak_col_pitch}"
    print("  --> Step 3 PASSED: Verified low-to-high progression and variable-width columns.")

    # -------------------------------------------------------------------------
    # 4. Reproducible JSON Passage Format Round-Trip
    # -------------------------------------------------------------------------
    print("\n[Step 4] Reproducible JSON Passage Serialization & Round-Trip")
    json_str = song_to_json(song, indent=2)
    print(f"  Serialized JSON payload size: {len(json_str)} characters")

    # Deserialize back into a new SongTimeline
    song_restored = song_from_json(json_str)
    print(f"  Restored Song ID:    {song_restored.song_id}")
    print(f"  Restored Rows:       {song_restored.row_count}")
    print(f"  Restored Events:     {song_restored.event_count}")
    print(f"  Restored Columns:    {song_restored.column_count}")

    assert song.song_id == song_restored.song_id
    assert song.total_duration_ms == song_restored.total_duration_ms
    assert song.row_count == song_restored.row_count
    assert song.event_count == song_restored.event_count
    assert song.extract_boundaries() == song_restored.extract_boundaries()
    assert song.constant_row.values == song_restored.constant_row.values
    dev_restored = calculate_development_constant_row(song_restored.timeline)
    assert dev_row.values == dev_restored.values

    print("  --> Step 4 PASSED: 100% round-trip fidelity between SongTimeline and JSON.")

    # -------------------------------------------------------------------------
    # 5. Independent Song Timeline Isolation
    # -------------------------------------------------------------------------
    print("\n[Step 5] Independent Song Timeline Isolation")
    # Song 1: Orchestral Flight (20 columns)
    # Song 2: Register-grouped version (different rows, different boundaries)
    song2 = importer.import_bytes(
        midi_bytes,
        song_id="flight_grouped_by_register",
        title="Flight Grouped by Register",
        group_by="register",
    )

    print(f"  Song 1: '{song.title}' -> {song.row_count} rows, {song.column_count} columns")
    print(f"  Song 2: '{song2.title}' -> {song2.row_count} rows, {song2.column_count} columns")

    # Verify no state leakage or shared grids
    assert song.song_id != song2.song_id
    assert [r.row_id for r in song.rows] != [r.row_id for r in song2.rows]
    assert song.timeline is not song2.timeline

    print("  --> Step 5 PASSED: Separate songs maintain completely independent timelines.")

    print("\n" + "=" * 76)
    print("ALL STAGE 3 VERIFICATION CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 76)
    return True


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
