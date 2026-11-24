"""Music Model Package.

Mathematical foundation for temporary sound rows, linked time columns,
and derived constant musical rows.
"""

from music_model.constant_row import (
    ConstantRow,
    calculate_constant_row,
    count_distinct_active_rows,
    count_active_events,
)
from music_model.datasets import (
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
    create_continuity_timeline,
)
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow
from music_model.timeline import MusicTimeline, TimeColumn

__all__ = [
    "SoundEvent",
    "TemporaryRow",
    "TimeColumn",
    "MusicTimeline",
    "ConstantRow",
    "calculate_constant_row",
    "count_distinct_active_rows",
    "count_active_events",
    "create_stage_1_proof_timeline",
    "create_variable_width_timeline",
    "create_continuity_timeline",
]
