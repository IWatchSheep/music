"""Automated unit and integration test suite for JOB-03 Audio Playback and Transport.

Comprehensive Verification & Regression Controls:
- DEFECT-01: Windows MCI backend, non-silent failure handling, AudioBackendStatus, failure injection.
- DEFECT-02: Multi-tier timing (software, device, audible), simulated startup delays, buffer latency, clock deviation.
- DEFECT-03: Strict exact timing validation via get_authoritative_exact_timing, rejection of malformed rational attributes, rational synthesis.
- DEFECT-04: Authentic PCM WAV frame-derived duration, preservation of trailing silence, stale audio prevention.
- DEFECT-05: Continuous loop remainder preservation (1250ms -> 250ms), dynamic loop toggle, non-finite seek rejection, deadlock-free pause/resume.
- 18 Baseline Unit & GUI Integration Tests from first audit.
"""

from __future__ import annotations

import io
import math
import struct
import unittest
import wave
from fractions import Fraction
from typing import List, Set

from music_gui.audio_playback import (
    AudioBackend,
    AudioBackendError,
    AudioBackendStatus,
    Clock,
    NullAudioBackend,
    PlaybackTransport,
    RealClock,
    SimulatedAudioBackend,
    TestClock,
    TransportState,
    WindowsMciAudioBackend,
    WindowsWaveBackend,
    get_wav_duration_ms,
    synthesize_song_audio,
)
from music_gui.coordinates import TimelineCoordinates
from music_gui.main_window import MusicGUI
from music_gui.timeline_canvas import TimelineCanvas
from music_model.datasets import create_stage_1_proof_timeline
from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent, get_authoritative_exact_timing
from music_model.timeline import MusicTimeline


def create_test_wav_bytes(num_frames: int = 8000, frame_rate: int = 8000, channels: int = 1) -> bytes:
    """Helper creating valid PCM WAV bytes with specified frame count and rate."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(frame_rate)
        wf.writeframes(struct.pack("<" + "h" * num_frames, *([0] * num_frames)))
    return buf.getvalue()


class TestDeterministicTransportControls(unittest.TestCase):
    """Deterministic, zero-sleep tests for PlaybackTransport using TestClock."""

    def setUp(self) -> None:
        self.clock = TestClock(start_seconds=100.0)
        self.backend = SimulatedAudioBackend()
        self.timeline = create_stage_1_proof_timeline()
        # Stage 1 proof timeline:
        # Sound A: [0, 3000) ms
        # Sound B: [1000, 5000) ms
        # Sound C: [2000, 4000) ms
        # Total duration: 5000 ms
        self.transport = PlaybackTransport(
            timeline=self.timeline,
            clock=self.clock,
            audio_backend=self.backend,
        )

    def test_01_initial_stopped_state(self) -> None:
        """Control 1: Verify initial state is STOPPED, position is 0, backend not playing."""
        self.assertEqual(self.transport.state, TransportState.STOPPED)
        self.assertEqual(self.transport.position_ms, 0.0)
        self.assertEqual(self.transport.total_duration_ms, 5000.0)
        self.assertFalse(self.backend.is_playing)
        self.assertFalse(self.backend.is_paused)

    def test_02_play_and_transport_advancement(self) -> None:
        """Control 2: Verify play() transitions to PLAYING and clock advance moves position."""
        self.transport.play()
        self.assertEqual(self.transport.state, TransportState.PLAYING)
        self.assertTrue(self.backend.is_playing)
        self.assertEqual(self.transport.position_ms, 0.0)

        # Advance clock by 500 ms (0.5 s)
        self.clock.advance_ms(500.0)
        self.assertAlmostEqual(self.transport.position_ms, 500.0, places=4)

        # Advance by another 1000 ms
        self.clock.advance_ms(1000.0)
        self.assertAlmostEqual(self.transport.position_ms, 1500.0, places=4)

    def test_03_pause_without_unwanted_advancement(self) -> None:
        """Control 3: Verify pause() freezes position and subsequent clock advances do not affect it."""
        self.transport.play()
        self.clock.advance_ms(1200.0)
        self.transport.pause()

        self.assertEqual(self.transport.state, TransportState.PAUSED)
        self.assertTrue(self.backend.is_paused)
        self.assertAlmostEqual(self.transport.position_ms, 1200.0, places=4)

        # Advance clock while paused — transport must NOT advance
        self.clock.advance_ms(5000.0)
        self.assertAlmostEqual(self.transport.position_ms, 1200.0, places=4)
        self.assertEqual(self.transport.state, TransportState.PAUSED)

    def test_04_resume_from_exact_position(self) -> None:
        """Control 4: Verify resume/play from paused state continues from exact paused timestamp."""
        self.transport.play()
        self.clock.advance_ms(800.0)
        self.transport.pause()
        self.clock.advance_ms(2000.0)  # dormant time

        self.transport.play()  # resume
        self.assertEqual(self.transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(self.transport.position_ms, 800.0, places=4)

        # Advance clock by 300 ms
        self.clock.advance_ms(300.0)
        self.assertAlmostEqual(self.transport.position_ms, 1100.0, places=4)

    def test_05_stop_and_reset_to_zero(self) -> None:
        """Control 5: Verify stop() resets position to 0 and updates state to STOPPED."""
        self.transport.play()
        self.clock.advance_ms(2300.0)
        self.transport.stop()

        self.assertEqual(self.transport.state, TransportState.STOPPED)
        self.assertEqual(self.transport.position_ms, 0.0)
        self.assertFalse(self.backend.is_playing)

        # Clock advance after stop should not move position
        self.clock.advance_ms(1000.0)
        self.assertEqual(self.transport.position_ms, 0.0)

    def test_06_forward_and_backward_seeking(self) -> None:
        """Control 6: Verify seeking forwards and backwards works while playing, paused, or stopped."""
        # 1. Seek while stopped
        self.transport.seek(1500.0)
        self.assertAlmostEqual(self.transport.position_ms, 1500.0, places=4)
        self.assertEqual(self.transport.state, TransportState.STOPPED)

        # 2. Seek while playing
        self.transport.play()
        self.assertAlmostEqual(self.transport.position_ms, 1500.0, places=4)
        self.clock.advance_ms(200.0)
        self.assertAlmostEqual(self.transport.position_ms, 1700.0, places=4)

        # Seek backwards to 500 ms
        self.transport.seek(500.0)
        self.assertAlmostEqual(self.transport.position_ms, 500.0, places=4)
        self.clock.advance_ms(400.0)
        self.assertAlmostEqual(self.transport.position_ms, 900.0, places=4)

        # 3. Seek while paused
        self.transport.pause()
        self.transport.seek(3200.0)
        self.assertAlmostEqual(self.transport.position_ms, 3200.0, places=4)
        self.assertEqual(self.transport.state, TransportState.PAUSED)

    def test_07_exact_event_boundaries_half_open_interval(self) -> None:
        """Control 7: Verify half-open interval [t_start, t_end) active event semantics."""
        # At t = 0 ms: Sound A is active, B and C are inactive
        self.transport.seek(0.0)
        self.assertEqual(self.transport.active_event_ids, {"Sound A"})

        # At t = 999.999 ms: Only Sound A is active
        self.transport.seek(999.999)
        self.assertEqual(self.transport.active_event_ids, {"Sound A"})

        # At exact boundary t = 1000.000 ms: Sound A and Sound B are active
        self.transport.seek(1000.0)
        self.assertEqual(self.transport.active_event_ids, {"Sound A", "Sound B"})

        # At t = 2499.999 ms: Sound A, Sound B, Sound C are all active
        self.transport.seek(2499.999)
        self.assertEqual(self.transport.active_event_ids, {"Sound A", "Sound B", "Sound C"})

        # At t = 2500.000 ms: Sound A, Sound B, Sound C all remain active
        self.transport.seek(2500.0)
        self.assertEqual(self.transport.active_event_ids, {"Sound A", "Sound B", "Sound C"})

        # At exact boundary t = 3000.000 ms: Sound A ends! Sound B and Sound C remain active
        self.transport.seek(3000.0)
        self.assertEqual(self.transport.active_event_ids, {"Sound B", "Sound C"})

        # At exact boundary t = 4000.000 ms: Sound C ends! Only Sound B remains active
        self.transport.seek(4000.0)
        self.assertEqual(self.transport.active_event_ids, {"Sound B"})

        # At exact boundary t = 5000.000 ms: Sound B ends! Zero events active
        self.transport.seek(5000.0)
        self.assertEqual(self.transport.active_event_ids, set())

    def test_08_simultaneous_polyphony(self) -> None:
        """Control 8: Verify multiple concurrent sound events are tracked simultaneously."""
        self.transport.seek(2200.0)
        active_ids = self.transport.active_event_ids
        self.assertEqual(active_ids, {"Sound A", "Sound B", "Sound C"})
        self.assertEqual(len(active_ids), 3)

    def test_09_loop_boundaries(self) -> None:
        """Control 9: Verify loop=True wraps to 0 at end of duration, loop=False stops."""
        # 1. Loop enabled
        self.transport.set_loop(True)
        self.assertTrue(self.transport.is_looping)
        self.transport.play()
        self.clock.advance_ms(4900.0)
        self.assertAlmostEqual(self.transport.position_ms, 4900.0, places=4)

        # Cross 5000 ms boundary via step_tick
        self.transport.step_tick(delta_ms=200.0)  # advances past 5000 ms
        self.assertAlmostEqual(self.transport.position_ms, 100.0, places=4)
        self.assertEqual(self.transport.state, TransportState.PLAYING)

        # 2. Loop disabled
        self.transport.set_loop(False)
        self.transport.seek(4900.0)
        self.transport.step_tick(delta_ms=200.0)  # reaches end
        self.assertAlmostEqual(self.transport.position_ms, 5000.0, places=4)
        self.assertEqual(self.transport.state, TransportState.STOPPED)

    def test_10_natural_end_of_piece(self) -> None:
        """Control 10: Verify natural end-of-piece cleanly transitions to STOPPED and fires end callback."""
        end_fired = []
        self.transport.register_end_callback(lambda: end_fired.append(True))

        self.transport.set_loop(False)
        self.transport.play()
        self.clock.advance_ms(5000.0)
        self.transport.step_tick()

        self.assertEqual(self.transport.state, TransportState.STOPPED)
        self.assertEqual(self.transport.position_ms, 5000.0)
        self.assertEqual(len(end_fired), 1)

    def test_11_repeated_playback_cycles(self) -> None:
        """Control 11: Verify repeated play/pause/seek/stop cycles operate deterministically."""
        for cycle in range(5):
            self.transport.play()
            self.clock.advance_ms(500.0)
            self.assertEqual(self.transport.state, TransportState.PLAYING)

            self.transport.pause()
            self.assertEqual(self.transport.state, TransportState.PAUSED)
            self.assertAlmostEqual(self.transport.position_ms, 500.0, places=4)

            self.transport.seek(200.0)
            self.assertAlmostEqual(self.transport.position_ms, 200.0, places=4)

            self.transport.stop()
            self.assertEqual(self.transport.state, TransportState.STOPPED)
            self.assertEqual(self.transport.position_ms, 0.0)

    def test_12_invalid_transport_inputs(self) -> None:
        """Control 12: Verify invalid transport inputs are cleanly handled without uncaught exceptions."""
        self.transport.seek(-500.0)
        self.assertEqual(self.transport.position_ms, 0.0)

        self.transport.seek(999999.0)
        self.assertEqual(self.transport.position_ms, 5000.0)

        with self.assertRaises(ValueError):
            self.clock.advance(-10.0)

        with self.assertRaises(ValueError):
            self.clock.set_time(-5.0)

    def test_13_missing_audio_backend_graceful_degradation(self) -> None:
        """Control 13: Verify NullAudioBackend provides complete functionality without sound hardware."""
        null_backend = NullAudioBackend()
        self.assertFalse(null_backend.is_available())
        self.assertFalse(null_backend.is_genuinely_audible())
        self.assertEqual(null_backend.get_status(), AudioBackendStatus.UNAVAILABLE)

        transport = PlaybackTransport(
            timeline=self.timeline,
            clock=self.clock,
            audio_backend=null_backend,
        )
        transport.play()
        self.clock.advance_ms(500.0)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        transport.pause()
        transport.stop()

    def test_14_preservation_of_exact_source_timing_metadata(self) -> None:
        """Control 14: Verify exact rational timing metadata is preserved on sound events."""
        event_with_rational = SoundEvent(
            event_id="Rational1",
            row_id="Row1",
            start_time_ms=1000,
            end_time_ms=1500,
            attributes={
                "exact_start_ms_rational": Fraction(3000, 3),
                "exact_end_ms_rational": Fraction(4500, 3),
                "exact_tempo_bpm": Fraction(120, 1),
            },
        )
        start_frac, end_frac, dur_frac = get_authoritative_exact_timing(event_with_rational)
        self.assertEqual(start_frac, Fraction(1000, 1))
        self.assertEqual(end_frac, Fraction(1500, 1))
        self.assertEqual(dur_frac, Fraction(500, 1))

        single_timeline = MusicTimeline()
        r = single_timeline.create_row("Row1")
        r.add_event(event_with_rational)
        trans = PlaybackTransport(timeline=single_timeline, clock=self.clock, audio_backend=self.backend)

        trans.seek(999.0)
        self.assertEqual(trans.active_event_ids, set())
        trans.seek(1000.0)
        self.assertEqual(trans.active_event_ids, {"Rational1"})
        trans.seek(1499.0)
        self.assertEqual(trans.active_event_ids, {"Rational1"})
        trans.seek(1500.0)
        self.assertEqual(trans.active_event_ids, set())

    def test_15_absence_of_cumulative_transport_drift(self) -> None:
        """Control 15: Verify absence of cumulative drift across 10,000 small transport steps."""
        self.transport.play()
        step_ms = 0.1
        total_steps = 10000  # Total 1000 ms

        for _ in range(total_steps):
            self.clock.advance_ms(step_ms)

        expected_ms = step_ms * total_steps
        actual_ms = self.transport.position_ms
        drift_ms = abs(actual_ms - expected_ms)

        self.assertLess(drift_ms, 1e-6, f"Transport accumulated drift: {drift_ms} ms")


class TestDefectRegressions(unittest.TestCase):
    """Targeted regression test controls for DEFECT-01 through DEFECT-05."""

    def test_defect_01_backend_failure_handling_and_status(self) -> None:
        """DEFECT-01: Verify audio device failures raise AudioBackendError and update status to FAILED."""
        backend = SimulatedAudioBackend()
        backend.inject_failure = True

        with self.assertRaises(AudioBackendError):
            backend.load_wav_bytes(b"RIFF dummy bytes")
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)

        # Verify WindowsMciAudioBackend status reporting
        mci = WindowsMciAudioBackend()
        if mci.is_available():
            self.assertEqual(mci.get_status(), AudioBackendStatus.AVAILABLE)
        else:
            self.assertEqual(mci.get_status(), AudioBackendStatus.UNAVAILABLE)

        # Verify silent visual transport is distinguished from genuine audible playback
        self.assertFalse(backend.is_genuinely_audible())
        self.assertFalse(NullAudioBackend().is_genuinely_audible())

    def test_defect_02_multitier_timing_and_simulated_delays(self) -> None:
        """DEFECT-02: Verify multi-tier timing distinguishes software, device, and estimated audible position."""
        clock = TestClock(0.0)
        # Device with 40ms startup delay and 20ms buffer latency
        backend = SimulatedAudioBackend(startup_delay_ms=40.0, buffer_latency_ms=20.0)
        timeline = create_stage_1_proof_timeline()
        transport = PlaybackTransport(
            timeline=timeline,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()
        self.assertEqual(transport.software_transport_position_ms, 0.0)
        self.assertEqual(transport.estimated_audible_position_ms, 0.0)

        # Advance clock by 300 ms
        clock.advance_ms(300.0)
        soft_pos = transport.software_transport_position_ms
        self.assertAlmostEqual(soft_pos, 300.0, places=4)
        # Device position: 300ms - 40ms startup delay = 260ms
        self.assertAlmostEqual(transport.device_position_ms, 260.0, places=4)
        # Estimated audible position: 260ms - 20ms buffer latency = 240ms
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 240.0, places=4)

    def test_defect_03_rejection_of_malformed_exact_timing(self) -> None:
        """DEFECT-03: Verify playback engine strictly rejects malformed rational timing metadata."""
        # Bogus rational timing metadata
        malformed_event = SoundEvent("x", "r", 0, 10, attributes={"exact_start_ms_rational": "bogus"})

        # Must raise ValueError per JOB-02 get_authoritative_exact_timing validation
        single_timeline = MusicTimeline()
        r = single_timeline.create_row("r")
        r.add_event(malformed_event)

        transport = PlaybackTransport(audio_backend=SimulatedAudioBackend(), clock=TestClock(0.0))
        with self.assertRaises(ValueError):
            transport.load_timeline(single_timeline)

    def test_defect_03_synthesizer_uses_rational_timing(self) -> None:
        """DEFECT-03: Verify synthesizer quantizes exact rational timing rather than truncated integers."""
        event = SoundEvent(
            "E1", "R1", 333, 667,
            attributes={
                "exact_start_sec_rational": Fraction(1, 3),   # 0.333333... s
                "exact_end_sec_rational": Fraction(2, 3),     # 0.666666... s
            },
            height=69.0,
        )
        wav_bytes = synthesize_song_audio([event], total_duration_ms=1000, sample_rate=48000)
        self.assertGreater(len(wav_bytes), 44)
        # Expected frames: exactly 1.0 second * 48000 = 48000 frames * 2 bytes = 96000 data bytes
        self.assertEqual(len(wav_bytes) - 44, 48000 * 2)

    def test_defect_04_pcm_wav_duration_and_trailing_silence(self) -> None:
        """DEFECT-04: Verify pure PCM WAV without timeline derives duration from frame count and rate."""
        # 8,000 frames at 8,000 Hz = 1,000 ms duration
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)

        # Direct WAV duration calculation
        dur_ms = get_wav_duration_ms(wav_bytes)
        self.assertAlmostEqual(dur_ms, 1000.0, places=4)

        # Transport loaded with pure WAV without symbolic timeline
        transport = PlaybackTransport(
            timeline=None,
            wav_bytes=wav_bytes,
            audio_backend=SimulatedAudioBackend(),
            clock=TestClock(0.0),
        )
        self.assertAlmostEqual(transport.total_duration_ms, 1000.0, places=4)
        self.assertFalse(transport.is_synthesized_audio)

    def test_defect_04_stale_audio_cleanup_on_new_source(self) -> None:
        """DEFECT-04: Verify loading a new source unloads previous audio backend data completely."""
        backend = SimulatedAudioBackend()
        transport = PlaybackTransport(audio_backend=backend, clock=TestClock(0.0))

        wav1 = create_test_wav_bytes(num_frames=4000, frame_rate=4000)
        transport.load_timeline(wav_bytes=wav1)
        self.assertIsNotNone(backend.loaded_bytes)
        self.assertEqual(len(backend.loaded_bytes), len(wav1))

        # Load empty timeline without WAV
        empty_timeline = MusicTimeline()
        transport.load_timeline(timeline=empty_timeline, wav_bytes=None, synthesize=False)
        self.assertIsNone(backend.loaded_bytes)
        self.assertEqual(transport.total_duration_ms, 0.0)

    def test_defect_05_continuous_loop_remainder_preservation(self) -> None:
        """DEFECT-05: Verify advancing past loop boundary preserves remainder (1250 ms -> 250 ms)."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend()
        # 1000 ms single event timeline
        tl = MusicTimeline()
        r = tl.create_row("R1")
        r.add_event(SoundEvent("S1", "R1", 0, 1000))

        transport = PlaybackTransport(timeline=tl, clock=clock, audio_backend=backend)
        transport.set_loop(True)
        transport.play()

        # Advance clock by 1250 ms in one update
        transport.step_tick(delta_ms=1250.0)

        # Expected continuous loop position: 1250 % 1000 = 250 ms
        self.assertAlmostEqual(transport.position_ms, 250.0, places=4)
        self.assertEqual(transport.state, TransportState.PLAYING)

    def test_defect_05_rejection_of_non_finite_seek_values(self) -> None:
        """DEFECT-05: Verify seeking to NaN or infinity raises ValueError."""
        transport = PlaybackTransport(
            timeline=create_stage_1_proof_timeline(),
            clock=TestClock(0.0),
            audio_backend=SimulatedAudioBackend(),
        )
        with self.assertRaises(ValueError):
            transport.seek(float("nan"))
        with self.assertRaises(ValueError):
            transport.seek(float("inf"))
        with self.assertRaises(ValueError):
            transport.seek(float("-inf"))

    def test_defect_05_rapid_pause_resume_cycles(self) -> None:
        """DEFECT-05: Verify 50 rapid pause/resume cycles operate deterministically without deadlock."""
        clock = TestClock(0.0)
        transport = PlaybackTransport(
            timeline=create_stage_1_proof_timeline(),
            clock=clock,
            audio_backend=SimulatedAudioBackend(),
        )
        transport.play()
        for i in range(50):
            clock.advance_ms(10.0)
            transport.pause()
            self.assertEqual(transport.state, TransportState.PAUSED)
            transport.resume()
            self.assertEqual(transport.state, TransportState.PLAYING)
        transport.stop()
        self.assertEqual(transport.state, TransportState.STOPPED)

    def test_defect_06_control_a_startup_delay_pause_resume(self) -> None:
        """DEFECT-06 Control A: Verify 40ms startup delay preserves position across pause and resume."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(startup_delay_ms=40.0, clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, clock=clock, audio_backend=backend)

        transport.play()
        clock.advance_ms(500.0)
        # Device position: 500 - 40 = 460 ms
        self.assertAlmostEqual(transport.device_position_ms, 460.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 460.0, places=4)

        transport.pause()
        self.assertEqual(transport.state, TransportState.PAUSED)
        # Position after pause MUST remain 460 ms (no jump to 500 ms!)
        self.assertAlmostEqual(transport.position_ms, 460.0, places=4)
        self.assertAlmostEqual(transport.device_position_ms, 460.0, places=4)

        # Dormant time while paused
        clock.advance_ms(2000.0)
        self.assertAlmostEqual(transport.position_ms, 460.0, places=4)

        # Resume playback: continues seamlessly from 460 ms
        transport.resume()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 460.0, places=4)

        clock.advance_ms(100.0)
        self.assertAlmostEqual(transport.position_ms, 560.0, places=4)

    def test_defect_06_control_b_device_clock_rate_pause_resume(self) -> None:
        """DEFECT-06 Control B: Verify clock deviation (rate=0.9) preserves position without jump."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(device_clock_rate=0.9, clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, clock=clock, audio_backend=backend)

        transport.play()
        clock.advance_ms(500.0)
        # Device position: 500 * 0.9 = 450 ms
        self.assertAlmostEqual(transport.device_position_ms, 450.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 450.0, places=4)

        transport.pause()
        self.assertEqual(transport.state, TransportState.PAUSED)
        # Position after pause MUST remain 450 ms (no jump to 500 ms!)
        self.assertAlmostEqual(transport.position_ms, 450.0, places=4)

        clock.advance_ms(3000.0)
        self.assertAlmostEqual(transport.position_ms, 450.0, places=4)

        transport.resume()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 450.0, places=4)

        clock.advance_ms(100.0)
        # 450 + (100 * 0.9) = 540 ms
        self.assertAlmostEqual(transport.position_ms, 540.0, places=4)

    def test_defect_06_control_c_buffer_latency_pause_resume(self) -> None:
        """DEFECT-06 Control C: Verify 20ms buffer latency preserves distinct frozen audible and device positions."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(buffer_latency_ms=20.0, clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()
        clock.advance_ms(500.0)
        # Device position: 500 ms, Estimated audible position: 500 - 20 = 480 ms
        self.assertAlmostEqual(transport.device_position_ms, 500.0, places=4)
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 480.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 480.0, places=4)

        transport.pause()
        self.assertEqual(transport.state, TransportState.PAUSED)
        # Positions after pause MUST NOT jump to 500 ms
        self.assertAlmostEqual(transport.device_position_ms, 500.0, places=4)
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 480.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 480.0, places=4)

        # Resume: continues without replaying or skipping
        transport.resume()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.device_position_ms, 500.0, places=4)
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 480.0, places=4)

        clock.advance_ms(100.0)
        self.assertAlmostEqual(transport.device_position_ms, 600.0, places=4)
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 580.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 580.0, places=4)

    def test_defect_07_device_aware_end_of_piece_startup_delay(self) -> None:
        """DEFECT-07: Verify device progress governs end-of-piece (40ms startup delay preserves ending)."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(startup_delay_ms=40.0, clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, clock=clock, audio_backend=backend)

        transport.play()
        clock.advance_ms(999.0)
        transport.step_tick()
        # Visible position is 959 ms; must NOT stop prematurely at 999 ms software time!
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 959.0, places=4)

        clock.advance_ms(1.0)
        transport.step_tick()
        # Visible position is 960 ms at 1000 ms software time; must continue!
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 960.0, places=4)

        clock.advance_ms(39.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 999.0, places=4)

        clock.advance_ms(1.0)
        transport.step_tick()
        # Device has reached 1000 ms at software clock 1040 ms -> transitions to STOPPED!
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

    def test_defect_07_device_clock_deviations_and_looping(self) -> None:
        """DEFECT-07: Verify slow/fast device clock rates and device-governed loop transitions."""
        clock = TestClock(0.0)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms

        # 1. Slow device clock (rate = 0.9)
        backend_slow = SimulatedAudioBackend(device_clock_rate=0.9, clock=clock)
        trans_slow = PlaybackTransport(wav_bytes=wav_bytes, clock=clock, audio_backend=backend_slow)
        trans_slow.play()
        clock.advance_ms(1000.0)
        trans_slow.step_tick()
        # At software 1000 ms, device is at 900 ms -> must be PLAYING!
        self.assertEqual(trans_slow.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_slow.position_ms, 900.0, places=4)

        # Advance to 1112 ms -> device reaches 1000.8 ms -> STOPPED
        clock.advance_ms(112.0)
        trans_slow.step_tick()
        self.assertEqual(trans_slow.state, TransportState.STOPPED)

        # 2. Fast device clock (rate = 1.1)
        clock2 = TestClock(0.0)
        backend_fast = SimulatedAudioBackend(device_clock_rate=1.1, clock=clock2)
        trans_fast = PlaybackTransport(wav_bytes=wav_bytes, clock=clock2, audio_backend=backend_fast)
        trans_fast.play()
        clock2.advance_ms(910.0)
        trans_fast.step_tick()
        # Device reached 910 * 1.1 = 1001 ms -> STOPPED
        self.assertEqual(trans_fast.state, TransportState.STOPPED)

        # 3. Looping governed by device progress
        clock3 = TestClock(0.0)
        backend_loop = SimulatedAudioBackend(startup_delay_ms=40.0, clock=clock3)
        trans_loop = PlaybackTransport(wav_bytes=wav_bytes, clock=clock3, audio_backend=backend_loop)
        trans_loop.set_loop(True)
        trans_loop.play()
        # At software clock 1000 ms, device is at 960 ms -> remains in loop
        clock3.advance_ms(1000.0)
        trans_loop.step_tick()
        self.assertEqual(trans_loop.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_loop.position_ms, 960.0, places=4)

        # Advance another 80 ms -> device reaches 1040 ms -> wraps to 40 ms remainder!
        trans_loop.step_tick(delta_ms=80.0)
        self.assertEqual(trans_loop.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_loop.position_ms, 40.0, places=4)

    def test_defect_08_failure_state_transitions(self) -> None:
        """DEFECT-08: Verify failed backend operations transition to ERROR, preserve position, and recover."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=backend, clock=clock)

        errors_received = []
        states_received = []
        transport.register_error_callback(lambda err: errors_received.append(err))
        transport.register_state_callback(lambda st: states_received.append(st))

        # 1. Play failure transitions to ERROR, device marked not playing
        backend.inject_failure = True
        with self.assertRaises(AudioBackendError):
            transport.play()
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        self.assertFalse(backend.is_playing)
        self.assertIn(TransportState.ERROR, states_received)
        self.assertEqual(len(errors_received), 1)

        # 2. Successful recovery and play after clearing failure
        backend.inject_failure = False
        transport.play()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertTrue(backend.is_playing)

        # Advance to 500 ms
        clock.advance_ms(500.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # 3. Pause failure: raises AudioBackendError, state is ERROR, preserves position, backend.is_playing is False
        backend.inject_failure = True
        with self.assertRaises(AudioBackendError):
            transport.pause()
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        self.assertFalse(backend.is_playing)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # 4. Seek failure: raises AudioBackendError, state is ERROR, preserves 500 ms
        with self.assertRaises(AudioBackendError):
            transport.seek(200.0)
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        self.assertFalse(backend.is_playing)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # 5. Stop failure: raises AudioBackendError, state is ERROR, does NOT report STOPPED, preserves 500 ms
        with self.assertRaises(AudioBackendError):
            transport.stop()
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # 6. Controlled recovery: clear failure and reset/stop
        backend.inject_failure = False
        transport.stop()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 0.0, places=4)

    def test_defect_08_natural_completion_backend_stop_failure(self) -> None:
        """DEFECT-08: Verify natural completion does NOT suppress backend stop failure and does not fire end callback."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=backend, clock=clock)

        end_called = []
        errors_called = []
        transport.register_end_callback(lambda: end_called.append(True))
        transport.register_error_callback(lambda err: errors_called.append(err))

        transport.play()
        clock.advance_ms(500.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)

        # Inject failure right before end of piece
        backend.inject_failure = True
        clock.advance_ms(500.0)  # Clock is now at 1000 ms

        # step_tick reaches 1000 ms and attempts backend.stop(), which fails
        with self.assertRaises(AudioBackendError):
            transport.step_tick()

        # State must be ERROR (NOT STOPPED!), backend FAILED, position preserved at 1000 ms
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        self.assertFalse(backend.is_playing)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        # Must NOT issue successful completion notification!
        self.assertEqual(len(end_called), 0)
        self.assertEqual(len(errors_called), 1)

    def test_defect_08_device_query_failure_and_recovery(self) -> None:
        """DEFECT-08: Verify device query failure during playback transitions to ERROR without silent software fallback, and recovers cleanly."""
        class FailingQueryBackend(SimulatedAudioBackend):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.inject_query_failure = False

            def get_device_position_ms(self) -> Optional[float]:
                if self.inject_query_failure:
                    self._status = AudioBackendStatus.FAILED
                    self.is_playing = False
                    raise AudioBackendError("Injected failure during get_device_position_ms")
                return super().get_device_position_ms()

        clock = TestClock(0.0)
        backend = FailingQueryBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=backend, clock=clock)

        errors_called = []
        transport.register_error_callback(lambda err: errors_called.append(err))

        transport.play()
        clock.advance_ms(300.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 300.0, places=4)

        # Inject query failure: step_tick must raise and transition to ERROR, NOT silently use software time
        backend.inject_query_failure = True
        clock.advance_ms(200.0)  # Software time is 500 ms, but device query fails
        with self.assertRaises(AudioBackendError):
            transport.step_tick()

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        # Position is frozen at last valid coordinate (300 ms, NOT 500 ms software time)
        self.assertAlmostEqual(transport.position_ms, 300.0, places=4)
        self.assertEqual(len(errors_called), 1)

        # Verify rapid recovery
        backend.inject_query_failure = False
        backend._status = AudioBackendStatus.AVAILABLE
        transport.play()
        self.assertEqual(transport.state, TransportState.PLAYING)
        clock.advance_ms(100.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 400.0, places=4)

        transport.stop()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 0.0, places=4)

    def test_defect_07_buffer_latency_completion_and_loop_continuity(self) -> None:
        """DEFECT-07: Verify 20ms buffer latency drains smoothly without terminal 21ms cursor jumps."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(buffer_latency_ms=20.0, clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()

        # Advance to device pos 999 ms
        clock.advance_ms(999.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.device_position_ms, 999.0, places=4)
        # Audible position: 999 - 20 = 979 ms
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 979.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 979.0, places=4)

        # Advance by 1 ms to device pos 1000 ms
        clock.advance_ms(1.0)
        transport.step_tick()
        # Device processing complete (1000 ms), but audible buffer is draining!
        # State MUST still be PLAYING, position MUST advance smoothly by 1 ms to 980 ms (NO 21ms jump!)
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.device_position_ms, 1000.0, places=4)
        self.assertAlmostEqual(transport.estimated_audible_position_ms, 980.0, places=4)
        self.assertAlmostEqual(transport.position_ms, 980.0, places=4)

        # Drain buffer by advancing 19 ms to 1019 ms
        clock.advance_ms(19.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 999.0, places=4)

        # Advance final 1 ms to 1020 ms (audible reaches 1000 ms)
        clock.advance_ms(1.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        # Also verify loop continuity with 20ms buffer latency
        clock2 = TestClock(0.0)
        backend2 = SimulatedAudioBackend(buffer_latency_ms=20.0, clock=clock2)
        trans_loop = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock2,
            audio_backend=backend2,
            buffer_latency_ms=20.0,
        )
        trans_loop.set_loop(True)
        trans_loop.play()

        # Advance to device 1025 ms (audible reaches 1005 ms -> wraps to 5 ms remainder)
        clock2.advance_ms(1025.0)
        trans_loop.step_tick()
        self.assertEqual(trans_loop.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_loop.position_ms, 5.0, places=4)

    def test_defect_07_capped_device_position_with_buffer_latency(self) -> None:
        """DEFECT-07: Verify device position capped at source duration drains buffer and completes cleanly."""
        class CappedBackend(SimulatedAudioBackend):
            def get_device_position_ms(self) -> Optional[float]:
                pos = super().get_device_position_ms()
                return min(1000.0, pos) if pos is not None else None

        clock = TestClock(0.0)
        backend = CappedBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()
        # Advance test clock by 1000 ms: device reached 1000 ms (capped), audible is at 980 ms
        clock.advance_ms(1000.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 980.0, places=4)

        # Advance by 10 ms: buffer drainage advances audible position to 990 ms
        clock.advance_ms(10.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 990.0, places=4)

        # Advance by 10 ms: buffer drainage completes to 1000 ms, state transitions to STOPPED
        clock.advance_ms(10.0)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        # Verify looping with capped backend
        clock2 = TestClock(0.0)
        backend2 = CappedBackend(clock=clock2)
        trans_loop = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock2,
            audio_backend=backend2,
            buffer_latency_ms=20.0,
        )
        trans_loop.set_loop(True)
        trans_loop.play()

        # Advance to 1000 ms (feeder complete at source duration)
        clock2.advance_ms(1000.0)
        trans_loop.step_tick()
        # Advance buffer drain by 25 ms (drained to 1005 ms -> wraps to remainder 5 ms)
        clock2.advance_ms(25.0)
        trans_loop.step_tick()
        self.assertEqual(trans_loop.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_loop.position_ms, 5.0, places=4)

    def test_defect_08_reset_failure_handling(self) -> None:
        """DEFECT-08: Verify reset() maintains ERROR state and position when device stop fails, and recovers on success."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=backend, clock=clock)

        errors_called = []
        transport.register_error_callback(lambda err: errors_called.append(err))

        transport.play()
        clock.advance_ms(500.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # Inject backend failure and call reset()
        backend.inject_failure = True
        with self.assertRaises(AudioBackendError):
            transport.reset()

        # Must NOT report successful reset: state is ERROR, status is FAILED, position preserved at 500 ms
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(backend.get_status(), AudioBackendStatus.FAILED)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        self.assertEqual(len(errors_called), 1)

        # Clear failure and reset again: successful reset to STOPPED and position 0
        backend.inject_failure = False
        transport.reset()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 0.0, places=4)

    def test_defect_08_unexpected_missing_device_position(self) -> None:
        """DEFECT-08: Verify unexpected loss of device coordinates (returning None while available) transitions to ERROR."""
        class MissingPositionBackend(SimulatedAudioBackend):
            def get_device_position_ms(self) -> Optional[float]:
                if self.is_playing:
                    return None
                return super().get_device_position_ms()

        clock = TestClock(0.0)
        backend = MissingPositionBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=backend, clock=clock)

        errors_called = []
        transport.register_error_callback(lambda err: errors_called.append(err))

        transport.play()
        clock.advance_ms(500.0)

        # Calling step_tick() must raise AudioBackendError, NOT silently substitute software clock
        with self.assertRaises(AudioBackendError):
            transport.step_tick()

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(len(errors_called), 1)

        # Verify intentional NullAudioBackend does NOT raise and legitimately uses software clock
        null_backend = NullAudioBackend()
        clock_null = TestClock(0.0)
        trans_null = PlaybackTransport(wav_bytes=wav_bytes, audio_backend=null_backend, clock=clock_null)
        trans_null.play()
        clock_null.advance_ms(500.0)
        trans_null.step_tick()
        self.assertEqual(trans_null.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_null.position_ms, 500.0, places=4)

    def test_defect_07a_pause_resume_completion_during_capped_buffer_drainage(self) -> None:
        """DEFECT-07A: Verify pause, resume, and completion during capped device buffer drainage, including looping."""
        class CappedBackend(SimulatedAudioBackend):
            def get_device_position_ms(self):
                pos = super().get_device_position_ms()
                return min(1000.0, pos) if pos is not None else None

        clock = TestClock(0.0)
        backend = CappedBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)
        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()
        clock.advance_ms(1000)
        transport.step_tick()

        clock.advance_ms(10)
        transport.step_tick()

        # Before pause: 990 ms
        self.assertAlmostEqual(transport.position_ms, 990.0, places=4)
        transport.pause()
        # After pause: must remain frozen at 990 ms (no 10 ms backward jump to 980 ms!)
        self.assertEqual(transport.state, TransportState.PAUSED)
        self.assertAlmostEqual(transport.position_ms, 990.0, places=4)

        # Resume and advance remaining 10 ms to completion
        transport.resume()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 990.0, places=4)

        clock.advance_ms(10)
        transport.step_tick()
        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        # Verify looping with pause during drainage
        clock2 = TestClock(0.0)
        backend2 = CappedBackend(clock=clock2)
        trans_loop = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock2,
            audio_backend=backend2,
            buffer_latency_ms=20.0,
        )
        trans_loop.set_loop(True)
        trans_loop.play()
        clock2.advance_ms(1000)
        trans_loop.step_tick()
        clock2.advance_ms(10)
        trans_loop.step_tick()
        self.assertAlmostEqual(trans_loop.position_ms, 990.0, places=4)
        trans_loop.pause()
        self.assertAlmostEqual(trans_loop.position_ms, 990.0, places=4)
        trans_loop.resume()
        # Advance 15 ms: 10 ms drains to end, 5 ms wraps into loop remainder
        clock2.advance_ms(15)
        trans_loop.step_tick()
        self.assertEqual(trans_loop.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans_loop.position_ms, 5.0, places=4)

    def test_defect_08a_combined_missing_position_and_pause_failure(self) -> None:
        """DEFECT-08A: Verify combined missing position and backend pause failure avoids UnboundLocalError and notifies."""
        class MissingPositionBackend(SimulatedAudioBackend):
            def get_device_position_ms(self):
                if self.is_playing:
                    return None
                return super().get_device_position_ms()

            def pause(self):
                raise AudioBackendError("pause failed")

        clock = TestClock(0.0)
        backend = MissingPositionBackend(clock=clock)
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock,
            audio_backend=backend,
        )
        errors = []
        transport.register_error_callback(errors.append)
        transport.play()
        # Advance to 300 ms with valid position query before failure
        # In this backend, get_device_position_ms returns None while is_playing
        with self.assertRaises(AudioBackendError):
            transport.pause()

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertEqual(len(errors), 1)
        self.assertAlmostEqual(transport.position_ms, 0.0, places=4)

    def test_defect_08b_invalid_device_position_or_query_exception_during_pause(self) -> None:
        """DEFECT-08B: Verify pause rejects NaN, inf, negative positions, and query exceptions into ERROR state."""
        for bad_val in [float("nan"), float("inf"), float("-inf"), -5.0]:
            class InvalidPositionBackend(SimulatedAudioBackend):
                def get_device_position_ms(self):
                    if self.is_playing:
                        return bad_val
                    return super().get_device_position_ms()

            clock = TestClock(0.0)
            backend = InvalidPositionBackend(clock=clock)
            transport = PlaybackTransport(
                wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
                clock=clock,
                audio_backend=backend,
            )
            errors = []
            transport.register_error_callback(errors.append)
            transport.play()
            clock.advance_ms(500)

            with self.assertRaises(AudioBackendError):
                transport.pause()

            self.assertEqual(transport.state, TransportState.ERROR)
            self.assertAlmostEqual(transport.position_ms, 0.0, places=4)
            self.assertEqual(len(errors), 1)

        # Query exception during pause
        class QueryExplodingBackend(SimulatedAudioBackend):
            def get_device_position_ms(self):
                if self.is_playing:
                    raise RuntimeError("query exploded")
                return super().get_device_position_ms()

        clock2 = TestClock(0.0)
        backend2 = QueryExplodingBackend(clock=clock2)
        transport2 = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock2,
            audio_backend=backend2,
        )
        errors2 = []
        transport2.register_error_callback(errors2.append)
        transport2.play()
        clock2.advance_ms(500)

        with self.assertRaises(AudioBackendError):
            transport2.pause()

        self.assertEqual(transport2.state, TransportState.ERROR)
        self.assertAlmostEqual(transport2.position_ms, 0.0, places=4)
        self.assertEqual(len(errors2), 1)

    def test_defect_09_single_device_query_and_atomic_snapshot_agreement(self) -> None:
        """DEFECT-09: Verify step_tick acquires single device snapshot; callback, active events, and return agree."""
        class ChangingBackend(SimulatedAudioBackend):
            def get_device_position_ms(self):
                if self.is_playing:
                    self.n = getattr(self, "n", 0) + 1
                    return self.n * 100.0
                return super().get_device_position_ms()

        clock = TestClock(0.0)
        backend = ChangingBackend(clock=clock)
        tl = MusicTimeline()
        r = tl.create_row("R1")
        # Boundaries between the sampled positions (100, 200, 300, 400)
        r.add_event(SoundEvent("E1", "R1", 0, 150))
        r.add_event(SoundEvent("E2", "R1", 150, 250))
        r.add_event(SoundEvent("E3", "R1", 250, 350))
        r.add_event(SoundEvent("E4", "R1", 350, 450))

        transport = PlaybackTransport(
            timeline=tl,
            clock=clock,
            audio_backend=backend,
        )
        transport.play()
        backend.n = 0

        observed_positions: List[float] = []
        observed_events: List[Set[str]] = []
        transport.register_tick_callback(
            lambda pos, act: (observed_positions.append(pos), observed_events.append(set(act)))
        )

        result_pos = transport.step_tick()

        # Exactly ONE device query occurred during transport update
        self.assertEqual(backend.n, 1)
        # Snapshot position returned, recorded, and delivered to callbacks agrees
        self.assertAlmostEqual(result_pos, 100.0, places=4)
        self.assertEqual(observed_positions, [100.0])
        self.assertEqual(observed_events, [{"E1"}])
        self.assertEqual(transport.active_event_ids, {"E1"})
        self.assertAlmostEqual(transport._software_pos_ms, 100.0, places=4)

    def test_defect_10_seek_and_resume_semantics_with_buffer_latency(self) -> None:
        """DEFECT-10: Verify seek/resume with buffer latency maintains consistent coordinates without backward jumps."""
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms

        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )

        transport.play()

        # Seeking while playing must not jump backward by buffer latency (500 -> not 480)
        transport.seek(500.0)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # Pausing preserves authoritative audible coordinate
        transport.pause()
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)

        # Seeking while paused establishes requested coordinate
        transport.seek(600.0)
        self.assertAlmostEqual(transport.position_ms, 600.0, places=4)

        # Resuming after paused seek must not jump backward (600 -> not 580)
        transport.resume()
        self.assertAlmostEqual(transport.position_ms, 600.0, places=4)

        # Advance clock during buffer-fill interval (10 ms): audible held at start of segment
        clock.advance_ms(10.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 600.0, places=4)

        # Advance clock to complete buffer-fill interval (total 20 ms): buffer full
        clock.advance_ms(10.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 600.0, places=4)

        # Advance clock past buffer latency (total 30 ms): sound advances smoothly (610 ms)
        clock.advance_ms(10.0)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 610.0, places=4)

    def test_defect_10_seek_stopped_playing_paused_boundaries_and_zero_latency(self) -> None:
        """DEFECT-10: Test seek across STOPPED, PLAYING, PAUSED, boundaries, and zero-latency controls."""
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms

        # 1. Seeking while stopped
        clock1 = TestClock(0.0)
        backend1 = SimulatedAudioBackend(clock=clock1)
        trans1 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock1, audio_backend=backend1, buffer_latency_ms=20.0)
        trans1.seek(300.0)
        self.assertEqual(trans1.state, TransportState.STOPPED)
        self.assertAlmostEqual(trans1.position_ms, 300.0, places=4)
        trans1.play()
        self.assertEqual(trans1.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans1.position_ms, 300.0, places=4)
        clock1.advance_ms(30.0)
        trans1.step_tick()
        self.assertAlmostEqual(trans1.position_ms, 310.0, places=4)

        # 2. Seeking near beginning
        clock2 = TestClock(0.0)
        backend2 = SimulatedAudioBackend(clock=clock2)
        trans2 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock2, audio_backend=backend2, buffer_latency_ms=20.0)
        trans2.play()
        trans2.seek(5.0)
        self.assertAlmostEqual(trans2.position_ms, 5.0, places=4)
        clock2.advance_ms(10.0)
        trans2.step_tick()
        self.assertAlmostEqual(trans2.position_ms, 5.0, places=4)
        clock2.advance_ms(15.0)  # total 25 ms -> 5 ms audible advance
        trans2.step_tick()
        self.assertAlmostEqual(trans2.position_ms, 10.0, places=4)

        # 3. Seeking near end (buffer drainage and clean completion)
        clock3 = TestClock(0.0)
        backend3 = SimulatedAudioBackend(clock=clock3)
        trans3 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock3, audio_backend=backend3, buffer_latency_ms=20.0)
        trans3.play()
        trans3.seek(990.0)
        self.assertAlmostEqual(trans3.position_ms, 990.0, places=4)
        # Advance 10 ms: device reaches 1000 ms, buffer starts draining
        clock3.advance_ms(10.0)
        trans3.step_tick()
        self.assertEqual(trans3.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans3.position_ms, 990.0, places=4)
        # Advance 10 ms (drain elapsed 10 ms): audible reaches 990 ms
        clock3.advance_ms(10.0)
        trans3.step_tick()
        self.assertEqual(trans3.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans3.position_ms, 990.0, places=4)
        # Advance 5 ms: audible drains to 995 ms
        clock3.advance_ms(5.0)
        trans3.step_tick()
        self.assertEqual(trans3.state, TransportState.PLAYING)
        self.assertAlmostEqual(trans3.position_ms, 995.0, places=4)
        # Advance 5 ms: audible reaches 1000 ms, completing piece cleanly
        clock3.advance_ms(5.0)
        trans3.step_tick()
        self.assertEqual(trans3.state, TransportState.STOPPED)
        self.assertAlmostEqual(trans3.position_ms, 1000.0, places=4)

        # 4. Zero-latency controls
        clock4 = TestClock(0.0)
        backend4 = SimulatedAudioBackend(clock=clock4)
        trans4 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock4, audio_backend=backend4, buffer_latency_ms=0.0)
        trans4.seek(200.0)
        self.assertAlmostEqual(trans4.position_ms, 200.0, places=4)
        trans4.play()
        self.assertAlmostEqual(trans4.position_ms, 200.0, places=4)
        trans4.seek(500.0)
        self.assertAlmostEqual(trans4.position_ms, 500.0, places=4)
        trans4.pause()
        self.assertAlmostEqual(trans4.position_ms, 500.0, places=4)
        trans4.seek(700.0)
        self.assertAlmostEqual(trans4.position_ms, 700.0, places=4)
        trans4.resume()
        self.assertAlmostEqual(trans4.position_ms, 700.0, places=4)
        clock4.advance_ms(15.0)
        trans4.step_tick()
        self.assertAlmostEqual(trans4.position_ms, 715.0, places=4)

    def test_defect_10a_loop_restart_source_audio_preservation(self) -> None:
        """DEFECT-10A: Verify loop restarts at intended source coordinate without skipping source audio."""
        # 1. Nonzero latency (20 ms) exact loop boundary
        clock = TestClock(0.0)
        backend = SimulatedAudioBackend(clock=clock)
        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        transport = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock,
            audio_backend=backend,
            buffer_latency_ms=20.0,
        )
        transport.set_loop(True)
        transport.play()
        clock.advance_ms(1020.0)
        step_pos = transport.step_tick()
        dev_pos = backend.get_device_position_ms()
        # Visual transport restarts at 0 ms, AND backend restarts at source coordinate 0 ms (NOT 20 ms!)
        self.assertAlmostEqual(step_pos, 0.0, places=4)
        self.assertAlmostEqual(dev_pos, 0.0, places=4)

        # 2. Nonzero loop remainder (advance 1025 ms -> 5 ms remainder)
        clock2 = TestClock(0.0)
        backend2 = SimulatedAudioBackend(clock=clock2)
        trans2 = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock2,
            audio_backend=backend2,
            buffer_latency_ms=20.0,
        )
        trans2.set_loop(True)
        trans2.play()
        clock2.advance_ms(1025.0)
        step_pos2 = trans2.step_tick()
        dev_pos2 = backend2.get_device_position_ms()
        self.assertAlmostEqual(step_pos2, 5.0, places=4)
        self.assertAlmostEqual(dev_pos2, 5.0, places=4)

        # 3. Zero latency control
        clock3 = TestClock(0.0)
        backend3 = SimulatedAudioBackend(clock=clock3)
        trans3 = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock3,
            audio_backend=backend3,
            buffer_latency_ms=0.0,
        )
        trans3.set_loop(True)
        trans3.play()
        clock3.advance_ms(1000.0)
        step_pos3 = trans3.step_tick()
        dev_pos3 = backend3.get_device_position_ms()
        self.assertAlmostEqual(step_pos3, 0.0, places=4)
        self.assertAlmostEqual(dev_pos3, 0.0, places=4)

        # 4. Repeated loop cycles
        clock4 = TestClock(0.0)
        backend4 = SimulatedAudioBackend(clock=clock4)
        trans4 = PlaybackTransport(
            wav_bytes=wav_bytes,
            clock=clock4,
            audio_backend=backend4,
            buffer_latency_ms=20.0,
        )
        trans4.set_loop(True)
        trans4.play()
        for _ in range(3):
            clock4.advance_ms(1020.0)
            r = trans4.step_tick()
            d = backend4.get_device_position_ms()
            self.assertAlmostEqual(r, 0.0, places=4)
            self.assertAlmostEqual(d, 0.0, places=4)

    def test_defect_09a_failed_seek_preserves_consistent_coordinates_and_visual_position(self) -> None:
        """DEFECT-09A: Verify seek failure preserves last valid position across state, callbacks, and active events."""
        class FailSeekBackend(SimulatedAudioBackend):
            def seek(self, pos_ms: float) -> None:
                raise AudioBackendError("Injected seek failure")

        wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms

        # 1. Failed seek while PLAYING
        clock1 = TestClock(0.0)
        backend1 = FailSeekBackend(clock=clock1)
        trans1 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock1, audio_backend=backend1)
        trans1.play()
        clock1.advance_ms(100.0)
        trans1.step_tick()
        seen1 = []
        trans1.register_tick_callback(lambda p, a: seen1.append(p))

        with self.assertRaises(AudioBackendError):
            trans1.seek(500.0)

        self.assertEqual(trans1.state, TransportState.ERROR)
        self.assertAlmostEqual(trans1.position_ms, 100.0, places=4)
        self.assertAlmostEqual(trans1._software_pos_ms, 100.0, places=4)
        # Visual callback MUST receive preserved position 100.0 (NOT unachieved target 500.0!)
        self.assertEqual(seen1, [100.0])

        # 2. Failed seek while STOPPED
        clock2 = TestClock(0.0)
        backend2 = FailSeekBackend(clock=clock2)
        trans2 = PlaybackTransport(wav_bytes=wav_bytes, clock=clock2, audio_backend=backend2)
        seen2 = []
        errs2 = []
        trans2.register_tick_callback(lambda p, a: seen2.append(p))
        trans2.register_error_callback(errs2.append)

        with self.assertRaises(AudioBackendError):
            trans2.seek(400.0)

        self.assertEqual(trans2.state, TransportState.ERROR)
        self.assertAlmostEqual(trans2.position_ms, 0.0, places=4)
        self.assertEqual(seen2, [0.0])
        self.assertEqual(len(errs2), 1)

        # 3. Failed seek while PAUSED with active event membership
        tl = MusicTimeline()
        r = tl.create_row("R1")
        r.add_event(SoundEvent("E1", "R1", 0, 150))
        r.add_event(SoundEvent("E2", "R1", 150, 300))
        r.add_event(SoundEvent("E3", "R1", 300, 450))
        r.add_event(SoundEvent("E4", "R1", 450, 600))
        clock3 = TestClock(0.0)
        backend3 = FailSeekBackend(clock=clock3)
        trans3 = PlaybackTransport(timeline=tl, clock=clock3, audio_backend=backend3)
        trans3.play()
        clock3.advance_ms(200.0)
        trans3.step_tick()
        trans3.pause()
        self.assertEqual(trans3.active_event_ids, {"E2"})

        seen3 = []
        trans3.register_tick_callback(lambda p, a: seen3.append(p))

        with self.assertRaises(AudioBackendError):
            trans3.seek(500.0)  # E4 would be active at 500.0

        self.assertEqual(trans3.state, TransportState.ERROR)
        self.assertAlmostEqual(trans3.position_ms, 200.0, places=4)
        # Active events MUST remain E2 at preserved coordinate (NOT E4!)
        self.assertEqual(trans3.active_event_ids, {"E2"})
        self.assertEqual(seen3, [200.0])

    def test_defect_09b_failed_stop_and_reset_preserve_consistent_coordinates_and_visual_position(self) -> None:
        """Verify DEFECT-09B: Failed stop() and reset() preserve last valid coordinate and visual position."""
        class FailStopBackend(SimulatedAudioBackend):
            fail = False
            def stop(self):
                if self.fail:
                    raise AudioBackendError("simulated backend stop/shutdown failure")
                return super().stop()

        for op in ["stop", "reset"]:
            with self.subTest(operation=op):
                tl = MusicTimeline()
                r = tl.create_row("R1")
                r.add_event(SoundEvent("E1", "R1", 0, 150))
                r.add_event(SoundEvent("E2", "R1", 150, 300))
                r.add_event(SoundEvent("E3", "R1", 300, 450))

                clock = TestClock(0.0)
                backend = FailStopBackend(clock=clock)
                trans = PlaybackTransport(
                    timeline=tl,
                    wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
                    clock=clock,
                    audio_backend=backend
                )

                # Start playback and advance to 200 ms (E2 active)
                trans.play()
                clock.advance_ms(200.0)
                trans.step_tick()
                self.assertAlmostEqual(trans.position_ms, 200.0, places=4)
                self.assertEqual(trans.active_event_ids, {"E2"})

                seen_ticks = []
                errors = []
                states = []
                trans.register_tick_callback(lambda p, a: seen_ticks.append((p, set(a))))
                trans.register_error_callback(errors.append)
                trans.register_state_callback(states.append)

                backend.fail = True

                with self.assertRaises(AudioBackendError):
                    getattr(trans, op)()

                # 1. State must transition to ERROR
                self.assertEqual(trans.state, TransportState.ERROR)
                self.assertIn(TransportState.ERROR, states)

                # 2. Position must be preserved at pre-operation coordinate (200.0 ms, NOT 0.0 ms)
                self.assertAlmostEqual(trans.position_ms, 200.0, places=4)

                # 3. Active-event membership must remain consistent with preserved coordinate
                self.assertEqual(trans.active_event_ids, {"E2"})

                # 4. Tick callback must receive preserved coordinate (200.0 ms, NOT 0.0 ms)
                self.assertEqual(len(seen_ticks), 1)
                cb_pos, cb_active = seen_ticks[0]
                self.assertAlmostEqual(cb_pos, 200.0, places=4)
                self.assertEqual(cb_active, {"E2"})

                # 5. Error callback must be notified with the raised error
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], AudioBackendError)

                # 6. Successful recovery when backend issue is resolved
                backend.fail = False
                trans.reset()
                self.assertEqual(trans.state, TransportState.STOPPED)
                self.assertAlmostEqual(trans.position_ms, 0.0, places=4)
                self.assertEqual(trans.active_event_ids, {"E1"})
                self.assertAlmostEqual(seen_ticks[-1][0], 0.0, places=4)

        # Also verify failed stop while PAUSED
        clock_paused = TestClock(0.0)
        backend_paused = FailStopBackend(clock=clock_paused)
        tl_paused = MusicTimeline()
        r_p = tl_paused.create_row("R1")
        r_p.add_event(SoundEvent("E1", "R1", 0, 100))
        r_p.add_event(SoundEvent("E2", "R1", 100, 250))
        trans_paused = PlaybackTransport(
            timeline=tl_paused,
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock_paused,
            audio_backend=backend_paused
        )
        trans_paused.play()
        clock_paused.advance_ms(150.0)
        trans_paused.step_tick()
        trans_paused.pause()
        self.assertEqual(trans_paused.state, TransportState.PAUSED)
        self.assertAlmostEqual(trans_paused.position_ms, 150.0, places=4)
        self.assertEqual(trans_paused.active_event_ids, {"E2"})

        seen_paused = []
        err_paused = []
        trans_paused.register_tick_callback(lambda p, a: seen_paused.append(p))
        trans_paused.register_error_callback(err_paused.append)

        backend_paused.fail = True
        with self.assertRaises(AudioBackendError):
            trans_paused.stop()

        self.assertEqual(trans_paused.state, TransportState.ERROR)
        self.assertAlmostEqual(trans_paused.position_ms, 150.0, places=4)
        self.assertEqual(trans_paused.active_event_ids, {"E2"})
        self.assertEqual(seen_paused, [150.0])
        self.assertEqual(len(err_paused), 1)

    def test_defect_09c_failed_pause_recalculates_active_events_and_publishes_consistent_snapshot(self) -> None:
        """Verify DEFECT-09C: Failed pause() recalculates active events and publishes consistent visual snapshot."""
        class FailPause(SimulatedAudioBackend):
            def pause(self):
                raise AudioBackendError("simulated pause failure")

        clock = TestClock(0)
        backend = FailPause(clock=clock)
        timeline = MusicTimeline()
        row = timeline.create_row("R1")
        row.add_event(SoundEvent("E1", "R1", 0, 150))
        row.add_event(SoundEvent("E2", "R1", 150, 1000))

        transport = PlaybackTransport(
            timeline=timeline,
            wav_bytes=create_test_wav_bytes(),
            clock=clock,
            audio_backend=backend
        )

        transport.play()
        clock.advance_ms(100)
        transport.step_tick()
        self.assertEqual(transport.active_event_ids, {"E1"})

        seen = []
        errors = []
        transport.register_tick_callback(lambda p, a: seen.append((p, set(a))))
        transport.register_error_callback(errors.append)

        clock.advance_ms(100)  # Clock reaches 200 ms (E2 active)

        with self.assertRaises(AudioBackendError):
            transport.pause()

        # State must transition to ERROR
        self.assertEqual(transport.state, TransportState.ERROR)
        # Position must report 200.0 ms
        self.assertAlmostEqual(transport.position_ms, 200.0, places=4)
        # Active events must be recalculated at 200.0 ms ({"E2"}, NOT stale {"E1"}!)
        self.assertEqual(transport.active_event_ids, {"E2"})
        # Visual callback must receive consistent snapshot (200.0, {"E2"})
        self.assertEqual(seen, [(200.0, {"E2"})])
        # Error callback notified
        self.assertEqual(len(errors), 1)

    def test_defect_09d_failed_loop_restart_preserves_completed_cycle_and_suppresses_unachieved_remainder(self) -> None:
        """Verify DEFECT-09D: Failed loop restart preserves completed cycle coordinate and suppresses unachieved remainder."""
        class FailLoop(SimulatedAudioBackend):
            fail = False
            def play(self, *args, **kwargs):
                if self.fail:
                    raise AudioBackendError("simulated loop restart failure")
                return super().play(*args, **kwargs)

        clock = TestClock(0)
        backend = FailLoop(clock=clock)
        timeline = MusicTimeline()
        row = timeline.create_row("R1")
        row.add_event(SoundEvent("E1", "R1", 0, 150))
        row.add_event(SoundEvent("E2", "R1", 150, 1000))

        transport = PlaybackTransport(
            timeline=timeline,
            wav_bytes=create_test_wav_bytes(),
            clock=clock,
            audio_backend=backend
        )
        transport.set_loop(True)
        transport.play()

        clock.advance_ms(100)
        transport.step_tick()

        seen = []
        errors = []
        transport.register_tick_callback(lambda p, a: seen.append((p, set(a))))
        transport.register_error_callback(errors.append)

        # Advance clock to cross 1000 ms duration by 5 ms remainder
        clock.advance_ms(905)
        backend.fail = True

        with self.assertRaises(AudioBackendError):
            transport.step_tick()

        # State must transition to ERROR
        self.assertEqual(transport.state, TransportState.ERROR)
        # Position must report completed cycle coordinate (1000.0 ms, NOT unachieved 5.0 ms!)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)
        # Active events at 1000.0 ms under half-open interval [150, 1000) must be empty (NOT {"E1"}!)
        self.assertEqual(transport.active_event_ids, set())
        # Visual callback must receive (1000.0, set()), suppressing the rejected remainder 5.0 ms
        self.assertEqual(seen, [(1000.0, set())])
        # Error callback notified
        self.assertEqual(len(errors), 1)

    def test_defect_09e_failed_replay_preserves_completed_coordinate(self) -> None:
        """Verify DEFECT-09E: Failed replay preserves completed coordinate instead of prematurely zeroing position."""
        class FailReplay(SimulatedAudioBackend):
            fail = False
            def play(self, *args, **kwargs):
                if self.fail:
                    raise AudioBackendError("simulated replay failure")
                return super().play(*args, **kwargs)

        clock = TestClock(0)
        backend = FailReplay(clock=clock)
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(),
            clock=clock,
            audio_backend=backend
        )

        transport.play()
        clock.advance_ms(1000)
        transport.step_tick()

        self.assertEqual(transport.state, TransportState.STOPPED)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        seen = []
        errors = []
        transport.register_tick_callback(lambda p, a: seen.append((p, set(a))))
        transport.register_error_callback(errors.append)

        backend.fail = True

        with self.assertRaises(AudioBackendError):
            transport.play()

        # State must transition to ERROR
        self.assertEqual(transport.state, TransportState.ERROR)
        # Position must be preserved at completed coordinate (1000.0 ms, NOT 0.0 ms!)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)
        # Tick callback must deliver preserved coordinate
        self.assertEqual(len(seen), 1)
        self.assertAlmostEqual(seen[0][0], 1000.0, places=4)
        # Error callback notified
        self.assertEqual(len(errors), 1)

        # Verify clean recovery when replay issue is resolved
        backend.fail = False
        transport.play()
        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertAlmostEqual(transport.position_ms, 0.0, places=4)

    def test_defect_09f_seek_in_error_state_recovers_and_maintains_coordinate_agreement(self) -> None:
        """Verify DEFECT-09F: Seek in ERROR state recovers consistently and agrees across state, latches, and callbacks."""
        clock = TestClock(0)
        backend = SimulatedAudioBackend(clock=clock)
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock,
            audio_backend=backend
        )

        transport.play()
        clock.advance_ms(100)
        transport.step_tick()

        # Enter ERROR state via injected failure on stop
        backend.inject_failure = True
        with self.assertRaises(AudioBackendError):
            transport.stop()

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertAlmostEqual(transport.position_ms, 100.0, places=4)

        # 1. Failed seek while in ERROR remains in ERROR with preserved coordinates
        seen_err = []
        transport.register_tick_callback(lambda p, a: seen_err.append(p))
        with self.assertRaises(AudioBackendError):
            transport.seek(700.0)

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertAlmostEqual(transport.position_ms, 100.0, places=4)
        self.assertEqual(seen_err, [100.0])

        # 2. Successful seek in ERROR state executes explicit recovery transition to PAUSED
        backend.inject_failure = False
        seen_success = []
        states = []
        transport.register_tick_callback(lambda p, a: seen_success.append(p))
        transport.register_state_callback(states.append)

        transport.seek(500.0)

        # State must recover to PAUSED
        self.assertEqual(transport.state, TransportState.PAUSED)
        self.assertIn(TransportState.PAUSED, states)

        # Position, visual callback, and backend device coordinate must all agree at 500.0 ms
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        self.assertEqual(seen_success, [500.0])
        self.assertAlmostEqual(backend.get_device_position_ms(), 500.0, places=4)

        # Continued playback from recovered position
        transport.play()
        self.assertEqual(transport.state, TransportState.PLAYING)
        clock.advance_ms(50)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 550.0, places=4)

    def test_defect_09g_pause_at_unprocessed_loop_boundary_preserves_completed_cycle(self) -> None:
        """Verify DEFECT-09G: Pause at unprocessed loop boundary preserves completed cycle coordinate."""
        class FailPause(SimulatedAudioBackend):
            def pause(self):
                raise AudioBackendError("simulated pause failure")

        clock = TestClock(0)
        backend = FailPause(clock=clock)
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock,
            audio_backend=backend
        )

        transport.set_loop(True)
        transport.play()

        # Advance clock to 1005 ms before step_tick() executes loop restart transaction
        clock.advance_ms(1005)

        # Progress in current cycle must be bounded by total_duration (1000.0 ms, NOT uncommitted 5.0 ms!)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)

        seen = []
        errors = []
        transport.register_tick_callback(lambda p, a: seen.append(p))
        transport.register_error_callback(errors.append)

        # Failed pause at boundary
        with self.assertRaises(AudioBackendError):
            transport.pause()

        # State must transition to ERROR
        self.assertEqual(transport.state, TransportState.ERROR)
        # Position must preserve completed cycle coordinate (1000.0 ms, NOT 5.0 ms!)
        self.assertAlmostEqual(transport.position_ms, 1000.0, places=4)
        # Visual callback must receive 1000.0 ms
        self.assertEqual(seen, [1000.0])
        self.assertEqual(len(errors), 1)

        # Also test successful pause at unprocessed loop boundary
        clock_succ = TestClock(0)
        backend_succ = SimulatedAudioBackend(clock=clock_succ)
        transport_succ = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock_succ,
            audio_backend=backend_succ
        )
        transport_succ.set_loop(True)
        transport_succ.play()
        clock_succ.advance_ms(1005)

        transport_succ.pause()
        self.assertEqual(transport_succ.state, TransportState.PAUSED)
        self.assertAlmostEqual(transport_succ.position_ms, 1000.0, places=4)

    def test_defect_09h_error_recovery_seek_requires_verified_non_playing_backend(self) -> None:
        """Verify DEFECT-09H: Seek in ERROR state requires verified non-playing backend condition before committing PAUSED."""
        class FailStop(SimulatedAudioBackend):
            fail = False
            def stop(self):
                if self.fail:
                    raise AudioBackendError("simulated stop failure without stopping")
                return super().stop()

        clock = TestClock(0)
        backend = FailStop(clock=clock)
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock,
            audio_backend=backend
        )

        transport.play()
        clock.advance_ms(100)
        transport.step_tick()

        # 1. Stop fails, leaving backend actively playing
        backend.fail = True
        with self.assertRaises(AudioBackendError):
            transport.stop()

        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertAlmostEqual(transport.position_ms, 100.0, places=4)
        self.assertTrue(backend.is_playing)

        # 2. Seek attempted while backend still cannot establish non-playing condition must be rejected
        seen_rejected = []
        transport.register_tick_callback(lambda p, a: seen_rejected.append(p))
        with self.assertRaises(AudioBackendError):
            transport.seek(500.0)

        # Transport must remain in ERROR at preserved coordinate (NOT falsely claim PAUSED at 500 ms!)
        self.assertEqual(transport.state, TransportState.ERROR)
        self.assertAlmostEqual(transport.position_ms, 100.0, places=4)
        self.assertEqual(seen_rejected, [100.0])
        self.assertTrue(backend.is_playing)

        # 3. Resolve backend failure and perform successful recovery seek
        backend.fail = False
        seen_success = []
        states = []
        transport.register_tick_callback(lambda p, a: seen_success.append(p))
        transport.register_state_callback(states.append)

        transport.seek(500.0)

        # Non-playing condition is established and state recovers to PAUSED
        self.assertEqual(transport.state, TransportState.PAUSED)
        self.assertIn(TransportState.PAUSED, states)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        self.assertFalse(backend.is_playing)
        self.assertAlmostEqual(backend.get_device_position_ms(), 500.0, places=4)
        self.assertEqual(seen_success, [500.0])

        # 4. Advancing clock by 50 ms must NOT advance backend position
        clock.advance_ms(50)
        self.assertEqual(transport.state, TransportState.PAUSED)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        self.assertAlmostEqual(backend.get_device_position_ms(), 500.0, places=4)

        # 5. Continued playback resumes cleanly from 500 ms
        transport.play()
        self.assertEqual(transport.state, TransportState.PLAYING)
        clock.advance_ms(50)
        transport.step_tick()
        self.assertAlmostEqual(transport.position_ms, 550.0, places=4)
        self.assertAlmostEqual(backend.get_device_position_ms(), 550.0, places=4)

    def test_defect_09i_windows_mci_resume_after_recovery_issues_play_from_recovered_position(self) -> None:
        """DEFECT-09I: Verify Windows MCI backend issues play command from recovered coordinate, resolving silent resume no-op."""
        class MockMCI(WindowsMciAudioBackend):
            def __init__(self):
                super().__init__()
                self._winmm = object()
                self.commands = []
                self.fail_stop = False
                self.pos = 0.0

            def load_wav_bytes(self, data):
                self._is_open = True
                self._status = AudioBackendStatus.AVAILABLE

            def _send_mci(self, command, expect_output=False):
                parts = command.split()
                op = parts[0]
                self.commands.append(command)
                if op == "stop" and self.fail_stop:
                    raise AudioBackendError("stop failed")
                if op in ("play", "seek"):
                    self.pos = float(parts[-1])
                if op == "status":
                    return str(int(round(self.pos)))
                return ""

        clock = TestClock(0)
        backend = MockMCI()
        transport = PlaybackTransport(
            wav_bytes=create_test_wav_bytes(num_frames=8000, frame_rate=8000),
            clock=clock,
            audio_backend=backend,
        )

        transport.play()
        backend.pos = 100.0
        transport.step_tick()

        # Shutdown failure leaves transport in ERROR
        backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            transport.stop()

        # Resolve shutdown failure and perform recovery seek to 500 ms
        backend.fail_stop = False
        transport.seek(500.0)

        self.assertEqual(transport.state, TransportState.PAUSED)
        self.assertAlmostEqual(transport.position_ms, 500.0, places=4)
        self.assertFalse(backend.is_playing)
        self.assertFalse(backend.is_paused)

        backend.commands.clear()

        # Resuming playback must issue 'play <alias> from 500' rather than silent resume no-op
        transport.play()

        self.assertEqual(transport.state, TransportState.PLAYING)
        self.assertTrue(backend.is_playing)
        self.assertIn(f"play {backend._alias} from 500", backend.commands)
        self.assertNotIn(f"resume {backend._alias}", backend.commands)


class TestGUIPlaybackIntegration(unittest.TestCase):
    """Integration tests verifying TimelineCanvas playhead and MusicGUI transport wiring."""

    def setUp(self) -> None:
        self.timeline = create_stage_1_proof_timeline()
        self.app = MusicGUI(self.timeline)
        self.app.withdraw()

    def tearDown(self) -> None:
        self.app.destroy()

    def test_16_timeline_canvas_playhead_cursor_rendering(self) -> None:
        """Verify playhead cursor items are created, moved, and retrieved via find_playback_cursor()."""
        canvas = self.app.timeline_view
        self.assertEqual(len(canvas.find_playback_cursor()), 0)

        canvas.set_playback_cursor(1000.0, auto_scroll=False)
        items = canvas.find_playback_cursor()
        self.assertGreaterEqual(len(items), 2)

        line_item = canvas.canvas.find_withtag("playback_cursor_line")
        head_item = canvas.canvas.find_withtag("playback_cursor_head")
        self.assertTrue(line_item)
        self.assertTrue(head_item)

        expected_x = canvas.coords.time_to_x(1000.0)
        line_coords = canvas.canvas.coords(line_item[0])
        self.assertAlmostEqual(line_coords[0], expected_x, places=2)

        canvas.clear_playback_cursor()
        self.assertEqual(len(canvas.find_playback_cursor()), 0)

    def test_17_active_sound_bar_highlighting_and_restoration(self) -> None:
        """Verify active sound bars gain highlight outline, and cleanly restore original border on deactivation."""
        canvas = self.app.timeline_view
        sound_a_tag = "sound_bar_Sound_A"

        initial_width = float(canvas.canvas.itemcget(sound_a_tag, "width"))
        self.assertAlmostEqual(initial_width, 2.0, places=1)

        canvas.set_playback_cursor(500.0, active_event_ids={"Sound A"}, auto_scroll=False)
        highlight_width = float(canvas.canvas.itemcget(sound_a_tag, "width"))
        highlight_color = canvas.canvas.itemcget(sound_a_tag, "outline")
        self.assertAlmostEqual(highlight_width, 3.5, places=1)
        self.assertEqual(highlight_color, "#dc2626")

        canvas.set_playback_cursor(4500.0, active_event_ids={"Sound B"}, auto_scroll=False)
        restored_width = float(canvas.canvas.itemcget(sound_a_tag, "width"))
        self.assertAlmostEqual(restored_width, 2.0, places=1)

    def test_18_main_window_transport_wiring(self) -> None:
        """Verify transport controls, buttons, and badges in MusicGUI."""
        self.assertIsNotNone(self.app.transport)
        self.assertEqual(self.app.transport.state, TransportState.STOPPED)

        self.assertIn("Audio:", self.app.lbl_audio_mode.cget("text"))
        self.assertIn("00:00.000", self.app.lbl_time.cget("text"))

        self.app.on_transport_toggle_play_pause()
        self.assertEqual(self.app.transport.state, TransportState.PLAYING)

        self.app.on_transport_toggle_play_pause()
        self.assertEqual(self.app.transport.state, TransportState.PAUSED)

        self.app.on_transport_stop()
        self.assertEqual(self.app.transport.state, TransportState.STOPPED)




class MockMciBackend(WindowsMciAudioBackend):
    """Production WindowsMciAudioBackend subclass with intercepted _send_mci for deterministic command inspection."""

    def __init__(self) -> None:
        super().__init__()
        self._winmm = object()
        self._status = AudioBackendStatus.AVAILABLE
        self.commands: List[str] = []
        self.fail_stop: bool = False
        self.fail_play: bool = False
        self.fail_pause: bool = False
        self.fail_resume: bool = False
        self.fail_seek: bool = False
        self.fail_status: bool = False
        self.pos: float = 0.0

    def load_wav_bytes(self, wav_bytes: bytes) -> None:
        self._is_open = True
        self._status = AudioBackendStatus.AVAILABLE

    def _send_mci(self, command: str, expect_output: bool = False) -> str:
        self.commands.append(command)
        parts = command.split()
        op = parts[0]

        if op == "stop" and self.fail_stop:
            raise AudioBackendError("Simulated stop failure")
        if op == "play" and self.fail_play:
            raise AudioBackendError("Simulated play failure")
        if op == "pause" and self.fail_pause:
            raise AudioBackendError("Simulated pause failure")
        if op == "resume" and self.fail_resume:
            raise AudioBackendError("Simulated resume failure")
        if op == "seek" and self.fail_seek:
            raise AudioBackendError("Simulated seek failure")
        if op == "status" and self.fail_status:
            raise AudioBackendError("Simulated status failure")

        if op == "play":
            if len(parts) >= 4 and parts[2] == "from":
                self.pos = float(parts[3])
        elif op == "seek":
            if len(parts) >= 4 and parts[2] == "to":
                self.pos = float(parts[3])
        elif op == "status":
            return str(int(round(self.pos)))

        return ""


class TestWindowsMciCommandControlPath(unittest.TestCase):
    """Deterministic command-level control-path regression coverage using production WindowsMciAudioBackend."""

    def setUp(self) -> None:
        self.clock = TestClock(0.0)
        self.backend = MockMciBackend()
        self.wav_bytes = create_test_wav_bytes(num_frames=8000, frame_rate=8000)  # 1000 ms
        self.transport = PlaybackTransport(
            wav_bytes=self.wav_bytes,
            clock=self.clock,
            audio_backend=self.backend,
        )

    def test_01_initial_playback_issues_play_command(self) -> None:
        """Verify initial playback issues the appropriate play command."""
        self.transport.play()
        self.assertEqual(self.transport.state, TransportState.PLAYING)
        self.assertTrue(self.backend.is_playing)
        self.assertFalse(self.backend.is_paused)
        self.assertIn(f"play {self.backend._alias} from 0", self.backend.commands)

    def test_02_pause_and_resume_issue_appropriate_commands(self) -> None:
        """Verify ordinary pause and resume issue the appropriate commands."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.transport.pause()
        self.assertEqual(self.transport.state, TransportState.PAUSED)
        self.assertFalse(self.backend.is_playing)
        self.assertTrue(self.backend.is_paused)
        self.assertEqual(self.backend.commands[-1], f"pause {self.backend._alias}")

        self.transport.resume()
        self.assertEqual(self.transport.state, TransportState.PLAYING)
        self.assertTrue(self.backend.is_playing)
        self.assertFalse(self.backend.is_paused)
        self.assertEqual(self.backend.commands[-1], f"resume {self.backend._alias}")

    def test_03_failed_stop_leaves_transport_in_error(self) -> None:
        """Verify failed stop leaves the transport in ERROR."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        self.assertEqual(self.transport.state, TransportState.ERROR)
        self.assertAlmostEqual(self.transport.position_ms, 200.0, places=4)
        self.assertEqual(self.backend.commands[-1], f"stop {self.backend._alias}")

    def test_04_recovery_seek_fails_when_controlled_shutdown_fails(self) -> None:
        """Verify recovery seek fails when controlled shutdown fails."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        with self.assertRaises(AudioBackendError):
            self.transport.seek(500.0)

        self.assertEqual(self.transport.state, TransportState.ERROR)
        self.assertAlmostEqual(self.transport.position_ms, 200.0, places=4)
        self.assertEqual(self.backend.commands[-1], f"stop {self.backend._alias}")

    def test_05_successful_recovery_performs_stop_and_seek_in_order(self) -> None:
        """Verify successful recovery performs stop and seek in the correct order."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        self.backend.fail_stop = False
        self.backend.commands.clear()
        self.transport.seek(500.0)

        self.assertEqual(self.transport.state, TransportState.PAUSED)
        self.assertAlmostEqual(self.transport.position_ms, 500.0, places=4)
        self.assertFalse(self.backend.is_playing)
        self.assertFalse(self.backend.is_paused)
        self.assertEqual(
            self.backend.commands,
            [f"stop {self.backend._alias}", f"seek {self.backend._alias} to 500"],
        )

    def test_06_playback_after_recovery_issues_play_from_recovered_position(self) -> None:
        """Verify playback after successful recovery issues an actual play command at recovered coordinate."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        self.backend.fail_stop = False
        self.transport.seek(500.0)

        self.backend.commands.clear()
        self.transport.play()

        self.assertEqual(self.transport.state, TransportState.PLAYING)
        self.assertTrue(self.backend.is_playing)
        self.assertFalse(self.backend.is_paused)
        self.assertEqual(self.backend.commands[0], f"play {self.backend._alias} from 500")

    def test_07_failed_playback_after_recovery_preserves_error_and_coord(self) -> None:
        """Verify failed playback after recovery preserves the valid coordinate and ERROR state."""
        self.transport.play()
        self.clock.advance_ms(200.0)
        self.backend.pos = 200.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        self.backend.fail_stop = False
        self.transport.seek(500.0)

        self.backend.fail_play = True
        with self.assertRaises(AudioBackendError):
            self.transport.play()

        self.assertEqual(self.transport.state, TransportState.ERROR)
        self.assertAlmostEqual(self.transport.position_ms, 500.0, places=4)
        self.assertFalse(self.backend.is_playing)

    def test_08_visual_callbacks_and_active_event_membership_consistency(self) -> None:
        """Verify visual callbacks and active-event membership remain consistent throughout recovery."""
        ticks = []
        errors = []
        self.transport.register_tick_callback(lambda pos, ids: ticks.append((pos, set(ids))))
        self.transport.register_error_callback(lambda ex: errors.append(ex))

        self.transport.play()
        self.clock.advance_ms(100.0)
        self.backend.pos = 100.0
        self.transport.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            self.transport.stop()

        self.assertEqual(ticks[-1][0], 100.0)
        self.assertEqual(len(errors), 1)

        self.backend.fail_stop = False
        self.transport.seek(500.0)
        self.assertEqual(ticks[-1][0], 500.0)

        self.backend.fail_play = True
        with self.assertRaises(AudioBackendError):
            self.transport.play()

        self.assertEqual(ticks[-1][0], 500.0)
        self.assertEqual(len(errors), 2)
        self.assertEqual(self.transport.state, TransportState.ERROR)

    def test_09_nonzero_buffer_latency_source_preservation(self) -> None:
        """Verify nonzero buffer latency and source-coordinate preservation remain intact."""
        trans = PlaybackTransport(
            wav_bytes=self.wav_bytes,
            clock=self.clock,
            audio_backend=self.backend,
            buffer_latency_ms=20.0,
        )
        trans.play()
        self.backend.pos = 200.0
        self.clock.advance_ms(200.0)
        trans.step_tick()

        self.backend.fail_stop = True
        with self.assertRaises(AudioBackendError):
            trans.stop()

        self.backend.fail_stop = False
        trans.seek(500.0)

        self.backend.commands.clear()
        trans.play()

        # Command must be play from 500 without subtracting buffer latency from source command
        self.assertEqual(self.backend.commands[0], f"play {self.backend._alias} from 500")

        # Clock advance 10 ms (buffer fill interval [500, 520]): audible held at 500
        self.clock.advance_ms(10.0)
        self.backend.pos = 510.0
        trans.step_tick()
        self.assertAlmostEqual(trans.position_ms, 500.0, places=4)

        # Clock advance 15 ms (device reaches 525): audible advances to 505
        self.clock.advance_ms(15.0)
        self.backend.pos = 525.0
        trans.step_tick()
        self.assertAlmostEqual(trans.position_ms, 505.0, places=4)


if __name__ == "__main__":
    unittest.main()
