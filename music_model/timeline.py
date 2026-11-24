"""Timeline and variable-width time columns implementation.

The timeline collects all sound event boundaries from temporary rows, sorts and
deduplicates them, and derives variable-width time columns spanning [t_j, t_{j+1}).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple

from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow


@dataclass(frozen=True)
class TimeColumn:
    """A derived time interval between two consecutive sound boundaries.

    Attributes:
        index: 0-based column index.
        start_time_ms: Column start time in milliseconds.
        end_time_ms: Column end time in milliseconds (end_time_ms > start_time_ms).
        duration_ms: Duration of this column in milliseconds.
        active_event_ids: Tuple of event IDs active during this column interval (sorted).
        active_row_ids: Tuple of temporary row IDs active during this column interval (sorted).
    """

    index: int
    start_time_ms: int
    end_time_ms: int
    duration_ms: int
    active_event_ids: Tuple[str, ...]
    active_row_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"Column index must be nonnegative, got {self.index}")
        if self.start_time_ms < 0:
            raise ValueError(f"start_time_ms must be nonnegative, got {self.start_time_ms}")
        if self.end_time_ms <= self.start_time_ms:
            raise ValueError(
                f"end_time_ms ({self.end_time_ms}) must be strictly greater than "
                f"start_time_ms ({self.start_time_ms})"
            )
        expected_duration = self.end_time_ms - self.start_time_ms
        if self.duration_ms != expected_duration:
            raise ValueError(
                f"duration_ms ({self.duration_ms}) does not match "
                f"end_time_ms - start_time_ms ({expected_duration})"
            )

    @property
    def start_seconds(self) -> float:
        """Start time in fractional seconds."""
        return self.start_time_ms / 1000.0

    @property
    def end_seconds(self) -> float:
        """End time in fractional seconds."""
        return self.end_time_ms / 1000.0

    @property
    def duration_seconds(self) -> float:
        """Duration in fractional seconds."""
        return self.duration_ms / 1000.0

    @property
    def active_event_count(self) -> int:
        """Total number of active sound events in this column."""
        return len(self.active_event_ids)

    @property
    def active_row_count(self) -> int:
        """Number of distinct temporary rows active in this column."""
        return len(self.active_row_ids)

    @property
    def is_silent_gap(self) -> bool:
        """True if no sound events are active during this column interval."""
        return len(self.active_event_ids) == 0

    @property
    def has_active_sounds(self) -> bool:
        """True if at least one sound event is active during this column interval."""
        return len(self.active_event_ids) > 0


class MusicTimeline:
    """Manages temporary sound rows and derives linked variable-width time columns."""

    def __init__(self) -> None:
        self._rows: Dict[str, TemporaryRow] = {}

    def add_row(self, row: TemporaryRow) -> None:
        """Add an existing TemporaryRow to the timeline.

        Raises:
            ValueError: If a row with row_id already exists.
            ValueError: If any event_id in the row already exists in another row.
        """
        if not isinstance(row, TemporaryRow):
            raise TypeError(f"Expected TemporaryRow instance, got {type(row).__name__}")
        if row.row_id in self._rows:
            raise ValueError(f"Row with ID '{row.row_id}' already exists in timeline.")

        # Check for event_id collisions across other rows
        existing_event_ids = self._all_event_ids_set()
        for event in row.events:
            if event.event_id in existing_event_ids:
                raise ValueError(
                    f"Duplicate event_id '{event.event_id}' detected. "
                    "Event IDs must be globally unique across the entire timeline."
                )

        self._rows[row.row_id] = row

    def create_row(self, row_id: str, label: str = "") -> TemporaryRow:
        """Create and register a new TemporaryRow in the timeline."""
        row = TemporaryRow(row_id=row_id, label=label)
        self.add_row(row)
        return row

    def get_row(self, row_id: str) -> Optional[TemporaryRow]:
        """Retrieve a TemporaryRow by ID, or None if not found."""
        return self._rows.get(row_id)

    def remove_row(self, row_id: str) -> TemporaryRow:
        """Remove a TemporaryRow by ID from the timeline.

        Returns:
            The removed TemporaryRow.
        """
        if row_id not in self._rows:
            raise KeyError(f"Row ID '{row_id}' not found in timeline.")
        return self._rows.pop(row_id)

    def add_event(self, event: SoundEvent) -> None:
        """Add a sound event to the timeline, routing it to its temporary row.

        If the target row does not yet exist, it is automatically created.

        Raises:
            ValueError: If an event with the same event_id already exists in any row.
        """
        if not isinstance(event, SoundEvent):
            raise TypeError(f"Expected SoundEvent instance, got {type(event).__name__}")

        # Check for duplicate event ID across all rows
        if self.has_event(event.event_id):
            raise ValueError(
                f"Cannot add event: duplicate event ID '{event.event_id}' already exists in timeline."
            )

        if event.row_id not in self._rows:
            self._rows[event.row_id] = TemporaryRow(row_id=event.row_id)

        self._rows[event.row_id].add_event(event)

    def has_event(self, event_id: str) -> bool:
        """Check if an event ID exists anywhere in the timeline."""
        return any(row.has_event(event_id) for row in self._rows.values())

    def get_event(self, event_id: str) -> Optional[SoundEvent]:
        """Find a sound event by ID across all rows, or None if not found."""
        for row in self._rows.values():
            event = row.get_event(event_id)
            if event is not None:
                return event
        return None

    def _all_event_ids_set(self) -> Set[str]:
        """Internal helper to get a set of all event IDs currently in the timeline."""
        result: Set[str] = set()
        for row in self._rows.values():
            result.update(row.event_ids)
        return result

    @property
    def rows(self) -> Tuple[TemporaryRow, ...]:
        """Tuple of temporary rows in the timeline, sorted by row_id."""
        return tuple(sorted(self._rows.values(), key=lambda r: r.row_id))

    @property
    def row_ids(self) -> Tuple[str, ...]:
        """Tuple of row IDs in the timeline, sorted alphabetically."""
        return tuple(sorted(self._rows.keys()))

    @property
    def all_events(self) -> Tuple[SoundEvent, ...]:
        """Tuple of all sound events across all rows, sorted by start time, end time, and ID."""
        events: List[SoundEvent] = []
        for row in self._rows.values():
            events.extend(row.events)
        return tuple(sorted(events, key=lambda e: (e.start_time_ms, e.end_time_ms, e.event_id)))

    def extract_boundaries(self) -> Tuple[int, ...]:
        """Collect all start and end timestamps from all sound events, sorted and deduplicated.

        Returns:
            Tuple of unique integer millisecond boundaries: (t_0, t_1, ..., t_m).
            Returns an empty tuple if there are no sound events.
        """
        boundaries_set: Set[int] = set()
        for event in self.all_events:
            boundaries_set.add(event.start_time_ms)
            boundaries_set.add(event.end_time_ms)
        return tuple(sorted(boundaries_set))

    def build_columns(self) -> Tuple[TimeColumn, ...]:
        """Derive variable-width time columns from event boundaries.

        Returns:
            Tuple of TimeColumn instances covering each interval [t_j, t_{j+1}).
            Returns an empty tuple if there are fewer than 2 boundaries.
        """
        boundaries = self.extract_boundaries()
        if len(boundaries) < 2:
            return ()

        columns: List[TimeColumn] = []
        events = self.all_events
        rows = self.rows

        for j in range(len(boundaries) - 1):
            t_start = boundaries[j]
            t_end = boundaries[j + 1]
            duration = t_end - t_start

            # Find active events covering [t_start, t_end)
            active_events = [
                e.event_id for e in events if e.covers_column(t_start, t_end)
            ]
            # Find active rows covering [t_start, t_end)
            active_rows = [
                r.row_id for r in rows if r.is_active_in_column(t_start, t_end)
            ]

            columns.append(
                TimeColumn(
                    index=j,
                    start_time_ms=t_start,
                    end_time_ms=t_end,
                    duration_ms=duration,
                    active_event_ids=tuple(sorted(active_events)),
                    active_row_ids=tuple(sorted(active_rows)),
                )
            )

        return tuple(columns)

    @property
    def total_duration_ms(self) -> int:
        """Total elapsed duration from the earliest boundary to the latest boundary, or 0."""
        boundaries = self.extract_boundaries()
        if len(boundaries) < 2:
            return 0
        return boundaries[-1] - boundaries[0]

    @property
    def total_duration_seconds(self) -> float:
        """Total elapsed duration in fractional seconds."""
        return self.total_duration_ms / 1000.0

    @property
    def row_count(self) -> int:
        """Number of temporary rows in the timeline."""
        return len(self._rows)

    @property
    def event_count(self) -> int:
        """Total number of sound events in the timeline."""
        return sum(len(r) for r in self._rows.values())

    def __len__(self) -> int:
        return self.row_count

    def __iter__(self) -> Iterator[TemporaryRow]:
        return iter(self.rows)

    def __repr__(self) -> str:
        return f"MusicTimeline(rows={self.row_count}, events={self.event_count})"
