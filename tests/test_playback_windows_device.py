"""Opt-in JOB-03 integration tests against the REAL Windows MCI waveaudio device.

Enable with:   set MUSIC_REAL_AUDIO_TESTS=1   (PowerShell: $env:MUSIC_REAL_AUDIO_TESTS="1")
Then run:      python -m unittest tests.test_playback_windows_device -v

Every test plays SILENT PCM WAV data (all-zero samples) and keeps its temporary WAV files
in a test-owned directory, so nothing audible is produced and no unrelated temp file is
touched.  The tests drive the production configuration: PlaybackTransport +
WindowsMciAudioBackend + RealClock + TkScheduler on a Tk main loop.

What these tests can and cannot establish:
- They establish device-coordinate behaviour reported by MCI (mode, position, length),
  thread ownership, completion, pause/resume/seek command acceptance and cleanup.
- They do NOT measure acoustic output.  "Position" here is the MCI device coordinate and
  the transport's published coordinate; agreement between them is software/device
  agreement, not physical audio/visual synchronization, which only the Author can judge.

Measurements are printed with a "[measure]" prefix for the verification log.
"""

from __future__ import annotations

import ctypes
import io
import os
import shutil
import tempfile
import threading
import time
import tkinter as tk
import unittest
import wave
from typing import Callable, List, Optional

from music_gui.audio_playback import (
    AudioBackendError,
    PlaybackTransport,
    RealClock,
    TkScheduler,
    TransportSnapshot,
    TransportState,
    WindowsMciAudioBackend,
    get_wav_duration_ms,
)
from music_model.sound_event import SoundEvent
from music_model.timeline import MusicTimeline

ENABLED = os.environ.get("MUSIC_REAL_AUDIO_TESTS") == "1"
REASON = "real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)"


def silent_wav(frames: int, rate: int = 44100) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


def raw_status(alias: str, what: str) -> tuple:
    """Direct winmm query on the calling thread (bypasses the backend)."""
    buf = ctypes.create_unicode_buffer(128)
    rc = ctypes.windll.winmm.mciSendStringW(f"status {alias} {what}", buf, 128, None)
    return rc, buf.value


def measure(msg: str) -> None:
    print(f"[measure] {msg}", flush=True)


def pump(root: tk.Tk, max_ms: float, until: Optional[Callable[[], bool]] = None) -> float:
    """Run the Tk main loop until `until()` is true or max_ms elapses.  Returns elapsed ms."""
    t0 = time.perf_counter()
    deadline = t0 + max_ms / 1000.0

    def check() -> None:
        if (until is not None and until()) or time.perf_counter() >= deadline:
            root.quit()
            return
        root.after(2, check)
    root.after(2, check)
    root.mainloop()
    return (time.perf_counter() - t0) * 1000.0


@unittest.skipUnless(ENABLED and os.name == "nt", REASON)
class TestRealMciDevice(unittest.TestCase):

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="job03_realdev_")
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def make(self, wav: bytes, timeline=None, loop: bool = False):
        backend = WindowsMciAudioBackend(temp_dir=self.tmpdir)
        self.assertTrue(backend.is_available())
        tr = PlaybackTransport(timeline=timeline, wav_bytes=wav, audio_backend=backend,
                               clock=RealClock(), scheduler=TkScheduler(self.root))
        tr.set_loop(loop)
        rec = {"snaps": [], "ends": [], "errors": [], "snap_wall": []}
        tr.add_snapshot_callback(lambda s: (rec["snaps"].append(s), rec["snap_wall"].append(time.perf_counter())))
        tr.add_end_callback(lambda: rec["ends"].append(time.perf_counter()))
        tr.add_error_callback(rec["errors"].append)
        self.addCleanup(lambda: tr.is_closed or tr.close())
        return tr, backend, rec

    # R1 -------------------------------------------------------------------------
    def test_r1_ordinary_playback_advances_without_mci_263(self) -> None:
        tr, be, rec = self.make(silent_wav(44100 * 2))
        tick_durations: List[float] = []
        original = tr.step_tick

        def timed_step(delta_ms=None):
            t0 = time.perf_counter()
            try:
                return original(delta_ms)
            finally:
                tick_durations.append((time.perf_counter() - t0) * 1000.0)
        tr.step_tick = timed_step  # type: ignore[assignment]
        # Independent Tk event-loop probe: distinguishes slow updates from late timer delivery.
        probe_late: List[float] = []

        def probe(expected: float) -> None:
            probe_late.append((time.perf_counter() - expected) * 1000.0)
            self.root.after(1, probe, time.perf_counter() + 0.001)
        t_play = time.perf_counter()
        tr.play()
        self.root.after(1, probe, time.perf_counter() + 0.001)
        pump(self.root, 400)
        ticks = [s for s in rec["snaps"] if s.reason == "tick"]
        dev = float(raw_status(be._alias, "position")[1])
        pub = tr.snapshot.position_ms
        wall = (time.perf_counter() - t_play) * 1000.0
        tick_walls = [w for s, w in zip(rec["snaps"], rec["snap_wall"]) if s.reason == "tick"]
        intervals = [(b - a) * 1000.0 for a, b in zip(tick_walls, tick_walls[1:])] or [0.0]
        durs = tick_durations or [0.0]
        # Measurements are printed BEFORE the assertions so that a failing run stays diagnosable.
        measure(f"R1 ticks={len(ticks)} last_published={pub:.1f}ms device_now={dev:.0f}ms wall_since_play={wall:.1f}ms "
                f"device-published={dev - pub:.1f}ms")
        measure(f"R1 update interval ms: mean={sum(intervals)/len(intervals):.2f} max={max(intervals):.2f}; "
                f"step_tick duration ms: mean={sum(durs)/len(durs):.3f} max={max(durs):.3f}; "
                f"independent Tk 1 ms probe lateness max={max(probe_late or [0.0]):.1f}ms")
        self.assertEqual(rec["errors"], [], rec["errors"])
        self.assertEqual(tr.state, TransportState.PLAYING)
        self.assertGreater(ticks[-1].position_ms, tr.tick_interval_ms * 2)
        self.assertEqual(raw_status(be._alias, "mode"), (0, "playing"))
        self.assertLess(max(durs), 20.0, "a transport update must not block the GUI thread")
        self.assertGreater(len(ticks), 10, "fewer than 10 updates in 400 ms; see the probe lateness above")
        tr.stop()
        self.assertEqual(raw_status(be._alias, "mode"), (0, "stopped"))

    # R2/R3 ----------------------------------------------------------------------
    def _complete(self, frames: int, rate: int = 44100) -> None:
        wav = silent_wav(frames, rate)
        exact = get_wav_duration_ms(wav)
        tr, be, rec = self.make(wav)
        t_play = time.perf_counter()
        tr.play()
        pump(self.root, exact + 1500, until=lambda: tr.state != TransportState.PLAYING)
        rounding = "exact" if round(exact, 6) == exact else ("up" if round(exact, 6) > exact else "down")
        lateness = (rec["ends"][0] - t_play) * 1000.0 - exact if rec["ends"] else float("nan")
        measure(f"frames={frames}@{rate}: exact={exact!r}ms (round-6 {rounding}) device_length={be.device_length_ms}ms "
                f"state={tr.state.name} final={tr.snapshot.position_ms!r} "
                f"completion wall time - exact duration = {lateness:.1f}ms")
        self.assertEqual(rec["errors"], [], rec["errors"])
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(tr.snapshot.position_ms, exact)
        self.assertEqual(tr.snapshot.reason, "end")
        self.assertEqual(len(rec["ends"]), 1)
        self.assertFalse(tr.has_pending_tick)

    def test_r2_fractional_22070_frame_wav_completes(self) -> None:
        self._complete(22070)               # round(T, 6) rounds UP

    def test_r2b_fractional_22071_frame_wav_rounding_down_completes(self) -> None:
        self._complete(22071)               # round(T, 6) rounds DOWN (ChatGPT audit case)

    def test_r2c_fractional_48khz_wav_rounding_down_completes(self) -> None:
        self._complete(4801, 48000)         # 100.0208333... ms, rounds DOWN

    def test_r6b_rounding_down_fractional_duration_looping(self) -> None:
        wav = silent_wav(22071)
        exact = get_wav_duration_ms(wav)
        tr, be, rec = self.make(wav, loop=True)
        tr.play()
        pump(self.root, 1800)
        loops = [s for s in rec["snaps"] if s.reason == "loop"]
        measure(f"R6b 22071 frames: loops={len(loops)} errors={len(rec['errors'])} state={tr.state.name}")
        self.assertEqual(rec["errors"], [], rec["errors"])
        self.assertEqual(tr.state, TransportState.PLAYING)
        self.assertTrue(all(0.0 <= s.position_ms < exact for s in rec["snaps"] if s.state == TransportState.PLAYING))
        self.assertGreaterEqual(len(loops), 2)
        tr.stop()

    def test_r3_exact_1000ms_control_completes(self) -> None:
        self._complete(44100)

    # R4 -------------------------------------------------------------------------
    def test_r4_pause_halts_device_and_resume_continues(self) -> None:
        tr, be, rec = self.make(silent_wav(44100 * 3))
        tr.play()
        pump(self.root, 300)
        tr.pause()
        self.assertEqual(raw_status(be._alias, "mode"), (0, "paused"))
        p1 = raw_status(be._alias, "position")[1]
        pump(self.root, 300)
        p2 = raw_status(be._alias, "position")[1]
        self.assertEqual(p1, p2, "device position must not advance while paused")
        paused_at = tr.snapshot.position_ms
        measure(f"R4 paused transport={paused_at:.1f}ms device-after-pause={p1}ms "
                f"(device coordinate step across 'pause' = {float(p1) - paused_at:.1f}ms; stable over 300 ms: {p1 == p2})")
        n_before = len(rec["snaps"])
        tr.play()
        self.assertEqual(raw_status(be._alias, "mode"), (0, "playing"))
        pump(self.root, 200)
        self.assertGreater(tr.snapshot.position_ms, paused_at + 100)
        self.assertEqual(rec["errors"], [])
        after = [s.position_ms for s in rec["snaps"][n_before:] if s.state == TransportState.PLAYING]
        self.assertEqual(after, sorted(after), "published position must not move backwards after resume")
        first_moves = [p for p in after if p != after[0]]
        measure(f"R4 after resume: first published={after[0]:.1f}ms, first changed value="
                f"{first_moves[0] if first_moves else None}ms (forward step at resume = "
                f"{(first_moves[0] - after[0]) if first_moves else 0:.1f}ms)")

    # R5 -------------------------------------------------------------------------
    def test_r5_seek_while_paused_then_play(self) -> None:
        tr, be, rec = self.make(silent_wav(44100 * 3))
        tr.play()
        pump(self.root, 200)
        tr.pause()
        tr.seek(2000.4)
        self.assertEqual(raw_status(be._alias, "mode"), (0, "stopped"))
        self.assertEqual(tr.snapshot.position_ms, 2000.4)
        tr.play()
        pump(self.root, 200)
        self.assertEqual(rec["errors"], [])
        self.assertGreater(tr.snapshot.position_ms, 2100.0)
        measure(f"R5 after seek(2000.4)+play+200ms: transport={tr.snapshot.position_ms:.1f}ms "
                f"device={raw_status(be._alias, 'position')[1]}ms")

    # R6 -------------------------------------------------------------------------
    def test_r6_fractional_duration_looping(self) -> None:
        wav = silent_wav(22070)
        exact = get_wav_duration_ms(wav)
        tr, be, rec = self.make(wav, loop=True)
        tr.play()
        pump(self.root, 1800)
        loop_idx = [i for i, s in enumerate(rec["snaps"]) if s.reason == "loop"]
        # Wall time from each cycle's start (play or loop) to the next restart, minus the exact duration.
        starts = [i for i, s in enumerate(rec["snaps"]) if s.reason in ("play", "loop")]
        cycle_excess = [(rec["snap_wall"][b] - rec["snap_wall"][a]) * 1000.0 - exact
                        for a, b in zip(starts, starts[1:])]
        ticks = [s for s in rec["snaps"] if s.reason == "tick"]
        measure(f"R6 loops={len(loop_idx)} ticks={len(ticks)}; per-cycle wall time beyond exact duration (upper bound "
                f"on the restart gap, includes up to one update interval): {[round(x, 1) for x in cycle_excess]} ms")
        self.assertEqual(rec["errors"], [], rec["errors"])
        self.assertEqual(tr.state, TransportState.PLAYING)
        playing = [s.position_ms for s in rec["snaps"] if s.state == TransportState.PLAYING]
        self.assertTrue(all(0.0 <= p < exact for p in playing))
        self.assertGreaterEqual(len(loop_idx), 3)
        tr.stop()

    # R7 -------------------------------------------------------------------------
    def test_r7_cross_thread_command_is_refused_device_unaffected(self) -> None:
        tr, be, rec = self.make(silent_wav(44100 * 2))
        tr.play()
        pump(self.root, 100)
        out = {}
        status_before = be.get_status()

        def worker() -> None:
            try:
                be.get_device_position_ms()
            except AudioBackendError as ex:
                out["err"] = str(ex)
        t = threading.Thread(target=worker)
        t.start(); t.join()
        self.assertIn("thread-affine", out.get("err", ""))
        self.assertEqual(be.get_status(), status_before, "a refused call must not change backend status")
        pump(self.root, 100)
        self.assertEqual(tr.state, TransportState.PLAYING)
        self.assertEqual(rec["errors"], [])

    # R8 -------------------------------------------------------------------------
    def test_r8_close_releases_device_and_temp_file(self) -> None:
        tr, be, rec = self.make(silent_wav(44100))
        alias, path = be._alias, be.temp_wav_path
        self.assertTrue(os.path.exists(path))
        tr.play()
        pump(self.root, 100)
        tr.close()
        self.assertEqual(raw_status(alias, "mode")[0], 263, "alias must be closed")
        self.assertFalse(os.path.exists(path))
        self.assertEqual(os.listdir(self.tmpdir), [])
        tr.close()

    # R9 -------------------------------------------------------------------------
    def test_r9_source_replacement_releases_previous_device(self) -> None:
        tr, be, rec = self.make(silent_wav(44100))
        alias, path1 = be._alias, be.temp_wav_path
        tr.play()
        pump(self.root, 100)
        tr.load_timeline(wav_bytes=silent_wav(22070))
        self.assertFalse(os.path.exists(path1))
        self.assertEqual(len(os.listdir(self.tmpdir)), 1)
        self.assertEqual(raw_status(alias, "length"), (0, "500"))   # same alias, new media
        tr.play()
        pump(self.root, 1500, until=lambda: tr.state != TransportState.PLAYING)
        self.assertEqual(tr.state, TransportState.STOPPED)
        self.assertEqual(rec["errors"], [])


@unittest.skipUnless(ENABLED and os.name == "nt", REASON)
class TestRealMciThroughMusicGUI(unittest.TestCase):

    def test_gui_end_to_end_playback_completion_and_teardown(self) -> None:
        from music_gui.main_window import MusicGUI
        app = MusicGUI()
        app.withdraw()
        try:
            tl = MusicTimeline()
            row = tl.create_row("R")
            row.add_event(SoundEvent("A", "R", 0, 250))
            row.add_event(SoundEvent("B", "R", 250, 500))
            app.timeline = tl
            app._sync_transport_with_current_timeline(wav_bytes=silent_wav(22070))
            tr = app.transport
            exact = tr.total_duration_ms
            self.assertAlmostEqual(exact, 500.4535147392, places=6)
            rendered: List[TransportSnapshot] = []
            tr.add_snapshot_callback(lambda s: rendered.append(app._rendered_snapshot))
            # GUI responsiveness probe: lateness of 1 ms Tk timers while playing
            lateness: List[float] = []

            def probe(t_expected: float) -> None:
                now = time.perf_counter()
                lateness.append((now - t_expected) * 1000.0)
                if tr.state == TransportState.PLAYING:
                    app.after(1, probe, time.perf_counter() + 0.001)
            app.on_transport_play()
            app.after(1, probe, time.perf_counter() + 0.001)
            pump(app, 1500, until=lambda: tr.state != TransportState.PLAYING)
            self.assertEqual(tr.state, TransportState.STOPPED)
            snap = tr.snapshot
            self.assertEqual(snap.position_ms, exact)
            self.assertIs(app._rendered_snapshot, snap)
            self.assertAlmostEqual(app.seek_var.get(), exact, places=6)
            self.assertEqual(app.timeline_view._playback_cursor_ms, exact)
            self.assertEqual(app.timeline_view._currently_active_event_ids, set())
            self.assertTrue(all(r is not None for r in rendered))
            ticks = [s for s in rendered if s.reason == "tick"]
            self.assertGreater(len(ticks), 10)
            # the GUI rendered the B event while the playhead was in [250, 500)
            self.assertTrue(any(s.active_event_ids == frozenset({"B"}) for s in ticks))
            lateness.sort()
            measure(f"R10 GUI: snapshots rendered={len(rendered)}, Tk 1 ms timer lateness during playback: "
                    f"median={lateness[len(lateness)//2]:.2f}ms p95={lateness[int(len(lateness)*0.95)]:.2f}ms "
                    f"max={lateness[-1]:.2f}ms (n={len(lateness)})")
            path = tr.audio_backend.temp_wav_path
            self.assertTrue(path and os.path.exists(path))
        finally:
            app.destroy()
        self.assertTrue(tr.is_closed)
        self.assertFalse(os.path.exists(path))


@unittest.skipUnless(ENABLED and os.name == "nt", REASON)
class TestRealMciNonSilentWavImport(unittest.TestCase):
    """Real MCI device: the corrected GUI WAV import path with a NON-SILENT fixture.

    The non-silent audio is LOADED into the real device but never played (no sound is produced);
    playback/completion of imported PCM is covered deterministically in test_wav_import_regression.
    """

    def test_gui_imports_non_silent_wav_into_real_device_and_releases_it(self) -> None:
        from unittest import mock
        import music_gui.main_window as mw
        from tests.test_wav_import_regression import gapped_wav, NOTES
        tmp = tempfile.mkdtemp(prefix="job03_realdev_wav_")
        self.addCleanup(shutil.rmtree, tmp, True)
        wav1, wav2 = gapped_wav(), gapped_wav(0.25, 0.1, notes=NOTES[:2])
        p1, p2 = os.path.join(tmp, "four.wav"), os.path.join(tmp, "two.wav")
        for p, d in ((p1, wav1), (p2, wav2)):
            with open(p, "wb") as f:
                f.write(d)
        errors = []
        app = mw.MusicGUI()
        app.withdraw()
        try:
            with mock.patch.object(mw.messagebox, "showerror", lambda t, m: errors.append(m)):
                for path in (p1, p2):
                    t0 = time.perf_counter()
                    with mock.patch.object(mw.filedialog, "askopenfilename", lambda **kw: path):
                        app._on_open_wav_file()
                    self.assertLess(time.perf_counter() - t0, 0.5)
                    pump(app, 300000, until=lambda: app._wav_import_job is None)
                    self.assertEqual(errors, [])
                    tr, be = app.transport, app.transport.audio_backend
                    self.assertIsInstance(be, WindowsMciAudioBackend)
                    self.assertFalse(tr.is_synthesized_audio)
                    expected = get_wav_duration_ms(wav1 if path == p1 else wav2)
                    self.assertEqual(tr.total_duration_ms, expected)
                    self.assertEqual(be.device_length_ms, int(expected))           # real device opened it
                    self.assertEqual(raw_status(be._alias, "mode"), (0, "stopped"))  # loaded, not playing
                    with open(be.temp_wav_path, "rb") as f:
                        self.assertEqual(f.read(), wav1 if path == p1 else wav2)
                    if path == p1:
                        first_temp = be.temp_wav_path
                        pitches = sorted(e.attributes["pitch_midi"] for r in app.timeline.rows for e in r.events)
                        self.assertEqual(pitches, [60, 62, 64, 67])
                self.assertFalse(os.path.exists(first_temp), "previous source's temp WAV must be removed")
                last_temp = app.transport.audio_backend.temp_wav_path
                measure(f"R11 real-device non-silent WAV import: 2 imports OK, device lengths "
                        f"{int(get_wav_duration_ms(wav1))}/{int(get_wav_duration_ms(wav2))} ms, previous temp released")
        finally:
            app.destroy()
        self.assertFalse(os.path.exists(last_temp))


if __name__ == "__main__":
    unittest.main()
