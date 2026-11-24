"""Coordinate transformation and layout mathematics for the Music GUI.

Ensures that:
1. Column widths are strictly proportional to actual millisecond durations.
2. An exact, linear 1-to-1 mapping exists between data timestamps and screen pixels:
   x(t) = left_header_width + t * pixels_per_ms.
3. Minimum readable column width is achieved by globally scaling pixels_per_ms,
   so no individual columns are artificially stretched or distorted relative to others.
4. Row 1 (Constant Musical Row) is positioned at the top beneath the time header,
   with temporary sound rows (Row 2, Row 3, ...) placed sequentially below it.
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
        constant_row_height: Pixel height of Row 1 (constant musical row lane).
        min_column_width: Minimum desired readable pixel width for any column.
        constant_row_at_top: If True (default), Row 1 is placed at the top beneath the header.
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
        constant_row_at_top: bool = True,
    ) -> None:
        self.timeline: MusicTimeline = timeline
        self.base_pixels_per_ms: float = float(base_pixels_per_ms)
        self.left_header_width: int = left_header_width
        self.header_height: int = header_height
        self.row_height: int = row_height
        self.constant_row_height: int = constant_row_height
        self.min_column_width: float = float(min_column_width)
        self.padding_right: int = padding_right
        self.padding_top: int = padding_top
        self.padding_bottom: int = padding_bottom
        self.lane_gap: int = lane_gap
        self.constant_row_at_top: bool = constant_row_at_top

        self._zoom_multiplier: float = 1.0

    # --- Scale Factor Calculation ---

    @property
    def pixels_per_ms(self) -> float:
        """Effective pixels-per-millisecond scale factor.

        Guarantees that the shortest column in the active timeline achieves
        at least `min_column_width` pixels (before applying zoom multiplier),
        while maintaining strict proportionality across ALL columns.
        """
        columns = self.timeline.build_columns()
        if not columns:
            return self.base_pixels_per_ms * self._zoom_multiplier

        shortest_duration = min(col.duration_ms for col in columns)
        if shortest_duration <= 0:
            scale = self.base_pixels_per_ms
        else:
            required_scale = self.min_column_width / float(shortest_duration)
            scale = max(self.base_pixels_per_ms, required_scale)

        return scale * self._zoom_multiplier

    # --- Zoom Controls ---

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

    def constant_row_y_bounds(self) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for Row 1 (Constant Row)."""
        if self.constant_row_at_top:
            # Placed at top directly beneath the header
            y_header_bottom = self.padding_top + self.header_height
            y0 = float(y_header_bottom + 4)
            y1 = y0 + float(self.constant_row_height)
            return (y0, y1)
        else:
            # Legacy bottom placement
            num_rows = self.timeline.row_count
            y_rows_bottom = self.padding_top + self.header_height + num_rows * self.row_height
            y0 = float(y_rows_bottom + self.lane_gap)
            y1 = y0 + float(self.constant_row_height)
            return (y0, y1)

    def row_y_bounds(self, row_index: int) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for temporary row at row_index (0-based)."""
        if self.constant_row_at_top:
            # Placed below Row 1 (Constant Row)
            y_const_bottom = self.padding_top + self.header_height + 4 + self.constant_row_height
            y0 = float(y_const_bottom + self.lane_gap + row_index * self.row_height)
            y1 = y0 + float(self.row_height)
            return (y0, y1)
        else:
            # Legacy above constant row
            y_header_bottom = self.padding_top + self.header_height
            y0 = float(y_header_bottom + row_index * self.row_height)
            y1 = y0 + float(self.row_height)
            return (y0, y1)

    def temporary_row_y_bounds(self, row_id: str) -> Tuple[float, float]:
        """Return (y_top, y_bottom) for the temporary row identified by row_id."""
        row_ids = self.timeline.row_ids
        if row_id not in row_ids:
            raise KeyError(f"Row {row_id!r} not found in timeline")
        idx = row_ids.index(row_id)
        return self.row_y_bounds(idx)

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
        num_rows = self.timeline.row_count
        if self.constant_row_at_top:
            if num_rows == 0:
                _, y_const_bot = self.constant_row_y_bounds()
                return int(y_const_bot + self.padding_bottom)
            _, y_last_row_bot = self.row_y_bounds(num_rows - 1)
            return int(y_last_row_bot + self.padding_bottom)
        else:
            _, y_const_bottom = self.constant_row_y_bounds()
            return int(y_const_bottom + self.padding_bottom)
