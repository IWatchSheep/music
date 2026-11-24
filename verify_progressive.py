"""Verification script for Progressive Column Refitting and Independent Song Timelines.

Demonstrates:
1. Sequential progressive refitting within a single song across Stage A, Stage B, Stage C.
2. Preservation of Sound A's interval and object identity across all stages.
3. Independent Song 2 construction with its own temporary rows and column structure.
4. Proof of isolation: mutations to Song 2 have zero effect on Song 1.
"""

from __future__ import annotations

import sys
from music_model.song import ProgressiveRefitter, SongTimeline
from music_model.sound_event import SoundEvent


def run_progressive_refitting_proof() -> bool:
    print("=" * 80)
    print("PART 1: PROGRESSIVE COLUMN REFITTING WITHIN A SONG")
    print("=" * 80)
    print("Demonstrating how Row 2 sets initial columns, Row 3 refits them, and Row 4 refits again.\n")

    song1 = SongTimeline("song_1", "Progressive Refitting Passage (Song 1)")
    refitter = ProgressiveRefitter(song1)

    sound_a = SoundEvent("Sound A", "Row 2", 0, 3000, label="Low sustained bass")
    sound_b = SoundEvent("Sound B", "Row 3", 1000, 5000, label="Melody phrase")
    sound_c = SoundEvent("Sound C", "Row 4", 2000, 4000, label="Harmony layer")

    # --- STAGE A: Row 2 only ---
    print("--- STAGE A: Row 2 Introduced (Initial Columns) ---")
    step_a = refitter.add_temporary_row_with_events("Row 2", [sound_a], row_label="Bass Group")
    print(f"Sound Added: {sound_a.event_id} [{sound_a.start_time_ms}, {sound_a.end_time_ms}) ms")
    print(f"Resulting Boundaries: {list(step_a.boundaries)} ms")
    print(f"Column Count: {step_a.column_count}")
    for col in step_a.columns:
        print(f"  Col {col.index}: [{col.start_time_ms}, {col.end_time_ms}) ms (Δ {col.duration_ms} ms) | Active: {col.active_row_ids}")
    print(f"Row 1 (Constant Row): {list(step_a.constant_row.values)}")

    assert step_a.boundaries == (0, 3000), f"Expected (0, 3000), got {step_a.boundaries}"
    assert step_a.column_count == 1, f"Expected 1 column, got {step_a.column_count}"
    assert step_a.constant_row.values == (1,), f"Expected (1,), got {step_a.constant_row.values}"
    print("  -> Stage A: PASSED\n")

    # --- STAGE B: Add Row 3 ---
    print("--- STAGE B: Row 3 Introduced (Columns Refit) ---")
    step_b = refitter.add_temporary_row_with_events("Row 3", [sound_b], row_label="Melody Group")
    print(f"Sound Added: {sound_b.event_id} [{sound_b.start_time_ms}, {sound_b.end_time_ms}) ms")
    print(f"Resulting Boundaries: {list(step_b.boundaries)} ms")
    print(f"Column Count: {step_b.column_count}")
    for col in step_b.columns:
        print(f"  Col {col.index}: [{col.start_time_ms}, {col.end_time_ms}) ms (Δ {col.duration_ms} ms) | Active: {col.active_row_ids}")
    print(f"Row 1 (Constant Row): {list(step_b.constant_row.values)}")

    assert step_b.boundaries == (0, 1000, 3000, 5000), f"Expected (0, 1000, 3000, 5000), got {step_b.boundaries}"
    assert step_b.column_count == 3, f"Expected 3 columns, got {step_b.column_count}"
    assert step_b.constant_row.values == (1, 2, 1), f"Expected (1, 2, 1), got {step_b.constant_row.values}"
    print("  -> Stage B: PASSED\n")

    # --- STAGE C: Add Row 4 ---
    print("--- STAGE C: Row 4 Introduced (Columns Refit Again) ---")
    step_c = refitter.add_temporary_row_with_events("Row 4", [sound_c], row_label="Harmony Group")
    print(f"Sound Added: {sound_c.event_id} [{sound_c.start_time_ms}, {sound_c.end_time_ms}) ms")
    print(f"Resulting Boundaries: {list(step_c.boundaries)} ms")
    print(f"Column Count: {step_c.column_count}")
    for col in step_c.columns:
        print(f"  Col {col.index}: [{col.start_time_ms}, {col.end_time_ms}) ms (Δ {col.duration_ms} ms) | Active: {col.active_row_ids}")
    print(f"Row 1 (Constant Row): {list(step_c.constant_row.values)}")

    assert step_c.boundaries == (0, 1000, 2000, 3000, 4000, 5000)
    assert step_c.column_count == 5
    assert step_c.constant_row.values == (1, 2, 3, 2, 1)
    print("  -> Stage C: PASSED\n")

    # Verify Sound A identity and interval preservation
    print("--- VERIFYING SOUND EVENT INTERVAL & IDENTITY PRESERVATION ---")
    stored_a = song1.get_event("Sound A")
    assert stored_a is sound_a, "Sound A object identity must be preserved"
    assert stored_a.start_time_ms == 0, "Sound A start time must remain 0"
    assert stored_a.end_time_ms == 3000, "Sound A end time must remain 3000"
    assert stored_a.duration_ms == 3000, "Sound A duration must remain 3000"
    print(f"Sound A is identical: [{stored_a.start_time_ms}, {stored_a.end_time_ms}) ms throughout all refits.")
    print("  -> Sound Event Preservation: PASSED\n")
    return True


def run_independent_songs_proof() -> bool:
    print("=" * 80)
    print("PART 2: INDEPENDENT SONGS PROOF (NO CROSS-SONG GRID SHARING)")
    print("=" * 80)

    # Song 1: 3 boundaries, 2 columns
    song1 = SongTimeline("song_1", "Song 1 (Classical)", tempo_bpm=120.0)
    song1.add_event(SoundEvent("S1_Bass", "Row 2", 0, 4000))
    song1.add_event(SoundEvent("S1_Lead", "Row 3", 2000, 4000))

    # Song 2: Completely different timing, 6 boundaries, 5 columns
    song2 = SongTimeline("song_2", "Song 2 (Modern)", tempo_bpm=90.0)
    song2.add_event(SoundEvent("S2_Beat", "Row 2", 250, 1500))
    song2.add_event(SoundEvent("S2_Synth", "Row 3", 500, 2500))
    song2.add_event(SoundEvent("S2_Chop", "Row 4", 1000, 1750))

    print(f"Song 1 Title: '{song1.title}' | Tempo: {song1.tempo_bpm} BPM")
    print(f"  Boundaries: {list(song1.extract_boundaries())} ms")
    print(f"  Columns ({song1.column_count}): {[(c.start_time_ms, c.end_time_ms) for c in song1.build_columns()]}")
    print(f"  Row 1 (Constant Row): {list(song1.constant_row.values)}")

    print(f"\nSong 2 Title: '{song2.title}' | Tempo: {song2.tempo_bpm} BPM")
    print(f"  Boundaries: {list(song2.extract_boundaries())} ms")
    print(f"  Columns ({song2.column_count}): {[(c.start_time_ms, c.end_time_ms) for c in song2.build_columns()]}")
    print(f"  Row 1 (Constant Row): {list(song2.constant_row.values)}")

    assert song1.extract_boundaries() == (0, 2000, 4000)
    assert song1.column_count == 2
    assert song1.constant_row.values == (1, 2)

    assert song2.extract_boundaries() == (250, 500, 1000, 1500, 1750, 2500)
    assert song2.column_count == 5
    assert song2.constant_row.values == (1, 2, 3, 2, 1)

    print("\n--- PROVING STRICT ISOLATION ---")
    print("Modifying Song 2 by adding a new event [3000, 4500) ms...")
    song2.add_event(SoundEvent("S2_Outro", "Row 5", 3000, 4500))

    print(f"Song 2 revised columns: {song2.column_count} columns")
    print(f"Checking Song 1 state...")
    print(f"  Song 1 Boundaries: {list(song1.extract_boundaries())} ms (unchanged)")
    print(f"  Song 1 Columns: {song1.column_count} columns (unchanged)")
    print(f"  Song 1 Constant Row: {list(song1.constant_row.values)} (unchanged)")

    assert song1.extract_boundaries() == (0, 2000, 4000)
    assert song1.column_count == 2
    assert song1.constant_row.values == (1, 2)
    assert song2.column_count == 7

    print("  -> Multi-Song Isolation Proof: PASSED\n")
    return True


if __name__ == "__main__":
    success = True
    success &= run_progressive_refitting_proof()
    success &= run_independent_songs_proof()

    if success:
        print("=" * 80)
        print("ALL PROGRESSIVE REFITTING & SONG INDEPENDENCE PROOFS PASSED!")
        print("=" * 80)
        sys.exit(0)
    else:
        sys.exit(1)
