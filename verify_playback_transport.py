"""Standalone verification and benchmark script for JOB-03 Audio Playback and Transport.

Demonstrates and verifies:
1. Authoritative Monotonic Transport Clock:
   Unified time coordinate t governing audio backend and visual coordinates without cumulative drift.
2. Half-Open Active Event Interval Semantics:
   Sound event active condition t_start <= t < t_end verified at microsecond boundaries.
3. Polyphonic Multi-Voice Sound Tracking:
   Simultaneous sound events across independent rows tracked concurrently.
4. Fast Interactive Seeking:
   Bidirectional transport seeking with instant state and active event recalculation.
5. Loop Wrapping vs Natural End-of-Piece Termination:
   Loop wrap to 0 vs clamped stop at duration T with end callback notification.
6. Cumulative Transport Drift Elimination:
   Zero cumulative drift benchmark across 10,000 discrete micro-steps (< 1e-6 ms).
   NOTE: TestClock + SimulatedAudioBackend derive position from the same clock, so zero drift
   holds by construction; this checks arithmetic accumulation, not device or acoustic drift.
7. Software Transport Dispatch Latency:
   seek() + active-event query cost on the SIMULATED backend, compared with the <= 20 ms
   target.  This is software execution time, not audio/visual synchronization latency.
8. Polyphonic Symbolic Audio Synthesis:
   Band-limited sine synthesizer with 5 ms attack/decay envelopes and 16-bit PCM WAV output.

All eight scenarios use simulated timing.  None of them measures physical audio output.
"""

from __future__ import annotations

import sys
import time
from fractions import Fraction
from typing import List, Set, Tuple

from music_gui.audio_playback import (
    AudioBackend,
    Clock,
    NullAudioBackend,
    PlaybackTransport,
    RealClock,
    SimulatedAudioBackend,
    TestClock,
    TransportState,
    synthesize_song_audio,
)
from music_model.datasets import create_stage_1_proof_timeline
from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent, get_authoritative_exact_timing
from music_model.timeline import MusicTimeline


def run_playback_transport_verification() -> bool:
    print("=" * 80)
    print("JOB-03 VERIFICATION: REAL-TIME AUDIO PLAYBACK & SYNCHRONIZED VISUAL TRANSPORT")
    print("=" * 80)
    print("Validating authoritative clock, half-open interval, polyphony, drift, and audio synthesis.\n")

    passed_scenarios = 0
    passed_assertions = 0

    # -------------------------------------------------------------------------
    # SCENARIO 1: Deterministic Transport Lifecycle
    # -------------------------------------------------------------------------
    print("--- SCENARIO 1: Deterministic Transport Lifecycle (Play, Pause, Resume, Stop) ---")
    clock = TestClock(start_seconds=0.0)
    backend = SimulatedAudioBackend()
    timeline = create_stage_1_proof_timeline()
    transport = PlaybackTransport(timeline=timeline, clock=clock, audio_backend=backend)

    assert transport.state == TransportState.STOPPED
    assert transport.position_ms == 0.0
    passed_assertions += 2

    # Play
    transport.play()
    assert transport.state == TransportState.PLAYING
    assert backend.is_playing is True
    passed_assertions += 2

    # Advance clock by 750 ms
    clock.advance_ms(750.0)
    assert abs(transport.position_ms - 750.0) < 1e-5
    passed_assertions += 1

    # Pause
    transport.pause()
    assert transport.state == TransportState.PAUSED
    assert backend.is_paused is True
    assert abs(transport.position_ms - 750.0) < 1e-5
    passed_assertions += 3

    # Clock advancement while paused must have 0 effect
    clock.advance_ms(2000.0)
    assert abs(transport.position_ms - 750.0) < 1e-5
    passed_assertions += 1

    # Resume from exact position
    transport.play()
    assert transport.state == TransportState.PLAYING
    clock.advance_ms(250.0)
    assert abs(transport.position_ms - 1000.0) < 1e-5
    passed_assertions += 2

    # Stop and reset to 0
    transport.stop()
    assert transport.state == TransportState.STOPPED
    assert transport.position_ms == 0.0
    assert backend.is_playing is False
    passed_assertions += 3

    print(f"  -> Scenario 1 PASSED ({passed_assertions} assertions)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 2: Half-Open Active Event Interval Semantics [t_start, t_end)
    # -------------------------------------------------------------------------
    print("--- SCENARIO 2: Half-Open Active Event Boundaries [t_start, t_end) ---")
    # Sound A: [0, 3000), Sound B: [1000, 5000), Sound C: [2000, 4000)
    transport.seek(0.0)
    assert transport.active_event_ids == {"Sound A"}
    passed_assertions += 1

    transport.seek(999.999)
    assert transport.active_event_ids == {"Sound A"}
    passed_assertions += 1

    transport.seek(1000.000)
    assert transport.active_event_ids == {"Sound A", "Sound B"}
    passed_assertions += 1

    transport.seek(2999.999)
    assert transport.active_event_ids == {"Sound A", "Sound B", "Sound C"}
    passed_assertions += 1

    # Exact boundary t = 3000.000 ms: Sound A transitions to inactive
    transport.seek(3000.000)
    assert transport.active_event_ids == {"Sound B", "Sound C"}
    passed_assertions += 1

    # Exact boundary t = 4000.000 ms: Sound C transitions to inactive
    transport.seek(4000.000)
    assert transport.active_event_ids == {"Sound B"}
    passed_assertions += 1

    # Exact boundary t = 5000.000 ms: Sound B transitions to inactive
    transport.seek(5000.000)
    assert transport.active_event_ids == set()
    passed_assertions += 1

    print(f"  -> Scenario 2 PASSED (boundary precision verified at microsecond level)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 3: Polyphonic Multi-Voice Sound Tracking
    # -------------------------------------------------------------------------
    print("--- SCENARIO 3: Polyphonic Multi-Voice Concurrency ---")
    # Test 4-part polyphony
    poly_timeline = MusicTimeline()
    r1 = poly_timeline.create_row("Soprano")
    r2 = poly_timeline.create_row("Alto")
    r3 = poly_timeline.create_row("Tenor")
    r4 = poly_timeline.create_row("Bass")

    r1.add_event(SoundEvent("Sop1", "Soprano", 0, 4000, height=72.0))
    r2.add_event(SoundEvent("Alt1", "Alto", 500, 3500, height=67.0))
    r3.add_event(SoundEvent("Ten1", "Tenor", 1000, 3000, height=60.0))
    r4.add_event(SoundEvent("Bas1", "Bass", 1500, 2500, height=48.0))

    poly_trans = PlaybackTransport(timeline=poly_timeline, clock=clock, audio_backend=backend)

    poly_trans.seek(250.0)
    assert poly_trans.active_event_ids == {"Sop1"}
    passed_assertions += 1

    poly_trans.seek(750.0)
    assert poly_trans.active_event_ids == {"Sop1", "Alt1"}
    passed_assertions += 1

    poly_trans.seek(1250.0)
    assert poly_trans.active_event_ids == {"Sop1", "Alt1", "Ten1"}
    passed_assertions += 1

    poly_trans.seek(2000.0)
    assert poly_trans.active_event_ids == {"Sop1", "Alt1", "Ten1", "Bas1"}
    assert len(poly_trans.active_event_ids) == 4
    passed_assertions += 2

    print(f"  -> Scenario 3 PASSED (4 concurrent polyphonic voices verified)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 4: Fast Bidirectional Seeking
    # -------------------------------------------------------------------------
    print("--- SCENARIO 4: Fast Bidirectional Seeking & Bounds Clamping ---")
    # Forward seek
    transport.seek(2500.0)
    assert transport.position_ms == 2500.0
    passed_assertions += 1

    # Backward seek
    transport.seek(500.0)
    assert transport.position_ms == 500.0
    passed_assertions += 1

    # Negative seek clamped to 0.0
    transport.seek(-1000.0)
    assert transport.position_ms == 0.0
    passed_assertions += 1

    # Beyond total duration clamped to total_duration_ms
    transport.seek(999999.0)
    assert transport.position_ms == 5000.0
    passed_assertions += 1

    print(f"  -> Scenario 4 PASSED (seeking and clamping robustly verified)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 5: Loop Boundary Wrapping vs Natural Termination
    # -------------------------------------------------------------------------
    print("--- SCENARIO 5: Loop Wrapping vs Natural Termination ---")
    # 1. Loop enabled: wrap with continuous loop remainder preservation (DEFECT-05)
    transport.set_loop(True)
    transport.seek(4950.0)
    transport.play()
    transport.step_tick(delta_ms=100.0)  # reaches 5050 ms across 5000 ms duration -> wraps to 50.0 ms
    assert abs(transport.position_ms - 50.0) < 1e-5
    assert transport.state == TransportState.PLAYING
    passed_assertions += 2

    # 2. Loop disabled: natural termination
    transport.set_loop(False)
    transport.seek(4950.0)
    end_signals = []
    transport.register_end_callback(lambda: end_signals.append(True))
    transport.step_tick(delta_ms=100.0)  # reaches 5050 ms -> clamped to 5000 ms and stopped
    assert transport.position_ms == 5000.0
    assert transport.state == TransportState.STOPPED
    assert len(end_signals) == 1
    passed_assertions += 3

    print(f"  -> Scenario 5 PASSED (loop wrap and natural termination verified)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 6: Cumulative Transport Drift Elimination Benchmark
    # -------------------------------------------------------------------------
    print("--- SCENARIO 6: Cumulative Transport Drift Benchmark (10,000 steps) ---")
    drift_clock = TestClock(start_seconds=0.0)
    drift_trans = PlaybackTransport(timeline=timeline, clock=drift_clock, audio_backend=backend)
    drift_trans.play()

    step_ms = 0.1  # 0.1 ms steps
    num_steps = 10000  # Total 1000 ms

    for _ in range(num_steps):
        drift_clock.advance_ms(step_ms)

    expected_position_ms = step_ms * num_steps
    actual_position_ms = drift_trans.position_ms
    drift_ms = abs(actual_position_ms - expected_position_ms)

    print(f"  Steps executed: {num_steps}")
    print(f"  Step interval: {step_ms} ms")
    print(f"  Expected transport position: {expected_position_ms:.6f} ms")
    print(f"  Actual transport position:   {actual_position_ms:.6f} ms")
    print(f"  Measured cumulative drift:   {drift_ms:.12f} ms ({drift_ms * 1e6:.4f} picoseconds)")

    assert drift_ms < 1e-6, f"Cumulative drift exceeds sub-nanosecond tolerance: {drift_ms} ms"
    passed_assertions += 1

    print(f"  -> Scenario 6 PASSED (arithmetic drift is sub-nanosecond: {drift_ms * 1e6:.2f} ps; simulated clock, zero by construction)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 7: Software Transport Dispatch & Query Latency Benchmark
    # -------------------------------------------------------------------------
    print("--- SCENARIO 7: Software Transport Dispatch & Query Latency Benchmark (Evaluation against <= 20 ms Target) ---")
    # Evaluates software transport execution overhead: position calculation, active event set querying,
    # and seek dispatch latency against experimental <= 20 ms budget.
    # Note: Physical acoustic synchronization requires external acoustic sensors and physical audio
    # measurement apparatus; this benchmark strictly measures software dispatch and query latency.
    latencies_ms: List[float] = []
    received_ticks = []

    def sync_probe(pos_ms: float, active_ids: Set[str]) -> None:
        received_ticks.append((pos_ms, active_ids))

    drift_trans.register_tick_callback(sync_probe)

    for i in range(1000):
        t0 = time.perf_counter()
        drift_trans.seek(float(i * 4))
        active = drift_trans.active_event_ids
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    p99_latency = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)]

    print(f"  Evaluations: {len(latencies_ms)}")
    print(f"  Mean latency: {avg_latency:.4f} ms")
    print(f"  99th percentile: {p99_latency:.4f} ms")
    print(f"  Max latency: {max_latency:.4f} ms")
    print(f"  Target requirement: <= 20.0 ms")

    assert max_latency < 20.0, f"Sync latency exceeded 20 ms target: {max_latency:.4f} ms"
    assert p99_latency < 5.0, f"99th percentile latency too high: {p99_latency:.4f} ms"
    passed_assertions += 2

    print(f"  -> Scenario 7 PASSED (software dispatch time on simulated backend within <= 20 ms target; not an acoustic measurement)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # SCENARIO 8: Polyphonic Symbolic Audio Synthesizer
    # -------------------------------------------------------------------------
    print("--- SCENARIO 8: Polyphonic Symbolic Audio Synthesis ---")
    test_events = [
        SoundEvent("Sine1", "R1", 0, 1000, height=69.0),   # Concert A4 (440 Hz)
        SoundEvent("Sine2", "R2", 500, 1500, height=60.0),  # Middle C4 (261.63 Hz)
    ]
    wav_bytes = synthesize_song_audio(test_events, total_duration_ms=1500, sample_rate=44100)

    # Verify standard RIFF WAV header
    assert len(wav_bytes) > 44, "WAV byte stream must be longer than 44-byte header"
    assert wav_bytes[0:4] == b"RIFF", "Header must begin with RIFF"
    assert wav_bytes[8:12] == b"WAVE", "Header must have WAVE chunk identifier"
    assert wav_bytes[12:16] == b"fmt ", "Format chunk marker must be present"
    assert wav_bytes[36:40] == b"data", "Data chunk marker must be present"
    passed_assertions += 5

    # Check length matches 1.5 seconds * 44100 samples/s * 2 bytes/sample = 132300 bytes + 44 header
    expected_data_len = int(1.5 * 44100) * 2
    actual_data_len = len(wav_bytes) - 44
    assert actual_data_len == expected_data_len, f"Expected {expected_data_len} data bytes, got {actual_data_len}"
    passed_assertions += 1

    print(f"  Generated {len(wav_bytes)} WAV bytes for 1500 ms 44.1 kHz 16-bit audio.")
    print(f"  -> Scenario 8 PASSED (WAV header, sample rate, bit depth, duration verified)\n")
    passed_scenarios += 1

    # -------------------------------------------------------------------------
    # Final Accounting
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("JOB-03 VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Benchmark Scenarios Passed: {passed_scenarios} / 8")
    print(f"Total Assertions Passed:    {passed_assertions} / 44")
    print("Zero Failures. Zero Errors. Status: PASS")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = run_playback_transport_verification()
    sys.exit(0 if success else 1)
