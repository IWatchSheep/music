"""Coordinate transformation and layout mathematics for the Music GUI.

Ensures that:
1. Column widths are strictly proportional to actual millisecond durations.
2. An exact, linear 1-to-1 mapping exists between data timestamps and screen pixels:
   x(t) = left_header_width + t * pixels_per_ms.
3. Minimum readable column width is achieved by globally scaling pixels_per_ms,
   so no individual columns are artificially stretched or distorted relative to others.
"""

from __future__ import annotations

from typing import Optional, Tuple

from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline, TimeColumn


class TimelineCoordinates:
    """Calculates screen pixel layout coordinates from a MusicTimeline.

    Attributes:
        timeline: The MusicTimeline instance being visualized.
        base_pixels_per_ms: Base scaling factor (pixels per millisecond).
        left_header_width: Pixel width of the left label sidebar.
        header_height: Pixel height of the top time-column header.
        row_height: Pixel height of each temporary sound row lane.
        constant_row_height: Pixel height of the bottom constant row lane.
        min_column_width: Minimum desired readable pixel width for any column.
    """

    def __init__(
        self,
        timeline: MusicTimeline,
        base_pixels_per_ms: float = 0.16,  # 160 pixels per second
        left_header_width: int = 160,
        header_height: int = 56,
        row_height: int = 64,
        constant_row_height: int = 60,
        min_column_width: float = 90.0,
        padding_right: int = 40,
        padding_top: int = 10,
        padding_bottom: int = 20,
        lane_gap: int = 14,
    ) -> None:
        self.timeline: MusicTimeline = timeline
        self.left_header_width: int = left_header_width
        self.header_height: int = header_height
        self.row_height: int = row_height
        self.constant_row_height: int = constant_row_height
        self.min_column_width: float = min_column_width
        self.padding_right: int = padding_right
        self.padding_top: int = padding_top
        self.padding_bottom: int = padding_bottom
        self.lane_gap: int = lane_gap

        self._zoom_multiplier: float = 1.0
        self._user_pixels_per_ms: float = base_pixels_per_ms

    @property
    def pixels_per_ms(self) -> float:
        """Effective pixels per millisecond, uniformly scaled across all columns.

        Calculated as:
          effective_scale = max(user_scale, min_column_width / min_column_duration) * zoom_multiplier
        This guarantees that even the shortest column is at least min_column_width wide,
        while maintaining EXACT linear proportionality across the entire timeline.
        """
        columns = self.timeline.build_columns()
        if not columns:
            return self._user_pixels_per_ms * self._zoom_multiplier

        min_duration = min(c.duration_ms for c in columns)
        needed_scale = (
            self.min_column_width / min_duration if min_duration > 0 else self._user_pixels_per_ms
        )
        base_effective = max(self._user_pixels_per_ms, needed_scale)
        return base_effective * self._zoom_multiplier

    def zoom_in(self, factor: float = 1.25) -> None:
        """Increase the horizontal time magnification."""
        self._zoom_multiplier = min(self._zoom_multiplier * factor, 5.0)

    def zoom_out(self, factor: float = 1.25) -> None:
        """Decrease the horizontal time magnification."""
        self._zoom_multiplier = max(self._zoom_multiplier / factor, 0.4)

    def reset_zoom(self) -> None:
        """Reset zoom multiplier to 1.0."""
        self._zoom_multiplier = 1.0

    @property
    def zoom_level(self) -> float:
        """Current zoom multiplier."""
        return self._zoom_multiplier

    # --- Horizontal Time-to-Pixel Transformations ---

    def time_to_x(self, time_ms: int) -> float:
        """Convert an integer millisecond timestamp to an absolute canvas X pixel coordinate.

        Linear transformation:
          x(t) = left_header_width + t * pixels_per_ms
        """
        return float(self.left_header_width + time_ms * self.pixels_per_ms)

    def x_to_time(self, x: float) -> float:
        """Convert a canvas X pixel coordinate back to millisecond timestamp."""
        return max(0.0, (x - self.left_header_width) / self.pixels_per_ms)

    def column_x_bounds(self, column: TimeColumn) -> Tuple[float, float]:
        """Return (x_left, x_right) for a time column."""
        x0 = self.time_to_x(column.start_time_ms)
        x1 = self.time_to_x(column.end_time_ms)
        return (x0, x1)

    def column_width(self, column: TimeColumn) -> float:
        """Pixel width of a time column (proportional to duration_ms)."""
        return float(column.duration_ms * self.pixels_per_ms)

    def event_x_bounds(self, event: SoundEvent) -> Tuple[float, float]:
        """Return (x_left, x_right) for a sound event bar."""
        x0 = self.time_to_x(event.start_time_ms)
        x1 = self.time_to_x(event.end_time_ms)
        return (x0, x1)

    def event_width(self, event: SoundEvent) -> float:
        """Pixel width of a sound event bar (proportional to duration_ms)."""
        return float(event.duration_ms * self.pixels_per_ms)

    # --- Vertical Layout Coordinates ---

    def header_y_bounds(self) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for the top time-column header lane."""
        y0 = float(self.padding_top)
        y1 = y0 + float(self.header_height)
        return (y0, y1)

    def row_y_bounds(self, row_index: int) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for temporary row at row_index (0-based)."""
        y_header_bottom = self.padding_top + self.header_height
        y0 = float(y_header_bottom + row_index * self.row_height)
        y1 = y0 + float(self.row_height)
        return (y0, y1)

    def constant_row_y_bounds(self) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for the calculated constant row at the bottom."""
        num_rows = self.timeline.row_count
        y_rows_bottom = self.padding_top + self.header_height + num_rows * self.row_height
        y0 = float(y_rows_bottom + self.lane_gap)
        y1 = y0 + float(self.constant_row_height)
        return (y0, y1)

    # --- Total Workspace Dimensions for Scrollregion ---

    @property
    def total_width(self) -> int:
        """Total required canvas pixel width to encompass all columns and headers."""
        boundaries = self.timeline.extract_boundaries()
        latest_time = boundaries[-1] if boundaries else 0
        timeline_w = int(latest_time * self.pixels_per_ms)
        return self.left_header_width + timeline_w + self.padding_right

    @property
    def total_height(self) -> int:
        """Total required canvas pixel height to encompass header, rows, and constant row."""
        _, y_const_bottom = self.constant_row_y_bounds()
        return int(y_const_bottom + self.padding_bottom)
