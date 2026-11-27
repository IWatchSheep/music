"""Main application window for the Music Project Stage 2B/Stage 3 GUI.

Houses:
- Non-clipping, responsive two-tier navigation and action toolbar.
- View Mode Switcher:
  1. Progressive Refitting Mode: Selectable Stage A (1 col), Stage B (3 cols), Stage C (5 cols).
  2. Duck Flight Experiment (Stage 2B Phase 3): Low-to-high musical development (Arrangement A vs B).
  3. MIDI & Symbolic Passage View (Stage 3): Import SMF Type 0/1 files or reproducible JSON passages.
  4. Dual Independent Songs View: Song 1 vs Song 2 with independent columns and scrolling.
  5. Single Timeline View: Inspect any individual timeline or synthetic proof.
  6. 32-Column Stress Test: Validating wide many-column layouts.
- Row 1 (Constant Musical Row) prominently displayed at the top beneath the time header:
  - Active Temporary Row Count (Diagnostic Baseline).
  - Low-to-High / Pitch Development Profile (Experimental Continuous Measurement).
- Temporary sound rows (Row 2, Row 3, ...) placed below Row 1.
- Pinned left sidebar badges remaining visible during horizontal scrolling.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional, Set

from music_gui.dual_view import DualSongView
from music_gui.gui_style import (
    BG_TOOLBAR,
    BG_WINDOW,
    BORDER_DEFAULT,
    FONT_STATUS,
    FONT_TITLE,
    FONT_TOOLBAR,
    FONT_TOOLBAR_BOLD,
)
from music_gui.audio_playback import (
    AudioBackendError,
    AudioBackendStatus,
    NullAudioBackend,
    PlaybackTransport,
    RealClock,
    TkScheduler,
    TransportSnapshot,
    TransportState,
    WindowsMciAudioBackend,
    WindowsWaveBackend,
)
from music_model.audio_importer import import_audio_to_sound_events
from music_model.musicxml_importer import parse_musicxml
from music_gui.timeline_canvas import TimelineCanvas
from music_model.constant_row import calculate_constant_row
from music_model.datasets import (
    create_32_column_timeline,
    create_continuity_timeline,
    create_dual_independent_songs,
    create_duck_flight_experiment,
    create_linear_many_columns_timeline,
    create_progressive_stage_timeline,
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
)
from music_model.development_profile import calculate_development_constant_row
from music_model.midi_fixture import create_synthetic_orchestral_song
from music_model.midi_importer import MidiImporter
from music_model.passage_format import load_song_from_file, save_song_to_file
from music_model.song import SongTimeline
from music_model.timeline import MusicTimeline
from verify_group_units import (
    build_ascending_passage,
    build_flat_control_passage,
    build_song_2_independent,
)


_log = logging.getLogger(__name__)


class _WavImportJob(threading.Thread):
    """Background JOB-02 analysis of one WAV file (no Tk, transport or device access).

    The result (events or the raised exception) is read by MusicGUI._poll_wav_import on the Tk
    thread after the thread has finished.  The original bytes are kept unchanged for playback.

    Computational lifetime and publishing authority are separate.  The thread always runs to
    completion (Python threads cannot be terminated safely).  It may publish only while it is still
    MusicGUI._wav_import_job and its `generation` equals MusicGUI._source_generation, i.e. no other
    source or mode has been selected since it started (see MusicGUI._supersede_pending_wav_import).
    """

    def __init__(self, filepath: str, wav_bytes: bytes, row_id: str, generation: int) -> None:
        super().__init__(name="WavImportAnalysis", daemon=True)
        self.filepath = filepath
        self.wav_bytes = wav_bytes
        self.row_id = row_id
        self.generation = generation         # source-selection generation at start (read on the Tk thread only)
        self.events: list = []
        self.error: Optional[BaseException] = None

    def run(self) -> None:
        try:
            self.events = import_audio_to_sound_events(self.wav_bytes, row_id=self.row_id)
        except BaseException as ex:          # reported to the user on the Tk thread
            self.error = ex


class MusicGUI(tk.Tk):
    """Main window for the Music Project Timeline GUI."""

    def __init__(self, timeline: Optional[MusicTimeline] = None) -> None:
        super().__init__()
        self.title("Music Project — Progressive Refitting & Independent Song Timelines")
        self.geometry("1180x680")
        self.minsize(800, 480)
        self.configure(bg=BG_WINDOW)

        # Current view states
        self.current_view_mode: str = "progressive"  # 'progressive', 'single', 'dual', 'stress', 'duck', 'midi'
        self.current_stage: str = "A"               # 'A', 'B', 'C'
        self.current_constant_row_mode: str = "active_rows"  # 'active_rows' or 'development'
        self.current_dataset_name: str = "Progressive Refitting — Stage A (Row 2 alone)"
        self.current_group_passage: str = "ascending"
        self.current_group_song: str = "song1"

        # Active timelines
        self.timeline: MusicTimeline = (
            timeline if timeline is not None else create_progressive_stage_timeline("A").timeline
        )
        self.song1, self.song2 = create_dual_independent_songs()
        self.current_song: Optional[SongTimeline] = None
        self.transport: Optional[PlaybackTransport] = None
        self._slider_seeking: bool = False
        # Last transport snapshot rendered by the GUI (stale-notification rejection).
        self._rendered_snapshot: Optional[TransportSnapshot] = None
        # Asynchronous WAV import lifecycle (see _on_open_wav_file and _supersede_pending_wav_import).
        # _source_generation: incremented on every source or mode selection (Tk thread only).
        # _wav_import_job: the pending import that still has authority to publish; None otherwise.
        # _wav_worker: the most recently started analysis thread, authorized or not, so that at most
        #   one analysis computes at a time (an obsolete worker is never terminated, only disowned).
        self._source_generation: int = 0
        self._wav_import_job: Optional[_WavImportJob] = None
        self._wav_worker: Optional[_WavImportJob] = None
        self._wav_import_after_id: Optional[str] = None

        # Build UI layout
        self._build_toolbar()
        self._build_transport_bar()
        self._build_summary_bar()
        self._build_content_area()
        self._build_status_bar()

        # Initial view display
        self.show_progressive_mode("A")

    def _build_toolbar(self) -> None:
        """Create the non-clipping responsive two-tier toolbar."""
        toolbar_container = tk.Frame(self, bg=BG_TOOLBAR, bd=0)
        toolbar_container.pack(fill="x", side="top", padx=8, pady=(6, 2))

        # --- Tier 1: App Title + View Mode Selector ---
        tier1 = tk.Frame(toolbar_container, bg=BG_TOOLBAR)
        tier1.pack(fill="x", side="top", pady=(2, 4))

        title_lbl = tk.Label(
            tier1,
            text="🎵 Music Timeline Studio",
            font=FONT_TITLE,
            bg=BG_TOOLBAR,
            fg="#0f172a",
        )
        title_lbl.pack(side="left", padx=(6, 16))

        tk.Label(
            tier1,
            text="View Mode:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        self.btn_mode_progressive = tk.Button(
            tier1,
            text="Progressive Refitting (A/B/C)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="sunken",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_progressive_mode(self.current_stage),
        )
        self.btn_mode_progressive.pack(side="left", padx=2)

        self.btn_mode_duck = tk.Button(
            tier1,
            text="Duck Flight (Low-to-High)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.show_duck_mode,
        )
        self.btn_mode_duck.pack(side="left", padx=2)

        self.btn_mode_midi = tk.Button(
            tier1,
            text="MIDI / Symbolic Passage",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.show_midi_mode,
        )
        self.btn_mode_midi.pack(side="left", padx=2)

        self.btn_mode_groups = tk.Button(
            tier1,
            text="★ Fundamental Groups (Statement 18)",
            font=FONT_TOOLBAR_BOLD,
            bg="#fef3c7",
            fg="#92400e",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_groups_mode(self.current_group_passage, self.current_group_song),
        )
        self.btn_mode_groups.pack(side="left", padx=2)

        self.btn_mode_dual = tk.Button(
            tier1,
            text="Dual Independent Songs",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.show_dual_mode,
        )
        self.btn_mode_dual.pack(side="left", padx=2)

        self.btn_mode_single = tk.Button(
            tier1,
            text="Single Timeline View",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.show_single_mode,
        )
        self.btn_mode_single.pack(side="left", padx=2)

        self.btn_mode_stress = tk.Button(
            tier1,
            text="32-Column Stress Test",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.show_stress_mode,
        )
        self.btn_mode_stress.pack(side="left", padx=2)

        # --- Tier 2: Dynamic Action Controls & Zoom ---
        self.tier2 = tk.Frame(toolbar_container, bg=BG_TOOLBAR)
        self.tier2.pack(fill="x", side="top", pady=(2, 4))

        # Dynamic subcontrols frame on left of Tier 2
        self.subcontrols_frame = tk.Frame(self.tier2, bg=BG_TOOLBAR)
        self.subcontrols_frame.pack(side="left", fill="x", expand=True)

        # Zoom controls on right of Tier 2 (always visible, never clipped)
        zoom_frame = tk.Frame(self.tier2, bg=BG_TOOLBAR)
        zoom_frame.pack(side="right", padx=(8, 4))

        tk.Label(
            zoom_frame,
            text="Zoom:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 4))

        tk.Button(
            zoom_frame,
            text="Zoom In (+)",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_in,
        ).pack(side="left", padx=2)

        tk.Button(
            zoom_frame,
            text="Zoom Out (−)",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_out,
        ).pack(side="left", padx=2)

        tk.Button(
            zoom_frame,
            text="Reset",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_reset,
        ).pack(side="left", padx=2)

    def _build_transport_bar(self) -> None:
        """Create the real-time audio playback and transport control bar (JOB-03)."""
        bar = tk.Frame(self, bg="#0f172a", padx=8, pady=4)
        bar.pack(fill="x", side="top", padx=8, pady=(0, 2))

        # 1. Transport Buttons
        btn_frame = tk.Frame(bar, bg="#0f172a")
        btn_frame.pack(side="left", padx=(4, 12))

        self.btn_play = tk.Button(
            btn_frame,
            text="▶ Play",
            font=FONT_TOOLBAR_BOLD,
            bg="#22c55e",
            fg="#ffffff",
            activebackground="#16a34a",
            activeforeground="#ffffff",
            relief="raised",
            bd=1,
            padx=10,
            pady=2,
            command=self.on_transport_play,
        )
        self.btn_play.pack(side="left", padx=2)

        self.btn_pause = tk.Button(
            btn_frame,
            text="⏸ Pause",
            font=FONT_TOOLBAR_BOLD,
            bg="#eab308",
            fg="#0f172a",
            activebackground="#ca8a04",
            relief="raised",
            bd=1,
            padx=10,
            pady=2,
            command=self.on_transport_pause,
        )
        self.btn_pause.pack(side="left", padx=2)

        self.btn_stop = tk.Button(
            btn_frame,
            text="⏹ Stop",
            font=FONT_TOOLBAR_BOLD,
            bg="#ef4444",
            fg="#ffffff",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            relief="raised",
            bd=1,
            padx=10,
            pady=2,
            command=self.on_transport_stop,
        )
        self.btn_stop.pack(side="left", padx=2)

        # Loop toggle
        self.loop_var = tk.BooleanVar(value=False)
        self.chk_loop = tk.Checkbutton(
            btn_frame,
            text="Loop",
            variable=self.loop_var,
            font=FONT_TOOLBAR,
            bg="#0f172a",
            fg="#e2e8f0",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            command=self.on_transport_toggle_loop,
        )
        self.chk_loop.pack(side="left", padx=8)

        # 2. Time Position Display
        self.lbl_time = tk.Label(
            bar,
            text="00:00.000 / 00:00.000",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            padx=8,
            pady=3,
            relief="sunken",
            bd=1,
        )
        self.lbl_time.pack(side="left", padx=(0, 12))

        # 3. Audio Mode Badge
        self.lbl_audio_mode = tk.Label(
            bar,
            text="[Audio: Synthesized]",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#a855f7",
            padx=6,
            pady=2,
            relief="groove",
            bd=1,
        )
        self.lbl_audio_mode.pack(side="left", padx=(0, 12))

        # 4. Seek Slider
        self.seek_var = tk.DoubleVar(value=0.0)
        self.seek_slider = ttk.Scale(
            bar,
            from_=0.0,
            to=1000.0,
            orient="horizontal",
            variable=self.seek_var,
            command=self._on_slider_change,
        )
        self.seek_slider.pack(side="left", fill="x", expand=True, padx=4)
        self.seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "_slider_seeking", True))
        self.seek_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Keyboard shortcuts
        self.bind("<space>", lambda e: self.on_transport_toggle_play_pause())
        self.bind("<Escape>", lambda e: self.on_transport_stop())

    def _handle_audio_error(self, ex: Exception) -> None:
        """Surface audio backend failures cleanly in GUI status badge."""
        err_msg = f"[Audio Error: {ex}]"
        if hasattr(self, "lbl_audio_mode"):
            self.lbl_audio_mode.configure(text=err_msg[:40], fg="#ef4444")

    def on_transport_play(self) -> None:
        """Start audio playback and visual transport."""
        if self.transport is not None:
            try:
                self.transport.play()
            except AudioBackendError as ex:
                self._handle_audio_error(ex)

    def on_transport_pause(self) -> None:
        """Pause playback preserving exact position."""
        if self.transport is not None:
            try:
                self.transport.pause()
            except AudioBackendError as ex:
                self._handle_audio_error(ex)

    def on_transport_stop(self) -> None:
        """Stop playback.

        The cursor is not cleared here: the transport's own snapshot decides it.  A
        successful stop publishes STOPPED at 0 (idle: cursor cleared); a failed stop
        publishes ERROR at the preserved coordinate (cursor kept there).
        """
        if self.transport is not None:
            try:
                self.transport.stop()
            except AudioBackendError as ex:
                self._handle_audio_error(ex)

    def on_transport_toggle_play_pause(self) -> None:
        """Toggle play/pause via keyboard shortcut or toolbar."""
        if self.transport is not None:
            try:
                if self.transport.state == TransportState.PLAYING:
                    self.transport.pause()
                else:
                    self.transport.play()
            except AudioBackendError as ex:
                self._handle_audio_error(ex)

    def on_transport_toggle_loop(self) -> None:
        """Toggle transport loop mode."""
        if self.transport is not None:
            self.transport.set_loop(self.loop_var.get())

    def _on_slider_change(self, val: Any) -> None:
        """Handle interactive slider dragging (preview label only; no transport change)."""
        if self._slider_seeking:
            target_ms = float(val)
            dur_ms = self.transport.total_duration_ms if self.transport else 0.0
            self.lbl_time.configure(text=f"{self._format_time(target_ms)} / {self._format_time(dur_ms)}")

    def _on_slider_release(self, _event: Any) -> None:
        """Apply seek position when slider is released.

        On failure the transport publishes ERROR at the preserved coordinate and the
        slider is moved back there by that snapshot.
        """
        self._slider_seeking = False
        if self.transport is not None:
            try:
                self.transport.seek(float(self.seek_var.get()))
            except AudioBackendError as ex:
                self._handle_audio_error(ex)
            # Re-render the authoritative coordinate (a drag preview may have changed the label).
            snap = self.transport.snapshot
            if snap is not None:
                self._render_snapshot(snap)

    def _format_time(self, ms: float) -> str:
        """Format milliseconds into mm:ss.mmm string."""
        s = int(ms // 1000)
        m = s // 60
        rem_s = s % 60
        rem_ms = int(ms % 1000)
        return f"{m:02d}:{rem_s:02d}.{rem_ms:03d}"

    # --- JOB-03 snapshot rendering ------------------------------------------------
    #
    # Cursor display policy (applied to every snapshot, in every transport state):
    #   * STOPPED at exactly 0 ms is the idle rest state: playhead cursor and active-event
    #     highlighting are cleared; slider at 0; label 00:00.000.
    #   * Every other snapshot (PLAYING, PAUSED, ERROR, and STOPPED at a non-zero
    #     position such as after a seek while stopped or after natural completion) shows
    #     the cursor at snapshot.position_ms and highlights exactly
    #     snapshot.active_event_ids.  Highlighting is shown if and only if the cursor is.
    # Slider, elapsed-time label, cursor, highlighting and the transport buttons are all
    # rendered from the same immutable snapshot.

    @staticmethod
    def _is_idle_snapshot(snap: TransportSnapshot) -> bool:
        return snap.state == TransportState.STOPPED and snap.position_ms == 0.0

    def _on_transport_snapshot(self, snap: TransportSnapshot) -> None:
        """Render one published transport snapshot (delivered on the Tk thread).

        Rejects snapshots from a replaced transport, from a replaced source, and any
        snapshot that does not supersede the one already rendered (out of order).
        """
        tr = self.transport
        if tr is None or snap.transport_id != tr.transport_id or snap.source_id != tr.source_id:
            return
        if not snap.supersedes(self._rendered_snapshot):
            return
        self._render_snapshot(snap)

    def _render_snapshot(self, snap: TransportSnapshot) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self._rendered_snapshot = snap
        pos_ms = snap.position_ms
        dur_ms = snap.total_duration_ms
        try:
            self.seek_slider.configure(to=max(1.0, dur_ms))
            if not self._slider_seeking:
                self.seek_var.set(pos_ms)
            self.lbl_time.configure(text=f"{self._format_time(pos_ms)} / {self._format_time(dur_ms)}")
            view = getattr(self, "timeline_view", None)
            if view is not None:
                if self._is_idle_snapshot(snap):
                    view.clear_playback_cursor()
                elif self.current_view_mode not in ("dual", "duck", "groups"):
                    view.set_playback_cursor(
                        pos_ms, set(snap.active_event_ids), auto_scroll=(snap.state == TransportState.PLAYING)
                    )
            self._update_transport_buttons(snap.state)
        except tk.TclError:
            _log.debug("Snapshot render skipped: widgets are being destroyed")

    def _on_transport_error(self, err: Exception) -> None:
        """Error callback (delivered on the Tk thread after the ERROR snapshot)."""
        try:
            if self.winfo_exists():
                self._handle_audio_error(err)
        except tk.TclError:
            pass

    def _update_transport_buttons(self, state: TransportState) -> None:
        """Update play/pause button visual states."""
        if state == TransportState.PLAYING:
            self.btn_play.configure(relief="sunken", bg="#15803d")
            self.btn_pause.configure(relief="raised", bg="#eab308")
        elif state == TransportState.PAUSED:
            self.btn_play.configure(relief="raised", bg="#22c55e")
            self.btn_pause.configure(relief="sunken", bg="#ca8a04")
        elif state == TransportState.ERROR:
            self.btn_play.configure(relief="raised", bg="#ef4444")
            self.btn_pause.configure(relief="raised", bg="#eab308")
        else:
            self.btn_play.configure(relief="raised", bg="#22c55e")
            self.btn_pause.configure(relief="raised", bg="#eab308")
        self._update_audio_mode_badge()

    def _update_audio_mode_badge(self) -> None:
        """Update audio mode indicator badge reflecting true device and synthesis state."""
        if self.transport is None:
            self.lbl_audio_mode.configure(text="[Audio: None]", fg="#64748b")
            return

        if self.transport.state == TransportState.ERROR:
            self.lbl_audio_mode.configure(text="[Audio: Device Error]", fg="#ef4444")
            return

        status = self.transport.audio_backend.get_status()
        if status == AudioBackendStatus.FAILED:
            self.lbl_audio_mode.configure(text="[Audio: Device Failed]", fg="#ef4444")
        elif status == AudioBackendStatus.UNAVAILABLE:
            self.lbl_audio_mode.configure(text="[Audio: Unavailable]", fg="#64748b")
        elif status == AudioBackendStatus.SIMULATED:
            self.lbl_audio_mode.configure(text="[Audio: Simulated]", fg="#f59e0b")
        elif self.transport.is_synthesized_audio:
            self.lbl_audio_mode.configure(text="[Audio: Synthesized (Audible)]", fg="#a855f7")
        else:
            self.lbl_audio_mode.configure(text="[Audio: Authentic PCM WAV]", fg="#22c55e")

    def _create_transport(self) -> PlaybackTransport:
        """Create the GUI's single transport: Tk-thread scheduler, owner = this Tk thread."""
        mci = WindowsMciAudioBackend()
        backend = mci if mci.is_available() else NullAudioBackend()
        transport = PlaybackTransport(
            clock=RealClock(),
            audio_backend=backend,
            scheduler=TkScheduler(self),
        )
        transport.set_loop(bool(self.loop_var.get()))
        transport.register_snapshot_callback(self._on_transport_snapshot)
        transport.register_error_callback(self._on_transport_error)
        return transport

    def _sync_transport_with_current_timeline(self, wav_bytes: Optional[bytes] = None) -> None:
        """Load the current active timeline (and synthesized or PCM audio) into the transport.

        Source replacement stops the previous source and releases its device resources
        (load_timeline); the 'load' snapshot resets slider, label and cursor.
        """
        # Installing any source supersedes a pending WAV import (no-op when none is pending; the
        # completing import itself is no longer pending when _apply_imported_wav calls this).
        self._supersede_pending_wav_import()
        if self.transport is None:
            self.transport = self._create_transport()
        try:
            self.transport.load_timeline(self.timeline, wav_bytes=wav_bytes, synthesize=True)
        except AudioBackendError as ex:
            self._handle_audio_error(ex)
        snap = self.transport.snapshot
        if snap is not None:
            self._render_snapshot(snap)

    def destroy(self) -> None:
        """Release playback resources before window teardown.

        close() cancels the pending Tk update, stops audio, closes the MCI device and
        removes this application's temp WAV.  A cleanup failure is logged, not hidden.
        """
        # An unfinished analysis loses its authority; its daemon thread may finish but never publishes.
        self._supersede_pending_wav_import(refresh_badge=False)
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                _log.exception("Playback transport cleanup failed during window teardown")
        super().destroy()

    def _build_summary_bar(self) -> None:
        """Create the summary metric banner above the timeline canvas."""
        f = tk.Frame(self, bg="#ffffff", highlightbackground=BORDER_DEFAULT, highlightthickness=1)
        f.pack(fill="x", padx=8, pady=(2, 4))

        self.lbl_dataset = tk.Label(
            f,
            text="",
            font=FONT_TOOLBAR_BOLD,
            bg="#ffffff",
            fg="#0369a1",
        )
        self.lbl_dataset.pack(side="left", padx=12, pady=4)

        self.lbl_summary = tk.Label(
            f,
            text="",
            font=FONT_TOOLBAR,
            bg="#ffffff",
            fg="#334155",
        )
        self.lbl_summary.pack(side="left", padx=8, pady=4)

        self.lbl_constant_summary = tk.Label(
            f,
            text="",
            font=FONT_TOOLBAR_BOLD,
            bg="#ffffff",
            fg="#7c2d12",
        )
        self.lbl_constant_summary.pack(side="right", padx=12, pady=4)

    def _build_content_area(self) -> None:
        """Create the central display area hosting the Single and Dual timeline canvases."""
        self.content_frame = tk.Frame(self, bg=BG_WINDOW)
        self.content_frame.pack(fill="both", expand=True, padx=8, pady=2)

        # 1. Single Timeline Canvas (used for Progressive Stages, Single View, Stress Test, MIDI)
        self.timeline_view = TimelineCanvas(self.content_frame, self.timeline)

        # 2. Dual Independent Songs View (used for Song 1 vs Song 2, Duck Flight A vs B)
        self.dual_view = DualSongView(self.content_frame, self.song1, self.song2)

    def _build_status_bar(self) -> None:
        """Create the bottom status bar."""
        status_frame = tk.Frame(self, bg=BG_TOOLBAR, bd=0)
        status_frame.pack(fill="x", side="bottom", padx=8, pady=(2, 4))

        self.lbl_status = tk.Label(
            status_frame,
            text="Row 1: Constant Musical Row (At Top) | Sounds dictate variable-width columns | Scroll: Wheel / Shift+Wheel / Ctrl+Wheel",
            font=FONT_STATUS,
            bg=BG_TOOLBAR,
            fg="#64748b",
        )
        self.lbl_status.pack(side="left", padx=8, pady=2)

    def _update_status_bar(self) -> None:
        """Update bottom status bar text based on active view mode."""
        if self.current_view_mode == "groups":
            self.lbl_status.configure(
                text="Fundamental cells have equal width | Sound groups span multiple cells | Row 1 combines group boundaries"
            )
        else:
            self.lbl_status.configure(
                text="Row 1: Constant Musical Row (At Top) | Sounds dictate variable-width columns | Scroll: Wheel / Shift+Wheel / Ctrl+Wheel"
            )

    def _clear_subcontrols(self) -> None:
        """Clear dynamic Tier 2 subcontrols."""
        for widget in self.subcontrols_frame.winfo_children():
            widget.destroy()

    def _set_active_mode_button(self, active_btn: tk.Button) -> None:
        """Update top-tier mode button styles.

        Every show_*_mode entry point calls this, including modes that do not reload the transport
        (dual, duck, groups), so a mode selection supersedes a pending WAV import here.
        """
        self._supersede_pending_wav_import()
        all_buttons = (
            self.btn_mode_progressive,
            self.btn_mode_duck,
            self.btn_mode_midi,
            self.btn_mode_groups,
            self.btn_mode_dual,
            self.btn_mode_single,
            self.btn_mode_stress,
        )
        for b in all_buttons:
            if b is active_btn:
                b.configure(bg="#e0f2fe", fg="#0369a1", relief="sunken")
            else:
                b.configure(bg="#f1f5f9", fg="#334155", relief="raised")

    # --- Mode 1: Progressive Refitting ---

    def show_progressive_mode(self, stage: str = "A") -> None:
        """Display the progressive column refitting demonstration."""
        self.current_view_mode = "progressive"
        self.current_stage = stage.upper()
        self.current_constant_row_mode = "active_rows"
        self.timeline_view.set_constant_row_mode("active_rows")
        self._set_active_mode_button(self.btn_mode_progressive)
        self.timeline_view.clear_group_timeline()

        # Show single canvas, hide dual view
        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        # Load stage timeline
        song = create_progressive_stage_timeline(self.current_stage)
        self.timeline = song.timeline
        self.timeline_view.set_timeline(self.timeline)

        # Populate Tier 2 subcontrols with Stage A, B, C buttons
        self._clear_subcontrols()

        tk.Label(
            self.subcontrols_frame,
            text="Progressive Stages:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        self.btn_stage_a = tk.Button(
            self.subcontrols_frame,
            text="Stage A: Row 2 alone (1 col)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe" if self.current_stage == "A" else "#f1f5f9",
            fg="#0369a1" if self.current_stage == "A" else "#334155",
            relief="sunken" if self.current_stage == "A" else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_progressive_mode("A"),
        )
        self.btn_stage_a.pack(side="left", padx=3)

        self.btn_stage_b = tk.Button(
            self.subcontrols_frame,
            text="Stage B: Add Row 3 (3 cols)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe" if self.current_stage == "B" else "#f1f5f9",
            fg="#0369a1" if self.current_stage == "B" else "#334155",
            relief="sunken" if self.current_stage == "B" else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_progressive_mode("B"),
        )
        self.btn_stage_b.pack(side="left", padx=3)

        self.btn_stage_c = tk.Button(
            self.subcontrols_frame,
            text="Stage C: Add Row 4 (5 cols)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe" if self.current_stage == "C" else "#f1f5f9",
            fg="#0369a1" if self.current_stage == "C" else "#334155",
            relief="sunken" if self.current_stage == "C" else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_progressive_mode("C"),
        )
        self.btn_stage_c.pack(side="left", padx=3)

        self.current_dataset_name = f"Progressive Refitting — Stage {self.current_stage}"
        self._update_summary()

    # --- Mode 2: Duck Flight Experiment (Low-to-High Development) ---

    def show_duck_mode(self) -> None:
        """Display the duck running on water low-to-high experiment (Arrangement A vs B)."""
        self.current_view_mode = "duck"
        self._set_active_mode_button(self.btn_mode_duck)
        self.timeline_view.clear_group_timeline()

        song_a, song_b = create_duck_flight_experiment()
        self.song1 = song_a
        self.song2 = song_b
        self.dual_view.set_songs(song_a, song_b)
        self.dual_view.set_constant_row_mode(self.current_constant_row_mode)

        self.timeline_view.pack_forget()
        self.dual_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Duck Flight Experiment:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            self.subcontrols_frame,
            text="Dual Comparison (A vs B)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="sunken",
            bd=1,
            padx=6,
            pady=2,
            command=self.show_duck_mode,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Inspect Arrangement A (Direct, 5 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=lambda: self._show_solo_duck(song_a),
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Inspect Arrangement B (Connected, 11 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=lambda: self._show_solo_duck(song_b),
        ).pack(side="left", padx=2)

        toggle_txt = "Mode: Active Rows" if self.current_constant_row_mode == "active_rows" else "Mode: Dev Profile"
        tk.Button(
            self.subcontrols_frame,
            text=f"Toggle {toggle_txt}",
            font=FONT_TOOLBAR_BOLD,
            bg="#fef3c7",
            fg="#92400e",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._toggle_constant_row_mode,
        ).pack(side="left", padx=(8, 2))

        self.current_dataset_name = "Duck Flight Experiment: Arrangement A (Direct) vs B (Connected)"
        self.lbl_dataset.configure(text=f"Mode: {self.current_dataset_name}")
        cols1 = self.song1.column_count
        cols2 = self.song2.column_count
        self.lbl_summary.configure(
            text=f"Arrangement A: {cols1} cols, {self.song1.total_duration_ms} ms  |  Arrangement B: {cols2} cols, {self.song2.total_duration_ms} ms"
        )
        self._refresh_dual_constant_summary()
        self._update_status_bar()
        if self.transport is not None:
            self.on_transport_stop()

    def _show_solo_duck(self, song: SongTimeline) -> None:
        """Display a single arrangement in the full single-canvas view."""
        self.timeline_view.clear_group_timeline()
        self.timeline = song.timeline
        self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
        self.timeline_view.set_timeline(self.timeline)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.current_dataset_name = song.title
        self._update_summary()

    # --- Mode 3: MIDI & Symbolic Passage Importer ---

    def show_midi_mode(self, song: Optional[SongTimeline] = None) -> None:
        """Display an imported MIDI file or reproducible JSON passage."""
        self.current_view_mode = "midi"
        self._set_active_mode_button(self.btn_mode_midi)
        self.timeline_view.clear_group_timeline()

        if song is None:
            song = create_synthetic_orchestral_song()

        self.current_song = song
        self.timeline = song.timeline
        self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
        self.timeline_view.set_timeline(self.timeline)

        # Show single canvas, hide dual view
        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="MIDI & Passage Tools:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            self.subcontrols_frame,
            text="Synthetic Orchestral (MIDI)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=lambda: self.show_midi_mode(create_synthetic_orchestral_song()),
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Open MIDI... (.mid)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_open_midi_file,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Open JSON... (.json)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_open_json_file,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Open Audio WAV... (.wav)",
            font=FONT_TOOLBAR_BOLD,
            bg="#dcfce7",
            fg="#166534",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_open_wav_file,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Open MusicXML... (.xml)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_open_musicxml_file,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Export JSON... (.json)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_export_json_file,
        ).pack(side="left", padx=2)

        self._btn_row1_toggle = tk.Button(
            self.subcontrols_frame,
            text=self._row1_toggle_text(),
            font=FONT_TOOLBAR_BOLD,
            bg="#fef3c7",
            fg="#92400e",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._toggle_constant_row_mode,
        )
        self._btn_row1_toggle.pack(side="left", padx=(8, 2))

        self.current_dataset_name = f"Imported: {song.title}"
        self._update_summary()

    def _on_open_midi_file(self) -> None:
        """Prompt user for a MIDI file and import it."""
        filepath = filedialog.askopenfilename(
            title="Open MIDI File",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")],
        )
        if not filepath:
            return
        try:
            importer = MidiImporter()
            song = importer.import_file(filepath)
            self.show_midi_mode(song)
        except Exception as ex:
            messagebox.showerror("MIDI Import Error", f"Failed to import MIDI file:\n{ex}")

    def _on_open_json_file(self) -> None:
        """Prompt user for a passage JSON file and load it."""
        filepath = filedialog.askopenfilename(
            title="Open Passage JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filepath:
            return
        try:
            song = load_song_from_file(filepath)
            self.show_midi_mode(song)
        except Exception as ex:
            messagebox.showerror("Passage Load Error", f"Failed to load JSON passage:\n{ex}")

    # Row that receives imported WAV events.  The importer must label events with this same
    # row id: TemporaryRow.add_event rejects events whose row_id differs from the row's id.
    WAV_IMPORT_ROW_ID = "Row 2"
    WAV_IMPORT_POLL_MS = 50

    def _on_open_wav_file(self) -> None:
        """Prompt for a PCM WAV file and analyse it without blocking the Tk thread.

        The JOB-02 analysis (pure Python, CPU-bound, ~26 s for a 4 s sustained recording) runs on a
        worker thread.  It touches no Tk widget, transport or audio device; the finished events are
        applied on the Tk thread by _poll_wav_import, which owns the transport and the MCI device.
        """
        filepath = filedialog.askopenfilename(
            title="Open PCM WAV File",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if not filepath:
            return
        if self._wav_import_job is not None:
            messagebox.showinfo("Audio Import", "A WAV file is still being analysed. Please wait until it finishes.")
            return
        if self._wav_worker is not None and self._wav_worker.is_alive():
            # A superseded analysis is still computing.  It cannot be stopped safely, and starting a
            # second one would let workers accumulate, so the new import is refused, not queued.
            messagebox.showinfo(
                "Audio Import",
                "A previous WAV analysis is still finishing in the background (its result will be discarded). "
                "Please try again in a moment.",
            )
            return
        try:
            with open(filepath, "rb") as f:
                wav_bytes = f.read()
        except OSError as ex:
            messagebox.showerror("Audio Import Error", f"Failed to read WAV audio file:\n{ex}")
            return
        job = _WavImportJob(filepath, wav_bytes, self.WAV_IMPORT_ROW_ID, self._source_generation)
        self._wav_import_job = job
        self._wav_worker = job
        self.lbl_audio_mode.configure(text="[Audio: Analysing WAV...]", fg="#f59e0b")
        job.start()
        self._wav_import_after_id = self.after(self.WAV_IMPORT_POLL_MS, self._poll_wav_import, job)

    def _has_publish_authority(self, job: "_WavImportJob") -> bool:
        """True only for the pending import, started under the current source-selection generation."""
        return job is self._wav_import_job and job.generation == self._source_generation

    def _supersede_pending_wav_import(self, refresh_badge: bool = True) -> None:
        """Record a source or mode selection; a pending WAV import loses its authority to publish.

        Tk thread only.  The worker thread is not touched: it runs to completion and its result,
        success or failure, is discarded (no timeline, transport, dialog or badge change).  The
        'Analysing' badge is replaced by the truthful badge for the current transport.
        """
        self._source_generation += 1
        job = self._wav_import_job
        if job is None:
            return
        self._wav_import_job = None
        if self._wav_import_after_id is not None:
            try:
                self.after_cancel(self._wav_import_after_id)
            except tk.TclError:
                pass
            self._wav_import_after_id = None
        _log.info("WAV import of %r superseded by a newer source selection; its result will be discarded",
                  job.filepath)
        if refresh_badge:
            try:
                self._update_audio_mode_badge()
            except tk.TclError:
                pass

    def _poll_wav_import(self, job: "_WavImportJob") -> None:
        """Tk-thread completion check for a background WAV analysis."""
        if not self._has_publish_authority(job):
            return                                   # superseded, or window being destroyed
        if job.is_alive():
            self._wav_import_after_id = self.after(self.WAV_IMPORT_POLL_MS, self._poll_wav_import, job)
            return
        self._wav_import_job = None
        self._wav_import_after_id = None
        self._update_audio_mode_badge()              # truthful badge for the (unchanged) current source
        if job.error is not None:
            messagebox.showerror("Audio Import Error", f"Failed to import WAV audio file:\n{job.error}")
            return
        try:
            self._apply_imported_wav(job.filepath, job.wav_bytes, job.events)
        except Exception as ex:
            messagebox.showerror("Audio Import Error", f"Failed to import WAV audio file:\n{ex}")

    def _apply_imported_wav(self, filepath: str, wav_bytes: bytes, events: list) -> None:
        """Install analysed WAV events and the ORIGINAL PCM bytes as the playback source (Tk thread)."""
        import os
        basename = os.path.basename(filepath)
        song = SongTimeline("imported_wav", basename)
        row = song.create_row(self.WAV_IMPORT_ROW_ID, label="Audio Events")
        for e in events:
            row.add_event(e)
        self.current_song = song
        self.timeline = song.timeline
        self.timeline_view.clear_group_timeline()
        self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
        self.timeline_view.set_timeline(self.timeline)
        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)
        self.current_dataset_name = f"Imported WAV: {song.title}"
        self._refresh_summary_display()
        self._sync_transport_with_current_timeline(wav_bytes=wav_bytes)   # the one load: original PCM

    def _on_open_musicxml_file(self) -> None:
        """Prompt user for a MusicXML file and import it for playback."""
        filepath = filedialog.askopenfilename(
            title="Open MusicXML File",
            filetypes=[("MusicXML files", "*.xml *.musicxml"), ("All files", "*.*")],
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                xml_content = f.read()
            import_res = parse_musicxml(xml_content)
            import os
            basename = os.path.basename(filepath)
            song = SongTimeline("imported_musicxml", basename)
            rows_dict = {}
            for e in import_res.sound_events:
                r_id = e.row_id or "Row 2"
                if r_id not in rows_dict:
                    rows_dict[r_id] = song.create_row(r_id, label=r_id)
                rows_dict[r_id].add_event(e)
            self.current_song = song
            self.timeline = song.timeline
            self.timeline_view.clear_group_timeline()
            self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
            self.timeline_view.set_timeline(self.timeline)
            self.dual_view.pack_forget()
            self.timeline_view.pack(fill="both", expand=True)
            self.current_dataset_name = f"Imported MusicXML: {song.title}"
            self._refresh_summary_display()
            self._sync_transport_with_current_timeline(wav_bytes=None)    # the one load: synthesized
        except Exception as ex:
            messagebox.showerror("MusicXML Import Error", f"Failed to import MusicXML file:\n{ex}")

    def _on_export_json_file(self) -> None:
        """Export the currently active song/passage to JSON."""
        if self.current_song is None:
            # Build a song from the active timeline
            self.current_song = SongTimeline("exported_passage", self.current_dataset_name)
            for r in self.timeline.rows:
                row = self.current_song.create_row(r.row_id, r.label)
                for e in r.events:
                    row.add_event(e)

        filepath = filedialog.asksaveasfilename(
            title="Export Passage to JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.current_song.song_id}.json",
        )
        if not filepath:
            return
        try:
            save_song_to_file(self.current_song, filepath)
            messagebox.showinfo("Export Successful", f"Passage saved to:\n{filepath}")
        except Exception as ex:
            messagebox.showerror("Export Error", f"Failed to export passage:\n{ex}")

    def _toggle_constant_row_mode(self) -> None:
        """Toggle Row 1 measurement between active_rows baseline and development profile."""
        if self.current_constant_row_mode == "active_rows":
            self.current_constant_row_mode = "development"
        else:
            self.current_constant_row_mode = "active_rows"

        self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
        self.dual_view.set_constant_row_mode(self.current_constant_row_mode)

        # Display only: Row 1 is a mathematical representation of the current source, not a new
        # source.  The transport (original PCM or synthesized audio, state, position), the dataset
        # identity and any pending WAV import are left untouched.  The canvases were redrawn above
        # (set_constant_row_mode -> redraw, which re-applies the playback cursor).
        if self.current_view_mode in ("duck", "dual"):
            self._refresh_dual_constant_summary()
        else:
            if self.current_view_mode == "midi":
                btn = getattr(self, "_btn_row1_toggle", None)
                if btn is not None and btn.winfo_exists():
                    btn.configure(text=self._row1_toggle_text())
            self._refresh_summary_display()

    def _row1_toggle_text(self) -> str:
        """Label of the MIDI-mode Row 1 toggle button for the current measurement mode."""
        return "Row 1: Active Rows" if self.current_constant_row_mode == "active_rows" else "Row 1: Pitch Dev Profile"

    def _refresh_dual_constant_summary(self) -> None:
        """Update summary banner for dual views."""
        if self.current_constant_row_mode == "development":
            c1 = [round(v, 1) for v in calculate_development_constant_row(self.song1.timeline).values]
            c2 = [round(v, 1) for v in calculate_development_constant_row(self.song2.timeline).values]
            lbl = "Row 1 (Dev Profile)"
        else:
            c1 = list(self.song1.constant_row.values)
            c2 = list(self.song2.constant_row.values)
            lbl = "Row 1 (Constant)"

        self.lbl_constant_summary.configure(
            text=f"{lbl} S1: {c1}  |  S2: {c2}"
        )

    # --- Mode 4: Dual Independent Songs View ---

    def show_dual_mode(self) -> None:
        """Display two independent songs with separate timelines and scrollbars."""
        self.current_view_mode = "dual"
        self._set_active_mode_button(self.btn_mode_dual)
        self.timeline_view.clear_group_timeline()

        self.song1, self.song2 = create_dual_independent_songs()
        self.dual_view.set_songs(self.song1, self.song2)
        self.dual_view.set_constant_row_mode(self.current_constant_row_mode)

        # Show dual view, hide single view
        self.timeline_view.pack_forget()
        self.dual_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Dual Independent Songs:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            self.subcontrols_frame,
            text="Inspect Song 1 Alone (5 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._show_solo_song1,
        ).pack(side="left", padx=3)

        tk.Button(
            self.subcontrols_frame,
            text="Inspect Song 2 Alone (7 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._show_solo_song2,
        ).pack(side="left", padx=3)

        self.current_dataset_name = "Dual Independent Songs: Song 1 (5 cols) vs Song 2 (7 cols)"
        self.lbl_dataset.configure(text=f"Dataset: {self.current_dataset_name}")
        cols1 = self.song1.column_count
        cols2 = self.song2.column_count
        self.lbl_summary.configure(
            text=f"Song 1: {cols1} cols, {self.song1.total_duration_ms} ms  |  Song 2: {cols2} cols, {self.song2.total_duration_ms} ms"
        )
        self._refresh_dual_constant_summary()
        self._update_status_bar()
        if self.transport is not None:
            self.on_transport_stop()

    def _show_solo_song1(self) -> None:
        """Display Song 1 alone in single view."""
        self.timeline_view.clear_group_timeline()
        self.timeline = self.song1.timeline
        self.timeline_view.set_timeline(self.timeline)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.current_dataset_name = self.song1.title
        self._update_summary()

    def _show_solo_song2(self) -> None:
        """Display Song 2 alone in single view."""
        self.timeline_view.clear_group_timeline()
        self.timeline = self.song2.timeline
        self.timeline_view.set_timeline(self.timeline)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.current_dataset_name = self.song2.title
        self._update_summary()

    # --- Mode 5: Single Timeline View ---

    def show_single_mode(self) -> None:
        """Display single timeline mode with synthetic proof selection."""
        self.current_view_mode = "single"
        self._set_active_mode_button(self.btn_mode_single)
        self.timeline_view.clear_group_timeline()

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.timeline = create_stage_1_proof_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self.current_dataset_name = "Stage 1 Mathematical Proof (Events A, B, C)"

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Synthetic Datasets:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            self.subcontrols_frame,
            text="Stage 1 Proof (5 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_stage_1_proof,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Variable-Width (4 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_variable_width_proof,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Continuity Proof (7 cols)",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_continuity_proof,
        ).pack(side="left", padx=2)

        self._update_summary()

    # --- Mode 6: 32-Column Stress Test ---

    def show_stress_mode(self) -> None:
        """Display the 32-column layout stress test."""
        self.current_view_mode = "stress"
        self._set_active_mode_button(self.btn_mode_stress)
        self.timeline_view.clear_group_timeline()

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.timeline = create_32_column_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self.current_dataset_name = "32-Column Layout Stress Test (Dense boundary alignment)"

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Stress Test: 32 linked columns derived across 32,000 ms.",
            font=FONT_TOOLBAR,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=6)

        self._update_summary()

    # --- Mode 7: Statement 18 Fundamental Column Groups Mode ---

    def show_groups_mode(self, passage_mode: str = "ascending", song_id: str = "song1") -> None:
        """Display Statement 18 uniform fundamental cells, multi-unit groups, and composite Row 1."""
        self.current_view_mode = "groups"
        self.current_group_passage = passage_mode
        self.current_group_song = song_id
        self._set_active_mode_button(self.btn_mode_groups)

        # Show single canvas, hide dual view
        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        if song_id == "song2":
            gt = build_song_2_independent(250)
            desc_title = "Statement 18 — Song 2 Independent (5u vs 2u, u=250ms, 10 cells)"
        elif passage_mode == "flat":
            gt = build_flat_control_passage(100)
            desc_title = "Statement 18 — Flat Control Passage (49.0 steady, 12 cells)"
        else:
            gt = build_ascending_passage(100)
            desc_title = "Statement 18 — Ascending Takeoff Passage (48.0 -> 66.0, 12 cells)"

        self.timeline_view.set_group_timeline(gt, passage_mode=passage_mode)

        # Populate Tier 2 subcontrols
        self._clear_subcontrols()

        tk.Label(
            self.subcontrols_frame,
            text="Statement 18 Controls:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        is_asc = (song_id == "song1" and passage_mode == "ascending")
        tk.Button(
            self.subcontrols_frame,
            text="Ascending Takeoff (48→66)",
            font=FONT_TOOLBAR_BOLD if is_asc else FONT_TOOLBAR,
            bg="#e0f2fe" if is_asc else "#f1f5f9",
            fg="#0369a1" if is_asc else "#334155",
            relief="sunken" if is_asc else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_groups_mode("ascending", "song1"),
        ).pack(side="left", padx=2)

        is_flat = (song_id == "song1" and passage_mode == "flat")
        tk.Button(
            self.subcontrols_frame,
            text="Flat Control (49 steady)",
            font=FONT_TOOLBAR_BOLD if is_flat else FONT_TOOLBAR,
            bg="#e0f2fe" if is_flat else "#f1f5f9",
            fg="#0369a1" if is_flat else "#334155",
            relief="sunken" if is_flat else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_groups_mode("flat", "song1"),
        ).pack(side="left", padx=2)

        is_s2 = (song_id == "song2")
        tk.Button(
            self.subcontrols_frame,
            text="Song 2 Independent (5u vs 2u)",
            font=FONT_TOOLBAR_BOLD if is_s2 else FONT_TOOLBAR,
            bg="#e0f2fe" if is_s2 else "#f1f5f9",
            fg="#0369a1" if is_s2 else "#334155",
            relief="sunken" if is_s2 else "raised",
            bd=1,
            padx=8,
            pady=2,
            command=lambda: self.show_groups_mode("ascending", "song2"),
        ).pack(side="left", padx=2)

        # Update Summary Bar
        self.current_dataset_name = desc_title
        self.lbl_dataset.configure(text=f"Dataset: {self.current_dataset_name}")
        r1_segs = gt.derive_row1_segments()
        widths = [s.width_units for s in r1_segs]
        pitches = [round(s.mean_pitch, 1) for s in r1_segs]
        self.lbl_summary.configure(
            text=f"Grid: {gt.grid.total_cells} cells (u={gt.grid.u_ms}ms)  |  Row 1: {len(r1_segs)} segments (widths {widths})  |  Bounds: {gt.combined_boundaries()}"
        )
        self.lbl_constant_summary.configure(
            text=f"Row 1 Pitches: {pitches}"
        )
        self._update_status_bar()
        if self.transport is not None:
            self.on_transport_stop()

    # --- Helper & Utility Methods ---

    def _update_summary(self) -> None:
        """Install the current timeline as the playback source and refresh the summary display.

        For genuine source selections only.  Display-only changes (the Row 1 toggle) call
        _refresh_summary_display, which never touches the transport.
        """
        self._refresh_summary_display()
        self._sync_transport_with_current_timeline()

    def _refresh_summary_display(self) -> None:
        """Update the top metric banner labels for single-timeline views (display only, no transport)."""
        col_count = len(self.timeline.build_columns())
        row_count = self.timeline.row_count
        dur_s = self.timeline.total_duration_seconds
        dur_ms = self.timeline.total_duration_ms

        self.lbl_dataset.configure(text=f"Dataset: {self.current_dataset_name}")
        self.lbl_summary.configure(
            text=f"Rows: {row_count}  |  Columns: {col_count}  |  Duration: {dur_s:.2f}s ({dur_ms} ms)"
        )
        self._update_status_bar()

        if self.current_constant_row_mode == "development":
            c_row = calculate_development_constant_row(self.timeline)
            c_vals = [round(v, 1) for v in c_row.values]
            r1_lbl = "Row 1 (Dev Profile)"
        else:
            c_row = calculate_constant_row(self.timeline)
            c_vals = list(c_row.values)
            r1_lbl = "Row 1 (Constant)"

        self.lbl_constant_summary.configure(
            text=f"{r1_lbl}: {c_vals}"
        )

    def load_stage_1_proof(self) -> None:
        """Load and display the Stage 1 proof dataset."""
        self.current_dataset_name = "Stage 1 Mathematical Proof (Events A, B, C)"
        self.timeline = create_stage_1_proof_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._update_summary()

    def load_variable_width_proof(self) -> None:
        """Load and display the variable-width demonstration dataset."""
        self.current_dataset_name = "Variable-Width Proof (Non-uniform column durations)"
        self.timeline = create_variable_width_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._update_summary()

    def load_continuity_proof(self) -> None:
        """Load and display the multi-column continuity dataset."""
        self.current_dataset_name = "Sound Continuity Proof (Long event spanning subdivisions)"
        self.timeline = create_continuity_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._update_summary()

    def load_duck_arrangement_a(self) -> None:
        """Load and display Duck Flight Arrangement A."""
        song_a, _ = create_duck_flight_experiment()
        self.current_dataset_name = song_a.title
        self.timeline = song_a.timeline
        self.timeline_view.set_timeline(self.timeline)
        self._update_summary()

    def load_duck_arrangement_b(self) -> None:
        """Load and display Duck Flight Arrangement B."""
        _, song_b = create_duck_flight_experiment()
        self.current_dataset_name = song_b.title
        self.timeline = song_b.timeline
        self.timeline_view.set_timeline(self.timeline)
        self._update_summary()

    def _on_zoom_in(self) -> None:
        if self.current_view_mode in ("dual", "duck"):
            self.dual_view.zoom_in()
        else:
            self.timeline_view.zoom_in()

    def _on_zoom_out(self) -> None:
        if self.current_view_mode in ("dual", "duck"):
            self.dual_view.zoom_out()
        else:
            self.timeline_view.zoom_out()

    def _on_zoom_reset(self) -> None:
        if self.current_view_mode in ("dual", "duck"):
            self.dual_view.reset_zoom()
        else:
            self.timeline_view.reset_zoom()
