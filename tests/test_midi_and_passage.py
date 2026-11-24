"""Automated test suite for Stage 3: MIDI and Musical Passage Import.

Tests cover:
1. Pure-Python SMF Type 0 and Type 1 parsing.
2. Note-on and note-off pairing (including velocity 0 as note-off).
3. Polyphonic overlapping notes and repeated notes of the same pitch.
4. Running status handling.
5. Tempo changes and piecewise rational arithmetic.
6. Integer-millisecond deterministic rounding & non-zero duration guarantee.
7. Malformed and unsupported MIDI files (Type 2, SMPTE, truncated chunks).
8. Reproducible JSON passage serialization & deserialization.
9. Many-column layouts (>16 columns) and variable widths.
10. Song independence and isolation.
11. GUI MIDI mode smoke test.
"""

from __future__ import annotations

import io
import struct
import unittest
from fractions import Fraction

from music_gui.main_window import MusicGUI
from music_model.development_profile import calculate_development_constant_row
from music_model.midi_fixture import (
    create_synthetic_orchestral_midi_bytes,
    create_synthetic_orchestral_song,
)
from music_model.midi_importer import (
    MidiImporter,
    MidiParser,
    TempoEvent,
    TempoMap,
    write_variable_length,
)
from music_model.passage_format import (
    load_song_from_file,
    save_song_to_file,
    song_from_dict,
    song_from_json,
    song_to_dict,
    song_to_json,
)
from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent


class TestMidiParsingAndTiming(unittest.TestCase):
    """Test low-level binary SMF parsing and timing conversions."""

    def test_vlq_read_write(self) -> None:
        """Verify variable-length quantity encoding and decoding for standard MIDI values."""
        from music_model.midi_importer import read_variable_length

        test_cases = [0, 64, 127, 128, 255, 16383, 16384, 2097151, 268435455]
        for val in test_cases:
            enc = write_variable_length(val)
            dec = read_variable_length(io.BytesIO(enc))
            self.assertEqual(val, dec, f"VLQ mismatch for value {val}")

    def test_tempo_map_exact_rational_arithmetic(self) -> None:
        """Verify tempo map conversion from ticks to microseconds and milliseconds."""
        tempo_events = [
            TempoEvent(tick=0, microseconds_per_beat=500_000),       # 120 BPM
            TempoEvent(tick=960, microseconds_per_beat=1_000_000),   # 60 BPM at beat 2
        ]
        tmap = TempoMap(ticks_per_beat=480, tempo_events=tempo_events)

        # Tick 480 = 1 beat = 500,000 us = 500 ms
        self.assertEqual(tmap.tick_to_microseconds_exact(480), Fraction(500_000, 1))
        self.assertEqual(tmap.tick_to_milliseconds(480), 500)

        # Tick 960 = 2 beats = 1,000,000 us = 1000 ms
        self.assertEqual(tmap.tick_to_microseconds_exact(960), Fraction(1_000_000, 1))
        self.assertEqual(tmap.tick_to_milliseconds(960), 1000)

        # Tick 1440 = 960 + 480 ticks at 1,000,000 us/beat = 1,000,000 + 1,000,000 = 2,000,000 us = 2000 ms
        self.assertEqual(tmap.tick_to_microseconds_exact(1440), Fraction(2_000_000, 1))
        self.assertEqual(tmap.tick_to_milliseconds(1440), 2000)

    def test_note_on_velocity_zero_acts_as_note_off(self) -> None:
        """Verify that note-on with velocity 0 is treated as note-off."""
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        track_body = (
            b"\x00\x90\x3C\x40"      # delta 0, note-on pitch 60, vel 64
            + write_variable_length(480) + b"\x90\x3C\x00"  # delta 480, note-on pitch 60, vel 0
            + b"\x00\xFF\x2F\x00"      # end of track
        )
        track = b"MTrk" + struct.pack(">I", len(track_body)) + track_body
        midi_data = header + track

        importer = MidiImporter()
        song = importer.import_bytes(midi_data, "type0_test")
        self.assertEqual(song.event_count, 1)
        event = song.all_events[0]
        self.assertEqual(event.attributes["pitch"], 60)
        self.assertEqual(event.attributes["start_tick"], 0)
        self.assertEqual(event.attributes["end_tick"], 480)
        self.assertEqual(event.start_time_ms, 0)
        self.assertEqual(event.end_time_ms, 500)

    def test_running_status_handling(self) -> None:
        """Verify that running status byte persistence works correctly."""
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        track_body = (
            b"\x00\x90\x3C\x40"  # status byte 0x90, C4 vel 64
            + b"\x00\x40\x40"      # running status 0x90! E4 vel 64
            + write_variable_length(480) + b"\x80\x3C\x00"  # delta 480, status 0x80, note-off C4
            + b"\x00\x40\x00"      # running status 0x80! note-off E4
            + b"\x00\xFF\x2F\x00"  # end of track
        )
        track = b"MTrk" + struct.pack(">I", len(track_body)) + track_body
        midi_data = header + track

        importer = MidiImporter()
        song = importer.import_bytes(midi_data, "running_status_test")
        self.assertEqual(song.event_count, 2)
        pitches = {e.attributes["pitch"] for e in song.all_events}
        self.assertEqual(pitches, {60, 64})

    def test_polyphonic_and_overlapping_notes(self) -> None:
        """Verify overlapping polyphony where two notes sound simultaneously."""
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        d240 = write_variable_length(240)
        track_body = (
            b"\x00\x90\x3C\x40"      # delta 0: Note On C4
            + d240 + b"\x90\x40\x40"  # delta 240: Note On E4 (polyphonic overlap!)
            + d240 + b"\x80\x3C\x00"  # delta 240 (tick 480): Note Off C4
            + d240 + b"\x80\x40\x00"  # delta 240 (tick 720): Note Off E4
            + b"\x00\xFF\x2F\x00"
        )
        track = b"MTrk" + struct.pack(">I", len(track_body)) + track_body
        midi_data = header + track

        importer = MidiImporter()
        song = importer.import_bytes(midi_data, "polyphony_test")
        self.assertEqual(song.event_count, 2)
        # Boundaries: 0, 250, 500, 750 ms (since 120 BPM = 500 ms/beat, 240 ticks = 250 ms)
        self.assertEqual(song.extract_boundaries(), (0, 250, 500, 750))
        self.assertEqual(song.column_count, 3)
        cols = song.build_columns()
        self.assertEqual(cols[1].active_event_ids, ("note_0_0_60_0_0", "note_0_0_64_240_1"))

    def test_repeated_notes_of_same_pitch(self) -> None:
        """Verify that repeated notes of the same pitch are matched FIFO."""
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        d240 = write_variable_length(240)
        track_body = (
            b"\x00\x90\x3C\x50"  # tick 0: Note On C4
            + d240 + b"\x80\x3C\x00"  # tick 240: Note Off C4
            + b"\x00\x90\x3C\x60"  # tick 240: Note On C4 again
            + d240 + b"\x80\x3C\x00"  # tick 480: Note Off C4
            + b"\x00\xFF\x2F\x00"
        )
        track = b"MTrk" + struct.pack(">I", len(track_body)) + track_body
        midi_data = header + track

        importer = MidiImporter()
        song = importer.import_bytes(midi_data, "repeated_notes_test")
        self.assertEqual(song.event_count, 2)
        ev1, ev2 = song.all_events
        self.assertEqual(ev1.start_time_ms, 0)
        self.assertEqual(ev1.end_time_ms, 250)
        self.assertEqual(ev2.start_time_ms, 250)
        self.assertEqual(ev2.end_time_ms, 500)

    def test_coordinate_collapse_minimum_one_millisecond(self) -> None:
        """Verify that extremely short notes (rounding to start_ms == end_ms) are given duration 1 ms."""
        tempo_events = [TempoEvent(tick=0, microseconds_per_beat=500_000)]
        tmap = TempoMap(ticks_per_beat=9600, tempo_events=tempo_events)
        self.assertEqual(tmap.tick_to_milliseconds(0), 0)
        self.assertEqual(tmap.tick_to_milliseconds(1), 0)

        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 9600)
        track_body = (
            b"\x00\x90\x3C\x40"  # tick 0: note-on
            b"\x01\x80\x3C\x00"  # tick 1: note-off (rounds to 0 ms!)
            b"\x00\xFF\x2F\x00"
        )
        track = b"MTrk" + struct.pack(">I", len(track_body)) + track_body
        midi_data = header + track

        importer = MidiImporter()
        song = importer.import_bytes(midi_data, "tiny_note_test")
        self.assertEqual(song.event_count, 1)
        ev = song.all_events[0]
        self.assertEqual(ev.start_time_ms, 0)
        self.assertEqual(ev.end_time_ms, 1)
        self.assertTrue(ev.attributes["collapsed_duration"])

    def test_malformed_midi_rejection(self) -> None:
        """Verify that corrupt or unsupported MIDI files are cleanly rejected."""
        parser = MidiParser()

        # Bad magic header
        with self.assertRaises(ValueError):
            parser.parse(b"RIFF\x00\x00\x00\x06\x00\x01\x00\x01\x01\xE0")

        # Truncated header
        with self.assertRaises(ValueError):
            parser.parse(b"MThd\x00\x00\x00\x02\x00")

        # Unsupported Type 2
        bad_type2 = b"MThd" + struct.pack(">IHHH", 6, 2, 1, 480)
        with self.assertRaises(ValueError):
            parser.parse(bad_type2)

        # Unsupported SMPTE division (bit 15 set)
        bad_smpte = b"MThd" + struct.pack(">IHHH", 6, 1, 1, 0x8000 | 120)
        with self.assertRaises(ValueError):
            parser.parse(bad_smpte)


class TestReproduciblePassageFormat(unittest.TestCase):
    """Test JSON passage serialization, deserialization, and round-trip fidelity."""

    def test_json_roundtrip_fidelity(self) -> None:
        """Verify that a SongTimeline round-trips through JSON with identical structure."""
        song_orig = create_synthetic_orchestral_song()
        json_str = song_to_json(song_orig)

        song_restored = song_from_json(json_str)

        self.assertEqual(song_orig.song_id, song_restored.song_id)
        self.assertEqual(song_orig.title, song_restored.title)
        self.assertEqual(song_orig.tempo_bpm, song_restored.tempo_bpm)
        self.assertEqual(song_orig.total_duration_ms, song_restored.total_duration_ms)
        self.assertEqual(song_orig.row_count, song_restored.row_count)
        self.assertEqual(song_orig.event_count, song_restored.event_count)
        self.assertEqual(song_orig.column_count, song_restored.column_count)
        self.assertEqual(song_orig.extract_boundaries(), song_restored.extract_boundaries())
        self.assertEqual(song_orig.constant_row.values, song_restored.constant_row.values)

        dev_orig = calculate_development_constant_row(song_orig.timeline)
        dev_restored = calculate_development_constant_row(song_restored.timeline)
        self.assertEqual(dev_orig.values, dev_restored.values)

    def test_json_deserialization_validation(self) -> None:
        """Verify that malformed JSON passage structures raise ValueError."""
        with self.assertRaises(ValueError):
            song_from_dict({"title": "No Song ID"})

        with self.assertRaises(ValueError):
            song_from_dict({"song_id": "test", "events": "not a list"})

        with self.assertRaises(ValueError):
            song_from_dict({
                "song_id": "test",
                "events": [{"event_id": "e1", "row_id": "r1", "start_time_ms": 100}]
            })


class TestStage3IntegrationAndGUI(unittest.TestCase):
    """Integration and GUI test for Stage 3."""

    def test_synthetic_orchestral_many_columns(self) -> None:
        """Verify synthetic orchestral fixture produces >= 16 columns and low-to-high progression."""
        song = create_synthetic_orchestral_song()
        self.assertGreaterEqual(song.column_count, 16)
        self.assertEqual(song.row_count, 4)

        dev_row = calculate_development_constant_row(song.timeline)
        self.assertLessEqual(dev_row.values[0], 40.0)
        self.assertGreaterEqual(max(dev_row.values), 75.0)

    def test_song_independence(self) -> None:
        """Verify that two songs imported from the same MIDI bytes do not share state."""
        midi_bytes = create_synthetic_orchestral_midi_bytes()
        importer = MidiImporter()
        song1 = importer.import_bytes(midi_bytes, "song1", group_by="track")
        song2 = importer.import_bytes(midi_bytes, "song2", group_by="register")

        self.assertNotEqual(song1.song_id, song2.song_id)
        self.assertIsNot(song1.timeline, song2.timeline)
        self.assertNotEqual([r.row_id for r in song1.rows], [r.row_id for r in song2.rows])

    def test_gui_midi_mode_interactive(self) -> None:
        """Verify Tkinter GUI cleanly switches to MIDI mode and updates summary labels."""
        app = MusicGUI()
        try:
            app.update()
            app.show_midi_mode()
            app.update()
            self.assertEqual(app.current_view_mode, "midi")
            self.assertIn("Synthetic Orchestral Flight", app.lbl_dataset.cget("text"))
            self.assertIn("Columns: 20", app.lbl_summary.cget("text"))

            # Test Row 1 toggle
            app._toggle_constant_row_mode()
            app.update()
            self.assertEqual(app.current_constant_row_mode, "development")
            self.assertIn("Row 1 (Dev Profile)", app.lbl_constant_summary.cget("text"))

            app._toggle_constant_row_mode()
            app.update()
            self.assertEqual(app.current_constant_row_mode, "active_rows")
            self.assertIn("Row 1 (Constant)", app.lbl_constant_summary.cget("text"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
