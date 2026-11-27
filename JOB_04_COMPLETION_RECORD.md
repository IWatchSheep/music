# Job Completion Record: JOB-04 — Sifter Discovery Engine for Recurring Loops & Melodic Phrases (revision 2)

> **Status:** **JOB-04 APPROVED FOR PUBLICATION WITH DOCUMENTED LIMITATIONS** (ChatGPT's final independent review of `JOB_04_PUBLICATION_REVIEW_R2.zip`, 2026-11-27) and **publication authorized by the Author** (staging, commit and push to `IWatchSheep/music`, branch `main`). See §11.
> **Protected checkpoint (HEAD; published JOB-03):** `e1a11e7d5b03a44621f177e8bce5aa504d726334`
> **Frozen implementation reviewed:** `JOB_04_STAGE2B_R3_REVIEW.zip`, SHA-256 `5b53a5da114ff6635271220737b5c0f1351b13c9896345f841f9d309984bccf1`. Production code and the 79 earlier tests are byte-identical to it.
> **Previous publication package:** `JOB_04_PUBLICATION_REVIEW.zip` (R1, `d377db81…`), audited by ChatGPT and preserved.
> **Limitations:** `JOB_04_REMAINING_LIMITATIONS.md`. **Verification:** `JOB_04_VERIFICATION_LOG.txt`. **Publication boundary:** `JOB_04_PUBLICATION_MANIFEST.md`. **Path sanitization:** `JOB_04_PATH_SANITIZATION.md`.
> **Prepared by:** Claude Opus 5.5 (PyCharm terminal), 2026-11-27.
> **Continuous gate:** JOB-22 remains active.

---

## 1. Permanent schema fields (README §9.2)

- **Job:** `JOB-04`, Sifter Discovery Engine for Recurring Loops & Melodic Phrases.
- **Relevant Author statements:** 1, 2, 4, 10, 13, 14. They are unchanged; no Author statement was edited.
- **Starting checkpoint:** `e1a11e7` (JOB-03 published). The JOB-04 prototype files were untracked local work.
- **What JOB-04 establishes:** tested **mathematical relation correctness in the symbolic domain**. On controlled passages, the reported recurrence families are exactly the window pairs that satisfy each method's exact relation.
- **What it does not establish:** that a reported family is a musically significant phrase. **No universal musical recognition is claimed.**

## 2. Stages

| Stage | Outcome | Record |
|---|---|---|
| Baseline investigation | The existing boundary sifters A–D were evaluated unmodified against constructed ground truth; 14 defect probes were run. No recurrence output existed. | `JOB_04_BASELINE_INVESTIGATION.md` |
| Stage 2a | Input-handling corrections to the boundary engine, plus the authorized README factual correction (Milestone 5A, Passage 1). Accepted. | `JOB_04_STAGE2A_REPORT.md` |
| Stage 2b | New recurrence engine `discover_sound_groups()` with six exact relations. Identity contract revised (R2), then global identifier uniqueness (R3). Accepted. | `JOB_04_STAGE2B_SPECIFICATION.md`, `JOB_04_STAGE2B_REPORT.md`, `JOB_04_STAGE2B_IDENTITY_REVISION.md` |
| Stage 2c | ChatGPT's independent held-out validation: 17 passages, a direct value-by-value oracle, **886/886** checks. Accepted; no production-code tuning. A coverage test was added in publication R2 (§8). | §4; `JOB_04_VERIFICATION_LOG.txt` §5 |

## 3. Files

**Production** (both new to the repository; byte-identical to R3):
- `music_model/group_discovery.py`: the boundary sifters A–D and comparison controls, with the Stage 2a input corrections, and the `discover_sound_groups` delegate.
- `music_model/recurrence_discovery.py`: `discover_sound_groups(notes_by_row, config, **overrides)` and `DiscoveryConfig`.
  - Methods: `exact`, `transposition`, `rhythm` and `contour` (the defaults), plus `interval_only` and `rhythm_proportional`.
  - Output: families, occurrences with original-event references, nesting, stricter-method equivalence, stream reports, exclusions, rejected candidates and search accounting.

**Tests (80):**

| Module | Tests | Status |
|---|---|---|
| `tests/test_group_discovery.py` | 15 (original) | unchanged |
| `tests/test_group_discovery_stage2a.py` | 16 | unchanged |
| `tests/test_group_discovery_stage2b.py` | 29 | unchanged |
| `tests/test_group_discovery_stage2b_identity.py` | 11 | unchanged |
| `tests/test_group_discovery_stage2b_unique_ids.py` | 8 | unchanged |
| `tests/test_group_discovery_stage2c_coverage.py` | **1** | **new in R2**, authorized by ChatGPT |

**Verification:**
- `verify_group_discovery.py`: 22 asserted checks. It is a **required** acceptance script.
- `job04_investigation/job04_heldout_audit.py`: ChatGPT's independent verifier, **byte-identical** to the supplied file. SHA-256 `713be72a2d050fc0782d35a760afdafd6cc469cda05fb4c186d314df49e54846`. It is a **required** acceptance script.
- `job04_investigation/`: the research harness. Its generated `results/` folder is now ignored by `.gitignore`.

**Acceptance infrastructure** (tracked; modified, §5): `acceptance/run_acceptance.py`, `acceptance/acceptance_matrix.json`, `acceptance/README.md` and `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md`.

**Other tracked files:**
- `README.md` (§6):
  - line 595: the Stage 2a correction;
  - line 649: path sanitization;
  - lines 714 and 1018: the authorized JOB-04 status.
- `.gitignore`: `job04_investigation/results/` added; every existing rule is preserved.
- `JOB_02_COMPLETION_RECORD.md`: path sanitization only.

`music.txt`, the JOB-03 production code and the calculator repository are unchanged.

**Records:** the five stage reports, this record, `JOB_04_VERIFICATION_LOG.txt`, `JOB_04_REMAINING_LIMITATIONS.md`, `JOB_04_PATH_SANITIZATION.md` and `JOB_04_PUBLICATION_MANIFEST.md`.

## 4. Completion criteria (README JOB-04) and evidence

| Criterion | Evidence | Matrix |
|---|---|---|
| Automated sifting evaluated against ground-truth repeated phrases | Development set: 13 passages, 44/44 asserted expectations, 8/8 intended relations found by their primary method. Independent held-out set: 17 passages, 886/886 checks (306/306 exhaustive pair-set comparisons, 11/11 intended relations, 17/17 determinism, 552/552 original-event references). Strict transposition also compares onset spacing (coverage test). | G03, G07 |
| Boundary indices reported transparently | Half-open `[start_index, start_index + n)` windows. Every occurrence lists `EventRef`s holding the original source object, chronological and input indices, exact timing and pitch provenance. Reported identifiers are globally unique. | G04 |
| Existing 15 regression tests preserved as regression evidence (not proof of general discovery) | 15/15 unchanged; `verify_group_discovery.py` 22/22 | G01 |
| Candidate algorithms and limitations documented | `JOB_04_STAGE2B_SPECIFICATION.md`; `JOB_04_REMAINING_LIMITATIONS.md` | G09 (documentation; reviewed, not tested) |
| Comparison controls preserved (from Purpose) | Fixed-width and count-matched seeded random controls; shuffled surrogates (descriptive only) | G08 |

## 5. Acceptance integration

- **Required scripts (9):** the seven JOB-01–JOB-03 scripts (unchanged), `verify_group_discovery.py` (promoted from optional to required) and `job04_investigation/job04_heldout_audit.py`.
- **Optional (1):** `verify_row_merger.py`, outside the publication boundary. It runs only when present.
- **Script environment:** each script runs with the project root prepended to `PYTHONPATH`.
- **Matrix:** version `acceptance-2.1`.
  - A01–A21 are unchanged.
  - A22 lists the new script sets.
  - G01–G09 cover JOB-04, and G01–G08 map all **80** JOB-04 tests. **G03 now requires the coverage test.**
- **Not run by the runner:** the research harness, because it writes generated results. Its commands and exit codes are in the verification log, §4.
- **Rule check (R1):** with the held-out verifier removed, the runner reports `MISSING (required)` and exits 1.

## 6. README changes (applied in R2)

**Stage 2a historical correction, preserved.** Line 595, Milestone 5A, Passage 1. The values were recomputed by `verify_group_discovery.py`, and the previous values are kept in a note on that line:

| | Previously stated | Corrected |
|---|---|---|
| Internal references | N = 6 | N = 4 (6 including passage edges) |
| Sifter B precision / recall | 50.0 % / 66.7 % | 66.7 % / 50.0 % |
| Random baseline | 0.125 ± 0.119 | 0.089 ± 0.150 |

**Other changed lines:**
- **Line 714 (authorized):** JOB-04 `Current Status` becomes **`[COMPLETED WITH DOCUMENTED LIMITATIONS]`**, disclosing exact-only matching, unsupported ambiguous polyphony, weak contour evidence, unresolved nested and incidental relationships, cubic search within configured limits, and unverified general musical phrase significance.
- **Line 1018 (authorized):** the milestone tree shows `JOB-04: Sifter Discovery Engine [COMPLETED WITH DOCUMENTED LIMITATIONS]`.
- **Line 649 (Author-approved):** path sanitization only.

No Author statement, no other job status and no historical test result was changed.

## 7. Verification summary (actual results; details in `JOB_04_VERIFICATION_LOG.txt`)

All runs used Windows 11 and CPython 3.15.2. The exit codes are the child processes' own.

| Check | Result |
|---|---|
| **R2 run 1:** full acceptance on the R2 tree (`--windows-device`) | **FAILED, runner exit 1.** `verify_audio_and_sheet_adapters.py` (JOB-02 code) died with 0xC0000005 at `audio_importer.py:437`: the A21 access violation. Otherwise: suite **358 run, 344 passed, 14 skipped**, 0 failures or errors; device 14/14; the other 8 required scripts exit 0; G01–G08 PASS. Preserved as evidence; no automatic retry. |
| **R2 run 2:** planned confirmation on the final R2 tree (`--windows-device`) | Recorded in `JOB_04_PUBLICATION_MANIFEST.md` §3 and `JOB_04_VERIFICATION_LOG.txt` §13. This record was written before that run and is part of the tree it tested. |
| Coverage test | passes on the correct engine (1 test, exit 0); **fails on the mutant** (exit 1) |
| The 79 earlier tests, both production files, the held-out verifier | byte-identical to the reviewed versions |
| Focused JOB-04 tests (R1) / `verify_group_discovery.py` / held-out verifier | 79/79 / 22/22 / 886 checks, 0 failures; now 80/80 with the coverage test (both R2 runs) |
| Development evaluation (R1) | Run 1 **crashed** (A21). Run 2: 44/44, exit 0. Both preserved separately. |
| R1 full acceptance and confirmation (357 tests) | both exit 0 (log §6, §9) |

ChatGPT's independent results are 79/79, 886/886 and 22/22. ChatGPT did not repeat the full Windows regression or the device suite.

## 8. Findings during publication preparation

1. **A21 recurred twice during publication preparation.** It remains **unresolved**, with no automatic retries. Both events are preserved as separate evidence in `%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\`.
   - **R1 development evaluation:** pure-Python JOB-04 code with no audio or GUI. This shows the problem is not confined to GUI or audio execution.
   - **R2 acceptance run 1:** in `verify_audio_and_sheet_adapters.py`, at the same frame as the 05:22 UTC occurrence.
   - **The cause is not attributed** to Python, hardware or drivers, and no system-level change was made.
   - **Count within JOB-04 work:** four observations in four separate processes (two at 05:22 UTC, one at about 10:12 UTC, one at about 10:35 UTC).
2. **The test-coverage gap is closed.** The "transposition ignores inter-onset intervals" mutant passed the held-out verifier and the 79 tests. ChatGPT reproduced this independently. The authorized test `tests/test_group_discovery_stage2c_coverage.py` now detects it. No production code changed.

## 9. Limitations (summary; full text in `JOB_04_REMAINING_LIMITATIONS.md`)

- Exact-only matching.
- Unsupported ambiguous polyphony.
- Weak contour evidence.
- Nested and incidental relationships reported, not resolved.
- Cubic worst-case search.
- Configured search limits.
- Generated identities are not persistent.
- Unverified general musical phrase significance.
- Finite test sensitivity.
- Retained legacy-sifter behaviours (P06, P07, P08, P10, P12).
- JOB-03 A20 (acoustic synchronization unmeasured) and A21 (native access violation unresolved).

## 10. Not done (protected boundaries)

The following were **not** implemented or touched:
- row assignment, column fitting, row merging, Row 1 transfer and graph classification;
- JOB-05;
- the JOB-03 production code, `music.txt` and the calculator repository;
- the row-merger experiment (not published).

Nothing was staged, committed or pushed.

## 11. Final independent review and Author authorization (2026-11-27)

**ChatGPT's final review of `JOB_04_PUBLICATION_REVIEW_R2.zip`** (SHA-256 `1f569a6bcd6cd261ae2ceb9724ba16a601dddcdf1964b0f8b8c290e0a65450a9`, 810 325 bytes, 87 entries).

Archive and manifest:
- integrity PASS;
- all 86 listed file hashes match;
- the manifest hash (`8549d436…`) was confirmed independently;
- 7 modified, 26 new and 54 unchanged tracked files;
- the 33-path staging list was confirmed.

Focused execution:
- JOB-04 regression 80/80 in 0.213 s;
- held-out verifier 886 checks with 0 failures;
- legacy verification 22/22;
- the coverage test passes on the correct engine and detects the inter-onset-interval mutant.

Also confirmed:
- the held-out verifier is byte-identical to the supplied version;
- the README changes, path sanitization and ignore rule;
- A01–A21 unchanged from the published JOB-03 matrix;
- protected production code, previous tests and `music.txt` unchanged.

ChatGPT did not repeat the complete Windows acceptance runs.

**Windows acceptance evidence, both runs preserved.**
- R2 run 1 **FAILED** (exit 1): the native access violation 0xC0000005 in `verify_audio_and_sheet_adapters.py`; 8/9 required scripts. This remains valid historical evidence.
- R2 run 2 **PASSED** (exit 0): 358 run, 344 passed, 14 skipped; device 14/14; 9/9 required scripts.
- The second run does not erase the first failure.
- A20 remains unmeasured. A21 remains unresolved.

**Final independent engineering decision:** "JOB-04 APPROVED FOR PUBLICATION WITH DOCUMENTED LIMITATIONS."

**Author authorization:** staging, committing and pushing JOB-04 to `IWatchSheep/music`, branch `main`, with explicit by-name staging of the 33 manifest paths.

**Pre-staging checks** (made before this section was written):
- HEAD = `origin/main` = `e1a11e7d5b03a44621f177e8bce5aa504d726334` (after `git fetch`);
- the index is empty;
- all 87 files are byte-identical to the approved R2 archive.

After authorization, only this record and the manifest changed: this section and the status line here; the status line and the hashes of these two files in the manifest. No production code or test was changed.
