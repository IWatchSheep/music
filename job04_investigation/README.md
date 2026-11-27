# JOB-04 Investigation and Validation Harness

This folder holds the research harness used to evaluate JOB-04 against ground truth that is fixed when each passage is constructed, plus the independent held-out verifier. It uses the standard library only. Run every command from the project root.

| Command | Purpose | Exit code | Output |
|---|---|---|---|
| `PYTHONPATH=. python job04_investigation/job04_heldout_audit.py` (PowerShell: `$env:PYTHONPATH='.'; python job04_investigation/job04_heldout_audit.py`) | **Stage 2c independent held-out verifier**, supplied by ChatGPT and kept byte-identical. 17 controlled passages; six methods at lengths 3–5; exhaustive pair sets compared with a direct value-by-value oracle; 886 checks. Run by `acceptance/run_acceptance.py` as a required script. | 0 when all checks pass; 1 otherwise | stdout only |
| `python job04_investigation/run_stage2b_evaluation.py` | Stage 2b development-set evaluation of `discover_sound_groups()` on 13 frozen passages, with comparison controls; 44 asserted expectations | 0 when every expectation holds; 1 if any fails; 2 on a harness error | `results/stage2b_evaluation.json`, `results/stage2b_examples.txt` |
| `python job04_investigation/run_stage2b_performance.py` | Performance and complexity observations (wall-clock; data, not pass/fail) | 0 when the run completes; 2 on a harness error | stdout only |
| `python job04_investigation/run_baseline_validation.py` | Baseline: the legacy boundary sifters A–D, the fixed-width control and the count-matched 100-seed random control on 13 controlled passages | 0 when the run completes (data, not pass/fail); 2 on a harness error | `results/baseline_validation.json` |
| `python job04_investigation/defect_probes.py` | 14 concrete defect probes of the boundary engine | 0 when the run completes; 2 on a harness error | `results/defect_probes.json` |

- **`fixtures.py`**: the designed development passages and their ground truth (boundaries, phrase instances, recurrence relations). It is deterministic, and the one random passage uses a recorded seed.
- **`results/`** is generated output. It is **not** part of the publication, and the acceptance runner does not run the scripts that write it.
- **Parameters:** identical to `verify_group_discovery.py`. Nothing was tuned to the held-out verifier.
- **Reports** (project root): `JOB_04_BASELINE_INVESTIGATION.md`, `JOB_04_STAGE2A_REPORT.md`, `JOB_04_STAGE2B_SPECIFICATION.md`, `JOB_04_STAGE2B_REPORT.md`, `JOB_04_STAGE2B_IDENTITY_REVISION.md`, and the completion record `JOB_04_COMPLETION_RECORD.md`.

These results establish tested mathematical relation correctness on controlled symbolic passages. They do not establish general musical phrase significance.
