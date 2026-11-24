"""Main application window for the Music Project Stage 2 GUI.

Houses:
- Top control toolbar with dataset switcher and zoom controls.
- Summary metrics bar reporting column count, duration, rows, and constant row values.
- Scrollable TimelineCanvas displaying temporary rows, continuous sound bars,
  and the derived constant row.
- Bottom status bar.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

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
    create_continuity_timeline,
    create_stage_1_proof_timeline,
    create_variable_width_timeline,
)
from music_model.timeline import MusicTimeline


class MusicGUI(tk.Tk):
    """Main window for the Music Project Stage 2 Timeline GUI."""

    def __init__(self, timeline: Optional[MusicTimeline] = None) -> None:
        super().__init__()
        self.title("Music Project — Temporary Sound Rows & Linked Time Columns (Stage 2)")
        self.geometry("1180x620")
        self.minsize(800, 450)
        self.configure(bg=BG_WINDOW)

        self.current_dataset_name: str = "Stage 1 Mathematical Proof (Events A, B, C)"
        self.timeline: MusicTimeline = (
            timeline if timeline is not None else create_stage_1_proof_timeline()
        )

        self._build_toolbar()
        self._build_summary_bar()
        self._build_canvas_area()
        self._build_status_bar()

        self._update_summary()

    def _build_toolbar(self) -> None:
        """Create the top navigation and action toolbar."""
        toolbar = tk.Frame(self, bg=BG_TOOLBAR, bd=0, relief="flat")
        toolbar.pack(fill="x", side="top", padx=8, pady=(8, 2))

        # Title
        title_lbl = tk.Label(
            toolbar,
            text="🎵 Music Timeline Explorer",
            font=FONT_TITLE,
            bg=BG_TOOLBAR,
            fg="#0f172a",
        )
        title_lbl.pack(side="left", padx=(8, 16), pady=6)

        # Dataset Switcher Buttons
        sep1 = ttk.Separator(toolbar, orient="vertical")
        sep1.pack(side="left", fill="y", padx=8, pady=4)

        tk.Label(
            toolbar,
            text="Datasets:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        self.btn_proof = tk.Button(
            toolbar,
            text="Stage 1 Proof (A/B/C)",
            font=FONT_TOOLBAR,
            bg="#e0f2fe",
            fg="#0369a1",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.load_stage_1_proof,
        )
        self.btn_proof.pack(side="left", padx=3)

        self.btn_var_width = tk.Button(
            toolbar,
            text="Variable-Width Proof",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.load_variable_width_proof,
        )
        self.btn_var_width.pack(side="left", padx=3)

        self.btn_continuity = tk.Button(
            toolbar,
            text="Sound Continuity Proof",
            font=FONT_TOOLBAR,
            bg="#f1f5f9",
            fg="#334155",
            relief="raised",
            bd=1,
            padx=8,
            pady=2,
            command=self.load_continuity_proof,
        )
        self.btn_continuity.pack(side="left", padx=3)

        # Zoom Controls (Right side)
        sep2 = ttk.Separator(toolbar, orient="vertical")
        sep2.pack(side="left", fill="y", padx=12, pady=4)

        tk.Label(
            toolbar,
            text="Zoom:",
            font=FONT_TOOLBAR_BOLD,
            bg=BG_TOOLBAR,
            fg="#475569",
        ).pack(side="left", padx=(4, 6))

        btn_zoom_in = tk.Button(
            toolbar,
            text="Zoom In (+)",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_in,
        )
        btn_zoom_in.pack(side="left", padx=2)

        btn_zoom_out = tk.Button(
            toolbar,
            text="Zoom Out (−)",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_out,
        )
        btn_zoom_out.pack(side="left", padx=2)

        btn_zoom_reset = tk.Button(
            toolbar,
            text="Reset",
            font=FONT_TOOLBAR,
            bg="#f8fafc",
            fg="#1e293b",
            relief="raised",
            bd=1,
            padx=6,
            pady=2,
            command=self._on_zoom_reset,
        )
        btn_zoom_reset.pack(side="left", padx=2)

    def _build_summary_bar(self) -> None:
        """Create the summary metric banner above the timeline canvas."""
        f = tk.Frame(self, bg="#ffffff", highlightbackground=BORDER_DEFAULT, highlightthickness=1)
        f.pack(fill="x", padx=8, pady=(2, 6))

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

    def _build_canvas_area(self) -> None:
        """Embed the TimelineCanvas viewport inside a styled outer frame."""
        holder = tk.Frame(
            self,
            bg=BG_WINDOW,
            highlightbackground="#94a3b8",
            highlightthickness=1,
        )
        holder.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self.timeline_view = TimelineCanvas(holder, self.timeline)
        self.timeline_view.pack(fill="both", expand=True)

    def _build_status_bar(self) -> None:
        """Create the bottom status bar."""
        status_frame = tk.Frame(self, bg=BG_TOOLBAR)
        status_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 4))

        tk.Label(
            status_frame,
            text="Stage 2 Read-Only GUI | Sounds dictate variable-width columns | Constant row: Active Temporary Row Count | Scroll: Wheel / Shift+Wheel / Ctrl+Wheel",
            font=FONT_STATUS,
            bg=BG_TOOLBAR,
            fg="#64748b",
        ).pack(side="left", padx=8, pady=2)

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
            text=f"Constant Row: {list(constant_row.values)}"
        )

    def _set_active_dataset_button(self, active_btn: tk.Button) -> None:
        """Update button styles to highlight the active dataset."""
        for b in (self.btn_proof, self.btn_var_width, self.btn_continuity):
            if b is active_btn:
                b.configure(bg="#e0f2fe", fg="#0369a1", relief="sunken")
            else:
                b.configure(bg="#f1f5f9", fg="#334155", relief="raised")

    def load_stage_1_proof(self) -> None:
        """Load and display the Stage 1 proof dataset."""
        self.current_dataset_name = "Stage 1 Mathematical Proof (Events A, B, C)"
        self.timeline = create_stage_1_proof_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._set_active_dataset_button(self.btn_proof)
        self._update_summary()

    def load_variable_width_proof(self) -> None:
        """Load and display the variable-width demonstration dataset."""
        self.current_dataset_name = "Variable-Width Proof (Non-uniform column durations)"
        self.timeline = create_variable_width_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._set_active_dataset_button(self.btn_var_width)
        self._update_summary()

    def load_continuity_proof(self) -> None:
        """Load and display the multi-column continuity dataset."""
        self.current_dataset_name = "Sound Continuity Proof (Long event spanning subdivisions)"
        self.timeline = create_continuity_timeline()
        self.timeline_view.set_timeline(self.timeline)
        self._set_active_dataset_button(self.btn_continuity)
        self._update_summary()

    def _on_zoom_in(self) -> None:
        self.timeline_view.zoom_in()

    def _on_zoom_out(self) -> None:
        self.timeline_view.zoom_out()

    def _on_zoom_reset(self) -> None:
        self.timeline_view.reset_zoom()
