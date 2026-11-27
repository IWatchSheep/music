# JOB-04 Stage 2b: Identity-Contract Revision

**Authorization:** ChatGPT's Stage 2b audit ("recurrence mathematics accepted in the tested domain; localized identity-contract correction required").
**Scope:** localized. The recurrence mathematics is unchanged: signatures, counting, nesting and equivalence. Row 1, row assignment, held-out validation and JOB-05 were not touched. HEAD is `e1a11e7`, and nothing was staged, committed or pushed.
**Contracts:** `JOB_04_STAGE2B_SPECIFICATION.md` §1, §5, §6 and §7 (updated).

## 1. Findings and decisions

| Audit item | Decision | Implementation |
|---|---|---|
| §4 stream-key collision (None vs `""`) | **An empty or whitespace-only voice means *unspecified*,** identical to None. No voice separation is invented. | `normalize_note` maps blank voices to None. `_Stream.key = (row, 0, "")` for unspecified and `(row, 1, voice)` for named voices, so keys cannot collide. Every counting, nesting and equivalence step uses that key. |
| §5 anonymous identity | **Determinism contract** (spec §5): results are equal for the same notes in any input order. Supplied ids are preserved exactly. Anonymous events get chronological generated keys `anon\|row=…\|voice=…\|k`, flagged `event_id_generated`. These keys are **stable under reordering but not persistent identities** (documented). | `_chrono_key` no longer depends on input-derived ids. Input position is used only to separate notes that are identical in every other field. |
| §5 duplicate supplied ids | **Default `disambiguate`:** `<id>#dupK` in (row, voice, chronological) order, with the original kept in `supplied_event_id` and the disambiguation reported in `search_notes`. **`error`** raises `ValueError`. Nothing is discarded. | The default is `disambiguate` because two existing Stage 2b tests use fixtures that reuse ids. Defaulting to `error` would have required editing them, and the audit asked for all 60 tests to be preserved. This is recorded here for review. |
| §6 public references | **Lookup contract:** each `Occurrence.events` holds one `EventRef` per note, with the original `source` object, `chronological_index`, `input_index`, exact timing, timing source and all pitch provenance. | `source` and `input_index` are excluded from equality, because they describe how the input was built. |
| §6 configuration validation | Integer parameters must be `int` (not `bool`/`float`); `include_nested` a `bool`; `methods` a non-empty sequence of names; `duplicate_event_ids` in {disambiguate, error}. | Raises `ValueError` |
| §6 completeness | `search_complete` means complete **within the configured bounds**. `unrestricted_search_complete` additionally requires that `max_length` excluded nothing. `search_scope` gives, per method, the minimum length, the maximum length searched, the longest run and the status. | New result fields, with defaults |

## 2. Evidence

### Negative baseline
`tests/test_group_discovery_stage2b_identity.py` (11 tests), run on the pre-revision engine: **10 of 11 fail** (3 failures, 7 errors, exit 1).
- The one test that passes on the old engine, `test_unspecified_and_named_voices_never_share_a_key`, is a **guard**: a voice literally named `"None"` must stay distinct from an unspecified voice. The old key also met that, so it is not counted as negative-baseline evidence.
- The collision itself is covered by `test_auditor_reproduction_empty_voice_is_unspecified`.

### The auditor's reproduction, before and after (`auditor_repro_BEFORE.txt` / `_AFTER.txt`)

| | Before | After |
|---|---|---|
| None and `""` voices | 2 "monophonic" streams that share one key; 2 raw occurrences, **1 independent**, 0 families | **1 stream** (unspecified voice) of 6 notes containing simultaneous onsets, reported as `polyphonic_unsupported` |
| Anonymous 6-note passage, reversed | ids `('r#0','r#1','r#2')` became `('r#5','r#4','r#3')`; results unequal | identical generated keys; **results equal** |

### Focused verification (exit codes)

| Check | Result |
|---|---|
| All group-discovery tests | **71/71** (15 original + 16 Stage 2a + 29 Stage 2b, **unchanged**, + 11 identity), exit 0 |
| `verify_group_discovery.py` | 22/22, exit 0 |
| Defect probes | 5/14 confirmed (the retained limitations), exit 0 |
| Stage 2b development evaluation | **44/44**, exit 0. 8/8 intended relations; the recurrence results are unchanged. |
| Stage 2b mutation check | 7/7 mutants killed, exit 0 |

### Full regression
See §3.

## 3. Full regression

Command: `python acceptance/run_acceptance.py --windows-device`, Windows, CPython 3.15.2, 2026-11-27 06:14 UTC (`evidence/stage2b_identity/acceptance_run.txt`). The exit codes are the child processes' own.

| Step | Result |
|---|---|
| Suite | **349 run, 335 passed, 14 skipped** (gated device tests), 0 failures or errors, exit 0. This is 338 + 11 identity tests. |
| Real Windows device | 14/14, exit 0 |
| Scripts | 7/7 required exit 0; both optional scripts (present) exit 0 |
| JOB-03 requirements | A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE; A21 regression only |
| Runner | **exit 0** |

The native access violation did not occur in this single run. It remains **unresolved**, and there were no automatic retries.

---

## 4. Addendum (Revision 3): global identifier uniqueness

**Audit finding:** the disambiguation did not reserve existing keys before allocating suffixes. For example, `["x", "x", "x#dup1", …]` gave `('x#dup1', 'x#dup2', 'x#dup1', …)`, which is not unique.

**Correction:** `_build_streams` in `music_model/recurrence_discovery.py` only.
1. It reserves every existing key: unique, duplicated, supplied and generated.
2. It retires each duplicated key and gives every instance the smallest free `#dupK`, reserving it immediately, in (row, voice, chronological) order.
3. It **asserts** that all reported keys are globally unique.

Unique supplied keys are unchanged, and the originals stay in `EventRef.supplied_event_id`. The default policy is still `disambiguate`, and `error` is unchanged. Specification §5 is updated.

**Tests** (`tests/test_group_discovery_stage2b_unique_ids.py`, 8 tests):
- an existing id matching a proposed suffix (the auditor's reproduction);
- multiple occupied suffixes;
- a collision with a generated anonymous key;
- reversed input order;
- collisions across rows and voices;
- supplied ids preserved in the event references;
- strict rejection of each collision kind;
- a seeded 200-case randomized uniqueness property.

**Negative baseline** (pre-correction engine): **5 of 8 fail** (exit 1). The 3 that pass there are guards for existing behaviour: strict mode, the supplied-id references, and the generated-key case, which the old allocation happened to resolve uniquely.

**The auditor's reproduction:**
- before: `('x#dup1', 'x#dup2', 'x#dup1', 'a', 'b', 'c')`, not unique;
- after: `('x#dup2', 'x#dup3', 'x#dup1', 'a', 'b', 'c')`, unique.

Files: `auditor_repro_BEFORE.txt` / `_AFTER.txt`.

**Focused verification** (`evidence/stage2b_unique_ids/focused_verification.txt`):

| Check | Result |
|---|---|
| Group-discovery tests | **79/79** (the 71 existing, unchanged, + 8), exit 0 |
| `verify_group_discovery.py` | 22/22, exit 0 |
| Stage 2b development evaluation | 44/44, exit 0; results identical to R2 apart from wall-clock timings |

**Full regression:** see §5.

## 5. Full regression (Revision 3)

Command: `python acceptance/run_acceptance.py --windows-device`, Windows, CPython 3.15.2, 2026-11-27 06:29 UTC (`evidence/stage2b_unique_ids/acceptance_run.txt`). The exit codes are the child processes' own.

| Step | Result |
|---|---|
| Suite | **357 run, 343 passed, 14 skipped** (gated device tests), 0 failures or errors, exit 0. This is 349 + 8 uniqueness tests. |
| Real Windows device | 14/14, exit 0 |
| Scripts | 7/7 required exit 0; both optional scripts (present) exit 0 |
| JOB-03 requirements | A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE; A21 regression only |
| Runner | **exit 0** |

The native access violation did not occur in this run. It remains **unresolved**, and there were no automatic retries.
