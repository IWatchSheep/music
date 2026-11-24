"""Scrollable Tkinter Canvas rendering the Music Timeline.

Visualizes:
1. Horizontal time axis with exact boundaries and variable-width column durations.
2. Row 1: The Calculated Constant Musical Row (Active Temporary Row Count) at the top.
3. Temporary sound rows (Row 2, Row 3, ...) placed sequentially below Row 1.
4. Vertical column boundary guidelines extending through all rows and Row 1.
5. Pinned left header badges that remain readable during horizontal scrolling.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from music_gui.coordinates import TimelineCoordinates
from music_gui.gui_style import (
    BG_CANVAS,
    BG_CONSTANT_CELL,
    BG_CONSTANT_LABEL,
    BG_CONSTANT_ROW,
    BG_HEADER,
    BG_ROW_EVEN,
    BG_ROW_LABEL,
    BG_ROW_ODD,
    BORDER_CONSTANT_CELL,
    BORDER_CONSTANT_LABEL,
    BORDER_DEFAULT,
    BORDER_HEADER,
    BORDER_ROW_LABEL,
    FG_CONSTANT_LABEL,
    FG_CONSTANT_VAL,
    FG_HEADER,
    FG_HEADER_SUB,
    FG_ROW_LABEL,
    FONT_CONSTANT_LABEL,
    FONT_CONSTANT_SUB,
    FONT_CONSTANT_VAL,
    FONT_EVENT_SUB,
    FONT_EVENT_TITLE,
    FONT_HEADER,
    FONT_HEADER_SUB,
    FONT_ROW_LABEL,
    FONT_ROW_SUB,
    GRID_LINE_COLOR,
    GRID_LINE_DASH,
    SOUND_COLORS,
)
from music_model.constant_row import calculate_constant_row
from music_model.timeline import MusicTimeline


def clean_tag(name: str) -> str:
    """Format a name safely for Tkinter canvas tags without space splitting."""
    return name.replace(" ", "_")


class TimelineCanvas(tk.Frame):
    """A scrollable canvas viewport that renders temporary rows and linked columns."""

    def __init__(
        self,
        parent: tk.Widget,
        timeline: MusicTimeline,
        constant_row_at_top: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=BG_CANVAS, **kwargs)

        self.coords: TimelineCoordinates = TimelineCoordinates(
            timeline, constant_row_at_top=constant_row_at_top
        )
        self._last_pinned_x: float = 0.0

        # Build scrollable canvas architecture (adapted from the calculator)
        self.canvas = tk.Canvas(
            self,
            bg=BG_CANVAS,
            highlightthickness=0,
            bd=0,
        )
        self.v_scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.h_scrollbar = ttk.Scrollbar(
            self, orient="horizontal", command=self._on_scrollbar_x
        )
        self.canvas.configure(
            xscrollcommand=self._on_canvas_xscroll,
            yscrollcommand=self.v_scrollbar.set,
        )

        # Grid placement
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bindings
        self.canvas.bind("<Configure>", self._on_configure)
        self._bind_mousewheel()

        # Initial render
        self.redraw()

    def set_timeline(self, timeline: MusicTimeline) -> None:
        """Update the displayed timeline and redraw."""
        self.coords.timeline = timeline
        self.redraw()

    def zoom_in(self) -> None:
        """Increase time scale magnification."""
        self.coords.zoom_in()
        self.redraw()

    def zoom_out(self) -> None:
        """Decrease time scale magnification."""
        self.coords.zoom_out()
        self.redraw()

    def reset_zoom(self) -> None:
        """Reset time scale magnification to default."""
        self.coords.reset_zoom()
        self.redraw()

    # Query Helpers for Testing and Verification
    def find_sound_bar(self, event_id: str) -> List[int]:
        """Find canvas item IDs for a sound event bar by event ID."""
        return list(self.canvas.find_withtag(f"sound_bar_{clean_tag(event_id)}"))

    def find_col_header(self, col_index: int) -> List[int]:
        """Find canvas item IDs for a column header box by column index."""
        return list(self.canvas.find_withtag(f"col_header_{col_index}"))

    def find_const_cell(self, col_index: int) -> List[int]:
        """Find canvas item IDs for a constant row cell box by column index."""
        return list(self.canvas.find_withtag(f"const_cell_{col_index}"))

    def find_const_val(self, col_index: int) -> List[int]:
        """Find canvas item IDs for constant row value text by column index."""
        return list(self.canvas.find_withtag(f"const_val_{col_index}"))

    def _on_scrollbar_x(self, *args) -> None:
        """Handle horizontal scrollbar interaction and keep left headers pinned."""
        self.canvas.xview(*args)
        self._update_pinned_headers()

    def _on_canvas_xscroll(self, first: str, last: str) -> None:
        """Callback from canvas when horizontal view position changes."""
        self.h_scrollbar.set(first, last)
        self._update_pinned_headers()

    def _update_pinned_headers(self) -> None:
        """Keep left row badges and header title pinned in view during horizontal scrolling."""
        curr_x = self.canvas.canvasx(0)
        dx = curr_x - self._last_pinned_x
        if dx != 0:
            self.canvas.move("pinned_left", dx, 0)
            self._last_pinned_x = curr_x

    def _bind_mousewheel(self) -> None:
        """Set up mouse wheel scrolling (vertical, horizontal with Shift, zoom with Ctrl)."""

        def on_mousewheel(event: tk.Event) -> None:
            # Check for Ctrl modifier -> Zoom
            if event.state & 0x0004:
                if event.delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return

            # Check for Shift modifier -> Horizontal scroll
            if event.state & 0x0001:
                self.canvas.xview_scroll(-1 * (event.delta // 120), "units")
                self._update_pinned_headers()
            else:
                self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

        self.canvas.bind("<MouseWheel>", on_mousewheel)

    def _on_configure(self, _event: Optional[tk.Event] = None) -> None:
        """Update scrollregion to encompass all content and the viewport."""
        w = max(self.canvas.winfo_width(), self.coords.total_width)
        h = max(self.canvas.winfo_height(), self.coords.total_height)
        self.canvas.configure(scrollregion=(0, 0, w, h))
        self._update_pinned_headers()

    def redraw(self) -> None:
        """Erase and redraw the complete timeline, sound rows, and constant row."""
        self.canvas.delete("all")
        self._last_pinned_x = 0.0

        timeline = self.coords.timeline
        columns = timeline.build_columns()
        boundaries = timeline.extract_boundaries()
        constant_row = calculate_constant_row(timeline)

        total_w = self.coords.total_width
        total_h = self.coords.total_height

        # Update scrollregion
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # Y bounds for Header and Row 1 (Constant Row)
        y_hdr_top, y_hdr_bot = self.coords.header_y_bounds()
        y_const_top, y_const_bot = self.coords.constant_row_y_bounds()
        rows = timeline.rows
        timeline_bottom_y = total_h - self.coords.padding_bottom

        # 1. Draw Top Header Background & Column Headers
        self.canvas.create_rectangle(
            0,
            y_hdr_top,
            total_w,
            y_hdr_bot,
            fill=BG_HEADER,
            outline=BORDER_HEADER,
            width=1,
            tags=("header_bg",),
        )

        for col in columns:
            x0, x1 = self.coords.column_x_bounds(col)

            # Column header box
            self.canvas.create_rectangle(
                x0,
                y_hdr_top,
                x1,
                y_hdr_bot,
                fill=BG_HEADER,
                outline=BORDER_HEADER,
                width=1,
                tags=(f"col_header_{col.index}", "col_header"),
            )
            # Column index & interval text
            self.canvas.create_text(
                (x0 + x1) / 2,
                y_hdr_top + 14,
                text=f"Col {col.index}",
                font=FONT_HEADER,
                fill=FG_HEADER,
                tags=("col_title",),
            )
            self.canvas.create_text(
                (x0 + x1) / 2,
                y_hdr_top + 30,
                text=f"[{col.start_time_ms}, {col.end_time_ms}) ms",
                font=FONT_HEADER_SUB,
                fill=FG_HEADER_SUB,
                tags=("col_interval",),
            )
            self.canvas.create_text(
                (x0 + x1) / 2,
                y_hdr_top + 44,
                text=f"Δ {col.duration_ms} ms ({col.duration_seconds:.2f}s)",
                font=FONT_HEADER_SUB,
                fill="#0f766e",  # Teal duration note
                tags=("col_duration",),
            )

        # 2. Draw Row 1: Calculated Constant Musical Row (At Top Beneath Header)
        # Constant row background lane
        self.canvas.create_rectangle(
            0,
            y_const_top,
            total_w,
            y_const_bot,
            fill=BG_CONSTANT_ROW,
            outline=BORDER_CONSTANT_LABEL,
            width=1,
            tags=("constant_row_bg",),
        )

        # Constant Row Values per Column
        for col in columns:
            cx0, cx1 = self.coords.column_x_bounds(col)
            val = constant_row[col.index]

            cell_pad_x = 4
            cell_pad_y = 6
            cell_x0 = cx0 + cell_pad_x
            cell_x1 = cx1 - cell_pad_x
            cell_y0 = y_const_top + cell_pad_y
            cell_y1 = y_const_bot - cell_pad_y

            # Result card matching the column
            self.canvas.create_rectangle(
                cell_x0,
                cell_y0,
                cell_x1,
                cell_y1,
                fill=BG_CONSTANT_CELL,
                outline=BORDER_CONSTANT_CELL,
                width=1,
                tags=(f"const_cell_{col.index}", "const_cell"),
            )
            cell_center_x = (cell_x0 + cell_x1) / 2
            self.canvas.create_text(
                cell_center_x,
                cell_y0 + 17,
                text=str(val),
                font=FONT_CONSTANT_VAL,
                fill=FG_CONSTANT_VAL,
                tags=(f"const_val_{col.index}", "const_val"),
            )
            active_note = f"{val} active row" + ("s" if val != 1 else "")
            self.canvas.create_text(
                cell_center_x,
                cell_y0 + 34,
                text=active_note,
                font=FONT_CONSTANT_SUB,
                fill="#78350f",
                tags=("const_sub",),
            )

        # Separator line beneath Row 1
        self.canvas.create_line(
            0,
            y_const_bot + 6,
            total_w,
            y_const_bot + 6,
            fill="#d97706",
            width=2,
            tags=("const_separator",),
        )

        # 3. Draw Temporary Sound Rows (Row 2, Row 3, ...) Sequentially Below Row 1
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            row_bg = BG_ROW_EVEN if row_idx % 2 == 0 else BG_ROW_ODD

            # Row background lane
            self.canvas.create_rectangle(
                0,
                y_r_top,
                total_w,
                y_r_bot,
                fill=row_bg,
                outline=BORDER_DEFAULT,
                width=1,
                tags=(f"row_lane_{clean_tag(row.row_id)}", "row_lane"),
            )

            # Sound Events in this row (continuous colored bars)
            for event_idx, event in enumerate(row.events):
                ex0, ex1 = self.coords.event_x_bounds(event)
                ey0 = y_r_top + 10
                ey1 = y_r_bot - 10

                color_tuple = SOUND_COLORS[(row_idx * 3 + event_idx) % len(SOUND_COLORS)]
                fill_color, border_color, text_color = color_tuple

                self.canvas.create_rectangle(
                    ex0,
                    ey0,
                    ex1,
                    ey1,
                    fill=fill_color,
                    outline=border_color,
                    width=2,
                    tags=(f"sound_bar_{clean_tag(event.event_id)}", "sound_bar"),
                )

                bar_center_x = (ex0 + ex1) / 2
                display_label = event.label if event.label else event.event_id
                self.canvas.create_text(
                    bar_center_x,
                    ey0 + 13,
                    text=f"{event.event_id}: {display_label}",
                    font=FONT_EVENT_TITLE,
                    fill=text_color,
                    tags=(f"sound_title_{clean_tag(event.event_id)}", "sound_title"),
                )
                self.canvas.create_text(
                    bar_center_x,
                    ey0 + 29,
                    text=f"[{event.start_time_ms}, {event.end_time_ms}) ms  ({event.duration_ms} ms)",
                    font=FONT_EVENT_SUB,
                    fill=text_color,
                    tags=(f"sound_sub_{clean_tag(event.event_id)}", "sound_sub"),
                )

        # 4. Vertical Column Boundary Guidelines (Across header, Row 1, and all temporary rows)
        for b_time in boundaries:
            bx = self.coords.time_to_x(b_time)
            self.canvas.create_line(
                bx,
                y_hdr_top,
                bx,
                timeline_bottom_y,
                fill=GRID_LINE_COLOR,
                dash=GRID_LINE_DASH,
                width=1,
                tags=("grid_line",),
            )

        # 5. Pinned Left Header & Badges (Stay visible during horizontal scrolling)
        # Solid background covering left sidebar to prevent scrolling timeline from showing through
        self.canvas.create_rectangle(
            0,
            y_hdr_top,
            self.coords.left_header_width,
            timeline_bottom_y,
            fill="#f1f5f9",
            outline="#cbd5e1",
            width=1,
            tags=("pinned_left", "pinned_sidebar_bg"),
        )
        self.canvas.create_line(
            self.coords.left_header_width,
            y_hdr_top,
            self.coords.left_header_width,
            timeline_bottom_y,
            fill="#94a3b8",
            width=2,
            tags=("pinned_left", "pinned_sidebar_border"),
        )

        # Pinned Header Badge
        self.canvas.create_rectangle(
            8,
            y_hdr_top + 4,
            self.coords.left_header_width - 12,
            y_hdr_bot - 4,
            fill=BG_HEADER,
            outline=BORDER_HEADER,
            width=1,
            tags=("pinned_left", "header_label_box"),
        )
        self.canvas.create_text(
            16,
            (y_hdr_top + y_hdr_bot) / 2 - 8,
            text="Linked Columns",
            font=FONT_HEADER,
            fill=FG_HEADER,
            anchor="w",
            tags=("pinned_left", "header_label"),
        )
        self.canvas.create_text(
            16,
            (y_hdr_top + y_hdr_bot) / 2 + 10,
            text="Time Axis (ms) →",
            font=FONT_HEADER_SUB,
            fill=FG_HEADER_SUB,
            anchor="w",
            tags=("pinned_left", "header_sublabel"),
        )

        # Pinned Row 1 Badge (Constant Musical Row)
        badge_y0 = y_const_top + 6
        badge_y1 = y_const_bot - 6
        self.canvas.create_rectangle(
            8,
            badge_y0,
            self.coords.left_header_width - 12,
            badge_y1,
            fill=BG_CONSTANT_LABEL,
            outline=BORDER_CONSTANT_LABEL,
            width=1,
            tags=("pinned_left", "constant_badge"),
        )
        self.canvas.create_text(
            (8 + self.coords.left_header_width - 12) / 2,
            badge_y0 + 14,
            text="Row 1: Constant",
            font=FONT_CONSTANT_LABEL,
            fill=FG_CONSTANT_LABEL,
            tags=("pinned_left", "const_label"),
        )
        self.canvas.create_text(
            (8 + self.coords.left_header_width - 12) / 2,
            badge_y0 + 32,
            text="(Active Row Count)",
            font=FONT_CONSTANT_SUB,
            fill=FG_CONSTANT_LABEL,
            tags=("pinned_left", "const_sublabel"),
        )

        # Pinned Badges for Temporary Rows (Row 2, Row 3, ...)
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            badge_y0 = y_r_top + 8
            badge_y1 = y_r_bot - 8

            self.canvas.create_rectangle(
                8,
                badge_y0,
                self.coords.left_header_width - 12,
                badge_y1,
                fill=BG_ROW_LABEL,
                outline=BORDER_ROW_LABEL,
                width=1,
                tags=("pinned_left", f"row_badge_{clean_tag(row.row_id)}", "row_badge"),
            )

            # Display "Row 2", "Row 3", etc. based on index or row_id
            if row.row_id.lower().startswith("row "):
                display_row_name = row.row_id
            else:
                display_row_name = f"Row {row_idx + 2}: {row.row_id}"

            self.canvas.create_text(
                (8 + self.coords.left_header_width - 12) / 2,
                badge_y0 + 14,
                text=display_row_name,
                font=FONT_ROW_LABEL,
                fill=FG_ROW_LABEL,
                tags=("pinned_left", "row_label_text"),
            )
            sub_label = row.label if row.label else f"{len(row)} sound(s)"
            self.canvas.create_text(
                (8 + self.coords.left_header_width - 12) / 2,
                badge_y0 + 32,
                text=sub_label,
                font=FONT_ROW_SUB,
                fill=FG_ROW_LABEL,
                tags=("pinned_left", "row_sublabel_text"),
            )

        # Raise all pinned items to ensure they float above scrolling sound bars
        self.canvas.tag_raise("pinned_left")
        self._update_pinned_headers()
