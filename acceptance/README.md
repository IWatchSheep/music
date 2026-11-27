# JOB-03 Independent Acceptance Package

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
   - The **seven required** scripts always run: `verify_audio_and_sheet_adapters.py`, `verify_development.py`, `verify_group_units.py`, `verify_midi_import.py`, `verify_playback_transport.py`, `verify_progressive.py` and `verify_proof.py`. A missing or failing required script fails acceptance.
   - The **two unpublished experimental** scripts, `verify_group_discovery.py` (JOB-04) and `verify_row_merger.py`, are outside the JOB-03 publication boundary. They run only when present; a present one that fails still fails acceptance. When absent, they are reported as `OUTSIDE PUBLICATION SCOPE (absent)`.
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

## Interpreting timing

Numbers printed with `[measure]` come from software or the driver: the Tk loop gap, the simulated clock and MCI positions. **None of them is an acoustic measurement.** Synchronization as heard is listed as unverified (requirement A20).

## Runtime

About 4–6 minutes on the Author's Windows machine, including about 30 s per analysis of the actual 4 s WAV. The device tests add about 25 s.
