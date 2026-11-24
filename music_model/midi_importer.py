"""Pure-Python Standard MIDI File (SMF) parser and importer.

Converts MIDI files (Type 0 and Type 1) into temporary sound rows and
linked variable-width time columns for the Music Timeline architecture.

Mathematical & Timing Principles:
1. Exact Tick Timelines:
   Every event preserves its original integer tick position within its track.
2. Global Tempo Map:
   Tempo change events (0xFF 0x51 0x03) across all tracks are merged into a
   global piecewise linear timeline. Exact rational arithmetic (fractions.Fraction)
   computes elapsed microseconds without cumulative floating-point drift.
3. Deterministic Integer Millisecond Rounding:
   Elapsed time in milliseconds is computed as:
       elapsed_ms = round(Fraction(elapsed_us, 1000))
   Timestamps strictly belong to nonnegative integer milliseconds (Z_>=0).
4. Non-zero Duration Guarantee:
   If an imported note has start_tick < end_tick but rounds to the same
   millisecond (start_ms == end_ms), its duration is explicitly set to 1 ms,
   preserving non-zero duration while logging attribute 'collapsed_duration': True.
5. Multi-Track & Polyphony:
   Overlapping notes, repeated notes of the same pitch, and multi-channel/multi-track
   structures are cleanly parsed using FIFO note-tracking queues.
"""

from __future__ import annotations

import io
import math
import struct
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Tuple, Union

from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow


# ---------------------------------------------------------------------------
# MIDI Constants & Specifications
# ---------------------------------------------------------------------------
DEFAULT_MICROSECONDS_PER_BEAT: int = 500_000  # Default 120 BPM in MIDI spec
SMF_MTHD_MAGIC: bytes = b"MThd"
SMF_MTRK_MAGIC: bytes = b"MTrk"


# ---------------------------------------------------------------------------
# Low-Level MIDI Structures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MidiNoteRaw:
    """Raw parsed MIDI note before conversion to timeline coordinates."""

    track_index: int
    channel: int
    pitch: int
    velocity: int
    start_tick: int
    end_tick: int
    track_name: str = ""

    @property
    def duration_ticks(self) -> int:
        return self.end_tick - self.start_tick


@dataclass(frozen=True)
class TempoEvent:
    """Global tempo change event."""

    tick: int
    microseconds_per_beat: int

    @property
    def bpm(self) -> float:
        return 60_000_000.0 / self.microseconds_per_beat


class TempoMap:
    """Piecewise linear tick-to-time converter using exact rational arithmetic."""

    def __init__(
        self,
        ticks_per_beat: int,
        tempo_events: Sequence[TempoEvent],
    ) -> None:
        if ticks_per_beat <= 0:
            raise ValueError(f"ticks_per_beat must be a positive integer, got {ticks_per_beat}")

        self.ticks_per_beat: int = ticks_per_beat

        # Sort and deduplicate tempo events by tick
        sorted_events = sorted(tempo_events, key=lambda e: e.tick)
        cleaned: List[TempoEvent] = []
        for te in sorted_events:
            if cleaned and cleaned[-1].tick == te.tick:
                # Later tempo event at same tick overrides earlier
                cleaned[-1] = te
            else:
                cleaned.append(te)

        # Ensure baseline at tick 0
        if not cleaned or cleaned[0].tick > 0:
            cleaned.insert(0, TempoEvent(tick=0, microseconds_per_beat=DEFAULT_MICROSECONDS_PER_BEAT))

        self._events: Tuple[TempoEvent, ...] = tuple(cleaned)

        # Precompute exact cumulative microseconds at each tempo change boundary
        # using rational arithmetic (Fraction) to eliminate cumulative drift.
        self._anchor_ticks: List[int] = []
        self._anchor_us: List[Fraction] = []
        self._rates_us_per_tick: List[Fraction] = []

        accum_us = Fraction(0, 1)
        prev_tick = 0
        prev_tempo = self._events[0].microseconds_per_beat

        for te in self._events:
            delta_ticks = te.tick - prev_tick
            rate = Fraction(prev_tempo, self.ticks_per_beat)
            accum_us += delta_ticks * rate

            self._anchor_ticks.append(te.tick)
            self._anchor_us.append(accum_us)
            self._rates_us_per_tick.append(Fraction(te.microseconds_per_beat, self.ticks_per_beat))

            prev_tick = te.tick
            prev_tempo = te.microseconds_per_beat

    @property
    def events(self) -> Tuple[TempoEvent, ...]:
        return self._events

    def tick_to_microseconds_exact(self, tick: int) -> Fraction:
        """Convert a MIDI tick to exact microseconds as a rational Fraction."""
        if tick < 0:
            raise ValueError(f"Tick must be nonnegative, got {tick}")

        # Find the active tempo segment
        idx = 0
        for i, anchor in enumerate(self._anchor_ticks):
            if tick >= anchor:
                idx = i
            else:
                break

        anchor_tick = self._anchor_ticks[idx]
        anchor_us = self._anchor_us[idx]
        rate = self._rates_us_per_tick[idx]

        return anchor_us + (tick - anchor_tick) * rate

    def tick_to_milliseconds(self, tick: int) -> int:
        """Convert a MIDI tick to integer milliseconds using deterministic rounding."""
        us_exact = self.tick_to_microseconds_exact(tick)
        ms_exact = us_exact / 1000
        # Deterministic half-to-even integer rounding
        return round(float(ms_exact))

    def tick_to_seconds(self, tick: int) -> float:
        """Convert a MIDI tick to fractional seconds."""
        us_exact = self.tick_to_microseconds_exact(tick)
        return float(us_exact / 1_000_000)


# ---------------------------------------------------------------------------
# Variable-Length Quantity (VLQ) Binary Helpers
# ---------------------------------------------------------------------------
def read_variable_length(stream: BinaryIO) -> int:
    """Read a MIDI variable-length quantity (1 to 4 bytes).

    Raises:
        ValueError: If EOF is reached unexpectedly or VLQ exceeds 4 bytes.
    """
    value = 0
    bytes_read = 0
    while True:
        b = stream.read(1)
        if not b:
            raise ValueError("Unexpected EOF while reading MIDI variable-length quantity")
        byte_val = b[0]
        bytes_read += 1
        value = (value << 7) | (byte_val & 0x7F)
        if (byte_val & 0x80) == 0:
            break
        if bytes_read > 4:
            raise ValueError("MIDI variable-length quantity exceeded 4 bytes")
    return value


def write_variable_length(value: int) -> bytes:
    """Encode an integer as a MIDI variable-length quantity."""
    if value < 0:
        raise ValueError(f"VLQ value must be nonnegative, got {value}")
    if value == 0:
        return b"\x00"

    buffer = bytearray()
    buffer.append(value & 0x7F)
    value >>= 7
    while value > 0:
        buffer.append((value & 0x7F) | 0x80)
        value >>= 7
    buffer.reverse()
    return bytes(buffer)


# ---------------------------------------------------------------------------
# Pure-Python SMF Parser
# ---------------------------------------------------------------------------
@dataclass
class ParsedMidiFile:
    """Result of low-level MIDI parsing."""

    format_type: int
    num_tracks: int
    ticks_per_beat: int
    tempo_map: TempoMap
    raw_notes: List[MidiNoteRaw]
    track_names: Dict[int, str]
    max_tick: int


class MidiParser:
    """Strict, robust binary Standard MIDI File (SMF Type 0 and Type 1) parser."""

    def parse(self, stream_or_bytes: Union[BinaryIO, bytes]) -> ParsedMidiFile:
        """Parse binary SMF data into tracks, tempo events, and raw notes."""
        if isinstance(stream_or_bytes, bytes):
            stream = io.BytesIO(stream_or_bytes)
        else:
            stream = stream_or_bytes

        # 1. Parse MThd Header
        header_tag = stream.read(4)
        if header_tag != SMF_MTHD_MAGIC:
            raise ValueError(f"Invalid MIDI header magic: expected b'MThd', got {header_tag!r}")

        header_len_bytes = stream.read(4)
        if len(header_len_bytes) < 4:
            raise ValueError("Truncated MIDI header length")
        (header_len,) = struct.unpack(">I", header_len_bytes)
        if header_len < 6:
            raise ValueError(f"Invalid MIDI header length: expected >= 6, got {header_len}")

        header_data = stream.read(header_len)
        if len(header_data) < header_len:
            raise ValueError("Truncated MIDI header data")

        fmt, num_tracks, division = struct.unpack(">HHH", header_data[:6])

        if fmt not in (0, 1):
            raise ValueError(
                f"Unsupported MIDI file format: Type {fmt}. "
                "Only Type 0 (single track) and Type 1 (synchronous multi-track) are supported."
            )

        if division & 0x8000:
            raise ValueError(
                "SMPTE timecode division in MIDI files is not supported. "
                "Standard PPQ (ticks per quarter-note) division is required."
            )
        ticks_per_beat = division
        if ticks_per_beat <= 0:
            raise ValueError(f"Invalid ticks_per_beat: {ticks_per_beat}")

        # 2. Parse MTrk Chunks
        raw_notes: List[MidiNoteRaw] = []
        tempo_events: List[TempoEvent] = []
        track_names: Dict[int, str] = {}
        global_max_tick = 0

        tracks_read = 0
        while tracks_read < num_tracks:
            chunk_type = stream.read(4)
            if not chunk_type:
                break
            chunk_len_bytes = stream.read(4)
            if len(chunk_len_bytes) < 4:
                raise ValueError(f"Truncated chunk length in track {tracks_read}")
            (chunk_len,) = struct.unpack(">I", chunk_len_bytes)

            if chunk_type != SMF_MTRK_MAGIC:
                # Skip unknown chunk safely
                stream.seek(chunk_len, io.SEEK_CUR)
                continue

            track_data = stream.read(chunk_len)
            if len(track_data) < chunk_len:
                raise ValueError(f"Truncated track {tracks_read} data: expected {chunk_len} bytes, got {len(track_data)}")

            track_max_tick, trk_name = self._parse_track(
                track_index=tracks_read,
                track_data=track_data,
                raw_notes=raw_notes,
                tempo_events=tempo_events,
            )
            track_names[tracks_read] = trk_name
            if track_max_tick > global_max_tick:
                global_max_tick = track_max_tick

            tracks_read += 1

        if tracks_read < num_tracks:
            raise ValueError(f"Expected {num_tracks} tracks in header, but only found {tracks_read}")

        tempo_map = TempoMap(ticks_per_beat=ticks_per_beat, tempo_events=tempo_events)

        return ParsedMidiFile(
            format_type=fmt,
            num_tracks=num_tracks,
            ticks_per_beat=ticks_per_beat,
            tempo_map=tempo_map,
            raw_notes=raw_notes,
            track_names=track_names,
            max_tick=global_max_tick,
        )

    def _parse_track(
        self,
        track_index: int,
        track_data: bytes,
        raw_notes: List[MidiNoteRaw],
        tempo_events: List[TempoEvent],
    ) -> Tuple[int, str]:
        """Parse events from a single MTrk byte sequence."""
        stream = io.BytesIO(track_data)
        current_tick = 0
        running_status: Optional[int] = None
        track_name = ""

        # Active note tracker: (channel, pitch) -> list of (start_tick, velocity) FIFO
        active_notes: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

        while stream.tell() < len(track_data):
            delta = read_variable_length(stream)
            current_tick += delta

            b = stream.read(1)
            if not b:
                break
            status_byte = b[0]

            if status_byte < 0x80:
                # Running status applies
                if running_status is None:
                    raise ValueError(
                        f"Running status encountered before any status byte at track {track_index}, byte {stream.tell()}"
                    )
                data_byte1 = status_byte
                status = running_status
            else:
                status = status_byte
                if status < 0xF0:
                    running_status = status
                else:
                    running_status = None  # SysEx and Meta clear running status
                data_byte1 = None

            # Handle Meta Events (0xFF)
            if status == 0xFF:
                meta_type_byte = stream.read(1)
                if not meta_type_byte:
                    raise ValueError("Truncated meta event type")
                meta_type = meta_type_byte[0]
                meta_len = read_variable_length(stream)
                meta_data = stream.read(meta_len)
                if len(meta_data) < meta_len:
                    raise ValueError(f"Truncated meta event {meta_type:#x} data")

                if meta_type == 0x51:  # Set Tempo
                    if meta_len == 3:
                        tempo_us = (meta_data[0] << 16) | (meta_data[1] << 8) | meta_data[2]
                        if tempo_us > 0:
                            tempo_events.append(TempoEvent(tick=current_tick, microseconds_per_beat=tempo_us))
                elif meta_type == 0x03:  # Track Name
                    try:
                        track_name = meta_data.decode("utf-8", errors="replace").strip()
                    except Exception:
                        track_name = f"Track {track_index}"
                elif meta_type == 0x2F:  # End of Track
                    break
                continue

            # Handle SysEx Events (0xF0 / 0xF7)
            if status in (0xF0, 0xF7):
                sysex_len = read_variable_length(stream)
                stream.read(sysex_len)
                continue

            # Handle Channel Messages (0x80 - 0xEF)
            msg_type = status & 0xF0
            channel = status & 0x0F

            if data_byte1 is None:
                d1_b = stream.read(1)
                if not d1_b:
                    raise ValueError("Truncated channel event data byte 1")
                d1 = d1_b[0]
            else:
                d1 = data_byte1

            # Determine number of additional data bytes
            if msg_type in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                d2_b = stream.read(1)
                if not d2_b:
                    raise ValueError("Truncated channel event data byte 2")
                d2 = d2_b[0]
            else:
                d2 = 0

            # Process Note-On / Note-Off
            if msg_type == 0x90:
                pitch = d1
                velocity = d2
                key = (channel, pitch)

                if velocity > 0:
                    # Note On
                    if key not in active_notes:
                        active_notes[key] = []
                    active_notes[key].append((current_tick, velocity))
                else:
                    # Note On with velocity 0 is Note Off
                    self._close_note(active_notes, key, current_tick, track_index, raw_notes, track_name)

            elif msg_type == 0x80:
                # Note Off
                pitch = d1
                key = (channel, pitch)
                self._close_note(active_notes, key, current_tick, track_index, raw_notes, track_name)

        # Close any lingering active notes at the end of the track
        for (chan, pitch), note_list in active_notes.items():
            for start_tick, vel in note_list:
                end_tick = max(current_tick, start_tick + 1)
                raw_notes.append(
                    MidiNoteRaw(
                        track_index=track_index,
                        channel=chan,
                        pitch=pitch,
                        velocity=vel,
                        start_tick=start_tick,
                        end_tick=end_tick,
                        track_name=track_name,
                    )
                )

        if not track_name:
            track_name = f"Track {track_index}"

        return current_tick, track_name

    def _close_note(
        self,
        active_notes: Dict[Tuple[int, int], List[Tuple[int, int]]],
        key: Tuple[int, int],
        current_tick: int,
        track_index: int,
        raw_notes: List[MidiNoteRaw],
        track_name: str,
    ) -> None:
        """Close an active note (FIFO matching) and record MidiNoteRaw."""
        if key in active_notes and active_notes[key]:
            start_tick, vel = active_notes[key].pop(0)
            end_tick = max(current_tick, start_tick + 1)
            raw_notes.append(
                MidiNoteRaw(
                    track_index=track_index,
                    channel=key[0],
                    pitch=key[1],
                    velocity=vel,
                    start_tick=start_tick,
                    end_tick=end_tick,
                    track_name=track_name,
                )
            )


# ---------------------------------------------------------------------------
# High-Level MIDI Importer to SongTimeline
# ---------------------------------------------------------------------------
ENHARMONIC_NAMES: Dict[int, str] = {
    1: "C# / Db",
    3: "D# / Eb",
    6: "F# / Gb",
    8: "G# / Ab",
    10: "A# / Bb",
}


def pitch_to_note_name(pitch: int, enharmonic: bool = False) -> str:
    """Format MIDI pitch (0-127) as standard scientific note name.

    Standard convention:
        MIDI 60 = C4
        MIDI 69 = A4
        MIDI 72 = C5
        MIDI 75 = D#5 / Eb5
        MIDI 84 = C6

    Args:
        pitch: Integer MIDI note number (0 to 127).
        enharmonic: If True, include both sharp and flat names for accidental notes.

    Returns:
        Formatted note string like 'C4 (60)' or 'D#5 / Eb5 (75)'.
    """
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (pitch // 12) - 1
    semitone = pitch % 12
    if enharmonic and semitone in ENHARMONIC_NAMES:
        enh = ENHARMONIC_NAMES[semitone]
        parts = enh.split(" / ")
        return f"{parts[0]}{octave} / {parts[1]}{octave} ({pitch})"
    note_name = notes[semitone]
    return f"{note_name}{octave} ({pitch})"


# Internal backward-compatibility alias
_pitch_to_note_name = pitch_to_note_name


class MidiImporter:
    """Imports Standard MIDI Files into SongTimeline models."""

    def __init__(self, parser: Optional[MidiParser] = None) -> None:
        self.parser: MidiParser = parser if parser is not None else MidiParser()

    def import_file(
        self,
        filepath: str,
        song_id: Optional[str] = None,
        title: Optional[str] = None,
        group_by: str = "auto",
    ) -> SongTimeline:
        """Import a MIDI file from disk into a SongTimeline.

        Args:
            filepath: Path to the .mid file.
            song_id: Optional unique song ID. Defaults to file basename.
            title: Optional descriptive title.
            group_by: Row grouping rule: 'auto', 'track', 'channel', or 'register'.
        """
        import os

        with open(filepath, "rb") as f:
            data = f.read()

        base_name = os.path.splitext(os.path.basename(filepath))[0]
        s_id = song_id or f"midi_{base_name}"
        t_title = title or base_name.replace("_", " ").title()

        return self.import_bytes(data, song_id=s_id, title=t_title, group_by=group_by)

    def import_bytes(
        self,
        midi_bytes: bytes,
        song_id: str = "imported_midi",
        title: str = "Imported MIDI Composition",
        group_by: str = "auto",
    ) -> SongTimeline:
        """Import MIDI bytes into a SongTimeline.

        Args:
            midi_bytes: Binary SMF data.
            song_id: Unique identifier for the song.
            title: Title for the song.
            group_by: 'auto', 'track', 'channel', or 'register'.
        """
        parsed = self.parser.parse(midi_bytes)

        # Baseline tempo in BPM from first tempo event
        initial_bpm = parsed.tempo_map.events[0].bpm if parsed.tempo_map.events else 120.0

        song = SongTimeline(
            song_id=song_id,
            title=title,
            tempo_bpm=round(initial_bpm, 2),
            description=(
                f"Imported SMF Type {parsed.format_type} with {parsed.num_tracks} track(s), "
                f"{parsed.ticks_per_beat} PPQ, {len(parsed.raw_notes)} total note(s)."
            ),
        )

        # Determine grouping strategy
        # Auto: If multiple tracks contain notes, group by track; if single track with multiple channels, group by channel.
        tracks_with_notes = {n.track_index for n in parsed.raw_notes}
        channels_with_notes = {n.channel for n in parsed.raw_notes}

        actual_group_by = group_by
        if actual_group_by == "auto":
            if len(tracks_with_notes) > 1:
                actual_group_by = "track"
            elif len(channels_with_notes) > 1:
                actual_group_by = "channel"
            else:
                actual_group_by = "track"

        # Sort raw notes chronologically by start_tick, then pitch
        sorted_notes = sorted(parsed.raw_notes, key=lambda n: (n.start_tick, n.end_tick, n.pitch))

        collapsed_count = 0

        for idx, rn in enumerate(sorted_notes):
            # Convert ticks to exact milliseconds using TempoMap
            start_ms = parsed.tempo_map.tick_to_milliseconds(rn.start_tick)
            end_ms = parsed.tempo_map.tick_to_milliseconds(rn.end_tick)

            collapsed = False
            if end_ms <= start_ms:
                # Deterministic coordinate collapse handling: ensure minimum 1 ms duration
                end_ms = start_ms + 1
                collapsed = True
                collapsed_count += 1

            # Determine temporary row ID based on grouping rule
            if actual_group_by == "channel":
                row_id = f"Row Channel {rn.channel + 1}"
                row_label = f"Channel {rn.channel + 1}"
            elif actual_group_by == "register":
                # Divide standard 88-key piano into 4 registers
                if rn.pitch < 48:
                    row_id = "Row Bass (< C3)"
                elif rn.pitch < 60:
                    row_id = "Row Tenor (C3 - B3)"
                elif rn.pitch < 72:
                    row_id = "Row Alto (C4 - B4)"
                else:
                    row_id = "Row Soprano (>= C5)"
                row_label = row_id.replace("Row ", "")
            else:
                # Group by Track
                trk_name = parsed.track_names.get(rn.track_index, f"Track {rn.track_index}")
                row_id = f"Row Track {rn.track_index + 1}: {trk_name}"
                row_label = f"Track {rn.track_index + 1} ({trk_name})"

            # Ensure row exists in song
            if song.get_row(row_id) is None:
                song.create_row(row_id=row_id, label=row_label)

            note_label = pitch_to_note_name(rn.pitch)
            event_id = f"note_{rn.track_index}_{rn.channel}_{rn.pitch}_{rn.start_tick}_{idx}"

            attributes: Dict[str, Any] = {
                "pitch": rn.pitch,
                "velocity": rn.velocity,
                "channel": rn.channel,
                "track": rn.track_index,
                "start_tick": rn.start_tick,
                "end_tick": rn.end_tick,
                "duration_ticks": rn.duration_ticks,
                "collapsed_duration": collapsed,
                "original_start_ms_exact": float(parsed.tempo_map.tick_to_microseconds_exact(rn.start_tick) / 1000),
                "original_end_ms_exact": float(parsed.tempo_map.tick_to_microseconds_exact(rn.end_tick) / 1000),
            }

            # Map MIDI note pitch (0-127) directly to experimental height (float)
            event = SoundEvent(
                event_id=event_id,
                row_id=row_id,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                label=note_label,
                attributes=attributes,
                height=float(rn.pitch),
            )
            song.add_event(event)

        if collapsed_count > 0:
            song.description += f" [Note: {collapsed_count} note(s) had rounded durations adjusted to 1 ms]."

        return song
