"""Interactive Tkinter timeline viewport widget.

Displays:
1. Linked time columns with duration and millisecond boundaries.
2. Row 1: The Calculated Constant Musical Row (Active Temporary Row Count or Low-to-High Profile).
3. Temporary sound rows (Row 2, Row 3, ...) placed sequentially below Row 1.
4. Continuous colored sound bars spanning across multi-column intervals.
5. Vertical boundary guidelines indicating how temporary rows dictate time columns.
6. Pinned left sidebar badges remaining visible during horizontal scrolling.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from music_gui.coordinates import TimelineCoordinates
from music_gui.gui_style import (
    BG_CANVAS,
    BG_CONSTANT_CELL,
    BG_CONSTANT_LABEL,
    BG_CONSTANT_ROW,
    BG_HEADER,
    BG_ROW_EVEN,
    BG_ROW_ODD,
    BORDER_CONSTANT_CELL,
    BORDER_CONSTANT_LABEL,
    BORDER_DEFAULT,
    BORDER_HEADER,
    FG_CONSTANT_LABEL,
    FG_CONSTANT_VAL,
    FG_HEADER,
    FG_HEADER_SUB,
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
from music_model.development_profile import calculate_development_constant_row
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
        constant_row_mode: str = "active_rows",  # 'active_rows' or 'development'
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=BG_CANVAS, **kwargs)

        self.coords: TimelineCoordinates = TimelineCoordinates(
            timeline, constant_row_at_top=constant_row_at_top
        )
        self.constant_row_mode: str = constant_row_mode
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

    def set_constant_row_mode(self, mode: str) -> None:
        """Set measurement mode for Row 1 ('active_rows' or 'development')."""
        self.constant_row_mode = mode.lower().strip()
        self.redraw()

    def zoom_in(self) -> None:
        """Magnify horizontal timeline resolution."""
        self.coords.zoom_in()
        self.redraw()

    def zoom_out(self) -> None:
        """Demagnify horizontal timeline resolution."""
        self.coords.zoom_out()
        self.redraw()

    def reset_zoom(self) -> None:
        """Reset horizontal zoom to default resolution."""
        self.coords.reset_zoom()
        self.redraw()

    # --- Element Query Helpers for Automated GUI Smoke Tests ---

    def find_sound_bar(self, event_id: str) -> List[int]:
        """Find canvas item ID(s) for a sound event bar."""
        return list(self.canvas.find_withtag(f"sound_bar_{clean_tag(event_id)}"))

    def find_col_header(self, col_index: int) -> List[int]:
        """Find canvas item ID(s) for a column header box."""
        return list(self.canvas.find_withtag(f"col_header_{col_index}"))

    def find_const_cell(self, col_index: int) -> List[int]:
        """Find canvas item ID(s) for a constant row cell."""
        return list(self.canvas.find_withtag(f"const_cell_{col_index}"))

    def find_const_val(self, col_index: int) -> List[int]:
        """Find canvas text item ID(s) for a constant row value."""
        return list(self.canvas.find_withtag(f"const_val_{col_index}"))

    # --- Pinned Left Sidebar Scroll Synchronization ---

    def _on_scrollbar_x(self, *args) -> None:
        """Intercept horizontal scrollbar movement to keep left badges pinned."""
        self.canvas.xview(*args)
        self._update_pinned_headers()

    def _on_canvas_xscroll(self, first: str, last: str) -> None:
        """Update horizontal scrollbar thumb and adjust pinned sidebar position."""
        self.h_scrollbar.set(first, last)
        self._update_pinned_headers()

    def _update_pinned_headers(self) -> None:
        """Reposition left sidebar items so they stay stationary during horizontal scrolling."""
        target_x = self.canvas.canvasx(0)
        dx = target_x - self._last_pinned_x
        if abs(dx) > 0.001:
            self.canvas.move("pinned_left", dx, 0)
            self._last_pinned_x = target_x
        self.canvas.tag_raise("pinned_left")

    def _bind_mousewheel(self) -> None:
        """Cross-platform mouse wheel scrolling."""
        def on_mousewheel(event: tk.Event) -> None:
            # Shift+Scroll = Horizontal scroll
            # Ctrl+Scroll = Zoom
            # Normal Scroll = Vertical scroll
            state = getattr(event, "state", 0)
            shift_pressed = bool(state & 0x0001)
            ctrl_pressed = bool(state & 0x0004)

            delta = -1 if event.delta < 0 else 1

            if ctrl_pressed:
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
            elif shift_pressed:
                self.canvas.xview_scroll(-1 * delta, "units")
                self._update_pinned_headers()
            else:
                self.canvas.yview_scroll(-1 * delta, "units")

        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", on_mousewheel)

    def _on_configure(self, _event: Optional[tk.Event] = None) -> None:
        """Re-check pinned header positioning on window resize."""
        self._update_pinned_headers()

    def redraw(self) -> None:
        """Erase and redraw the complete timeline, sound rows, and constant row."""
        self.canvas.delete("all")
        self._last_pinned_x = 0.0

        timeline = self.coords.timeline
        columns = timeline.build_columns()
        boundaries = timeline.extract_boundaries()

        if self.constant_row_mode == "development":
            constant_row = calculate_development_constant_row(timeline)
        else:
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

            if self.constant_row_mode == "development":
                val_text = f"{val:.1f}" if isinstance(val, float) else str(val)
                active_note = f"height: {val_text}"
            else:
                val_text = str(val)
                active_note = f"{val} active row" + ("s" if val != 1 else "")

            self.canvas.create_text(
                cell_center_x,
                cell_y0 + 17,
                text=val_text,
                font=FONT_CONSTANT_VAL,
                fill=FG_CONSTANT_VAL,
                tags=(f"const_val_{col.index}", "const_val"),
            )
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
                ey0 = y_r_top + 8
                ey1 = y_r_bot - 8

                color_idx = (row_idx * 3 + event_idx) % len(SOUND_COLORS)
                bar_fill, bar_border, text_color = SOUND_COLORS[color_idx]

                # Draw continuous colored bar
                self.canvas.create_rectangle(
                    ex0,
                    ey0,
                    ex1,
                    ey1,
                    fill=bar_fill,
                    outline=bar_border,
                    width=2,
                    tags=(f"sound_bar_{clean_tag(event.event_id)}", "sound_bar"),
                )

                # Sound Event label & duration
                bar_w = ex1 - ex0
                bar_center_x = (ex0 + ex1) / 2
                label_text = event.label if event.label else event.event_id
                if event.height is not None:
                    label_text += f" (H: {event.height:.1f})"

                if bar_w < 110:
                    display_title = event.event_id
                else:
                    display_title = f"{event.event_id}: {label_text}"

                self.canvas.create_text(
                    bar_center_x,
                    ey0 + 13,
                    text=display_title,
                    font=FONT_EVENT_TITLE,
                    fill=text_color,
                    tags=(f"sound_label_{clean_tag(event.event_id)}", "sound_label"),
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

        if self.constant_row_mode == "development":
            badge_title = "Row 1: Development"
            badge_sub = "(Low-to-High Profile)"
        else:
            badge_title = "Row 1: Constant"
            badge_sub = "(Active Row Count)"

        self.canvas.create_text(
            (8 + self.coords.left_header_width - 12) / 2,
            badge_y0 + 14,
            text=badge_title,
            font=FONT_CONSTANT_LABEL,
            fill=FG_CONSTANT_LABEL,
            tags=("pinned_left", "const_label"),
        )
        self.canvas.create_text(
            (8 + self.coords.left_header_width - 12) / 2,
            badge_y0 + 32,
            text=badge_sub,
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
                fill="#ffffff",
                outline="#cbd5e1",
                width=1,
                tags=("pinned_left", f"badge_box_{clean_tag(row.row_id)}"),
            )
            # Label
            display_row_label = row.label if row.label else f"Sound Group {row_idx + 1}"
            self.canvas.create_text(
                16,
                badge_y0 + 14,
                text=row.row_id,
                font=FONT_ROW_LABEL,
                fill="#0f172a",
                anchor="w",
                tags=("pinned_left", f"badge_lbl_{clean_tag(row.row_id)}"),
            )
            self.canvas.create_text(
                16,
                badge_y0 + 30,
                text=display_row_label,
                font=FONT_ROW_SUB,
                fill="#64748b",
                anchor="w",
                tags=("pinned_left", f"badge_sub_{clean_tag(row.row_id)}"),
            )

        # Position pinned items over current scroll position
        self._update_pinned_headers()
