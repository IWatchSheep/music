"""Calculated constant musical row implementation.

The constant row represents a continuous, derived measurement across all derived
time columns. For Stage 1, the default measurement is the count of distinct active
temporary rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, Optional, Tuple, Union

from music_model.timeline import MusicTimeline, TimeColumn

# Flexible measurement function signature: takes (column, timeline) -> numeric measurement
MeasurementFunction = Callable[[TimeColumn, MusicTimeline], Union[int, float]]


def count_distinct_active_rows(column: TimeColumn, timeline: MusicTimeline) -> int:
    """Default Stage 1 measurement: count the number of distinct active temporary rows.

    For example, three simultaneous sounds belonging to the same temporary row
    count as 1 active row, not 3.
    """
    return column.active_row_count


def count_active_events(column: TimeColumn, timeline: MusicTimeline) -> int:
    """Alternative measurement: count the total number of active sound events."""
    return column.active_event_count


@dataclass(frozen=True)
class ConstantRow:
    """A continuous calculated musical row derived across all time columns.

    Attributes:
        measurement_name: Name of the applied measurement (e.g. 'Active Temporary Row Count').
        values: Tuple of calculated numeric values for each column interval.
        columns: Tuple of the underlying derived TimeColumn objects.
    """

    measurement_name: str
    values: Tuple[Union[int, float], ...]
    columns: Tuple[TimeColumn, ...]

    def __post_init__(self) -> None:
        if len(self.values) != len(self.columns):
            raise ValueError(
                f"Mismatch: {len(self.values)} values provided for {len(self.columns)} columns."
            )

    @property
    def column_count(self) -> int:
        """Total number of time columns in this constant row."""
        return len(self.values)

    @property
    def total_duration_ms(self) -> int:
        """Total elapsed duration in milliseconds across all columns."""
        return sum(c.duration_ms for c in self.columns)

    @property
    def total_duration_seconds(self) -> float:
        """Total elapsed duration in fractional seconds."""
        return self.total_duration_ms / 1000.0

    @property
    def is_empty(self) -> bool:
        """True if the constant row contains no columns."""
        return len(self.values) == 0

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, index: int) -> Union[int, float]:
        return self.values[index]

    def __iter__(self) -> Iterator[Union[int, float]]:
        return iter(self.values)

    def __repr__(self) -> str:
        return (
            f"ConstantRow(measurement='{self.measurement_name}', "
            f"columns={self.column_count}, values={list(self.values)})"
        )


def calculate_constant_row(
    timeline: MusicTimeline,
    measurement_fn: Optional[MeasurementFunction] = None,
    measurement_name: str = "Active Temporary Row Count",
) -> ConstantRow:
    """Derive the constant row from a MusicTimeline.

    Args:
        timeline: The MusicTimeline instance to analyze.
        measurement_fn: Optional measurement function taking (TimeColumn, MusicTimeline) -> number.
                        Defaults to count_distinct_active_rows.
        measurement_name: Descriptive label for the calculation.

    Returns:
        A ConstantRow instance with values for every derived column.
    """
    if measurement_fn is None:
        measurement_fn = count_distinct_active_rows

    columns = timeline.build_columns()
    values = tuple(measurement_fn(col, timeline) for col in columns)

    return ConstantRow(
        measurement_name=measurement_name,
        values=values,
        columns=columns,
    )
