# JOB-04 Baseline Investigation: Sifter Discovery Engine (First Stage)

**Job:** JOB-04, "Sifter Discovery Engine for Recurring Loops & Melodic Phrases" (README.md §8).
**Stage:** first stage, a baseline investigation only. **No production code, test or published file was changed.**
**Investigator:** Claude Opus 5.5, 2026-11-26/27.
**Starting checkpoint:** `e1a11e7d5b03a44621f177e8bce5aa504d726334` (JOB-03 published). HEAD = origin/main = that commit.

**Labels used in this report:**
- **[FACT]** means mathematically or programmatically established from source or execution.
- **[OBS]** is an experimental observation, valid only for the inputs tested.
- **[HYP]** is a hypothesis, written in the Author's convention as "I guess …".

---

## 1. Inputs and state

### Official specification (README.md §8, verbatim)
- **Purpose:** "Algorithmically evaluate candidate methods (including n-gram matching, interval contour sifting, and repetition detectors) to discover recurring sound groups and phrases across time, preserving comparison controls."
- **Expected deliverable:** "`music_model/group_discovery.py` providing configurable `discover_sound_groups()` sifter algorithms alongside baseline comparison controls."
- **Verification procedure:** "Run `tests/test_group_discovery.py` and `verify_group_discovery.py`."
- **Completion criteria:** "Automated sifting evaluated against ground-truth repeated phrases; boundary indices reported transparently; existing 15 regression tests preserved as regression evidence (not proof of general discovery); candidate algorithms and limitations documented."

### Relevant Author statements
Statements 1, 2, 4, 10, 13 and 14 were read in README §2, and their original wording is unchanged. JOB-04's relevance to each statement is set out in the README traceability table, rows 1, 2, 4, 10, 13 and 14.

### Repository state
- **Branch:** `main`, remote `IWatchSheep/music`.
- **Working tree:** clean apart from untracked items:
  - the experimental files `music_model/group_discovery.py`, `tests/test_group_discovery.py`, `verify_group_discovery.py` and `verify_row_merger.py` (the last is outside JOB-04 scope);
  - the review ZIPs and the crash log.

### Backup
Before any work, the experimental files were backed up to `%USERPROFILE%\JOB_04_EXPERIMENTAL_BACKUP_20261126_211422\`, with `SHA256SUMS.txt`. Their SHA-256 hashes (first 12 hex digits):

| File | SHA-256 |
|---|---|
| `group_discovery.py` | `baa07247f1a4…` |
| `test_group_discovery.py` | `202535932ff4…` |
| `verify_group_discovery.py` | `e3f50a2c4997…` |
| `verify_row_merger.py` | `8b628d263fee…` |

The experimental files were not modified during this stage.

---

## 2. Baseline regression (JOB-22)

All runs: Windows, CPython 3.15.2. The exit codes are the child Python processes' own.

| Run | Result |
|---|---|
| `python acceptance/run_acceptance.py --windows-device` (complete local project) | Suite **293 run, 279 passed, 14 skipped**, 0 failures or errors (exit 0). Device 14/14 (exit 0). 7/7 required scripts plus 2/2 optional (present) scripts exit 0. Runner **exit 0**. |
| `python -m unittest tests.test_group_discovery` | 15/15 passed (exit 0) |
| `python verify_group_discovery.py` | exit 0. **It has no assertions, so exit 0 carries no verification meaning** (§6, P13). |

- The 14 skips are the gated real-device tests, which pass when opted in. These are platform/opt-in skips, not failures.
- The published JOB-03 tree (278 tests) is unchanged.

Logs: `evidence/baseline_acceptance_run.txt`, `evidence/test_group_discovery_output.txt` and `evidence/verify_group_discovery_output.txt`.

### 2.1 Recurrence of the unresolved native access violation (JOB-03 limitation A21) during this stage

While verifying that this review archive is self-contained, the acceptance runner was run inside a freshly extracted copy of the archive (2026-11-27 05:22 UTC). In that run, **two separate child processes ended with exit code 3221225477 (0xC0000005, `Windows fatal exception: access violation`)**:

| Process | Faulting Python frame (faulthandler) | Context |
|---|---|---|
| Full suite (`unittest discover`), after 47.9 s, with no result file | `music_gui/audio_playback.py:1079` in `synthesize_song_audio`, called from `load_timeline` ← `tests/test_playback_consolidated.py:1095` (`setUp`) | Headless unit test; no GUI hang; no MCI involvement in that frame |
| `verify_audio_and_sheet_adapters.py`, after 18.2 s | `music_model/audio_importer.py:437` in `_estimate_pitch_autocorrelation` (generator expression) | Command-line script; no Tk at all |

What this run shows:
- **[FACT]** The code was byte-identical to the local tree, whose full run passed minutes earlier (§2). No JOB-04 code is on either faulting stack.
- **[FACT]** The device tests (14/14) and the other 8 scripts in the same run exited 0.
- **[FACT]** The Windows Application log has no entry for these two crashes. No new kernel bugcheck has been recorded since 2026-11-26 10:24.
- **[OBS]** Both faults are in long pure-Python floating-point loops: the same pattern as the JOB-03 crash. **They occurred without any frozen GUI.** This weakens the earlier observation that the fatal crashes coincided with a hung window.
- **[HYP]** I guess this adds weight to the system- or interpreter-level explanation (CPython 3.15.2 defect, or driver/hardware instability; three kernel bugchecks this week). It is not proof, and the cause remains **unresolved**. Investigating it further is outside JOB-04 and needs the Author's separate authorization.

A repeat run of the same extracted archive was made; its result is recorded in §2.2. The crashed run's logs are kept in `evidence/extracted_run1_CRASHED_20261127T052203Z/`.

### 2.2 Repeat run of the extracted archive (2026-11-27 05:24 UTC)

The same extracted tree, the same command (`--windows-device`), immediately after the crash:
- **Suite:** 293 run, **279 passed, 14 skipped**, 0 failures or errors (exit 0).
- **Device:** 14/14 (exit 0).
- **Scripts:** 7/7 required exit 0, `verify_group_discovery.py` exit 0, and `verify_row_merger.py` reported `OUTSIDE PUBLICATION SCOPE (absent)`.
- **Runner:** exit 0.

**[OBS]** The access violation is **intermittent**: 1 of 2 runs of identical code crashed, in 2 of its child processes. The archive is self-contained, and when the native fault does not occur it reproduces the §2 baseline exactly. Logs: `evidence/extracted_archive_acceptance_run.txt` (crashed) and `evidence/extracted_archive_acceptance_run2.txt` (passed).

---

## 3. What the existing engine calculates

**Input:** `notes_by_row: Dict[row_id, Sequence[note]]`.

**Note normalization.** Every note is reduced by `extract_note_timing` to `(start_ms: float, end_ms: float, pitch: int, label)`. [FACT]
- Pitch is read from `pitch`, falling back to `height`, falling back to **60**. It is then converted with `int(round(·))`.

**Output.** Every method returns a `GroupingResult` containing:
- `groups_by_row`: per row, a list of `DiscoveredGroup(start_ms, end_ms, notes, method, units)`;
- `discovered_boundaries_ms`: the sorted union, across all rows, of group starts and ends;
- `diagnostics`;
- `row1_segments`. [FACT]

The individual methods:

| Method | Mathematical definition [FACT] | Boundary rule | Output shape |
|---|---|---|---|
| **Sifter A, rests** | Sort notes by start. Cut between consecutive notes i, i+1 when `start(i+1) − end(i) ≥ min_gap_ms` (default 100; the verification script uses 80). | silence gap | Partition of each row into variable-length groups. A group ends at the **last note's** end, not at the maximum end. |
| **Sifter B, motoric** | For each candidate span s ∈ {300, 400, 200} ms: let K = round(T/s). Count the grid points `row_start + k·s` (k = 0..K) that lie within 20 ms of *any* note onset or offset. Accept s if at least 70% of the points match, and pick the s with the most matches. | **Periodic grid** | K **equal-width** slices of the chosen s; otherwise a single "NoRepetition" group. |
| **Sifter C, contour** | Sort notes by start. Cut after note i when the pitch direction changes (sign(p_i − p_{i−1}) ≠ sign(p_{i+1} − p_i), with both signs non-zero) or when \|p_{i+1} − p_i\| ≥ `min_leap` (default 5). | Local turning point or leap | Partition into variable-length groups |
| **Sifter D, cross-row** | Cut between consecutive notes of a row when any **other** row has an onset or offset in (start(i), start(i+1)], or within `window_ms` of end(i). | Event in another row | Partition. A single-row passage is never cut. |
| **Control 1, fixed-width** | Slices of `width_ms` from the row start | Grid | Equal-width slices |
| **Control 2, random** | A seeded `random.Random(seed)`. Internal points are uniform over the passage span, and the count is matched to the candidate under test. | Random | Points (Monte Carlo over 100 seeds: mean ± population standard deviation of P, R and F1) |
| **Evaluation** | Kuhn augmenting-path maximum one-to-one matching of boundaries within ±tolerance, giving P, R and F1. `internal_only` drops points within the tolerance of either end of the span. | — | `EvaluationMetrics` |
| **Row 1 derivation** | Union of all group boundaries; for each segment, counts of active rows and groups and the mean pitch | — | `row1_segments`, attached to **every** result |

- **Matching check.** The evaluation's matching was cross-checked against an independent exhaustive matcher on every validation case, and the two agreed everywhere. [FACT, harness `engine_vs_bruteforce_tp`]

---

## 4. Answers to the ten baseline questions

1. **What each sifter calculates.** See §3. All four sifters are **segmenters**: each places cut points inside a row. [FACT]
2. **Inputs and outputs.**
   - **Inputs:** start and end in float ms, an integer pitch, and the row id. Nothing else is read: no velocity, no exact rational timing, no event attributes. [FACT, P04]
   - **Outputs:** per-row group lists (holding the original note objects), a boundary union, diagnostics and Row 1 segments. [FACT]
3. **How group boundaries are identified.**
   - A uses silence; B a periodic grid; C local pitch turning points or leaps; D events in other rows. [FACT]
   - None of these rules refers to whether material *repeats*. [FACT]
4. **Whether recurring phrases are identified, as well as boundaries.**
   - **No.** No method compares one group with another, and no result field represents "these groups recur". The full set of result fields is: sifter_name, groups_by_row, discovered_boundaries_ms, diagnostics, row1_segments, group_id, row_id, start_ms, end_ms, notes, method, start_unit, end_unit. [FACT]
   - In the validation, **0 of 8** ground-truth recurrence relations were reported. [OBS]
5. **How rhythm, pitch intervals and contour are compared.**
   - **Rhythm:** only B uses it, and only as agreement of onsets and offsets with a periodic grid. Rhythm is never compared between two passages. [FACT]
   - **Pitch intervals:** used only as a single-step size threshold (C's leap rule). Interval *sequences* are never compared, and transposition invariance does not exist. [FACT]
   - **Contour:** C uses the sign changes of a single pitch stream only to cut. Contours are never compared. [FACT]
6. **Whether groups can differ in duration and event count.**
   - A, C and D produce variable durations and note counts. [FACT]
   - B and the fixed-width control produce **equal-width** slices only; probe P07 shows a note straddling a slice. B therefore conflicts with the JOB-04 boundary "do not force discovered sound groups into a predetermined equal-width grid". [FACT]
7. **How overlapping or ambiguous candidates are represented.** They are **not represented**.
   - Each sifter returns one partition per row. There are no alternative segmentations, no overlapping groups and no confidence values. [FACT]
   - In B, the fixed control and the random control, a note that crosses a slice edge is listed in both slices. [FACT]
   - With polyphony inside a row, A detects false rests and truncates group ends (P05). D cuts at almost every note in dense polyphony (P08). [FACT]
8. **How exact source timing and event identity are preserved.**
   - **Identity is preserved.** Groups hold the original note objects, so `event_id` and the attributes are reachable. [FACT]
   - **Exact timing is not preserved.** Only `start_time_ms`/`end_time_ms` (integer ms for a `SoundEvent`) are read. The exact rationals (`exact_*_sec_rational`) are ignored (P04). MIDI ticks are taken as milliseconds when no ms field exists (P02). Fractional heights are rounded (P03). [FACT]
   - A `SoundEvent` with `height=None`, which the JOB-02 WAV importer emits for unpitched events, **crashes every sifter** (P14). [FACT]
9. **Official requirements already satisfied.** See §7. The comparison controls (fixed-width and count-matched random) exist, and boundary evaluation with maximum matching is correct. [FACT]
10. **Requirements missing or unverified.** See §7. These are:
    - the core purpose (recurring groups and phrases);
    - n-gram matching;
    - interval-contour sifting as recurrence;
    - repetition detectors beyond the periodic grid;
    - the `discover_sound_groups()` entry point;
    - evaluation against ground-truth repeated phrases;
    - boundary indices (only ms times are reported);
    - the limitations documentation.

---

## 5. Independent validation (existing engine, unmodified, untuned)

### Design
`job04_investigation/fixtures.py` builds every passage as a concatenation of designed segments. The ground truth is written down **while constructing** and is never derived from a sifter:
- segment boundaries;
- phrase instances (row, start, end, phrase, transformation);
- recurrence relations.

### Benchmark conventions (stated, not Author requirements)
- A recurring phrase has **at least 3 notes**. I guess this threshold is reasonable; reviewers may change it.
- Times are exact integer milliseconds.
- The random material in `non_repeating` uses seed **2028**, found by deterministic rejection sampling from seed 2026. A brute-force check that is independent of the engine confirms it has no repeated 3-note interval pattern and no repeated 3-duration rhythm.

### Parameters
Exactly those used by `verify_group_discovery.py`:
- Sifter A gap 80 ms; Sifter B at its defaults with min_repeats 2; Sifter C leap 5; Sifter D window 60 ms;
- fixed-width control 400 ms; u = 100 ms; boundary tolerance ±60 ms;
- random control: 100 seeds, count-matched.

**Nothing was tuned.**

### Results
Full table: `evidence/baseline_validation_output.txt`; data: `job04_investigation/results/baseline_validation.json`.

| Category | Passage | Best boundary F1 (method) | Random F1, count-matched | Phrase instances delimited | Recurrences reported |
|---|---|---|---|---|---|
| Exact recurrence with rests | exact_with_rests | **1.000 (A)** | 0.096 ± 0.146 | A: 2/2 | 0/1 |
| Exact recurrence, legato | exact_legato | 0.400 (C: 8 FP) | 0.098 ± 0.092 | 0/3 (all methods) | 0/1 |
| Transposed (+7) | transposed | 0.444 (C) | 0.100 ± 0.123 | 0/2 | 0/1 |
| Same rhythm, other pitches | rhythm_only | 0.400 (C) | 0.105 ± 0.121 | 0/2 | 0/1 |
| Same contour, other intervals | contour_only | 0.400 (C) | 0.105 ± 0.121 | 0/2 | 0/1 |
| Different-length groups (3 and 5 notes) | different_lengths | 0.600 (C) | 0.096 ± 0.120 | C: 2/4 | 0/2 |
| Non-repeating | non_repeating | A, B, D: 0 boundaries. **C: 8 false**; fixed: 12 false | — | — | — |
| Misleading similarity | accidental_similarity | A, B, D: 0. **C: 5 false**; fixed: 7 false | — | — | — |
| Cross-row recurrence | cross_row | 0.400 (D), 0.333 (C) | 0.091 ± 0.172 | D: 1/2 | 0/1 |
| Empty / one note / two notes | 4 passages | No crash. Fixed-width creates an internal point; C cuts two notes | — | — | — |

### Observations [OBS]
- **A** is perfect *only* when rests separate the designed segments. On every legato passage it finds nothing.
- **B** produced no segmentation in any validation passage: there is no 200/300/400 ms periodicity in them.
- **C** has high boundary recall, but most of its cuts are false: 5–8 false boundaries even where nothing recurs. It never identifies *which* segments recur.
- **D** is silent on single-row music.
- **Against the random control:**
  - **C** beats the count-matched random control on boundary F1 in every passage whose ground truth has internal boundaries (0.333–0.615, against random means of 0.096–0.135).
  - **A** beats it only when rests are present.
  - **B and D** score 0.000 wherever they find nothing, which is below random.
  - **The fixed-width control** is below random in 2 of 7 such passages (`rhythm_only`, `contour_only`: 0.000 against 0.100).

  Better-than-chance boundary placement does **not** show phrase discovery.
- **Missed discoveries:** all 8 recurrence relations. **False positives:** C and fixed-width on the non-repeating and misleading passages. **Ambiguous results:** the 2/4 instances C delimits in `different_lengths` arise from turning points, not from recurrence.

### On the existing 15 tests and the verification script [FACT]
- **The 15 tests check behaviour on hand-made inputs.** None compares against ground-truth repeated phrases.
- **Some tests are weak.** The Sifter D test only asserts that the boundaries form a subset of the note times, and the Sifter C test asserts "≥ 2 groups".
- **The completion criteria already say this:** the tests are "regression evidence (not proof of general discovery)".
- **Passage 2's references in the verification script are defined at rests,** which makes Sifter A's perfect score there largely a consequence of the reference definition.

---

## 6. Defects, missing capabilities and limitations

All probes are in `job04_investigation/defect_probes.py`; output in `evidence/defect_probes_output.txt`. **14/14 were confirmed** (exit 0).

| ID | Severity | Finding |
|---|---|---|
| P14 | **High** | A `SoundEvent` with `height=None`, as emitted by the JOB-02 WAV importer for unpitched events, crashes every sifter (`TypeError` in `round(None)`). |
| P05 | High | Sifter A with polyphony inside a row: it reports rests while an earlier note is still sounding, and a group ends at the last-started note's end. |
| P07 | High (scope) | Sifter B outputs equal-width grid slices. This conflicts with "do not force … equal-width grid". |
| P06 | Medium | Sifter B tests only the hard-coded spans 200/300/400 ms; a clean 500 ms periodicity is reported as "NoRepetition". |
| P08 | Medium | Sifter D cuts at nearly every note in dense polyphony across two rows. |
| P04 | Medium | Exact rational source timing is ignored; integer milliseconds are used. |
| P02 | Medium | MIDI ticks are taken as milliseconds when no ms field exists. |
| P01 | Medium | A missing pitch silently becomes 60. |
| P03 | Low | Fractional pitch is rounded to an integer. |
| P09 | Medium | The Monte Carlo baseline silently assumes a span of (0, 1000) ms when none is given. |
| P10 | Low | `specificity` is 1 or 0 by "no false positives", not a true-negative rate, and F1 = 1.0 is reported for empty versus empty. |
| P11 | Low | `discovered_boundaries_ms` is a union across rows and loses the row. Boundaries are times, not event indices. |
| P12 | Scope | Every result also derives Row 1 segments, which belongs to later jobs (merger and transfer to Row 1). It must not be extended in JOB-04. |
| P13 | **High (evidence)** | `verify_group_discovery.py` has no assertions, always exits 0, and prints hard-coded summary figures that differ from its own computed output (see below). |

**P13 detail.** The printed summary and README Milestone 5A disagree with the script's own computed output:
- Passage 1 random F1: claimed **0.125 ± 0.119**, computed **0.089 ± 0.150**.
- Passage 2 random F1: printed **0.222 ± 0.141**, computed 0.217 ± 0.158 (README quotes 0.217 ± 0.158).
- Passage 1 Sifter B: README states precision 50.0% and recall 66.7%; computed precision is **66.7%** and recall **50.0%** (F1 0.571 matches).

The README text is unchanged here; correcting it would need Author authorization.

### Missing capabilities [FACT]
- Recurrence detection of any kind (exact, transposed, rhythmic or contour).
- A representation of groups as recurring *identities* (clusters of occurrences).
- Overlapping or alternative candidates, and confidence values.
- Voice separation inside polyphonic rows.
- Event-index boundary reporting.
- The `discover_sound_groups()` entry point.
- A chance-recurrence control (surrogate data).

---

## 7. Official requirements coverage matrix

| # | Requirement (source) | Status | Evidence |
|---|---|---|---|
| R1 | Discover **recurring sound groups and phrases across time** (Purpose) | **MISSING** | §4 Q4; 0/8 recurrences |
| R2 | Candidate method: **n-gram matching** (Purpose) | **MISSING** | No n-gram code exists |
| R3 | Candidate method: **interval contour sifting** (Purpose) | **PARTIAL**: contour is used for cutting only, not for matching | Sifter C; §4 Q5 |
| R4 | Candidate method: **repetition detectors** (Purpose) | **PARTIAL**: periodic-grid alignment only (B), with fixed spans and equal-width output | P06, P07 |
| R5 | **Preserving comparison controls** (Purpose) | **SATISFIED** for boundary evaluation (fixed-width and count-matched random). **MISSING** for recurrence (no surrogate control). | §3 |
| R6 | **Configurable `discover_sound_groups()`** entry point (Deliverable) | **MISSING** | The function does not exist; the sifters are separate functions |
| R7 | **Evaluated against ground-truth repeated phrases** (Completion) | **MISSING in the existing work**; a baseline now exists (this stage) | §5. The existing benchmark uses designer boundary references, not repeated-phrase truth. |
| R8 | **Boundary indices reported transparently** (Completion) | **PARTIAL** | Times are reported, not event indices; row attribution is lost in the union (P11) |
| R9 | **Existing 15 regression tests preserved** as regression evidence (Completion) | **SATISFIED** (15/15, exit 0; unchanged and backed up) | §2 |
| R10 | **Candidate algorithms and limitations documented** (Completion) | **PARTIAL**: this report documents them; nothing in the code or docs yet | §3, §6 |
| R11 | Verification procedure: run the tests and `verify_group_discovery.py` (Verification) | **RUNS but not meaningful**: the script asserts nothing | P13 |
| B1 | Do not force an equal-width grid (assignment boundary) | **VIOLATED by Sifter B** (and the fixed control by design, as a control) | P07 |
| B2 | Do not assign groups to Rows 2/3; no merger or Row 1 transfer (assignment boundary) | **AT RISK**: Row 1 segments are derived in every result | P12 |
| B3 | Preserve exact source timing and event identity (JOB-01 principle; assignment) | Identity **SATISFIED**; exact timing **NOT** (integer ms, ticks, rounding, crash) | P01–P04, P14 |
| S1/S14 | Statement 1 ("loops of sound that's repeated … other sound that's repeated") and Statement 14 ("the sound in a group is distinct from a different sound in a group") | **NOT ADDRESSED**: there is no notion of distinct recurring groups | [HYP] below |
| S2/S4/S10/S13 | These concern Row 1, the shape of the constant line and column fitting. In JOB-04 they only require that discoveries **preserve the evidence later stages need** | **PARTIAL**: groups keep note objects but lose exact timing | B3 |

### Hypotheses [HYP]
- I guess Statement 1's "loops of sound that's repeated. then you have other sound that's repeated" means there are several **distinct** recurring groups at once. Discovery should then return clusters of occurrences (group identities), not a single segmentation.
- I guess Statement 14's "the sound in a group is distinct from a different sound in a group" supports giving each discovered recurring group an identity that later jobs can carry into Rows 2/3. Assigning rows remains a later job.
- I guess transposed recurrence (the same intervals at another pitch) should count as "the same sound group" for some purposes and not for others. The engine should report the relation type rather than decide.
- I guess polyphonic rows (chords, sustained bass under melody) will need voice or onset-stream separation before melodic matching. P05 and P08 show that the current sequence-by-start approach breaks there.

---

## 8. Proposed implementation plan

This plan needs ChatGPT's review and Author authorization before implementation. It is localized: the existing code, its 15 tests and its results are preserved.

**Stage 2a: correctness of the existing engine (no change to the sifters' documented semantics).**
- P14: treat `height=None` as **unpitched**. Pitch-based sifters skip it with an explicit diagnostic; time-based ones use it.
- P01, P02: no silent defaults. Require milliseconds, or convert ticks only with an explicit tempo map; otherwise raise.
- P05: in Sifter A, use the running maximum end (a true silence is when nothing sounds).
- P09: require the span. P10: rename or clarify the metric, keeping the old field for compatibility.
- P13: make `verify_group_discovery.py` compute its summary and **assert** the documented expectations, so that its exit code means something.
- Keep exact rational timing (P04) available on the groups. Each defect gets a regression test first, shown to fail on the current code.

**Stage 2b: the missing core.** Add `discover_sound_groups(notes_by_row, method=..., **config)`. It returns **recurrence clusters**: occurrences carrying the exact source event ids, exact start/end, event-index boundaries per row, the relation type and a score. It allows **overlapping and alternative** candidates, and imposes no partition and no grid. Candidate methods, each evaluated separately:

| Method | Compares | Invariance |
|---|---|---|
| M1 exact n-gram | (pitch, duration) sequences | none |
| M2 interval n-gram | pitch-interval sequences (plus duration ratios as an option) | transposition |
| M3 rhythm n-gram | inter-onset and duration ratios | pitch; tempo optional |
| M4 contour | direction-sign (Parsons) sequences | expected to over-match; measured and reported |

- **Recurrence control:** seeded surrogate passages (pitch-shuffled, onset-shuffled) estimate the chance recurrence rate. The existing fixed-width and random boundary controls are kept.
- **Sifters A–D** stay as boundary candidates and can be combined as constraints, but are not required.

**Stage 2c: evaluation without tuning.**
- The fixtures in this report are frozen as the **development set**.
- A **held-out set** should be specified independently before any implementation is evaluated on it. I propose ChatGPT or the Author write it.
- Report instance-level and relation-level precision and recall, false positives on the non-repeating and misleading sets, and results against controls.

**Out of scope (unchanged):**
- assigning rows (Rows 2/3);
- uniform column fitting and the merger;
- transfer to Row 1, and the linear or curved graph;
- breath and pause classification as an acoustic problem (JOB-05);
- the row-merger experiment.

**Decisions requested from the reviewers:**
1. the minimum phrase length (proposed: 3 notes);
2. exact versus tolerant timing for "same rhythm";
3. whether transposed recurrences belong to the same cluster or to a linked cluster;
4. the approach to voice separation for polyphonic rows;
5. who writes the held-out set;
6. whether to correct the README Milestone 5A figures (needs Author authorization).

---

## 9. Reproduction

From the project root (standard library only; Tk is needed only for the full suite):

```
python -m unittest tests.test_group_discovery
python verify_group_discovery.py
python job04_investigation/run_baseline_validation.py
python job04_investigation/defect_probes.py
python acceptance/run_acceptance.py            # add --windows-device on Windows
```

- **Expected results:**
  - the tests pass 15/15;
  - the verification script exits 0 (it has no assertions);
  - the validation and probe scripts exit 0 and reproduce the tables above, deterministically;
  - the acceptance runner reports the baseline in §2.
- **On Linux without a display:** prefix the acceptance command with `xvfb-run -a`. Expect 293 run with one more skip than on Windows (the device-dependent GUI cleanup test).
