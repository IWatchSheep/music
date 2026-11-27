# JOB-03 / JOB-04 Independent Acceptance Package

One runner covers JOB-03 (requirements A01–A22) and JOB-04 (requirements G01–G09).

## One command

From the extracted archive root (the folder that contains `main.py`):

| Platform | Command |
|---|---|
| Windows (platform-independent checks) | `python acceptance/run_acceptance.py` |
| Windows, plus the real MCI device tests | `python acceptance/run_acceptance.py --windows-device` |
| Linux / macOS with a display | `python3 acceptance/run_acceptance.py` |
| Linux without a display | `xvfb-run -a python3 acceptance/run_acceptance.py` |

The runner's own exit code is:
- **0**: every acceptance check passed;
- **1**: something failed or is incomplete;
- **2**: the runner itself failed.

It writes `acceptance_results/<UTC timestamp>/` containing:
- `report.md` (the coverage matrix with this run's statuses);
- `report.json`;
- one log per step.

## Dependencies

- Python 3.10 or newer, standard library only (see `requirements.txt`). Verified with CPython 3.15.2 on Windows. ChatGPT's independent runs used CPython 3.13.5 on Linux.
- Tkinter with Tcl/Tk. On Debian/Ubuntu: `apt install python3-tk xvfb`.
- No network and no third-party packages.
- The real device tests need Windows with a working audio output (`winmm.dll`). They play mostly **silent** audio.

## What it runs

Every step runs in its own child process, and its own Python exit code is recorded.

1. **The complete regression suite** (`python -m unittest discover -s tests -t .`), through `acceptance/unittest_json.py`, which records the result of each test.
   - `MUSIC_REAL_AUDIO_TESTS` is removed for this step, so the gated device tests skip and stay separately identifiable.
   - `TestD8GuiTeardownReleasesItsOwnTempWav` self-skips when no Windows MCI device is present.
2. **Only with `--windows-device` on Windows:** `tests.test_playback_windows_device` with `MUSIC_REAL_AUDIO_TESTS=1`.
3. **The standalone verification scripts.**
   - The **nine required** scripts always run. A missing or failing required script fails acceptance.
     - JOB-01 to JOB-03: `verify_audio_and_sheet_adapters.py`, `verify_development.py`, `verify_group_units.py`, `verify_midi_import.py`, `verify_playback_transport.py`, `verify_progressive.py` and `verify_proof.py`.
     - JOB-04: `verify_group_discovery.py`, and `job04_investigation/job04_heldout_audit.py`, the independent held-out verifier supplied by ChatGPT (kept byte-identical; it exits non-zero if any of its 886 checks fails).
   - Every script runs with the project root prepended to `PYTHONPATH`. The held-out verifier lives in a subfolder and imports `music_model`, so it needs this.
   - The **one unpublished experimental** script, `verify_row_merger.py`, is outside the publication boundary. It runs only when present; a present one that fails still fails acceptance. When absent, it is reported as `OUTSIDE PUBLICATION SCOPE (absent)`.
4. **The matrix evaluation.** Each requirement in `acceptance/acceptance_matrix.json` is evaluated from the per-test results.
   - A test id that does not exist is a matrix error, which fails the run.
   - Any skip other than the device tests fails the run.

## Status vocabulary

| Status | Meaning |
|---|---|
| PASS | Every mapped platform-independent test passed, and every mapped script exited 0 |
| FAIL | A mapped test failed, errored or is missing, or a script exited non-zero |
| INCOMPLETE | A mapped platform-independent test was skipped here |
| NO-AUTOMATED-COVERAGE | A physical or unresolved item; see "Remaining unverified" |
| PASS (regression only…) | The automated part passed, but the requirement itself stays unverified or unresolved |

The Windows device column shows PASS, FAIL or PARTIAL when the device tests ran. Otherwise it shows **NOT RUN HERE**, together with the recorded Windows evidence.

## Fixtures

- `tests/fixtures/JOB03_test.wav`: the Author's controlled file, byte-identical to the original. SHA-256 `defffd2a0178fb1cd4d0002d2901afc42169782f38966b4b467bbc4232149c70`, verified by a test.
- All other audio fixtures are generated deterministically in code (`tests/test_wav_import_regression.py`: `author_equivalent_wav`, `gapped_wav`, `FOUR_NOTE_MUSICXML`).

## JOB-04 requirements (G01–G09)

| ID | Covers |
|---|---|
| G01 | The original 15 group-discovery tests and `verify_group_discovery.py` (regression evidence, not proof of general discovery) |
| G02 | The 16 Stage 2a input-correction tests |
| G03 | The six exact candidate relations, exact rational timing, nesting, and the Stage 2c coverage test (strict transposition compares inter-onset intervals); plus the held-out verifier |
| G04 | Occurrence identities, original-event references and unique identifiers; plus the held-out verifier |
| G05 | Ambiguity and limits reported (polyphony, unpitched notes, overlaps, search limits, configuration) |
| G06 | Input-order determinism; plus the held-out verifier |
| G07 | The independent held-out controlled validation (886 checks) |
| G08 | The comparison controls (fixed-width and seeded random baselines) |
| G09 | Documentation of candidate algorithms and limitations: `NO-AUTOMATED-COVERAGE`, by design (reviewed, not tested) |

Together G01–G08 map all 80 JOB-04 tests: the 79 reviewed earlier, plus `tests/test_group_discovery_stage2c_coverage.py` (1 test). The JOB-04 research harness in `job04_investigation/` (development evaluation, baseline validation, defect probes, performance) is **not** run by this runner, because it writes generated results into `job04_investigation/results/`. Its commands and recorded exit codes are in `JOB_04_VERIFICATION_LOG.txt`.

JOB-04 results establish tested mathematical relation correctness on controlled symbolic passages. They do **not** establish general musical phrase significance.

## Interpreting timing

Numbers printed with `[measure]` come from software or the driver: the Tk loop gap, the simulated clock and MCI positions. **None of them is an acoustic measurement.** Synchronization as heard is listed as unverified (requirement A20).

## Runtime

About 4–6 minutes on the Author's Windows machine, including about 30 s per analysis of the actual 4 s WAV. The device tests add about 25 s. The JOB-04 tests and scripts add a few seconds.
