"""MusicXML ingestion adapter for the music project (JOB-02).

Provides prototype ingestion of standard MusicXML <score-partwise> documents into
the project's non-destructive SoundEvent model.

Features & Invariants:
- Two-Pass Score Ingestion Architecture (DEFECT-10 & DEFECT-11):
  * Pass 1: Parse all measures and voices across parts into exact fractional quarter-note
    coordinates (Fraction), collecting score-position tempo directives and verifying
    conforming notation.
  * Pass 2: Reconstruct a continuous, monotonic shared ScoreTimeline across all parts,
    integrating exact piecewise-linear milliseconds and coalescing tied notes.
- Mid-measure tempo changes (<sound tempo="..."/>, <metronome>) apply at exact score beat
  positions without retrospective whole-measure distortion (DEFECT-01 & DEFECT-11).
- Multi-part score tempo sharing: parts without explicit tempo inherit the score tempo
  timeline; conflicting independent part tempos are detected and reported (DEFECT-10).
- Flexible score cursor navigation (<forward>, <backup>) across multi-voice measures
  without voice collision or measure boundary desynchronization (DEFECT-02 & DEFECT-12D).
- Trailing rests and silent intervals are tracked in measure durations, ensuring total
  score duration accurately reflects the score's end (DEFECT-03).
- Exact Fraction zero-gap continuity criterion for tied notes; any non-zero gap (including
  1ms) is rejected from coalescing, flagged as an interrupted tie, and emitted as separate
  events (DEFECT-04).
- Continuous multi-note tie chains (3+ notes with stop and start tags) coalesce cleanly
  without spurious orphaned stop warnings (DEFECT-05).
- Comprehensive notation inspection: grace notes, cue notes, glissandi, slides, ornaments,
  dynamics (including nested directions), lyrics, microtonal alterations, and repeat barlines
  are explicitly recorded in unsupported_features, forcing is_complete_faithful_representation
  to False (DEFECT-06 & DEFECT-12A/C).
- Non-positive ordinary note durations are rejected without fabricating artificial positive
  durations (DEFECT-07).
- Metronome beat unit interpretation: supports whole, half, quarter, eighth, 16th, 32nd,
  and dotted units, converting per-minute values accurately to quarter-note BPM (DEFECT-12B).
- Preserves exact rational timing coordinates in SoundEvent.attributes as serialized
  fractions.Fraction strings ('exact_start_ms_rational', 'exact_end_ms_rational',
  'exact_duration_ms_rational').
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from music_model.sound_event import (
    SoundEvent,
    get_authoritative_exact_timing,
)


class MusicXMLParseError(ValueError):
    """Raised when MusicXML parsing fails due to malformed XML or invalid structure."""
    pass


STEP_TO_SEMITONE: Dict[str, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

BEAT_UNIT_FACTORS: Dict[str, float] = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
    "64th": 0.0625,
}


class ScoreTimeline:
    """Piecewise-linear timeline mapping fractional quarter-note beats to exact milliseconds.

    Maintains a dictionary of tempo changes keyed by exact quarter-note beat Fraction.
    Rebuilds continuous integrated segments upon query, ensuring monotonic and continuous
    timestamps regardless of insertion order (DEFECT-11).
    """

    def __init__(self, initial_tempo: float = 120.0) -> None:
        init_f = float(initial_tempo)
        if not math.isfinite(init_f) or init_f <= 0.0:
            raise ValueError(f"Invalid initial tempo {initial_tempo}. Tempo must be positive and finite.")
        self._raw_tempos: Dict[Fraction, Fraction] = {
            Fraction(0, 1): Fraction(str(initial_tempo))
        }
        self._dirty: bool = True
        self._segments: List[Tuple[Fraction, Fraction, Fraction]] = []

    def set_tempo(self, q_pos: Fraction, tempo_bpm: float) -> None:
        """Register a tempo change taking effect at quarter-note beat position q_pos.

        Validates that q_pos is not before beat 0 (DEFECT-18) and tempo is positive and finite (DEFECT-17).
        """
        q_pos = Fraction(q_pos)
        if q_pos < 0:
            raise ValueError(f"Invalid tempo position {q_pos}: cannot position tempo before beat 0 (score beginning).")
        bpm_f = float(tempo_bpm)
        if not math.isfinite(bpm_f) or bpm_f <= 0.0:
            raise ValueError(f"Invalid tempo {tempo_bpm}. Tempo must be positive and finite.")
        self._raw_tempos[q_pos] = Fraction(str(tempo_bpm))
        self._dirty = True

    def _rebuild(self) -> None:
        sorted_qs = sorted(self._raw_tempos.keys())
        self._segments = []
        curr_time = Fraction(0, 1)
        for i in range(len(sorted_qs)):
            q_start = sorted_qs[i]
            tempo = self._raw_tempos[q_start]
            if i > 0:
                prev_q = sorted_qs[i - 1]
                prev_tempo = self._raw_tempos[prev_q]
                curr_time += (q_start - prev_q) * Fraction(60000, 1) / prev_tempo
            self._segments.append((q_start, tempo, curr_time))
        self._dirty = False

    def q_to_ms(self, q_pos: Fraction) -> Fraction:
        """Convert a quarter-note beat position to exact rational milliseconds."""
        if self._dirty:
            self._rebuild()
        q_pos = Fraction(q_pos)
        for i in range(len(self._segments) - 1, -1, -1):
            s_q, s_tempo, s_time = self._segments[i]
            if q_pos >= s_q:
                return s_time + (q_pos - s_q) * Fraction(60000, 1) / s_tempo
        return Fraction(0, 1)


@dataclass
class MusicXMLImportResult:
    """The result of importing a MusicXML document."""

    sound_events: List[SoundEvent]
    total_duration_ms: int
    total_duration_ms_rational: Fraction
    part_count: int
    voice_count: int
    measure_count: int
    note_count: int
    rest_count: int
    unsupported_features: List[str] = field(default_factory=list)

    @property
    def has_unsupported_features(self) -> bool:
        """True if any notation or structure was encountered that could not be fully represented."""
        return len(self.unsupported_features) > 0

    @property
    def is_complete_faithful_representation(self) -> bool:
        """True only if the imported events represent the score without omission or unsupported features."""
        return not self.has_unsupported_features


def step_octave_to_midi(step: str, octave: int, alter: int = 0) -> int:
    """Convert note step (A-G), octave (0-9), and alter (-2..2) to standard MIDI pitch."""
    step_upper = step.upper().strip()
    if step_upper not in STEP_TO_SEMITONE:
        raise ValueError(f"Invalid musical pitch step: {step!r}")
    semitones = STEP_TO_SEMITONE[step_upper]
    midi_val = (octave + 1) * 12 + semitones + alter
    if not (0 <= midi_val <= 127):
        raise ValueError(
            f"Calculated MIDI pitch {midi_val} out of valid range [0, 127] for {step}{octave} (alter={alter})"
        )
    return midi_val


@dataclass
class _RawNote:
    part_idx: int
    part_id: str
    voice: int
    voice_row_id: str
    measure_num: int
    step: str
    octave: int
    alter: int
    midi_pitch: int
    notated_type: Optional[str]
    q_start: Fraction
    q_end: Fraction
    has_tie_start: bool
    has_tie_stop: bool


def parse_musicxml(
    source: Union[str, bytes],
    default_tempo_bpm: float = 120.0,
    row_prefix: str = "row_xml",
) -> MusicXMLImportResult:
    """Parse a MusicXML score-partwise document into validated SoundEvents using a two-pass approach."""
    def_bpm = float(default_tempo_bpm)
    if not math.isfinite(def_bpm) or def_bpm <= 0.0:
        raise ValueError(f"Invalid default_tempo_bpm {default_tempo_bpm}. Tempo must be positive and finite.")

    root = _load_xml_root(source)
    _strip_namespaces(root)

    if root.tag not in ("score-partwise", "score-timewise"):
        raise MusicXMLParseError(
            f"Unsupported MusicXML root tag: <{root.tag}>. Expected <score-partwise>."
        )

    if root.tag == "score-timewise":
        raise MusicXMLParseError(
            "score-timewise layout is not currently supported; please use score-partwise."
        )

    parts = root.findall("part")
    if not parts:
        raise MusicXMLParseError("MusicXML document contains no <part> elements.")

    unsupported_features: List[str] = []
    total_notes = 0
    total_rests = 0
    active_voices: Set[str] = set()

    # UNIFIED PASS 1: Synchronized Measure-by-Measure Note Extraction & Measure Reach (DEFECT-14)
    part_measure_lists: List[Tuple[int, str, List[ET.Element]]] = []
    max_m_count = 0
    for part_idx, part in enumerate(parts, start=1):
        part_id = part.get("id", f"P{part_idx}")
        measures = part.findall("measure")
        max_m_count = max(max_m_count, len(measures))
        part_measure_lists.append((part_idx, part_id, measures))

    total_measures = max_m_count
    raw_notes: List[_RawNote] = []
    tempo_directives: List[Tuple[Fraction, float, str, int]] = []
    current_divs_map: Dict[int, int] = {p_idx: 1 for p_idx, _, _ in part_measure_lists}
    active_time_signatures: Dict[int, Optional[Fraction]] = {p_idx: None for p_idx, _, _ in part_measure_lists}

    measure_start_q = Fraction(0, 1)

    for m_idx in range(total_measures):
        part_reaches: Dict[int, Fraction] = {}
        measure_nom_time: Optional[Fraction] = None

        for part_idx, part_id, measures in part_measure_lists:
            if m_idx >= len(measures):
                continue
            measure = measures[m_idx]
            measure_num_str = measure.get("number", str(m_idx + 1))
            try:
                measure_num = int(measure_num_str)
            except ValueError:
                measure_num = m_idx + 1

            cur_div = current_divs_map[part_idx]
            measure_cursor_q = measure_start_q
            measure_max_q = measure_start_q
            chord_start_q = measure_start_q
            chord_max_end_q = measure_start_q

            # Barline repeats (DEFECT-06)
            for barline in measure.findall("barline"):
                if barline.find("repeat") is not None:
                    unsupported_features.append(
                        f"Part {part_id}, Measure {measure_num}: Repeat barline encountered (repeats not expanded)."
                    )

            for child in measure:
                tag = child.tag

                if tag == "attributes":
                    div_elem = child.find("divisions")
                    if div_elem is not None and div_elem.text:
                        try:
                            d_val = int(div_elem.text.strip())
                            if d_val > 0:
                                cur_div = d_val
                                current_divs_map[part_idx] = cur_div
                            else:
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Non-positive divisions {d_val} encountered."
                                )
                        except ValueError:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Malformed divisions {div_elem.text!r}."
                            )

                    time_elem = child.find("time")
                    if time_elem is not None:
                        beats_elem = time_elem.find("beats")
                        btype_elem = time_elem.find("beat-type")
                        if beats_elem is not None and btype_elem is not None and beats_elem.text and btype_elem.text:
                            try:
                                bts = int(beats_elem.text.strip())
                                btp = int(btype_elem.text.strip())
                                if bts > 0 and btp > 0:
                                    t_dur = Fraction(bts * 4, btp)
                                    active_time_signatures[part_idx] = t_dur
                                    measure_nom_time = t_dur
                            except ValueError:
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Malformed time signature."
                                )

                    # Check for unsupported transposition (DEFECT-15)
                    if child.find("transpose") is not None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Transposition notation (<transpose>) not currently supported (sounding pitch preserved without transposition)."
                        )

                elif tag == "direction":
                    # Check for direction offset (DEFECT-15)
                    offset_q = Fraction(0, 1)
                    offset_elem = child.find("offset")
                    if offset_elem is not None and offset_elem.text:
                        try:
                            off_val = int(offset_elem.text.strip())
                            if cur_div > 0:
                                offset_q = Fraction(off_val, cur_div)
                        except ValueError:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Malformed direction offset {offset_elem.text!r}."
                            )

                    # Check for tempo directives (<sound tempo="..."> and <metronome>) (DEFECT-17 & DEFECT-18)
                    for sound_elem in child.findall(".//sound"):
                        tempo_attr = sound_elem.get("tempo")
                        if tempo_attr is not None:
                            try:
                                t_val = float(tempo_attr.strip())
                                if not math.isfinite(t_val) or t_val <= 0.0:
                                    unsupported_features.append(
                                        f"Part {part_id}, Measure {measure_num}: Invalid non-positive or non-finite tempo attribute ({tempo_attr!r})."
                                    )
                                else:
                                    effective_q = measure_cursor_q + offset_q
                                    if effective_q < 0:
                                        unsupported_features.append(
                                            f"Part {part_id}, Measure {measure_num}: Invalid tempo directive position ({effective_q}): tempo cannot be set before the beginning of the score (beat < 0)."
                                        )
                                    else:
                                        tempo_directives.append((effective_q, t_val, part_id, measure_num))
                            except ValueError:
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Malformed non-numeric tempo attribute ({tempo_attr!r})."
                                )

                    for metro in child.findall(".//metronome"):
                        bpm_elem = metro.find("per-minute")
                        unit_elem = metro.find("beat-unit")
                        if bpm_elem is not None and bpm_elem.text:
                            try:
                                bpm_val = float(bpm_elem.text.strip())
                                if not math.isfinite(bpm_val) or bpm_val <= 0.0:
                                    unsupported_features.append(
                                        f"Part {part_id}, Measure {measure_num}: Invalid non-positive or non-finite metronome tempo ({bpm_elem.text!r})."
                                    )
                                else:
                                    factor = 1.0
                                    if unit_elem is not None and unit_elem.text:
                                        u_str = unit_elem.text.strip().lower()
                                        if u_str in BEAT_UNIT_FACTORS:
                                            factor = BEAT_UNIT_FACTORS[u_str]
                                            if metro.find("beat-unit-dot") is not None:
                                                factor *= 1.5
                                        else:
                                            unsupported_features.append(
                                                f"Part {part_id}, Measure {measure_num}: Unsupported metronome beat-unit <{u_str}>."
                                            )
                                    quarter_bpm = bpm_val * factor
                                    effective_q = measure_cursor_q + offset_q
                                    if effective_q < 0:
                                        unsupported_features.append(
                                            f"Part {part_id}, Measure {measure_num}: Invalid tempo directive position ({effective_q}): tempo cannot be set before the beginning of the score (beat < 0)."
                                        )
                                    else:
                                        tempo_directives.append((effective_q, quarter_bpm, part_id, measure_num))
                            except ValueError:
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Malformed non-numeric metronome tempo ({bpm_elem.text!r})."
                                )
                        else:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Metronome directive missing <per-minute> tempo."
                            )

                    # Check for unsupported direction types including nested dynamics (DEFECT-06 & DEFECT-12A)
                    if child.find(".//dynamics") is not None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Dynamics notation not supported."
                        )

                    for dir_child in child.iter():
                        if dir_child.tag in ("wedge", "words", "damp", "pedal", "octave-shift", "coda", "segno"):
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Unsupported direction <{dir_child.tag}> encountered."
                            )

                elif tag == "forward":
                    dur_div = 0
                    dur_elem = child.find("duration")
                    if dur_elem is not None and dur_elem.text:
                        try:
                            dur_div = int(dur_elem.text.strip())
                        except ValueError:
                            dur_div = 0
                    if dur_elem is None or dur_div <= 0:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Invalid non-positive forward duration ({dur_div})."
                        )
                    elif cur_div > 0:
                        delta_q = Fraction(dur_div, cur_div)
                        measure_cursor_q += delta_q
                        measure_max_q = max(measure_max_q, measure_cursor_q)

                elif tag == "backup":
                    dur_div = 0
                    dur_elem = child.find("duration")
                    if dur_elem is not None and dur_elem.text:
                        try:
                            dur_div = int(dur_elem.text.strip())
                        except ValueError:
                            dur_div = 0
                    if dur_elem is None or dur_div <= 0:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Invalid non-positive backup duration ({dur_div})."
                        )
                    elif cur_div > 0:
                        delta_q = Fraction(dur_div, cur_div)
                        if measure_cursor_q - delta_q < measure_start_q:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Invalid backup operation: cursor backed up before start of measure."
                            )
                            measure_cursor_q = measure_start_q
                        else:
                            measure_cursor_q -= delta_q

                elif tag == "note":
                    if child.find("grace") is not None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Grace note encountered (zero-duration embellishment skipped)."
                        )
                        continue

                    if child.find("cue") is not None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Cue note encountered."
                        )

                    if child.find("lyric") is not None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Lyric encountered (text ignored)."
                        )

                    notations_elem = child.find("notations")
                    if notations_elem is not None:
                        for not_child in notations_elem:
                            if not_child.tag not in ("tied", "tie"):
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Unsupported notation <{not_child.tag}> encountered."
                                )

                    voice = 1
                    voice_elem = child.find("voice")
                    if voice_elem is not None and voice_elem.text:
                        try:
                            voice = int(voice_elem.text.strip())
                        except ValueError:
                            voice = 1

                    voice_row_id = f"{row_prefix}_p{part_idx}_v{voice}"
                    active_voices.add(voice_row_id)

                    dur_elem = child.find("duration")
                    duration_div = 0
                    if dur_elem is not None and dur_elem.text:
                        try:
                            duration_div = int(dur_elem.text.strip())
                        except ValueError:
                            duration_div = 0

                    is_chord = child.find("chord") is not None
                    is_rest = child.find("rest") is not None

                    if is_rest:
                        if dur_elem is None or duration_div <= 0:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Invalid non-positive duration ({duration_div}) for rest."
                            )
                            continue
                    else:
                        if dur_elem is None or duration_div <= 0:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Invalid non-positive duration ({duration_div}) for ordinary note."
                            )
                            continue

                    delta_q = Fraction(duration_div, cur_div) if cur_div > 0 else Fraction(0, 1)

                    if is_chord:
                        note_start_q = chord_start_q
                        note_end_q = note_start_q + delta_q
                        chord_max_end_q = max(chord_max_end_q, note_end_q)
                        measure_cursor_q = max(measure_cursor_q, chord_max_end_q)
                        measure_max_q = max(measure_max_q, measure_cursor_q)
                    else:
                        note_start_q = measure_cursor_q
                        note_end_q = note_start_q + delta_q
                        chord_start_q = note_start_q
                        chord_max_end_q = note_end_q
                        measure_cursor_q = note_end_q
                        measure_max_q = max(measure_max_q, measure_cursor_q)

                    if is_rest:
                        total_rests += 1
                        continue

                    # Pitch parsing
                    pitch_elem = child.find("pitch")
                    if pitch_elem is None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Note without pitch element skipped."
                        )
                        continue

                    step_elem = pitch_elem.find("step")
                    octave_elem = pitch_elem.find("octave")
                    alter_elem = pitch_elem.find("alter")

                    if step_elem is None or octave_elem is None:
                        unsupported_features.append(
                            f"Part {part_id}, Measure {measure_num}: Incomplete pitch element."
                        )
                        continue

                    step_str = step_elem.text.strip() if step_elem.text else "C"
                    try:
                        octave_val = int(octave_elem.text.strip()) if octave_elem.text else 4
                    except ValueError:
                        octave_val = 4

                    alter_val = 0
                    if alter_elem is not None and alter_elem.text:
                        alter_text = alter_elem.text.strip()
                        try:
                            alter_f = float(alter_text)
                            if alter_f != math.floor(alter_f):
                                unsupported_features.append(
                                    f"Part {part_id}, Measure {measure_num}: Microtonal alteration <alter>{alter_text}</alter> is not supported."
                                )
                                alter_val = int(round(alter_f))
                            else:
                                alter_val = int(alter_f)
                        except ValueError:
                            unsupported_features.append(
                                f"Part {part_id}, Measure {measure_num}: Malformed <alter> tag: {alter_text!r}."
                            )

                    try:
                        midi_pitch = step_octave_to_midi(step_str, octave_val, alter_val)
                    except ValueError as err:
                        unsupported_features.append(f"Part {part_id}, Measure {measure_num}: {err}")
                        continue

                    total_notes += 1
                    notated_type = None
                    type_elem = child.find("type")
                    if type_elem is not None and type_elem.text:
                        notated_type = type_elem.text.strip()

                    tie_types: Set[str] = set()
                    for t in child.findall("tie"):
                        t_type = t.get("type")
                        if t_type:
                            tie_types.add(t_type.strip().lower())
                    if notations_elem is not None:
                        for tied in notations_elem.findall("tied"):
                            t_type = tied.get("type")
                            if t_type:
                                tie_types.add(t_type.strip().lower())

                    raw_notes.append(
                        _RawNote(
                            part_idx=part_idx,
                            part_id=part_id,
                            voice=voice,
                            voice_row_id=voice_row_id,
                            measure_num=measure_num,
                            step=step_str,
                            octave=octave_val,
                            alter=alter_val,
                            midi_pitch=midi_pitch,
                            notated_type=notated_type,
                            q_start=note_start_q,
                            q_end=note_end_q,
                            has_tie_start="start" in tie_types,
                            has_tie_stop="stop" in tie_types,
                        )
                    )

            part_reaches[part_idx] = measure_max_q - measure_start_q

        # Determine measure span for this measure across all parts
        delta_m_dur = max(part_reaches.values()) if part_reaches else Fraction(0, 1)

        # Check time signature against reach
        active_nom_time = measure_nom_time
        if active_nom_time is None:
            for p_idx in current_divs_map:
                if active_time_signatures.get(p_idx) is not None:
                    active_nom_time = active_time_signatures[p_idx]
                    break

        if delta_m_dur == 0:
            if active_nom_time is not None:
                delta_m_dur = active_nom_time
            else:
                delta_m_dur = Fraction(4, 1)
        else:
            if active_nom_time is not None:
                if m_idx == 0 and delta_m_dur < active_nom_time:
                    # Valid pickup measure (anacrusis): duration is actual reach, no invented timing
                    pass
                elif delta_m_dur != active_nom_time:
                    unsupported_features.append(
                        f"Measure {m_idx + 1}: Incomplete or overfull measure (musical reach {float(delta_m_dur):g} beats != time signature {float(active_nom_time):g} beats)."
                    )

        measure_start_q += delta_m_dur

    acc_q = measure_start_q

    # Build Shared Score Timeline across all parts (DEFECT-10 & DEFECT-11)
    shared_timeline = ScoreTimeline(initial_tempo=default_tempo_bpm)
    tempo_directives.sort(key=lambda item: item[0])

    grouped_tempos: Dict[Fraction, List[Tuple[float, str, int]]] = {}
    for q_pos, bpm, p_id, m_num in tempo_directives:
        grouped_tempos.setdefault(q_pos, []).append((bpm, p_id, m_num))

    for q_pos, entries in grouped_tempos.items():
        first_bpm, first_pid, first_mnum = entries[0]
        shared_timeline.set_tempo(q_pos, first_bpm)
        for other_bpm, other_pid, other_mnum in entries[1:]:
            if abs(other_bpm - first_bpm) > 1e-4:
                unsupported_features.append(
                    f"Part {other_pid}, Measure {other_mnum}: Conflicting tempo {other_bpm} BPM at beat {q_pos} conflicts with Part {first_pid} ({first_bpm} BPM). Independent part tempos are not supported."
                )

    # PASS 2: Convert Raw Notes to exact milliseconds and coalesce tied notes
    all_sound_events: List[SoundEvent] = []
    open_ties: Dict[Tuple[int, int, int], Dict[str, Any]] = {}

    raw_notes.sort(key=lambda n: (n.part_idx, n.voice, n.q_start))

    for n in raw_notes:
        event_start_ms_frac = shared_timeline.q_to_ms(n.q_start)
        event_end_ms_frac = shared_timeline.q_to_ms(n.q_end)

        start_ms = int(round(float(event_start_ms_frac)))
        end_ms = int(round(float(event_end_ms_frac)))
        if end_ms <= start_ms:
            end_ms = start_ms + 1

        tie_key = (n.part_idx, n.voice, n.midi_pitch)

        if n.has_tie_stop and n.has_tie_start:
            # Multi-note continuous tie chain (DEFECT-05)
            if tie_key in open_ties:
                prev_tie = open_ties[tie_key]
                if prev_tie["end_frac"] == event_start_ms_frac:
                    prev_tie["end_ms"] = end_ms
                    prev_tie["end_frac"] = event_end_ms_frac
                    continue
                else:
                    gap = float(event_start_ms_frac - prev_tie["end_frac"])
                    unsupported_features.append(
                        f"Part {n.part_id}, Measure {n.measure_num}: Interrupted tie detected for pitch {n.midi_pitch} (temporal gap: {gap:g}ms). Emitted as separate events."
                    )
                    prev = open_ties.pop(tie_key)
                    all_sound_events.append(_create_event_from_dict(prev, len(all_sound_events) + 1, is_tied=False))
                    open_ties[tie_key] = _make_note_dict(
                        start_ms, end_ms, event_start_ms_frac, event_end_ms_frac,
                        n.voice_row_id, n.measure_num, n.step, n.octave, n.alter,
                        n.notated_type, n.midi_pitch, n.voice
                    )
                    continue
            else:
                unsupported_features.append(
                    f"Part {n.part_id}, Measure {n.measure_num}: Orphaned tie stop for pitch {n.midi_pitch} without matching start."
                )

        elif n.has_tie_stop and not n.has_tie_start:
            # End of tie chain
            if tie_key in open_ties:
                prev_tie = open_ties[tie_key]
                if prev_tie["end_frac"] == event_start_ms_frac:
                    prev_tie["end_ms"] = end_ms
                    prev_tie["end_frac"] = event_end_ms_frac
                    completed_tie = open_ties.pop(tie_key)
                    all_sound_events.append(_create_event_from_dict(completed_tie, len(all_sound_events) + 1, is_tied=True))
                    continue
                else:
                    gap = float(event_start_ms_frac - prev_tie["end_frac"])
                    unsupported_features.append(
                        f"Part {n.part_id}, Measure {n.measure_num}: Interrupted tie detected for pitch {n.midi_pitch} (temporal gap: {gap:g}ms). Emitted as separate events."
                    )
                    prev = open_ties.pop(tie_key)
                    all_sound_events.append(_create_event_from_dict(prev, len(all_sound_events) + 1, is_tied=False))
            else:
                unsupported_features.append(
                    f"Part {n.part_id}, Measure {n.measure_num}: Orphaned tie stop for pitch {n.midi_pitch} without matching start."
                )

        elif n.has_tie_start and not n.has_tie_stop:
            # Start of tie chain
            if tie_key in open_ties:
                unsupported_features.append(
                    f"Part {n.part_id}, Measure {n.measure_num}: Duplicate tie start for pitch {n.midi_pitch} without closing prior tie."
                )
                prev = open_ties.pop(tie_key)
                all_sound_events.append(_create_event_from_dict(prev, len(all_sound_events) + 1, is_tied=False))

            open_ties[tie_key] = _make_note_dict(
                start_ms, end_ms, event_start_ms_frac, event_end_ms_frac,
                n.voice_row_id, n.measure_num, n.step, n.octave, n.alter,
                n.notated_type, n.midi_pitch, n.voice
            )
            continue

        # Standard non-tied note
        all_sound_events.append(
            _create_musicxml_sound_event(
                idx=len(all_sound_events) + 1,
                row_id=n.voice_row_id,
                start_ms=start_ms,
                end_ms=end_ms,
                start_frac=event_start_ms_frac,
                end_frac=event_end_ms_frac,
                midi_pitch=n.midi_pitch,
                step=n.step,
                octave=n.octave,
                alter=n.alter,
                notated_type=n.notated_type,
                measure_num=n.measure_num,
                voice=n.voice,
                is_tied=False,
            )
        )

    # Flush unclosed ties
    for tie_key, unclosed_tie in open_ties.items():
        unsupported_features.append(
            f"Part P{unclosed_tie['row_id'].split('_')[1][1:]}, Measure {unclosed_tie['measure']}: Unclosed tie for pitch {unclosed_tie['midi_pitch']} at end of score."
        )
        all_sound_events.append(_create_event_from_dict(unclosed_tie, len(all_sound_events) + 1, is_tied=False))

    all_sound_events.sort(key=lambda e: (e.start_time_ms, e.end_time_ms, e.row_id, e.event_id))

    is_faithful = (len(unsupported_features) == 0)
    for evt in all_sound_events:
        evt.attributes["is_complete_faithful_representation"] = is_faithful

    # Calculate total duration including trailing rests (DEFECT-03)
    total_score_q = max(acc_q, max((n.q_end for n in raw_notes), default=Fraction(0, 1)))
    total_duration_ms_rational = shared_timeline.q_to_ms(total_score_q)
    total_duration_ms = int(round(float(total_duration_ms_rational)))

    return MusicXMLImportResult(
        sound_events=all_sound_events,
        total_duration_ms=total_duration_ms,
        total_duration_ms_rational=total_duration_ms_rational,
        part_count=len(parts),
        voice_count=len(active_voices),
        measure_count=total_measures,
        note_count=total_notes,
        rest_count=total_rests,
        unsupported_features=unsupported_features,
    )


def _make_note_dict(
    start_ms: int,
    end_ms: int,
    start_frac: Fraction,
    end_frac: Fraction,
    row_id: str,
    measure_num: int,
    step: str,
    octave: int,
    alter: int,
    notated_type: Optional[str],
    midi_pitch: int,
    voice: int,
) -> Dict[str, Any]:
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "start_frac": start_frac,
        "end_frac": end_frac,
        "row_id": row_id,
        "measure": measure_num,
        "step": step,
        "octave": octave,
        "alter": alter,
        "notated_type": notated_type,
        "midi_pitch": midi_pitch,
        "voice": voice,
    }


def _create_event_from_dict(note_dict: Dict[str, Any], idx: int, is_tied: bool) -> SoundEvent:
    return _create_musicxml_sound_event(
        idx=idx,
        row_id=note_dict["row_id"],
        start_ms=note_dict["start_ms"],
        end_ms=note_dict["end_ms"],
        start_frac=note_dict["start_frac"],
        end_frac=note_dict["end_frac"],
        midi_pitch=note_dict["midi_pitch"],
        step=note_dict["step"],
        octave=note_dict["octave"],
        alter=note_dict["alter"],
        notated_type=note_dict["notated_type"],
        measure_num=note_dict["measure"],
        voice=note_dict["voice"],
        is_tied=is_tied,
    )


def _create_musicxml_sound_event(
    idx: int,
    row_id: str,
    start_ms: int,
    end_ms: int,
    start_frac: Fraction,
    end_frac: Fraction,
    midi_pitch: int,
    step: str,
    octave: int,
    alter: int,
    notated_type: Optional[str],
    measure_num: int,
    voice: int,
    is_tied: bool,
) -> SoundEvent:
    event_id = f"{row_id}_evt_{idx:04d}"
    dur_frac = end_frac - start_frac
    attrs: Dict[str, Any] = {
        "source_type": "musicxml",
        "pitch_midi": midi_pitch,
        "pitch_step": step,
        "pitch_octave": octave,
        "pitch_alter": alter,
        "measure_number": measure_num,
        "voice": voice,
        "is_tied": is_tied,
        "exact_start_ms_rational": str(start_frac),
        "exact_end_ms_rational": str(end_frac),
        "exact_duration_ms_rational": str(dur_frac),
    }
    if notated_type:
        attrs["notated_type"] = notated_type

    alter_sym = "#" if alter == 1 else "b" if alter == -1 else ""
    label = f"{step}{alter_sym}{octave} (m.{measure_num})"

    return SoundEvent(
        event_id=event_id,
        row_id=row_id,
        start_time_ms=start_ms,
        end_time_ms=end_ms,
        label=label,
        sound_ref=f"xml_measure_{measure_num}",
        attributes=attrs,
        height=float(midi_pitch),
    )


def _load_xml_root(source: Union[str, bytes]) -> ET.Element:
    try:
        if isinstance(source, bytes):
            return ET.fromstring(source)
        elif isinstance(source, str):
            if source.strip().startswith("<"):
                return ET.fromstring(source)
            else:
                tree = ET.parse(source)
                return tree.getroot()
        else:
            raise MusicXMLParseError(f"Unsupported source type: {type(source).__name__}")
    except ET.ParseError as exc:
        raise MusicXMLParseError(f"Malformed XML syntax: {exc}") from exc
    except OSError as exc:
        raise MusicXMLParseError(f"Failed to read file {source}: {exc}") from exc


def _strip_namespaces(element: ET.Element) -> None:
    if "}" in element.tag:
        element.tag = element.tag.split("}", 1)[1]
    for child in element:
        _strip_namespaces(child)


def generate_synthetic_musicxml(
    divisions: int = 1,
    tempo_bpm: float = 120.0,
    measures_data: Optional[List[List[Tuple[str, int, int, int, bool]]]] = None,
) -> str:
    """Generate in-memory synthetic MusicXML string for controlled testing."""
    if measures_data is None:
        measures_data = [[("C", 4, 0, 1, False), ("D", 4, 0, 1, False), ("R", 0, 0, 2, True)]]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<score-partwise version="3.1">',
        '  <part-list>',
        '    <score-part id="P1">',
        '      <part-name>MusicXML Test Part</part-name>',
        '    </score-part>',
        '  </part-list>',
        '  <part id="P1">',
    ]

    for m_idx, notes in enumerate(measures_data, start=1):
        lines.append(f'    <measure number="{m_idx}">')
        if m_idx == 1:
            lines.extend([
                '      <attributes>',
                f'        <divisions>{divisions}</divisions>',
                '        <key><fifths>0</fifths></key>',
                '        <time><beats>4</beats><beat-type>4</beat-type></time>',
                '        <clef><sign>G</sign><line>2</line></clef>',
                '      </attributes>',
                '      <direction placement="above">',
                f'        <sound tempo="{tempo_bpm}"/>',
                '      </direction>',
            ])

        for step, octave, alter, dur_div, is_rest in notes:
            lines.append('      <note>')
            if is_rest:
                lines.append('        <rest/>')
            else:
                lines.extend([
                    '        <pitch>',
                    f'          <step>{step}</step>',
                    f'          <alter>{alter}</alter>',
                    f'          <octave>{octave}</octave>',
                    '        </pitch>',
                ])
            lines.append(f'        <duration>{dur_div}</duration>')
            lines.append('        <voice>1</voice>')
            lines.append('      </note>')

        lines.append('    </measure>')

    lines.extend([
        '  </part>',
        '</score-partwise>',
    ])

    return "\n".join(lines)
