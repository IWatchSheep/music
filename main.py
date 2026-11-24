"""Main application entry point for the Music Project.

Launches the Stage 2 Tkinter GUI displaying temporary sound rows,
linked variable-width time columns, and the calculated constant musical row.
"""

from __future__ import annotations

import sys
from music_gui.main_window import MusicGUI


def main() -> int:
    """Run the Music Timeline Explorer GUI application."""
    app = MusicGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
