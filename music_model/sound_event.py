"""Sound event representation and interval validation.

Each sound event represents a continuous interval [start_time_ms, end_time_ms)
belonging to a temporary row.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _validate_integer_timestamp(value: Any, param_name: str) -> int:
    """Validate that a timestamp is a finite integer millisecond value.

    Raises:
        ValueError: If value is not a finite integer, or is a boolean.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Invalid {param_name}: expected integer milliseconds, got {type(value).__name__} ({value!r})"
        )
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Invalid {param_name}: timestamp must be finite, got {value}")
        if not value.is_integer():
            raise ValueError(
                f"Invalid {param_name}: fractional milliseconds not allowed ({value}). "
                "Timestamps must be exact integer milliseconds."
            )
        value = int(value)
    return value


@dataclass(frozen=True)
class SoundEvent:
    """A continuous sound interval belonging to a temporary sound row.

    Attributes:
        event_id: Unique identifier for this sound event (non-empty string).
        row_id: Identifier of the temporary row this sound belongs to.
        start_time_ms: Nonnegative start time in integer milliseconds.
        end_time_ms: End time in integer milliseconds (strictly greater than start_time_ms).
        label: Optional human-readable description or title.
        sound_ref: Optional future reference to an audio recording, file, or buffer.
        attributes: Optional musical attributes (pitch, intensity, instrument, etc.).
        height: Optional experimental low-to-high numeric value (e.g., 20.0, 50.0, 80.0).
    """

    event_id: str
    row_id: str
    start_time_ms: int
    end_time_ms: int
    label: str = ""
    sound_ref: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    height: Optional[float] = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError(f"event_id must be a non-empty string, got {self.event_id!r}")
        if not isinstance(self.row_id, str) or not self.row_id.strip():
            raise ValueError(f"row_id must be a non-empty string, got {self.row_id!r}")

        # Validate integer milliseconds
        start_ms = _validate_integer_timestamp(self.start_time_ms, "start_time_ms")
        end_ms = _validate_integer_timestamp(self.end_time_ms, "end_time_ms")

        # Bypass frozen state to ensure values are stored strictly as int
        object.__setattr__(self, "start_time_ms", start_ms)
        object.__setattr__(self, "end_time_ms", end_ms)

        if start_ms < 0:
            raise ValueError(f"start_time_ms must be nonnegative, got {start_ms}")
        if end_ms <= start_ms:
            raise ValueError(
                f"end_time_ms ({end_ms}) must be strictly greater than start_time_ms ({start_ms}). "
                "Zero-duration or backward sound intervals are not allowed."
            )

        # Validate optional experimental height
        if self.height is not None:
            if isinstance(self.height, bool) or not isinstance(self.height, (int, float)) or not math.isfinite(self.height):
                raise ValueError(f"height must be a finite number or None, got {self.height!r}")
            h_val = float(self.height)
            object.__setattr__(self, "height", h_val)
            if "height" not in self.attributes:
                self.attributes["height"] = h_val
        elif "height" in self.attributes:
            attr_h = self.attributes["height"]
            if isinstance(attr_h, bool) or not isinstance(attr_h, (int, float)) or not math.isfinite(attr_h):
                raise ValueError(f"attributes['height'] must be a finite number, got {attr_h!r}")
            object.__setattr__(self, "height", float(attr_h))

    @property
    def height_value(self) -> Optional[float]:
        """Experimental low-to-high value, or None if not set."""
        return self.height

    @property
    def duration_ms(self) -> int:
        """Duration of the sound event in integer milliseconds."""
        return self.end_time_ms - self.start_time_ms

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
        """Duration of the sound event in fractional seconds."""
        return self.duration_ms / 1000.0

    def contains_time_ms(self, time_ms: int) -> bool:
        """Check if this sound event is active at time_ms (half-open interval [start, end))."""
        return self.start_time_ms <= time_ms < self.end_time_ms

    def covers_column(self, col_start_ms: int, col_end_ms: int) -> bool:
        """Check if this sound event completely covers the column interval [col_start_ms, col_end_ms)."""
        return self.start_time_ms <= col_start_ms and self.end_time_ms >= col_end_ms
