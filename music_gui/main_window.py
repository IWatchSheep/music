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

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

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

        # Build UI layout
        self._build_toolbar()
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
        """Update top-tier mode button styles."""
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

        toggle_txt = "Active Rows" if self.current_constant_row_mode == "active_rows" else "Pitch Dev Profile"
        tk.Button(
            self.subcontrols_frame,
            text=f"Row 1: {toggle_txt}",
            font=FONT_TOOLBAR_BOLD,
            bg="#fef3c7",
            fg="#92400e",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._toggle_constant_row_mode,
        ).pack(side="left", padx=(8, 2))

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

        if self.current_view_mode in ("duck", "dual"):
            self._refresh_dual_constant_summary()
        elif self.current_view_mode == "midi":
            self.show_midi_mode(self.current_song)
        else:
            self._update_summary()

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

    # --- Helper & Utility Methods ---

    def _update_summary(self) -> None:
        """Update the top metric banner labels for single-timeline views."""
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
