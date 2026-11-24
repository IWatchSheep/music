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
    create_progressive_stage_timeline,
    create_dual_independent_songs,
    create_32_column_timeline,
    create_duck_flight_experiment,
    create_linear_many_columns_timeline,
)
from music_model.development_profile import (
    DevelopmentAnalysis,
    analyze_development_profile,
    calculate_column_height,
    calculate_development_constant_row,
    get_event_height,
)
from music_model.midi_fixture import (
    create_synthetic_orchestral_midi_bytes,
    create_synthetic_orchestral_song,
)
from music_model.midi_importer import (
    MidiImporter,
    MidiNoteRaw,
    MidiParser,
    ParsedMidiFile,
    TempoEvent,
    TempoMap,
    pitch_to_note_name,
)
from music_model.passage_format import (
    load_song_from_file,
    save_song_to_file,
    song_from_dict,
    song_from_json,
    song_to_dict,
    song_to_json,
)
from music_model.song import (
    ProgressiveRefitter,
    RefitStep,
    SongTimeline,
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
    "create_progressive_stage_timeline",
    "create_dual_independent_songs",
    "create_32_column_timeline",
    "create_duck_flight_experiment",
    "create_linear_many_columns_timeline",
    "SongTimeline",
    "ProgressiveRefitter",
    "RefitStep",
    "get_event_height",
    "calculate_column_height",
    "calculate_development_constant_row",
    "DevelopmentAnalysis",
    "analyze_development_profile",
    "MidiParser",
    "MidiImporter",
    "ParsedMidiFile",
    "MidiNoteRaw",
    "TempoEvent",
    "TempoMap",
    "pitch_to_note_name",
    "create_synthetic_orchestral_midi_bytes",
    "create_synthetic_orchestral_song",
    "song_to_dict",
    "song_from_dict",
    "song_to_json",
    "song_from_json",
    "save_song_to_file",
    "load_song_from_file",
]
