"""Pre-configured datasets for mathematical proofs and GUI demonstrations.

Includes:
1. Stage 1 Mathematical Proof (Events A, B, C)
2. Variable-Width Proof (Non-uniform column durations)
3. Sound Continuity Proof (One continuous event spanning multiple subdividing columns)
4. Progressive Refitting Stages (Stage A, Stage B, Stage C)
5. Dual Independent Songs (Song 1 vs Song 2 with non-shared grids)
6. 32-Column Stress Test Timeline
"""

from __future__ import annotations

from typing import Tuple

from music_model.song import ProgressiveRefitter, SongTimeline
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline


def create_stage_1_proof_timeline() -> MusicTimeline:
    """Stage 1 Proof: Events A, B, C yielding constant row [1, 2, 3, 2, 1]."""
    timeline = MusicTimeline()
    timeline.add_event(
        SoundEvent("Sound A", "Row A", 0, 3000, label="Low sustained sound")
    )
    timeline.add_event(
        SoundEvent("Sound B", "Row B", 1000, 5000, label="Second layer")
    )
    timeline.add_event(
        SoundEvent("Sound C", "Row C", 2000, 4000, label="Higher layer")
    )
    return timeline


def create_variable_width_timeline() -> MusicTimeline:
    """Variable-width demonstration with non-uniform column durations."""
    timeline = MusicTimeline()
    timeline.add_event(
        SoundEvent("E1", "Row 1", 0, 250, label="Short accent (250 ms)")
    )
    timeline.add_event(
        SoundEvent("E2", "Row 2", 250, 1500, label="Medium phrase (1250 ms)")
    )
    timeline.add_event(
        SoundEvent("E3", "Row 3", 1000, 3000, label="Long sustained sound (2000 ms)")
    )
    timeline.add_event(
        SoundEvent("E4", "Row 4", 2500, 4000, label="Cadence tail (1500 ms)")
    )
    return timeline


def create_continuity_timeline() -> MusicTimeline:
    """Multi-column continuity demonstration: single sound spanning across subdivisions."""
    timeline = MusicTimeline()
    timeline.add_event(
        SoundEvent("LongSound", "Pad Row", 0, 5000, label="Continuous Ambient Pad (5000 ms)")
    )
    timeline.add_event(
        SoundEvent("Punc1", "Lead Row", 1000, 1500, label="Staccato 1")
    )
    timeline.add_event(
        SoundEvent("Punc2", "Lead Row", 2000, 2500, label="Staccato 2")
    )
    timeline.add_event(
        SoundEvent("Punc3", "Lead Row", 3000, 3500, label="Staccato 3")
    )
    return timeline


def create_progressive_stage_timeline(stage: str) -> SongTimeline:
    """Create a SongTimeline representing one of the progressive refitting stages.

    Stages:
        'A': Row 2 alone -> [0, 3000) ms -> 1 column: [0, 3000), Row 1: [1]
        'B': Add Row 3 -> [1000, 5000) ms -> 3 columns, Row 1: [1, 2, 1]
        'C': Add Row 4 -> [2000, 4000) ms -> 5 columns, Row 1: [1, 2, 3, 2, 1]
    """
    stage_upper = stage.strip().upper()
    song = SongTimeline(
        f"progressive_stage_{stage_upper}",
        f"Progressive Refitting — Stage {stage_upper}",
    )
    # Row 2 (Sound A) is present in all stages
    sound_a = SoundEvent("Sound A", "Row 2", 0, 3000, label="Low sustained sound")
    song.add_event(sound_a)

    if stage_upper in ("B", "C"):
        sound_b = SoundEvent("Sound B", "Row 3", 1000, 5000, label="Second layer")
        song.add_event(sound_b)

    if stage_upper == "C":
        sound_c = SoundEvent("Sound C", "Row 4", 2000, 4000, label="Higher layer")
        song.add_event(sound_c)

    return song


def create_dual_independent_songs() -> Tuple[SongTimeline, SongTimeline]:
    """Create two independent songs with distinct, non-shared column grids.

    Song 1: 3 columns ([0, 2000), [2000, 4000), [4000, 6000)), Row 1: [1, 2, 3]
    Song 2: 5 columns ([250, 750), [750, 1500), [1500, 2250), [2250, 3000), [3000, 4000)), Row 1: [1, 2, 3, 2, 1]
    """
    song1 = SongTimeline("song_1", "Song 1: Direct Passage (3 Columns)", tempo_bpm=120.0)
    song1.add_event(SoundEvent("S1_Bass", "Row 2", 0, 6000, label="Foundation Bass"))
    song1.add_event(SoundEvent("S1_Mid", "Row 3", 2000, 6000, label="Mid Phrase"))
    song1.add_event(SoundEvent("S1_High", "Row 4", 4000, 6000, label="High Lead"))

    song2 = SongTimeline("song_2", "Song 2: Multi-Style Passage (5 Columns)", tempo_bpm=90.0)
    song2.add_event(SoundEvent("S2_Beat", "Row 2", 250, 2250, label="Rhythm Groove"))
    song2.add_event(SoundEvent("S2_Synth", "Row 3", 750, 3000, label="Synth Stabs"))
    song2.add_event(SoundEvent("S2_Chop", "Row 4", 1500, 4000, label="Vocal Chops"))

    return song1, song2


def create_32_column_timeline() -> SongTimeline:
    """Display stress test: create a synthetic timeline with at least 32 derived columns.

    Constructs 33 unique integer boundaries spanning 0 to 6400 ms:
    Boundaries: [0, 200, 400, 600, ..., 6400] ms -> exactly 32 columns.
    """
    song = SongTimeline("stress_32_col", "Many-Column Layout Stress Test (32 Derived Columns)")

    # Row 2: Even pulses [0, 400), [800, 1200), [1600, 2000), ...
    for k in range(8):
        t_start = k * 800
        t_end = t_start + 400
        song.add_event(SoundEvent(f"R2_P{k+1}", "Row 2", t_start, t_end, label=f"Beat {k+1}"))

    # Row 3: Staggered pulses [200, 600), [1000, 1400), ...
    for k in range(8):
        t_start = 200 + k * 800
        t_end = t_start + 400
        song.add_event(SoundEvent(f"R3_P{k+1}", "Row 3", t_start, t_end, label=f"Offbeat {k+1}"))

    # Row 4: Long pad [0, 6400) spanning all 32 columns
    song.add_event(SoundEvent("Pad_Long", "Row 4", 0, 6400, label="Master Pad [0, 6400) ms"))

    return song
