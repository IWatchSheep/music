"""Main application window for the Music Project Stage 2B GUI.

Houses:
- Non-clipping, responsive two-tier navigation and action toolbar.
- View Mode Switcher:
  1. Progressive Refitting Mode: Selectable Stage A (1 col), Stage B (3 cols), Stage C (5 cols).
  2. Dual Independent Songs View: Song 1 vs Song 2 with independent columns and scrolling.
  3. Single Timeline View: Inspect any individual timeline or synthetic proof.
  4. 32-Column Stress Test: Validating wide many-column layouts.
  5. Duck Flight Experiment (Stage 2B Phase 3): Low-to-high musical development (Arrangement A vs B).
- Row 1 (Constant Musical Row) prominently displayed at the top beneath the time header:
  - Active Temporary Row Count (Diagnostic Baseline).
  - Low-to-High Development Profile (Experimental Continuous Measurement).
- Temporary sound rows (Row 2, Row 3, ...) placed below Row 1.
- Pinned left sidebar badges remaining visible during horizontal scrolling.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
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
from music_model.song import SongTimeline
from music_model.timeline import MusicTimeline


class MusicGUI(tk.Tk):
    """Main window for the Music Project Timeline GUI."""

    def __init__(self, timeline: Optional[MusicTimeline] = None) -> None:
        super().__init__()
        self.title("Music Project — Progressive Refitting & Independent Song Timelines")
        self.geometry("1180x680")
        self.minsize(800, 480)
        self.configure(bg=BG_WINDOW)

        # Current view states
        self.current_view_mode: str = "progressive"  # 'progressive', 'single', 'dual', 'stress', 'duck'
        self.current_stage: str = "A"               # 'A', 'B', 'C'
        self.current_constant_row_mode: str = "active_rows"  # 'active_rows' or 'development'
        self.current_dataset_name: str = "Progressive Refitting — Stage A (Row 2 alone)"

        # Active timelines
        self.timeline: MusicTimeline = (
            timeline if timeline is not None else create_progressive_stage_timeline("A").timeline
        )
        self.song1, self.song2 = create_dual_independent_songs()

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
            fg="#b45309",
        )
        self.lbl_constant_summary.pack(side="right", padx=16, pady=4)

    def _build_content_area(self) -> None:
        """Embed the main viewport container."""
        self.content_holder = tk.Frame(
            self,
            bg=BG_WINDOW,
            highlightbackground="#94a3b8",
            highlightthickness=1,
        )
        self.content_holder.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Single canvas view
        self.timeline_view = TimelineCanvas(
            self.content_holder,
            self.timeline,
            constant_row_at_top=True,
            constant_row_mode=self.current_constant_row_mode,
        )

        # Dual canvas view
        self.dual_view = DualSongView(
            self.content_holder,
            self.song1,
            self.song2,
            constant_row_mode=self.current_constant_row_mode,
        )

    def _build_status_bar(self) -> None:
        """Create the bottom status bar."""
        status_frame = tk.Frame(self, bg=BG_TOOLBAR)
        status_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 4))

        self.lbl_status = tk.Label(
            status_frame,
            text="Row 1: Constant Musical Row (At Top) | Sounds dictate variable-width columns | Scroll: Wheel / Shift+Wheel / Ctrl+Wheel",
            font=FONT_STATUS,
            bg=BG_TOOLBAR,
            fg="#64748b",
        )
        self.lbl_status.pack(side="left", padx=8, pady=2)

    def _clear_subcontrols(self) -> None:
        """Clear dynamic Tier 2 subcontrols."""
        for widget in self.subcontrols_frame.winfo_children():
            widget.destroy()

    def _set_active_mode_button(self, active_btn: tk.Button) -> None:
        """Update top-tier mode button styles."""
        all_buttons = (
            self.btn_mode_progressive,
            self.btn_mode_duck,
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

    def _show_solo_duck(self, song: SongTimeline) -> None:
        """Display a single arrangement in the full single-canvas view."""
        self.timeline = song.timeline
        self.timeline_view.set_constant_row_mode(self.current_constant_row_mode)
        self.timeline_view.set_timeline(self.timeline)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self.current_dataset_name = song.title
        self._update_summary()

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

    # --- Mode 3: Dual Independent Songs View ---

    def show_dual_mode(self) -> None:
        """Display two independent songs with separate timelines and scrollbars."""
        self.current_view_mode = "dual"
        self._set_active_mode_button(self.btn_mode_dual)

        self.song1, self.song2 = create_dual_independent_songs()
        self.dual_view.set_songs(self.song1, self.song2)
        self.dual_view.set_constant_row_mode(self.current_constant_row_mode)

        # Show dual view, hide single view
        self.timeline_view.pack_forget()
        self.dual_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Independent Songs: Both songs calculate their own columns independently (No shared grid).",
            font=FONT_TOOLBAR,
            bg=BG_TOOLBAR,
            fg="#1e293b",
        ).pack(side="left", padx=(4, 6))

        self.current_dataset_name = "Dual Independent Songs View (Song 1 vs Song 2)"
        cols1 = self.song1.column_count
        cols2 = self.song2.column_count
        self.lbl_dataset.configure(text=f"Mode: {self.current_dataset_name}")
        self.lbl_summary.configure(
            text=f"Song 1: {cols1} columns, {self.song1.total_duration_ms} ms  |  Song 2: {cols2} columns, {self.song2.total_duration_ms} ms"
        )
        self._refresh_dual_constant_summary()

    # --- Mode 4: Single Timeline View ---

    def show_single_mode(self) -> None:
        """Display single timeline with dataset picker."""
        self.current_view_mode = "single"
        self._set_active_mode_button(self.btn_mode_single)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Select Dataset:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        tk.Button(
            self.subcontrols_frame,
            text="Stage 1 Proof (A/B/C)",
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
            text="Variable-Width Proof",
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
            text="Continuity Proof",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_continuity_proof,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Duck Flight: Arr. A",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_duck_arrangement_a,
        ).pack(side="left", padx=2)

        tk.Button(
            self.subcontrols_frame,
            text="Duck Flight: Arr. B",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self.load_duck_arrangement_b,
        ).pack(side="left", padx=2)

        self.load_stage_1_proof()

    # --- Mode 5: 32-Column Stress Test ---

    def show_stress_mode(self) -> None:
        """Display the 32-column layout stress test."""
        self.current_view_mode = "stress"
        self._set_active_mode_button(self.btn_mode_stress)

        self.dual_view.pack_forget()
        self.timeline_view.pack(fill="both", expand=True)

        self._clear_subcontrols()
        tk.Label(
            self.subcontrols_frame,
            text="Display Stress Test: 32 derived variable-width columns spanning beyond window width.",
            font=FONT_TOOLBAR,
            bg=BG_TOOLBAR,
            fg="#0f766e",
        ).pack(side="left", padx=(4, 6))

        song = create_32_column_timeline()
        self.timeline = song.timeline
        self.timeline_view.set_timeline(self.timeline)

        self.current_dataset_name = "32-Column Layout Stress Test"
        self._update_summary()

    def _update_summary(self) -> None:
        """Refresh summary metrics text from the active timeline."""
        columns = self.timeline.build_columns()

        if self.current_constant_row_mode == "development":
            constant_row = calculate_development_constant_row(self.timeline)
            c_vals = [round(v, 1) for v in constant_row.values]
            r1_lbl = "Row 1 (Dev Profile)"
        else:
            constant_row = calculate_constant_row(self.timeline)
            c_vals = list(constant_row.values)
            r1_lbl = "Row 1 (Constant)"

        self.lbl_dataset.configure(text=f"Dataset: {self.current_dataset_name}")
        self.lbl_summary.configure(
            text=(
                f"Columns: {len(columns)}  |  "
                f"Total Duration: {self.timeline.total_duration_ms} ms ({self.timeline.total_duration_seconds:.2f}s)  |  "
                f"Temporary Rows: {self.timeline.row_count}  |  "
                f"Sound Events: {self.timeline.event_count}"
            )
        )
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
