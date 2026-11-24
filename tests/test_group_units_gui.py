"""Automated GUI test suite for Milestone 4B: Statement 18 Fundamental Column Units.

Verifies:
1. Interactive display of uniform fundamental cells (u = 100 ms) with cyclic 0-9 labels.
2. Multi-unit sound group rendering (Row 2: 4-unit groups, Row 3: 3-unit groups).
3. Row 1 composite boundary segments (widths: 3, 1, 2, 2, 1, 3 units).
4. Low-to-high pitch development curve nodes horizontally centered within composite segments.
5. Interactive toggling between Ascending Takeoff (48 -> 66) and Flat Control (49 steady).
6. Meeting point boundary markers and subtle vertical highlight lines.
7. Two-song independence toggle (Song 1: 12 cells, 100 ms vs Song 2: 10 cells, 250 ms).
8. Responsive horizontal zoom controls (Zoom In, Zoom Out, Reset) in groups mode.
9. Clean mode transitions between Statement 18 and standard timeline modes.
"""

from __future__ import annotations

import unittest

from music_gui.main_window import MusicGUI


class TestGroupUnitsGUI(unittest.TestCase):
    """Test suite for Milestone 4B Statement 18 GUI visualization."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = MusicGUI()
        cls.app.update_idletasks()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.destroy()

    def setUp(self) -> None:
        # Reset to Ascending Takeoff mode on Song 1 for each test
        self.app.show_groups_mode("ascending", "song1")
        self.app.update_idletasks()

    def test_01_gui_opens_groups_mode(self) -> None:
        """Verify GUI cleanly switches to Statement 18 Fundamental Groups view mode."""
        self.assertEqual(self.app.current_view_mode, "groups")
        self.assertIsNotNone(self.app.timeline_view.group_timeline)
        self.assertEqual(self.app.timeline_view.group_passage_mode, "ascending")
        self.assertIn("Statement 18", self.app.lbl_dataset.cget("text"))

    def test_02_fundamental_grid_cells_rendered(self) -> None:
        """Verify 12 uniform cells are rendered with cyclic 0-9 labels and equal widths."""
        headers = self.app.timeline_view.find_group_cell_headers()
        self.assertEqual(len(headers), 12, "Should render exactly 12 fundamental cell headers")

        labels = self.app.timeline_view.find_group_cell_labels()
        self.assertEqual(len(labels), 12, "Should render exactly 12 cyclic 0-9 labels")

        expected_labels = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "1"]
        for idx, lbl_item in enumerate(labels):
            text_val = self.app.timeline_view.canvas.itemcget(lbl_item, "text")
            self.assertEqual(text_val, expected_labels[idx])

        # Verify equal cell widths of 80px
        for idx, hdr_item in enumerate(headers):
            coords = self.app.timeline_view.canvas.coords(hdr_item)
            width = coords[2] - coords[0]
            self.assertAlmostEqual(width, 80.0, places=1)

    def test_03_sound_group_box_geometry_and_counts(self) -> None:
        """Verify Row 2 (4u) and Row 3 (3u) sound groups render with exact unit spans."""
        all_boxes = self.app.timeline_view.find_group_boxes()
        self.assertEqual(len(all_boxes), 7, "Should have 3 groups in Row 2 + 4 groups in Row 3 = 7 total")

        r2_box_1 = self.app.timeline_view.find_group_boxes("R2_LowWhirr_1")
        self.assertEqual(len(r2_box_1), 1)
        coords_r2 = self.app.timeline_view.canvas.coords(r2_box_1[0])
        # 4 units * 80 px = 320 px (with 2px inner padding = 316 px)
        width_r2 = coords_r2[2] - coords_r2[0]
        self.assertAlmostEqual(width_r2, 316.0, delta=2.0)

        r3_box_a = self.app.timeline_view.find_group_boxes("R3_Flap_A")
        self.assertEqual(len(r3_box_a), 1)
        coords_r3 = self.app.timeline_view.canvas.coords(r3_box_a[0])
        # 3 units * 80 px = 240 px (with 2px inner padding = 236 px)
        width_r3 = coords_r3[2] - coords_r3[0]
        self.assertAlmostEqual(width_r3, 236.0, delta=2.0)

    def test_04_row1_composite_segments_geometry(self) -> None:
        """Verify Row 1 displays 6 composite segments with widths [3, 1, 2, 2, 1, 3] units."""
        segments = self.app.timeline_view.find_row1_segments()
        self.assertEqual(len(segments), 6, "Row 1 must have exactly 6 composite segments")

        expected_unit_widths = [3, 1, 2, 2, 1, 3]
        for idx, seg_item in enumerate(segments):
            coords = self.app.timeline_view.canvas.coords(seg_item)
            span_px = coords[2] - coords[0]
            expected_px = expected_unit_widths[idx] * 80.0
            self.assertAlmostEqual(span_px, expected_px - 4.0, delta=2.0)

    def test_05_development_trend_curve_nodes(self) -> None:
        """Verify development trend nodes are horizontally centered and rise in pitch."""
        nodes = self.app.timeline_view.find_dev_nodes()
        self.assertEqual(len(nodes), 6, "Should have 6 development nodes matching the 6 segments")

        # In Tkinter canvas coords, y increases downwards, so rising pitch means decreasing y
        y_positions = []
        x_positions = []
        for node in nodes:
            coords = self.app.timeline_view.canvas.coords(node)
            cx = (coords[0] + coords[2]) / 2.0
            cy = (coords[1] + coords[3]) / 2.0
            x_positions.append(cx)
            y_positions.append(cy)

        # Confirm horizontal progression strictly to the right
        for i in range(len(x_positions) - 1):
            self.assertGreater(x_positions[i + 1], x_positions[i])

        # Confirm strictly ascending pitch trajectory in ascending mode (decreasing y)
        for i in range(len(y_positions) - 1):
            self.assertLess(y_positions[i + 1], y_positions[i])

    def test_06_flat_control_passage_mode(self) -> None:
        """Verify Flat Control mode displays horizontal trend nodes at identical y-coordinates."""
        self.app.show_groups_mode("flat", "song1")
        self.app.update_idletasks()

        self.assertEqual(self.app.timeline_view.group_passage_mode, "flat")
        nodes = self.app.timeline_view.find_dev_nodes()
        self.assertEqual(len(nodes), 6)

        y_positions = []
        for node in nodes:
            coords = self.app.timeline_view.canvas.coords(node)
            cy = (coords[1] + coords[3]) / 2.0
            y_positions.append(cy)

        # All y-positions should be strictly equal in flat mode
        for y in y_positions:
            self.assertAlmostEqual(y, y_positions[0], places=1)

    def test_07_meeting_point_markers_and_highlight_lines(self) -> None:
        """Verify meeting markers and vertical highlight lines appear at combined boundaries."""
        markers = self.app.timeline_view.find_meeting_markers()
        # Combined boundaries for Song 1: [0, 3, 4, 6, 8, 9, 12] -> 7 markers
        self.assertEqual(len(markers), 7, "Should have meeting markers at all 7 combined boundaries")

        lines = self.app.timeline_view.find_meeting_lines()
        # Interior combined boundaries: 3, 4, 6, 8, 9 -> 5 vertical highlight lines
        self.assertEqual(len(lines), 5, "Should have 5 interior vertical highlight lines")

    def test_08_song2_independence_toggle(self) -> None:
        """Verify Song 2 displays 10 fundamental cells with u = 250 ms and independent groups."""
        self.app.show_groups_mode("ascending", "song2")
        self.app.update_idletasks()

        headers = self.app.timeline_view.find_group_cell_headers()
        self.assertEqual(len(headers), 10, "Song 2 must render exactly 10 fundamental cells")
        self.assertEqual(self.app.timeline_view.group_timeline.grid.u_ms, 250)

        # Song 2 Row 1 segments (5u vs 2u -> bounds [0, 2, 4, 5, 6, 8, 10] -> 6 segments)
        segments = self.app.timeline_view.find_row1_segments()
        self.assertEqual(len(segments), 6)

    def test_09_zoom_controls_in_groups_mode(self) -> None:
        """Verify horizontal zoom in, zoom out, and reset work properly in groups mode."""
        initial_w = self.app.timeline_view.group_cell_width
        self.assertEqual(initial_w, 80.0)

        self.app._on_zoom_in()
        self.app.update_idletasks()
        self.assertAlmostEqual(self.app.timeline_view.group_cell_width, 100.0)

        self.app._on_zoom_out()
        self.app.update_idletasks()
        self.assertAlmostEqual(self.app.timeline_view.group_cell_width, 80.0)

        self.app._on_zoom_in()
        self.app._on_zoom_in()
        self.app._on_zoom_reset()
        self.app.update_idletasks()
        self.assertEqual(self.app.timeline_view.group_cell_width, 80.0)

    def test_10_mode_switching_cleans_group_timeline(self) -> None:
        """Verify switching between groups mode and standard modes clears and restores group state."""
        self.assertIsNotNone(self.app.timeline_view.group_timeline)
        self.assertIn("Fundamental cells have equal width", self.app.lbl_status.cget("text"))

        # Switch to Progressive Mode
        self.app.show_progressive_mode("A")
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "progressive")
        self.assertIsNone(self.app.timeline_view.group_timeline)
        self.assertIn("Sounds dictate variable-width columns", self.app.lbl_status.cget("text"))

        # Switch back to Groups Mode
        self.app.show_groups_mode("ascending", "song1")
        self.app.update_idletasks()
        self.assertEqual(self.app.current_view_mode, "groups")
        self.assertIsNotNone(self.app.timeline_view.group_timeline)
        self.assertIn("Fundamental cells have equal width", self.app.lbl_status.cget("text"))

    def test_11_row1_no_visual_overlap_and_adaptive_text(self) -> None:
        """Verify pitch text, notes, and development line never overlap, and narrow cells adapt."""
        # Verify adaptive titles: 3u has full title, 1u has compact title
        t1 = self.app.timeline_view.canvas.itemcget(self.app.timeline_view.canvas.find_withtag("const_title_0")[0], "text")
        t2 = self.app.timeline_view.canvas.itemcget(self.app.timeline_view.canvas.find_withtag("const_title_1")[0], "text")
        self.assertIn("3u (300ms)", t1)
        self.assertEqual(t2, "Seg 2 (1u)")

        # Verify adaptive notes: 3u has full MIDI numbers, 1u has clean compact names
        n1 = self.app.timeline_view.canvas.itemcget(self.app.timeline_view.canvas.find_withtag("const_sub_0")[0], "text")
        n2 = self.app.timeline_view.canvas.itemcget(self.app.timeline_view.canvas.find_withtag("const_sub_1")[0], "text")
        self.assertIn("(36)", n1)
        self.assertEqual(n2, "C2, G4")

        # Verify vertical separation: pitch text must be strictly above the node line
        nodes = self.app.timeline_view.find_dev_nodes()
        for idx, node in enumerate(nodes):
            node_coords = self.app.timeline_view.canvas.coords(node)
            node_cy = (node_coords[1] + node_coords[3]) / 2.0

            val_items = self.app.timeline_view.canvas.find_withtag(f"const_val_{idx}")
            self.assertTrue(len(val_items) > 0)
            val_coords = self.app.timeline_view.canvas.coords(val_items[0])
            val_cy = val_coords[1]

            # Text is positioned strictly 13px above node center -> zero overlap with the trend line
            self.assertLess(val_cy, node_cy)
            self.assertAlmostEqual(node_cy - val_cy, 13.0, places=1)

    def test_12_unit_0_meeting_badge_no_clipping(self) -> None:
        """Verify Unit 0 meeting badge is clamped so its left edge is never clipped by the sidebar."""
        badge_items = self.app.timeline_view.canvas.find_withtag("meeting_label_0")
        self.assertTrue(len(badge_items) >= 2)
        rect_coords = self.app.timeline_view.canvas.coords(badge_items[0])
        # Left edge must be >= 200 (sidebar_w) so it is 100% visible
        self.assertGreaterEqual(rect_coords[0], 200.0)


if __name__ == "__main__":
    unittest.main()
