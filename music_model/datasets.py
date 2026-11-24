"""Pre-configured datasets for mathematical proofs and GUI demonstrations.

Includes:
1. Stage 1 Mathematical Proof (Events A, B, C)
2. Variable-Width Proof (Non-uniform column durations)
3. Sound Continuity Proof (One continuous event spanning multiple subdividing columns)
"""

from __future__ import annotations

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
