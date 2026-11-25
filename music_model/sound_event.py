"""Sound event representation and interval validation.

Each sound event represents a continuous interval [start_time_ms, end_time_ms)
belonging to a temporary row.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, Optional, Tuple


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


def get_authoritative_exact_timing(
    event: SoundEvent, unit: str = "ms"
) -> Tuple[Fraction, Fraction, Fraction]:
    """Retrieve the authoritative exact rational timing coordinates for a SoundEvent.

    This helper provides a uniform, documented mechanism to access exact rational timing
    without relying on rounded integer millisecond timestamps:
    - If the event originated from MusicXML, reads 'exact_start_ms_rational' and 'exact_end_ms_rational'.
    - If the event originated from continuous audio, reads 'exact_start_sec_rational' and 'exact_end_sec_rational'.
    - If no exact rational attributes are present (e.g. historical baseline events), constructs
      exact rational fractions from start_time_ms and end_time_ms.

    Validation & Incomplete Metadata Rejection (DEFECT-16 & DEFECT-19):
    Fallback to integer millisecond timestamps applies ONLY when authoritative rational metadata
    is genuinely absent. If partial, unpaired, malformed, or inconsistent rational timing attributes
    are present, this function raises ValueError immediately rather than silently falling back.
    - Rejects conflicting format metadata (contains both MusicXML and Audio timing attributes).
    - MusicXML requires paired 'exact_start_ms_rational' and 'exact_end_ms_rational'.
    - Audio requires paired 'exact_start_sec_rational' and 'exact_end_sec_rational' whenever any
      audio timing attributes (including sample indices) are present.
    - If redundant duration ('exact_duration_ms_rational' / 'exact_duration_sec_rational') is
      supplied, it must exactly equal (end - start).
    - If audio sample index metadata is present, it must be mathematically consistent with sample rate
      and declared sample count.
    - Verifies integer millisecond interval bounds (start_time_ms >= 0 and end_time_ms > start_time_ms).

    Fallback Disclaimer:
    When falling back to integer millisecond timestamps (start_time_ms, end_time_ms), the returned
    Fraction represents exact integer milliseconds (e.g. Fraction(123, 1)). This fallback reflects
    the stored integer bounds of the SoundEvent and does not reconstruct unpreserved fractional
    timing from historical source formats (such as fractional milliseconds derived from MIDI ticks).

    Args:
        event: The SoundEvent instance to inspect.
        unit: Target unit: 'ms' (exact rational milliseconds) or 'sec' (exact rational seconds).

    Returns:
        (exact_start, exact_end, exact_duration) as Fraction objects.

    Raises:
        ValueError: If unit is not 'ms' or 'sec', or if metadata is incomplete, malformed, or inconsistent.
    """
    if unit not in ("ms", "sec"):
        raise ValueError(f"Invalid unit {unit!r}. Expected 'ms' or 'sec'.")

    attrs = event.attributes or {}

    musicxml_keys = ("exact_start_ms_rational", "exact_end_ms_rational", "exact_duration_ms_rational")
    audio_rational_keys = ("exact_start_sec_rational", "exact_end_sec_rational", "exact_duration_sec_rational")
    audio_sample_keys = ("sample_start_idx", "sample_end_idx", "sample_count")
    audio_keys = audio_rational_keys + audio_sample_keys

    has_mxml_keys = any(k in attrs for k in musicxml_keys)
    has_audio_keys = any(k in attrs for k in audio_keys)

    # 0. Reject Conflicting Multi-Format Metadata (DEFECT-19)
    if has_mxml_keys and has_audio_keys:
        raise ValueError(
            f"Conflicting timing metadata on event {event.event_id!r}: "
            f"contains both MusicXML and Audio timing attributes."
        )

    # 1. MusicXML Rational Timing
    if has_mxml_keys:
        if "exact_start_ms_rational" not in attrs or "exact_end_ms_rational" not in attrs:
            raise ValueError(
                f"Incomplete MusicXML rational timing attributes on event {event.event_id!r}: "
                f"both 'exact_start_ms_rational' and 'exact_end_ms_rational' must be present."
            )
        try:
            start_ms = Fraction(str(attrs["exact_start_ms_rational"]))
            end_ms = Fraction(str(attrs["exact_end_ms_rational"]))
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(
                f"Malformed MusicXML rational timing attributes on event {event.event_id!r}: {exc}"
            ) from exc

        if start_ms < 0:
            raise ValueError(
                f"Invalid negative rational start time {start_ms} on event {event.event_id!r}"
            )
        if end_ms <= start_ms:
            raise ValueError(
                f"Invalid rational timing on event {event.event_id!r}: end ({end_ms}) <= start ({start_ms})"
            )
        dur_ms = end_ms - start_ms

        if "exact_duration_ms_rational" in attrs:
            try:
                declared_dur = Fraction(str(attrs["exact_duration_ms_rational"]))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(
                    f"Malformed MusicXML rational duration attribute on event {event.event_id!r}: {exc}"
                ) from exc
            if declared_dur != dur_ms:
                raise ValueError(
                    f"Inconsistent MusicXML rational duration attribute on event {event.event_id!r}: "
                    f"declared {declared_dur} != computed end - start ({dur_ms})"
                )

        # Check gross consistency with integer millisecond bounds (DEFECT-19)
        if abs(float(start_ms) - event.start_time_ms) > 2.0:
            raise ValueError(
                f"Inconsistent timing coordinates on event {event.event_id!r}: "
                f"rational start ({float(start_ms):.2f}ms) differs from integer start_time_ms ({event.start_time_ms}ms)"
            )
        if abs(float(end_ms) - event.end_time_ms) > 2.0:
            raise ValueError(
                f"Inconsistent timing coordinates on event {event.event_id!r}: "
                f"rational end ({float(end_ms):.2f}ms) differs from integer end_time_ms ({event.end_time_ms}ms)"
            )

        if unit == "ms":
            return start_ms, end_ms, dur_ms
        else:
            return start_ms / 1000, end_ms / 1000, dur_ms / 1000

    # 2. Continuous Audio Rational Timing
    if has_audio_keys:
        if "exact_start_sec_rational" not in attrs or "exact_end_sec_rational" not in attrs:
            raise ValueError(
                f"Incomplete Audio rational timing attributes on event {event.event_id!r}: "
                f"both 'exact_start_sec_rational' and 'exact_end_sec_rational' must be present."
            )
        try:
            start_sec = Fraction(str(attrs["exact_start_sec_rational"]))
            end_sec = Fraction(str(attrs["exact_end_sec_rational"]))
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(
                f"Malformed Audio rational timing attributes on event {event.event_id!r}: {exc}"
            ) from exc

        if start_sec < 0:
            raise ValueError(
                f"Invalid negative rational start time {start_sec} on event {event.event_id!r}"
            )
        if end_sec <= start_sec:
            raise ValueError(
                f"Invalid rational timing on event {event.event_id!r}: end ({end_sec}) <= start ({start_sec})"
            )
        dur_sec = end_sec - start_sec

        if "exact_duration_sec_rational" in attrs:
            try:
                declared_dur = Fraction(str(attrs["exact_duration_sec_rational"]))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(
                    f"Malformed Audio rational duration attribute on event {event.event_id!r}: {exc}"
                ) from exc
            if declared_dur != dur_sec:
                raise ValueError(
                    f"Inconsistent Audio rational duration attribute on event {event.event_id!r}: "
                    f"declared {declared_dur} != computed end - start ({dur_sec})"
                )

        # Consistency with sample indices if present (DEFECT-19)
        sr = attrs.get("sample_rate")
        s_start = attrs.get("sample_start_idx")
        s_end = attrs.get("sample_end_idx")
        s_count = attrs.get("sample_count")

        if any(k in attrs for k in audio_sample_keys):
            if not isinstance(sr, int) or sr <= 0:
                raise ValueError(
                    f"Invalid or missing sample_rate ({sr!r}) on audio event {event.event_id!r}."
                )
            if not isinstance(s_start, int) or s_start < 0:
                raise ValueError(
                    f"Invalid or missing sample_start_idx ({s_start!r}) on audio event {event.event_id!r}."
                )
            if not isinstance(s_end, int) or s_end <= s_start:
                raise ValueError(
                    f"Invalid or missing sample_end_idx ({s_end!r}) on audio event {event.event_id!r}: must be > start ({s_start})."
                )
            if s_count is not None:
                if not isinstance(s_count, int) or s_count != (s_end - s_start):
                    raise ValueError(
                        f"Inconsistent sample_count ({s_count!r}) on event {event.event_id!r}: "
                        f"declared count != end ({s_end}) - start ({s_start})."
                    )
            expected_start = Fraction(s_start, sr)
            if start_sec != expected_start:
                raise ValueError(
                    f"Inconsistent Audio start sample index on event {event.event_id!r}: "
                    f"sample {s_start}/{sr} ({expected_start}) != exact_start_sec_rational ({start_sec})"
                )
            expected_end = Fraction(s_end, sr)
            if end_sec != expected_end:
                raise ValueError(
                    f"Inconsistent Audio end sample index on event {event.event_id!r}: "
                    f"sample {s_end}/{sr} ({expected_end}) != exact_end_sec_rational ({end_sec})"
                )

        # Check gross consistency with integer millisecond bounds (DEFECT-19)
        start_ms_float = float(start_sec * 1000)
        end_ms_float = float(end_sec * 1000)
        if abs(start_ms_float - event.start_time_ms) > 2.0:
            raise ValueError(
                f"Inconsistent timing coordinates on event {event.event_id!r}: "
                f"rational start ({start_ms_float:.2f}ms) differs from integer start_time_ms ({event.start_time_ms}ms)"
            )
        if abs(end_ms_float - event.end_time_ms) > 2.0:
            raise ValueError(
                f"Inconsistent timing coordinates on event {event.event_id!r}: "
                f"rational end ({end_ms_float:.2f}ms) differs from integer end_time_ms ({event.end_time_ms}ms)"
            )

        if unit == "sec":
            return start_sec, end_sec, dur_sec
        else:
            return start_sec * 1000, end_sec * 1000, dur_sec * 1000

    # 3. Fallback: genuine absence of authoritative rational timing attributes
    # Validate integer interval bounds (DEFECT-19)
    if event.start_time_ms < 0:
        raise ValueError(
            f"Invalid SoundEvent interval bounds on {event.event_id!r}: start_time_ms ({event.start_time_ms}) cannot be negative."
        )
    if event.end_time_ms <= event.start_time_ms:
        raise ValueError(
            f"Invalid SoundEvent interval bounds on {event.event_id!r}: end_time_ms ({event.end_time_ms}) must be > start_time_ms ({event.start_time_ms})."
        )

    start_ms = Fraction(event.start_time_ms, 1)
    end_ms = Fraction(event.end_time_ms, 1)
    dur_ms = end_ms - start_ms
    if unit == "ms":
        return start_ms, end_ms, dur_ms
    else:
        return start_ms / 1000, end_ms / 1000, dur_ms / 1000
