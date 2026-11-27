"""JOB-03 regression: complete NON-SILENT WAV import path through the GUI (Author manual-check failure).

Background (2026-11-26 Author verification):
- "Open Audio WAV" could never succeed: the importer labels events with its default
  row_id 'row_audio' while the GUI added them to a row created as 'Row 2', and
  TemporaryRow.add_event rejects the mismatch ("Cannot add event ... to TemporaryRow 'Row 2'").
- The JOB-02 analysis (~26 s for the Author's 4 s file) ran on the Tk thread, so Windows marked
  the window as hung; the Author's fatal access violation occurred during that analysis.

Fixtures are generated in code (no binary file in the repository).  `author_equivalent_wav()`
reproduces the Author's controlled file JOB03_test.wav to within 1 LSB per sample (176,097 of
176,400 samples identical; SHA-256 of the original recorded in the evidence workspace):
PCM mono 16-bit 44.1 kHz, 176,400 frames, C4 D4 E4 G4 for 1 s each, amplitude 7000, 10 ms linear
fades, rounded.  `gapped_wav()` uses the same notes separated by silence, which the JOB-02
energy detector requires in order to split notes (documented hangover >= 20 ms below 5 % of peak).
"""

from __future__ import annotations

import io
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
from typing import Optional
from unittest import mock

from music_gui.audio_playback import (
    ManualScheduler,
    TestClock,
    TransportState,
    WindowsMciAudioBackend,
    get_wav_duration_ms,
)

NOTES = [("C4", 261.6255653005986, 60), ("D4", 293.6647679174076, 62),
         ("E4", 329.6275569128699, 64), ("G4", 391.99543598174927, 67)]
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _notes_wav(note_s: float, gap_s: float, rate: int = 44100, amp: float = 7000.0, fade_s: float = 0.01,
               notes=NOTES) -> bytes:
    frames = []
    n = int(round(note_s * rate)); m = int(round(fade_s * rate))
    for _, freq, _ in notes:
        for i in range(n):
            a = amp * min(1.0, i / m, (n - 1 - i) / m)
            frames.append(int(round(a * math.sin(2 * math.pi * freq * i / rate))))
        frames.extend([0] * int(round(gap_s * rate)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return buf.getvalue()


def author_equivalent_wav() -> bytes:
    """Contiguous (legato) C4 D4 E4 G4, 1 s each: equivalent of the Author's JOB03_test.wav."""
    return _notes_wav(1.0, 0.0)


def gapped_wav(note_s: float = 0.3, gap_s: float = 0.1, notes=NOTES) -> bytes:
    return _notes_wav(note_s, gap_s, notes=notes)


CHILD = r"""
import faulthandler, json, sys
faulthandler.enable()
sys.path.insert(0, sys.argv[1])
from music_model.audio_importer import import_audio_to_sound_events
evs = import_audio_to_sound_events(open(sys.argv[2], "rb").read(), row_id="Row 2")
print(json.dumps([[e.event_id, e.row_id, e.start_time_ms, e.end_time_ms, e.attributes.get("pitch_midi"),
                   e.attributes.get("frequency_hz")] for e in evs]))
"""


class TestNonSilentImportInChildProcess(unittest.TestCase):
    """The import runs in a child process so that a native crash fails this test (non-zero exit)
    instead of terminating the whole test run."""

    def test_author_equivalent_file_imports_without_crashing(self) -> None:
        wav = author_equivalent_wav()
        self.assertEqual(len(wav) - 44, 176400 * 2)
        tmp = tempfile.mkdtemp(prefix="job03_wavimp_"); self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "author_equivalent.wav")
        with open(path, "wb") as f:
            f.write(wav)
        r = subprocess.run([sys.executable, "-X", "faulthandler", "-c", CHILD, PROJECT_ROOT, path],
                           capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, f"child failed (native crash?):\n{r.stderr[-3000:]}")
        events = json.loads(r.stdout.strip().splitlines()[-1])
        # Legato notes with no silence between them are ONE energy event under the JOB-02 detector
        # (documented hangover rule); its single autocorrelation pitch is E4.  This pins the
        # current, documented behaviour; it is not a claim of note segmentation.
        self.assertEqual(len(events), 1)
        eid, row_id, start, end, midi, hz = events[0]
        self.assertEqual(row_id, "Row 2")
        self.assertAlmostEqual(start, 0, delta=20)
        self.assertAlmostEqual(end, 4000, delta=20)
        self.assertEqual(midi, 64)


class TestGuiWavImportPath(unittest.TestCase):
    """Production MusicGUI handler + production MCI backend on the FakeWinmm driver model."""

    def setUp(self) -> None:
        from tests.test_playback_consolidated import FakeWinmm
        import music_gui.main_window as mw
        self.mw = mw
        self.tmp = tempfile.mkdtemp(prefix="job03_wavgui_"); self.addCleanup(shutil.rmtree, self.tmp, True)
        self.clock = TestClock(0.0)
        self.sched = ManualScheduler(self.clock)
        self.winmm = FakeWinmm(self.clock)
        patches = [
            mock.patch.object(mw, "RealClock", lambda: self.clock),
            mock.patch.object(mw, "TkScheduler", lambda widget: self.sched),
            mock.patch.object(mw, "WindowsMciAudioBackend",
                              lambda: WindowsMciAudioBackend(winmm=self.winmm, temp_dir=self.tmp)),
            mock.patch.object(mw.messagebox, "showerror", lambda title, msg: self.errors.append(msg)),
            mock.patch.object(mw.messagebox, "showinfo", lambda title, msg: self.infos.append(msg)),
        ]
        self.errors, self.infos = [], []
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        self.app = mw.MusicGUI()
        self.app.withdraw()
        self.addCleanup(self._destroy)

    def _destroy(self) -> None:
        try:
            self.app.destroy()
        except Exception:
            pass

    def _write(self, name: str, data: bytes) -> str:
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _import(self, path: str):
        """Run the real handler; pump the Tk loop until the background analysis is applied.
        Returns the largest gap between consecutive Tk heartbeat callbacks during the analysis."""
        beats = []
        pending = []

        def heartbeat():
            beats.append(time.perf_counter())
            pending.clear()
            if self.app._wav_import_job is not None:
                pending.append(self.app.after(20, heartbeat))
        t0 = time.perf_counter()
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: path):
            self.app._on_open_wav_file()
        handler_s = time.perf_counter() - t0
        # The Tk callback must return immediately; the analysis (seconds) must not run inside it.
        self.assertLess(handler_s, 0.5, f"handler blocked the Tk thread for {handler_s:.2f} s")
        self.assertIsNotNone(self.app._wav_import_job, "analysis must run in the background")
        pending.append(self.app.after(20, heartbeat))
        deadline = time.perf_counter() + 600
        while self.app._wav_import_job is not None and time.perf_counter() < deadline:
            self.app.update()
            time.sleep(0.002)
        self.assertIsNone(self.app._wav_import_job, "analysis did not finish")
        for after_id in pending:
            self.app.after_cancel(after_id)
        gap = max((b - a for a, b in zip(beats, beats[1:])), default=0.0)
        print(f"[measure] {os.path.basename(path)}: Tk heartbeats during analysis={len(beats)}, largest gap={gap * 1000:.0f} ms", flush=True)
        return max((b - a for a, b in zip(beats, beats[1:])), default=0.0)

    def test_import_play_complete_and_replace_source(self) -> None:
        wav1 = gapped_wav()
        exact1 = get_wav_duration_ms(wav1)
        self.assertAlmostEqual(exact1, 1600.0, places=6)
        max_gap = self._import(self._write("four_notes.wav", wav1))
        self.assertEqual(self.errors, [])
        # GUI stayed operational: Tk callbacks kept running during the analysis.
        self.assertLess(max_gap, 0.5, f"Tk loop blocked for {max_gap:.3f} s during analysis")

        # Four detected events with the expected pitches (JOB-02 tolerances: exact MIDI,
        # frequency within 1 %, boundaries within the 20 ms analysis window).
        events = sorted((e for r in self.app.timeline.rows for e in r.events), key=lambda e: e.start_time_ms)
        self.assertEqual(len(events), 4)
        for e, (name, freq, midi), k in zip(events, NOTES, range(4)):
            self.assertEqual(e.row_id, "Row 2")
            self.assertEqual(e.attributes["pitch_midi"], midi, name)
            self.assertAlmostEqual(e.attributes["frequency_hz"], freq, delta=freq * 0.01)
            self.assertAlmostEqual(e.start_time_ms, 400 * k, delta=20)
            self.assertAlmostEqual(e.end_time_ms, 400 * k + 300, delta=20)
            self.assertEqual(e.attributes["source_type"], "audio_wav")

        # Original PCM retained for playback (not re-synthesized), exact duration.
        tr = self.app.transport
        self.assertFalse(tr.is_synthesized_audio)
        self.assertEqual(tr._wav_bytes, wav1)
        self.assertEqual(tr.total_duration_ms, exact1)
        first_temp = tr.audio_backend.temp_wav_path
        with open(first_temp, "rb") as f:
            self.assertEqual(f.read(), wav1)                       # the device plays these exact bytes
        self.assertEqual(len(self.winmm.devices), 1)

        # Playhead advances and the GUI renders it with the active note highlighted.
        self.app.on_transport_play()
        self.sched.advance(150)
        snap = tr.snapshot
        self.assertEqual(snap.state, TransportState.PLAYING)
        self.assertGreater(snap.position_ms, 100)
        self.assertEqual(self.app.timeline_view._playback_cursor_ms, snap.position_ms)
        self.assertEqual(snap.active_event_ids, frozenset({events[0].event_id}))
        self.assertEqual(self.app.timeline_view._currently_active_event_ids, {events[0].event_id})

        # Natural completion at the exact source duration.
        self.sched.advance(exact1 + 100)
        snap = tr.snapshot
        self.assertEqual(snap.state, TransportState.STOPPED)
        self.assertEqual(snap.position_ms, exact1)
        self.assertEqual(snap.reason, "end")
        self.assertEqual(self.app.timeline_view._playback_cursor_ms, exact1)

        # Importing a different file releases the previous source's resources.
        wav2 = gapped_wav(0.25, 0.1, notes=NOTES[:2])
        self._import(self._write("two_notes.wav", wav2))
        self.assertEqual(self.errors, [])
        self.assertFalse(os.path.exists(first_temp), "previous temp WAV must be removed")
        self.assertEqual(len(self.winmm.devices), 1, "previous MCI alias must be closed")
        self.assertEqual(tr.total_duration_ms, get_wav_duration_ms(wav2))
        self.assertEqual(tr._wav_bytes, wav2)
        self.assertEqual(len([e for r in self.app.timeline.rows for e in r.events]), 2)

    def test_second_open_while_analysing_is_refused_not_queued(self) -> None:
        path = self._write("four_notes.wav", gapped_wav())
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: path):
            self.app._on_open_wav_file()
            job = self.app._wav_import_job
            self.app._on_open_wav_file()
        self.assertIs(self.app._wav_import_job, job)
        self.assertEqual(len(self.infos), 1)
        while self.app._wav_import_job is not None:
            self.app.update(); time.sleep(0.002)
        self.assertEqual(self.errors, [])

    def test_analysis_error_is_reported_on_tk_thread(self) -> None:
        path = self._write("not_a_wav.wav", b"RIFF\x00\x00\x00\x00JUNK")
        self._import(path)
        self.assertEqual(len(self.errors), 1)
        self.assertIn("Failed to import WAV audio file", self.errors[0])
        self.assertTrue(self.app.transport.is_synthesized_audio)     # previous source untouched

    def test_window_destroyed_during_analysis_ignores_result(self) -> None:
        path = self._write("four_notes.wav", gapped_wav())
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: path):
            self.app._on_open_wav_file()
        job = self.app._wav_import_job
        self.app.destroy()
        job.join(120)
        self.assertFalse(job.is_alive())
        self.assertTrue(self.app.transport.is_closed)
        self.assertEqual(self.winmm.devices, {})
        self.assertEqual(self.errors, [])


FOUR_NOTE_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test piano</part-name></score-part></part-list>
  <part id="P1"><measure number="1">
    <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
    <sound tempo="60"/>
    <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
  </measure></part>
</score-partwise>
"""


class TestStaleWavImportLifecycle(TestGuiWavImportPath):
    """Asynchronous WAV import vs. later source/mode selection (ChatGPT audit, stale import).

    Policy under test: any source or mode selection made after a WAV analysis starts withdraws that
    analysis's authority to publish.  The worker is never terminated; it finishes, and its success or
    failure is discarded (no timeline, transport, dialog or badge change).  At most one analysis
    computes at a time.  Worker completion is controlled by a gate, never by timing.
    """

    # The inherited TestGuiWavImportPath tests must not run a second time under this class.
    test_import_play_complete_and_replace_source = None
    test_second_open_while_analysing_is_refused_not_queued = None
    test_analysis_error_is_reported_on_tk_thread = None
    test_window_destroyed_during_analysis_ignores_result = None

    def setUp(self) -> None:
        super().setUp()
        self.wav = gapped_wav(0.05, 0.1)
        self.wav_path = self._write("gated.wav", self.wav)
        from music_model.audio_importer import import_audio_to_sound_events as real_import
        self.real_events = real_import(self.wav, row_id="Row 2")
        self.calls = 0
        self.release = threading.Event()
        self.entered = threading.Event()
        self.fail_with: Optional[BaseException] = None
        self.addCleanup(self.release.set)               # never leave a worker blocked

        def gated(wav_bytes, row_id="row_audio", **kw):
            self.calls += 1
            self.entered.set()
            assert self.release.wait(30), "gate never released"
            if self.fail_with is not None:
                raise self.fail_with
            self.assertEqual(wav_bytes, self.wav)       # original PCM handed to the analysis unchanged
            return list(self.real_events)
        p = mock.patch.object(self.mw, "import_audio_to_sound_events", gated)
        p.start(); self.addCleanup(p.stop)

    # --- helpers -------------------------------------------------------------------------------

    def _start_gated_import(self):
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: self.wav_path):
            self.app._on_open_wav_file()
        job = self.app._wav_import_job
        self.assertIsNotNone(job)
        self.assertTrue(self.entered.wait(5), "worker did not start")
        self.assertEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Analysing WAV...]")
        return job

    def _finish_worker(self, job) -> None:
        """Let the worker complete, then run the Tk loop long enough for any poll to fire."""
        self.release.set()
        job.join(10)
        self.assertFalse(job.is_alive())
        end = time.perf_counter() + 0.4                  # > 6 poll intervals of WAV_IMPORT_POLL_MS
        while time.perf_counter() < end:
            self.app.update()
            time.sleep(0.005)

    def _state(self):
        tr = self.app.transport
        return (self.app.current_view_mode, self.app.current_dataset_name, self.app.timeline,
                tr.is_synthesized_audio, tr._wav_bytes, tr.total_duration_ms,
                self.app.lbl_audio_mode.cget("text"))

    def _assert_superseded_now(self, job) -> None:
        self.assertIsNone(self.app._wav_import_job, "pending import must lose its authority at once")
        self.assertNotEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Analysing WAV...]")
        self.assertTrue(job.is_alive(), "the worker is disowned, not terminated")

    def _analysis_threads(self):
        return [t for t in threading.enumerate() if t.name == "WavImportAnalysis" and t.is_alive()]

    # --- 1. WAV import followed by Progressive Refitting selection ----------------------------

    def test_progressive_selection_discards_obsolete_success(self) -> None:
        self.app.show_midi_mode()
        job = self._start_gated_import()
        self.app.show_progressive_mode("A")
        self._assert_superseded_now(job)
        after_switch = self._state()
        self.assertEqual(after_switch[0], "progressive")
        self.assertTrue(after_switch[3])
        self._finish_worker(job)
        self.assertEqual(job.error, None)
        self.assertEqual(len(job.events), 4)              # it did compute a successful result ...
        self.assertEqual(self._state(), after_switch)     # ... which changed nothing
        self.assertEqual(self.errors, []); self.assertEqual(self.infos, [])

    def test_mode_without_transport_reload_also_supersedes(self) -> None:
        # Dual mode does not reload the transport; the mode selection alone must supersede.
        self.app.show_midi_mode()
        job = self._start_gated_import()
        self.app.show_dual_mode()
        self._assert_superseded_now(job)
        after_switch = self._state()
        self._finish_worker(job)
        self.assertEqual(self._state(), after_switch)
        self.assertEqual(self.app.current_view_mode, "dual")
        self.assertEqual(self.errors, [])

    # --- 2. WAV import followed by a different successfully loaded source ----------------------

    def test_musicxml_source_loaded_during_analysis_is_kept(self) -> None:
        self.app.show_midi_mode()
        job = self._start_gated_import()
        xml_path = os.path.join(self.tmp, "four.musicxml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(FOUR_NOTE_MUSICXML)
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: xml_path):
            self.app._on_open_musicxml_file()
        self.assertEqual(self.errors, [])
        self._assert_superseded_now(job)
        after_xml = self._state()
        self.assertIn("four.musicxml", after_xml[1])
        self.assertTrue(after_xml[3])                     # synthesized MusicXML audio
        self._finish_worker(job)
        self.assertEqual(self._state(), after_xml)
        self.assertEqual(self.errors, [])

    def test_cancelled_dialog_is_not_a_source_selection(self) -> None:
        # Opening and cancelling another file dialog selects nothing, so the import still publishes.
        self.app.show_midi_mode()
        job = self._start_gated_import()
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: ""):
            self.app._on_open_musicxml_file()
            self.app._on_open_midi_file()
        self.assertIs(self.app._wav_import_job, job)
        self._finish_worker(job)
        self.assertIsNone(self.app._wav_import_job)
        self.assertEqual(self.app.transport._wav_bytes, self.wav)
        self.assertEqual(self.app.current_dataset_name, "Imported WAV: gated.wav")

    def test_row1_toggle_is_not_a_source_selection(self) -> None:
        # Row 1 toggle is display-only (Row 1 source-preservation correction): the pending import keeps
        # its authority and publishes with the Row 1 mode in force when it completes.
        self.app.show_midi_mode()
        job = self._start_gated_import()
        gen = self.app._source_generation
        self.app._toggle_constant_row_mode()
        self.assertIs(self.app._wav_import_job, job)
        self.assertEqual(self.app._source_generation, gen)
        self.assertEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Analysing WAV...]")
        self._finish_worker(job)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.app.transport._wav_bytes, self.wav)
        self.assertFalse(self.app.transport.is_synthesized_audio)
        self.assertEqual(self.app.current_dataset_name, "Imported WAV: gated.wav")
        self.assertEqual(self.app.timeline_view.constant_row_mode, "development")
        self.assertIn("Row 1 (Dev Profile)", self.app.lbl_constant_summary.cget("text"))

    # --- 3/4. Obsolete worker success and failure ----------------------------------------------

    def test_obsolete_failure_shows_no_dialog_and_keeps_badge(self) -> None:
        from music_model.audio_importer import AudioFormatError
        self.fail_with = AudioFormatError("simulated analysis failure")
        self.app.show_midi_mode()
        job = self._start_gated_import()
        self.app.show_progressive_mode("B")
        self._assert_superseded_now(job)
        after_switch = self._state()
        self._finish_worker(job)
        self.assertIsInstance(job.error, AudioFormatError)   # it did fail ...
        self.assertEqual(self.errors, [])                    # ... silently, because obsolete
        self.assertEqual(self._state(), after_switch)        # badge and source unchanged

    def test_current_failure_is_still_reported(self) -> None:
        from music_model.audio_importer import AudioFormatError
        self.fail_with = AudioFormatError("simulated analysis failure")
        self.app.show_midi_mode()
        before = self._state()
        job = self._start_gated_import()
        self._finish_worker(job)
        self.assertEqual(len(self.errors), 1)
        self.assertIn("simulated analysis failure", self.errors[0])
        self.assertEqual(self._state(), before)              # previous source and truthful badge restored

    # --- 5. Normal import without an intervening source change ----------------------------------

    def test_normal_import_publishes_exactly_once(self) -> None:
        self.app.show_midi_mode()
        job = self._start_gated_import()
        gen = self.app._source_generation
        self.assertEqual(job.generation, gen)
        self._finish_worker(job)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.calls, 1)
        tr = self.app.transport
        self.assertFalse(tr.is_synthesized_audio)
        self.assertEqual(tr._wav_bytes, self.wav)
        self.assertEqual(tr.total_duration_ms, get_wav_duration_ms(self.wav))
        events = sorted((e for r in self.app.timeline.rows for e in r.events), key=lambda e: e.start_time_ms)
        self.assertEqual([(e.start_time_ms, e.end_time_ms, e.attributes["pitch_midi"]) for e in events],
                         [(e.start_time_ms, e.end_time_ms, e.attributes["pitch_midi"]) for e in self.real_events])
        self.assertEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Authentic PCM WAV]")
        # A later poll cannot re-publish: the job no longer exists.
        self.assertIsNone(self.app._wav_import_job)

    # --- 6. Subsequent imports and application shutdown -----------------------------------------

    def test_new_import_refused_while_obsolete_worker_computes_then_allowed(self) -> None:
        self.app.show_midi_mode()
        old = self._start_gated_import()
        self.app.show_midi_mode()                            # re-selecting a source supersedes too
        self._assert_superseded_now(old)
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: self.wav_path):
            self.app._on_open_wav_file()
        self.assertIsNone(self.app._wav_import_job, "no second analysis may start")
        self.assertEqual(len(self.infos), 1)
        self.assertIn("still finishing", self.infos[0])
        self.assertEqual(len(self._analysis_threads()), 1)
        self.assertEqual(self.calls, 1)
        self._finish_worker(old)
        self.assertEqual(self.app.transport.is_synthesized_audio, True)   # obsolete result discarded
        # Now a new import starts, runs and publishes normally.
        self.entered.clear()
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: self.wav_path):
            self.app._on_open_wav_file()
        new = self.app._wav_import_job
        self.assertIsNotNone(new)
        self.assertIsNot(new, old)
        self.assertTrue(self.entered.wait(5))
        self._finish_worker(new)
        self.assertEqual(self.calls, 2)
        self.assertFalse(self.app.transport.is_synthesized_audio)
        self.assertEqual(self.app.transport._wav_bytes, self.wav)
        self.assertEqual(self.errors, [])
        self.assertEqual(self._analysis_threads(), [])

    def test_shutdown_with_obsolete_worker_running(self) -> None:
        self.app.show_midi_mode()
        job = self._start_gated_import()
        self.app.show_progressive_mode("A")
        self._assert_superseded_now(job)
        self.app.destroy()
        self.assertTrue(self.app.transport.is_closed)
        self.assertEqual(self.winmm.devices, {})
        self.release.set()
        job.join(10)
        self.assertFalse(job.is_alive())
        self.assertEqual(self.errors, [])
        self.assertEqual([n for n in os.listdir(self.tmp) if n.startswith("music_play_")], [], "temp WAV leaked")


class TestRow1SourcePreservation(TestGuiWavImportPath):
    """Row 1 is a mathematical representation of the source, not a source (ChatGPT audit).

    Negative baseline (pre-correction code, evidence probe_row1_source_matrix_BEFORE.txt): every Row 1
    toggle reloaded the transport.  The original PCM became synthesized audio, playback stopped and
    returned to 0, and the dataset identity changed to 'Imported: <file>'.  Imports loaded the transport
    twice.  Deterministic: FakeWinmm driver model, ManualScheduler, TestClock.
    """

    test_import_play_complete_and_replace_source = None
    test_second_open_while_analysing_is_refused_not_queued = None
    test_analysis_error_is_reported_on_tk_thread = None
    test_window_destroyed_during_analysis_ignores_result = None

    def setUp(self) -> None:
        super().setUp()
        from music_gui.audio_playback import PlaybackTransport
        self.loads = []
        real_load = PlaybackTransport.load_timeline

        def counting_load(tr, timeline=None, wav_bytes=None, synthesize=True):
            self.loads.append("pcm" if wav_bytes is not None else "synth")
            return real_load(tr, timeline, wav_bytes=wav_bytes, synthesize=synthesize)
        p = mock.patch.object(PlaybackTransport, "load_timeline", counting_load)
        p.start(); self.addCleanup(p.stop)
        self.app.show_midi_mode()
        self.loads.clear()

    # --- helpers -------------------------------------------------------------------------------

    def _row1_label(self) -> str:
        return self.app.lbl_constant_summary.cget("text")

    def _expected_row1(self, mode: str) -> str:
        from music_model.constant_row import calculate_constant_row
        from music_model.development_profile import calculate_development_constant_row
        tl = self.app.timeline
        if mode == "development":
            return f"Row 1 (Dev Profile): {[round(v, 1) for v in calculate_development_constant_row(tl).values]}"
        return f"Row 1 (Constant): {list(calculate_constant_row(tl).values)}"

    def _source_identity(self):
        tr = self.app.transport
        return (tr._wav_bytes, tr.is_synthesized_audio, tr.total_duration_ms, self.app.timeline,
                self.app.current_dataset_name, self.app.lbl_audio_mode.cget("text"),
                tr.audio_backend.temp_wav_path,
                [(e.event_id, e.start_time_ms, e.end_time_ms) for r in self.app.timeline.rows for e in r.events])

    def _toggle_and_check(self, identity, expect_mode: str) -> None:
        snap_before = self.app.transport.snapshot
        self.app._toggle_constant_row_mode()
        self.assertEqual(self.loads, [], "Row 1 toggle must not reload the transport")
        self.assertEqual(self._source_identity(), identity)
        snap = self.app.transport.snapshot
        self.assertIs(snap, snap_before, "no new transport snapshot: state, position and active events untouched")
        self.assertEqual(self.app.current_constant_row_mode, expect_mode)
        self.assertEqual(self.app.timeline_view.constant_row_mode, expect_mode)
        self.assertEqual(self._row1_label(), self._expected_row1(expect_mode))
        self.assertEqual(self.app._btn_row1_toggle.cget("text"),
                         "Row 1: Pitch Dev Profile" if expect_mode == "development" else "Row 1: Active Rows")
        if snap.state != TransportState.STOPPED or snap.position_ms > 0:
            self.assertEqual(self.app.timeline_view._playback_cursor_ms, snap.position_ms)  # cursor survives redraw

    # --- 1-8: original PCM WAV, toggled while stopped, playing and paused ------------------------

    def test_wav_pcm_survives_row1_toggles_in_every_transport_state(self) -> None:
        wav = gapped_wav()
        self._import(self._write("four.wav", wav))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.loads, ["pcm"], "a WAV import loads the transport once, with the original PCM")
        self.loads.clear()
        tr = self.app.transport
        identity = self._source_identity()
        self.assertEqual(identity[0], wav)
        self.assertFalse(identity[1])
        self.assertEqual(identity[4], "Imported WAV: four.wav")
        self.assertEqual(identity[5], "[Audio: Authentic PCM WAV]")
        label_active = self._row1_label()
        self.assertEqual(label_active, self._expected_row1("active_rows"))

        # Stopped: active rows -> development profile; the mathematical display actually changes.
        self._toggle_and_check(identity, "development")
        self.assertNotEqual(self._row1_label(), label_active)
        # Playing.
        self.app.on_transport_play()
        self.sched.advance(150)
        playing = tr.snapshot
        self.assertEqual(playing.state, TransportState.PLAYING)
        self._toggle_and_check(identity, "active_rows")
        self.assertEqual(self._row1_label(), label_active)            # toggled back: identical display
        self.sched.advance(100)
        self.assertEqual(tr.snapshot.state, TransportState.PLAYING)   # playback continued, not restarted
        self.assertGreater(tr.snapshot.position_ms, playing.position_ms)
        # Paused.
        self.app.on_transport_pause()
        paused = tr.snapshot
        self.assertEqual(paused.state, TransportState.PAUSED)
        self._toggle_and_check(identity, "development")
        self._toggle_and_check(identity, "active_rows")
        # Resume and complete naturally at the exact PCM duration: snapshots stay coherent.
        self.app.on_transport_play()
        self.sched.advance(get_wav_duration_ms(wav) + 100)
        end = tr.snapshot
        self.assertEqual((end.state, end.position_ms, end.reason), (TransportState.STOPPED, get_wav_duration_ms(wav), "end"))
        with open(tr.audio_backend.temp_wav_path, "rb") as f:
            self.assertEqual(f.read(), wav)                              # the device still holds the original bytes
        self.assertEqual(self.loads, [])

    # --- 9: a genuinely different source still replaces the previous one ------------------------

    def test_genuine_source_selection_still_replaces_wav(self) -> None:
        wav = gapped_wav()
        self._import(self._write("four.wav", wav))
        self.app._toggle_constant_row_mode()                             # Row 1 = development, display only
        first_temp = self.app.transport.audio_backend.temp_wav_path
        self.loads.clear()
        xml_path = os.path.join(self.tmp, "four.musicxml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(FOUR_NOTE_MUSICXML)
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: xml_path):
            self.app._on_open_musicxml_file()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.loads, ["synth"], "a MusicXML import loads the transport once")
        tr = self.app.transport
        self.assertTrue(tr.is_synthesized_audio)
        self.assertNotEqual(tr._wav_bytes, wav)
        self.assertEqual(self.app.current_dataset_name, "Imported MusicXML: four.musicxml")
        self.assertEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Synthesized (Audible)]")
        self.assertFalse(os.path.exists(first_temp), "previous source's temp WAV released")
        self.assertEqual(len(self.winmm.devices), 1)
        self.assertEqual(self._row1_label(), self._expected_row1("development"))   # Row 1 mode carried over
        # Selecting the MIDI fixture is also a genuine source selection: exactly one load.
        self.loads.clear()
        self.app.show_midi_mode()
        self.assertEqual(self.loads, ["synth"])
        self.assertTrue(self.app.current_dataset_name.startswith("Imported: "))

    # --- equivalent display behaviour for MusicXML and MIDI ------------------------------------

    def test_musicxml_and_midi_sources_survive_row1_toggles(self) -> None:
        xml_path = os.path.join(self.tmp, "four.musicxml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(FOUR_NOTE_MUSICXML)
        with mock.patch.object(self.mw.filedialog, "askopenfilename", lambda **kw: xml_path):
            self.app._on_open_musicxml_file()
        self.assertEqual(self.loads, ["synth"])
        for source in ("musicxml", "midi"):
            if source == "midi":
                self.app.show_midi_mode()
                self.assertEqual(self.loads, ["synth"])
            self.loads.clear()
            identity = self._source_identity()
            self._toggle_and_check(identity, "development")
            self.app.on_transport_play(); self.sched.advance(120)
            self._toggle_and_check(identity, "active_rows")
            self.app.on_transport_pause()
            self._toggle_and_check(identity, "development")
            self._toggle_and_check(identity, "active_rows")
            self.app.on_transport_stop()
            self.loads.clear()
        self.assertEqual(self.errors, [])


AUTHOR_FIXTURE = os.path.join(PROJECT_ROOT, "tests", "fixtures", "JOB03_test.wav")
AUTHOR_FIXTURE_SHA256 = "defffd2a0178fb1cd4d0002d2901afc42169782f38966b4b467bbc4232149c70"


class TestAuthorControlledWavFixture(TestGuiWavImportPath):
    """The Author's ACTUAL controlled file JOB03_test.wav (tests/fixtures), byte-identical to the file
    supplied to the Author: four continuous (legato) pitches C4 D4 E4 G4, 1 s each, no silence between.

    Under the documented JOB-02 silence-based segmentation, continuous notes form ONE sound event
    covering the whole 4 s; its single autocorrelation pitch is E4 (MIDI 64).  This pins that documented
    behaviour; it is not a claim of note segmentation (four-note detection with silences between notes
    is covered by TestGuiWavImportPath.test_import_play_complete_and_replace_source).
    """

    test_import_play_complete_and_replace_source = None
    test_second_open_while_analysing_is_refused_not_queued = None
    test_analysis_error_is_reported_on_tk_thread = None
    test_window_destroyed_during_analysis_ignores_result = None

    def _fixture_bytes(self) -> bytes:
        with open(AUTHOR_FIXTURE, "rb") as f:
            return f.read()

    def test_fixture_is_the_authors_file(self) -> None:
        import hashlib
        data = self._fixture_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), AUTHOR_FIXTURE_SHA256)
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual((w.getcomptype(), w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()),
                             ("NONE", 1, 2, 44100, 176400))
            frames = w.readframes(w.getnframes())
        self.assertEqual(get_wav_duration_ms(data), 4000.0)
        # Ties the code-generated fixture used elsewhere to the actual file (within 1 LSB per sample).
        actual = struct.unpack(f"<{176400}h", frames)
        gen = struct.unpack(f"<{176400}h", author_equivalent_wav()[44:])
        self.assertLessEqual(max(abs(a - b) for a, b in zip(actual, gen)), 1)
        self.assertGreaterEqual(sum(a == b for a, b in zip(actual, gen)), 176000)

    def test_actual_file_gui_import_one_event_pcm_and_natural_completion(self) -> None:
        data = self._fixture_bytes()
        path = self._write("JOB03_test.wav", data)
        max_gap = self._import(path)
        self.assertEqual(self.errors, [])
        self.assertLess(max_gap, 0.5, "Tk loop blocked during analysis")

        # Exactly one continuous sound event covering the full 4 s (JOB-02 segmentation policy).
        events = [e for r in self.app.timeline.rows for e in r.events]
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual((ev.row_id, ev.start_time_ms, ev.end_time_ms), ("Row 2", 0, 4000))
        self.assertEqual((ev.attributes["exact_start_sec_rational"], ev.attributes["exact_end_sec_rational"]), ("0", "4"))
        self.assertEqual((ev.attributes["sample_start_idx"], ev.attributes["sample_end_idx"]), (0, 176400))
        self.assertEqual(ev.attributes["source_type"], "audio_wav")
        self.assertEqual(ev.attributes["pitch_midi"], 64)

        # Dataset identity, badge, and the original PCM recording as the playback source.
        tr = self.app.transport
        self.assertEqual(self.app.current_dataset_name, "Imported WAV: JOB03_test.wav")
        self.assertEqual(self.app.lbl_audio_mode.cget("text"), "[Audio: Authentic PCM WAV]")
        self.assertFalse(tr.is_synthesized_audio)
        self.assertEqual(tr._wav_bytes, data)
        self.assertEqual(tr.total_duration_ms, 4000.0)
        with open(tr.audio_backend.temp_wav_path, "rb") as f:
            self.assertEqual(f.read(), data)

        # Playback: playhead advances, the event is highlighted, completion at exactly 4000 ms.
        self.app.on_transport_play()
        self.sched.advance(1000)
        snap = tr.snapshot
        self.assertEqual(snap.state, TransportState.PLAYING)
        self.assertGreater(snap.position_ms, 900)
        self.assertEqual(self.app.timeline_view._playback_cursor_ms, snap.position_ms)
        self.assertEqual(snap.active_event_ids, frozenset({ev.event_id}))
        self.assertEqual(self.app.timeline_view._currently_active_event_ids, {ev.event_id})
        self.sched.advance(3200)
        end = tr.snapshot
        self.assertEqual((end.state, end.position_ms, end.reason), (TransportState.STOPPED, 4000.0, "end"))
        self.assertEqual(end.active_event_ids, frozenset())
        self.assertEqual(self.app.timeline_view._playback_cursor_ms, 4000.0)
        self.assertEqual(self.app.timeline_view._currently_active_event_ids, set())


if __name__ == "__main__":
    unittest.main()
