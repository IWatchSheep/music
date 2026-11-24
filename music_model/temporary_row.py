"""Temporary sound row implementation.

A temporary row holds a collection of related sound events. Sounds within a row
can be sequential or overlapping, and exist for the duration of the musical group.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Tuple

from music_model.sound_event import SoundEvent


class TemporaryRow:
    """A temporary sound row containing a group of related sound events.

    Attributes:
        row_id: Unique row/group identifier (non-empty string).
        label: Descriptive name or label for this temporary musical group.
    """

    def __init__(self, row_id: str, label: str = "") -> None:
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(f"row_id must be a non-empty string, got {row_id!r}")
        self.row_id: str = row_id
        self.label: str = label
        self._events: Dict[str, SoundEvent] = {}

    def add_event(self, event: SoundEvent) -> None:
        """Add a sound event to this temporary row.

        Raises:
            ValueError: If event belongs to a different row_id.
            ValueError: If an event with the same event_id already exists in this row.
        """
        if not isinstance(event, SoundEvent):
            raise TypeError(f"Expected SoundEvent instance, got {type(event).__name__}")
        if event.row_id != self.row_id:
            raise ValueError(
                f"Cannot add event '{event.event_id}' with row_id '{event.row_id}' "
                f"to TemporaryRow '{self.row_id}'."
            )
        if event.event_id in self._events:
            raise ValueError(
                f"Event with ID '{event.event_id}' already exists in row '{self.row_id}'."
            )
        self._events[event.event_id] = event

    def remove_event(self, event_id: str) -> SoundEvent:
        """Remove a sound event by ID from this temporary row.

        Returns:
            The removed SoundEvent.

        Raises:
            KeyError: If event_id does not exist.
        """
        if event_id not in self._events:
            raise KeyError(f"Event ID '{event_id}' not found in row '{self.row_id}'.")
        return self._events.pop(event_id)

    def get_event(self, event_id: str) -> Optional[SoundEvent]:
        """Retrieve a sound event by ID, or None if not present."""
        return self._events.get(event_id)

    def has_event(self, event_id: str) -> bool:
        """Check if an event ID exists in this row."""
        return event_id in self._events

    @property
    def events(self) -> Tuple[SoundEvent, ...]:
        """Tuple of sound events in this row, sorted by start time, end time, and event ID."""
        return tuple(
            sorted(
                self._events.values(),
                key=lambda e: (e.start_time_ms, e.end_time_ms, e.event_id),
            )
        )

    @property
    def event_ids(self) -> Tuple[str, ...]:
        """Tuple of event IDs in this row."""
        return tuple(e.event_id for e in self.events)

    @property
    def earliest_start_ms(self) -> Optional[int]:
        """Earliest start time across all events in this row, or None if empty."""
        if not self._events:
            return None
        return min(e.start_time_ms for e in self._events.values())

    @property
    def latest_end_ms(self) -> Optional[int]:
        """Latest end time across all events in this row, or None if empty."""
        if not self._events:
            return None
        return max(e.end_time_ms for e in self._events.values())

    def is_active_in_column(self, col_start_ms: int, col_end_ms: int) -> bool:
        """Check if any sound event in this row covers the column interval [col_start_ms, col_end_ms)."""
        return any(e.covers_column(col_start_ms, col_end_ms) for e in self._events.values())

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[SoundEvent]:
        return iter(self.events)

    def __contains__(self, event_id: str) -> bool:
        return event_id in self._events

    def __repr__(self) -> str:
        return f"TemporaryRow(row_id={self.row_id!r}, label={self.label!r}, event_count={len(self)})"
