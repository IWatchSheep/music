"""Main application window for the Music Project Stage 2B GUI.

Houses:
- Non-clipping, responsive two-tier navigation and action toolbar.
- View Mode Switcher:
  1. Progressive Refitting Mode: Selectable Stage A (1 col), Stage B (3 cols), Stage C (5 cols).
  2. Dual Independent Songs View: Song 1 vs Song 2 with independent columns and scrolling.
  3. Single Timeline View: Inspect any individual timeline or synthetic proof.
  4. 32-Column Stress Test: Validating wide many-column layouts.
- Row 1 (Constant Musical Row) prominently displayed at the top beneath the time header.
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
    create_progressive_stage_timeline,
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
)
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
        self.current_view_mode: str = "progressive"  # 'progressive', 'single', 'dual', 'stress'
        self.current_stage: str = "A"               # 'A', 'B', 'C'
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
        self.timeline_view = TimelineCanvas(self.content_holder, self.timeline, constant_row_at_top=True)

        # Dual canvas view
        self.dual_view = DualSongView(self.content_holder, self.song1, self.song2)

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
        for b in (self.btn_mode_progressive, self.btn_mode_dual, self.btn_mode_single, self.btn_mode_stress):
            if b is active_btn:
                b.configure(bg="#e0f2fe", fg="#0369a1", relief="sunken")
            else:
                b.configure(bg="#f1f5f9", fg="#334155", relief="raised")

    # --- Mode 1: Progressive Refitting ---

    def show_progressive_mode(self, stage: str = "A") -> None:
        """Display the progressive column refitting demonstration."""
        self.current_view_mode = "progressive"
        self.current_stage = stage.upper()
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

    # --- Mode 2: Dual Independent Songs View ---

    def show_dual_mode(self) -> None:
        """Display two independent songs with separate timelines and scrollbars."""
        self.current_view_mode = "dual"
        self._set_active_mode_button(self.btn_mode_dual)

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
        self.lbl_constant_summary.configure(
            text=f"Row 1 (S1): {list(self.song1.constant_row.values)}  |  Row 1 (S2): {list(self.song2.constant_row.values)}"
        )

    # --- Mode 3: Single Timeline View ---

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

        self.load_stage_1_proof()

    # --- Mode 4: 32-Column Stress Test ---

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
        constant_row = calculate_constant_row(self.timeline)

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
            text=f"Row 1 (Constant): {list(constant_row.values)}"
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

    def _on_zoom_in(self) -> None:
        if self.current_view_mode == "dual":
            self.dual_view.zoom_in()
        else:
            self.timeline_view.zoom_in()

    def _on_zoom_out(self) -> None:
        if self.current_view_mode == "dual":
            self.dual_view.zoom_out()
        else:
            self.timeline_view.zoom_out()

    def _on_zoom_reset(self) -> None:
        if self.current_view_mode == "dual":
            self.dual_view.reset_zoom()
        else:
            self.timeline_view.reset_zoom()
