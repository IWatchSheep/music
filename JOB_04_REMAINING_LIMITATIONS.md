# JOB-04 Remaining Limitations (2026-11-27, revision 2)

These are preserved as documented. None is claimed to be fixed by the publication package.

JOB-04's accepted results establish **tested mathematical relation correctness in the symbolic domain**: on controlled passages, the reported families are exactly the window pairs that satisfy each method's relation. They do **not** establish that a reported family is a musically significant phrase. **No universal musical recognition is claimed.**

## Scope of the recurrence engine (`discover_sound_groups()`)

1. **Exact-only matching.** Every method compares exact values (`Fraction` timing; exact pitch keys). There is no tolerance, so:
   - a difference of 10⁻²⁰ ms or 10⁻²⁰ semitone breaks a match (held-out cases `near_pitch` and `near_timing`);
   - performed or transcribed music with timing jitter, including WAV-derived integer-ms timing, will rarely match.

   Tolerance-based or quantized matching would have to be a separately configured and separately evaluated method. None is implemented.
2. **Ambiguous polyphony is unsupported.** A stream without voice information whose notes overlap is reported as `polyphonic_unsupported`, and its events are listed in `exclusions`. No order is invented and no voice separation is implemented.
   - Explicit voices form separate monophonic streams.
   - In the held-out case `ambiguous_chord`, two simultaneous copies of a phrase give no families, by design.
3. **Contour is weak evidence.**
   - Shuffled surrogates give contour counts at chance level.
   - Passages constructed to contain no recurrence still give contour families (5 and 3 in the development set; 1 in the held-out `negative` case). These are valid two-direction contour matches, not defects.
   - Short rhythm patterns also recur by chance.
4. **Nested and incidental relationships are reported, not resolved.**
   - A maximal repeat may be longer than the intended phrase. In "X Y X Y", the maximal exact repeat is "X Y", and X and Y appear only as nested families.
   - Stricter relations also satisfy weaker methods: an exact repeat is also a rhythm and a contour family. These are reported as implied, never as independent confirmations.
   - Windows that straddle phrase edges produce valid rhythm and contour matches that are not intended phrases.

   Deciding which level is "the phrase" is a musical judgement outside this method.
5. **Cubic search performance.** The worst case is O(L³) in the stream length L. Measured (Stage 2b report §7):
   - random input: 10 s at L = 200 and 81 s at L = 400;
   - identical notes: 16 s at L = 200.

   The publication-preparation run measured 83 s and 25 s for the same inputs. Wall-clock time varies between runs. See `JOB_04_VERIFICATION_LOG.txt` §4.

   A linear-time repeat structure (for example a suffix automaton) is a possible future optimization. It is not implemented.
6. **Configured search limits.** `min_length` (default 3), `min_occurrences` (default 2), `max_length` and `max_windows` (default 500 000 per method) bound the search.
   - A search stopped by `max_windows` stops at a whole length, sets `search_complete=False`, and reports the unsearched lengths. It never truncates silently.
   - `search_complete` means complete **within the configured bounds**. `unrestricted_search_complete` additionally requires that `max_length` excluded nothing.
   - Results outside the configured bounds are not reported.
7. **Generated identities are not persistent.** Anonymous events receive generated keys that are stable under input reordering, but they are not persistent identities across edits of the passage. Duplicate supplied ids are disambiguated by default (`#dupK`), with the originals kept in `supplied_event_id`.
8. **Unpitched notes** break every pitch-based method (exact, transposition, contour, interval_only). Only the rhythm methods can match across them.

## Validation scope

9. **General musical phrase significance is unverified.**
   - The development set has 13 constructed passages, and the independent held-out set has 17.
   - Both are controlled symbolic passages. They are not a corpus of real music with expert phrase annotations.
   - Shuffled-surrogate comparisons are descriptive. No statistical-significance claim is made.
10. **Test-coverage gap found and closed** (publication preparation; the engine itself was correct and is unchanged).
    - A sensitivity check injected six faults into scratch copies of `recurrence_discovery.py`. The held-out verifier detected 5 of the 6.
    - The undetected one made the `transposition` signature ignore inter-onset intervals. It passed both the held-out verifier and the 79 JOB-04 tests. ChatGPT independently reproduced this.
    - **Closed by the authorized test** `tests/test_group_discovery_stage2c_coverage.py` (1 test).
      - Input: two 3-note phrases with equal durations and intervals (+2, +2), but onset gaps (1, 1) versus (3, 3).
      - It asserts no `exact` and no strict `transposition` family, and exactly one `interval_only` family at `[0, 3)` and `[3, 6)`.
      - It passes on the correct engine and fails on that mutant (`JOB_04_VERIFICATION_LOG.txt` §5.3).
    - **What remains:** the 80 tests and the held-out verifier are finite. A mutation check is evidence of sensitivity to the faults tried, not proof that every fault is detected.
11. **Real recordings were evaluated qualitatively only.** The one real MIDI passage (the legacy calibration passage) has no ground truth. Two of its four tracks are excluded as polyphonic.

## Legacy boundary sifters A–D (retained as regression evidence)

The 15 original tests and `verify_group_discovery.py` are preserved as **regression evidence, not proof of general discovery**. Stage 2a corrected the input handling. These behaviours remain, as recorded by `job04_investigation/defect_probes.py` (5 of 14 probes confirmed, all retained by design):

| Probe | Retained behaviour |
|---|---|
| P06 | Sifter B tests only three hard-coded spans (300, 400 and 200 ms); a clean 500 ms periodic pattern is reported as non-repeating. |
| P07 | Sifter B output is a periodic grid of equal-width slices, not musically delimited groups. |
| P08 | Sifter D in dense two-row polyphony places a boundary between almost every pair of notes. |
| P10 | The legacy `specificity` is defined by "no false positive" rather than a true-negative rate, and F1 = 1.0 is reported when nothing exists and nothing is found. This is labelled explicitly. |
| P12 | Every sifter result also derives Row 1 segments, which belongs to later jobs. Neither the recurrence engine nor its results use that derivation. |

## Not part of JOB-04 (protected boundaries)

- Row assignment, column fitting, row merging, Row 1 transfer and graph classification are **not** implemented. `verify_row_merger.py` is an unpublished experiment outside the publication boundary.
- JOB-05 (phrase boundaries and pauses) has not been started.

## Inherited JOB-03 limitations (unchanged)

- **A20:** physical acoustic synchronization remains **unmeasured**.
- **A21:** the native access violation remains **unresolved**; the tests provide regression detection only.
  - **It recurred during JOB-04** (2026-11-27 05:22 UTC, baseline stage): two child processes of one acceptance run of an extracted archive ended with 0xC0000005. The faulting frames were in `music_gui/audio_playback.py` (`synthesize_song_audio`) and `music_model/audio_importer.py` (`_estimate_pitch_autocorrelation`). No JOB-04 code was on either stack.
  - An immediate repeat run of the same tree passed (`JOB_04_BASELINE_INVESTIGATION.md` §2.1–2.2).
  - **It recurred again during publication preparation** (2026-11-27, about 10:12 UTC).
    - The process was `python job04_investigation/run_stage2b_evaluation.py`, running on a scratch copy of the publication tree. It ended with an access violation (reported by Git Bash as exit 139), while printing `Traceback (most recent call last):`.
    - That process runs only pure-Python JOB-04 harness and engine code (`Fraction` arithmetic and seeded shuffles), with no audio, MCI or Tk.
    - `faulthandler` was not enabled in that run, so no faulting frame is available.
    - One deliberate repeat with `-X faulthandler` passed 44/44 (exit 0). See `JOB_04_VERIFICATION_LOG.txt` §4.
    - **[FACT]** This failure, during pure-Python evaluation, shows that the observed problem is **not confined to GUI or audio execution**.
    - **Its underlying cause remains unresolved.** It is not attributed to Python, to hardware or to drivers.
    - No system-level change was made.
  - **Preserved as separate evidence** (outside the repository; SHA-256 in `JOB_04_VERIFICATION_LOG.txt` §4):
    - `%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\run1_CRASHED_stage2b_evaluation.txt`;
    - `%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\run2_PASSED_stage2b_evaluation.txt`.

    The failure is not hidden by the later successful run.
  - **It recurred a fourth time, in the first R2 acceptance run** (2026-11-27, run started 10:34:36 UTC, on the R2 publication tree).
    - `verify_audio_and_sheet_adapters.py` (JOB-02 code) ended with exit code 3221225477 (0xC0000005).
    - `faulthandler` gave `music_model/audio_importer.py` line 437 (`_estimate_pitch_autocorrelation`, generator expression), the same frame as the 05:22 UTC occurrence. No JOB-04 code was on the stack.
    - **The runner correctly reported ACCEPTANCE CHECKS FAILED (exit 1).** A02, A03, A19 and A22 FAILED because they map that script.
    - Everything else in that run passed: the suite (358 run, 344 passed, 14 skipped, 0 failures), the device tests (14/14), the other 8 required scripts, and G01–G08.
    - The complete run is preserved as separate evidence: `%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\r2_acceptance_run_FAILED_20261127T103436Z\`.
    - There was no automatic retry. The subsequent planned confirmation run on the final tree is recorded separately (`JOB_04_VERIFICATION_LOG.txt` §11 and §13; manifest §3).
  - Its absence from other runs does not establish elimination. There were no automatic retries.

See `JOB_03_REMAINING_LIMITATIONS.md`.
