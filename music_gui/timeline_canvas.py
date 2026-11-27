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
7. Statement 18 Fundamental Groups Mode:
   - Uniform fundamental cells with cyclic 0-9 labels.
   - Distinct multi-unit sound groups (e.g. 4u and 3u).
   - Composite Row 1 boundary segments and continuous takeoff development line.
   - Meeting point highlight lines and directional hand-off badges.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, List, Optional, Tuple

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

        # Milestone 4B: Statement 18 Group Timeline state
        self.group_timeline: Optional[Any] = None
        self.group_passage_mode: str = "ascending"  # 'ascending' or 'flat'
        self.group_cell_width: float = 80.0

        # Playback Transport Cursor & Highlight state (JOB-03)
        self._sound_bar_original_borders: Dict[str, Tuple[str, float]] = {}
        self._currently_active_event_ids: Set[str] = set()
        self._playback_cursor_ms: Optional[float] = None
        # Active-event ids last supplied by the transport snapshot (None = derive from timeline).
        self._playback_explicit_ids: Optional[Set[str]] = None

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
        self.group_timeline = None
        self.coords.timeline = timeline
        self.redraw()

    def set_group_timeline(self, timeline: Any, passage_mode: str = "ascending") -> None:
        """Set Statement 18 group timeline mode."""
        self.group_timeline = timeline
        self.group_passage_mode = passage_mode
        self.redraw()

    def clear_group_timeline(self) -> None:
        """Exit Statement 18 group timeline mode and return to standard timeline."""
        self.group_timeline = None
        self.redraw()

    def set_constant_row_mode(self, mode: str) -> None:
        """Set measurement mode for Row 1 ('active_rows' or 'development')."""
        self.constant_row_mode = mode.lower().strip()
        self.redraw()

    def zoom_in(self) -> None:
        """Magnify horizontal timeline resolution."""
        if self.group_timeline is not None:
            self.group_cell_width = min(self.group_cell_width * 1.25, 240.0)
            self.redraw()
        else:
            self.coords.zoom_in()
            self.redraw()

    def zoom_out(self) -> None:
        """Demagnify horizontal timeline resolution."""
        if self.group_timeline is not None:
            self.group_cell_width = max(self.group_cell_width * 0.8, 40.0)
            self.redraw()
        else:
            self.coords.zoom_out()
            self.redraw()

    def reset_zoom(self) -> None:
        """Reset horizontal zoom to default resolution."""
        if self.group_timeline is not None:
            self.group_cell_width = 80.0
            self.redraw()
        else:
            self.coords.reset_zoom()
            self.redraw()

    # --- Element Query Helpers for Automated GUI Tests ---

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

    # --- Milestone 4B Query Helpers ---

    def find_group_cell_headers(self) -> List[int]:
        """Find canvas item IDs for fundamental grid cell header boxes."""
        return list(self.canvas.find_withtag("group_cell_header"))

    def find_group_cell_labels(self) -> List[int]:
        """Find canvas text item IDs for cyclic 0-9 labels."""
        return list(self.canvas.find_withtag("group_cell_label"))

    def find_group_boxes(self, group_id: str = "") -> List[int]:
        """Find multi-unit sound group boxes."""
        if group_id:
            return list(self.canvas.find_withtag(f"group_box_{clean_tag(group_id)}"))
        return list(self.canvas.find_withtag("group_box"))

    def find_row1_segments(self) -> List[int]:
        """Find Row 1 composite boundary segments."""
        return list(self.canvas.find_withtag("row1_segment"))

    def find_meeting_markers(self) -> List[int]:
        """Find meeting point hand-off indicator markers."""
        return list(self.canvas.find_withtag("meeting_marker"))

    def find_meeting_lines(self) -> List[int]:
        """Find vertical meeting point highlight lines across rows."""
        return list(self.canvas.find_withtag("meeting_highlight_line"))

    def find_dev_nodes(self) -> List[int]:
        """Find development curve node points in Row 1."""
        return list(self.canvas.find_withtag("dev_node"))

    # --- JOB-03 Playhead Transport & Active Highlighting ---

    def find_playback_cursor(self) -> List[int]:
        """Find canvas item IDs for playback cursor components."""
        return list(self.canvas.find_withtag("playback_cursor"))

    def clear_playback_cursor(self) -> None:
        """Remove playback cursor and restore original outlines of sound bars."""
        self._playback_cursor_ms = None
        self._playback_explicit_ids = None
        self.canvas.delete("playback_cursor")
        for ev_id in list(self._currently_active_event_ids):
            orig_border, orig_w = self._sound_bar_original_borders.get(ev_id, (BORDER_DEFAULT, 2.0))
            self.canvas.itemconfigure(f"sound_bar_{clean_tag(ev_id)}", outline=orig_border, width=orig_w)
        self._currently_active_event_ids.clear()

    def set_playback_cursor(
        self,
        position_ms: float,
        active_event_ids: Optional[Set[str]] = None,
        auto_scroll: bool = True,
    ) -> None:
        """Position the playback playhead cursor and highlight active sound events.

        Args:
            position_ms: Authoritative playback position in milliseconds.
            active_event_ids: Optional set of active event IDs. If None, derived
                from the timeline's get_active_events_at(position_ms).
            auto_scroll: Whether to automatically scroll canvas to keep the cursor in view.
        """
        self._playback_cursor_ms = float(position_ms)
        self._playback_explicit_ids = None if active_event_ids is None else set(active_event_ids)
        x = self.coords.time_to_x(self._playback_cursor_ms)

        y_hdr_top, _ = self.coords.header_y_bounds()
        timeline_bottom_y = self.coords.total_height - 20

        # Create or update cursor items
        cursor_lines = self.canvas.find_withtag("playback_cursor_line")
        cursor_heads = self.canvas.find_withtag("playback_cursor_head")

        if cursor_lines and cursor_heads:
            self.canvas.coords("playback_cursor_line", x, y_hdr_top, x, timeline_bottom_y)
            self.canvas.coords(
                "playback_cursor_head",
                x - 6, y_hdr_top,
                x + 6, y_hdr_top,
                x, y_hdr_top + 10,
            )
        else:
            self.canvas.delete("playback_cursor")
            self.canvas.create_line(
                x, y_hdr_top, x, timeline_bottom_y,
                fill="#dc2626", width=2.5,
                tags=("playback_cursor", "playback_cursor_line"),
            )
            self.canvas.create_polygon(
                x - 6, y_hdr_top,
                x + 6, y_hdr_top,
                x, y_hdr_top + 10,
                fill="#dc2626", outline="#991b1b", width=1,
                tags=("playback_cursor", "playback_cursor_head"),
            )

        self.canvas.tag_raise("playback_cursor")
        self.canvas.tag_raise("pinned_left")

        # Update event highlighting
        if active_event_ids is None and self.coords.timeline:
            if hasattr(self.coords.timeline, "get_active_events_at"):
                active_events = self.coords.timeline.get_active_events_at(self._playback_cursor_ms)
                new_active_ids = {e.event_id for e in active_events}
            elif hasattr(self.coords.timeline, "timeline") and hasattr(self.coords.timeline.timeline, "get_active_events_at"):
                active_events = self.coords.timeline.timeline.get_active_events_at(self._playback_cursor_ms)
                new_active_ids = {e.event_id for e in active_events}
            else:
                new_active_ids = {
                    e.event_id
                    for r in getattr(self.coords.timeline, "rows", ())
                    for e in getattr(r, "events", ())
                    if e.start_time_ms <= self._playback_cursor_ms < e.end_time_ms
                }
        else:
            new_active_ids = set(active_event_ids or ())

        # Un-highlight deactivated events
        for ev_id in (self._currently_active_event_ids - new_active_ids):
            orig_border, orig_w = self._sound_bar_original_borders.get(ev_id, (BORDER_DEFAULT, 2.0))
            self.canvas.itemconfigure(f"sound_bar_{clean_tag(ev_id)}", outline=orig_border, width=orig_w)

        # Highlight newly activated events
        for ev_id in (new_active_ids - self._currently_active_event_ids):
            self.canvas.itemconfigure(f"sound_bar_{clean_tag(ev_id)}", outline="#dc2626", width=3.5)

        self._currently_active_event_ids = new_active_ids

        # Auto-scrolling to keep playhead comfortably visible
        if auto_scroll:
            try:
                x_view = self.canvas.xview()
                total_w = self.coords.total_width
                if total_w > 0 and len(x_view) == 2:
                    vis_start = x_view[0] * total_w
                    vis_end = x_view[1] * total_w
                    header_w = self.coords.left_header_width
                    if x > vis_end - 60 or x < vis_start + header_w:
                        target_x = max(0.0, x - header_w - 80.0)
                        self.canvas.xview_moveto(max(0.0, min(1.0, target_x / total_w)))
                        self._update_pinned_headers()
            except Exception:
                pass

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
        """Erase and redraw the active timeline."""
        if self.group_timeline is not None:
            self._redraw_group_timeline()
        else:
            self._redraw_standard_timeline()

    # =========================================================================
    # Milestone 4B: Statement 18 Fundamental Groups Rendering
    # =========================================================================

    def _redraw_group_timeline(self) -> None:
        """Renders the Statement 18 uniform fundamental cells, multi-unit groups, and composite Row 1."""
        self.canvas.delete("all")
        self._last_pinned_x = 0.0

        timeline = self.group_timeline
        u_ms = timeline.grid.u_ms
        N = timeline.grid.total_cells
        cell_w = self.group_cell_width
        sidebar_w = 200

        total_w = sidebar_w + N * cell_w + 60
        total_h = 420

        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

        # Lane vertical bounds
        y_hdr_top = 0
        y_hdr_bot = 50
        y_r1_top = 50
        y_r1_bot = 160
        y_r2_top = 160
        y_r2_bot = 245
        y_r3_top = 245
        y_r3_bot = 330
        y_meet_top = 330
        y_meet_bot = 425
        total_h = 445

        # 1. Background tracks for each lane
        self.canvas.create_rectangle(sidebar_w, y_r1_top, total_w, y_r1_bot, fill="#fffbeb", outline="", tags="lane_bg")
        self.canvas.create_rectangle(sidebar_w, y_r2_top, total_w, y_r2_bot, fill="#ffffff", outline="", tags="lane_bg")
        self.canvas.create_rectangle(sidebar_w, y_r3_top, total_w, y_r3_bot, fill="#f8fafc", outline="", tags="lane_bg")
        self.canvas.create_rectangle(sidebar_w, y_meet_top, total_w, y_meet_bot, fill="#ffffff", outline="", tags="lane_bg")

        # 2. Fundamental Grid Header & Full-Height Vertical Gridlines
        for i in range(N):
            x1 = sidebar_w + i * cell_w
            x2 = x1 + cell_w
            fill_c = "#f8fafc" if i % 2 == 0 else "#f1f5f9"
            self.canvas.create_rectangle(
                x1, y_hdr_top, x2, y_hdr_bot,
                fill=fill_c, outline="#cbd5e1",
                tags=(f"group_cell_header_{i}", "group_cell_header"),
            )
            lbl = timeline.grid.cell_label(i)
            self.canvas.create_text(
                (x1 + x2) / 2, 18,
                text=str(lbl),
                font=("Segoe UI", 12, "bold"),
                fill="#0f172a",
                tags=(f"group_cell_label_{i}", "group_cell_label"),
            )
            self.canvas.create_text(
                (x1 + x2) / 2, 36,
                text=f"[{i * u_ms}-{(i + 1) * u_ms}ms]",
                font=("Segoe UI", 8),
                fill="#64748b",
                tags=(f"group_cell_sub_{i}", "group_cell_sub"),
            )

        # Full-height vertical gridlines
        for i in range(N + 1):
            x = sidebar_w + i * cell_w
            self.canvas.create_line(
                x, y_hdr_top, x, y_meet_top,
                fill="#cbd5e1", dash=(2, 2),
                tags=(f"group_gridline_{i}", "group_gridline"),
            )

        # Subtle vertical meeting point highlight lines at combined boundaries
        bounds = timeline.combined_boundaries()
        for b_unit in bounds:
            if 0 < b_unit < N:
                bx = sidebar_w + b_unit * cell_w
                self.canvas.create_line(
                    bx, y_r1_top, bx, y_meet_top,
                    fill="#3b82f6", width=2,
                    tags=(f"meeting_line_{b_unit}", "meeting_highlight_line"),
                )

        # 3. Row 1 Composite Segments & Development Curve
        segments = timeline.derive_row1_segments()
        trend_points = []
        for idx, seg in enumerate(segments):
            sx1 = sidebar_w + seg.start_unit * cell_w
            sx2 = sidebar_w + seg.end_unit * cell_w
            seg_w = sx2 - sx1
            cx = (sx1 + sx2) / 2.0

            self.canvas.create_rectangle(
                sx1 + 2, y_r1_top + 4, sx2 - 2, y_r1_bot - 4,
                fill="#ffffff", outline="#d97706", width=1.5,
                tags=(f"row1_seg_{idx}", "row1_segment", f"const_cell_{idx}"),
            )
            if seg_w >= 130:
                seg_title = f"Seg {idx + 1}: {seg.width_units}u ({int(seg.width_units * u_ms)}ms)"
            else:
                seg_title = f"Seg {idx + 1} ({seg.width_units}u)"

            self.canvas.create_text(
                cx, y_r1_top + 16,
                text=seg_title,
                font=("Segoe UI", 8, "bold"),
                fill="#92400e",
                tags=(f"const_title_{idx}",),
            )
            if seg_w >= 130:
                notes_text = ", ".join(seg.active_notes)
            else:
                notes_text = ", ".join([n.split("(")[0].strip() for n in seg.active_notes])

            self.canvas.create_text(
                cx, y_r1_top + 32,
                text=notes_text,
                font=("Segoe UI", 7),
                fill="#78350f",
                tags=(f"const_sub_{idx}",),
            )
            self.canvas.create_line(
                sx1 + 6, y_r1_top + 44, sx2 - 6, y_r1_top + 44,
                fill="#fde68a", dash=(2, 2),
                tags=(f"card_div_{idx}",),
            )

            # Horizontal center proportional to actual segment span
            if self.group_passage_mode == "flat":
                cy = 136.0
            else:
                norm_p = max(0.0, min(1.0, (seg.mean_pitch - 36.0) / 48.0))
                cy = 146.0 - norm_p * 32.0

            trend_points.append((cx, cy))
            self.canvas.create_text(
                cx, cy - 13,
                text=f"{seg.mean_pitch:.1f}",
                font=("Segoe UI", 8, "bold"),
                fill="#b45309",
                tags=(f"const_val_{idx}",),
            )

        if len(trend_points) >= 2:
            flat_coords = [c for pt in trend_points for c in pt]
            self.canvas.create_line(
                *flat_coords,
                fill="#d97706", width=2.5,
                tags=("dev_trend_line", "development_line"),
            )
            for p_idx, (px, py) in enumerate(trend_points):
                self.canvas.create_oval(
                    px - 4, py - 4, px + 4, py + 4,
                    fill="#f59e0b", outline="#b45309", width=1.5,
                    tags=(f"dev_node_{p_idx}", "dev_node"),
                )

        # 4. Row 2 Groups (e.g. 4-unit groups)
        rows_list = list(timeline.groups_by_row.values())
        if len(rows_list) > 0:
            r2_groups = rows_list[0]
            for g_idx, g in enumerate(r2_groups):
                gx1 = sidebar_w + g.start_unit * cell_w
                gx2 = sidebar_w + g.end_unit * cell_w
                self.canvas.create_rectangle(
                    gx1 + 2, y_r2_top + 4, gx2 - 2, y_r2_bot - 4,
                    fill="#fef3c7", outline="#d97706", width=2,
                    tags=(f"group_box_{clean_tag(g.group_id)}", "group_box", "group_box_row2"),
                )
                for k in range(1, g.width_units):
                    kx = gx1 + k * cell_w
                    self.canvas.create_line(
                        kx, y_r2_top + 6, kx, y_r2_bot - 6,
                        fill="#f59e0b", dash=(3, 2),
                        tags=("internal_unit_tick",),
                    )
                note_desc = f"{g.notes[0].note_name} (MIDI {g.notes[0].pitch})" if g.notes else ""
                self.canvas.create_text(
                    (gx1 + gx2) / 2, y_r2_top + 28,
                    text=f"{g.group_id} ({g.width_units} units = {int(g.width_units * u_ms)}ms)",
                    font=("Segoe UI", 9, "bold"),
                    fill="#92400e",
                )
                self.canvas.create_text(
                    (gx1 + gx2) / 2, y_r2_top + 52,
                    text=f"{note_desc} [{int(g.start_time_ms(u_ms))}-{int(g.end_time_ms(u_ms))}ms]",
                    font=("Segoe UI", 8),
                    fill="#78350f",
                )

        # 5. Row 3 Groups (e.g. 3-unit groups)
        if len(rows_list) > 1:
            r3_groups = rows_list[1]
            for g_idx, g in enumerate(r3_groups):
                gx1 = sidebar_w + g.start_unit * cell_w
                gx2 = sidebar_w + g.end_unit * cell_w
                self.canvas.create_rectangle(
                    gx1 + 2, y_r3_top + 4, gx2 - 2, y_r3_bot - 4,
                    fill="#e0f2fe", outline="#0284c7", width=2,
                    tags=(f"group_box_{clean_tag(g.group_id)}", "group_box", "group_box_row3"),
                )
                for k in range(1, g.width_units):
                    kx = gx1 + k * cell_w
                    self.canvas.create_line(
                        kx, y_r3_top + 6, kx, y_r3_bot - 6,
                        fill="#38bdf8", dash=(3, 2),
                        tags=("internal_unit_tick",),
                    )
                note_desc = f"{g.notes[0].note_name} (MIDI {g.notes[0].pitch})" if g.notes else ""
                self.canvas.create_text(
                    (gx1 + gx2) / 2, y_r3_top + 28,
                    text=f"{g.group_id} ({g.width_units} units = {int(g.width_units * u_ms)}ms)",
                    font=("Segoe UI", 9, "bold"),
                    fill="#0369a1",
                )
                self.canvas.create_text(
                    (gx1 + gx2) / 2, y_r3_top + 52,
                    text=f"{note_desc} [{int(g.start_time_ms(u_ms))}-{int(g.end_time_ms(u_ms))}ms]",
                    font=("Segoe UI", 8),
                    fill="#0c4a6e",
                )

        # 6. Meeting Points Bar
        for b_unit in bounds:
            bx = sidebar_w + b_unit * cell_w
            desc = timeline._describe_boundary_events(b_unit)
            self.canvas.create_polygon(
                bx - 5, y_meet_top + 8, bx + 5, y_meet_top + 8, bx, y_meet_top + 2,
                fill="#3b82f6", outline="#1d4ed8",
                tags=(f"meeting_triangle_{b_unit}", "meeting_marker"),
            )

            stag_y = y_meet_top + (24 if b_unit % 2 == 0 else 54)
            if "R3" in desc:
                b_fill, b_outline, t_fill = "#dbeafe", "#2563eb", "#1e40af"
            elif "R2" in desc:
                b_fill, b_outline, t_fill = "#fef3c7", "#d97706", "#92400e"
            else:
                b_fill, b_outline, t_fill = "#f1f5f9", "#64748b", "#334155"

            if "Hand-off" in desc:
                short_desc = f"Unit {b_unit}: R3 Hand-off" if "R3" in desc else f"Unit {b_unit}: R2 Hand-off"
            elif "Entry" in desc:
                short_desc = f"Unit {b_unit}: Entry (R2, R3)"
            else:
                short_desc = f"Unit {b_unit}: Exit"

            badge_w = 54
            badge_cx = bx
            if bx - badge_w < sidebar_w + 4:
                badge_cx = sidebar_w + badge_w + 4
            elif bx + badge_w > total_w - 4:
                badge_cx = total_w - badge_w - 4

            self.canvas.create_rectangle(
                badge_cx - badge_w, stag_y - 10, badge_cx + badge_w, stag_y + 10,
                fill=b_fill, outline=b_outline, width=1,
                tags=(f"meeting_label_{b_unit}", "meeting_label"),
            )
            self.canvas.create_text(
                badge_cx, stag_y,
                text=short_desc,
                font=("Segoe UI", 7, "bold"),
                fill=t_fill,
                tags=(f"meeting_label_{b_unit}", "meeting_label"),
            )

        # 7. Left Pinned Badges (Stationary when scrolled horizontally)
        self.canvas.create_rectangle(
            0, y_hdr_top, sidebar_w, y_hdr_bot,
            fill="#e2e8f0", outline="#cbd5e1",
            tags=("pinned_left", "group_header_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, 18,
            text="Fundamental Grid",
            font=("Segoe UI", 9, "bold"),
            fill="#0f172a",
            tags=("pinned_left", "group_header_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, 34,
            text=f"u = {u_ms}ms (Equal Cells)",
            font=("Segoe UI", 8),
            fill="#475569",
            tags=("pinned_left", "group_header_badge"),
        )

        self.canvas.create_rectangle(
            0, y_r1_top, sidebar_w, y_r1_bot,
            fill="#fef3c7", outline="#f59e0b",
            tags=("pinned_left", "row1_badge", "constant_badge", "const_label_bg"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r1_top + 26,
            text="Row 1: Master Carrier",
            font=("Segoe UI", 9, "bold"),
            fill="#92400e",
            tags=("pinned_left", "row1_badge", "constant_badge", "const_label_title"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r1_top + 48,
            text="Composite Segments",
            font=("Segoe UI", 8),
            fill="#b45309",
            tags=("pinned_left", "row1_badge", "constant_badge", "const_label_sub"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r1_top + 68,
            text="Takeoff Flight Trajectory",
            font=("Segoe UI", 7, "italic"),
            fill="#78350f",
            tags=("pinned_left", "row1_badge", "constant_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r1_top + 88,
            text="Pitch Development Profile",
            font=("Segoe UI", 7),
            fill="#92400e",
            tags=("pinned_left", "row1_badge", "constant_badge"),
        )

        r2_name = list(timeline.groups_by_row.keys())[0] if len(rows_list) > 0 else "Row 2"
        self.canvas.create_rectangle(
            0, y_r2_top, sidebar_w, y_r2_bot,
            fill="#fef3c7", outline="#f59e0b",
            tags=("pinned_left", "row2_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r2_top + 30,
            text=r2_name,
            font=("Segoe UI", 9, "bold"),
            fill="#92400e",
            tags=("pinned_left", "row2_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r2_top + 52,
            text=f"{len(r2_groups)} Sound Groups",
            font=("Segoe UI", 8),
            fill="#b45309",
            tags=("pinned_left", "row2_badge"),
        )

        r3_name = list(timeline.groups_by_row.keys())[1] if len(rows_list) > 1 else "Row 3"
        self.canvas.create_rectangle(
            0, y_r3_top, sidebar_w, y_r3_bot,
            fill="#e0f2fe", outline="#0284c7",
            tags=("pinned_left", "row3_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r3_top + 30,
            text=r3_name,
            font=("Segoe UI", 9, "bold"),
            fill="#0369a1",
            tags=("pinned_left", "row3_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_r3_top + 52,
            text=f"{len(r3_groups)} Sound Groups",
            font=("Segoe UI", 8),
            fill="#0284c7",
            tags=("pinned_left", "row3_badge"),
        )

        self.canvas.create_rectangle(
            0, y_meet_top, sidebar_w, y_meet_bot,
            fill="#f1f5f9", outline="#94a3b8",
            tags=("pinned_left", "meeting_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_meet_top + 30,
            text="Meeting Points",
            font=("Segoe UI", 9, "bold"),
            fill="#1e293b",
            tags=("pinned_left", "meeting_badge"),
        )
        self.canvas.create_text(
            sidebar_w / 2, y_meet_top + 50,
            text="Boundary Hand-offs",
            font=("Segoe UI", 8),
            fill="#475569",
            tags=("pinned_left", "meeting_badge"),
        )

        self.canvas.create_line(
            sidebar_w, 0, sidebar_w, y_meet_bot,
            fill="#94a3b8", width=2,
            tags=("pinned_left", "pinned_border"),
        )

        self._update_pinned_headers()

    # =========================================================================
    # Standard Timeline Rendering
    # =========================================================================

    def _redraw_standard_timeline(self) -> None:
        """Erase and redraw the complete timeline, sound rows, and constant row."""
        self.canvas.delete("all")
        self._last_pinned_x = 0.0
        self._sound_bar_original_borders.clear()
        self._currently_active_event_ids.clear()

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

        y_hdr_top, y_hdr_bot = self.coords.header_y_bounds()
        y_const_top, y_const_bot = self.coords.constant_row_y_bounds()
        rows = timeline.rows
        timeline_bottom_y = self.coords.total_height - 20

        # Background lanes
        self.canvas.create_rectangle(
            self.coords.left_header_width, y_const_top, total_w, y_const_bot,
            fill=BG_CONSTANT_ROW, outline="", tags="const_bg",
        )
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            row_bg = "#ffffff" if row_idx % 2 == 0 else "#f8fafc"
            self.canvas.create_rectangle(
                self.coords.left_header_width, y_r_top, total_w, y_r_bot,
                fill=row_bg, outline="", tags=f"row_bg_{clean_tag(row.row_id)}",
            )

        # Draw master column cells
        for col_idx, col in enumerate(columns):
            x1, x2 = self.coords.column_x_bounds(col)
            duration_s = col.duration_ms / 1000.0
            hdr_bg = BG_COL_EVEN if col_idx % 2 == 0 else BG_COL_ODD

            # Time header cell
            self.canvas.create_rectangle(
                x1, y_hdr_top, x2, y_hdr_bot,
                fill=hdr_bg, outline=BORDER_HEADER, width=1,
                tags=(f"col_header_{col_idx}", "col_header"),
            )
            col_cx = (x1 + x2) / 2
            col_w = x2 - x1
            header_title = f"Col {col_idx}" if col_w < 100 else f"Master Col {col_idx}"
            self.canvas.create_text(
                col_cx, y_hdr_top + 14,
                text=header_title, font=FONT_HEADER, fill=FG_HEADER,
                tags=(f"col_title_{col_idx}", "col_header_text"),
            )
            self.canvas.create_text(
                col_cx, y_hdr_top + 28,
                text=f"[{col.start_time_ms}, {col.end_time_ms}) ms",
                font=FONT_HEADER_SUB, fill=FG_HEADER_SUB,
                tags=(f"col_range_{col_idx}", "col_header_subtext"),
            )
            self.canvas.create_text(
                col_cx, y_hdr_top + 40,
                text=f"Δ {col.duration_ms} ms ({duration_s:.2f}s)",
                font=FONT_HEADER_SUB, fill="#0284c7",
                tags=(f"col_dur_{col_idx}", "col_header_subtext"),
            )

            # Row 1 cell
            val = constant_row[col_idx]
            self.canvas.create_rectangle(
                x1 + 2, y_const_top + 4, x2 - 2, y_const_bot - 4,
                fill=BG_CONSTANT_CELL, outline=BORDER_CONSTANT_CELL, width=1.5,
                tags=(f"const_cell_{col_idx}", "constant_cell"),
            )
            val_text = f"{val:.1f}" if self.constant_row_mode == "development" else str(val)
            self.canvas.create_text(
                col_cx, (y_const_top + y_const_bot) / 2 - 8,
                text=val_text, font=FONT_CONSTANT_VAL, fill=FG_CONSTANT_VAL,
                tags=(f"const_val_{col_idx}", "constant_val"),
            )
            if self.constant_row_mode == "development":
                note_str = pitch_to_note_name(int(round(val)))
                sub_label = f"{note_str} ({int(round(val))})" if col_w >= 70 else note_str
            else:
                sub_label = "active row" if val == 1 else "active rows"
            self.canvas.create_text(
                col_cx, (y_const_top + y_const_bot) / 2 + 10,
                text=sub_label, font=FONT_CONSTANT_SUB, fill="#78350f",
                tags=(f"const_sub_{col_idx}", "constant_sub"),
            )

            # Master column cells in temporary rows
            for row_idx, row in enumerate(rows):
                y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
                cell_bg = "#ffffff" if (row_idx + col_idx) % 2 == 0 else "#f8fafc"
                self.canvas.create_rectangle(
                    x1, y_r_top, x2, y_r_bot,
                    fill=cell_bg, outline="#e2e8f0", width=1,
                    tags=(f"row_{clean_tag(row.row_id)}_col_{col_idx}", "master_col_cell"),
                )

        # Continuous trend line for development mode
        if self.constant_row_mode == "development" and len(columns) > 1:
            pitches = dev_profile
            trend_points = []
            for col_idx, col in enumerate(columns):
                x1, x2 = self.coords.column_x_bounds(col)
                col_cx = (x1 + x2) / 2
                pitch = pitches[col_idx]
                min_p, max_p = 20.0, 100.0
                norm_p = max(0.0, min(1.0, (pitch - min_p) / (max_p - min_p)))
                plot_y = (y_const_bot - 14) - norm_p * (y_const_bot - y_const_top - 28)
                trend_points.extend([col_cx, plot_y])

            self.canvas.create_line(
                *trend_points,
                fill=FG_TREND_LINE, width=2.5, smooth=True,
                tags=("dev_trend_line", "trend_line"),
            )
            for i in range(0, len(trend_points), 2):
                nx, ny = trend_points[i], trend_points[i + 1]
                self.canvas.create_oval(
                    nx - 4, ny - 4, nx + 4, ny + 4,
                    fill=FG_TREND_NODE, outline="#ffffff", width=1.5,
                    tags=("dev_trend_node", "trend_node"),
                )

        # Sound Event Bars
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            color_idx = row_idx % len(SOUND_COLORS)
            fill_color, border_color, text_color = SOUND_COLORS[color_idx]

            for event in row.events:
                ex1, ex2 = self.coords.event_x_bounds(event)
                ey0 = y_r_top + 6
                ey1 = y_r_bot - 6
                bar_w = ex2 - ex1

                self.canvas.create_rectangle(
                    ex1, ey0, ex2, ey1,
                    fill=fill_color, outline=border_color, width=2,
                    tags=(
                        f"sound_bar_{clean_tag(event.event_id)}",
                        "sound_bar",
                        f"row_event_{clean_tag(row.row_id)}",
                    ),
                )
                self._sound_bar_original_borders[event.event_id] = (border_color, 2.0)

                for b_time in boundaries:
                    if event.start_time_ms < b_time < event.end_time_ms:
                        div_x = self.coords.time_to_x(b_time)
                        self.canvas.create_line(
                            div_x, ey0 + 2, div_x, ey1 - 2,
                            fill=INTERNAL_DIVIDER_COLOR, width=1.5,
                            tags=(
                                f"internal_col_divider_{clean_tag(event.event_id)}",
                                "internal_col_divider",
                            ),
                        )

                bar_center_x = (ex1 + ex2) / 2
                label_text = event.label if event.label else ""
                if event.height is not None:
                    label_text += f" (H: {event.height:.1f})"

                display_title = event.event_id if bar_w < 110 else f"{event.event_id}: {label_text}"
                self.canvas.create_text(
                    bar_center_x, ey0 + 13,
                    text=display_title, font=FONT_EVENT_TITLE, fill=text_color,
                    tags=(f"sound_label_{clean_tag(event.event_id)}", "sound_label"),
                )
                self.canvas.create_text(
                    bar_center_x, ey0 + 29,
                    text=f"[{event.start_time_ms}, {event.end_time_ms}) ms  ({event.duration_ms} ms)",
                    font=FONT_EVENT_SUB, fill=text_color,
                    tags=(f"sound_sub_{clean_tag(event.event_id)}", "sound_sub"),
                )

        # Solid Vertical Master Column Boundaries
        for b_time in boundaries:
            bx = self.coords.time_to_x(b_time)
            self.canvas.create_line(
                bx, y_hdr_top, bx, timeline_bottom_y,
                fill=GRID_LINE_COLOR, width=1,
                tags=("master_grid_line", "grid_line"),
            )

        # Pinned Left Header & Badges
        self.canvas.create_rectangle(
            0, y_hdr_top, self.coords.left_header_width, timeline_bottom_y,
            fill="#f1f5f9", outline="#cbd5e1", width=1,
            tags=("pinned_left", "pinned_sidebar_bg"),
        )
        self.canvas.create_line(
            self.coords.left_header_width, y_hdr_top, self.coords.left_header_width, timeline_bottom_y,
            fill="#94a3b8", width=2,
            tags=("pinned_left", "pinned_sidebar_border"),
        )

        hdr_center_y = (y_hdr_top + y_hdr_bot) / 2
        self.canvas.create_text(
            self.coords.left_header_width / 2, hdr_center_y - 8,
            text="Master Timeline", font=FONT_HEADER, fill=FG_HEADER,
            tags=("pinned_left", "pinned_title"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2, hdr_center_y + 10,
            text=f"{len(columns)} Master Columns ({len(boundaries)} Boundaries)",
            font=FONT_HEADER_SUB, fill=FG_HEADER_SUB,
            tags=("pinned_left", "pinned_subtitle"),
        )

        # Row 1 Badge
        const_badge_y = (y_const_top + y_const_bot) / 2
        r1_badge_title = "Row 1: Constant (Development Profile)" if self.constant_row_mode == "development" else "Row 1: Constant (Active Row Count)"
        r1_badge_sub = "Development Profile (Low-to-High)" if self.constant_row_mode == "development" else "Active Row Count"
        self.canvas.create_rectangle(
            4, y_const_top + 4, self.coords.left_header_width - 4, y_const_bot - 4,
            fill=BG_CONSTANT_LABEL, outline=BORDER_CONSTANT_LABEL, width=1.5,
            tags=("pinned_left", "const_label_bg", "constant_badge"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2, const_badge_y - 8,
            text=r1_badge_title, font=FONT_CONSTANT_LABEL, fill=FG_CONSTANT_LABEL,
            tags=("pinned_left", "const_label_title", "const_label"),
        )
        self.canvas.create_text(
            self.coords.left_header_width / 2, const_badge_y + 10,
            text=r1_badge_sub, font=FONT_CONSTANT_SUB, fill="#78350f",
            tags=("pinned_left", "const_label_sub", "const_sublabel"),
        )

        # Temporary Row Badges
        for row_idx, row in enumerate(rows):
            y_r_top, y_r_bot = self.coords.row_y_bounds(row_idx)
            row_badge_y = (y_r_top + y_r_bot) / 2
            row_title = f"{row.row_id}" if not row.label else f"{row.row_id} ({row.label})"

            self.canvas.create_rectangle(
                4, y_r_top + 4, self.coords.left_header_width - 4, y_r_bot - 4,
                fill="#dcfce7", outline="#86efac", width=1.5,
                tags=("pinned_left", f"row_badge_bg_{clean_tag(row.row_id)}"),
            )
            self.canvas.create_text(
                self.coords.left_header_width / 2, row_badge_y - 8,
                text=row_title, font=FONT_ROW_LABEL, fill="#166534",
                tags=("pinned_left", f"row_badge_title_{clean_tag(row.row_id)}"),
            )
            self.canvas.create_text(
                self.coords.left_header_width / 2, row_badge_y + 10,
                text=f"{len(row)} event(s) on Master Timeline", font=FONT_ROW_SUB, fill="#15803d",
                tags=("pinned_left", f"row_badge_sub_{clean_tag(row.row_id)}"),
            )

        self._update_pinned_headers()
        if self._playback_cursor_ms is not None:
            # Re-apply the transport's own exact-timing membership, not an integer re-derivation.
            self.set_playback_cursor(self._playback_cursor_ms, self._playback_explicit_ids, auto_scroll=False)
