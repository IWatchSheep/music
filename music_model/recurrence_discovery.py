"""recurrence_discovery.py - JOB-04 Stage 2b: discovery of RECURRING sound groups (candidate methods).

Entry point: discover_sound_groups(notes_by_row, config) -> DiscoveryResult  (also exposed by
music_model.group_discovery).  Specification: JOB_04_STAGE2B_SPECIFICATION.md.

Summary of the mathematics
--------------------------
Notes are normalized by group_discovery.normalize_note (exact Fraction milliseconds, timing provenance,
exact pitch key, event identity).  They are partitioned into STREAMS = (row id, explicit voice id or
None) and ordered chronologically by (start, end, event id, input index).  A stream is MONOPHONIC when
no note starts before every earlier note has ended; only monophonic streams are searched (no melodic
order is invented for polyphony; polyphonic streams are reported, with their events excluded).

A window W = (s, i, n) is the n consecutive notes at chronological positions i .. i+n-1 of stream s
(half-open index range [i, i+n)).  Derived features of W (exact rationals):
  pitches   P = (p_i, ..., p_{i+n-1})                  (exact pitch keys)
  durations D = (e_k - o_k)                            (o = onset, e = end)
  IOIs      Q = (o_{k+1} - o_k), k = i .. i+n-2       (relative onsets are partial sums of Q)
  intervals I = (p_{k+1} - p_k)
  contour   C = (sign(I_k)) in {-1, 0, +1}
Methods compare windows of equal n by an exact signature (no tolerance, no rounding):
  exact                : (P, D, Q)          - same absolute pitches and rhythm; any time displacement
  transposition        : (I, D, Q)          - strict: intervals and rhythm; displacement p_i(occ) - p_i(ref)
  interval_only        : (I)                - optional, weaker: intervals regardless of rhythm
  rhythm               : (D, Q)             - exact rhythm, independent of pitch (unpitched notes allowed)
  rhythm_proportional  : (D/d0, Q/d0)       - optional: rhythm up to an exact scale factor d0(occ)/d0(ref)
  contour              : (C)                - direction only (including repeated pitches); WEAK relation
Pitch-based methods are applied to maximal runs of pitched notes (an unpitched note breaks the run).

A FAMILY is one signature of one method and length n with at least min_occurrences INDEPENDENT
occurrences (the maximum number of pairwise non-overlapping occurrences, computed per stream by the
greedy earliest-end rule, which is optimal for equal-length intervals).  All occurrences, including
overlapping ones, are listed and overlaps are flagged.  A family is NESTED (not maximal) when another
family of the same method with length n+1 has the same number of occurrences and contains each of its
occurrences (one note longer on the left or right); nested families are kept and linked to their parents.
Families whose occurrence set equals that of a stricter method's family of the same length are flagged
'same_occurrences_as' (e.g. a rhythm family that is also an exact family).

Identity: a family is identified by its method, length and canonical feature sequence (family_key, a
readable text form), never by a hash or by discovery order.  Output order is deterministic.
Search limits: config.max_windows bounds the windows examined per method; if reached, the search stops
at a whole window length, search_complete=False and the covered lengths are reported (never silent).
No Row 1, column, row-assignment or graph computation is performed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

from music_model.group_discovery import NormalizedNote, normalize_note

METHOD_ORDER = ("exact", "transposition", "interval_only", "rhythm", "rhythm_proportional", "contour")
DEFAULT_METHODS = ("exact", "transposition", "rhythm", "contour")
PITCH_METHODS = {"exact", "transposition", "interval_only", "contour"}
# Methods whose relation is strictly stronger (same windows match under them => also match here).
STRICTER = {
    "exact": (),
    "transposition": ("exact",),
    "interval_only": ("exact", "transposition"),
    "rhythm": ("exact", "transposition"),
    "rhythm_proportional": ("exact", "transposition", "rhythm"),
    "contour": ("exact", "transposition", "interval_only"),
}
INTERPRETATION = {
    "exact": "Same absolute pitches, durations and relative onsets (time-displaced repetition).",
    "transposition": "Same pitch intervals, durations and relative onsets; absolute pitch displaced by the "
                     "reported semitone amount (0 for occurrences identical in pitch). Distinct pitch "
                     "identities are kept per occurrence.",
    "interval_only": "Same successive pitch intervals; rhythm NOT compared (weaker than transposition).",
    "rhythm": "Same note durations and inter-onset intervals; pitch NOT compared.",
    "rhythm_proportional": "Durations and inter-onset intervals equal up to one exact scale factor; "
                           "scale 1 coincides with exact rhythm.",
    "contour": "Same sequence of pitch-change directions (up/down/repeat) only. WEAK relation: not "
               "evidence of melodic identity; short contours recur by chance.",
}


# ---------------------------------------------------------------------------
# Configuration and results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DiscoveryConfig:
    methods: Tuple[str, ...] = DEFAULT_METHODS
    min_length: int = 3                 # notes; experimental convention, configurable
    max_length: Optional[int] = None    # notes; None = up to the stream/run length
    min_occurrences: int = 2            # independent (non-overlapping) occurrences
    include_nested: bool = True         # nested families are always computed; False hides them from .families
    max_windows: int = 500_000          # per method; reaching it is reported (search_complete=False)
    duplicate_event_ids: str = "disambiguate"  # 'disambiguate' (suffix '#dupK', reported) | 'error' (raise)

    def validate(self) -> None:
        def is_int(x):
            return isinstance(x, int) and not isinstance(x, bool)
        if not isinstance(self.methods, (tuple, list)) or not self.methods or \
                not all(isinstance(m, str) for m in self.methods):
            raise ValueError(f"methods must be a non-empty sequence of method names, got {self.methods!r}")
        for name in ("min_length", "min_occurrences", "max_windows"):
            if not is_int(getattr(self, name)):
                raise ValueError(f"{name} must be an int, got {getattr(self, name)!r}")
        if self.max_length is not None and not is_int(self.max_length):
            raise ValueError(f"max_length must be an int or None, got {self.max_length!r}")
        if not isinstance(self.include_nested, bool):
            raise ValueError(f"include_nested must be a bool, got {self.include_nested!r}")
        if self.duplicate_event_ids not in ("error", "disambiguate"):
            raise ValueError(f"duplicate_event_ids must be 'error' or 'disambiguate', got {self.duplicate_event_ids!r}")
        unknown = [m for m in self.methods if m not in METHOD_ORDER]
        if unknown:
            raise ValueError(f"unknown method(s) {unknown}; choose from {METHOD_ORDER}")
        if self.min_length < 2:
            raise ValueError("min_length must be >= 2")
        if self.max_length is not None and self.max_length < self.min_length:
            raise ValueError("max_length must be >= min_length")
        if self.min_occurrences < 2:
            raise ValueError("min_occurrences must be >= 2")
        if self.max_windows < 1:
            raise ValueError("max_windows must be >= 1")


@dataclass(frozen=True)
class StreamReport:
    row_id: str
    voice_id: Optional[str]
    note_count: int
    status: str                 # 'monophonic' | 'polyphonic_unsupported'
    unpitched_count: int
    event_ids: Tuple[str, ...]  # chronological order (index convention for occurrences)


@dataclass(frozen=True)
class Exclusion:
    event_id: str
    row_id: str
    voice_id: Optional[str]
    method: str
    reason: str


@dataclass(frozen=True)
class EventRef:
    """Public reference to one original event inside an occurrence (lookup contract, specification §7).

    'source' is the original object passed in; 'input_index' is its position in the input row list.
    Both are excluded from equality: they depend on how the caller built the input, not on the music.
    """
    event_id: str                    # the reported key: supplied id, generated id, or disambiguated id
    supplied_event_id: Optional[str]
    event_id_generated: bool
    row_id: str
    voice_id: Optional[str]
    chronological_index: int         # position in the stream's chronological order
    exact_start_ms: Fraction
    exact_end_ms: Fraction
    timing_source: str
    pitch: Any                       # stored value as supplied (int, Fraction, float) or None
    pitch_exact: Optional[Fraction]
    pitch_kind: str
    pitch_source: str
    pitch_estimated: bool
    label: str
    input_index: int = field(default=-1, compare=False)
    source: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class Occurrence:
    row_id: str
    voice_id: Optional[str]
    start_index: int            # half-open [start_index, end_index) in the stream's chronological order
    end_index: int
    event_ids: Tuple[str, ...]
    exact_start_ms: Fraction
    exact_end_ms: Fraction
    timing_sources: Tuple[str, ...]
    pitches: Tuple[Optional[Fraction], ...]     # exact pitch keys of this occurrence (identities kept)
    transposition_semitones: Optional[Fraction] = None   # relative to the family reference occurrence
    scale_factor: Optional[Fraction] = None              # rhythm_proportional, relative to the reference
    overlaps_with: Tuple[int, ...] = ()                  # positions of overlapping occurrences in the family
    events: Tuple[EventRef, ...] = ()                    # one reference per note, in chronological order

    @property
    def start_ms(self) -> float:
        return float(self.exact_start_ms)

    @property
    def end_ms(self) -> float:
        return float(self.exact_end_ms)


@dataclass(frozen=True)
class RecurrenceFamily:
    family_key: str
    method: str
    length: int
    features: Tuple[Tuple[str, Tuple[str, ...]], ...]      # named canonical feature sequences
    occurrences: Tuple[Occurrence, ...]
    independent_occurrence_count: int
    is_maximal: bool
    nested_in: Tuple[str, ...]
    same_occurrences_as: Tuple[str, ...]
    parameters: Tuple[Tuple[str, str], ...]
    interpretation: str
    limitations: Tuple[str, ...]


@dataclass(frozen=True)
class RejectedCandidate:
    family_key: str
    method: str
    length: int
    raw_occurrences: int
    independent_occurrences: int
    reason: str


@dataclass(frozen=True)
class DiscoveryResult:
    config: DiscoveryConfig
    families: Tuple[RecurrenceFamily, ...]
    all_families: Tuple[RecurrenceFamily, ...]        # including nested, regardless of include_nested
    streams: Tuple[StreamReport, ...]
    exclusions: Tuple[Exclusion, ...]
    rejected_candidates: Tuple[RejectedCandidate, ...]
    search_complete: bool
    search_notes: Tuple[str, ...]
    windows_examined: Tuple[Tuple[str, int], ...]
    # search_complete: every window within the CONFIGURED bounds (min_length..max_length) was examined.
    # unrestricted_search_complete: additionally, no searchable window was excluded by max_length.
    unrestricted_search_complete: bool = False
    # per method: (method, min_length, max_length_searched, longest_searchable_run, status)
    search_scope: Tuple[Tuple[Any, ...], ...] = ()

    def families_by_method(self, method: str, maximal_only: bool = False) -> List[RecurrenceFamily]:
        return [f for f in self.all_families if f.method == method and (f.is_maximal or not maximal_only)]


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

@dataclass
class _Stream:
    row_id: str
    voice_id: Optional[str]
    notes: List[NormalizedNote]
    monophonic: bool
    ids: List[str] = field(default_factory=list)          # reported event key per chronological position
    generated: List[bool] = field(default_factory=list)   # True when the key was generated (no supplied id)

    @property
    def key(self) -> Tuple[str, int, str]:
        # Unspecified voice (None) and every named voice have distinct keys; names are never '' (normalized).
        return (self.row_id, 0, "") if self.voice_id is None else (self.row_id, 1, self.voice_id)


def _chrono_key(x: NormalizedNote):
    """Chronological order independent of input order (input position only separates identical notes)."""
    pitch = (0, Fraction(0)) if x.pitch_exact is None else (1, x.pitch_exact)
    return (x.start, x.end, pitch, x.supplied_event_id or "", x.input_index)


def _build_streams(notes_by_row: Dict[str, Sequence[Any]], duplicate_policy: str = "disambiguate"
                   ) -> Tuple[List[_Stream], List[str]]:
    streams: Dict[Tuple[str, Optional[str]], List[NormalizedNote]] = {}
    for row_id, notes in notes_by_row.items():
        for i, n in enumerate(notes or []):
            nn = normalize_note(n, row_id, i)
            streams.setdefault((row_id, nn.voice_id), []).append(nn)
    out: List[_Stream] = []
    for (row_id, voice), nn in streams.items():
        nn.sort(key=_chrono_key)
        mono, run_end = True, None
        for x in nn:
            if run_end is not None and x.start < run_end:
                mono = False
                break
            run_end = x.end if run_end is None else max(run_end, x.end)
        ids = [x.supplied_event_id or f"anon|row={row_id!r}|voice={voice!r}|{k}" for k, x in enumerate(nn)]
        out.append(_Stream(row_id, voice, nn, mono, ids, [x.supplied_event_id is None for x in nn]))
    out.sort(key=lambda s: s.key)

    # Duplicate keys (supplied ids reused, or a supplied id equal to a generated one).
    seen: Dict[str, int] = {}
    for s in out:
        for k in s.ids:
            seen[k] = seen.get(k, 0) + 1
    dups = sorted(k for k, c in seen.items() if c > 1)
    notes: List[str] = []
    if dups:
        if duplicate_policy == "error":
            raise ValueError(f"duplicate event ids in input: {dups[:10]}{' ...' if len(dups) > 10 else ''} "
                             f"(use duplicate_event_ids='disambiguate' to suffix them deterministically)")
        # Reserve EVERY existing key (unique keys are kept; duplicated keys are retired) and every newly
        # assigned key, then give each duplicate the smallest free '#dupK' (K >= 1), visiting duplicates
        # in (row, voice, chronological) order.  This cannot collide with a supplied, generated or
        # previously assigned key.
        reserved = set(seen)
        dup_set = set(dups)
        for s in out:
            for k, eid in enumerate(s.ids):
                if eid in dup_set:
                    j = 1
                    while f"{eid}#dup{j}" in reserved:
                        j += 1
                    s.ids[k] = f"{eid}#dup{j}"
                    reserved.add(s.ids[k])
        notes.append(f"duplicate event id(s) {dups[:10]} disambiguated as '<id>#dupK' (smallest K not already "
                     f"used by any supplied, generated or assigned id) in (row, voice, chronological) order; "
                     f"supplied ids kept in EventRef.supplied_event_id")
    final = [k for s in out for k in s.ids]
    if len(final) != len(set(final)):                  # defensive: the contract is global uniqueness
        raise RuntimeError("internal error: reported event ids are not unique after disambiguation")
    return out, notes


# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------

def _sign(x: Fraction) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _signature(method: str, w: Sequence[NormalizedNote]) -> Tuple[Tuple[str, Tuple[Any, ...]], ...]:
    d = tuple(n.end - n.start for n in w)
    q = tuple(w[k + 1].start - w[k].start for k in range(len(w) - 1))
    if method == "rhythm":
        return (("durations_ms", d), ("ioi_ms", q))
    if method == "rhythm_proportional":
        s = d[0]
        return (("durations_over_first", tuple(x / s for x in d)), ("ioi_over_first_duration", tuple(x / s for x in q)))
    p = tuple(n.pitch_exact for n in w)
    iv = tuple(p[k + 1] - p[k] for k in range(len(p) - 1))
    if method == "exact":
        return (("pitches", p), ("durations_ms", d), ("ioi_ms", q))
    if method == "transposition":
        return (("intervals", iv), ("durations_ms", d), ("ioi_ms", q))
    if method == "interval_only":
        return (("intervals", iv),)
    if method == "contour":
        return (("contour", tuple(_sign(x) for x in iv)),)
    raise ValueError(method)


def _fmt(v: Any) -> str:
    if isinstance(v, Fraction):
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return str(v)


def _canonical(method: str, n: int, sig) -> Tuple[str, Tuple[Tuple[str, Tuple[str, ...]], ...]]:
    feats = tuple((name, tuple(_fmt(x) for x in vals)) for name, vals in sig)
    key = f"{method}|n={n}|" + "|".join(f"{name}=({','.join(vals)})" for name, vals in feats)
    return key, feats


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _segments(stream: _Stream, method: str) -> List[Tuple[int, int]]:
    """Maximal index ranges [a, b) searched by a method (pitch methods break at unpitched notes)."""
    if method not in PITCH_METHODS:
        return [(0, len(stream.notes))] if stream.notes else []
    segs, a = [], None
    for i, n in enumerate(stream.notes):
        if n.pitch_exact is None:
            if a is not None:
                segs.append((a, i)); a = None
        elif a is None:
            a = i
    if a is not None:
        segs.append((a, len(stream.notes)))
    return segs


def _independent_count(windows: Sequence[Tuple[_Stream, int]], n: int) -> int:
    by_stream: Dict[Tuple[str, str], List[int]] = {}
    for s, i in windows:
        by_stream.setdefault(s.key, []).append(i)
    total = 0
    for starts in by_stream.values():
        last_end = None
        for i in sorted(starts):                      # equal lengths: earliest start = earliest end
            if last_end is None or i >= last_end:
                total += 1
                last_end = i + n
    return total


def _event_ref(s: _Stream, k: int) -> EventRef:
    x = s.notes[k]
    return EventRef(event_id=s.ids[k], supplied_event_id=x.supplied_event_id, event_id_generated=s.generated[k],
                    row_id=s.row_id, voice_id=s.voice_id, chronological_index=k, exact_start_ms=x.start,
                    exact_end_ms=x.end, timing_source=x.timing_source, pitch=x.pitch, pitch_exact=x.pitch_exact,
                    pitch_kind=x.pitch_kind, pitch_source=x.pitch_source, pitch_estimated=x.pitch_estimated,
                    label=x.label, input_index=x.input_index, source=x.source)


def _occurrence(s: _Stream, i: int, n: int) -> Occurrence:
    w = s.notes[i:i + n]
    return Occurrence(
        row_id=s.row_id, voice_id=s.voice_id, start_index=i, end_index=i + n,
        event_ids=tuple(s.ids[i:i + n]), exact_start_ms=w[0].start, exact_end_ms=max(x.end for x in w),
        timing_sources=tuple(sorted({x.timing_source for x in w})), pitches=tuple(x.pitch_exact for x in w),
        events=tuple(_event_ref(s, k) for k in range(i, i + n)))


def discover_sound_groups(notes_by_row: Dict[str, Sequence[Any]],
                          config: Optional[DiscoveryConfig] = None, **overrides: Any) -> DiscoveryResult:
    """Discover recurring sound groups (see module docstring and JOB_04_STAGE2B_SPECIFICATION.md).

    config: DiscoveryConfig; keyword overrides (e.g. methods=("exact",), min_length=4) are applied on top.
    Raises group_discovery.NoteTimingError for inputs violating the Stage 2a/2b input contract.
    """
    cfg = config or DiscoveryConfig()
    if overrides:
        cfg = DiscoveryConfig(**{**cfg.__dict__, **overrides})
    if isinstance(cfg.methods, str):
        cfg = DiscoveryConfig(**{**cfg.__dict__, "methods": (cfg.methods,)})
    cfg.validate()
    methods = tuple(m for m in METHOD_ORDER if m in cfg.methods)

    streams, id_notes = _build_streams(notes_by_row, cfg.duplicate_event_ids)
    reports = tuple(StreamReport(s.row_id, s.voice_id, len(s.notes),
                                 "monophonic" if s.monophonic else "polyphonic_unsupported",
                                 sum(1 for x in s.notes if x.pitch_exact is None),
                                 tuple(s.ids)) for s in streams)
    exclusions: List[Exclusion] = []
    for s in streams:
        for k, x in enumerate(s.notes):
            for m in methods:
                if not s.monophonic:
                    exclusions.append(Exclusion(s.ids[k], s.row_id, s.voice_id, m,
                                                "polyphonic stream: no melodic order is invented"))
                elif m in PITCH_METHODS and x.pitch_exact is None:
                    exclusions.append(Exclusion(s.ids[k], s.row_id, s.voice_id, m,
                                                "unpitched event: breaks pitched sequences for this method"))

    searchable = [s for s in streams if s.monophonic and s.notes]
    families_raw: List[Tuple[str, int, Any, List[Tuple[_Stream, int]]]] = []
    rejected: List[RejectedCandidate] = []
    notes: List[str] = list(id_notes)
    examined: List[Tuple[str, int]] = []
    scope: List[Tuple[Any, ...]] = []
    complete = True

    for m in methods:
        segs = [(s, a, b) for s in searchable for a, b in _segments(s, m)]
        longest = max((b - a for _, a, b in segs), default=0)
        top = longest if cfg.max_length is None else min(longest, cfg.max_length)
        count = 0
        searched_to, status = top, ("complete" if top >= longest else "bounded_by_max_length")
        for n in range(cfg.min_length, top + 1):
            n_windows = sum(max(0, b - a - n + 1) for _, a, b in segs)
            if count + n_windows > cfg.max_windows:
                complete = False
                searched_to, status = n - 1, "stopped_by_max_windows"
                notes.append(f"{m}: window limit {cfg.max_windows} reached; searched lengths "
                             f"{cfg.min_length}..{n - 1} of {cfg.min_length}..{top} (lengths >= {n} NOT searched)")
                break
            count += n_windows
            table: Dict[Any, List[Tuple[_Stream, int]]] = {}
            for s, a, b in segs:
                for i in range(a, b - n + 1):
                    table.setdefault(_signature(m, s.notes[i:i + n]), []).append((s, i))
            for sig, wins in table.items():
                if len(wins) < 2:
                    continue
                ind = _independent_count(wins, n)
                if ind < cfg.min_occurrences:
                    key, _ = _canonical(m, n, sig)
                    rejected.append(RejectedCandidate(key, m, n, len(wins), ind,
                                                      f"only {ind} non-overlapping occurrence(s) "
                                                      f"(< min_occurrences={cfg.min_occurrences})"))
                    continue
                families_raw.append((m, n, sig, sorted(wins, key=lambda w: (w[0].key, w[1]))))
        examined.append((m, count))
        scope.append((m, cfg.min_length, max(cfg.min_length - 1, searched_to), longest, status))

    # Build families, nesting and stricter-method equivalence.
    occ_sets: Dict[Tuple[str, int], Dict[frozenset, str]] = {}
    by_window: Dict[Tuple[str, int, Tuple[str, str], int], str] = {}
    keyed = []
    for m, n, sig, wins in families_raw:
        key, feats = _canonical(m, n, sig)
        oset = frozenset((s.key, i) for s, i in wins)
        occ_sets.setdefault((m, n), {})[oset] = key
        for s, i in wins:
            by_window[(m, n, s.key, i)] = key
        keyed.append((m, n, sig, wins, key, feats, oset))
    sizes = {key: len(oset) for *_, key, _f, oset in keyed}

    families: List[RecurrenceFamily] = []
    for m, n, sig, wins, key, feats, oset in keyed:
        parents = set()
        s0, i0 = wins[0]
        for cand_start in (i0, i0 - 1):
            pkey = by_window.get((m, n + 1, s0.key, cand_start))
            if pkey is None or sizes[pkey] != len(wins):
                continue
            if all(by_window.get((m, n + 1, s.key, i)) == pkey or by_window.get((m, n + 1, s.key, i - 1)) == pkey
                   for s, i in wins):
                parents.add(pkey)
        same_as = tuple(sm for sm in STRICTER[m] if oset in occ_sets.get((sm, n), {}))
        ref_s, ref_i = wins[0]
        ref = ref_s.notes[ref_i:ref_i + n]
        occs = []
        for s, i in wins:
            o = _occurrence(s, i, n)
            if m == "transposition":
                o = Occurrence(**{**o.__dict__, "transposition_semitones": s.notes[i].pitch_exact - ref[0].pitch_exact})
            if m == "rhythm_proportional":
                o = Occurrence(**{**o.__dict__, "scale_factor":
                                  (s.notes[i].end - s.notes[i].start) / (ref[0].end - ref[0].start)})
            occs.append(o)
        overl = []
        for a, oa in enumerate(occs):
            overl.append(tuple(b for b, ob in enumerate(occs) if b != a and ob.row_id == oa.row_id
                               and ob.voice_id == oa.voice_id and ob.start_index < oa.end_index
                               and oa.start_index < ob.end_index))
        occs = [Occurrence(**{**o.__dict__, "overlaps_with": ov}) for o, ov in zip(occs, overl)]
        params: List[Tuple[str, str]] = [("min_length", str(cfg.min_length)), ("min_occurrences", str(cfg.min_occurrences))]
        if m == "transposition":
            params.append(("displacements_semitones", ",".join(sorted({_fmt(o.transposition_semitones) for o in occs}, key=lambda t: Fraction(t)))))
        if m == "rhythm_proportional":
            params.append(("scale_factors", ",".join(sorted({_fmt(o.scale_factor) for o in occs}, key=lambda t: Fraction(t)))))
        lim = []
        if any(o.overlaps_with for o in occs):
            lim.append("some occurrences overlap; independent_occurrence_count counts only non-overlapping ones")
        if m == "contour":
            lim.append("contour similarity is weak evidence; it does not establish melodic identity")
        if any(x.pitch_estimated for s, i in wins for x in s.notes[i:i + n]) and m in PITCH_METHODS:
            lim.append("includes acoustically estimated pitches")
        families.append(RecurrenceFamily(
            family_key=key, method=m, length=n, features=feats, occurrences=tuple(occs),
            independent_occurrence_count=_independent_count(wins, n), is_maximal=not parents,
            nested_in=tuple(sorted(parents)), same_occurrences_as=same_as, parameters=tuple(params),
            interpretation=INTERPRETATION[m], limitations=tuple(lim)))

    families.sort(key=lambda f: (METHOD_ORDER.index(f.method), -f.length, f.family_key))
    rejected.sort(key=lambda r: (METHOD_ORDER.index(r.method), -r.length, r.family_key))
    shown = tuple(f for f in families if cfg.include_nested or f.is_maximal)
    if not cfg.include_nested:
        notes.append(f"{sum(1 for f in families if not f.is_maximal)} nested families hidden (include_nested=False); "
                     f"see all_families")
    unrestricted = complete and all(st == "complete" for *_, st in scope)
    return DiscoveryResult(cfg, shown, tuple(families), reports, tuple(exclusions), tuple(rejected),
                           complete, tuple(notes), tuple(examined), unrestricted, tuple(scope))
