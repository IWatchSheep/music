"""JOB-03 consolidated refactor: regression coverage for defects D1-D8.

All tests here are deterministic and need no audio hardware.

`FakeWinmm` models the Windows MCI waveaudio driver at the `winmm.mciSendStringW`
level, so the production `WindowsMciAudioBackend` (including `_send_mci` and its ctypes
buffers) is exercised unmodified.  The fake reproduces device behaviour that was
observed on real hardware during the JOB-03 investigation and the refactor probes
(silent WAV only):

- aliases are thread-affine: a command from a non-opening thread returns 263;
- `status length` is the floor of the exact media duration (22070 frames @ 44.1 kHz
  -> exact 500.453515 ms, reported 500);
- at end of media the device stops itself: mode 'stopped', position == length;
- `seek` leaves the device in mode 'stopped'; `stop` does not rewind the position;
- `pause`/`resume` on a stopped device return 302; `play from`/`seek to` beyond the
  length return 282;
- position advances with time and is reported as an integer millisecond count.

Optional fault injection models an unexpected early stop and failing commands.
"""

from __future__ import annotations

import gc
import io
import math
import os
import shutil
import struct
import tempfile
import threading
import unittest
import wave
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from music_gui.audio_playback import (
    AudioBackendError,
    ManualScheduler,
    MciThreadOwnershipError,
    PlaybackTransport,
    SimulatedAudioBackend,
    TestClock,
    TkScheduler,
    TransportClosedError,
    TransportSnapshot,
    TransportState,
    TransportThreadError,
    WindowsMciAudioBackend,
    get_wav_duration_ms,
)
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline


# -----------------------------------------------------------------------------
# Test fixtures
# -----------------------------------------------------------------------------


def silent_wav(frames: int, rate: int = 44100) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


MCI_ERRORS = {
    263: "The specified device is not open or is not recognized by MCI.",
    282: "The specified parameter is out of range for the specified command.",
    302: "Cannot carry out the commands in the order specified.",
}


class _FakeDevice:
    def __init__(self, path: str, owner: int, clock: TestClock) -> None:
        with wave.open(path, "rb") as wf:
            frames, rate = wf.getnframes(), wf.getframerate()
        self.path = path
        self.exact_ms = frames * 1000.0 / rate
        self.length = int(math.floor(self.exact_ms))
        self.owner = owner
        self.clock = clock
        self.mode = "stopped"
        self.pos = 0.0
        self.anchor: Optional[Tuple[float, float]] = None
        self.early_stop_at: Optional[int] = None

    def update(self) -> None:
        if self.mode == "playing" and self.anchor is not None:
            t0, p0 = self.anchor
            p = p0 + (self.clock.now_seconds() - t0) * 1000.0
            limit = self.length if self.early_stop_at is None else min(self.length, self.early_stop_at)
            if p >= limit:
                self.mode, self.pos, self.anchor = "stopped", float(limit), None
            else:
                self.pos = p

    def start(self, from_ms: float) -> None:
        self.mode, self.pos = "playing", float(from_ms)
        self.anchor = (self.clock.now_seconds(), float(from_ms))
        self.update()


class FakeWinmm:
    """Behavioural model of winmm's MCI string interface (see module docstring)."""

    def __init__(self, clock: TestClock) -> None:
        self.clock = clock
        self.devices: Dict[str, _FakeDevice] = {}
        self.log: List[Tuple[int, str, int]] = []   # (thread id, command, return code)
        self.fail: Dict[str, int] = {}              # "verb" or "status position" -> code (persistent)
        self.early_stop_at: Optional[int] = None

    def _code(self, command: str, code: int) -> int:
        self.log.append((threading.get_ident(), command, code))
        return code

    def mciGetErrorStringW(self, code, buf, size) -> int:  # noqa: N802 (winmm name)
        buf.value = MCI_ERRORS.get(code, f"MCI error {code}")
        return 1

    def mciSendStringW(self, command, buffer, size, hwnd) -> int:  # noqa: N802 (winmm name)
        parts = command.split()
        verb = parts[0]
        if verb == "open":
            path = command.split('"')[1]
            alias = parts[parts.index("alias") + 1]
            if not os.path.exists(path):
                return self._code(command, 263)
            dev = _FakeDevice(path, threading.get_ident(), self.clock)
            dev.early_stop_at = self.early_stop_at
            self.devices[alias] = dev
            if buffer is not None:
                buffer.value = "1"
            return self._code(command, 0)

        alias = parts[1] if len(parts) > 1 else ""
        dev = self.devices.get(alias)
        if dev is None or dev.owner != threading.get_ident():
            return self._code(command, 263)
        key2 = f"{verb} {parts[2]}" if len(parts) > 2 else verb
        for key in (key2, verb):
            if key in self.fail:
                return self._code(command, self.fail[key])

        dev.update()
        out = ""
        if verb == "set":
            pass
        elif verb == "status":
            what = parts[2]
            out = {"length": str(dev.length), "mode": dev.mode, "position": str(int(math.floor(dev.pos)))}[what]
        elif verb == "play":
            n = int(parts[3]) if len(parts) >= 4 and parts[2] == "from" else int(dev.pos)
            if n > dev.length:
                return self._code(command, 282)
            dev.start(n)
        elif verb == "pause":
            if dev.mode == "stopped":
                return self._code(command, 302)
            if dev.mode == "playing":
                dev.mode, dev.anchor = "paused", None
        elif verb == "resume":
            if dev.mode == "stopped":
                return self._code(command, 302)
            if dev.mode == "paused":
                dev.start(dev.pos)
        elif verb == "stop":
            dev.mode, dev.anchor = "stopped", None
        elif verb == "seek":
            n = int(parts[3])
            if n > dev.length:
                return self._code(command, 282)
            dev.mode, dev.pos, dev.anchor = "stopped", float(n), None
        elif verb == "close":
            del self.devices[alias]
        else:
            return self._code(command, 263)
        if buffer is not None:
            buffer.value = out
        return self._code(command, 0)

    def commands(self, verb: Optional[str] = None) -> List[str]:
        return [c for (_, c, _) in self.log if verb is None or c.split()[0] == verb]

    def error_codes(self) -> List[int]:
        return [rc for (_, _, rc) in self.log if rc != 0]


class FakeMciHarness:
    """Production backend + transport on a fake driver, a TestClock and a ManualScheduler."""

    def __init__(self, test: unittest.TestCase, wav: bytes, timeline=None, loop: bool = False,
                 early_stop_at: Optional[int] = None, buffer_latency_ms: float = 0.0) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="job03_test_")
        test.addCleanup(shutil.rmtree, self.tmpdir, True)
        self.clock = TestClock(0.0)
        self.winmm = FakeWinmm(self.clock)
        self.winmm.early_stop_at = early_stop_at
        self.backend = WindowsMciAudioBackend(winmm=self.winmm, temp_dir=self.tmpdir)
        self.scheduler = ManualScheduler(self.clock)
        self.snaps: List[TransportSnapshot] = []
        self.ends: List[float] = []
        self.errors: List[Exception] = []
        self.transport = PlaybackTransport(
            timeline=timeline, wav_bytes=wav, audio_backend=self.backend,
            clock=self.clock, scheduler=self.scheduler, buffer_latency_ms=buffer_latency_ms,
        )
        self.transport.set_loop(loop)
        self.transport.add_snapshot_callback(self.snaps.append)
        self.transport.add_end_callback(lambda: self.ends.append(self.clock.now_seconds()))
        self.transport.add_error_callback(self.errors.append)
        test.addCleanup(self._close)

    def _close(self) -> None:
        if not self.transport.is_closed:
            try:
                self.transport.close()
            except Exception:
                pass

    @property
    def device(self) -> _FakeDevice:
        return self.winmm.devices[self.backend._alias]

    def run_until(self, predicate, limit_ms: float = 10000.0, step_ms: float = 5.0) -> None:
        waited = 0.0
        while not predicate() and waited < limit_ms:
            self.scheduler.advance(step_ms)
            waited += step_ms


def two_event_timeline(events: List[Tuple[str, int, int]]) -> MusicTimeline:
    tl = MusicTimeline()
    row = tl.create_row("R")
    for eid, s, e in events:
        row.add_event(SoundEvent(eid, "R", s, e))
    return tl


def membership(transport: PlaybackTransport, pos: float) -> frozenset:
    return frozenset(e.event_id for e in transport.get_active_events_at(pos))


# -----------------------------------------------------------------------------
# Fake driver self-validation (the mock must reproduce the recorded device facts)
# -----------------------------------------------------------------------------


class TestFakeDriverReproducesRecordedDeviceFacts(unittest.TestCase):

    def test_fake_reproduces_d1_d2_d3_device_facts(self) -> None:
        clock = TestClock(0.0)
        winmm = FakeWinmm(clock)
        tmp = tempfile.mkdtemp(prefix="job03_test_")
        self.addCleanup(shutil.rmtree, tmp, True)
        be = WindowsMciAudioBackend(winmm=winmm, temp_dir=tmp)
        be.load_wav_bytes(silent_wav(22070))
        a = be._alias
        self.assertEqual(be.device_length_ms, 500)                       # floored length
        be.play(0)
        clock.advance_ms(600)
        self.assertEqual(be._send_mci(f"status {a} mode", True), "stopped")      # self-stop
        self.assertEqual(be._send_mci(f"status {a} position", True), "500")      # at length
        with self.assertRaisesRegex(AudioBackendError, r"code 302"):
            be._send_mci(f"pause {a}")                                     # D3 command order
        with self.assertRaisesRegex(AudioBackendError, r"code 282"):
            be._send_mci(f"play {a} from 501")
        res = {}
        t = threading.Thread(target=lambda: res.setdefault("rc", winmm.mciSendStringW(f"status {a} mode", None, 0, None)))
        t.start(); t.join()
        self.assertEqual(res["rc"], 263)                                   # D1 thread affinity
        be.unload()


# -----------------------------------------------------------------------------
# D1 - thread ownership
# -----------------------------------------------------------------------------


class TestD1ThreadOwnership(unittest.TestCase):

    def test_ordinary_playback_advances_beyond_first_interval_without_263(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        threads_before = threading.active_count()
        h.transport.play()
        self.assertEqual(threading.active_count(), threads_before, "play() must not start a thread")
        h.scheduler.advance(15 * 20)                       # 20 scheduled updates
        self.assertEqual(h.transport.state, TransportState.PLAYING)
        self.assertEqual(h.winmm.error_codes(), [])
        tick_positions = [s.position_ms for s in h.snaps if s.reason == "tick"]
        self.assertGreaterEqual(len(tick_positions), 19)
        self.assertGreater(tick_positions[-1], 15.0)
        self.assertAlmostEqual(tick_positions[-1], 300.0, delta=1.0)
        # every MCI command ran on the opening (owner) thread
        self.assertEqual({tid for (tid, _, _) in h.winmm.log}, {threading.get_ident()})

    def test_pause_halts_device_after_scheduled_updates(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(300)
        h.transport.pause()
        self.assertEqual(h.device.mode, "paused")
        frozen = h.device.pos
        h.clock.advance_ms(500)
        h.device.update()
        self.assertEqual(h.device.pos, frozen)
        self.assertEqual(h.transport.state, TransportState.PAUSED)
        self.assertEqual(h.scheduler.pending_count, 0)

    def test_backend_refuses_cross_thread_commands_with_explicit_error(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100))
        h.transport.play()
        status_before = h.backend.get_status()
        result = {}

        def worker() -> None:
            for call in (h.backend.get_device_position_ms, h.backend.observe, h.backend.pause,
                         h.backend.stop, lambda: h.backend.seek(10.0), lambda: h.backend.play(0.0)):
                try:
                    call()
                except MciThreadOwnershipError as ex:
                    result.setdefault("errs", []).append(str(ex))
        t = threading.Thread(target=worker)
        t.start(); t.join()
        self.assertEqual(len(result["errs"]), 6)
        self.assertTrue(all("thread-affine" in e for e in result["errs"]))
        # a refused call does not change the backend's view of the device
        self.assertEqual(h.backend.get_status(), status_before)
        self.assertTrue(h.backend.is_playing)
        # the refused command never reached the driver
        self.assertNotIn(263, h.winmm.error_codes())
        # the device keeps working on its owner thread
        h.scheduler.advance(60)
        self.assertEqual(h.transport.state, TransportState.PLAYING)

    def test_transport_rejects_lifecycle_calls_from_non_owner_thread(self) -> None:
        tr = PlaybackTransport(timeline=two_event_timeline([("E", 0, 1000)]),
                               audio_backend=SimulatedAudioBackend(), clock=TestClock(0.0))
        caught = {}

        def worker() -> None:
            for name in ("play", "pause", "stop", "reset", "step_tick", "close"):
                try:
                    getattr(tr, name)()
                except TransportThreadError:
                    caught[name] = True
            try:
                tr.seek(10.0)
            except TransportThreadError:
                caught["seek"] = True
        t = threading.Thread(target=worker)
        t.start(); t.join()
        self.assertEqual(set(caught), {"play", "pause", "stop", "reset", "step_tick", "close", "seek"})
        self.assertEqual(tr.state, TransportState.STOPPED)
        tr.close()

    def test_query_failure_during_playback_shuts_audio_down(self) -> None:
        """The original D1 symptom: ERROR while the device kept playing.  Now audio is stopped."""
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(60)
        h.winmm.fail["status position"] = 263
        h.scheduler.advance(15)
        self.assertEqual(h.transport.state, TransportState.ERROR)
        self.assertEqual(len(h.errors), 1)
        self.assertEqual(h.device.mode, "stopped", "controlled shutdown must silence the device")
        self.assertIn(f"stop {h.backend._alias}", h.winmm.commands("stop"))
        self.assertEqual(h.scheduler.pending_count, 0)
        # preserved coordinate is the last committed one, not a guess
        last_tick = [s for s in h.snaps if s.reason == "tick"][-1]
        self.assertEqual(h.transport.snapshot.position_ms, last_tick.position_ms)
        del h.winmm.fail["status position"]
        h.transport.play()
        h.scheduler.advance(30)
        self.assertEqual(h.transport.state, TransportState.PLAYING)


# -----------------------------------------------------------------------------
# D2 - exact completion with integer-millisecond devices
# -----------------------------------------------------------------------------


class TestD2FractionalDurationCompletion(unittest.TestCase):

    def test_fractional_22070_frame_wav_completes_at_exact_duration(self) -> None:
        wav = silent_wav(22070)
        exact = get_wav_duration_ms(wav)
        self.assertAlmostEqual(exact, 500.4535147392, places=9)
        h = FakeMciHarness(self, wav)
        self.assertEqual(h.transport.total_duration_ms, exact)
        self.assertEqual(h.backend.device_length_ms, 500)
        h.transport.play()
        h.run_until(lambda: h.transport.state != TransportState.PLAYING, limit_ms=2000)
        self.assertEqual(h.transport.state, TransportState.STOPPED)
        self.assertEqual(h.transport.snapshot.position_ms, exact)        # exact, not 500
        self.assertEqual(h.transport.snapshot.reason, "end")
        self.assertEqual(len(h.ends), 1)
        self.assertEqual(h.errors, [])
        self.assertEqual(h.scheduler.pending_count, 0)
        # completion observed within one update interval of the device stopping (t=500 ms)
        self.assertLessEqual(h.ends[0] * 1000.0, 500.0 + 15.0 + 1e-6)
        self.assertEqual(h.winmm.error_codes(), [])

    def test_exact_1000_ms_control_completes(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100))
        h.transport.play()
        h.run_until(lambda: h.transport.state != TransportState.PLAYING, limit_ms=3000)
        self.assertEqual(h.transport.state, TransportState.STOPPED)
        self.assertEqual(h.transport.snapshot.position_ms, 1000.0)
        self.assertEqual(len(h.ends), 1)

    def test_fractional_duration_looping(self) -> None:
        wav = silent_wav(22070)
        exact = get_wav_duration_ms(wav)
        h = FakeMciHarness(self, wav, loop=True)
        h.transport.play()
        h.scheduler.advance(1700)                         # > 3 cycles
        self.assertEqual(h.transport.state, TransportState.PLAYING)
        loops = [s for s in h.snaps if s.reason == "loop"]
        self.assertGreaterEqual(len(loops), 3)
        for s in loops:
            # device stopped at end of media -> restart at source 0 (no remainder available)
            self.assertEqual(s.position_ms, 0.0)
        positions = [s.position_ms for s in h.snaps if s.state == TransportState.PLAYING]
        self.assertTrue(all(0.0 <= p < exact for p in positions))
        epochs = [s.epoch for s in loops]
        self.assertEqual(epochs, sorted(set(epochs)))
        self.assertEqual(len(h.ends), 0)
        self.assertEqual(h.errors, [])
        self.assertEqual(h.winmm.error_codes(), [])

    def test_unexpected_early_device_stop_is_an_error_not_completion(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100), early_stop_at=400)
        h.transport.play()
        h.run_until(lambda: h.transport.state != TransportState.PLAYING, limit_ms=2000)
        self.assertEqual(h.transport.state, TransportState.ERROR)
        self.assertEqual(len(h.ends), 0)
        self.assertEqual(len(h.errors), 1)
        self.assertIn("stopped unexpectedly", str(h.errors[0]))
        self.assertLess(h.transport.snapshot.position_ms, 1000.0)

    def test_timeline_longer_than_media_continues_as_silent_tail(self) -> None:
        # Media 500.45 ms, timeline event ends at 800 ms: transport must reach 800 and stop.
        wav = silent_wav(22070)
        tl = two_event_timeline([("A", 0, 300), ("B", 300, 800)])
        h = FakeMciHarness(self, wav, timeline=tl)
        self.assertEqual(h.transport.total_duration_ms, 800.0)
        h.transport.play()
        h.run_until(lambda: h.transport.state != TransportState.PLAYING, limit_ms=3000)
        self.assertEqual(h.transport.state, TransportState.STOPPED)
        self.assertEqual(h.transport.snapshot.position_ms, 800.0)
        playing = [s.position_ms for s in h.snaps if s.state == TransportState.PLAYING and s.reason == "tick"]
        self.assertTrue(any(p > 500.46 for p in playing), "progress must continue past media end")
        self.assertEqual(playing, sorted(playing))
        self.assertEqual(len(h.ends), 1)


# -----------------------------------------------------------------------------
# D3 - backend flags reconciled with the device
# -----------------------------------------------------------------------------


def _rounding_class(total_ms: float) -> str:
    """'exact' if T is a multiple of 1e-6 ms; else whether round(T, 6) rounds 'up' or 'down'."""
    r = round(total_ms, 6)
    if r == total_ms:
        return "exact"
    return "up" if r > total_ms else "down"


# (frames, sample rate): fractional durations rounding up and down at 6 decimals, exact decimals,
# integer-ms controls, a sub-millisecond media (device length 0), and several sample rates.
COMPLETION_CASES = [
    (22070, 44100), (22071, 44100), (22069, 44100), (44101, 44100), (33333, 44100), (7, 44100),
    (1000, 22050), (9999, 11025), (12345, 48000), (10001, 8000), (4801, 48000), (96001, 96000),
    (16001, 32000), (44100, 44100), (22050, 44100), (48000, 48000), (8000, 8000),
]


class TestD2CompletionPredicateAcrossDurations(unittest.TestCase):
    """Fractional-duration completion for ALL durations (ChatGPT audit: 22,071 frames never completed).

    The thirteenth-revision predicate round(p, 6) >= T rounds only the left side; with confirmed
    end of media p == T exactly, so completion failed whenever round(T, 6) < T.
    """

    def test_case_table_covers_round_up_round_down_and_exact(self) -> None:
        classes = {_rounding_class(f * 1000.0 / r) for f, r in COMPLETION_CASES}
        self.assertEqual(classes, {"up", "down", "exact"})
        self.assertEqual(_rounding_class(22070 * 1000.0 / 44100), "up")
        self.assertEqual(_rounding_class(22071 * 1000.0 / 44100), "down")

    def _complete(self, frames: int, rate: int, buffer_latency_ms: float = 0.0) -> None:
        wav = silent_wav(frames, rate)
        exact = get_wav_duration_ms(wav)
        h = FakeMciHarness(self, wav, buffer_latency_ms=buffer_latency_ms)
        self.assertEqual(h.transport.total_duration_ms, exact)       # source duration unrounded
        h.transport.play()
        h.run_until(lambda: h.transport.state != TransportState.PLAYING, limit_ms=exact + 2000)
        tag = f"{frames}@{rate} T={exact!r} ({_rounding_class(exact)}) L={buffer_latency_ms}"
        self.assertEqual(h.transport.state, TransportState.STOPPED, tag)
        self.assertEqual(h.transport.snapshot.position_ms, exact, tag)   # exact T, never rounded
        self.assertEqual(h.transport.snapshot.reason, "end", tag)
        self.assertEqual(h.transport.snapshot.active_event_ids, frozenset(), tag)
        self.assertEqual(len(h.ends), 1, tag)
        self.assertEqual(h.errors, [], tag)
        self.assertEqual(h.scheduler.pending_count, 0, tag)
        # Completion is observed no later than one update (+ step granularity) after the evidence:
        # the device stopping at its floored length.  With buffer latency the drain clock starts when
        # end of media is OBSERVED (up to one update after it happened), so allow one more update.
        updates = 2 if buffer_latency_ms > 0 else 1
        latest = (h.backend.device_length_ms + buffer_latency_ms + updates * h.transport.tick_interval_ms + 5.0) / 1000.0
        self.assertLessEqual(h.ends[0], latest + 1e-9, tag)
        # No snapshot before completion claimed the end; positions never exceed T.
        before_end = [s for s in h.snaps if s.state == TransportState.PLAYING]
        self.assertTrue(all(s.position_ms <= exact for s in before_end), tag)

    def _loop(self, frames: int, rate: int, buffer_latency_ms: float = 0.0) -> None:
        wav = silent_wav(frames, rate)
        exact = get_wav_duration_ms(wav)
        h = FakeMciHarness(self, wav, loop=True, buffer_latency_ms=buffer_latency_ms)
        h.transport.play()
        h.scheduler.advance(max(4 * exact, 200.0) + 4 * (buffer_latency_ms + 40.0))
        tag = f"{frames}@{rate} T={exact!r} ({_rounding_class(exact)}) L={buffer_latency_ms}"
        loops = [s for s in h.snaps if s.reason == "loop"]
        self.assertGreaterEqual(len(loops), 3, tag)
        self.assertEqual(h.transport.state, TransportState.PLAYING, tag)
        self.assertEqual(h.ends, [], tag)
        self.assertEqual(h.errors, [], tag)
        self.assertNotIn(282, h.winmm.error_codes(), tag)
        for s in h.snaps:
            if s.state == TransportState.PLAYING:
                self.assertGreaterEqual(s.position_ms, 0.0, tag)
                self.assertLess(s.position_ms, exact, tag)
        if buffer_latency_ms == 0.0:
            # Device stops at end of media: no remainder exists, every cycle restarts at 0.
            self.assertTrue(all(s.position_ms == 0.0 for s in loops), tag)

    def test_natural_completion_for_every_case(self) -> None:
        for frames, rate in COMPLETION_CASES:
            with self.subTest(frames=frames, rate=rate):
                self._complete(frames, rate)

    def test_looping_for_every_case(self) -> None:
        for frames, rate in COMPLETION_CASES:
            with self.subTest(frames=frames, rate=rate):
                self._loop(frames, rate)

    def test_frame_sweep_22000_to_22150_at_44100(self) -> None:
        downs = 0
        for frames in range(22000, 22151):
            downs += _rounding_class(frames * 1000.0 / 44100) == "down"
            with self.subTest(frames=frames):
                self._complete(frames, 44100)
        self.assertGreater(downs, 30)        # the sweep really contains round-down durations

    def test_nonzero_buffer_latency_completion_and_looping(self) -> None:
        for frames, rate in [(22070, 44100), (22071, 44100), (44100, 44100), (12345, 48000)]:
            for latency in (5.0, 20.0):
                with self.subTest(frames=frames, rate=rate, latency=latency):
                    self._complete(frames, rate, buffer_latency_ms=latency)
                    self._loop(frames, rate, buffer_latency_ms=latency)

    # -- backend-independent: a simulator whose position stops exactly at fractional T ----------

    def _capped_transport(self, frames: int, rate: int, cap_offset_ms: float, loop: bool = False):
        wav = silent_wav(frames, rate)
        exact = get_wav_duration_ms(wav)
        cap = exact - cap_offset_ms

        class CappedAt(SimulatedAudioBackend):
            def get_device_position_ms(self):
                pos = super().get_device_position_ms()
                return min(cap, pos) if pos is not None else None
        clock = TestClock(0.0)
        sched = ManualScheduler(clock)
        tr = PlaybackTransport(wav_bytes=wav, audio_backend=CappedAt(clock=clock), clock=clock, scheduler=sched)
        tr.set_loop(loop)
        self.addCleanup(tr.close)
        snaps: List[TransportSnapshot] = []
        tr.add_snapshot_callback(snaps.append)
        tr.play()
        return tr, sched, exact, snaps

    def test_simulated_device_capped_exactly_at_fractional_end_completes(self) -> None:
        for frames, rate in [(22070, 44100), (22071, 44100), (9999, 11025)]:
            with self.subTest(frames=frames, rate=rate):
                tr, sched, exact, snaps = self._capped_transport(frames, rate, 0.0)
                sched.advance(exact + 100)
                self.assertEqual(tr.state, TransportState.STOPPED)
                self.assertEqual(tr.snapshot.position_ms, exact)
                tr2, sched2, _, snaps2 = self._capped_transport(frames, rate, 0.0, loop=True)
                sched2.advance(exact + 100)
                self.assertEqual(tr2.state, TransportState.PLAYING)
                self.assertTrue(any(s.reason == "loop" for s in snaps2))

    def test_no_premature_completion_without_evidence(self) -> None:
        # Progress stuck 10 ns (20x the tolerance) or 1 ms short of T is NOT completion.
        for offset in (1e-5, 1.0):
            with self.subTest(offset_ms=offset):
                tr, sched, exact, snaps = self._capped_transport(22071, 44100, offset)
                sched.advance(3000)
                self.assertEqual(tr.state, TransportState.PLAYING)
                self.assertLess(tr.snapshot.position_ms, exact)
                self.assertFalse(any(s.reason == "end" for s in snaps))

    def test_progress_within_tolerance_below_end_completes_and_loops_from_zero(self) -> None:
        # (22070 frames, 4e-7 ms short): round(p, 6) = 500.453514 falls below T - tol, so a
        # p-mod-T remainder would restart the device ~0.0005 ms before the end instead of at 0.
        for frames, offset in [(22071, 1e-7), (22070, 4e-7)]:
            with self.subTest(frames=frames, offset=offset):
                tr, sched, exact, snaps = self._capped_transport(frames, 44100, offset)
                sched.advance(exact + 100)
                self.assertEqual(tr.state, TransportState.STOPPED)
                self.assertEqual(tr.snapshot.position_ms, exact)   # published as exact T, not T - offset
                tr2, sched2, _, snaps2 = self._capped_transport(frames, 44100, offset, loop=True)
                sched2.advance(exact + 30)
                loops = [s for s in snaps2 if s.reason == "loop"]
                self.assertTrue(loops)
                self.assertEqual(loops[0].position_ms, 0.0)        # not p mod T ~= T

    def test_predicate_equals_previous_rounding_where_previous_was_well_defined(self) -> None:
        """For T that is a multiple of 1e-6 ms, p >= T - 5e-7 accepts exactly what round(p, 6) >= T did."""
        tr = PlaybackTransport(audio_backend=SimulatedAudioBackend(), clock=TestClock(0.0))
        self.addCleanup(tr.close)
        for total in (1.0, 500.0, 1000.0, 5000.0, 257.1875, 1250.125, 999.999999, 123456.000001):
            tr._total_duration_ms = total
            for k in range(-30, 31):
                if k in (-5, 5):
                    continue          # exact half-way ties: float representation decides either way
                p = total + k * 1e-7
                with self.subTest(total=total, k=k):
                    self.assertEqual(tr._has_reached_end(p), round(p, 6) >= total)


class TestD3DeviceStateReconciliation(unittest.TestCase):

    def test_flags_reconcile_after_natural_end_and_no_302_is_sent(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100), timeline=two_event_timeline([("A", 0, 2000)]))
        # timeline (2000) longer than media (1000): device ends while transport PLAYING
        h.transport.play()
        h.clock.advance_ms(1100)               # device self-stops at 1000; no update yet
        self.assertTrue(h.backend.is_playing)  # unreconciled cache (before any observation)
        h.transport.pause()                    # observation happens inside pause()
        self.assertFalse(h.backend.is_playing)
        self.assertFalse(h.backend.is_paused)
        self.assertNotIn(302, h.winmm.error_codes())
        self.assertNotIn(f"pause {h.backend._alias}", h.winmm.commands("pause"))
        self.assertEqual(h.transport.state, TransportState.PAUSED)
        h.transport.play()                     # no resumable session -> play from, not resume
        self.assertEqual(h.winmm.commands("resume"), [])
        self.assertNotIn(302, h.winmm.error_codes())
        self.assertEqual(h.transport.state, TransportState.PLAYING)

    def test_backend_pause_on_self_stopped_device_without_prior_observation(self) -> None:
        """Backend-level guard: pause() checks the device mode itself (no 302)."""
        h = FakeMciHarness(self, silent_wav(4410))     # 100 ms media
        h.backend.play(0)
        h.clock.advance_ms(300)                        # device self-stopped; nobody observed it
        self.assertTrue(h.backend.is_playing)          # stale acknowledgement cache
        h.backend.pause()                              # must not raise MCI 302
        self.assertNotIn(302, h.winmm.error_codes())
        self.assertFalse(h.backend.is_playing)
        self.assertFalse(h.backend.can_resume)

    def test_seek_while_paused_leaves_device_stopped_and_resume_uses_play_from(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(300)
        h.transport.pause()
        h.transport.seek(1234.4)
        self.assertEqual(h.device.mode, "stopped")
        self.assertFalse(h.backend.is_paused)
        h.transport.play()
        self.assertIn(f"play {h.backend._alias} from 1234", h.winmm.commands("play"))
        self.assertEqual(h.winmm.commands("resume"), [])
        self.assertEqual(h.transport.snapshot.position_ms, 1234.4)      # exact source coordinate kept
        h.scheduler.advance(30)
        self.assertEqual(h.winmm.error_codes(), [])

    def test_seek_while_playing_restarts_device(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(150)
        h.transport.seek(900.0)
        self.assertEqual(h.device.mode, "playing")
        h.scheduler.advance(150)
        self.assertAlmostEqual(h.transport.snapshot.position_ms, 1050.0, delta=1.0)

    def test_seek_beyond_device_length_is_clamped_not_282(self) -> None:
        # exact duration 500.4535; nearest integer of the end is 500 == length (not 501)
        h = FakeMciHarness(self, silent_wav(22070))
        h.transport.seek(10_000.0)
        self.assertEqual(h.transport.snapshot.position_ms, h.transport.total_duration_ms)
        self.assertNotIn(282, h.winmm.error_codes())
        h.transport.play()                     # at end -> replay from 0
        self.assertIn(f"play {h.backend._alias} from 0", h.winmm.commands("play"))

    def test_resume_refuses_to_send_302_when_device_not_paused(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.backend.play(0)
        h.clock.advance_ms(100)
        h.backend.pause()
        h.device.mode = "stopped"              # external change behind the backend's back
        with self.assertRaises(AudioBackendError):
            h.backend.resume()
        self.assertEqual(h.winmm.commands("resume"), [])


# -----------------------------------------------------------------------------
# D4 / D6 - scheduling: single pending update, no obsolete callbacks
# -----------------------------------------------------------------------------


class TestD4D6Scheduling(unittest.TestCase):

    def _sim(self, duration_ms: int = 1000, loop: bool = False):
        clock = TestClock(0.0)
        sched = ManualScheduler(clock)
        tr = PlaybackTransport(timeline=two_event_timeline([("E", 0, duration_ms)]),
                               audio_backend=SimulatedAudioBackend(clock=clock), clock=clock, scheduler=sched)
        tr.set_loop(loop)
        self.addCleanup(tr.close)
        return tr, sched, clock

    def test_rapid_pause_play_keeps_at_most_one_pending_update(self) -> None:
        tr, sched, clock = self._sim(10_000)
        threads = threading.active_count()
        for i in range(200):
            tr.play()
            self.assertLessEqual(sched.pending_count, 1)
            if i % 3 == 0:
                sched.advance(7)
            tr.pause()
            self.assertEqual(sched.pending_count, 0)
        tr.play()
        self.assertEqual(sched.pending_count, 1)
        self.assertEqual(threading.active_count(), threads)
        sched.advance(150)
        self.assertEqual(sched.pending_count, 1)
        ticks = [s for s in [tr.snapshot] if s.reason == "tick"]
        self.assertTrue(ticks)

    def test_obsolete_callback_cannot_restart_stopped_or_superseded_transport(self) -> None:
        tr, sched, clock = self._sim(1000)
        tr.play()
        stale = sched._entries[0].callback              # captured before cancellation
        tr.stop()
        seq = tr.snapshot.sequence
        stale()                                          # e.g. already dequeued by an event loop
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(tr.snapshot.sequence, seq)
        self.assertEqual(sched.pending_count, 0)
        tr.play()
        stale()                                          # old generation vs new session
        self.assertEqual(sched.pending_count, 1)
        self.assertEqual(tr.snapshot.reason, "play")
        tr.close()
        stale2 = None
        self.assertEqual(sched.pending_count, 0)
        self.assertIsNone(stale2)

    def test_replay_inside_end_callback_at_natural_completion(self) -> None:
        tr, sched, clock = self._sim(300)
        replays = []

        def on_end() -> None:
            if not replays:
                replays.append(1)
                tr.play()
        tr.add_end_callback(on_end)
        tr.play()
        sched.advance(320)
        self.assertEqual(tr.state, TransportState.PLAYING)
        self.assertEqual(sched.pending_count, 1, "replay must own exactly one pending update")
        sched.advance(400)
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(tr.snapshot.position_ms, 300.0)
        self.assertEqual(sched.pending_count, 0)

    def test_replay_immediately_after_completion(self) -> None:
        tr, sched, clock = self._sim(300)
        tr.play()
        sched.advance(310)
        self.assertEqual(tr.state, TransportState.STOPPED)
        tr.play()
        self.assertEqual(tr.snapshot.position_ms, 0.0)
        self.assertEqual(sched.pending_count, 1)
        sched.advance(310)
        self.assertEqual(tr.state, TransportState.STOPPED)

    def test_tk_scheduler_drives_transport_on_tk_thread(self) -> None:
        import tkinter as tk
        from music_gui.audio_playback import RealClock
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        tr = PlaybackTransport(timeline=two_event_timeline([("E", 0, 200)]),
                               audio_backend=SimulatedAudioBackend(), clock=RealClock(),
                               scheduler=TkScheduler(root))
        seen = []
        tr.add_snapshot_callback(lambda s: seen.append((threading.get_ident(), s)))
        tr.play()
        root.after(600, root.quit)
        root.mainloop()
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(tr.snapshot.position_ms, 200.0)
        self.assertEqual({tid for tid, _ in seen}, {threading.get_ident()})
        self.assertGreater(len([s for _, s in seen if s.reason == "tick"]), 3)
        self.assertFalse(tr.has_pending_tick)
        tr.close()


# -----------------------------------------------------------------------------
# D5 - immutable coherent snapshots
# -----------------------------------------------------------------------------


class TestD5CoherentSnapshots(unittest.TestCase):

    def _transport(self):
        clock = TestClock(0.0)
        sched = ManualScheduler(clock)
        tl = two_event_timeline([("E0", 0, 300), ("E1", 300, 3000)])
        tr = PlaybackTransport(timeline=tl, audio_backend=SimulatedAudioBackend(clock=clock),
                               clock=clock, scheduler=sched)
        self.addCleanup(tr.close)
        return tr, sched, clock

    def test_snapshots_are_immutable(self) -> None:
        tr, sched, clock = self._transport()
        snap = tr.snapshot
        with self.assertRaises(Exception):
            snap.position_ms = 5.0  # type: ignore[misc]
        self.assertIsInstance(snap.active_event_ids, frozenset)

    def test_every_snapshot_is_internally_coherent_and_ordered(self) -> None:
        tr, sched, clock = self._transport()
        snaps: List[TransportSnapshot] = []
        tr.add_snapshot_callback(snaps.append)
        tr.play(); sched.advance(450); tr.pause(); tr.seek(100.0); tr.play(); sched.advance(120)
        tr.seek(2990.0); sched.advance(30); tr.stop(); tr.seek(299.999); tr.seek(300.0)
        self.assertGreater(len(snaps), 30)
        seqs = [s.sequence for s in snaps]
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual(len(set(seqs)), len(seqs))
        for s in snaps:
            self.assertEqual(s.active_event_ids, membership(tr, s.position_ms), s)

    def test_reentrant_publication_is_rejectable_by_sequence(self) -> None:
        """A callback that changes the transport makes later callbacks see a newer snapshot
        before the older one; sequence numbers let consumers discard the older one."""
        tr, sched, clock = self._transport()
        tr.play(); sched.advance(450)
        done = []

        def first(snap: TransportSnapshot) -> None:
            if snap.reason == "pause" and not done:
                done.append(1)
                tr.seek(100.0)               # nested publication during delivery
        received: List[TransportSnapshot] = []
        tr.add_snapshot_callback(first)
        tr.add_snapshot_callback(received.append)
        tr.pause()
        self.assertEqual([s.reason for s in received], ["seek", "pause"])   # arrival order
        latest = None
        for s in received:
            if s.supersedes(latest):
                latest = s
        self.assertEqual(latest.reason, "seek")
        self.assertEqual(latest.position_ms, 100.0)
        self.assertEqual(latest.active_event_ids, frozenset({"E0"}))

    def test_tick_callback_payload_comes_from_one_snapshot(self) -> None:
        tr, sched, clock = self._transport()
        pairs = []
        tr.add_tick_callback(lambda p, ids: pairs.append((p, frozenset(ids))))
        tr.play()
        sched.advance(600)
        for p, ids in pairs:
            self.assertEqual(ids, membership(tr, p))

    def test_position_getter_does_not_silently_fall_back(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100))
        h.transport.play()
        h.winmm.fail["status position"] = 263
        with self.assertRaises(AudioBackendError):
            _ = h.transport.position_ms
        self.assertEqual(h.transport.state, TransportState.PLAYING)  # a read changes nothing
        self.assertEqual(h.transport.snapshot.reason, "play")        # snapshot read: no I/O
        del h.winmm.fail["status position"]


# -----------------------------------------------------------------------------
# Half-open membership through the scheduled path
# -----------------------------------------------------------------------------


class TestHalfOpenMembershipDuringPlayback(unittest.TestCase):

    def test_boundaries_adjacent_overlapping_silence_and_completion(self) -> None:
        clock = TestClock(0.0)
        sched = ManualScheduler(clock)
        # adjacent A|B at 100, overlap C over B, silence gap [400,500), D ends the piece at 600
        tl = two_event_timeline([("A", 0, 100), ("B", 100, 300), ("C", 200, 400), ("D", 500, 600)])
        tr = PlaybackTransport(timeline=tl, audio_backend=SimulatedAudioBackend(clock=clock),
                               clock=clock, scheduler=sched, tick_interval_ms=5)
        self.addCleanup(tr.close)
        got: Dict[float, frozenset] = {}
        tr.add_snapshot_callback(lambda s: got.__setitem__(round(s.position_ms, 6), s.active_event_ids))
        tr.play()
        sched.advance(700)
        expect = {0.0: {"A"}, 95.0: {"A"}, 100.0: {"B"}, 200.0: {"B", "C"}, 295.0: {"B", "C"},
                  300.0: {"C"}, 400.0: set(), 450.0: set(), 500.0: {"D"}, 595.0: {"D"}, 600.0: set()}
        for pos, ids in expect.items():
            self.assertIn(pos, got)
            self.assertEqual(got[pos], frozenset(ids), pos)
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(tr.snapshot.active_event_ids, frozenset())

    def test_exact_rational_boundaries_are_respected(self) -> None:
        tl = MusicTimeline()
        r = tl.create_row("R")
        r.add_event(SoundEvent("T", "R", 333, 667, attributes={
            "exact_start_ms_rational": Fraction(1000, 3), "exact_end_ms_rational": Fraction(2000, 3)}))
        tr = PlaybackTransport(timeline=tl, audio_backend=SimulatedAudioBackend(), clock=TestClock(0.0))
        self.addCleanup(tr.close)
        tr.seek(333.3333)
        self.assertEqual(tr.snapshot.active_event_ids, frozenset())
        tr.seek(333.33334)
        self.assertEqual(tr.snapshot.active_event_ids, frozenset({"T"}))
        tr.seek(666.66666)
        self.assertEqual(tr.snapshot.active_event_ids, frozenset({"T"}))
        tr.seek(666.66667)
        self.assertEqual(tr.snapshot.active_event_ids, frozenset())


# -----------------------------------------------------------------------------
# Transactions: error shutdown, secondary failures, recovery
# -----------------------------------------------------------------------------


class TestTransactionsAndRecovery(unittest.TestCase):

    def test_failed_pause_shuts_audio_down_and_preserves_coordinate(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(300)
        h.winmm.fail["pause"] = 263
        with self.assertRaises(AudioBackendError):
            h.transport.pause()
        self.assertEqual(h.transport.state, TransportState.ERROR)
        self.assertEqual(h.device.mode, "stopped")
        self.assertAlmostEqual(h.transport.snapshot.position_ms, 300.0, delta=1.0)
        self.assertEqual(h.scheduler.pending_count, 0)
        del h.winmm.fail["pause"]
        h.transport.play()
        self.assertEqual(h.transport.state, TransportState.PLAYING)

    def test_secondary_shutdown_failure_is_reported_not_swallowed(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(100)
        h.winmm.fail["pause"] = 263
        h.winmm.fail["stop"] = 263
        with self.assertRaises(AudioBackendError) as ctx:
            h.transport.pause()
        err = ctx.exception
        self.assertIn("pause", str(err))                              # original failure kept
        self.assertIsInstance(getattr(err, "secondary_shutdown_error", None), Exception)
        self.assertTrue(any("shutdown" in n for n in getattr(err, "__notes__", [])))
        self.assertEqual(len(h.errors), 1)
        self.assertEqual(h.transport.state, TransportState.ERROR)
        h.winmm.fail.clear()

    def test_failed_seek_while_playing_never_publishes_destination(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100 * 2))
        h.transport.play()
        h.scheduler.advance(200)
        h.winmm.fail["seek"] = 263
        with self.assertRaises(AudioBackendError):
            h.transport.seek(1500.0)
        self.assertNotIn(1500.0, [s.position_ms for s in h.snaps])
        self.assertEqual(h.transport.state, TransportState.ERROR)
        self.assertEqual(h.device.mode, "stopped")
        h.winmm.fail.clear()
        h.transport.seek(1500.0)                                       # recovery
        self.assertEqual(h.transport.state, TransportState.PAUSED)
        self.assertEqual(h.transport.snapshot.position_ms, 1500.0)

    def test_closed_transport_refuses_operations(self) -> None:
        tr = PlaybackTransport(timeline=two_event_timeline([("E", 0, 100)]),
                               audio_backend=SimulatedAudioBackend(), clock=TestClock(0.0))
        tr.close()
        tr.close()                                                     # idempotent
        for op in (tr.play, tr.pause, tr.stop, tr.reset, tr.step_tick):
            with self.assertRaises(TransportClosedError):
                op()
        with self.assertRaises(TransportClosedError):
            tr.seek(1.0)


# -----------------------------------------------------------------------------
# D8 - resource ownership and cleanup (test-owned temp directory only)
# -----------------------------------------------------------------------------


class TestD8ResourceCleanup(unittest.TestCase):

    def test_load_replace_and_close_release_device_and_temp_files(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100))
        files1 = os.listdir(h.tmpdir)
        self.assertEqual(len(files1), 1)
        alias = h.backend._alias
        self.assertIn(alias, h.winmm.devices)
        first = h.backend.temp_wav_path
        h.transport.play(); h.scheduler.advance(100)
        h.transport.load_timeline(wav_bytes=silent_wav(22070))        # source replacement
        self.assertFalse(os.path.exists(first))
        self.assertEqual(len(os.listdir(h.tmpdir)), 1)
        self.assertEqual(len(h.winmm.devices), 1)
        self.assertEqual(h.scheduler.pending_count, 0)
        h.transport.close()
        self.assertEqual(os.listdir(h.tmpdir), [])
        self.assertEqual(h.winmm.devices, {})
        h.transport.close()                                            # harmless twice
        self.assertEqual(h.winmm.commands("close"), [f"close {alias}", f"close {alias}"])

    def test_close_while_playing_stops_then_closes(self) -> None:
        h = FakeMciHarness(self, silent_wav(44100))
        h.transport.play(); h.scheduler.advance(100)
        h.transport.close()
        verbs = [c.split()[0] for c in h.winmm.commands()][-3:]
        self.assertEqual(verbs, ["stop", "stop", "close"])
        self.assertEqual(h.scheduler.pending_count, 0)
        self.assertEqual(os.listdir(h.tmpdir), [])

    def test_failed_open_cleans_up_partial_initialization(self) -> None:
        clock = TestClock(0.0)
        winmm = FakeWinmm(clock)
        tmp = tempfile.mkdtemp(prefix="job03_test_")
        self.addCleanup(shutil.rmtree, tmp, True)
        winmm.fail["status length"] = 263                              # open succeeds, then fails
        be = WindowsMciAudioBackend(winmm=winmm, temp_dir=tmp)
        tr = PlaybackTransport(audio_backend=be, clock=clock, scheduler=ManualScheduler(clock))
        errors = []
        tr.add_error_callback(errors.append)
        with self.assertRaises(AudioBackendError):
            tr.load_timeline(wav_bytes=silent_wav(4410))
        self.assertEqual(os.listdir(tmp), [])                          # temp file removed
        self.assertEqual(winmm.devices, {})                            # alias closed
        self.assertEqual(tr.state, TransportState.ERROR)
        self.assertEqual(len(errors), 1)
        winmm.fail.clear()
        tr.load_timeline(wav_bytes=silent_wav(4410))                   # recovers
        self.assertEqual(tr.state, TransportState.STOPPED)
        tr.close()
        self.assertEqual(os.listdir(tmp), [])

    def test_failed_close_is_reported_and_retryable(self) -> None:
        h = FakeMciHarness(self, silent_wav(4410))
        h.winmm.fail["close"] = 263
        with self.assertRaises(AudioBackendError):
            h.backend.unload()
        self.assertTrue(h.backend._is_open)                            # still held -> retry possible
        self.assertEqual(len(os.listdir(h.tmpdir)), 1)
        h.winmm.fail.clear()
        h.backend.unload()
        self.assertEqual(os.listdir(h.tmpdir), [])


# -----------------------------------------------------------------------------
# D7 - GUI renders every snapshot, rejects stale ones, and agrees with the transport
# -----------------------------------------------------------------------------


class TestD7GuiSnapshotRendering(unittest.TestCase):

    def setUp(self) -> None:
        from music_gui.main_window import MusicGUI
        from music_model.datasets import create_stage_1_proof_timeline
        self.app = MusicGUI(create_stage_1_proof_timeline())
        self.app.withdraw()
        self.addCleanup(self._destroy)
        # Replace the GUI's device transport with a deterministic one wired the same way.
        self.app.transport.close()
        self.clock = TestClock(0.0)
        self.sched = ManualScheduler(self.clock)
        self.tr = PlaybackTransport(timeline=self.app.timeline,
                                    audio_backend=SimulatedAudioBackend(clock=self.clock),
                                    clock=self.clock, scheduler=self.sched)
        self.tr.register_snapshot_callback(self.app._on_transport_snapshot)
        self.tr.register_error_callback(self.app._on_transport_error)
        self.app.transport = self.tr
        self.app._rendered_snapshot = None
        self.app._render_snapshot(self.tr.snapshot)

    def _destroy(self) -> None:
        try:
            self.app.destroy()
        except Exception:
            pass

    def assert_gui_matches(self, snap: TransportSnapshot) -> None:
        tv = self.app.timeline_view
        idle = snap.state == TransportState.STOPPED and snap.position_ms == 0.0
        self.assertAlmostEqual(self.app.seek_var.get(), snap.position_ms, places=6)
        self.assertTrue(self.app.lbl_time.cget("text").startswith(self.app._format_time(snap.position_ms)))
        if idle:
            self.assertIsNone(tv._playback_cursor_ms)
            self.assertEqual(tv.find_playback_cursor(), [])
            self.assertEqual(tv._currently_active_event_ids, set())
        else:
            self.assertEqual(tv._playback_cursor_ms, snap.position_ms)
            self.assertTrue(tv.find_playback_cursor())
            self.assertEqual(tv._currently_active_event_ids, set(snap.active_event_ids))
        self.assertIs(self.app._rendered_snapshot, snap)

    def test_seek_while_stopped_and_paused(self) -> None:
        self.tr.seek(2000.0)
        self.assertEqual(self.tr.state, TransportState.STOPPED)
        self.assert_gui_matches(self.tr.snapshot)
        self.assertTrue(self.tr.snapshot.active_event_ids)
        self.tr.play(); self.sched.advance(100); self.tr.pause()
        self.assert_gui_matches(self.tr.snapshot)
        self.tr.seek(4500.0)
        self.assertEqual(self.tr.state, TransportState.PAUSED)
        self.assert_gui_matches(self.tr.snapshot)

    def test_natural_completion_and_stop(self) -> None:
        self.tr.play()
        self.sched.advance(self.tr.total_duration_ms + 50)
        snap = self.tr.snapshot
        self.assertEqual(snap.state, TransportState.STOPPED)
        self.assertEqual(snap.position_ms, self.tr.total_duration_ms)
        self.assertEqual(snap.active_event_ids, frozenset())
        self.assert_gui_matches(snap)
        self.tr.play(); self.sched.advance(700)
        self.app.on_transport_stop()
        self.assert_gui_matches(self.tr.snapshot)
        self.assertEqual(self.tr.snapshot.position_ms, 0.0)

    def test_failed_operation_keeps_preserved_coordinate_on_screen(self) -> None:
        self.tr.play(); self.sched.advance(1200)
        self.tr.audio_backend.inject_failure = True
        try:
            self.tr.seek(2900.0)
        except AudioBackendError:
            pass
        snap = self.tr.snapshot
        self.assertEqual(snap.state, TransportState.ERROR)
        self.assertAlmostEqual(snap.position_ms, 1200.0, delta=15.0)
        self.assert_gui_matches(snap)
        self.assertEqual(self.app.btn_play.cget("bg"), "#ef4444")
        self.tr.audio_backend.inject_failure = False
        self.app.on_transport_stop()
        self.assert_gui_matches(self.tr.snapshot)

    def test_stale_and_foreign_snapshots_are_rejected(self) -> None:
        self.tr.seek(1000.0)
        current = self.tr.snapshot
        old = TransportSnapshot(current.transport_id, current.source_id, current.epoch, current.sequence - 1,
                                TransportState.PLAYING, 2500.0, frozenset({"X"}), current.total_duration_ms,
                                False, "tick")
        self.app._on_transport_snapshot(old)
        self.assert_gui_matches(current)
        foreign = TransportSnapshot(current.transport_id + 999, current.source_id, 0, 10 ** 9,
                                    TransportState.PLAYING, 2500.0, frozenset(), 1.0, False, "tick")
        self.app._on_transport_snapshot(foreign)
        self.assert_gui_matches(current)
        stale_source = TransportSnapshot(current.transport_id, current.source_id - 1, 0, current.sequence + 5,
                                         TransportState.PLAYING, 2500.0, frozenset(), 1.0, False, "tick")
        self.app._on_transport_snapshot(stale_source)
        self.assert_gui_matches(current)

    def test_source_replacement_resets_view(self) -> None:
        self.tr.play(); self.sched.advance(400); self.tr.pause()
        self.tr.load_timeline(two_event_timeline([("N", 0, 900)]))
        snap = self.tr.snapshot
        self.assertEqual(snap.reason, "load")
        self.assert_gui_matches(snap)
        self.assertEqual(float(self.app.seek_slider.cget("to")), 900.0)

    def test_application_shutdown_closes_transport_and_cancels_updates(self) -> None:
        self.tr.play()
        self.assertEqual(self.sched.pending_count, 1)
        self.app.destroy()
        self.assertTrue(self.tr.is_closed)
        self.assertEqual(self.sched.pending_count, 0)
        self.sched.advance(100)                                        # nothing runs after teardown


class TestD8GuiTeardownReleasesItsOwnTempWav(unittest.TestCase):

    def test_destroy_removes_the_application_temp_wav(self) -> None:
        from music_gui.main_window import MusicGUI
        app = MusicGUI()
        app.withdraw()
        backend = app.transport.audio_backend
        path = getattr(backend, "temp_wav_path", None)
        if not isinstance(backend, WindowsMciAudioBackend) or path is None:
            app.destroy()
            self.skipTest("No Windows MCI device in this environment")
        self.assertTrue(os.path.exists(path))
        app.destroy()
        self.assertFalse(os.path.exists(path), "the window's own temp WAV must be removed on exit")


if __name__ == "__main__":
    unittest.main()
