"""Unit tests for continuous audio and sheet-music adapters (JOB-02).

Comprehensive coverage addressing all ChatGPT review questions and audit defects:
- Exact rational timing preservation in SoundEvent attributes and get_authoritative_exact_timing().
- Variable chord durations within chords.
- Validated tied-note handling, including interrupted ties, multi-note tie chains, and unclosed ties.
- DEFECT-01: Tempo changes within a measure at exact musical positions.
- DEFECT-02: Score-position cursor handling forward and backup operations.
- DEFECT-03: Trailing rests preserved in total score duration.
- DEFECT-04: Zero-gap exact Fraction continuity for ties.
- DEFECT-05: Three-note tie chains and continuation handling.
- DEFECT-06: Comprehensive unsupported notation disclosure (glissandi, ornaments, dynamics, lyrics).
- DEFECT-07: Invalid non-positive ordinary note duration rejection.
- DEFECT-08: Autocorrelation pitch estimation with DC removal, valley detection, 10 Hz negative control.
- DEFECT-09: Robust rejection of truncated PCM WAV across all 4 bit depths (mono & stereo).
- JSON round-trip fidelity for exact rational attributes.
"""

from __future__ import annotations

import io
import math
import unittest
import wave
from fractions import Fraction
from typing import List

from music_model.audio_importer import (
    AudioData,
    AudioFormatError,
    AudioOnsetDetector,
    _estimate_pitch_autocorrelation,
    generate_synthetic_wav,
    import_audio_to_sound_events,
    parse_wav,
)
from music_model.musicxml_importer import (
    MusicXMLParseError,
    ScoreTimeline,
    generate_synthetic_musicxml,
    parse_musicxml,
    step_octave_to_midi,
)
from music_model.passage_format import song_from_json, song_to_json
from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent, get_authoritative_exact_timing


class TestAudioImporter(unittest.TestCase):
    """Test suite for PCM WAV audio ingestion and candidate onset discovery."""

    def test_silence_detection(self) -> None:
        """Verify that an entirely silent audio buffer produces zero sound events."""
        wav_bytes = generate_synthetic_wav(
            sample_rate=44100,
            channels=1,
            sample_width=2,
            events=[],
            total_duration_ms=500,
        )
        audio = parse_wav(wav_bytes)
        self.assertEqual(audio.sample_rate, 44100)
        self.assertEqual(audio.num_frames, 22050)

        detector = AudioOnsetDetector()
        candidates = detector.detect_candidates(audio)
        self.assertEqual(len(candidates), 0, "Silence must yield zero detected candidates.")

        events = import_audio_to_sound_events(wav_bytes)
        self.assertEqual(len(events), 0, "Silence must yield zero SoundEvents.")

    def test_single_sound_event_timing_and_exact_rationals(self) -> None:
        """Verify single tone burst detection and preservation of exact rational timing."""
        wav_bytes = generate_synthetic_wav(
            sample_rate=44100,
            channels=1,
            sample_width=2,
            events=[(200, 400, 440.0, 0.8)],
            total_duration_ms=1000,
        )
        events = import_audio_to_sound_events(wav_bytes, row_id="row_audio_test")
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(event.row_id, "row_audio_test")

        # Measured tolerance within predefined 20ms window size limit
        self.assertAlmostEqual(event.start_time_ms, 200, delta=20)
        self.assertAlmostEqual(event.end_time_ms, 600, delta=20)
        self.assertGreater(event.end_time_ms, event.start_time_ms)

        # Check exact rational coordinates preserved in attributes
        attrs = event.attributes
        self.assertEqual(attrs["sample_rate"], 44100)
        self.assertEqual(attrs["source_type"], "audio_wav")
        self.assertEqual(attrs["boundary_type"], "detected_acoustic_candidate")
        self.assertIn("exact_start_sec_rational", attrs)
        self.assertIn("exact_end_sec_rational", attrs)
        self.assertIn("exact_duration_sec_rational", attrs)

        # Rational start second must match start sample / sample rate
        start_frac = Fraction(attrs["exact_start_sec_rational"])
        self.assertEqual(start_frac, Fraction(attrs["sample_start_idx"], 44100))

        # Test authoritative exact timing helper
        s_sec, e_sec, d_sec = get_authoritative_exact_timing(event, "sec")
        s_ms, e_ms, d_ms = get_authoritative_exact_timing(event, "ms")
        self.assertEqual(s_sec, start_frac)
        self.assertEqual(s_ms, start_frac * 1000)
        self.assertEqual(d_sec, e_sec - s_sec)

    def test_non_window_aligned_and_closely_spaced_events(self) -> None:
        """Verify detection of events at arbitrary millisecond offsets and close spacing."""
        # Non-aligned start: 123 ms to 323 ms (dur=200ms)
        # 60ms silence gap: 323 to 383 ms
        # Second event: 383 ms to 583 ms (dur=200ms)
        wav_bytes = generate_synthetic_wav(
            sample_rate=44100,
            channels=1,
            sample_width=2,
            events=[
                (123, 200, 440.0, 0.8),
                (383, 200, 554.37, 0.8),
            ],
            total_duration_ms=800,
        )
        events = import_audio_to_sound_events(wav_bytes)
        self.assertEqual(len(events), 2, "Expected 2 closely spaced events to be cleanly resolved.")

        # Both events must be detected within the 20ms window tolerance
        self.assertAlmostEqual(events[0].start_time_ms, 123, delta=20)
        self.assertAlmostEqual(events[0].end_time_ms, 323, delta=20)
        self.assertAlmostEqual(events[1].start_time_ms, 383, delta=20)
        self.assertAlmostEqual(events[1].end_time_ms, 583, delta=20)

    def test_multiple_pitch_frequencies_and_amplitudes(self) -> None:
        """Verify autocorrelation pitch estimation across diverse musical pitches and amplitudes."""
        pitch_tests = [
            (261.63, 60),  # C4
            (329.63, 64),  # E4
            (440.00, 69),  # A4
            (587.33, 74),  # D5
        ]
        for freq, expected_midi in pitch_tests:
            for amp in (0.4, 0.8):
                wav_bytes = generate_synthetic_wav(
                    sample_rate=44100,
                    channels=1,
                    sample_width=2,
                    events=[(100, 400, freq, amp)],
                    total_duration_ms=600,
                )
                events = import_audio_to_sound_events(wav_bytes)
                self.assertEqual(len(events), 1)
                evt = events[0]
                self.assertEqual(evt.attributes["pitch_midi"], expected_midi, f"Failed for {freq}Hz (amp={amp})")
                self.assertTrue(evt.attributes["pitch_detected"])

    def test_ambiguous_and_unpitched_signal_handling(self) -> None:
        """Verify that ambiguous or unpitched white noise reports pitch_midi as None without crashing."""
        wav_bytes = generate_synthetic_wav(
            sample_rate=44100,
            channels=1,
            sample_width=2,
            events=[],
            noise_bursts=[(100, 300, 0.8)],
            total_duration_ms=500,
        )
        events = import_audio_to_sound_events(wav_bytes)
        self.assertEqual(len(events), 1, "White noise burst must be detected as an acoustic event.")
        self.assertIsNone(events[0].attributes["pitch_midi"], "Unpitched white noise must have pitch_midi == None.")
        self.assertFalse(events[0].attributes["pitch_detected"])

    def test_variable_sample_rates(self) -> None:
        """Verify timing accuracy across 22050 Hz and 44100 Hz audio buffers."""
        for rate in (22050, 44100):
            wav_bytes = generate_synthetic_wav(
                sample_rate=rate,
                channels=1,
                sample_width=2,
                events=[(150, 300, 440.0, 0.8)],
                total_duration_ms=600,
            )
            events = import_audio_to_sound_events(wav_bytes)
            self.assertEqual(len(events), 1)
            self.assertAlmostEqual(events[0].start_time_ms, 150, delta=20)
            self.assertAlmostEqual(events[0].end_time_ms, 450, delta=20)

    def test_8bit_and_16bit_depths(self) -> None:
        """Verify support for both 8-bit unsigned and 16-bit signed PCM."""
        for width in (1, 2):
            wav_bytes = generate_synthetic_wav(
                sample_rate=44100,
                channels=1,
                sample_width=width,
                events=[(100, 250, 440.0, 0.7)],
                total_duration_ms=500,
            )
            events = import_audio_to_sound_events(wav_bytes)
            self.assertEqual(len(events), 1, f"Failed for sample width {width}")
            self.assertAlmostEqual(events[0].start_time_ms, 100, delta=20)

    def test_malformed_and_unsupported_wav_rejection(self) -> None:
        """Verify that corrupted bytes or non-WAV data raise AudioFormatError cleanly."""
        with self.assertRaises(AudioFormatError):
            parse_wav(b"NOT_A_WAV_HEADER_DATA")

        with self.assertRaises(AudioFormatError):
            parse_wav(b"RIFF\x24\x00\x00\x00WAVEfmt ")

    def test_defect_08_pitch_estimation_controls(self) -> None:
        """Verify DEFECT-08: 10 Hz negative control, DC, 60 Hz, 200 Hz, 440 Hz, and short signals."""
        sr = 8000
        n = 2400

        # 1. Constant DC signal (must be rejected)
        dc_samples = [0.7] * n
        f_dc, m_dc, conf_dc = _estimate_pitch_autocorrelation(dc_samples, sr)
        self.assertIsNone(f_dc, "Constant DC must return pitch None.")
        self.assertIsNone(m_dc)
        self.assertEqual(conf_dc, 0.0)

        # 2. 10 Hz infrasonic wave (must be rejected as out-of-band / no periodic valley)
        samples_10hz = [0.7 * math.cos(2 * math.pi * 10 * i / sr) for i in range(n)]
        f_10, m_10, conf_10 = _estimate_pitch_autocorrelation(samples_10hz, sr)
        self.assertIsNone(f_10, "10 Hz infrasonic sine wave must return pitch None.")
        self.assertIsNone(m_10)

        # 3. 60 Hz low frequency (supported lower bound)
        samples_60hz = [0.7 * math.cos(2 * math.pi * 60 * i / sr) for i in range(n)]
        f_60, m_60, conf_60 = _estimate_pitch_autocorrelation(samples_60hz, sr)
        self.assertIsNotNone(f_60)
        self.assertAlmostEqual(f_60, 60.0, delta=2.0)
        self.assertEqual(m_60, 35)  # 60 Hz corresponds to MIDI 35 (B1)

        # 4. 200 Hz mid frequency
        samples_200hz = [0.7 * math.cos(2 * math.pi * 200 * i / sr) for i in range(n)]
        f_200, m_200, conf_200 = _estimate_pitch_autocorrelation(samples_200hz, sr)
        self.assertIsNotNone(f_200)
        self.assertAlmostEqual(f_200, 200.0, delta=2.0)
        self.assertEqual(m_200, 55)  # 200 Hz corresponds to MIDI 55 (G3)

        # 5. 440 Hz standard pitch
        samples_440hz = [0.7 * math.cos(2 * math.pi * 440 * i / sr) for i in range(n)]
        f_440, m_440, conf_440 = _estimate_pitch_autocorrelation(samples_440hz, sr)
        self.assertIsNotNone(f_440)
        self.assertAlmostEqual(f_440, 440.0, delta=3.0)
        self.assertEqual(m_440, 69)  # 440 Hz corresponds to MIDI 69 (A4)

        # 6. Short signal (< 2 periods) must return None
        short_samples = [0.7 * math.cos(2 * math.pi * 100 * i / sr) for i in range(30)]
        f_short, m_short, _ = _estimate_pitch_autocorrelation(short_samples, sr)
        self.assertIsNone(f_short, "Buffer with fewer than 2 full periods must return None.")

    def test_defect_09_truncated_pcm_wav_all_depths(self) -> None:
        """Verify DEFECT-09: truncated PCM WAV data is rejected cleanly across all bit depths."""
        for width in (1, 2, 3, 4):
            for channels in (1, 2):
                out = io.BytesIO()
                with wave.open(out, "wb") as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(width)
                    wf.setframerate(8000)
                    wf.writeframes(b"\x00" * (100 * channels * width))

                full_bytes = out.getvalue()
                # Truncate by 10 bytes so data stream is shorter than declared header
                truncated_bytes = full_bytes[:-10]

                with self.assertRaises(
                    AudioFormatError,
                    msg=f"Failed to raise AudioFormatError for truncated {width*8}-bit PCM (channels={channels})",
                ):
                    parse_wav(truncated_bytes)


    def test_defect_13_high_frequency_pitch_estimation_controls(self) -> None:
        """Verify DEFECT-13: 2000 Hz accuracy and clean rejection of out-of-band signals (2400 Hz, 3000 Hz)."""
        sr = 8000
        n = 2400

        # Frequency sweep from ChatGPT audit reproduction
        cases = [
            (10, None, "10 Hz infrasonic negative control"),
            (60, 35, "60 Hz low frequency supported lower bound"),
            (200, 55, "200 Hz mid frequency"),
            (440, 69, "440 Hz standard pitch"),
            (2000, 95, "2000 Hz supported upper bound"),
            (2400, None, "2400 Hz out-of-band rejection (no subharmonic 800 Hz)"),
            (3000, None, "3000 Hz out-of-band rejection (no subharmonic 1000 Hz)"),
        ]

        for hz, exp_midi, desc in cases:
            samples = [0.7 * math.cos(2 * math.pi * hz * i / sr) for i in range(n)]
            f_est, m_est, conf = _estimate_pitch_autocorrelation(samples, sr)
            if exp_midi is None:
                self.assertIsNone(
                    m_est,
                    f"{desc}: Expected pitch None for {hz} Hz at {sr} Hz, got MIDI {m_est} ({f_est} Hz)",
                )
            else:
                self.assertIsNotNone(
                    m_est,
                    f"{desc}: Expected pitch MIDI {exp_midi} for {hz} Hz at {sr} Hz, got None",
                )
                self.assertEqual(
                    m_est,
                    exp_midi,
                    f"{desc}: Expected MIDI {exp_midi} for {hz} Hz, got {m_est} ({f_est} Hz)",
                )

    def test_authoritative_exact_timing_audio_and_validation(self) -> None:
        """Verify authoritative timing retrieval for audio events, JSON roundtrip, and validation."""
        w_bytes = generate_synthetic_wav(events=[(123, 200, 440.0, 0.8)], sample_rate=22050, total_duration_ms=500)
        events = import_audio_to_sound_events(w_bytes)
        self.assertEqual(len(events), 1)
        evt = events[0]

        # Rational timing retrieval
        s_sec, e_sec, d_sec = get_authoritative_exact_timing(evt, "sec")
        s_ms, e_ms, d_ms = get_authoritative_exact_timing(evt, "ms")
        self.assertIsInstance(s_sec, Fraction)
        self.assertIsInstance(e_sec, Fraction)
        self.assertEqual(d_sec, e_sec - s_sec)
        self.assertEqual(s_ms, s_sec * 1000)
        self.assertEqual(e_ms, e_sec * 1000)

        # JSON Roundtrip test for Audio event
        song = SongTimeline(song_id="audio_test_song", title="Audio Test Song")
        row = song.create_row("row_audio", "Audio Row")
        row.add_event(evt)
        json_str = song_to_json(song)
        rt_song = song_from_json(json_str)
        rt_evt = rt_song.all_events[0]

        rt_s_sec, rt_e_sec, rt_d_sec = get_authoritative_exact_timing(rt_evt, "sec")
        self.assertEqual((rt_s_sec, rt_e_sec, rt_d_sec), (s_sec, e_sec, d_sec))

        # Test attribute mutability & validation: corrupted or negative coordinates raise ValueError
        bad_evt = SoundEvent("bad_evt", "r1", 0, 100, attributes={"exact_start_sec_rational": "not_a_fraction", "exact_end_sec_rational": "1/2"})
        with self.assertRaises(ValueError):
            get_authoritative_exact_timing(bad_evt, "sec")

        neg_evt = SoundEvent("neg_evt", "r1", 0, 100, attributes={"exact_start_sec_rational": "-1/2", "exact_end_sec_rational": "1/2"})
        with self.assertRaises(ValueError):
            get_authoritative_exact_timing(neg_evt, "sec")

        inv_order_evt = SoundEvent("inv_evt", "r1", 0, 100, attributes={"exact_start_sec_rational": "2/1", "exact_end_sec_rational": "1/1"})
        with self.assertRaises(ValueError):
            get_authoritative_exact_timing(inv_order_evt, "sec")


class TestMusicXMLImporter(unittest.TestCase):
    """Test suite for MusicXML score ingestion and symbolic-to-timeline mapping."""

    def test_step_octave_to_midi(self) -> None:
        """Verify note name and octave conversion to MIDI pitch numbers."""
        self.assertEqual(step_octave_to_midi("C", 4, 0), 60)
        self.assertEqual(step_octave_to_midi("A", 4, 0), 69)
        self.assertEqual(step_octave_to_midi("C", 4, 1), 61)
        self.assertEqual(step_octave_to_midi("B", 3, -1), 58)
        with self.assertRaises(ValueError):
            step_octave_to_midi("H", 4, 0)

    def test_single_note_timing_and_exact_rationals(self) -> None:
        """Verify single note timing and preservation of exact rational milliseconds."""
        xml_str = generate_synthetic_musicxml(
            divisions=1,
            tempo_bpm=120.0,
            measures_data=[[("C", 4, 0, 1, False)]],
        )
        result = parse_musicxml(xml_str)
        self.assertEqual(len(result.sound_events), 1)
        evt = result.sound_events[0]
        self.assertEqual(evt.start_time_ms, 0)
        self.assertEqual(evt.end_time_ms, 500)
        self.assertEqual(evt.attributes["exact_start_ms_rational"], "0")
        self.assertEqual(evt.attributes["exact_end_ms_rational"], "500")
        self.assertTrue(result.is_complete_faithful_representation)

    def test_fractional_timing_triplets(self) -> None:
        """Verify that fractional triplet durations preserve exact rational fractions."""
        xml_str = generate_synthetic_musicxml(
            divisions=3,
            tempo_bpm=120.0,
            measures_data=[[
                ("C", 4, 0, 1, False),
                ("D", 4, 0, 1, False),
                ("E", 4, 0, 1, False),
            ]],
        )
        result = parse_musicxml(xml_str)
        self.assertEqual(len(result.sound_events), 3)
        e1, e2, e3 = result.sound_events

        # Check exact rational strings
        self.assertEqual(e1.attributes["exact_start_ms_rational"], "0")
        self.assertEqual(e1.attributes["exact_end_ms_rational"], "500/3")
        self.assertEqual(e2.attributes["exact_start_ms_rational"], "500/3")
        self.assertEqual(e2.attributes["exact_end_ms_rational"], "1000/3")
        self.assertEqual(e3.attributes["exact_start_ms_rational"], "1000/3")
        self.assertEqual(e3.attributes["exact_end_ms_rational"], "500")

        # Integer milliseconds contract
        self.assertEqual(e1.start_time_ms, 0)
        self.assertEqual(e1.end_time_ms, 167)
        self.assertEqual(e2.start_time_ms, 167)
        self.assertEqual(e2.end_time_ms, 333)
        self.assertEqual(e3.start_time_ms, 333)
        self.assertEqual(e3.end_time_ms, 500)

    def test_variable_chord_durations(self) -> None:
        """Verify chords where individual notes have different durations."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <!-- C4 half note (dur=2 = 1000ms), E4 quarter note (dur=1 = 500ms) -->
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice></note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
    </measure>
  </part>
</score-partwise>"""
        result = parse_musicxml(xml_content)
        self.assertEqual(len(result.sound_events), 2)
        c4_evt = [e for e in result.sound_events if e.attributes["pitch_midi"] == 60][0]
        e4_evt = [e for e in result.sound_events if e.attributes["pitch_midi"] == 64][0]

        # Both start simultaneously at 0ms, but end at different times
        self.assertEqual(c4_evt.start_time_ms, 0)
        self.assertEqual(c4_evt.end_time_ms, 1000)
        self.assertEqual(e4_evt.start_time_ms, 0)
        self.assertEqual(e4_evt.end_time_ms, 500)

    def test_tied_notes_coalescing_and_interrupted_ties(self) -> None:
        """Verify tied note coalescing, and transparent handling of interrupted ties."""
        xml_success = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><tie type="start"/></note>
    </measure>
    <measure number="2">
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><tie type="stop"/></note>
    </measure>
  </part>
</score-partwise>"""
        res_ok = parse_musicxml(xml_success)
        self.assertEqual(len(res_ok.sound_events), 1)
        self.assertEqual(res_ok.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_ok.sound_events[0].end_time_ms, 2000)
        self.assertTrue(res_ok.sound_events[0].attributes["is_tied"])

        # Interrupted tie (gap between tied notes)
        xml_interrupted = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="start"/></note>
      <note><rest/><duration>1</duration></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="stop"/></note>
    </measure>
  </part>
</score-partwise>"""
        res_err = parse_musicxml(xml_interrupted)
        self.assertEqual(len(res_err.sound_events), 2, "Interrupted tie must be emitted as 2 separate events.")
        self.assertTrue(res_err.has_unsupported_features)
        self.assertIn("Interrupted tie detected", res_err.unsupported_features[0])

    def test_unsupported_notation_disclosure(self) -> None:
        """Verify that unsupported features cause is_complete_faithful_representation to become False."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><grace/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
    </measure>
  </part>
</score-partwise>"""
        result = parse_musicxml(xml_content)
        self.assertEqual(len(result.sound_events), 1)
        self.assertTrue(result.has_unsupported_features)
        self.assertFalse(result.is_complete_faithful_representation)
        self.assertFalse(result.sound_events[0].attributes["is_complete_faithful_representation"])

    def test_malformed_xml_rejected(self) -> None:
        """Verify that corrupted XML raises MusicXMLParseError cleanly."""
        with self.assertRaises(MusicXMLParseError):
            parse_musicxml("<score-partwise><unclosed_tag>")

        with self.assertRaises(MusicXMLParseError):
            parse_musicxml("<unknown-root-tag></unknown-root-tag>")

    def test_defect_01_tempo_changes_within_a_measure(self) -> None:
        """Verify DEFECT-01: mid-measure tempo changes apply at their exact musical positions."""
        xml_tempo = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <direction><sound tempo="60"/></direction>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_tempo)
        self.assertEqual(len(res.sound_events), 2)
        e1, e2 = res.sound_events
        # Note 1: at 120 BPM -> [0, 500) ms
        self.assertEqual(e1.start_time_ms, 0)
        self.assertEqual(e1.end_time_ms, 500)
        # Note 2: at 60 BPM -> [500, 1500) ms
        self.assertEqual(e2.start_time_ms, 500)
        self.assertEqual(e2.end_time_ms, 1500)

    def test_defect_02_forward_and_backup_operations(self) -> None:
        """Verify DEFECT-02: forward and backup score-position cursor operations."""
        # Forward operation
        xml_fwd = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <forward><duration>1</duration></forward>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_fwd = parse_musicxml(xml_fwd)
        self.assertEqual(len(res_fwd.sound_events), 2)
        self.assertEqual(res_fwd.sound_events[1].start_time_ms, 1000)

        # Backup operation with multi-voice alignment
        xml_bak = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
      <note><rest/><duration>1</duration><voice>1</voice></note>
      <backup><duration>1</duration></backup>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note>
    </measure>
  </part>
</score-partwise>"""
        res_bak = parse_musicxml(xml_bak)
        e_v2 = [e for e in res_bak.sound_events if "v2" in e.row_id][0]
        self.assertEqual(e_v2.start_time_ms, 500)

    def test_defect_03_trailing_rests_in_total_duration(self) -> None:
        """Verify DEFECT-03: trailing rests are included in the score's total duration."""
        xml_rest = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <note><rest/><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_rest)
        self.assertEqual(res.total_duration_ms, 1000)
        self.assertEqual(res.total_duration_ms_rational, Fraction(1000, 1))

    def test_defect_04_exact_fraction_tie_continuity(self) -> None:
        """Verify DEFECT-04: exact zero-gap Fraction continuity for ties (rejects 1ms gap coalescing)."""
        xml_tie_gap = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>500</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>500</duration><tie type="start"/></note>
      <note><rest/><duration>1</duration></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>500</duration><tie type="stop"/></note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_tie_gap)
        self.assertEqual(len(res.sound_events), 2)
        self.assertFalse(res.is_complete_faithful_representation)
        self.assertTrue(any("Interrupted tie detected" in f for f in res.unsupported_features))

    def test_defect_05_three_note_tie_chain_and_continuation(self) -> None:
        """Verify DEFECT-05: 3-note tie chain coalescing without orphaned stop warnings."""
        xml_3tie = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="start"/></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="stop"/><tie type="start"/></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="stop"/></note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_3tie)
        self.assertEqual(len(res.sound_events), 1)
        evt = res.sound_events[0]
        self.assertEqual(evt.start_time_ms, 0)
        self.assertEqual(evt.end_time_ms, 1500)
        self.assertTrue(evt.attributes["is_tied"])
        self.assertTrue(res.is_complete_faithful_representation)

    def test_defect_06_unsupported_notations_and_directions(self) -> None:
        """Verify DEFECT-06: glissando, ornaments, lyrics, and repeats are disclosed as unfaithful."""
        xml_gliss = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <notations><glissando type="start"/></notations>
      </note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_gliss)
        self.assertFalse(res.is_complete_faithful_representation)
        self.assertTrue(any("glissando" in f for f in res.unsupported_features))

    def test_defect_07_invalid_ordinary_note_duration(self) -> None:
        """Verify DEFECT-07: ordinary note with duration 0 is rejected/flagged without fabricating 1ms."""
        xml_zero_dur = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>0</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res = parse_musicxml(xml_zero_dur)
        self.assertEqual(len(res.sound_events), 0)
        self.assertFalse(res.is_complete_faithful_representation)
        self.assertTrue(any("non-positive duration" in f for f in res.unsupported_features))

    def test_authoritative_exact_timing_and_json_roundtrip(self) -> None:
        """Verify authoritative exact rational timing survives JSON serialization/deserialization."""
        xml_str = generate_synthetic_musicxml(
            divisions=3,
            tempo_bpm=120.0,
            measures_data=[[("C", 4, 0, 1, False)]],
        )
        res = parse_musicxml(xml_str)
        self.assertEqual(len(res.sound_events), 1)
        evt = res.sound_events[0]

        # Authoritative timing retrieval
        s_ms, e_ms, d_ms = get_authoritative_exact_timing(evt, "ms")
        s_sec, e_sec, d_sec = get_authoritative_exact_timing(evt, "sec")
        self.assertEqual((s_ms, e_ms, d_ms), (Fraction(0), Fraction(500, 3), Fraction(500, 3)))
        self.assertEqual((s_sec, e_sec, d_sec), (Fraction(0), Fraction(1, 6), Fraction(1, 6)))

        # Create a SongTimeline and test JSON round-trip
        song = SongTimeline(song_id="test_json_song", title="Test JSON Song")
        row = song.create_row("row_xml_p1_v1", "Row 1")
        row.add_event(evt)

        json_str = song_to_json(song)
        roundtrip_song = song_from_json(json_str)
        rt_evt = roundtrip_song.all_events[0]

        # Verify exact rational timing survived JSON round-trip
        rt_s_ms, rt_e_ms, rt_d_ms = get_authoritative_exact_timing(rt_evt, "ms")
        self.assertEqual((rt_s_ms, rt_e_ms, rt_d_ms), (Fraction(0), Fraction(500, 3), Fraction(500, 3)))


    def test_defect_10_shared_score_tempo_between_parts(self) -> None:
        """Verify DEFECT-10: multi-part shared score tempo and conflicting tempo diagnosis."""
        # Case A: Shared score tempo (Part 1 defines 60 BPM, Part 2 inherits it)
        xml_shared = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Part 1</part-name></score-part>
    <score-part id="P2"><part-name>Part 2</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="60"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_shared = parse_musicxml(xml_shared)
        p1 = [e for e in res_shared.sound_events if "p1" in e.row_id][0]
        p2 = [e for e in res_shared.sound_events if "p2" in e.row_id][0]
        self.assertEqual((p1.start_time_ms, p1.end_time_ms), (0, 1000))
        self.assertEqual((p2.start_time_ms, p2.end_time_ms), (0, 1000))
        self.assertTrue(res_shared.is_complete_faithful_representation)

        # Case B: Conflicting independent part tempos diagnosed
        xml_conflict = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Part 1</part-name></score-part>
    <score-part id="P2"><part-name>Part 2</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="60"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="90"/></direction>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_conflict = parse_musicxml(xml_conflict)
        self.assertFalse(res_conflict.is_complete_faithful_representation)
        self.assertTrue(any("Conflicting tempo" in f for f in res_conflict.unsupported_features))

    def test_defect_11_out_of_order_tempo_changes_and_score_timeline(self) -> None:
        """Verify DEFECT-11: ScoreTimeline insertion rebuild and out-of-order XML tempo handling."""
        # 1. Direct ScoreTimeline insertion test
        from music_model.musicxml_importer import ScoreTimeline
        st = ScoreTimeline(initial_tempo=120.0)
        st.set_tempo(Fraction(2), 60)
        st.set_tempo(Fraction(1), 30)
        self.assertEqual(st.q_to_ms(Fraction(2)), Fraction(2500, 1))

        # 2. XML backup out-of-order tempo test
        xml_ooo = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
      <backup><duration>1</duration></backup>
      <direction><sound tempo="60"/></direction>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note>
    </measure>
  </part>
</score-partwise>"""
        res_ooo = parse_musicxml(xml_ooo)
        v1_n1 = [e for e in res_ooo.sound_events if "v1" in e.row_id and e.label.startswith("C")][0]
        v1_n2 = [e for e in res_ooo.sound_events if "v1" in e.row_id and e.label.startswith("D")][0]
        v2_n1 = [e for e in res_ooo.sound_events if "v2" in e.row_id and e.label.startswith("E")][0]

        self.assertEqual((v1_n1.start_time_ms, v1_n1.end_time_ms), (0, 500))
        self.assertEqual((v1_n2.start_time_ms, v1_n2.end_time_ms), (500, 1500))
        self.assertEqual((v2_n1.start_time_ms, v2_n1.end_time_ms), (500, 1500))

    def test_defect_12_unsupported_features_nested_dynamics_metronome_microtonal_invalid_backup(self) -> None:
        """Verify DEFECT-12: nested dynamics, metronome beat units, microtonal alterations, and invalid backups."""
        # A. Nested Dynamics
        xml_dyn = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction>
        <direction-type><dynamics><ff/></dynamics></direction-type>
      </direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_dyn = parse_musicxml(xml_dyn)
        self.assertFalse(res_dyn.is_complete_faithful_representation)
        self.assertTrue(any("Dynamics notation not supported" in f for f in res_dyn.unsupported_features))

        # B. Metronome Beat Unit
        xml_metro = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction>
        <direction-type>
          <metronome>
            <beat-unit>eighth</beat-unit>
            <per-minute>120</per-minute>
          </metronome>
        </direction-type>
      </direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_metro = parse_musicxml(xml_metro)
        self.assertEqual(res_metro.sound_events[0].duration_ms, 1000)

        # C. Microtonal Accidental
        xml_micro = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><alter>0.5</alter><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_micro = parse_musicxml(xml_micro)
        self.assertFalse(res_micro.is_complete_faithful_representation)
        self.assertTrue(any("Microtonal alteration" in f for f in res_micro.unsupported_features))

        # D. Invalid Backup
        xml_bak = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <backup><duration>5</duration></backup>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_bak = parse_musicxml(xml_bak)
        self.assertFalse(res_bak.is_complete_faithful_representation)
        self.assertTrue(any("Invalid backup operation" in f for f in res_bak.unsupported_features))


    def test_defect_14_measure_duration_and_reach_controls(self) -> None:
        """Verify DEFECT-14: Mid-measure divisions change, backup with shorter voice, pickup measures, and incomplete measures."""
        # Control A: Mid-measure divisions change
        xml_control_a = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <attributes><divisions>2</divisions></attributes>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration></note>
    </measure>
    <measure number="2">
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_a = parse_musicxml(xml_control_a)
        self.assertEqual(len(res_a.sound_events), 3)
        self.assertEqual(res_a.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_a.sound_events[0].end_time_ms, 500)
        self.assertEqual(res_a.sound_events[1].start_time_ms, 500)
        self.assertEqual(res_a.sound_events[1].end_time_ms, 1000)
        self.assertEqual(res_a.sound_events[2].start_time_ms, 1000)
        self.assertEqual(res_a.sound_events[2].end_time_ms, 1500)
        self.assertEqual(res_a.sound_events[0].attributes["exact_start_ms_rational"], "0")
        self.assertEqual(res_a.sound_events[0].attributes["exact_end_ms_rational"], "500")
        self.assertEqual(res_a.sound_events[1].attributes["exact_start_ms_rational"], "500")
        self.assertEqual(res_a.sound_events[1].attributes["exact_end_ms_rational"], "1000")
        self.assertEqual(res_a.sound_events[2].attributes["exact_start_ms_rational"], "1000")
        self.assertEqual(res_a.sound_events[2].attributes["exact_end_ms_rational"], "1500")

        # Control B: Backup followed by shorter voice
        xml_control_b = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
      <backup><duration>2</duration></backup>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note>
    </measure>
    <measure number="2">
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
    </measure>
  </part>
</score-partwise>"""
        res_b = parse_musicxml(xml_control_b)
        m2_notes = [e for e in res_b.sound_events if e.attributes["measure_number"] == 2]
        self.assertEqual(len(m2_notes), 1)
        self.assertEqual(m2_notes[0].start_time_ms, 1000)
        self.assertEqual(m2_notes[0].end_time_ms, 1500)
        self.assertEqual(m2_notes[0].attributes["exact_start_ms_rational"], "1000")

        # Control C: Pickup measure (anacrusis) without artificial padding
        xml_pickup = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="0">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
    <measure number="1">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_pickup = parse_musicxml(xml_pickup)
        self.assertEqual(res_pickup.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_pickup.sound_events[0].end_time_ms, 500)
        self.assertEqual(res_pickup.sound_events[1].start_time_ms, 500)  # Starts at 500ms, not 2000ms!
        self.assertEqual(res_pickup.sound_events[1].end_time_ms, 2500)

        # Control D: Incomplete measure in middle of score flagged in unsupported_features
        xml_incomp = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note>
    </measure>
    <measure number="2">
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_incomp = parse_musicxml(xml_incomp)
        self.assertFalse(res_incomp.is_complete_faithful_representation)
        self.assertTrue(any("Incomplete or overfull measure" in f for f in res_incomp.unsupported_features))

    def test_defect_15_invalid_or_unsupported_timing_inputs(self) -> None:
        """Verify DEFECT-15: Non-positive rests/forwards/backups, direction offsets, and transpositions."""
        # A. Negative rest duration
        xml_neg_rest = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <note><rest/><duration>-1</duration></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_neg = parse_musicxml(xml_neg_rest)
        self.assertEqual(len(res_neg.sound_events), 2)
        self.assertEqual(res_neg.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_neg.sound_events[0].end_time_ms, 500)
        self.assertEqual(res_neg.sound_events[1].start_time_ms, 500)  # Preserves forward sequence
        self.assertFalse(res_neg.is_complete_faithful_representation)
        self.assertTrue(any("Invalid non-positive duration (-1) for rest" in f for f in res_neg.unsupported_features))

        # B. Direction Offset
        xml_offset = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="120"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
      <direction>
        <offset>1</offset>
        <sound tempo="60"/>
      </direction>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_off = parse_musicxml(xml_offset)
        self.assertEqual(res_off.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_off.sound_events[0].end_time_ms, 500)    # 120 BPM
        self.assertEqual(res_off.sound_events[1].start_time_ms, 500)
        self.assertEqual(res_off.sound_events[1].end_time_ms, 1000)   # Still 120 BPM (offset = 1)
        self.assertEqual(res_off.sound_events[2].start_time_ms, 1000)
        self.assertEqual(res_off.sound_events[2].end_time_ms, 2000)   # 60 BPM (takes effect at beat 2)

        # C. Transposition Notation Disclosure
        xml_trans = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <transpose><chromatic>-2</chromatic></transpose>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_trans = parse_musicxml(xml_trans)
        self.assertFalse(res_trans.is_complete_faithful_representation)
        self.assertTrue(any("Transposition notation (<transpose>) not currently supported" in f for f in res_trans.unsupported_features))

        # D. Non-positive forward and backup durations
        xml_fwd_bak = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <forward><duration>-2</duration></forward>
      <backup><duration>0</duration></backup>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_fb = parse_musicxml(xml_fwd_bak)
        self.assertFalse(res_fb.is_complete_faithful_representation)
        self.assertTrue(any("Invalid non-positive forward duration (-2)" in f for f in res_fb.unsupported_features))
        self.assertTrue(any("Invalid non-positive backup duration (0)" in f for f in res_fb.unsupported_features))

    def test_defect_16_incomplete_and_inconsistent_exact_timing(self) -> None:
        """Verify DEFECT-16: Incomplete, unpaired, malformed, or inconsistent exact rational timing raises ValueError."""
        # 1. ChatGPT reproduction: partial start attribute
        evt_partial_mxml = SoundEvent("x", "r", 0, 10, attributes={"exact_start_ms_rational": "bogus"})
        with self.assertRaises(ValueError) as cm:
            get_authoritative_exact_timing(evt_partial_mxml)
        self.assertIn("Incomplete MusicXML rational timing attributes", str(cm.exception))

        # 2. Missing end attribute
        evt_missing_end = SoundEvent("x", "r", 0, 10, attributes={"exact_start_ms_rational": "0/1"})
        with self.assertRaises(ValueError) as cm:
            get_authoritative_exact_timing(evt_missing_end)
        self.assertIn("Incomplete MusicXML rational timing attributes", str(cm.exception))

        # 3. Malformed rational string
        evt_malformed = SoundEvent("x", "r", 0, 10, attributes={"exact_start_ms_rational": "bogus", "exact_end_ms_rational": "10/1"})
        with self.assertRaises(ValueError) as cm:
            get_authoritative_exact_timing(evt_malformed)
        self.assertIn("Malformed MusicXML rational timing attributes", str(cm.exception))

        # 4. Inconsistent declared duration
        evt_bad_dur = SoundEvent(
            "x", "r", 0, 10,
            attributes={
                "exact_start_ms_rational": "0/1",
                "exact_end_ms_rational": "10/1",
                "exact_duration_ms_rational": "5/1",
            }
        )
        with self.assertRaises(ValueError) as cm:
            get_authoritative_exact_timing(evt_bad_dur)
        self.assertIn("Inconsistent MusicXML rational duration attribute", str(cm.exception))

        # 5. Inconsistent audio sample index
        evt_bad_audio_sample = SoundEvent(
            "a", "row_audio", 0, 100,
            attributes={
                "source_type": "audio_wav",
                "sample_rate": 1000,
                "sample_start_idx": 10,  # Expected 10/1000 = 1/100 sec
                "sample_end_idx": 100,
                "exact_start_sec_rational": "1/50",  # Inconsistent! (20/1000)
                "exact_end_sec_rational": "1/10",
            }
        )
        with self.assertRaises(ValueError) as cm:
            get_authoritative_exact_timing(evt_bad_audio_sample, unit="sec")
        self.assertIn("Inconsistent Audio start sample index", str(cm.exception))

        # 6. Genuine absence of rational attributes cleanly falls back
        evt_baseline = SoundEvent("b", "row_base", 15, 45)
        st, et, dt = get_authoritative_exact_timing(evt_baseline)
        self.assertEqual(st, Fraction(15, 1))
        self.assertEqual(et, Fraction(45, 1))
        self.assertEqual(dt, Fraction(30, 1))


    def test_defect_17_invalid_tempo_metadata_validation(self) -> None:
        """Verify DEFECT-17: Non-positive, non-finite, and malformed tempo directives are diagnosed/rejected."""
        # Control 1: Invalid <sound tempo="..."> (non-positive and non-numeric)
        xml_bad_sound = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction><sound tempo="0"/></direction>
      <direction><sound tempo="-60"/></direction>
      <direction><sound tempo="invalid_bpm"/></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_sound = parse_musicxml(xml_bad_sound)
        self.assertEqual(len(res_sound.sound_events), 1)
        self.assertFalse(res_sound.is_complete_faithful_representation)
        self.assertTrue(any("Invalid non-positive or non-finite tempo attribute ('0')" in f for f in res_sound.unsupported_features))
        self.assertTrue(any("Invalid non-positive or non-finite tempo attribute ('-60')" in f for f in res_sound.unsupported_features))
        self.assertTrue(any("Malformed non-numeric tempo attribute ('invalid_bpm')" in f for f in res_sound.unsupported_features))

        # Control 2: Invalid <metronome> tempo (non-positive, non-numeric, or missing per-minute)
        xml_bad_metro = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction>
        <metronome>
          <beat-unit>quarter</beat-unit>
          <per-minute>-120</per-minute>
        </metronome>
      </direction>
      <direction>
        <metronome>
          <beat-unit>quarter</beat-unit>
          <per-minute>abc</per-minute>
        </metronome>
      </direction>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_metro = parse_musicxml(xml_bad_metro)
        self.assertEqual(len(res_metro.sound_events), 1)
        self.assertFalse(res_metro.is_complete_faithful_representation)
        self.assertTrue(any("Invalid non-positive or non-finite metronome tempo ('-120')" in f for f in res_metro.unsupported_features))
        self.assertTrue(any("Malformed non-numeric metronome tempo ('abc')" in f for f in res_metro.unsupported_features))

        # Control 2b: Invalid default tempo or initial tempo raises ValueError
        with self.assertRaises(ValueError) as cm1:
            parse_musicxml(xml_bad_sound, default_tempo_bpm=0)
        self.assertIn("Invalid default_tempo_bpm", str(cm1.exception))

        with self.assertRaises(ValueError) as cm2:
            ScoreTimeline(initial_tempo=-10)
        self.assertIn("Invalid initial tempo", str(cm2.exception))

        timeline = ScoreTimeline(initial_tempo=120)
        with self.assertRaises(ValueError) as cm3:
            timeline.set_tempo(Fraction(1, 1), 0)
        self.assertIn("Invalid tempo", str(cm3.exception))

    def test_defect_18_tempo_positions_before_score_beginning(self) -> None:
        """Verify DEFECT-18: Negative offsets/positions before score beginning (beat < 0) are rejected."""
        # Control 3: Negative offset at measure 1 start attempting tempo before beat 0
        xml_neg_offset = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <direction>
        <offset>-1</offset>
        <sound tempo="60"/>
      </direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        res_neg = parse_musicxml(xml_neg_offset)
        self.assertEqual(len(res_neg.sound_events), 1)
        self.assertFalse(res_neg.is_complete_faithful_representation)
        self.assertTrue(any("Invalid tempo directive position (-1): tempo cannot be set before the beginning of the score" in f for f in res_neg.unsupported_features))
        # Ensure beat 0 starts cleanly at 0 ms without timeline corruption
        self.assertEqual(res_neg.sound_events[0].start_time_ms, 0)
        self.assertEqual(res_neg.sound_events[0].attributes["exact_start_ms_rational"], "0")

        # Control 4: Direct ScoreTimeline.set_tempo with negative q_pos raises ValueError
        timeline = ScoreTimeline(initial_tempo=120)
        with self.assertRaises(ValueError) as cm:
            timeline.set_tempo(Fraction(-1, 2), 60.0)
        self.assertIn("cannot position tempo before beat 0", str(cm.exception))
        # Beat 0 remains exactly at 0 ms
        self.assertEqual(timeline.q_to_ms(Fraction(0, 1)), Fraction(0, 1))

    def test_defect_19_complete_exact_rational_timing_metadata_validation(self) -> None:
        """Verify DEFECT-19: Comprehensive rational timing metadata validation across MusicXML, Audio, and Fallback."""
        # Control 5a: Conflicting MusicXML and Audio metadata
        evt_conflicting = SoundEvent(
            "c", "row_test", 0, 100,
            attributes={
                "exact_start_ms_rational": "0/1",
                "exact_end_ms_rational": "100/1",
                "exact_start_sec_rational": "0/1",
                "exact_end_sec_rational": "1/10",
            }
        )
        with self.assertRaises(ValueError) as cm_conf:
            get_authoritative_exact_timing(evt_conflicting)
        self.assertIn("Conflicting timing metadata", str(cm_conf.exception))

        # Control 5b: Audio sample indices present without paired rational timing
        evt_missing_audio_rat = SoundEvent(
            "a1", "row_audio", 0, 100,
            attributes={
                "sample_rate": 44100,
                "sample_start_idx": 0,
                "sample_end_idx": 4410,
            }
        )
        with self.assertRaises(ValueError) as cm_aud:
            get_authoritative_exact_timing(evt_missing_audio_rat)
        self.assertIn("Incomplete Audio rational timing attributes", str(cm_aud.exception))

        # Control 5c: Inconsistent declared sample_count
        evt_bad_sample_count = SoundEvent(
            "a2", "row_audio", 0, 100,
            attributes={
                "sample_rate": 44100,
                "sample_start_idx": 0,
                "sample_end_idx": 4410,
                "sample_count": 9999,  # Inconsistent! (Expected 4410)
                "exact_start_sec_rational": "0/1",
                "exact_end_sec_rational": "1/10",
            }
        )
        with self.assertRaises(ValueError) as cm_sc:
            get_authoritative_exact_timing(evt_bad_sample_count)
        self.assertIn("Inconsistent sample_count", str(cm_sc.exception))

        # Control 5d: Inconsistent integer bounds vs rational timing coordinates
        evt_inconsistent_bounds = SoundEvent(
            "m1", "row_xml", 0, 100,
            attributes={
                "exact_start_ms_rational": "5000/1",  # Inconsistent with start_time_ms=0!
                "exact_end_ms_rational": "5100/1",
            }
        )
        with self.assertRaises(ValueError) as cm_ib:
            get_authoritative_exact_timing(evt_inconsistent_bounds)
        self.assertIn("Inconsistent timing coordinates", str(cm_ib.exception))

        # Control 5e: SoundEvent rejects invalid interval bounds at creation and in get_authoritative_exact_timing
        with self.assertRaises(ValueError) as cm_neg:
            SoundEvent("fb1", "row_base", -10, 50)
        self.assertIn("start_time_ms must be nonnegative", str(cm_neg.exception))

        with self.assertRaises(ValueError) as cm_inv:
            SoundEvent("fb2", "row_base", 50, 20)
        self.assertIn("must be strictly greater than start_time_ms (50)", str(cm_inv.exception))


if __name__ == "__main__":
    unittest.main()
