"""Song-level timeline container and progressive column refitting.

Contains:
1. SongTimeline: A self-contained musical song container encapsulating its own
   MusicTimeline, temporary sound rows, derived columns, boundaries, and constant row.
2. ProgressiveRefitter: A demonstration and inspection engine tracking how time
   columns dynamically refit as temporary rows and sound events are introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Tuple, Union

from music_model.constant_row import (
    ConstantRow,
    MeasurementFunction,
    calculate_constant_row,
    count_distinct_active_rows,
)
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow
from music_model.timeline import MusicTimeline, TimeColumn


class SongTimeline:
    """A self-contained musical song model.

    Each song owns its own sound events, temporary rows, derived variable-width
    columns, and constant row. Songs are strictly isolated: no mutable state or
    time-column grid is shared across songs.

    Attributes:
        song_id: Unique identifier for this song.
        title: Descriptive title of the song or musical excerpt.
        tempo_bpm: Optional tempo in beats per minute for musical timing experiments.
        description: Optional notes regarding the passage or style.
    """

    def __init__(
        self,
        song_id: str,
        title: str,
        tempo_bpm: Optional[float] = None,
        description: str = "",
    ) -> None:
        if not isinstance(song_id, str) or not song_id.strip():
            raise ValueError(f"song_id must be a non-empty string, got {song_id!r}")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"title must be a non-empty string, got {title!r}")
        if tempo_bpm is not None:
            if not isinstance(tempo_bpm, (int, float)) or tempo_bpm <= 0:
                raise ValueError(f"tempo_bpm must be a positive number, got {tempo_bpm!r}")

        self.song_id: str = song_id
        self.title: str = title
        self.tempo_bpm: Optional[float] = float(tempo_bpm) if tempo_bpm is not None else None
        self.description: str = description

        # Each song encapsulates its own dedicated MusicTimeline instance
        self._timeline: MusicTimeline = MusicTimeline()

    @property
    def timeline(self) -> MusicTimeline:
        """The internal MusicTimeline instance for this song."""
        return self._timeline

    def add_row(self, row: TemporaryRow) -> None:
        """Add a TemporaryRow to this song's timeline."""
        self._timeline.add_row(row)

    def create_row(self, row_id: str, label: str = "") -> TemporaryRow:
        """Create and register a new TemporaryRow in this song."""
        return self._timeline.create_row(row_id=row_id, label=label)

    def get_row(self, row_id: str) -> Optional[TemporaryRow]:
        """Retrieve a TemporaryRow by ID from this song."""
        return self._timeline.get_row(row_id)

    def add_event(self, event: SoundEvent) -> None:
        """Add a sound event to this song.

        Raises:
            ValueError: If an event with the same event_id already exists in this song.
        """
        self._timeline.add_event(event)

    def get_event(self, event_id: str) -> Optional[SoundEvent]:
        """Find a sound event by ID within this song."""
        return self._timeline.get_event(event_id)

    def has_event(self, event_id: str) -> bool:
        """Check if an event ID exists in this song."""
        return self._timeline.has_event(event_id)

    @property
    def rows(self) -> Tuple[TemporaryRow, ...]:
        """Tuple of temporary rows in this song."""
        return self._timeline.rows

    @property
    def all_events(self) -> Tuple[SoundEvent, ...]:
        """Tuple of all sound events in this song."""
        return self._timeline.all_events

    def extract_boundaries(self) -> Tuple[int, ...]:
        """Derive sorted unique boundary timestamps (in milliseconds) for this song."""
        return self._timeline.extract_boundaries()

    def get_active_events_at(self, time_ms: Union[int, float]) -> List[SoundEvent]:
        """Return all sound events active at time_ms under half-open interval [start, end)."""
        return self._timeline.get_active_events_at(time_ms)

    def build_columns(self) -> Tuple[TimeColumn, ...]:
        """Derive variable-width time columns for this song."""
        return self._timeline.build_columns()

    def calculate_constant_row(
        self,
        measurement_fn: Optional[MeasurementFunction] = None,
        measurement_name: str = "Active Temporary Row Count",
    ) -> ConstantRow:
        """Derive Row 1 (the constant musical row) from this song's temporary rows."""
        return calculate_constant_row(
            self._timeline,
            measurement_fn=measurement_fn,
            measurement_name=measurement_name,
        )

    @property
    def constant_row(self) -> ConstantRow:
        """The default constant musical row for this song (Active Temporary Row Count)."""
        return self.calculate_constant_row()

    @property
    def column_count(self) -> int:
        """Number of derived time columns in this song."""
        return len(self.build_columns())

    @property
    def row_count(self) -> int:
        """Number of temporary rows in this song."""
        return self._timeline.row_count

    @property
    def event_count(self) -> int:
        """Total number of sound events in this song."""
        return self._timeline.event_count

    @property
    def total_duration_ms(self) -> int:
        """Total duration of this song in milliseconds."""
        return self._timeline.total_duration_ms

    @property
    def total_duration_seconds(self) -> float:
        """Total duration of this song in seconds."""
        return self._timeline.total_duration_seconds

    def __repr__(self) -> str:
        return (
            f"SongTimeline(song_id={self.song_id!r}, title={self.title!r}, "
            f"rows={self.row_count}, events={self.event_count}, cols={self.column_count})"
        )


@dataclass(frozen=True)
class RefitStep:
    """An immutable record of a single step in progressive column refitting.

    Attributes:
        step_index: 0-based sequential step number.
        description: Description of the action performed (e.g. 'Add Row 2 (Sound A)').
        added_row_id: The temporary row ID introduced in this step.
        added_event_ids: The event IDs introduced in this step.
        boundaries: The resulting boundary set after refitting.
        columns: The resulting derived time columns.
        constant_row: The resulting calculated constant row.
    """

    step_index: int
    description: str
    added_row_id: str
    added_event_ids: Tuple[str, ...]
    boundaries: Tuple[int, ...]
    columns: Tuple[TimeColumn, ...]
    constant_row: ConstantRow

    @property
    def column_count(self) -> int:
        return len(self.columns)


class ProgressiveRefitter:
    """Demonstrates and tracks progressive column refitting as temporary rows are added.

    Each addition recomputes the combined column structure while preserving the
    exact intervals and identities of all original SoundEvent objects.
    """

    def __init__(self, song: Optional[SongTimeline] = None) -> None:
        if song is None:
            song = SongTimeline("progressive_demo", "Progressive Refitting Demonstration")
        self._song: SongTimeline = song
        self._steps: List[RefitStep] = []

    @property
    def song(self) -> SongTimeline:
        """The underlying SongTimeline being progressively constructed."""
        return self._song

    @property
    def steps(self) -> Tuple[RefitStep, ...]:
        """All refit steps recorded so far."""
        return tuple(self._steps)

    @property
    def current_step(self) -> Optional[RefitStep]:
        """The most recent refit step, or None if no steps have been performed."""
        return self._steps[-1] if self._steps else None

    @property
    def step_count(self) -> int:
        """Total number of refit steps recorded."""
        return len(self._steps)

    def get_step(self, index: int) -> RefitStep:
        """Retrieve a specific refit step by index."""
        return self._steps[index]

    def add_temporary_row_with_events(
        self,
        row_id: str,
        events: List[SoundEvent],
        row_label: str = "",
        step_description: str = "",
    ) -> RefitStep:
        """Add a temporary musical row along with its sound events, causing columns to refit.

        Recomputes the combined boundary set, builds the refitted columns,
        calculates Row 1 (the constant musical row), and records the step.

        Args:
            row_id: Identifier for the new temporary row (e.g. 'Row 2').
            events: List of SoundEvent objects belonging to this row.
            row_label: Optional label for the row.
            step_description: Optional human-readable description of this step.

        Returns:
            The newly created RefitStep.
        """
        row = self._song.create_row(row_id=row_id, label=row_label)
        added_eids: List[str] = []
        for event in events:
            row.add_event(event)
            added_eids.append(event.event_id)

        # Derive refitted boundaries and columns
        boundaries = self._song.extract_boundaries()
        columns = self._song.build_columns()
        constant_row = self._song.calculate_constant_row()

        desc = (
            step_description
            if step_description
            else f"Add {row_id} with {len(events)} event(s)"
        )

        step = RefitStep(
            step_index=len(self._steps),
            description=desc,
            added_row_id=row_id,
            added_event_ids=tuple(added_eids),
            boundaries=boundaries,
            columns=columns,
            constant_row=constant_row,
        )
        self._steps.append(step)
        return step

    def add_event(
        self,
        event: SoundEvent,
        step_description: str = "",
    ) -> RefitStep:
        """Add a single sound event, refitting columns for the timeline."""
        self._song.add_event(event)

        boundaries = self._song.extract_boundaries()
        columns = self._song.build_columns()
        constant_row = self._song.calculate_constant_row()

        desc = (
            step_description
            if step_description
            else f"Add event {event.event_id} on {event.row_id}"
        )

        step = RefitStep(
            step_index=len(self._steps),
            description=desc,
            added_row_id=event.row_id,
            added_event_ids=(event.event_id,),
            boundaries=boundaries,
            columns=columns,
            constant_row=constant_row,
        )
        self._steps.append(step)
        return step
