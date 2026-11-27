"""group_discovery.py - Sound-group BOUNDARY candidates (JOB-04 experimental engine).

Status (JOB-04 Stage 2a, 2026-11-27)
------------------------------------
These are experimental BOUNDARY-DISCOVERY candidates.  None of them detects recurrence (that a phrase
or group recurs); recurrence discovery is the separately reviewed JOB-04 Stage 2b.  Contents:

* Sifter A: rests/breath (silence = no note sounding in the row, using the running maximum end).
* Sifter B: periodic-grid experiment (equal-width slices from fixed candidate spans).  Retained as a
  comparison candidate only; its output must not become the structure of recurrence discoveries.
* Sifter C: melodic contour turning points / leaps, on unambiguous monophonic pitched runs only.
* Sifter D: cross-row hand-offs.
* Controls: fixed-width slicing and seeded random boundaries (Monte Carlo, count-matched).
* Evaluation: maximum-cardinality one-to-one boundary matching (augmenting paths).
* derive_row1_from_discovered_groups: LEGACY compatibility only (Row 1 belongs to later jobs; it is not
  extended and is not part of recurrence discovery).

Input contract (Stage 2a)
-------------------------
Every note is normalized by normalize_note():
* Timing, in milliseconds.  SoundEvent: the authoritative exact accessor
  (sound_event.get_authoritative_exact_timing) is used, and its provenance is recorded
  ('musicxml_exact_rational', 'audio_exact_rational' or 'integer_ms_fallback').  Other objects:
  'start_ms'/'end_ms' or 'start_time_ms'/'end_time_ms' numbers ('ms_field'), converted to Fraction
  exactly (no rounding).  Tick-only objects are rejected (AmbiguousTimingError): ticks are not
  milliseconds.  Non-finite, boolean, missing or non-positive-duration timing raises NoteTimingError.
* Pitch: 'pitch', else 'height', kept as given (fractional pitch preserved).  None or absent means
  UNPITCHED; no pitch is ever invented.  Non-finite or boolean pitch raises NoteTimingError.
Sifters A, C and D compute in exact Fraction milliseconds; B and the controls keep their legacy float
arithmetic (they are grid and chance comparisons).  Groups hold the ORIGINAL note objects plus their
event ids and indices in the row's deterministic order (start, end, input position).
"""

from __future__ import annotations

import math
import numbers
import random
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from music_model.sound_event import SoundEvent, get_authoritative_exact_timing


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class NoteTimingError(ValueError):
    """A note's timing or pitch is missing, malformed or non-finite."""


class AmbiguousTimingError(NoteTimingError):
    """A note carries timing in a unit that cannot be interpreted as milliseconds (e.g. MIDI ticks)."""


# Supported input bounds (Stage 2b).  Values outside raise NoteTimingError; they are checked exactly.
MAX_TIME_MS = 10 ** 12          # about 31.7 years
PITCH_MIN, PITCH_MAX = -10_000, 10_000   # generous: MIDI is 0-127; experimental heights are small numbers


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizedNote:
    """A note reduced to exact millisecond timing and an optional pitch, linked to its source object."""

    source: Any
    row_id: str
    input_index: int
    start: Fraction           # exact milliseconds
    end: Fraction             # exact milliseconds
    timing_source: str        # 'musicxml_exact_rational' | 'audio_exact_rational' | 'integer_ms_fallback' | 'ms_field'
    pitch: Optional[Any]      # as given: int, Fraction or float (never rounded); None = unpitched
    pitch_source: str         # 'pitch' | 'height' | 'none'
    label: str
    event_id: str
    # Stage 2b additions
    pitch_exact: Optional[Fraction] = None   # exact value of the stored pitch (comparison key); None = unpitched
    pitch_kind: str = "none"                 # 'integer' | 'rational' | 'binary_float' | 'none'
    pitch_estimated: bool = False            # True when the source is an acoustic estimate (JOB-02 WAV import)
    voice_id: Optional[str] = None           # explicit source voice ('voice' attribute); '' or blank = unspecified (None)
    supplied_event_id: Optional[str] = None  # the event id supplied by the source (non-empty), else None

    @property
    def start_ms(self) -> float:
        return float(self.start)

    @property
    def end_ms(self) -> float:
        return float(self.end)


@dataclass(frozen=True)
class DiscoveredGroup:
    """A discovered sound group within a specific row."""

    group_id: str
    row_id: str
    start_ms: float
    end_ms: float
    notes: Tuple[Any, ...]
    method: str
    start_unit: Optional[float] = None
    end_unit: Optional[float] = None
    # Stage 2a additions (identity, exact timing, provenance)
    event_ids: Tuple[str, ...] = ()
    event_indices: Tuple[int, ...] = ()       # indices in the row's deterministic order
    exact_start_ms: Optional[Fraction] = None
    exact_end_ms: Optional[Fraction] = None
    timing_sources: Tuple[str, ...] = ()
    unpitched_count: int = 0

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    @property
    def width_units(self) -> Optional[float]:
        if self.start_unit is not None and self.end_unit is not None:
            return self.end_unit - self.start_unit
        return None


@dataclass(frozen=True)
class GroupingDiagnostic:
    """Diagnostics distinguishing silence, overlap, off-grid timing, unpitched events and defects."""

    silence_intervals_ms: Tuple[Tuple[float, float], ...]
    overlapping_intervals_ms: Tuple[Tuple[float, float, str], ...]
    off_grid_notes_count: int
    malformed_notes_count: int
    notes_analyzed_count: int
    # Stage 2a additions
    silence_intervals_by_row: Dict[str, Tuple[Tuple[float, float], ...]] = field(default_factory=dict)
    unpitched_notes_count: int = 0
    timing_source_counts: Dict[str, int] = field(default_factory=dict)
    polyphonic_rows: Tuple[str, ...] = ()
    malformed_notes: Tuple[Tuple[str, str], ...] = ()    # (event id, reason)


@dataclass(frozen=True)
class EvaluationMetrics:
    """Evaluation of discovered boundaries against reference boundaries.

    'specificity' is a LEGACY field: 1.0 when there are no false positives, else 0.0.  It is not a
    true-negative rate (boundary evaluation has no defined set of negatives).  Use
    'zero_false_positives', 'empty_reference' and 'vacuous' instead.  When both the reference and the
    discovered sets are empty, the legacy precision/recall/F1 of 1.0 are reported with vacuous=True.
    """

    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    tolerance_ms: float
    discovered_count: int
    reference_count: int
    is_internal_only: bool = False
    specificity: float = 1.0
    zero_false_positives: bool = True
    empty_reference: bool = False
    vacuous: bool = False


@dataclass(frozen=True)
class DiscoveredRow1Segment:
    """LEGACY composite segment derived from the union of discovered group boundaries.

    Retained for compatibility only.  mean_pitch averages PITCHED notes; it is NaN when none is pitched.
    """

    start_ms: float
    end_ms: float
    duration_ms: float
    active_row_count: int
    active_group_count: int
    mean_pitch: float
    active_groups: Tuple[str, ...]
    start_unit: Optional[float] = None
    end_unit: Optional[float] = None
    width_units: Optional[float] = None
    is_sub_unit: bool = False
    formatted_units: str = ""


@dataclass(frozen=True)
class GroupingResult:
    """Result of running a discovery sifter or control on a passage."""

    sifter_name: str
    groups_by_row: Dict[str, List[DiscoveredGroup]]
    discovered_boundaries_ms: List[float]          # union over rows (legacy); see boundaries_by_row
    diagnostics: GroupingDiagnostic
    row1_segments: List[DiscoveredRow1Segment]    # legacy compatibility only
    # Stage 2a additions
    boundaries_by_row: Dict[str, List[float]] = field(default_factory=dict)
    segmentation_kind: str = ""                    # 'boundary_candidate' | 'periodic_grid_experiment' | '..._control'
    warnings: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Note normalization (Stage 2a input contract)
# ---------------------------------------------------------------------------

def _real(value: Any, what: str, ident: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise NoteTimingError(f"{ident}: {what} must be a real number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise NoteTimingError(f"{ident}: {what} is not finite ({value!r})")
    return Fraction(value)


def _first_attr(note: Any, names: Sequence[str]) -> Tuple[Optional[str], Any]:
    for n in names:
        if hasattr(note, n):
            return n, getattr(note, n)
    return None, None


def normalize_note(note: Any, row_id: str, input_index: int) -> NormalizedNote:
    """Normalize one note (see the module docstring).  Raises NoteTimingError / AmbiguousTimingError."""
    ident = str(getattr(note, "event_id", "") or f"{row_id}#{input_index}")

    if isinstance(note, SoundEvent):
        try:
            start, end, _ = get_authoritative_exact_timing(note, unit="ms")
        except ValueError as ex:
            raise NoteTimingError(f"{ident}: {ex}") from ex
        attrs = note.attributes or {}
        if "exact_start_ms_rational" in attrs:
            timing_source = "musicxml_exact_rational"
        elif "exact_start_sec_rational" in attrs:
            timing_source = "audio_exact_rational"
        else:
            timing_source = "integer_ms_fallback"
    else:
        s_name, s_val = _first_attr(note, ("start_ms", "start_time_ms"))
        e_name, e_val = _first_attr(note, ("end_ms", "end_time_ms"))
        if s_name is None or e_name is None or s_val is None or e_val is None:
            if hasattr(note, "start_tick") or hasattr(note, "end_tick"):
                raise AmbiguousTimingError(
                    f"{ident}: only tick timing is present; ticks are not milliseconds. Convert with the "
                    f"source tempo map (e.g. MidiImporter) before group discovery.")
            raise NoteTimingError(f"{ident}: missing millisecond timing (start_ms/end_ms or start_time_ms/end_time_ms)")
        start = _real(s_val, s_name, ident)
        end = _real(e_val, e_name, ident)
        timing_source = "ms_field"

    # Supported bounds (checked exactly, before any float conversion).
    if start < 0:
        raise NoteTimingError(f"{ident}: start must be >= 0 ms (got {start})")
    if end > MAX_TIME_MS:
        raise NoteTimingError(f"{ident}: end exceeds the supported maximum of {MAX_TIME_MS} ms")
    if end <= start:
        raise NoteTimingError(f"{ident}: end ({float(end)}) must be after start ({float(start)})")

    p_name, p_val = None, None
    for name in ("pitch", "height"):
        if hasattr(note, name) and getattr(note, name) is not None:
            p_name, p_val = name, getattr(note, name)
            break
    pitch_exact: Optional[Fraction] = None
    pitch_kind = "none"
    if p_val is not None:
        if isinstance(p_val, bool) or not isinstance(p_val, numbers.Real):
            raise NoteTimingError(f"{ident}: pitch/height must be a real number or None, got {p_val!r}")
        if isinstance(p_val, float) and not math.isfinite(p_val):
            raise NoteTimingError(f"{ident}: pitch/height is not finite ({p_val!r})")
        try:
            pitch_exact = Fraction(p_val)
        except (TypeError, ValueError, OverflowError) as ex:
            raise NoteTimingError(f"{ident}: pitch/height {p_val!r} is not representable exactly ({ex})") from ex
        if not (PITCH_MIN <= pitch_exact <= PITCH_MAX):
            raise NoteTimingError(f"{ident}: pitch/height outside the supported range [{PITCH_MIN}, {PITCH_MAX}]")
        pitch_kind = ("integer" if isinstance(p_val, numbers.Integral)
                      else "binary_float" if isinstance(p_val, float) else "rational")
        pitch = p_val                                # stored value, unchanged (no float conversion)
    else:
        pitch = None

    attrs = getattr(note, "attributes", None) or {}
    estimated = isinstance(attrs, dict) and attrs.get("source_type") == "audio_wav"
    voice = getattr(note, "voice", None)
    if voice is None and isinstance(attrs, dict):
        voice = attrs.get("voice")
    voice_id = None if voice is None or str(voice).strip() == "" else str(voice)   # blank = unspecified
    supplied = getattr(note, "event_id", None)
    supplied_id = str(supplied) if supplied is not None and str(supplied) != "" else None
    label = getattr(note, "note_name", None) or getattr(note, "label", None) or (
        f"Note_{pitch}" if pitch is not None else "Unpitched")
    return NormalizedNote(note, row_id, input_index, start, end, timing_source, pitch,
                          p_name or "none", str(label), supplied_id or ident,
                          pitch_exact, pitch_kind, bool(estimated and pitch is not None),
                          voice_id, supplied_id)


def extract_note_timing(note: Any) -> Tuple[float, float, Optional[float], str]:
    """Legacy accessor: (start_ms, end_ms, pitch, label) under the Stage 2a contract.

    Pitch is returned as given (fractional kept) or None for unpitched; it is no longer defaulted to 60.
    Tick-only timing raises AmbiguousTimingError.
    """
    n = normalize_note(note, str(getattr(note, "row_id", "") or "row"), 0)
    return n.start_ms, n.end_ms, n.pitch, n.label


def _normalize_rows(notes_by_row: Dict[str, Sequence[Any]]) -> Dict[str, List[NormalizedNote]]:
    """Strict normalization, sorted deterministically by (start, end, input position)."""
    out: Dict[str, List[NormalizedNote]] = {}
    for row_id, notes in notes_by_row.items():
        nn = [normalize_note(n, row_id, i) for i, n in enumerate(notes or [])]
        out[row_id] = sorted(nn, key=lambda x: (x.start, x.end, x.input_index))
    return out


def _is_monophonic(row: Sequence[NormalizedNote]) -> bool:
    run_end: Optional[Fraction] = None
    for n in row:
        if run_end is not None and n.start < run_end:
            return False
        run_end = n.end if run_end is None else max(run_end, n.end)
    return True


# ---------------------------------------------------------------------------
# Diagnostics: Silence, Overlap, Off-Grid Notes
# ---------------------------------------------------------------------------

def diagnose_passage_timing(
    notes_by_row: Dict[str, Sequence[Any]],
    u_ms: Optional[float] = None,
    grid_tolerance_ms: float = 1e-3,
) -> GroupingDiagnostic:
    """Distinguish genuine silence, overlap, off-grid timing, unpitched and malformed notes.

    Lenient: notes that fail normalization are COUNTED (malformed_notes) and excluded, never raised.
    Silence is an interval in which no note of the row sounds (running maximum end).
    """
    silence_all: List[Tuple[float, float]] = []
    silence_by_row: Dict[str, Tuple[Tuple[float, float], ...]] = {}
    overlaps: List[Tuple[float, float, str]] = []
    off_grid = 0
    malformed: List[Tuple[str, str]] = []
    total = 0
    unpitched = 0
    sources: Dict[str, int] = {}
    poly: List[str] = []

    for row_id, notes in notes_by_row.items():
        notes = list(notes or [])
        total += len(notes)
        good: List[NormalizedNote] = []
        for i, n in enumerate(notes):
            try:
                good.append(normalize_note(n, row_id, i))
            except NoteTimingError as ex:
                malformed.append((str(getattr(n, "event_id", "") or f"{row_id}#{i}"), str(ex)))
        good.sort(key=lambda x: (x.start, x.end, x.input_index))
        row_sil: List[Tuple[float, float]] = []
        run_end: Optional[Fraction] = None
        for n in good:
            sources[n.timing_source] = sources.get(n.timing_source, 0) + 1
            if n.pitch is None:
                unpitched += 1
            if u_ms is not None and u_ms > 0:
                for t in (n.start_ms, n.end_ms):
                    rem = t % u_ms
                    if rem > grid_tolerance_ms and (u_ms - rem) > grid_tolerance_ms:
                        off_grid += 1
            if run_end is not None:
                if n.start > run_end:
                    row_sil.append((float(run_end), n.start_ms))
                elif n.start < run_end:
                    overlaps.append((n.start_ms, float(min(run_end, n.end)), row_id))
            run_end = n.end if run_end is None else max(run_end, n.end)
        if good and not _is_monophonic(good):
            poly.append(row_id)
        silence_by_row[row_id] = tuple(row_sil)
        silence_all.extend(row_sil)

    return GroupingDiagnostic(
        silence_intervals_ms=tuple(silence_all),
        overlapping_intervals_ms=tuple(overlaps),
        off_grid_notes_count=off_grid,
        malformed_notes_count=len(malformed),
        notes_analyzed_count=total,
        silence_intervals_by_row=silence_by_row,
        unpitched_notes_count=unpitched,
        timing_source_counts=sources,
        polyphonic_rows=tuple(poly),
        malformed_notes=tuple(malformed),
    )


# ---------------------------------------------------------------------------
# Shared group construction
# ---------------------------------------------------------------------------

def _member_group(row_id: str, group_id: str, members: Sequence[Tuple[int, NormalizedNote]],
                  method: str, u_ms: Optional[float]) -> DiscoveredGroup:
    """A group delimited by its member notes: start = earliest start, end = LATEST end."""
    start = min(n.start for _, n in members)
    end = max(n.end for _, n in members)
    return DiscoveredGroup(
        group_id=group_id, row_id=row_id, start_ms=float(start), end_ms=float(end),
        notes=tuple(n.source for _, n in members), method=method,
        start_unit=(float(start) / u_ms) if u_ms else None, end_unit=(float(end) / u_ms) if u_ms else None,
        event_ids=tuple(n.event_id for _, n in members), event_indices=tuple(i for i, _ in members),
        exact_start_ms=start, exact_end_ms=end,
        timing_sources=tuple(sorted({n.timing_source for _, n in members})),
        unpitched_count=sum(1 for _, n in members if n.pitch is None),
    )


def _slice_group(row_id: str, group_id: str, row: Sequence[NormalizedNote], g_start: float, g_end: float,
                 method: str, u_ms: Optional[float]) -> DiscoveredGroup:
    """A grid/control slice [g_start, g_end): members are notes intersecting the slice (legacy rule)."""
    members = [(i, n) for i, n in enumerate(row) if not (n.end_ms <= g_start or n.start_ms >= g_end)]
    return DiscoveredGroup(
        group_id=group_id, row_id=row_id, start_ms=g_start, end_ms=g_end,
        notes=tuple(n.source for _, n in members), method=method,
        start_unit=(g_start / u_ms) if u_ms else None, end_unit=(g_end / u_ms) if u_ms else None,
        event_ids=tuple(n.event_id for _, n in members), event_indices=tuple(i for i, _ in members),
        exact_start_ms=None, exact_end_ms=None,
        timing_sources=tuple(sorted({n.timing_source for _, n in members})),
        unpitched_count=sum(1 for _, n in members if n.pitch is None),
    )


def _finish(name: str, kind: str, groups_by_row: Dict[str, List[DiscoveredGroup]],
            notes_by_row: Dict[str, Sequence[Any]], u_ms: Optional[float],
            warnings: Sequence[str] = (), extra_boundaries: Optional[List[float]] = None) -> GroupingResult:
    by_row = {r: sorted({b for g in gs for b in (g.start_ms, g.end_ms)}) for r, gs in groups_by_row.items()}
    union = sorted({b for bs in by_row.values() for b in bs}) if extra_boundaries is None else extra_boundaries
    return GroupingResult(
        sifter_name=name, groups_by_row=groups_by_row, discovered_boundaries_ms=union,
        diagnostics=diagnose_passage_timing(notes_by_row, u_ms),
        row1_segments=derive_row1_from_discovered_groups(groups_by_row, u_ms),
        boundaries_by_row=by_row, segmentation_kind=kind, warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Sifter A: Breath / Articulation Rest Sifter
# ---------------------------------------------------------------------------

def sift_breath_rests(
    notes_by_row: Dict[str, Sequence[Any]],
    min_gap_ms: float = 100.0,
    u_ms: Optional[float] = None,
) -> GroupingResult:
    """Sifter A: group boundaries at rests of at least min_gap_ms.

    A rest is an interval in which NO note of the row sounds: the gap is measured from the running
    maximum end of the current group, so a sustained note under shorter notes is not a rest.
    """
    rows = _normalize_rows(notes_by_row)
    groups_by_row: Dict[str, List[DiscoveredGroup]] = {}
    for row_id, row in rows.items():
        if not row:
            continue
        groups: List[DiscoveredGroup] = []
        current: List[Tuple[int, NormalizedNote]] = [(0, row[0])]
        run_end = row[0].end
        for i in range(1, len(row)):
            n = row[i]
            if n.start - run_end >= Fraction(min_gap_ms):
                groups.append(_member_group(row_id, f"{row_id}_grp_{len(groups) + 1}", current, "Sifter_A_Rests", u_ms))
                current, run_end = [(i, n)], n.end
            else:
                current.append((i, n))
                run_end = max(run_end, n.end)
        groups.append(_member_group(row_id, f"{row_id}_grp_{len(groups) + 1}", current, "Sifter_A_Rests", u_ms))
        groups_by_row[row_id] = groups
    return _finish("Sifter A: Breath / Articulation Rest Sifter", "boundary_candidate", groups_by_row, notes_by_row, u_ms)


# ---------------------------------------------------------------------------
# Sifter B: Periodic-grid ("motoric rhythm") experiment
# ---------------------------------------------------------------------------

def sift_motoric_rhythm(
    notes_by_row: Dict[str, Sequence[Any]],
    u_ms: Optional[float] = 100.0,
    min_repeats: int = 2,
    candidate_spans_ms: Sequence[float] = (300.0, 400.0, 200.0),
    tolerance_ms: float = 20.0,
) -> GroupingResult:
    """Sifter B: PERIODIC-GRID EXPERIMENT (comparison candidate, not a recurrence detector).

    For each candidate span s, counts grid points row_start + k*s that lie within tolerance of a note
    onset or offset; a span is accepted at >= 70% alignment.  Output groups are EQUAL-WIDTH slices of the
    chosen span (legacy semantics, unchanged).  Only the spans in candidate_spans_ms are tried.
    """
    rows = _normalize_rows(notes_by_row)
    groups_by_row: Dict[str, List[DiscoveredGroup]] = {}
    for row_id, row in rows.items():
        if not row:
            continue
        row_start = row[0].start_ms
        row_end = max(n.end_ms for n in row)
        total = row_end - row_start
        best_span: Optional[float] = None
        best_score = 0
        for span in candidate_spans_ms:
            if span <= 0:
                continue
            periods = int(round(total / span))
            if periods < min_repeats:
                continue
            aligned = sum(
                1 for k in range(periods + 1)
                if any(abs(n.start_ms - (row_start + k * span)) <= tolerance_ms
                       or abs(n.end_ms - (row_start + k * span)) <= tolerance_ms for n in row))
            if aligned >= (periods + 1) * 0.7 and aligned > best_score:
                best_score, best_span = aligned, span
        groups: List[DiscoveredGroup] = []
        if best_span is not None:
            for k in range(int(round(total / best_span))):
                g_start = row_start + k * best_span
                g_end = min(row_start + (k + 1) * best_span, row_end)
                groups.append(_slice_group(row_id, f"{row_id}_motor_{k + 1}", row, g_start, g_end,
                                           f"Sifter_B_Motoric_{int(best_span)}ms", u_ms))
        else:
            groups.append(_member_group(row_id, f"{row_id}_unsegmented", list(enumerate(row)),
                                        "Sifter_B_NoRepetition", u_ms))
        groups_by_row[row_id] = groups
    return _finish("Sifter B: Motoric Rhythm Sifter", "periodic_grid_experiment", groups_by_row, notes_by_row, u_ms)


# ---------------------------------------------------------------------------
# Sifter C: Melodic Contour / Gestural Direction Sifter
# ---------------------------------------------------------------------------

def sift_melodic_contour(
    notes_by_row: Dict[str, Sequence[Any]],
    min_leap_semitones: int = 5,
    u_ms: Optional[float] = None,
) -> GroupingResult:
    """Sifter C: boundaries at pitch-direction turning points or leaps >= min_leap_semitones.

    Applied only to unambiguous MONOPHONIC rows (no note starts before the previous notes have ended).
    A polyphonic row is not given an invented melodic order: it is returned as one group
    ('Sifter_C_PolyphonicUnsupported') and reported in diagnostics.polyphonic_rows and warnings.
    Unpitched notes break the pitched sequence: each becomes its own 'Sifter_C_Unpitched' group, and no
    interval is computed across it.
    """
    rows = _normalize_rows(notes_by_row)
    groups_by_row: Dict[str, List[DiscoveredGroup]] = {}
    warnings: List[str] = []
    for row_id, row in rows.items():
        if not row:
            continue
        if len(row) == 1:
            groups_by_row[row_id] = [_member_group(row_id, f"{row_id}_gest_1", [(0, row[0])], "Sifter_C_SingleNote", u_ms)]
            continue
        if not _is_monophonic(row):
            warnings.append(f"Sifter C: row {row_id!r} is polyphonic; contour not computed (no melodic order invented)")
            groups_by_row[row_id] = [_member_group(row_id, f"{row_id}_poly_1", list(enumerate(row)),
                                                   "Sifter_C_PolyphonicUnsupported", u_ms)]
            continue
        groups: List[DiscoveredGroup] = []

        def emit(members, method="Sifter_C_Contour"):
            groups.append(_member_group(row_id, f"{row_id}_contour_{len(groups) + 1}", members, method, u_ms))

        # Split into maximal pitched runs separated by unpitched notes.
        run: List[Tuple[int, NormalizedNote]] = []
        runs: List[Tuple[str, List[Tuple[int, NormalizedNote]]]] = []
        for i, n in enumerate(row):
            if n.pitch is None:
                if run:
                    runs.append(("pitched", run)); run = []
                runs.append(("unpitched", [(i, n)]))
            else:
                run.append((i, n))
        if run:
            runs.append(("pitched", run))

        for kind, members in runs:
            if kind == "unpitched":
                emit(members, "Sifter_C_Unpitched")
                continue
            current = [members[0]]
            for j in range(len(members) - 1):
                p_curr = members[j][1].pitch
                p_next = members[j + 1][1].pitch
                interval = p_next - p_curr
                prev_dir = 0
                if j > 0:
                    p_prev = members[j - 1][1].pitch
                    prev_dir = 1 if p_curr > p_prev else (-1 if p_curr < p_prev else 0)
                curr_dir = 1 if interval > 0 else (-1 if interval < 0 else 0)
                turning = (prev_dir != 0 and curr_dir != 0 and prev_dir != curr_dir) or abs(interval) >= min_leap_semitones
                if turning:
                    emit(current)
                    current = [members[j + 1]]
                else:
                    current.append(members[j + 1])
            emit(current)
        groups_by_row[row_id] = groups
    return _finish("Sifter C: Melodic Contour / Gestural Sifter", "boundary_candidate", groups_by_row,
                   notes_by_row, u_ms, warnings)


# ---------------------------------------------------------------------------
# Sifter D: Cross-Row Hand-off / Interaction Sifter
# ---------------------------------------------------------------------------

def sift_cross_row_handoffs(
    notes_by_row: Dict[str, Sequence[Any]],
    window_ms: float = 50.0,
    u_ms: Optional[float] = None,
) -> GroupingResult:
    """Sifter D: boundaries in a row where another row has an onset/offset between consecutive notes
    (start(i) < t <= start(i+1)) or within window_ms of end(i).  Legacy rule; in dense polyphony it cuts
    at nearly every note (documented limitation).  Group end = latest end of its member notes."""
    rows = _normalize_rows(notes_by_row)
    triggers = {r: sorted({t for n in row for t in (n.start, n.end)}) for r, row in rows.items()}
    window = Fraction(window_ms)
    groups_by_row: Dict[str, List[DiscoveredGroup]] = {}
    for row_id, row in rows.items():
        if not row:
            continue
        external = sorted({t for r, ts in triggers.items() if r != row_id for t in ts})
        groups: List[DiscoveredGroup] = []
        current: List[Tuple[int, NormalizedNote]] = [(0, row[0])]
        for i in range(len(row) - 1):
            a, b = row[i], row[i + 1]
            if any((a.start < t <= b.start) or abs(t - a.end) <= window for t in external):
                groups.append(_member_group(row_id, f"{row_id}_handoff_{len(groups) + 1}", current, "Sifter_D_CrossRow", u_ms))
                current = [(i + 1, b)]
            else:
                current.append((i + 1, b))
        groups.append(_member_group(row_id, f"{row_id}_handoff_{len(groups) + 1}", current, "Sifter_D_CrossRow", u_ms))
        groups_by_row[row_id] = groups
    return _finish("Sifter D: Cross-Row Hand-off Sifter", "boundary_candidate", groups_by_row, notes_by_row, u_ms)


# ---------------------------------------------------------------------------
# Controls: Fixed-Width Slicing & Random Baseline
# ---------------------------------------------------------------------------

def control_fixed_width(
    notes_by_row: Dict[str, Sequence[Any]],
    width_ms: float = 400.0,
    u_ms: Optional[float] = None,
) -> GroupingResult:
    """Control 1: fixed-width periodic slicing from each row's start."""
    rows = _normalize_rows(notes_by_row)
    groups_by_row: Dict[str, List[DiscoveredGroup]] = {}
    for row_id, row in rows.items():
        if not row:
            continue
        row_start = row[0].start_ms
        row_end = max(n.end_ms for n in row)
        chunks = max(1, int(math.ceil((row_end - row_start) / width_ms)))
        groups_by_row[row_id] = [
            _slice_group(row_id, f"{row_id}_fix_{k + 1}", row, row_start + k * width_ms,
                         min(row_start + (k + 1) * width_ms, row_end), f"Control_1_FixedWidth_{int(width_ms)}ms", u_ms)
            for k in range(chunks)]
    return _finish(f"Control 1: Fixed-Width ({int(width_ms)}ms)", "fixed_width_control", groups_by_row, notes_by_row, u_ms)


def generate_random_internal_boundaries(
    span_start: float,
    span_end: float,
    count: int,
    seed: int = 42,
) -> List[float]:
    """Generates count seeded uniform random points strictly within (span_start, span_end)."""
    if count <= 0 or span_end <= span_start:
        return []
    rng = random.Random(seed)
    dur = span_end - span_start
    return sorted(span_start + rng.random() * dur for _ in range(count))


def control_random_grouping(
    notes_by_row: Dict[str, Sequence[Any]],
    target_boundary_count: int,
    seed: int = 42,
    u_ms: Optional[float] = None,
) -> GroupingResult:
    """Control 2: seeded random boundaries over the passage span (passage start and end included)."""
    rows = _normalize_rows(notes_by_row)
    all_notes = [n for row in rows.values() for n in row]
    if not all_notes:
        return GroupingResult(f"Control 2: Random (seed={seed})", {}, [], diagnose_passage_timing(notes_by_row, u_ms),
                              [], {}, "random_control")
    p_start = min(n.start_ms for n in all_notes)
    p_end = max(n.end_ms for n in all_notes)
    p_duration = max(1.0, p_end - p_start)
    rng = random.Random(seed)
    bounds = [p_start] + [p_start + rng.random() * p_duration for _ in range(max(0, target_boundary_count - 2))] + [p_end]
    bounds = sorted(set(bounds))
    groups_by_row = {
        row_id: [_slice_group(row_id, f"{row_id}_rnd_{k + 1}", row, bounds[k], bounds[k + 1], f"Control_2_Random_{seed}", u_ms)
                 for k in range(len(bounds) - 1)]
        for row_id, row in rows.items() if row}
    return _finish(f"Control 2: Random (seed={seed})", "random_control", groups_by_row, notes_by_row, u_ms,
                   extra_boundaries=bounds)


def evaluate_monte_carlo_random_baseline(
    notes_by_row: Dict[str, Sequence[Any]],
    target_boundary_count: int,
    reference_boundaries_ms: Sequence[float],
    num_seeds: int = 100,
    tolerance_ms: float = 60.0,
    passage_span_ms: Optional[Tuple[float, float]] = None,
    internal_only: bool = True,
    u_ms: Optional[float] = None,
) -> Tuple[float, float, float, float, float, float]:
    """Seeded Monte Carlo random baseline matched to a boundary count.

    Returns (mean_prec, std_prec, mean_rec, std_rec, mean_f1, std_f1), population standard deviations
    over seeds 0..num_seeds-1.  internal_only=True REQUIRES passage_span_ms (no silent default span).
    A higher mean than this baseline is not by itself a statistical-significance claim.
    """
    if internal_only and passage_span_ms is None:
        raise ValueError("internal_only=True requires passage_span_ms (no default span is assumed)")
    precisions, recalls, f1s = [], [], []
    for seed in range(num_seeds):
        if internal_only:
            p_start, p_end = passage_span_ms
            pts = generate_random_internal_boundaries(p_start, p_end, target_boundary_count, seed=seed)
            m = evaluate_boundaries(pts, reference_boundaries_ms, tolerance_ms=tolerance_ms,
                                    passage_span_ms=passage_span_ms, internal_only=True)
        else:
            res = control_random_grouping(notes_by_row, target_boundary_count=target_boundary_count, seed=seed, u_ms=u_ms)
            m = evaluate_boundaries(res.discovered_boundaries_ms, reference_boundaries_ms, tolerance_ms=tolerance_ms,
                                    passage_span_ms=passage_span_ms, internal_only=False)
        precisions.append(m.precision); recalls.append(m.recall); f1s.append(m.f1_score)

    def mean_std(xs):
        mu = sum(xs) / len(xs)
        return mu, math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))

    mp, sp = mean_std(precisions); mr, sr = mean_std(recalls); mf, sf = mean_std(f1s)
    return mp, sp, mr, sr, mf, sf


# ---------------------------------------------------------------------------
# Maximum-Cardinality Bipartite Matching Algorithm
# ---------------------------------------------------------------------------

def max_bipartite_matching(
    reference: Sequence[float],
    discovered: Sequence[float],
    tolerance_ms: float,
) -> Set[Tuple[int, int]]:
    """Maximum-cardinality one-to-one matching of reference and discovered boundaries within tolerance
    (Kuhn's augmenting-path algorithm; candidate edges tried nearest-first)."""
    adj: List[List[int]] = []
    for r in reference:
        neighbors = sorted((abs(d - r), d_idx) for d_idx, d in enumerate(discovered) if abs(d - r) <= tolerance_ms)
        adj.append([d_idx for _, d_idx in neighbors])
    match_d = [-1] * len(discovered)

    def dfs(r_idx: int, visited: Set[int]) -> bool:
        for d_idx in adj[r_idx]:
            if d_idx not in visited:
                visited.add(d_idx)
                if match_d[d_idx] == -1 or dfs(match_d[d_idx], visited):
                    match_d[d_idx] = r_idx
                    return True
        return False

    for r_idx in range(len(reference)):
        dfs(r_idx, set())
    return {(r_idx, d_idx) for d_idx, r_idx in enumerate(match_d) if r_idx != -1}


# ---------------------------------------------------------------------------
# Reference Boundary Evaluation
# ---------------------------------------------------------------------------

def evaluate_boundaries(
    discovered_boundaries_ms: Sequence[float],
    reference_boundaries_ms: Sequence[float],
    tolerance_ms: float = 50.0,
    passage_span_ms: Optional[Tuple[float, float]] = None,
    internal_only: bool = False,
) -> EvaluationMetrics:
    """Precision/recall/F1 of discovered against reference boundaries under maximum one-to-one matching.

    internal_only with passage_span_ms drops points within tolerance_ms of the span ends.  Empty
    reference: precision/recall/F1 are 1.0 if nothing was discovered (vacuous=True) and 0.0 otherwise;
    empty_reference=True in both cases.  'specificity' is the legacy 'no false positives' indicator.
    """
    raw_discovered = sorted(set(discovered_boundaries_ms))
    raw_reference = sorted(set(reference_boundaries_ms))
    if internal_only and passage_span_ms is not None:
        p_start, p_end = passage_span_ms
        keep = lambda b: abs(b - p_start) > tolerance_ms and abs(b - p_end) > tolerance_ms  # noqa: E731
        discovered = [b for b in raw_discovered if keep(b)]
        reference = [b for b in raw_reference if keep(b)]
    else:
        discovered, reference = raw_discovered, raw_reference

    if not reference:
        vac = not discovered
        return EvaluationMetrics(
            precision=1.0 if vac else 0.0, recall=1.0 if vac else 0.0, f1_score=1.0 if vac else 0.0,
            true_positives=0, false_positives=len(discovered), false_negatives=0, tolerance_ms=tolerance_ms,
            discovered_count=len(discovered), reference_count=0, is_internal_only=internal_only,
            specificity=1.0 if vac else 0.0, zero_false_positives=vac, empty_reference=True, vacuous=vac)

    tp = len(max_bipartite_matching(reference, discovered, tolerance_ms))
    fp = len(discovered) - tp
    fn = len(reference) - tp
    precision = tp / len(discovered) if discovered else 0.0
    recall = tp / len(reference)
    f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return EvaluationMetrics(
        precision=precision, recall=recall, f1_score=f1, true_positives=tp, false_positives=fp,
        false_negatives=fn, tolerance_ms=tolerance_ms, discovered_count=len(discovered),
        reference_count=len(reference), is_internal_only=internal_only,
        specificity=1.0 if fp == 0 else 0.0, zero_false_positives=(fp == 0), empty_reference=False, vacuous=False)


# ---------------------------------------------------------------------------
# Stage 2b: recurrence discovery (implemented in music_model/recurrence_discovery.py)
# ---------------------------------------------------------------------------

def discover_sound_groups(notes_by_row: Dict[str, Sequence[Any]], config: Any = None, **overrides: Any):
    """Configurable discovery of RECURRING sound groups (JOB-04 Stage 2b).

    Delegates to music_model.recurrence_discovery.discover_sound_groups; see that module and
    JOB_04_STAGE2B_SPECIFICATION.md.  It does not use the boundary sifters or the legacy Row 1 derivation.
    """
    from music_model.recurrence_discovery import discover_sound_groups as _discover
    return _discover(notes_by_row, config, **overrides)


# ---------------------------------------------------------------------------
# LEGACY: Composite Row 1 Segments (compatibility only; not extended)
# ---------------------------------------------------------------------------

def derive_row1_from_discovered_groups(
    groups_by_row: Dict[str, List[DiscoveredGroup]],
    u_ms: Optional[float] = None,
) -> List[DiscoveredRow1Segment]:
    """LEGACY compatibility: composite segments from the union of discovered group boundaries.

    Row 1 construction belongs to later jobs; this function is retained unchanged in intent and is not
    used by recurrence discovery.  Underlying groups and events are not modified.  mean_pitch uses
    pitched notes only (NaN when a segment has none).
    """
    bounds = sorted({b for groups in groups_by_row.values() for g in groups for b in (g.start_ms, g.end_ms)})
    if len(bounds) < 2:
        return []
    segments: List[DiscoveredRow1Segment] = []
    for s_ms, e_ms in zip(bounds, bounds[1:]):
        dur_ms = e_ms - s_ms
        active_g: List[str] = []
        active_r: Set[str] = set()
        pitches: List[float] = []
        for row_id, groups in groups_by_row.items():
            for g in groups:
                if not (e_ms <= g.start_ms or s_ms >= g.end_ms):
                    active_g.append(g.group_id)
                    active_r.add(row_id)
                    for n in g.notes:
                        p = normalize_note(n, row_id, 0).pitch
                        if p is not None:
                            pitches.append(p)
        mean_p = sum(pitches) / len(pitches) if pitches else math.nan
        if u_ms is not None and u_ms > 0:
            width = dur_ms / u_ms
            s_u, e_u, is_sub = s_ms / u_ms, e_ms / u_ms, width < 1.0
            formatted = f"{int(round(width))}u" if abs(width - round(width)) < 1e-4 else f"{width:.2f}u"
        else:
            width, s_u, e_u, is_sub, formatted = None, None, None, False, ""
        segments.append(DiscoveredRow1Segment(
            start_ms=s_ms, end_ms=e_ms, duration_ms=dur_ms, active_row_count=len(active_r),
            active_group_count=len(active_g), mean_pitch=mean_p, active_groups=tuple(active_g),
            start_unit=s_u, end_unit=e_u, width_units=width, is_sub_unit=is_sub, formatted_units=formatted))
    return segments
