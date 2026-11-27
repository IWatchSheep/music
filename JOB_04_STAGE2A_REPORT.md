# JOB-04 Stage 2a: Input Handling, Timing Preservation, Diagnostics and Verification

**Authorization:** ChatGPT's independent baseline audit ("JOB-04 baseline accepted. Stage 2a … recommended for implementation").
**Scope:** corrections to the existing boundary-candidate engine only. **No recurrence discovery** (that is Stage 2b, not started). No row assignment, column fitting, merger, Row 1 transfer or graph work. No JOB-05.
**Protected checkpoint:** `e1a11e7d5b03a44621f177e8bce5aa504d726334`. No JOB-03 playback code was modified, and nothing was staged, committed or pushed.

---

## 1. What changed

| File | Change |
|---|---|
| `music_model/group_discovery.py` (experimental, untracked) | Corrected input contract, timing, diagnostics and evaluation controls (§2). Public functions keep their names and parameters; the new result fields are additive, with defaults. |
| `tests/test_group_discovery_stage2a.py` (new) | 16 regression tests. **All 16 fail on the pre-Stage-2a engine** (§3). |
| `tests/test_group_discovery.py` | **Unchanged.** All 15 original methods pass, so no test contradicted the corrected semantics. |
| `verify_group_discovery.py` (experimental, untracked) | The hard-coded summary is replaced by computed values plus **22 asserted expectations**. Exit 1 on any failure. A mutation check proves the assertions bite (§5). |
| `job04_investigation/defect_probes.py` | P02 and P09 now record a raised rejection as the corrected outcome. P11's baseline check (`isinstance(float)`) could never fail, so it now tests for per-row boundaries. The baseline version is preserved as evidence. |
| `README.md` | The authorized **factual correction** of Milestone 5A, Passage 1 (one line; the old values are kept in a note) (§7). Nothing else changed. |

### Semantic changes in the existing API (intended, documented)
- **`extract_note_timing`:**
  - returns pitch as given (a fractional pitch is kept), or **None** for an unpitched note (formerly a fabricated 60);
  - raises `AmbiguousTimingError` for tick-only timing (formerly ticks were taken as ms).

  No caller outside the engine exists (checked by grep).
- **Sifters reject malformed or non-finite timing** (`NoteTimingError`) instead of computing with it. `diagnose_passage_timing` still counts malformed notes without raising.
- **Sifter A:** a rest is now an interval with *no* sounding note (running maximum end). Every member-delimited group ends at its **latest** note end.
- **Sifter C:**
  - polyphonic rows are no longer given an invented melodic order; they are reported instead;
  - unpitched notes break the pitched sequence.
- **Monte Carlo baseline:** `internal_only=True` now **requires** `passage_span_ms` (formerly a silent `(0, 1000)` default).

---

## 2. Disposition of the 14 baseline findings

| ID | Finding | Classification | Disposition | Evidence after Stage 2a |
|---|---|---|---|---|
| P01 | A missing pitch silently becomes 60 | **Defect** | Fixed: `pitch=None`, `pitch_source="none"`; never invented | NOT CONFIRMED; `test_p01_*` |
| P02 | MIDI ticks taken as milliseconds | **Defect** | Fixed: `AmbiguousTimingError` (convert with the tempo map first) | NOT CONFIRMED (rejected); `test_p02_*` |
| P03 | Fractional pitch rounded | **Defect** (information loss) | Fixed: pitch kept as given | NOT CONFIRMED; `test_p03_*` |
| P04 | Exact rational timing ignored | **Defect** | Fixed: `get_authoritative_exact_timing` used for SoundEvents. Provenance is recorded (`musicxml_exact_rational` / `audio_exact_rational` / `integer_ms_fallback` / `ms_field`). Groups carry `exact_start_ms` / `exact_end_ms` (Fraction). | NOT CONFIRMED; `test_p04_*`, `test_integer_fallback_*` |
| P05 | Sifter A false rest under a sustained note; group end truncated | **Defect** | Fixed: running maximum end, for both the gap and the group end. The diagnostics' silence uses the same rule. | NOT CONFIRMED; `test_p05_*` |
| P06 | Sifter B tries only 200/300/400 ms | **Methodological limitation** (legacy experiment) | Retained. The spans were already configurable (`candidate_spans_ms`); documented. | still CONFIRMED (by design) |
| P07 | Sifter B outputs equal-width grid slices | **Scope issue** | Retained as a labelled **periodic-grid experiment** (`segmentation_kind="periodic_grid_experiment"`). It must not become the structure of recurrence discoveries. | still CONFIRMED (by design); `test_periodic_grid_*` |
| P08 | Sifter D over-segments dense polyphony | **Methodological limitation** | Retained and documented in the docstring | still CONFIRMED (by design) |
| P09 | Silent `(0, 1000)` span default | **Defect** | Fixed: `ValueError` when the span is missing for internal evaluation | NOT CONFIRMED (rejected); `test_p09_*` |
| P10 | "specificity" is not a true-negative rate; F1 = 1 for empty versus empty | **Methodological limitation / compatibility** | Clarified. The legacy fields are kept (an original test asserts F1 = 1.0 for empty versus empty). New fields: `zero_false_positives`, `empty_reference`, `vacuous`. | still CONFIRMED (legacy values kept, now flagged); `test_p10_*` |
| P11 | Row attribution lost in the boundary union | **Defect** (transparency) | Fixed additively: `boundaries_by_row`, `silence_intervals_by_row`, per-group `event_ids` / `event_indices` | NOT CONFIRMED; `test_p11_*`, `test_event_identity_*` |
| P12 | Every result derives Row 1 segments | **Scope issue** | Retained for **legacy compatibility only**: docstring-labelled, not extended, not used by future recurrence discovery. Mean pitch now uses pitched notes only (NaN if none). | still CONFIRMED (by design) |
| P13 | Verification script: hard-coded results, no assertions, always exit 0 | **Defect** (evidence) | Fixed: computed summary, 22 asserted expectations, exit 1 on failure | NOT CONFIRMED; mutation check |
| P14 | `height=None` (unpitched WAV event) crashes every sifter | **Defect** | Fixed: treated as unpitched. Time-based methods include it; Sifter C breaks its pitched sequence at it. Counted in `unpitched_notes_count`. | NOT CONFIRMED; `test_p14_*`, `test_unpitched_event_breaks_*` |

**Totals:**
- 9 defects fixed (P01, P02, P03, P04, P05, P09, P11, P13, P14).
- 2 methodological limitations retained and documented (P06, P08).
- 1 compatibility/methodological item clarified without changing legacy values (P10).
- 2 scope issues retained as labelled legacy or comparison behaviour (P07, P12).

---

## 3. Negative baseline

`tests/test_group_discovery_stage2a.py` was run against the **pre-Stage-2a** engine (SHA-256 `baa07247f1a4…`, the backup copy): **16 run, 5 failures, 11 errors, exit 1** (`evidence/stage2a/negative_baseline_stage2a_tests_on_OLD_engine.txt`).
- The 11 errors include tests of new API names (for example `normalize_note` and the new result fields). For those, the baseline failure is the missing capability itself.
- The 5 failures are behavioural on existing API:
  - the false rest;
  - the overlapping group end;
  - contour computed across an unpitched note;
  - invented polyphonic order;
  - the silent span default.

**Probes, before and after:**
- The revised probe script on the **old** engine: **14/14 confirmed**.
- On the **corrected** engine: **5/14 confirmed** (P06, P07, P08, P10, P12, all retained by design), 0 probe errors.
- Logs: `defect_probes_revised_on_OLD_engine.txt` and `defect_probes_AFTER.txt`. The original baseline run is `evidence/defect_probes_output.txt`.

---

## 4. Effect on results

**Development set (13 frozen passages), corrected engine:** **0 metric differences** from the baseline for every method and passage (`baseline_validation_AFTER.txt`; the before-JSON is preserved).
- The passages are monophonic with exact ms timing, so the corrections do not alter them.
- Recurrence relations reported: still **0/8**. The engine still has no recurrence output; that is Stage 2b.

**Legacy benchmark passages** (`verify_group_discovery.py`), before and after Stage 2a:

| Item | Before | After | Cause |
|---|---|---|---|
| Passage 1, Sifter C, internal | 11 discovered, TP 3, F1 0.400 | **10 discovered, TP 3, F1 0.429** | Track 4 ("High Trumpets") is polyphonic, so contour is no longer computed on an invented order |
| Passage 1, Sifter C, total coverage | 13 discovered, F1 0.526 | 12 discovered, F1 0.556 | same |
| Passage 1, diagnostics, silence intervals | 5 (including a false [1800, 2400) under a sustained note) | **4** | running-maximum silence |
| Passage 1, Sifter A, legacy Row 1 segments (display only) | mean pitch 39.5 / 44.7 / …; segment 6 had 1 active row | 42.5 / 45.0 / …; segment 6 has 2 active rows | group membership and end now use the latest end |
| All other method/passage values | — | unchanged | — |

---

## 5. Verification script (P13)

`python verify_group_discovery.py` gives **22/22 expectation checks passed, exit 0** (`verify_group_discovery_AFTER.txt`). The expectations cover:
- Passage 1, Sifter B: TP=2, FP=1, FN=2 (precision 2/3, recall 1/2, F1 4/7);
- Passage 1, Sifter C: 10 discovered, TP 3;
- Passage 1: polyphonic rows reported;
- Passage 2, Sifter A: P=R=F1=1. This is noted as following from references defined at rests;
- the Passage 3 negative control: 0 false positives for A–D, and 3 for the fixed-width control;
- the Passage 2 legacy 0.50u segment;
- for every sifter and passage, the union of `boundaries_by_row` equals `discovered_boundaries_ms`.

These pin regression behaviour; they are not proof of discovery.

**Mutation check.** A scratch copy with the fixed-width control changed from 400 to 300 ms gives "21/22 … VERIFICATION FAILED", **exit 1** (`verify_mutation_check.txt`).

---

## 6. Regression (JOB-22)

The full run after Stage 2a is in §9. The JOB-03 acceptance requirements A01–A22 are unchanged and pass.

---

## 7. README factual correction (authorized for local preparation; not published)

Line 595, Milestone 5A, Passage 1. Only this line changed; it keeps the previous values in a note:

| | Previously stated | Corrected (computed by the legacy script) |
|---|---|---|
| Internal references | N = 6 | **N = 4** (6 including passage edges) |
| Sifter B precision / recall | 50.0% / 66.7% | **66.7% / 50.0%** |
| Random baseline | 0.125 ± 0.119 | **0.089 ± 0.150** |

Notes:
- **Unchanged:** Passage 2's figures (0.217 ± 0.158) were already correct, and the Passage 3 statements are accurate. Author statements, job statuses and music.txt are unchanged.
- **Historical evidence preserved:** the pre-correction README is preserved, and the baseline verification output that shows the discrepancy is kept.
- **The README describes the Milestone 5A prototype's results.** Stage 2a's changed values (§4) are recorded here, not in README.

---

## 8. Open items for Stage 2b (not started; requires review)

Stage 2b will add `discover_sound_groups()` with recurrence clusters under the approved decisions:
- **Minimum phrase length:** 3 notes, configurable.
- **Timing:** exact timing first. Exact, proportional and tolerance-based rhythm are kept separate.
- **Transposition:** linked identities, with the interval preserved.
- **Input:** monophonic streams; polyphony is reported, not reordered.

It is evaluated on the frozen development set, then on ChatGPT's held-out set, with these counting rules:
- separate relation types;
- intended phrases versus all matching subsequences;
- maximal versus nested repeats;
- documented surrogate assumptions.

The Stage 2a contract (normalized notes, exact timing, provenance, identity and per-row indices) is the input layer Stage 2b will use.

---

## 9. Full regression run after Stage 2a

Command: `python acceptance/run_acceptance.py --windows-device` on the complete local project, Windows, CPython 3.15.2, 2026-11-27 05:39 UTC. The exit codes are the child Python processes' own (`stage2a_acceptance_run.txt`).

| Step | Result |
|---|---|
| Suite | **309 run, 295 passed, 14 skipped**, 0 failures or errors (exit 0). This is the 293-test baseline plus the 16 Stage 2a tests. The 14 skips are the gated device tests, not failures. |
| Real Windows device | 14/14 (exit 0) |
| 7 required scripts | all exit 0 |
| Optional `verify_group_discovery.py` (present) | exit 0 (22/22 expectation checks) |
| Optional `verify_row_merger.py` (present) | exit 0 |
| Requirements | JOB-03 A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE; A21 regression only |
| Runner | **exit 0** |

**Native access violation:** it did not occur in this run. One run without a crash says nothing about the intermittent fault (Stage 1 §2.1: 1 of 2 identical runs crashed). It remains **unresolved**; there were no automatic retries.

### Commands and exit codes (this stage)

| Command | Exit code |
|---|---|
| `python -m unittest tests.test_group_discovery_stage2a` on the **old** engine (negative baseline) | 1 (16 run, 5 failures, 11 errors) |
| `python -m unittest tests.test_group_discovery tests.test_group_discovery_stage2a` | 0 (31 run) |
| `python verify_group_discovery.py` | 0 (22/22) |
| Mutated copy of `verify_group_discovery.py` | **1** (21/22) |
| `python job04_investigation/defect_probes.py`, old engine / corrected engine | 0 / 0 (14/14 versus 5/14 confirmed) |
| `python job04_investigation/run_baseline_validation.py` | 0 (0 metric differences) |
| `python acceptance/run_acceptance.py --windows-device` | 0 |
