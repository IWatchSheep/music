# JOB-04 Stage 2b Report: Recurring Sound-Group Discovery

**Authorization:** ChatGPT, "Stage 2a accepted. Stage 2b recurring phrase discovery recommended for implementation."
**Specification:** `JOB_04_STAGE2B_SPECIFICATION.md`.
**Protected checkpoint:** `e1a11e7d5b03a44621f177e8bce5aa504d726334` (HEAD unchanged). Nothing was staged, committed or pushed. JOB-03 playback code, `music.txt` and the calculator repository are unchanged. Stage 2c has not been started.

## 1. What was implemented

| File | Change |
|---|---|
| `music_model/recurrence_discovery.py` (new) | `discover_sound_groups(notes_by_row, config, **overrides)` with `DiscoveryConfig`. Six candidate methods: `exact`, `transposition`, `rhythm` and `contour` (the defaults), plus `interval_only` and `rhythm_proportional` (optional). Returns families, occurrences, nesting, stricter-method equivalence, stream reports, exclusions, rejected candidates and search accounting. |
| `music_model/group_discovery.py` | **Input safeguards** (ChatGPT §3): exact pitch preservation (`pitch` kept as given; `pitch_exact`, `pitch_kind`, `pitch_estimated`); explicit `voice_id`; consistent bounds (start ≥ 0, end ≤ 10¹² ms, pitch within ±10 000, all checked exactly before any float conversion). Adds the `discover_sound_groups` delegate. The boundary sifters are unchanged. |
| `tests/test_group_discovery_stage2b.py` (new) | 29 tests (§4) |
| `job04_investigation/run_stage2b_evaluation.py` (new) | Development-set evaluation with controls and 44 asserted expectations (§5) |
| `job04_investigation/run_stage2b_performance.py` (new) | Performance and complexity observations (§7) |
| `JOB_04_STAGE2B_SPECIFICATION.md` (new) | The mathematical specification |

The 15 original and 16 Stage 2a tests are unchanged and pass. Neither the recurrence engine nor its results use the legacy Row 1 derivation.

## 2. ChatGPT's input-contract probes: before and after

| Probe | Before (Stage 2a engine) | After |
|---|---|---|
| `Fraction(181, 3)` pitch | became float 60.333333333333336 | kept as `181/3` (`pitch_kind="rational"`) |
| `Fraction(60) + Fraction(1, 10**20)` | collapsed to 60.0 | kept exactly; ≠ 60 (test `test_distinct_rationals_do_not_collapse`) |
| Generic `start_ms = -1` | accepted | **rejected** (`NoteTimingError`), consistent with SoundEvent |
| Pitch `10**400` | uncaught `OverflowError` | `NoteTimingError`; `diagnose_passage_timing` counts it and does not raise |
| Float pitch 60.4 | 60.4 | 60.4 kept; key = its exact binary value (`binary_float`) |

## 3. Candidate output examples

Excerpts from `job04_investigation/results/stage2b_examples.txt`, a deterministic run.

**`transposed`** (A, filler, A + 7 semitones):
```
[transposition] n=4 maximal independent=2 same_as=[] params={'min_length': '3', 'min_occurrences': '2', 'displacements_semitones': '0,7'}
   key: transposition|n=4|intervals=(2,2,-4)|durations_ms=(250,250,250,500)|ioi_ms=(250,250,250)
   occ melody/None [0,4) 0.000-1250.000 ms ids=['e001', 'e002', 'e003', 'e004'] transp=0
   occ melody/None [8,12) 2500.000-3750.000 ms ids=['e009', 'e010', 'e011', 'e012'] transp=7
```
No `exact` family exists here, because the absolute pitches differ; the pitches of each occurrence are kept.

**`cross_row`** (A in the upper row; A − 24 semitones in the lower row):
- The transposition family has occurrences in both rows. The lower row's occurrence is listed first, by stream order, and the upper one has displacement +24.

**`different_lengths`** (X Y X Y):
- The only maximal exact family is **"X Y"** (n = 8, 2 occurrences).
- X (n = 3) and Y (n = 5) are **nested** families. They are linked by `nested_in` through intermediate lengths, because each occurs exactly where "X Y" occurs.

**Real MIDI** (the legacy calibration passage; no ground truth; qualitative):
- 2 of 4 tracks are reported `polyphonic_unsupported`, and their events are listed in `exclusions`. No order is invented for them.
- The monophonic tracks are searched.

## 4. Tests (29 new, plus a mutation check)

The tests cover:
- the input safeguards (6);
- exact recurrence with time displacement, event ids, half-open indices, exact timing and readable keys;
- nested repeats and the configurable minimum length (5 versus 2), and `include_nested=False` reporting;
- the absence of Row 1 or grid fields in results;
- transposition with a preserved displacement and kept identities;
- `interval_only` as distinct from strict transposition;
- a cross-row transposed match;
- rhythm independent of pitch, and proportional rhythm as a separate relation with an exact scale of 2;
- contour including repeated pitch, with its weak interpretation;
- an overlapping-only repeat rejected and reported; overlapping occurrences listed with an independent count of 2;
- exact fractional timing (1000/3 ms matches; 333 ms does **not**: there is no tolerance);
- a non-repeating passage giving no strict families;
- **input-order determinism** (5 seeded permutations, across two rows);
- a polyphonic stream reported as unsupported, and explicit voices forming separate streams;
- an unpitched note breaking the pitch methods while rhythm supports it;
- the window limit reported (`search_complete=False`);
- invalid configuration rejected; empty and short inputs;
- the `group_discovery` entry point and the `DiscoveryConfig` object.

**Mutation check** (`evidence/stage2b/mutation_test_output.txt`): **7/7 mutants killed**. Each injected fault makes at least one test fail:
- overlap counting;
- contour zero;
- transposition displacement;
- polyphony acceptance;
- nesting;
- the exact signature ignoring durations;
- unpitched breaks.

## 5. Development-set evaluation (13 frozen passages)

Command: `python job04_investigation/run_stage2b_evaluation.py`. **44/44 asserted expectations passed, exit 0.** The expectations come from fixture construction: all 8 intended relations found by their primary method; no exact, transposition or rhythm families on the non-repeating and misleading passages; no families on empty or short inputs; determinism; complete search.

### 5.1 Intended relations

| Passage | Relation | Primary method | Result |
|---|---|---|---|
| exact_with_rests | A × 2 | exact | **found**, maximal, exact set |
| exact_legato | A × 3 (no rests) | exact | **found**, maximal, exact set (Sifter A found nothing here) |
| transposed | A, A + 7 | transposition | **found**, maximal, displacement 7 |
| rhythm_only | R × 2 | rhythm | **found**, maximal, exact set |
| contour_only | K × 2 | contour | **found**, maximal, exact set |
| different_lengths | X × 2 | exact | **found as nested** within "X Y" (not maximal) |
| different_lengths | Y × 2 | exact | **found as nested** within "X Y" (not maximal) |
| cross_row | A upper, A − 24 lower | transposition | **found**, maximal, displacement 24 |

**8/8 were found by their primary method; 6/8 as maximal families.** The two nested cases are correct under the maximal-repeat policy: X and Y occur only together, as "X Y". Whether X, Y or "X Y" is "the phrase" is a musical judgement that the mathematics does not settle. Stricter relations also satisfy weaker methods (an exact A is also a rhythm and a contour family). Those are reported as `intended_implied`, never as independent confirmations.

### 5.2 Classification of maximal families (exact / transposition / rhythm / contour)

| Passage | intended (primary + implied) | contains intended | overlaps intended | **incidental** |
|---|---|---|---|---|
| exact_with_rests | 1 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 1 / 4 | 0 / 0 / 0 / 0 |
| exact_legato | 1 / 1 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 6 / 8 | 0 / 0 / 0 / 0 |
| transposed | – / 1 / 1 / 0 | – | 0 / 0 / 4 / 4 | 0 |
| rhythm_only | – / – / 1 / 0 | – | 0 / 0 / 0 / 2 | 0 |
| contour_only | – / – / 0 / 1 | – | 0 / 0 / 2 / 2 | 0 |
| different_lengths | 0 / 0 / 0 / 0 | 1 / 1 / 1 / 1 | 0 / 0 / 1 / 3 | 0 |
| non_repeating | – | – | – | 0 / 0 / 0 / **5** |
| accidental_similarity | – | – | – | 0 / 0 / 0 / **3** |
| cross_row | – / 1 / 1 / 1 | – | 0 / 0 / 2 / 2 | 0 |

- **Incidental matches occur only for contour.** There are 5 and 3 contour families on passages constructed to contain no recurrence. They are mathematically valid two-direction contour matches, not implementation defects, but they show that **contour is weak evidence**.
- **"Overlaps intended" rhythm and contour families** are windows that straddle phrase edges, such as the end of A plus the start of the filler. They are valid mathematical matches, not intended phrases.
- **Nested families:**
  - different_lengths has 20/20/18/14 (exact/transposition/rhythm/contour): every sub-window of "X Y";
  - exact_with_rests has 2 exact (the two 3-note sub-phrases of A).
- **Ambiguity:** truth instances touched by two or more maximal families of the same method occur for rhythm and contour (counts are in the JSON), but never for exact or transposition.
- **The baseline harness** (`run_baseline_validation.py`) still reports 0 recurrences, by design: it evaluates only the legacy boundary sifters.

### 5.3 Comparison controls

**Instance delimitation** (both ends within ±60 ms; legacy control definitions):

| Passage | Truth instances | Discovery (primary method) | Fixed-width 400 ms | Random, count-matched (mean of 100) |
|---|---|---|---|---|
| exact_with_rests | 2 | 2 | 0 | 0.01 |
| exact_legato | 3 | 3 | 0 | 0.01 |
| transposed | 2 | 2 | 0 | 0.00 |
| rhythm_only | 2 | 2 | 0 | 0.01 |
| contour_only | 2 | 2 | 0 | 0.01 |
| different_lengths | 4 | 4 | 0 | 0.18 |
| cross_row | 2 | 2 | 0 | 0.02 |

**Shuffled surrogates** (100 seeds each). Shown for each method: observed maximal families, then the surrogate mean and the fraction of surrogates with a count ≥ observed. What each shuffle preserves and destroys is listed under the excerpt.

```
exact_legato    pitch_shuffle : exact 1 / 0.01 (0.01)  transp 1 / 0.06 (0.05)  rhythm 8 / 8.0 (1.0)   contour 8 / 6.59 (0.27)
                rhythm_shuffle: exact 1 / 0.88 (0.73)  transp 1 / 0.88 (0.73)  rhythm 8 / 6.37 (0.2)  contour 8 / 8.0 (1.0)
transposed      pitch_shuffle : transp 1 / 0.06 (0.06) ; rhythm_shuffle: transp 1 / 0.66 (0.61), rhythm 5 / 2.38 (0.04)
non_repeating   contour 5 / 5.11 (0.64) under pitch shuffle  -> contour matches are at chance level
```
Full table: `evidence/stage2b/stage2b_evaluation_output.txt`.

What each shuffle preserves and destroys:
- **S1, pitch shuffle:** preserves all timing and the pitch multiset; destroys pitch order.
- **S2, rhythm shuffle:** permutes (duration, following gap) units and rebuilds onsets; preserves the pitch sequence and the duration and gap multisets; destroys rhythmic order.
- **S3, note shuffle:** permutes whole notes; preserves the note multiset; destroys both orders.

How to read these:
- **Exact and transposition families rarely arise in pitch-shuffled surrogates** (fraction 0.00–0.06). Under rhythm shuffle, they arise often for `exact_legato` (0.73), because its rhythm units are nearly uniform (250 ms), so shuffling them barely changes the passage.
- **Contour counts in surrogates are comparable to the observed ones,** including on the non-repeating passage.
- **These are descriptive comparisons on passages of 9–20 notes.** They make **no statistical-significance claim**. The surrogates assume exchangeable units, which ignores musical structure such as metre and phrase position.

## 6. Distinctions requested (§7 of the assignment)

| Category | Where reported |
|---|---|
| Mathematical matches | `all_families` (every method, every length) |
| Intended musical repetitions | §5.1 (8 relations) |
| Incidental similarities | §5.2 (contour only: 5 and 3 families) |
| Missing repetitions | none of the 8 is missing under its primary method. The two found only as nested are reported as such. |
| Nested repetitions | `is_maximal=False` with `nested_in`; counts in §5.2 |
| Ambiguous candidates | overlapping occurrences (`overlaps_with`), rejected overlapping-only candidates, instances with alternative maximal families (JSON), and polyphonic or unpitched exclusions |

## 7. Performance and complexity (`evidence/stage2b/stage2b_performance_output.txt`)

Wall-clock, one run each, methods exact/transposition/rhythm/contour:

| Input | L | Seconds | Windows/method | Families | Maximal | Complete |
|---|---|---|---|---|---|---|
| random | 50 | 0.16 | 1 176 | 44 | 26 | yes |
| random | 100 | 1.26 | 4 851 | 178 | 96 | yes |
| random | 200 | 10.05 | 19 701 | 317 | 226 | yes |
| random | 400 | 80.63 | 79 401 | 770 | 496 | yes |
| identical notes | 50 | 0.27 | 1 176 | 92 | 92 | yes |
| identical notes | 200 | 15.57 | 19 701 | 392 | 392 | yes |
| identical, `max_windows=20000` | 400 | 2.70 | 19 716 | 53 | 53 | **no**: lengths ≥ 56 not searched (reported) |

- **Growth is consistent with the O(L³) worst-case bound** (signature construction dominates). The 13 development passages take ≤ 0.02 s each.
- **Long pieces need `max_length`,** or a future linear-time repeat structure (suffix automaton). That is a possible Stage 2c optimization; it is not implemented.
- **For identical notes, every length is a maximal family:** each shorter repeat has more occurrences than its extension. This is correct under §5 of the specification, but the output is large; it is reported as a characteristic.

## 8. Verification and regression (actual exit codes)

| Command | Exit code |
|---|---|
| `python -m unittest tests.test_group_discovery tests.test_group_discovery_stage2a tests.test_group_discovery_stage2b` | 0 (60 tests) |
| mutation check of the Stage 2b tests | 0 (7/7 killed) |
| `python verify_group_discovery.py` | 0 (22/22) |
| `python job04_investigation/defect_probes.py` | 0 (5/14 confirmed: the retained limitations; 0 errors) |
| `python job04_investigation/run_baseline_validation.py` | 0 |
| `python job04_investigation/run_stage2b_evaluation.py` | 0 (44/44) |
| `python job04_investigation/run_stage2b_performance.py` | 0 |
| `python acceptance/run_acceptance.py --windows-device` | see §9 |

## 9. Full regression

Command: `python acceptance/run_acceptance.py --windows-device`, complete local project, Windows, CPython 3.15.2, 2026-11-27 05:57 UTC (`evidence/stage2b/stage2b_acceptance_run.txt`). The exit codes are the child processes' own.

| Step | Result |
|---|---|
| Suite | **338 run, 324 passed, 14 skipped**, 0 failures or errors (exit 0). This is 309 + 29 Stage 2b tests. The 14 skips are the gated device tests. |
| Real Windows device | 14/14 (exit 0) |
| 7 required scripts | all exit 0 |
| Optional scripts (present) | `verify_group_discovery.py` exit 0; `verify_row_merger.py` exit 0 |
| JOB-03 requirements | A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE; A21 regression only |
| Runner | **exit 0** |

The covered tests are unchanged and all pass: the published JOB-03 tests (278 including the 14 device tests), the 15 original group-discovery tests and the 16 Stage 2a tests.

**Native access violation:** it did not occur in this single run. That does not establish elimination; it remains **unresolved**, and there were no automatic retries.

## 10. Limitations and open items for review

- **Exact matching only.** Performed or transcribed music with timing jitter will not match. Tolerance or quantized rhythm would need to be a separately configured and separately evaluated method; none is implemented.
- **Polyphony without voice information is excluded,** with the reason reported. A voice-separation method is not implemented.
- **Contour is weak:** chance-level counts in surrogates, and incidental families on non-repeating passages.
- **Maximal repeat versus intended phrase** ("X Y" versus X and Y) is reported, not resolved.
- **Worst-case cubic time.**
- **Held-out evaluation** awaits ChatGPT's independent set. Its answers were not requested and nothing was tuned.
- **The native access violation remains unresolved** (see §9 for this stage's run). There were no automatic retries.
