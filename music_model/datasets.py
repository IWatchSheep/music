"""Pre-configured datasets for mathematical proofs and GUI demonstrations.

Includes:
1. Stage 1 Mathematical Proof (Events A, B, C)
2. Variable-Width Proof (Non-uniform column durations)
3. Sound Continuity Proof (One continuous event spanning multiple subdividing columns)
4. Progressive Refitting Stages (Stage A, Stage B, Stage C)
5. Dual Independent Songs (Song 1 vs Song 2 with non-shared grids)
6. 32-Column Stress Test Timeline
7. Duck Flight Experiment: Low-to-high musical development (Arrangement A vs B)
8. Linear Many-Columns Timeline: Proof that more columns do not imply curvature
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


def create_duck_flight_experiment() -> Tuple[SongTimeline, SongTimeline]:
    """Create two comparative arrangements of the duck running on water experiment.

    The user's theory:
    - Row 2: Low whirring sound on water surface (experimental height = 20.0).
    - Row 3: Transitional acceleration and liftoff sound (experimental height = 50.0).
    - Row 4: High airborne flight sound (experimental height = 80.0 / 85.0).

    Arrangement A: Direct low-to-high progression.
      - 3 events with clean progressive handoffs.
      - Produces 5 columns: [0, 1500), [1500, 2000), [2000, 3000), [3000, 3500), [3500, 5000) ms.
      - Experimental Row 1 values: [20.0, 35.0, 50.0, 65.0, 80.0].
      - Strictly monotonic, directness ratio = 1.0.

    Arrangement B: Intermediate connected progression.
      - 6 events with multiple intermediate transitions and recurring water contact.
      - Produces 11 columns over 6000 ms.
      - Experimental Row 1 values: [20.0, 32.5, 45.0, 35.0, 41.67, 40.0, 55.0, 65.0, 71.67, 70.0, 85.0].
      - Shows recurring transitions before achieving sustained high flight.
    """
    # --- Arrangement A: Direct Progression ---
    song_a = SongTimeline(
        "arrangement_a",
        "Arrangement A: Direct Low-to-High Development (5 Columns)",
        tempo_bpm=120.0,
        description="Direct transition from water run to liftoff to flight with clean progressive handoffs.",
    )
    song_a.add_event(
        SoundEvent(
            "A_Whir",
            "Row 2",
            0,
            2000,
            label="Low Whirring (Water Run)",
            height=20.0,
        )
    )
    song_a.add_event(
        SoundEvent(
            "A_Lift",
            "Row 3",
            1500,
            3500,
            label="Transitional Lift (Acceleration & Takeoff)",
            height=50.0,
        )
    )
    song_a.add_event(
        SoundEvent(
            "A_Flight",
            "Row 4",
            3000,
            5000,
            label="High Airborne Flight",
            height=80.0,
        )
    )

    # --- Arrangement B: More Intermediate Connections ---
    song_b = SongTimeline(
        "arrangement_b",
        "Arrangement B: Intermediate Connected Development (11 Columns)",
        tempo_bpm=100.0,
        description="Complex transitions with recurring water kicks and gradual staged liftoff.",
    )
    # Row 2: Initial run + recurring water kick
    song_b.add_event(
        SoundEvent(
            "B_Whir_1",
            "Row 2",
            0,
            1600,
            label="Initial Water Run",
            height=20.0,
        )
    )
    song_b.add_event(
        SoundEvent(
            "B_Whir_2",
            "Row 2",
            2000,
            3000,
            label="Water Kick & Trailing Splash",
            height=25.0,
        )
    )

    # Row 3: Early acceleration + secondary sustained lift
    song_b.add_event(
        SoundEvent(
            "B_Lift_1",
            "Row 3",
            1000,
            2400,
            label="Early Acceleration Thrust",
            height=45.0,
        )
    )
    song_b.add_event(
        SoundEvent(
            "B_Lift_2",
            "Row 3",
            2200,
            4200,
            label="Main Ascent & Wing Flap",
            height=55.0,
        )
    )

    # Row 4: Tentative airborne wingbeat + sustained soaring flight
    song_b.add_event(
        SoundEvent(
            "B_Flight_1",
            "Row 4",
            3200,
            4000,
            label="Tentative Airborne Glide",
            height=75.0,
        )
    )
    song_b.add_event(
        SoundEvent(
            "B_Flight_2",
            "Row 4",
            3800,
            6000,
            label="Sustained High Soaring Flight",
            height=85.0,
        )
    )

    return song_a, song_b


def create_linear_many_columns_timeline(n_columns: int = 16) -> SongTimeline:
    """Create a synthetic timeline with many columns whose development profile is perfectly linear.

    Proves mathematically that having many derived columns does NOT imply curvature.
    With constant rate of change dh/dt across all columns:
      - Slope s_j = constant
      - Second differences s_{j+1} - s_j = 0.0
      - Curvature variance = 0.0
    """
    if n_columns < 2:
        raise ValueError("n_columns must be at least 2")

    song = SongTimeline(
        f"linear_{n_columns}_col",
        f"Linear Control Passage ({n_columns} Columns, Zero Curvature)",
    )
    step_duration = 500  # ms per column
    h_start = 10.0
    h_step = 5.0

    for i in range(n_columns):
        t0 = i * step_duration
        t1 = (i + 1) * step_duration
        h_val = h_start + i * h_step
        # Stagger across Row 2 and Row 3 to maintain multiple rows
        row_id = "Row 2" if i % 2 == 0 else "Row 3"
        song.add_event(
            SoundEvent(
                f"Lin_E{i+1}",
                row_id,
                t0,
                t1,
                label=f"Step {i+1} ({h_val:.1f})",
                height=h_val,
            )
        )

    return song
