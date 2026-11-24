"""Mathematical model and analysis of low-to-high musical development.

This module formalizes the user's musical concept:
1. Low-to-high development:
   - Row 2: Low sound (e.g. initial whirring on water).
   - Row 3: Transitional sound (e.g. accelerating, lifting off).
   - Row 4: High sound (e.g. airborne flight).
2. Continuous musical identity (Row 1):
   - Row 1 traces the continuous development profile across linked time columns.
   - The Stage 1 baseline (Active Temporary Row Count) remains preserved.
   - The experimental low-to-high profile provides an explicit, transparent
     measurement without claiming an arbitrary weighted average equals musical identity.
3. Comparative Analysis:
   - Compares direct vs intermediate arrangements.
   - Quantifies directness ratio, transition count, time-to-high, refitting complexity,
     and verifies that more columns do not imply greater curvature.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from music_model.constant_row import ConstantRow, calculate_constant_row
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline, TimeColumn


def get_event_height(event: SoundEvent) -> Optional[float]:
    """Retrieve the experimental low-to-high value from a SoundEvent.

    Checks:
    1. Direct `event.height` attribute.
    2. `event.attributes['height']` or `event.attributes['low_to_high']`.
    """
    if event.height is not None:
        return float(event.height)
    if event.attributes:
        if "height" in event.attributes:
            val = event.attributes["height"]
            if val is not None and math.isfinite(float(val)):
                return float(val)
        if "low_to_high" in event.attributes:
            val = event.attributes["low_to_high"]
            if val is not None and math.isfinite(float(val)):
                return float(val)
    return None


def calculate_column_height(
    column: TimeColumn,
    timeline: MusicTimeline,
    aggregation: str = "mean",
    silent_value: Optional[float] = 0.0,
) -> Optional[float]:
    """Calculate the experimental low-to-high development value for a single time column.

    Mathematical definition:
    - If no events are active in the column (silent gap):
      returns `silent_value`.
    - If active events have defined height values {h_1, ..., h_k}:
      - 'mean': Arithmetic mean = (1/k) * sum(h_i). Simple, unweighted, transparent.
      - 'max': Maximum active height = max(h_i).
      - 'min': Minimum active height = min(h_i).
    - If active events have no height values defined, returns None.

    Args:
        column: The derived TimeColumn.
        timeline: The MusicTimeline containing the sound events.
        aggregation: Aggregation rule ('mean', 'max', 'min'). Defaults to 'mean'.
        silent_value: Value returned for silent columns. Defaults to 0.0.

    Returns:
        Calculated numeric height value, or None if undefined.
    """
    if not column.has_active_sounds:
        return silent_value

    heights: List[float] = []
    for event_id in column.active_event_ids:
        event = timeline.get_event(event_id)
        if event is not None:
            h = get_event_height(event)
            if h is not None:
                heights.append(h)

    if not heights:
        return None

    agg = aggregation.lower().strip()
    if agg == "mean":
        return sum(heights) / float(len(heights))
    elif agg == "max":
        return max(heights)
    elif agg == "min":
        return min(heights)
    else:
        raise ValueError(f"Unknown aggregation method: {aggregation!r}. Valid: 'mean', 'max', 'min'")


def calculate_development_constant_row(
    timeline: MusicTimeline,
    aggregation: str = "mean",
    silent_value: Optional[float] = 0.0,
    measurement_name: str = "Low-to-High Development Profile",
) -> ConstantRow:
    """Generate a ConstantRow containing the experimental low-to-high development profile.

    Args:
        timeline: MusicTimeline to analyze.
        aggregation: Aggregation rule ('mean', 'max', 'min').
        silent_value: Value for silent gaps.
        measurement_name: Descriptive name for this calculation.

    Returns:
        ConstantRow instance holding the column-by-column development values.
    """
    def _dev_fn(col: TimeColumn, tl: MusicTimeline) -> Union[int, float]:
        val = calculate_column_height(col, tl, aggregation=aggregation, silent_value=silent_value)
        return val if val is not None else 0.0

    return calculate_constant_row(
        timeline=timeline,
        measurement_fn=_dev_fn,
        measurement_name=measurement_name,
    )


@dataclass(frozen=True)
class DevelopmentAnalysis:
    """Rigorous analytical metrics for an experimental low-to-high musical profile.

    Separates mathematical observations from subjective interpretations.
    """

    arrangement_name: str
    column_count: int
    total_duration_ms: int
    column_durations_ms: Tuple[int, ...]
    boundaries: Tuple[int, ...]
    profile_values: Tuple[Optional[float], ...]
    active_row_counts: Tuple[int, ...]
    initial_value: Optional[float]
    final_value: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    net_change: float
    total_absolute_variation: float
    directness_ratio: float
    time_to_high_ms: Optional[int]
    transition_count: int
    is_strictly_monotonic_increasing: bool
    is_non_decreasing: bool
    refitting_complexity: float
    second_differences: Tuple[float, ...]
    curvature_variance: float

    def summary_table(self) -> str:
        """Return a formatted ASCII table comparing column-level measurements."""
        lines = [
            f"=== {self.arrangement_name} ===",
            f"Columns: {self.column_count} | Duration: {self.total_duration_ms} ms | Directness Ratio: {self.directness_ratio:.3f}",
            f"Time to High: {self.time_to_high_ms} ms | Transition Count: {self.transition_count} | Non-decreasing: {self.is_non_decreasing}",
            f"Curvature Variance: {self.curvature_variance:.6f} | Refitting Complexity: {self.refitting_complexity:.2f}",
            "",
            f"{'Col':<5} | {'Interval (ms)':<18} | {'Dur (ms)':<8} | {'Active Rows':<11} | {'Dev Value (Row 1)':<18}",
            "-" * 72,
        ]
        for idx in range(self.column_count):
            start = self.boundaries[idx]
            end = self.boundaries[idx + 1]
            dur = self.column_durations_ms[idx]
            arc = self.active_row_counts[idx]
            val = self.profile_values[idx]
            val_str = f"{val:.2f}" if val is not None else "None"
            lines.append(f"{idx:<5} | [{start:>5}, {end:>5}) ms   | {dur:>6}   | {arc:>11} | {val_str:>18}")
        return "\n".join(lines)


def analyze_development_profile(
    timeline: MusicTimeline,
    arrangement_name: str = "Experimental Arrangement",
    aggregation: str = "mean",
    silent_value: Optional[float] = 0.0,
) -> DevelopmentAnalysis:
    """Perform a rigorous mathematical analysis of the low-to-high development profile.

    Quantifies:
    1. Directness ratio: |net_change| / total_absolute_variation (1.0 = strictly monotonic).
    2. Time to high: Timestamp where maximum value is first achieved.
    3. Transition count: Number of column boundaries with value changes.
    4. Refitting complexity: Column count relative to total sound events.
    5. Curvature variance: Variance of second differences across adjacent column intervals.

    Args:
        timeline: The MusicTimeline to analyze.
        arrangement_name: Descriptive name for reporting.
        aggregation: Aggregation rule for overlapping sounds.
        silent_value: Value for silent columns.

    Returns:
        DevelopmentAnalysis instance with all calculated metrics.
    """
    columns = timeline.build_columns()
    boundaries = timeline.extract_boundaries()
    col_count = len(columns)
    total_dur = timeline.total_duration_ms
    col_durations = tuple(col.duration_ms for col in columns)

    # Calculate profile values
    raw_values: List[Optional[float]] = [
        calculate_column_height(col, timeline, aggregation=aggregation, silent_value=silent_value)
        for col in columns
    ]
    profile_values = tuple(raw_values)
    active_row_counts = tuple(col.active_row_count for col in columns)

    # Filter numeric values for analysis
    numeric_vals = [v for v in raw_values if v is not None]

    if not numeric_vals:
        return DevelopmentAnalysis(
            arrangement_name=arrangement_name,
            column_count=col_count,
            total_duration_ms=total_dur,
            column_durations_ms=col_durations,
            boundaries=boundaries,
            profile_values=profile_values,
            active_row_counts=active_row_counts,
            initial_value=None,
            final_value=None,
            min_value=None,
            max_value=None,
            net_change=0.0,
            total_absolute_variation=0.0,
            directness_ratio=1.0,
            time_to_high_ms=None,
            transition_count=0,
            is_strictly_monotonic_increasing=True,
            is_non_decreasing=True,
            refitting_complexity=0.0,
            second_differences=(),
            curvature_variance=0.0,
        )

    initial_val = numeric_vals[0]
    final_val = numeric_vals[-1]
    min_val = min(numeric_vals)
    max_val = max(numeric_vals)
    net_change = final_val - initial_val

    # Total variation & transition count
    total_variation = 0.0
    transitions = 0
    strictly_increasing = True
    non_decreasing = True

    for i in range(len(numeric_vals) - 1):
        diff = numeric_vals[i + 1] - numeric_vals[i]
        total_variation += abs(diff)
        if abs(diff) > 1e-9:
            transitions += 1
        if diff <= 0:
            strictly_increasing = False
        if diff < -1e-9:
            non_decreasing = False

    # Directness ratio: |net_change| / total_variation
    if total_variation > 1e-9:
        directness = min(1.0, abs(net_change) / total_variation)
    else:
        directness = 1.0

    # Time to reach the maximum/high state (start of first column with max value)
    time_to_high: Optional[int] = None
    for idx, val in enumerate(raw_values):
        if val is not None and abs(val - max_val) < 1e-9:
            time_to_high = columns[idx].start_time_ms
            break

    # Refitting complexity: derived columns per sound event
    event_count = timeline.event_count
    refitting_complexity = float(col_count) / float(max(1, event_count))

    # Curvature analysis: second differences between column midpoint rates
    # First derivatives (slopes between consecutive column midpoints)
    slopes: List[float] = []
    for i in range(len(columns) - 1):
        mid_i = (columns[i].start_time_ms + columns[i].end_time_ms) / 2.0
        mid_next = (columns[i + 1].start_time_ms + columns[i + 1].end_time_ms) / 2.0
        dt = mid_next - mid_i
        v_i = raw_values[i] if raw_values[i] is not None else 0.0
        v_next = raw_values[i + 1] if raw_values[i + 1] is not None else 0.0
        if dt > 0:
            slopes.append((v_next - v_i) / dt)

    # Second differences (rate of change of slope)
    second_diffs: List[float] = []
    for i in range(len(slopes) - 1):
        second_diffs.append(slopes[i + 1] - slopes[i])

    # Variance of second differences
    if second_diffs:
        mean_sd = sum(second_diffs) / len(second_diffs)
        curv_var = sum((sd - mean_sd) ** 2 for sd in second_diffs) / len(second_diffs)
    else:
        curv_var = 0.0

    return DevelopmentAnalysis(
        arrangement_name=arrangement_name,
        column_count=col_count,
        total_duration_ms=total_dur,
        column_durations_ms=col_durations,
        boundaries=boundaries,
        profile_values=profile_values,
        active_row_counts=active_row_counts,
        initial_value=initial_val,
        final_value=final_val,
        min_value=min_val,
        max_value=max_val,
        net_change=net_change,
        total_absolute_variation=total_variation,
        directness_ratio=directness,
        time_to_high_ms=time_to_high,
        transition_count=transitions,
        is_strictly_monotonic_increasing=strictly_increasing,
        is_non_decreasing=non_decreasing,
        refitting_complexity=refitting_complexity,
        second_differences=tuple(second_diffs),
        curvature_variance=curv_var,
    )
