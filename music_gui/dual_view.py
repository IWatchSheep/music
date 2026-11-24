"""Dual song independent timeline view.

Displays two independent songs stacked vertically, each having:
- Its own column count and variable-width column durations.
- Its own Row 1 calculated constant musical row at the top.
- Its own temporary sound rows (Row 2, Row 3, ...).
- Its own independent horizontal scrollbar.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from music_gui.gui_style import BG_CANVAS, BG_TOOLBAR, BG_WINDOW, FONT_TITLE
from music_gui.timeline_canvas import TimelineCanvas
from music_model.song import SongTimeline


class DualSongView(tk.Frame):
    """Container widget displaying two independent SongTimeline instances."""

    def __init__(
        self,
        parent: tk.Widget,
        song1: SongTimeline,
        song2: SongTimeline,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=BG_WINDOW, **kwargs)

        self.song1: SongTimeline = song1
        self.song2: SongTimeline = song2

        # Grid: Upper pane for Song 1, lower pane for Song 2
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Build Upper Pane (Song 1)
        self.pane1 = tk.Frame(self, bg=BG_WINDOW, highlightbackground="#94a3b8", highlightthickness=1)
        self.pane1.grid(row=0, column=0, sticky="nsew", padx=4, pady=(2, 4))
        self.pane1.grid_rowconfigure(1, weight=1)
        self.pane1.grid_columnconfigure(0, weight=1)

        self.lbl_s1_title = tk.Label(
            self.pane1,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#e0f2fe",
            fg="#0369a1",
            anchor="w",
            padx=8,
            pady=3,
        )
        self.lbl_s1_title.grid(row=0, column=0, sticky="ew")

        self.canvas1 = TimelineCanvas(self.pane1, song1.timeline, constant_row_at_top=True)
        self.canvas1.grid(row=1, column=0, sticky="nsew")

        # Build Lower Pane (Song 2)
        self.pane2 = tk.Frame(self, bg=BG_WINDOW, highlightbackground="#94a3b8", highlightthickness=1)
        self.pane2.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 4))
        self.pane2.grid_rowconfigure(1, weight=1)
        self.pane2.grid_columnconfigure(0, weight=1)

        self.lbl_s2_title = tk.Label(
            self.pane2,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#fef3c7",
            fg="#92400e",
            anchor="w",
            padx=8,
            pady=3,
        )
        self.lbl_s2_title.grid(row=0, column=0, sticky="ew")

        self.canvas2 = TimelineCanvas(self.pane2, song2.timeline, constant_row_at_top=True)
        self.canvas2.grid(row=1, column=0, sticky="nsew")

        self._refresh_titles()

    def _refresh_titles(self) -> None:
        """Update pane header labels with song metadata and column statistics."""
        cols1 = self.song1.column_count
        dur1 = self.song1.total_duration_ms
        const1 = list(self.song1.constant_row.values)
        self.lbl_s1_title.configure(
            text=f"🎵 Song 1: {self.song1.title}  |  Columns: {cols1}  |  Duration: {dur1} ms  |  Row 1 (Constant): {const1}"
        )

        cols2 = self.song2.column_count
        dur2 = self.song2.total_duration_ms
        const2 = list(self.song2.constant_row.values)
        self.lbl_s2_title.configure(
            text=f"🎶 Song 2: {self.song2.title}  |  Columns: {cols2}  |  Duration: {dur2} ms  |  Row 1 (Constant): {const2}"
        )

    def set_songs(self, song1: SongTimeline, song2: SongTimeline) -> None:
        """Update both displayed songs and redraw."""
        self.song1 = song1
        self.song2 = song2
        self.canvas1.set_timeline(song1.timeline)
        self.canvas2.set_timeline(song2.timeline)
        self._refresh_titles()

    def zoom_in(self) -> None:
        self.canvas1.zoom_in()
        self.canvas2.zoom_in()

    def zoom_out(self) -> None:
        self.canvas1.zoom_out()
        self.canvas2.zoom_out()

    def reset_zoom(self) -> None:
        self.canvas1.reset_zoom()
        self.canvas2.reset_zoom()
