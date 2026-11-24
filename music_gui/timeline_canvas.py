"""Interactive Tkinter timeline viewport widget.

Displays:
1. Unified Master Columns: Every row (Header, Row 1, and all temporary rows)
   displays the exact same master column structure derived from the song's sound events.
2. Row 1: Musical Development Carrier (Low-to-High Profile, Trend Line, and Active Row Diagnostic).
3. Temporary sound rows (Row 2, Row 3, ...) placed sequentially below Row 1.
4. Continuous colored sound bars spanning across multi-column intervals with crisp
   internal column boundary markers (visual annotations preserving SoundEvent integrity).
5. Solid vertical master column guidelines unifying all rows at exact x-coordinates.
6. Pinned left sidebar badges remaining visible during horizontal scrolling.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from music_gui.coordinates import TimelineCoordinates
from music_gui.gui_style import (
    BG_CANVAS,
    BG_COL_EVEN,
    BG_COL_ODD,
    BG_CONSTANT_CELL,
    BG_CONSTANT_LABEL,
    BG_CONSTANT_ROW,
    BG_HEADER,
    BORDER_CONSTANT_CELL,
    BORDER_CONSTANT_LABEL,
    BORDER_DEFAULT,
    BORDER_HEADER,
    FG_CONSTANT_LABEL,
    FG_CONSTANT_VAL,
    FG_HEADER,
    FG_HEADER_SUB,
    FG_TREND_LINE,
    FG_TREND_NODE,
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
    INTERNAL_DIVIDER_COLOR,
    SOUND_COLORS,
)
from music_model.constant_row import calculate_constant_row
from music_model.development_profile import calculate_development_constant_row
from music_model.midi_importer import pitch_to_note_name
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
        constant_row_mode: str = "active_rows",
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)

        self.coords: TimelineCoordinates = TimelineCoordinates(
            timeline, constant_row_at_top=constant_row_at_top
        )
        self.constant_row_mode: str = constant_row_mode
        self._last_pinned_x: float = 0.0

        # Build scrollable canvas architecture
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

    def find_column_header(self, col_index: int) -> List[int]:
        """Find canvas item ID(s) for a column header box."""
        return list(self.canvas.find_withtag(f"col_header_{col_index}"))

    # Backward compatibility alias for tests
    find_col_header = find_column_header

    def find_constant_cell(self, col_index: int) -> List[int]:
        """Find canvas item ID(s) for a constant row cell."""
        return list(self.canvas.find_withtag(f"const_cell_{col_index}"))

    find_const_cell = find_constant_cell

    def find_constant_val(self, col_index: int) -> List[int]:
        """Find canvas text item ID(s) for a constant row value."""
        return list(self.canvas.find_withtag(f"const_val_{col_index}"))

    find_const_val = find_constant_val

    def find_master_grid_lines(self) -> List[int]:
        """Find canvas line items for vertical master column gridlines."""
        return list(self.canvas.find_withtag("master_grid_line"))

    def find_internal_column_dividers(self, event_id: str = "") -> List[int]:
        """Find internal boundary divider lines over continuous sound bars."""
        if event_id:
            return list(self.canvas.find_withtag(f"internal_col_divider_{clean_tag(event_id)}"))
        return list(self.canvas.find_withtag("internal_col_divider"))

    def find_dev_trend_line(self) -> List[int]:
        """Find the continuous musical development trend line in Row 1."""
        return list(self.canvas.find_withtag("dev_trend_line"))

    def find_master_col_cells(self, row_id: str = "", col_index: Optional[int] = None) -> List[int]:
        """Find background master column cells in temporary rows."""
        if row_id and col_index is not None:
            return list(self.canvas.find_withtag(f"row_{clean_tag(row_id)}_col_{col_index}"))
        return list(self.canvas.find_withtag("master_col_cell"))

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

        active_row_counts = calculate_constant_row(timeline)
        dev_profile = calculate_development_constant_row(timeline) if self.constant_row_mode == "development" else None
        constant_row = dev_profile if self.constant_row_mode == "development" else active_row_counts

        total_w = self.coords.total_width
        total_h = self.coords.total_height

        # Update scrollregion
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # Y bounds for Header and Row 1 (Constant Row)
        y_hdr_top, y_hdr_bot = self.coords.header_y_bounds()
        y_const_top, y_const_bot = self.coords.constant_row_y_bounds()
        rows = timeline.rows
        timeline_bottom_y = total_h - self.coords.padding_bottom

        # -------------------------------------------------------------
        # 1. Master Timeline Header (Top): Columns & Shared Interval Titles
        # -------------------------------------------------------------
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

            # Master column header box
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
            # Column index & shared interval text
            self.canvas.create_text(
                (x0 + x1) / 2,
                y_hdr_top + 14,
                text=f"Master Col {col.index}",
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
                fill="#0f766e",
                tags=("col_duration",),
            )

        # -------------------------------------------------------------
        # 2. Row 1: The Musical Development Carrier (Prominent Row at Top)
        # -------------------------------------------------------------
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

        trend_points: List[Tuple[float, float]] = []
        valid_dev_vals = [
            v for v in (dev_profile.values if dev_profile else ())
            if isinstance(v, (int, float)) and v > 0
        ]
        min_dev = min(valid_dev_vals) if valid_dev_vals else 0.0
        max_dev = max(valid_dev_vals) if valid_dev_vals else 100.0
        dev_range = max_dev - min_dev if max_dev > min_dev else 1.0

        for col in columns:
            cx0, cx1 = self.coords.column_x_bounds(col)
            val = constant_row[col.index]
            act_count = active_row_counts[col.index]

            cell_pad_x = 4
            cell_pad_y = 6
            cell_x0 = cx0 + cell_pad_x
            cell_x1 = cx1 - cell_pad_x
            cell_y0 = y_const_top + cell_pad_y
            cell_y1 = y_const_bot - cell_pad_y

            # Result card aligned with master column
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
                if isinstance(val, (int, float)) and val > 0:
                    val_text = f"{val:.1f}" if isinstance(val, float) else str(val)
                    pitch_int = int(round(val))
                    if 0 <= pitch_int <= 127:
                        note_str = pitch_to_note_name(pitch_int)
                        active_sub = f"{note_str}  |  [{act_count} row" + ("s" if act_count != 1 else "") + "]"
                    else:
                        active_sub = f"Dev: {val_text}  |  [{act_count} row" + ("s" if act_count != 1 else "") + "]"

                    # Normalize y position for visible development trend line
                    norm_y = (val - min_dev) / dev_range
                    trend_y = cell_y1 - 10 - (norm_y * (cell_y1 - cell_y0 - 24))
                    trend_points.append((cell_center_x, trend_y))
                else:
                    val_text = "N/A"
                    active_sub = f"[{act_count} active row" + ("s" if act_count != 1 else "") + "]"
            else:
                val_text = str(val)
                active_sub = f"{val} active row" + ("s" if val != 1 else "")

            # Value text
            self.canvas.create_text(
                cell_center_x,
                cell_y0 + 17,
                text=val_text,
                font=FONT_CONSTANT_VAL,
                fill=FG_CONSTANT_VAL,
                tags=(f"const_val_{col.index}", "const_val"),
            )
            # Secondary diagnostic badge
            self.canvas.create_text(
                cell_center_x,
                cell_y0 + 34,
                text=active_sub,
                font=FONT_CONSTANT_SUB,
                fill="#78350f",
                tags=("const_sub",),
            )

        # Draw Development Trend Line connecting column nodes across Row 1
        if len(trend_points) >= 2:
            flat_coords = [coord for pt in trend_points for coord in pt]
            self.canvas.create_line(
                *flat_coords,
                fill=FG_TREND_LINE,
                width=2,
                tags=("dev_trend_line",),
            )
            for tx, ty in trend_points:
                self.canvas.create_oval(
                    tx - 3, ty - 3, tx + 3, ty + 3,
                    fill=FG_TREND_NODE,
                    outline="#ffffff",
                    width=1,
                    tags=("dev_trend_node",),
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

        # -------------------------------------------------------------
        # 3. Temporary Sound Rows (Row 2, Row 3, ...) Sequentially Below Row 1
        #    Every row renders the exact same master columns
        # -------------------------------------------------------------
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)

            # Master column cells on this temporary row (alternating subtle tint)
            for col in columns:
                cx0, cx1 = self.coords.column_x_bounds(col)
                col_tint = BG_COL_EVEN if (row_idx + col.index) % 2 == 0 else BG_COL_ODD
                self.canvas.create_rectangle(
                    cx0,
                    y_r_top,
                    cx1,
                    y_r_bot,
                    fill=col_tint,
                    outline="#e2e8f0",
                    width=1,
                    tags=(f"row_{clean_tag(row.row_id)}_col_{col.index}", "master_col_cell"),
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

                # Crisp internal column boundary markers across this continuous sound event
                # Visual annotation only: SoundEvent data object remains 100% continuous
                for b_time in boundaries:
                    if event.start_time_ms < b_time < event.end_time_ms:
                        bx = self.coords.time_to_x(b_time)
                        self.canvas.create_line(
                            bx,
                            ey0,
                            bx,
                            ey1,
                            fill=INTERNAL_DIVIDER_COLOR,
                            width=2,
                            dash=(2, 2),
                            tags=(f"internal_col_divider_{clean_tag(event.event_id)}", "internal_col_divider"),
                        )
                        # Notches at top and bottom edge of bar
                        self.canvas.create_line(
                            bx - 2, ey0, bx + 2, ey0, fill=bar_border, width=2, tags=("internal_col_divider",)
                        )
                        self.canvas.create_line(
                            bx - 2, ey1, bx + 2, ey1, fill=bar_border, width=2, tags=("internal_col_divider",)
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

        # -------------------------------------------------------------
        # 4. Solid Vertical Master Column Boundaries
        #    Extend through Header, Row 1, and all temporary rows
        # -------------------------------------------------------------
        for b_time in boundaries:
            bx = self.coords.time_to_x(b_time)
            self.canvas.create_line(
                bx,
                y_hdr_top,
                bx,
                timeline_bottom_y,
                fill=GRID_LINE_COLOR,
                width=1,
                tags=("master_grid_line", "grid_line"),
            )

        # -------------------------------------------------------------
        # 5. Pinned Left Header & Badges (Stay stationary during scrolling)
        # -------------------------------------------------------------
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

        # Header Title Badge (Top Left)
        hdr_center_y = (y_hdr_top + y_hdr_bot) / 2
        self.canvas.create_text(
            self.coords.left_header_width / 2,
            hdr_center_y - 8,
            text="Master Timeline",
            font=FONT_HEADER,
            fill=FG_HEADER,
            tags=("pinned_left", "pinned_title"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2,
            hdr_center_y + 10,
            text=f"{len(columns)} Master Columns ({len(boundaries)} Boundaries)",
            font=FONT_HEADER_SUB,
            fill=FG_HEADER_SUB,
            tags=("pinned_left", "pinned_subtitle"),
        )

        # Row 1 Badge
        const_badge_y = (y_const_top + y_const_bot) / 2
        r1_badge_title = (
            "Row 1: Constant (Development Profile)"
            if self.constant_row_mode == "development"
            else "Row 1: Constant (Active Row Count)"
        )
        r1_badge_sub = (
            "Development Profile (Low-to-High)"
            if self.constant_row_mode == "development"
            else "Active Row Count"
        )
        self.canvas.create_rectangle(
            4,
            y_const_top + 4,
            self.coords.left_header_width - 4,
            y_const_bot - 4,
            fill=BG_CONSTANT_LABEL,
            outline=BORDER_CONSTANT_LABEL,
            width=1.5,
            tags=("pinned_left", "const_label_bg", "constant_badge"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2,
            const_badge_y - 8,
            text=r1_badge_title,
            font=FONT_CONSTANT_LABEL,
            fill=FG_CONSTANT_LABEL,
            tags=("pinned_left", "const_label_title", "const_label"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2,
            const_badge_y + 10,
            text=r1_badge_sub,
            font=FONT_CONSTANT_SUB,
            fill="#78350f",
            tags=("pinned_left", "const_label_sub", "const_sublabel"),
        )

        # Temporary Row Badges (Below Row 1)
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            row_badge_y = (y_r_top + y_r_bot) / 2
            row_title = f"{row.row_id}" if not row.label else f"{row.row_id} ({row.label})"

            self.canvas.create_rectangle(
                4,
                y_r_top + 4,
                self.coords.left_header_width - 4,
                y_r_bot - 4,
                fill="#dcfce7",
                outline="#86efac",
                width=1.5,
                tags=("pinned_left", f"row_badge_bg_{clean_tag(row.row_id)}"),
            )
            self.canvas.create_text(
                self.coords.left_header_width / 2,
                row_badge_y - 8,
                text=row_title,
                font=FONT_ROW_LABEL,
                fill="#166534",
                tags=("pinned_left", f"row_badge_title_{clean_tag(row.row_id)}"),
            )
            self.canvas.create_text(
                self.coords.left_header_width / 2,
                row_badge_y + 10,
                text=f"{len(row)} event(s) on Master Timeline",
                font=FONT_ROW_SUB,
                fill="#15803d",
                tags=("pinned_left", f"row_badge_sub_{clean_tag(row.row_id)}"),
            )

        self._update_pinned_headers()
