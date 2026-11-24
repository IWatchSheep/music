"""Visual styling, color themes, and font configurations for the Music GUI.

Provides a clean, distinct, Excel-inspired palette adapted for musical timelines:
- Subtle neutral backgrounds for timeline grid and headers.
- Distinct vibrant pastel colors for sound event bars.
- Prominent warm amber theme for the calculated constant musical row.
"""

from __future__ import annotations

# General application colors
BG_WINDOW = "#f1f5f9"          # Slate 100
BG_TOOLBAR = "#ffffff"         # Pure white toolbar
BG_CANVAS = "#f8fafc"          # Slate 50 canvas workspace
BORDER_DEFAULT = "#cbd5e1"     # Slate 300
BORDER_DARK = "#94a3b8"        # Slate 400

# Timeline header (top)
BG_HEADER = "#e2e8f0"          # Slate 200
FG_HEADER = "#1e293b"          # Slate 800
FG_HEADER_SUB = "#64748b"      # Slate 500
BORDER_HEADER = "#cbd5e1"

# Column boundary vertical grid guidelines
GRID_LINE_COLOR = "#cbd5e1"    # Dotted or solid line separating columns
GRID_LINE_DASH = (3, 3)

# Temporary Row Lanes
BG_ROW_EVEN = "#ffffff"
BG_ROW_ODD = "#f8fafc"
BG_ROW_LABEL = "#dcfce7"       # Green 100 badge
BORDER_ROW_LABEL = "#86efac"   # Green 300 border
FG_ROW_LABEL = "#166534"       # Green 800 text

# Sound Event Color Palette (Fill, Border, Text)
SOUND_COLORS = [
    ("#93c5fd", "#2563eb", "#1e3a8a"),  # 0: Sky Blue
    ("#86efac", "#16a34a", "#14532d"),  # 1: Spring Green
    ("#fcd34d", "#d97706", "#78350f"),  # 2: Warm Amber
    ("#c4b5fd", "#7c3aed", "#4c1d95"),  # 3: Violet
    ("#fca5a5", "#dc2626", "#7f1d1d"),  # 4: Rose
    ("#6ee7b7", "#0d9488", "#134e4a"),  # 5: Mint Teal
    ("#fdba74", "#ea580c", "#7c2d12"),  # 6: Coral Orange
]

# Constant Row Theme (bottom)
BG_CONSTANT_ROW = "#fffbeb"          # Amber 50
BG_CONSTANT_LABEL = "#fef3c7"        # Amber 100 badge
BORDER_CONSTANT_LABEL = "#f59e0b"    # Amber 500
FG_CONSTANT_LABEL = "#92400e"        # Amber 800
BG_CONSTANT_CELL = "#ffffff"         # White box inside constant row
BORDER_CONSTANT_CELL = "#d97706"     # Amber 600 border
FG_CONSTANT_VAL = "#b45309"          # Amber 700 bold number

# Fonts
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_TOOLBAR = ("Segoe UI", 9)
FONT_TOOLBAR_BOLD = ("Segoe UI", 9, "bold")
FONT_HEADER = ("Segoe UI", 9, "bold")
FONT_HEADER_SUB = ("Segoe UI", 8)
FONT_ROW_LABEL = ("Segoe UI", 9, "bold")
FONT_ROW_SUB = ("Segoe UI", 7)
FONT_EVENT_TITLE = ("Segoe UI", 9, "bold")
FONT_EVENT_SUB = ("Segoe UI", 8)
FONT_CONSTANT_LABEL = ("Segoe UI", 9, "bold")
FONT_CONSTANT_SUB = ("Segoe UI", 8)
FONT_CONSTANT_VAL = ("Segoe UI", 13, "bold")
FONT_STATUS = ("Segoe UI", 8)
