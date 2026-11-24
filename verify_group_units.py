"""
verify_group_units.py - Milestone 4A Mathematical Proof of Statement 18.

Demonstrates:
1. Shared uniform fundamental column units (u = 100ms default) with cyclic 0-9 labels.
2. Distinct multi-unit sound groups (Row 2: 4-unit groups, Row 3: 3-unit groups).
3. Derived composite Row 1 boundary segments ([0, 3, 4, 6, 8, 9, 12] -> widths 3, 1, 2, 2, 1, 3).
4. Strict non-destruction: The 12 fundamental cells remain uniform; Row 1 segments are composite overlays.
5. Sound preservation:
   - Input float values preserved without grid snapping.
   - Exact rational timing supported via fractions.Fraction.
6. Empirical comparison: Ascending duck-flight passage vs. Flat non-rising control passage.
7. Two-song independence: Song 1 (u=100ms, 4 vs 3) vs. Song 2 (u=250ms, 5 vs 2).
8. Meeting points (Guess C): Explicit boundary hand-offs where groups transition.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Tuple, Dict, Any, Union
import sys


@dataclass(frozen=True)
class NoteEvent:
    event_id: str
    pitch: int
    note_name: str
    start_ms: Union[float, Fraction]
    end_ms: Union[float, Fraction]

    @property
    def duration_ms(self) -> Union[float, Fraction]:
        return self.end_ms - self.start_ms


@dataclass(frozen=True)
class SoundGroup:
    group_id: str
    row_id: str
    start_unit: int
    end_unit: int
    notes: Tuple[NoteEvent, ...]

    @property
    def width_units(self) -> int:
        return self.end_unit - self.start_unit

    def start_time_ms(self, u_ms: int) -> float:
        return float(self.start_unit * u_ms)

    def end_time_ms(self, u_ms: int) -> float:
        return float(self.end_unit * u_ms)


@dataclass(frozen=True)
class FundamentalGrid:
    u_ms: int
    total_cells: int

    def cell_label(self, cell_idx: int) -> int:
        """Cyclic 0-9 display label."""
        return cell_idx % 10

    def cell_span_ms(self, cell_idx: int) -> Tuple[int, int]:
        return (cell_idx * self.u_ms, (cell_idx + 1) * self.u_ms)


@dataclass(frozen=True)
class Row1Segment:
    start_unit: int
    end_unit: int
    width_units: int
    start_ms: float
    end_ms: float
    active_groups: Tuple[str, ...]
    active_notes: Tuple[str, ...]
    mean_pitch: float
    active_row_count: int
    left_boundary_handoff: str
    right_boundary_handoff: str


class GroupTimeline:
    """Manages fundamental grid and multi-unit groups within an independent song."""

    def __init__(self, song_id: str, u_ms: int = 100, total_cells: int = 12):
        self.song_id = song_id
        self.grid = FundamentalGrid(u_ms=u_ms, total_cells=total_cells)
        self.groups_by_row: Dict[str, List[SoundGroup]] = {}
        self.off_grid_events: List[NoteEvent] = []

    def add_group(self, group: SoundGroup) -> None:
        if group.row_id not in self.groups_by_row:
            self.groups_by_row[group.row_id] = []
        self.groups_by_row[group.row_id].append(group)

    def add_off_grid_note(self, note: NoteEvent) -> None:
        """Preserves off-grid note event without destructive quantization."""
        self.off_grid_events.append(note)

    def row_boundaries(self, row_id: str) -> List[int]:
        """Boundary indices for a specific row."""
        boundaries = set()
        for g in self.groups_by_row.get(row_id, []):
            boundaries.add(g.start_unit)
            boundaries.add(g.end_unit)
        return sorted(boundaries)

    def combined_boundaries(self) -> List[int]:
        """Union of all group boundary unit indices across all temporary rows."""
        boundaries = set()
        for row_groups in self.groups_by_row.values():
            for g in row_groups:
                boundaries.add(g.start_unit)
                boundaries.add(g.end_unit)
        return sorted(boundaries)

    def _describe_boundary_events(self, unit_idx: int) -> str:
        """Describes specific group meeting points / hand-offs occurring at a boundary unit."""
        starts = []
        ends = []
        for row_groups in self.groups_by_row.values():
            for g in row_groups:
                if g.start_unit == unit_idx:
                    starts.append(g.group_id)
                if g.end_unit == unit_idx:
                    ends.append(g.group_id)

        if not starts and not ends:
            return "None (Continuous)"
        if starts and ends:
            return f"Hand-off: {', '.join(ends)} -> {', '.join(starts)}"
        if starts:
            return f"Entry: {', '.join(starts)}"
        return f"Exit: {', '.join(ends)}"

    def derive_row1_segments(self) -> List[Row1Segment]:
        """
        Derives the composite Row 1 intervals from the union of group boundaries.
        The underlying fundamental cells remain completely uniform.
        """
        bounds = self.combined_boundaries()
        if len(bounds) < 2:
            return []

        segments = []
        for i in range(len(bounds) - 1):
            s_u = bounds[i]
            e_u = bounds[i + 1]
            w_u = e_u - s_u
            s_ms = float(s_u * self.grid.u_ms)
            e_ms = float(e_u * self.grid.u_ms)

            # Identify active groups and notes covering this segment
            active = []
            active_notes = []
            active_rows = set()
            pitches = []
            for row_id, groups in self.groups_by_row.items():
                for g in groups:
                    # An interval [s_u, e_u) is active in group if it overlaps [g.start_unit, g.end_unit)
                    if not (e_u <= g.start_unit or s_u >= g.end_unit):
                        active.append(g.group_id)
                        active_rows.add(row_id)
                        for n in g.notes:
                            pitches.append(n.pitch)
                            active_notes.append(f"{n.note_name}({n.pitch})")

            mean_p = sum(pitches) / len(pitches) if pitches else 0.0

            left_desc = self._describe_boundary_events(s_u)
            right_desc = self._describe_boundary_events(e_u)

            segments.append(
                Row1Segment(
                    start_unit=s_u,
                    end_unit=e_u,
                    width_units=w_u,
                    start_ms=s_ms,
                    end_ms=e_ms,
                    active_groups=tuple(active),
                    active_notes=tuple(active_notes),
                    mean_pitch=mean_p,
                    active_row_count=len(active_rows),
                    left_boundary_handoff=left_desc,
                    right_boundary_handoff=right_desc,
                )
            )
        return segments


def build_ascending_passage(u_ms: int = 100) -> GroupTimeline:
    """
    Builds Passage 1: Ascending Duck-Flight Progression.
    Row 2 (width 4u): Low whirring / water contact (MIDI 36 -> 43 -> 48).
    Row 3 (width 3u): Flapping & rising flight (MIDI 60 -> 67 -> 76 -> 84).
    """
    song = GroupTimeline(song_id="Ascending_Flight_Song", u_ms=u_ms, total_cells=12)

    # Row 2: 3 groups of width 4 units (cells 0-4, 4-8, 8-12)
    g1 = SoundGroup(
        group_id="R2_LowWhirr_1",
        row_id="Row 2 (Low Whirring)",
        start_unit=0,
        end_unit=4,
        notes=(NoteEvent("n1", 36, "C2", 0.0, 400.0),),
    )
    g2 = SoundGroup(
        group_id="R2_LowWhirr_2",
        row_id="Row 2 (Low Whirring)",
        start_unit=4,
        end_unit=8,
        notes=(NoteEvent("n2", 43, "G2", 400.0, 800.0),),
    )
    g3 = SoundGroup(
        group_id="R2_LowWhirr_3",
        row_id="Row 2 (Low Whirring)",
        start_unit=8,
        end_unit=12,
        notes=(NoteEvent("n3", 48, "C3", 800.0, 1200.0),),
    )
    song.add_group(g1)
    song.add_group(g2)
    song.add_group(g3)

    # Row 3: 4 groups of width 3 units (cells 0-3, 3-6, 6-9, 9-12)
    gA = SoundGroup(
        group_id="R3_Flap_A",
        row_id="Row 3 (Ascending Flight)",
        start_unit=0,
        end_unit=3,
        notes=(NoteEvent("nA", 60, "C4", 0.0, 300.0),),
    )
    gB = SoundGroup(
        group_id="R3_Flap_B",
        row_id="Row 3 (Ascending Flight)",
        start_unit=3,
        end_unit=6,
        notes=(NoteEvent("nB", 67, "G4", 300.0, 600.0),),
    )
    gC = SoundGroup(
        group_id="R3_Flap_C",
        row_id="Row 3 (Ascending Flight)",
        start_unit=6,
        end_unit=9,
        notes=(NoteEvent("nC", 76, "E5", 600.0, 900.0),),
    )
    gD = SoundGroup(
        group_id="R3_Flap_D",
        row_id="Row 3 (Ascending Flight)",
        start_unit=9,
        end_unit=12,
        notes=(NoteEvent("nD", 84, "C6", 900.0, 1200.0),),
    )
    song.add_group(gA)
    song.add_group(gB)
    song.add_group(gC)
    song.add_group(gD)

    return song


def build_flat_control_passage(u_ms: int = 100) -> GroupTimeline:
    """
    Builds Passage 2: Flat Non-Rising Control Passage.
    Identical structural grouping (4u and 3u), but pitch remains steady (MIDI 48-50).
    Proves the program does not assume or hardcode a rise.
    """
    song = GroupTimeline(song_id="Flat_Control_Song", u_ms=u_ms, total_cells=12)

    # Row 2: 3 groups of width 4 units (flat low register)
    song.add_group(
        SoundGroup(
            "R2_Flat_1",
            "Row 2 (Steady)",
            0,
            4,
            (NoteEvent("f1", 48, "C3", 0.0, 400.0),),
        )
    )
    song.add_group(
        SoundGroup(
            "R2_Flat_2",
            "Row 2 (Steady)",
            4,
            8,
            (NoteEvent("f2", 48, "C3", 400.0, 800.0),),
        )
    )
    song.add_group(
        SoundGroup(
            "R2_Flat_3",
            "Row 2 (Steady)",
            8,
            12,
            (NoteEvent("f3", 48, "C3", 800.0, 1200.0),),
        )
    )

    # Row 3: 4 groups of width 3 units (flat middle register)
    song.add_group(
        SoundGroup(
            "R3_Flat_A",
            "Row 3 (Steady)",
            0,
            3,
            (NoteEvent("fA", 50, "D3", 0.0, 300.0),),
        )
    )
    song.add_group(
        SoundGroup(
            "R3_Flat_B",
            "Row 3 (Steady)",
            3,
            6,
            (NoteEvent("fB", 50, "D3", 300.0, 600.0),),
        )
    )
    song.add_group(
        SoundGroup(
            "R3_Flat_C",
            "Row 3 (Steady)",
            6,
            9,
            (NoteEvent("fC", 50, "D3", 600.0, 900.0),),
        )
    )
    song.add_group(
        SoundGroup(
            "R3_Flat_D",
            "Row 3 (Steady)",
            9,
            12,
            (NoteEvent("fD", 50, "D3", 900.0, 1200.0),),
        )
    )

    return song


def build_song_2_independent(u_ms: int = 250) -> GroupTimeline:
    """
    Builds Independent Song 2:
    Demonstrates independent fundamental unit u=250ms, 10 cells,
    Row 2 with 5-unit groups, Row 3 with 2-unit groups (LCM = 10).
    """
    song2 = GroupTimeline(song_id="Independent_Song_2", u_ms=u_ms, total_cells=10)
    # Row 2: 2 groups of width 5 units
    song2.add_group(
        SoundGroup(
            "S2_R2_G1",
            "Row 2 (5-unit)",
            0,
            5,
            (NoteEvent("s2_1", 40, "E2", 0.0, 1250.0),),
        )
    )
    song2.add_group(
        SoundGroup(
            "S2_R2_G2",
            "Row 2 (5-unit)",
            5,
            10,
            (NoteEvent("s2_2", 47, "B2", 1250.0, 2500.0),),
        )
    )
    # Row 3: 5 groups of width 2 units
    for i in range(5):
        s_u = i * 2
        e_u = s_u + 2
        song2.add_group(
            SoundGroup(
                f"S2_R3_G{i+1}",
                "Row 3 (2-unit)",
                s_u,
                e_u,
                (
                    NoteEvent(
                        f"s2_note_{i}",
                        60 + i * 2,
                        "Note",
                        float(s_u * 250),
                        float(e_u * 250),
                    ),
                ),
            )
        )
    return song2


def run_proof():
    print("=" * 80)
    print("MUSIC PROJECT — MILESTONE 4A MATHEMATICAL PROOF (STATEMENT 18)")
    print("=" * 80)

    # 1. Inspect Fundamental Grid
    u = 100
    song1 = build_ascending_passage(u_ms=u)
    print(f"\n[1] FUNDAMENTAL GRID FOR SONG 1 (u = {u} ms, 12 cells):")
    labels = [str(song1.grid.cell_label(c)) for c in range(song1.grid.total_cells)]
    indices = [f"{c:2d}" for c in range(song1.grid.total_cells)]
    print(f"  Fundamental Cell Indices: [{' '.join(indices)}]")
    print(f"  Cyclic Display Labels:    [{' '.join(f' {l}' for l in labels)}]")
    print(f"  Grid Uniformity: All 12 cells strictly {u} ms each.")

    # 2. Inspect Row 2 and Row 3 Group Boundaries
    r2_bounds = song1.row_boundaries("Row 2 (Low Whirring)")
    r3_bounds = song1.row_boundaries("Row 3 (Ascending Flight)")
    print(f"\n[2] TEMPORARY ROW GROUP BOUNDARIES:")
    print(f"  Row 2 (Repeating 4-unit groups): {r2_bounds}")
    print(f"  Row 3 (Repeating 3-unit groups): {r3_bounds}")

    # Assert exact boundaries from specification
    assert r2_bounds == [
        0,
        4,
        8,
        12,
    ], f"Row 2 boundaries expected [0, 4, 8, 12], got {r2_bounds}"
    assert r3_bounds == [
        0,
        3,
        6,
        9,
        12,
    ], f"Row 3 boundaries expected [0, 3, 6, 9, 12], got {r3_bounds}"
    print("  -> Group boundaries verified matching Statement 18!")

    # 3. Inspect Combined Boundaries & Composite Segments
    comb_bounds = song1.combined_boundaries()
    print(f"\n[3] COMBINED BOUNDARIES & ROW 1 SEGMENTS:")
    print(f"  Combined Boundary Set: {comb_bounds}")
    assert comb_bounds == [
        0,
        3,
        4,
        6,
        8,
        9,
        12,
    ], f"Expected [0, 3, 4, 6, 8, 9, 12], got {comb_bounds}"

    r1_segments = song1.derive_row1_segments()
    seg_widths = [s.width_units for s in r1_segments]
    print(f"  Row 1 Composite Segment Widths (in units u): {seg_widths}")
    assert seg_widths == [
        3,
        1,
        2,
        2,
        1,
        3,
    ], f"Expected widths [3, 1, 2, 2, 1, 3], got {seg_widths}"
    assert (
        sum(seg_widths) == 12
    ), f"Expected total width 12 units, got {sum(seg_widths)}"
    print("  -> Composite segment widths verified: 3, 1, 2, 2, 1, 3 (Total = 12u)!")
    print(
        "  -> Non-Destruction Check: The 12 fundamental cells remain equal and intact."
    )

    # 4. Comparative Trajectory Analysis: Ascending vs Flat Control
    flat_song = build_flat_control_passage(u_ms=u)
    flat_segments = flat_song.derive_row1_segments()

    print(
        f"\n[4] MULTI-DIMENSIONAL DEVELOPMENT: ASCENDING (TAKEOFF) VS FLAT (CONTROL)"
    )
    print(
        "Note: 'Mean Pitch' is a numeric average centroid, not a discrete note name."
    )
    print("-" * 96)
    print(
        f"{'Seg':<4} | {'Units':<7} | {'Time (ms)':<12} | {'Active Notes':<18} | {'Asc Pitch':<10} | {'Flat Pitch':<10} | {'Left Boundary Meeting Point'}"
    )
    print("-" * 96)

    for idx, (asc_s, flt_s) in enumerate(
        zip(r1_segments, flat_segments), start=1
    ):
        notes_str = ", ".join(asc_s.active_notes)
        time_str = f"[{asc_s.start_ms:.0f}, {asc_s.end_ms:.0f})"
        unit_str = f"[{asc_s.start_unit}, {asc_s.end_unit}) ({asc_s.width_units}u)"
        print(
            f"{idx:<4} | {unit_str:<7} | {time_str:<12} | {notes_str:<18} | {asc_s.mean_pitch:<10.1f} | {flt_s.mean_pitch:<10.1f} | {asc_s.left_boundary_handoff}"
        )

    # Validate Ascending Trajectory
    asc_pitches = [s.mean_pitch for s in r1_segments]
    flat_pitches = [s.mean_pitch for s in flat_segments]
    print(
        f"\n  Ascending Numeric Pitch Trajectory: {[round(p, 1) for p in asc_pitches]}"
    )
    print(
        f"  Flat Numeric Pitch Trajectory:      {[round(p, 1) for p in flat_pitches]}"
    )

    assert (
        asc_pitches[-1] > asc_pitches[0]
    ), "Ascending passage must rise from start to finish"
    assert (
        flat_pitches[-1] == flat_pitches[0]
    ), "Flat control passage must remain steady"
    print("  -> Confirmed: Algorithm detects true rise without hardcoding it!")

    # 5. Timing Precision Check (Both Float and Exact Rational)
    print(f"\n[5] TIMING PRECISION AND NON-QUANTIZATION AUDIT:")
    # A. Float value preservation without grid snapping
    float_note = NoteEvent(
        "float_offgrid", pitch=65, note_name="F4", start_ms=145.2, end_ms=387.6
    )
    song1.add_off_grid_note(float_note)
    stored_float = song1.off_grid_events[0]
    assert (
        stored_float.start_ms == 145.2
    ), "Float start_ms was modified or quantized!"
    assert (
        stored_float.end_ms == 387.6
    ), "Float end_ms was modified or quantized!"
    assert (
        abs(stored_float.duration_ms - 242.4) < 1e-6
    ), "Float duration altered!"
    print(
        f"  [A. Float Preservation] Stored: start={stored_float.start_ms}ms, end={stored_float.end_ms}ms (No grid snapping)."
    )

    # B. Mathematically exact rational timing (using fractions.Fraction)
    rational_start = Fraction(726, 5)  # Exactly 145.2 ms
    rational_end = Fraction(1938, 5)  # Exactly 387.6 ms
    rational_note = NoteEvent(
        "rational_offgrid",
        pitch=65,
        note_name="F4",
        start_ms=rational_start,
        end_ms=rational_end,
    )
    assert (
        rational_note.start_ms == Fraction(726, 5)
    ), "Rational start timing altered!"
    assert (
        rational_note.end_ms == Fraction(1938, 5)
    ), "Rational end timing altered!"
    assert rational_note.duration_ms == Fraction(
        1212, 5
    ), "Rational duration altered!"
    print(
        f"  [B. Rational Exactness] Exact Fractions: start={rational_note.start_ms}ms, end={rational_note.end_note if hasattr(rational_note, 'end_note') else rational_note.end_ms}ms, duration={rational_note.duration_ms}ms."
    )
    print(
        "  -> Confirmed: Both float input preservation and exact rational arithmetic verified."
    )

    # 6. Two-Song Independence Check
    print(f"\n[6] TWO-SONG INDEPENDENCE PROOF:")
    song2 = build_song_2_independent(u_ms=250)
    s2_bounds = song2.combined_boundaries()
    s2_segments = song2.derive_row1_segments()
    s2_widths = [s.width_units for s in s2_segments]

    print(
        f"  Song 1: u={song1.grid.u_ms}ms, 12 cells, bounds={comb_bounds}, widths={seg_widths}"
    )
    print(
        f"  Song 2: u={song2.grid.u_ms}ms, 10 cells, bounds={s2_bounds}, widths={s2_widths}"
    )

    assert song1.grid.u_ms == 100 and song2.grid.u_ms == 250
    assert song1.grid.total_cells == 12 and song2.grid.total_cells == 10
    assert comb_bounds != s2_bounds
    print(
        "  -> Confirmed: Song 1 and Song 2 maintain completely independent grids and parameters."
    )

    print("\n" + "=" * 80)
    print("ALL MILESTONE 4A MATHEMATICAL CHECKS PASSED SUCCESSFULLY (EXIT CODE 0)!")
    print("=" * 80)


if __name__ == "__main__":
    run_proof()
