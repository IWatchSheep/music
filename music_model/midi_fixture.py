"""Synthetic orchestral MIDI passage generator and SMF writer.

Constructs valid Standard MIDI Files (Type 1) programmatically without
external dependencies or downloads.

Passage Structure (The "Duck Flight" Orchestral Passage):
- Track 0: Conductor / Tempo Track with tempo changes (100 BPM accelerating to 140 BPM).
- Track 1: Low Brass / Basses (Row Low): Low pedal and pulsing notes (MIDI 36-48).
- Track 2: Mid Horns / Violas (Row Mid): Rising transitional motif (MIDI 55-67).
- Track 3: High Trumpets / Violins (Row High): Soaring airborne phrases (MIDI 72-84).
- Track 4: High Woodwinds / Flutes (Row Flutter): Rapid embellishments and trills (MIDI 84-96).

Yields over 25 variable-width columns, overlapping polyphony, and a clear
low-to-high development pattern across independent tracks.
"""

from __future__ import annotations

import io
import struct
from typing import List, Tuple

from music_model.midi_importer import write_variable_length


def _create_track_chunk(events: List[Tuple[int, bytes]]) -> bytes:
    """Create an MTrk byte sequence from a list of (delta_tick, event_bytes)."""
    track_body = bytearray()
    for delta_tick, event_bytes in events:
        track_body.extend(write_variable_length(delta_tick))
        track_body.extend(event_bytes)
    # End of Track meta event: delta 0, FF 2F 00
    track_body.extend(write_variable_length(0))
    track_body.extend(b"\xFF\x2F\x00")

    chunk = bytearray()
    chunk.extend(b"MTrk")
    chunk.extend(struct.pack(">I", len(track_body)))
    chunk.extend(track_body)
    return bytes(chunk)


def create_synthetic_orchestral_midi_bytes() -> bytes:
    """Generate a rich Type 1 Standard MIDI File as bytes.

    Specifications:
    - Format: Type 1 (synchronous multi-track)
    - Division: 480 ticks per quarter note
    - 5 Tracks:
        Track 0: Conductor / Tempo Track (100 BPM accelerating to 140 BPM at tick 1920)
        Track 1: Low Brass (Low Group: C2=36, E2=40, G2=43, C3=48)
        Track 2: Mid Horns (Transitional Group: G3=55, C4=60, D4=62, E4=64, G4=67)
        Track 3: High Trumpets (High Group: C5=72, E5=76, G5=79, B5=83, C6=84)
        Track 4: High Woodwinds (Peak Group: G5=79, C6=84, E6=88, G6=91)
    """
    division = 480
    num_tracks = 5
    header = bytearray()
    header.extend(b"MThd")
    header.extend(struct.pack(">I", 6))
    header.extend(struct.pack(">HHH", 1, num_tracks, division))

    # -------------------------------------------------------------
    # Track 0: Tempo & Conductor Track
    # -------------------------------------------------------------
    # 100 BPM = 600,000 us/beat -> \x09\x27\xC0
    # 140 BPM = 428,571 us/beat -> \x06\x8A\x4B
    t0_events: List[Tuple[int, bytes]] = [
        (0, b"\xFF\x03\x09Conductor"),
        (0, b"\xFF\x51\x03\x09\x27\xC0"),       # 100 BPM at tick 0
        (1920, b"\xFF\x51\x03\x06\x8A\x4B"),    # Accelerate to 140 BPM at bar 5 (tick 1920)
    ]
    trk0 = _create_track_chunk(t0_events)

    # -------------------------------------------------------------
    # Track 1: Low Brass (Low Group: C2=36, G2=43, C3=48)
    # Channel 0
    # -------------------------------------------------------------
    # Note 1: C2 [0, 1920)
    # Note 2: G2 [480, 1440)
    # Note 3: C3 [1920, 2880)
    # Note 4: G2 [2880, 3840)
    t1_events: List[Tuple[int, bytes]] = [
        (0, b"\xFF\x03\x09Low Brass"),
        # Tick 0: Note On C2
        (0, bytes([0x90, 36, 90])),
        # Tick 480 (delta 480): Note On G2
        (480, bytes([0x90, 43, 80])),
        # Tick 1440 (delta 960): Note Off G2
        (960, bytes([0x80, 43, 0])),
        # Tick 1920 (delta 480): Note Off C2, Note On C3
        (480, bytes([0x80, 36, 0])),
        (0, bytes([0x90, 48, 85])),
        # Tick 2880 (delta 960): Note Off C3, Note On G2
        (960, bytes([0x80, 48, 0])),
        (0, bytes([0x90, 43, 80])),
        # Tick 3840 (delta 960): Note Off G2
        (960, bytes([0x80, 43, 0])),
    ]
    trk1 = _create_track_chunk(t1_events)

    # -------------------------------------------------------------
    # Track 2: Mid Horns (Transitional Group: G3=55, C4=60, D4=62, E4=64, G4=67)
    # Channel 1
    # -------------------------------------------------------------
    # Enters at Beat 2 (tick 480) with a rising staccato/legato arpeggio
    # Note 1: G3 [480, 840)
    # Note 2: C4 [960, 1320)
    # Note 3: D4 [1440, 1800)
    # Note 4: E4 [1920, 2400)
    # Note 5: G4 [2400, 3120)
    # Note 6: C4 [3360, 3840)
    t2_events: List[Tuple[int, bytes]] = [
        (0, b"\xFF\x03\x09Mid Horns"),
        # Tick 480: Note On G3
        (480, bytes([0x91, 55, 95])),
        # Tick 840 (delta 360): Note Off G3
        (360, bytes([0x81, 55, 0])),
        # Tick 960 (delta 120): Note On C4
        (120, bytes([0x91, 60, 95])),
        # Tick 1320 (delta 360): Note Off C4
        (360, bytes([0x81, 60, 0])),
        # Tick 1440 (delta 120): Note On D4
        (120, bytes([0x91, 62, 95])),
        # Tick 1800 (delta 360): Note Off D4
        (360, bytes([0x81, 62, 0])),
        # Tick 1920 (delta 120): Note On E4
        (120, bytes([0x91, 64, 100])),
        # Tick 2400 (delta 480): Note Off E4, Note On G4
        (480, bytes([0x81, 64, 0])),
        (0, bytes([0x91, 67, 105])),
        # Tick 3120 (delta 720): Note Off G4
        (720, bytes([0x81, 67, 0])),
        # Tick 3360 (delta 240): Note On C4
        (240, bytes([0x91, 60, 90])),
        # Tick 3840 (delta 480): Note Off C4
        (480, bytes([0x81, 60, 0])),
    ]
    trk2 = _create_track_chunk(t2_events)

    # -------------------------------------------------------------
    # Track 3: High Trumpets (High Group: C5=72, E5=76, G5=79, B5=83, C6=84)
    # Channel 2
    # -------------------------------------------------------------
    # Enters at Beat 4 (tick 1920) with soaring fanfare
    # Note 1: C5 [1920, 2280)
    # Note 2: E5 [2160, 2640) -- overlaps C5!
    # Note 3: G5 [2520, 3000) -- overlaps E5!
    # Note 4: B5 [2880, 3360) -- overlaps G5!
    # Note 5: C6 [3120, 3840) -- soaring peak!
    t3_events: List[Tuple[int, bytes]] = [
        (0, b"\xFF\x03\x0DHigh Trumpets"),
        # Tick 1920: Note On C5
        (1920, bytes([0x92, 72, 110])),
        # Tick 2160 (delta 240): Note On E5
        (240, bytes([0x92, 76, 112])),
        # Tick 2280 (delta 120): Note Off C5
        (120, bytes([0x82, 72, 0])),
        # Tick 2520 (delta 240): Note On G5
        (240, bytes([0x92, 79, 115])),
        # Tick 2640 (delta 120): Note Off E5
        (120, bytes([0x82, 76, 0])),
        # Tick 2880 (delta 240): Note On B5
        (240, bytes([0x92, 83, 118])),
        # Tick 3000 (delta 120): Note Off G5
        (120, bytes([0x82, 79, 0])),
        # Tick 3120 (delta 120): Note On C6
        (120, bytes([0x92, 84, 120])),
        # Tick 3360 (delta 240): Note Off B5
        (240, bytes([0x82, 83, 0])),
        # Tick 3840 (delta 480): Note Off C6
        (480, bytes([0x82, 84, 0])),
    ]
    trk3 = _create_track_chunk(t3_events)

    # -------------------------------------------------------------
    # Track 4: High Woodwinds (Flutter/Peak Group: G5=79, C6=84, E6=88, G6=91)
    # Channel 3
    # -------------------------------------------------------------
    # Rapid decorative arpeggios at climax (ticks 2880 to 3840)
    # Note 1: G5 [2880, 3000)
    # Note 2: C6 [3000, 3120)
    # Note 3: E6 [3120, 3240)
    # Note 4: G6 [3240, 3480)
    # Note 5: E6 [3480, 3600)
    # Note 6: G6 [3600, 3840)
    t4_events: List[Tuple[int, bytes]] = [
        (0, b"\xFF\x03\x0EHigh Woodwinds"),
        # Tick 2880: Note On G5
        (2880, bytes([0x93, 79, 105])),
        # Tick 3000 (delta 120): Note Off G5, Note On C6
        (120, bytes([0x83, 79, 0])),
        (0, bytes([0x93, 84, 110])),
        # Tick 3120 (delta 120): Note Off C6, Note On E6
        (120, bytes([0x83, 84, 0])),
        (0, bytes([0x93, 88, 115])),
        # Tick 3240 (delta 120): Note Off E6, Note On G6
        (120, bytes([0x83, 88, 0])),
        (0, bytes([0x93, 91, 120])),
        # Tick 3480 (delta 240): Note Off G6, Note On E6
        (240, bytes([0x83, 91, 0])),
        (0, bytes([0x93, 88, 110])),
        # Tick 3600 (delta 120): Note Off E6, Note On G6
        (120, bytes([0x83, 88, 0])),
        (0, bytes([0x93, 91, 120])),
        # Tick 3840 (delta 240): Note Off G6
        (240, bytes([0x83, 91, 0])),
    ]
    trk4 = _create_track_chunk(t4_events)

    out = bytearray()
    out.extend(header)
    out.extend(trk0)
    out.extend(trk1)
    out.extend(trk2)
    out.extend(trk3)
    out.extend(trk4)
    return bytes(out)


def create_synthetic_orchestral_song() -> SongTimeline:
    """Create a SongTimeline directly by generating and importing the synthetic orchestral passage."""
    from music_model.midi_importer import MidiImporter

    midi_bytes = create_synthetic_orchestral_midi_bytes()
    importer = MidiImporter()
    return importer.import_bytes(
        midi_bytes,
        song_id="synthetic_orchestral_flight",
        title="Synthetic Orchestral Flight (Low-to-High)",
        group_by="track",
    )
