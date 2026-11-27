"""JOB-04 Stage 2b: performance and complexity observations for discover_sound_groups().

Run from the project root:  python job04_investigation/run_stage2b_performance.py
Exit code 0 when the measurements completed (timings are observations, not pass/fail); 2 on error.

Inputs (seeded): random monophonic melodies (pitch steps from a small set, durations from 4 values) of
L notes, and a worst case of L identical notes (every window of every length matches every other).
Windows examined per method: sum over lengths n = min_length .. L of (L - n + 1) = O(L^2); building a
signature costs O(n), so the search is O(L^3) per method in the worst case, plus nesting checks that are
linear in the number of occurrences.  Timings are wall-clock on this machine, single run each.
"""

from __future__ import annotations

import os
import random
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from music_model.group_discovery import discover_sound_groups   # noqa: E402
from job04_investigation.fixtures import Note                     # noqa: E402

METHODS = ("exact", "transposition", "rhythm", "contour")


def random_melody(L, seed):
    rng = random.Random(seed)
    t, p, out = 0, 60, []
    for k in range(L):
        d = rng.choice([125, 250, 375, 500])
        out.append(Note(t, t + d, p, f"P{p}", f"n{k}"))
        t += d
        p = max(36, min(96, p + rng.choice([-4, -2, -1, 1, 2, 3, 5])))
    return out


def identical(L):
    return [Note(250 * k, 250 * k + 250, 60, "P60", f"n{k}") for k in range(L)]


def main() -> int:
    print(f"{'input':<24}{'L':>5}{'seconds':>9}{'windows/method':>16}{'families':>10}{'maximal':>9}{'complete':>9}")
    for kind, L in [("random", 50), ("random", 100), ("random", 200), ("random", 400),
                    ("identical", 50), ("identical", 100), ("identical", 200)]:
        notes = random_melody(L, 1000 + L) if kind == "random" else identical(L)
        t0 = time.perf_counter()
        r = discover_sound_groups({"m": notes}, methods=METHODS)
        dt = time.perf_counter() - t0
        w = dict(r.windows_examined)["exact"]
        print(f"{kind:<24}{L:>5}{dt:>9.2f}{w:>16}{len(r.all_families):>10}{sum(f.is_maximal for f in r.all_families):>9}"
              f"{str(r.search_complete):>9}")
    t0 = time.perf_counter()
    r = discover_sound_groups({"m": identical(400)}, methods=("exact",), max_windows=20_000)
    print(f"{'identical, max_windows=20000':<24}{400:>5}{time.perf_counter() - t0:>9.2f}{dict(r.windows_examined)['exact']:>16}"
          f"{len(r.all_families):>10}{sum(f.is_maximal for f in r.all_families):>9}{str(r.search_complete):>9}")
    print("search notes:", r.search_notes)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
