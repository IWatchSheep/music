# JOB-04 Publication Manifest (revision 2)

**Status:** **APPROVED FOR PUBLICATION.**
- ChatGPT completed its final independent review of `JOB_04_PUBLICATION_REVIEW_R2.zip`: SHA-256 `1f569a6bcd6cd261ae2ceb9724ba16a601dddcdf1964b0f8b8c290e0a65450a9`, approved manifest SHA-256 `8549d4361b7c104dd3049ca7a4eec6249421722fa768ecf48e7d06959e2081d9`.
- The Author authorized staging, commit and push to `IWatchSheep/music` `main` (2026-11-27).
- **After that approval, exactly two files changed:**
  - `JOB_04_COMPLETION_RECORD.md`: its §11 records the review and the authorization;
  - this manifest: this status block, and the regenerated hashes.

  The other 85 files are byte-identical to the approved archive, and no production code or test changed. The approved archive is preserved unchanged.
**Prepared:** 2026-11-27 (UTC) by Claude Opus 5.5.
**Authorizations in R2:**
- ChatGPT's publication audit authorized the coverage test, the two README status lines and the `.gitignore` line.
- The Author approved the path sanitization on 2026-11-27.

**This file is part of the publication** and is the record of the JOB-04 publication boundary. Its Git-state section describes the state *before* the commit.

## 1. Git state before the commit

- **Branch:** `main`. **HEAD (published JOB-03 checkpoint):** `e1a11e7d5b03a44621f177e8bce5aa504d726334`.
- **Index:** empty.
- **Modified tracked files (7):**
  - `.gitignore`;
  - `README.md`;
  - `JOB_02_COMPLETION_RECORD.md`;
  - four files in `acceptance/`.
- **New files for the commit:** 26, counting this manifest.
- **Untracked and excluded:** everything in §4.
- **Hashes** are of the working-copy bytes (Windows; `core.autocrlf=true`), which are exactly the bytes in the review archive. Git stores LF-normalized blobs for CRLF files. The held-out verifier has LF line endings, so its committed blob is byte-identical to the supplied file.

## 2. The publication tree (87 files) = the commit result

The commit changes **33 files**: **7 modified** and **26 new**. The other **54 tracked files are unchanged**.

`JOB_04_PUBLICATION_REVIEW_R2.zip` contains exactly these 87 files at their publication paths, and nothing else.

### 2.1 Files changed by the commit (33)

| File | Bytes | Change | SHA-256 |
|---|---:|---|---|
| `.gitignore` | 129 | MODIFIED: 1 line added, `job04_investigation/results/`; every existing rule kept byte-identical | `b982b902bce24b145cc23f1372aa05dbea00dcef74a21df4ceaa5da48d01d1af` |
| `JOB_02_COMPLETION_RECORD.md` | 34096 | MODIFIED: path sanitization only (lines 299, 327) | `85a2c80efe79c306f084b15d140535cb692d162a17807f4896290d09fe0de194` |
| `README.md` | 115030 | MODIFIED: line 595 (Stage 2a correction), 649 (path sanitization), 714 and 1018 (JOB-04 status) | `4522cc6e2f157b0253301b99293f42be7f1ff6456ee70921cf4ba8763df2ff61` |
| `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md` | 40112 | MODIFIED: regenerated from the R2 publication-tree run | `d1faec5f221376fbf2fcde5d47726eddf6ab93b8455071eaf5560be214915336` |
| `acceptance/README.md` | 6370 | MODIFIED: JOB-04 scripts and requirements described | `2a6de92c770f6ec66f809c98b838d6a30737f1451d4479eb96cf60d45a2393cc` |
| `acceptance/acceptance_matrix.json` | 43503 | MODIFIED: acceptance-2.1; G01-G09; G03 requires the coverage test; A22 script sets | `9c7a58be30fe3a2a8053dc9a00aa4fe6c030a8c33350b32dab90da7af569c67b` |
| `acceptance/run_acceptance.py` | 17445 | MODIFIED: 9 required scripts; 1 optional; PYTHONPATH for scripts | `8b4c3c852972308f6712170f09efbab921316ea0830edffaccffad5fc9e64cdc` |
| `music_model/group_discovery.py` | 42149 | NEW | `541fa23f528b125946705d682f79788fb24633def420ff35494433f1f3dcf2ff` |
| `music_model/recurrence_discovery.py` | 28696 | NEW | `f533324d3e4748ed5f3737e965d0c0092a4837b6f4d96b0e05b56b6b0bc97216` |
| `tests/test_group_discovery.py` | 15691 | NEW | `202535932ff40aaea0c8312bf6596623d7d61b2758c3bf63609fb0498028f109` |
| `tests/test_group_discovery_stage2a.py` | 8048 | NEW | `ba75cdbe332643dc04d17746637bcf7441086279b821a794fcb28d4a946f6b1c` |
| `tests/test_group_discovery_stage2b.py` | 14346 | NEW | `c7b3cb7863ad908fd073600234232885992fd354bdfc3a8d93c420b192b7e6e7` |
| `tests/test_group_discovery_stage2b_identity.py` | 8103 | NEW | `4e098610aa252c377d5457871a7a53b5e9b361729ff3cd625873fc21e5c79d42` |
| `tests/test_group_discovery_stage2b_unique_ids.py` | 5446 | NEW | `f3effea117c568deffcb3f2d0523de1898434f34ca963c43626b471a48c248fe` |
| `tests/test_group_discovery_stage2c_coverage.py` | 3302 | NEW (R2): authorized coverage test (1 test) | `0d84f88fe5e5b883cc66f093c5383bfa3dc1682072ef9f700a34b89eedd5f998` |
| `verify_group_discovery.py` | 20876 | NEW | `db93db4e780b9bc22d314b5b7d8df8aa5713446fcf990e8a3c948ccb9b822eba` |
| `job04_investigation/job04_heldout_audit.py` | 5306 | NEW: ChatGPT's verifier, byte-identical to the supplied file | `713be72a2d050fc0782d35a760afdafd6cc469cda05fb4c186d314df49e54846` |
| `job04_investigation/README.md` | 2740 | NEW (revised after R3: documents all harness scripts) | `02975eefc0a8bf468651751db32ffd1e9c50021837b4e357fbb7bd10c7d86989` |
| `job04_investigation/fixtures.py` | 10867 | NEW | `4c1b4829bcebd676fe791d647b38c1f7670c8b1f9db2c4c630c94df55a80e17e` |
| `job04_investigation/run_stage2b_evaluation.py` | 16533 | NEW | `af22016c790714b532a71ee5a53fb6a9a0aba6897a14e53186dcd3e6d7b8edc8` |
| `job04_investigation/run_baseline_validation.py` | 7701 | NEW | `41eab40df46e66f3cfc650a6d749fd028d727f61f6c590eefd9b45ac9f8ea2cf` |
| `job04_investigation/defect_probes.py` | 9069 | NEW | `66a963928b7aae8dc9746d1757fd670df278caef3f8b76e03a34d6bc9177c0d4` |
| `job04_investigation/run_stage2b_performance.py` | 2892 | NEW | `b98565ed5aaf352c7852072d3ed757afba9ee39f1f1410965cc6ece8bfd345d9` |
| `JOB_04_BASELINE_INVESTIGATION.md` | 28357 | NEW | `097137c8fd051debb86ff7336b431ff069d86a9d7418569e18f6f00f8a58c49c` |
| `JOB_04_STAGE2A_REPORT.md` | 13515 | NEW | `5cb16425b66c6908d86de693ae5f247af98ed3b81b8c567617142180aeb244c0` |
| `JOB_04_STAGE2B_SPECIFICATION.md` | 14827 | NEW | `85fa1d7db7952f98cddbdd20e01ccdb382f424c2e10147b2a0d7b3347678cca2` |
| `JOB_04_STAGE2B_REPORT.md` | 16010 | NEW | `ea59bac684e43d0b5260b1375744d2dd439bb2203c9176866ed94b165373b93e` |
| `JOB_04_STAGE2B_IDENTITY_REVISION.md` | 8106 | NEW | `d4614f2a614cd898336f4bbf43956afb98e1d86b04e24bbe5cddc4c965b100d6` |
| `JOB_04_COMPLETION_RECORD.md` | 14317 | NEW | `b2b18241f32dafe159793dddb7cfcd364d7acb1c285d6fda65b34a0ade9f69e1` |
| `JOB_04_VERIFICATION_LOG.txt` | 80075 | NEW | `9323f71fc7096783a24ed222ce77bc53c8e9dfe37f3b5d3771df16c245b8fa92` |
| `JOB_04_REMAINING_LIMITATIONS.md` | 10288 | NEW | `a9ccd4906ed3ef390e53aef8ac1e03271c9f7fb2b40c66c3c388c5a630d1ccaa` |
| `JOB_04_PATH_SANITIZATION.md` | 2864 | NEW (R2): sanitization record | `d0035a17e2d2d35e0ad27a2d459c468d7fd4e1cd4fe655062978161bad706776` |
| `JOB_04_PUBLICATION_MANIFEST.md` | — | NEW | (this file; a file cannot contain its own hash; reported with the archive) |

Changes since R1 (`JOB_04_PUBLICATION_REVIEW.zip`, `d377db81…`):
- **New test** `tests/test_group_discovery_stage2c_coverage.py`: 1 test, authorized by ChatGPT. It passes on the correct engine and fails on the "transposition ignores inter-onset intervals" mutant (`JOB_04_VERIFICATION_LOG.txt` §5.3). No production code changed.
- **`acceptance/acceptance_matrix.json`:** G03 requires the new test (version `acceptance-2.1`).
- **`acceptance/README.md`:** now says 80 JOB-04 tests.
- **`acceptance/ACCEPTANCE_COVERAGE_MATRIX.md`:** regenerated from the R2 run.
- **`README.md`:**
  - the two authorized JOB-04 status lines (714, 1018) are applied;
  - path sanitization at line 649;
  - the Stage 2a correction at line 595 is preserved.
- **`.gitignore`:** `job04_investigation/results/` added. The existing rules are byte-identical, including the pre-existing BOM and mixed line endings.
- **`JOB_02_COMPLETION_RECORD.md`:** path sanitization only (`JOB_04_PATH_SANITIZATION.md`).
- **New record** `JOB_04_PATH_SANITIZATION.md`.
- **Updated records:**
  - the completion record;
  - the verification log (R1 sections kept as history; R2 sections 10–13);
  - the limitations report (the coverage gap closed; the A21 wording follows the audit);
  - this manifest.
- **Byte-identical to R1, and to the reviewed R3 or supplied versions:**
  - both production files;
  - the 79 earlier tests;
  - the held-out verifier;
  - `verify_group_discovery.py`;
  - the research harness;
  - the five stage reports.

Unchanged:
- `music.txt`;
- all JOB-01–JOB-03 production code, tests and fixtures;
- every Author statement;
- every other job status;
- every historical test result.

### 2.2 Unchanged tracked files (54; identical to HEAD)

| File | Bytes | SHA-256 |
|---|---:|---|
| `JOB_02_VERIFICATION_LOG.txt` | 38061 | `552d20a26b332429ba7242e1ea0464af34419634e24edf08f50d48b04f1152b7` |
| `JOB_03_COMPLETION_RECORD.md` | 52735 | `810d98e5ad545cfbf1f566cb1bf2f34b715e19fba1f726bb185a607a87d3a448` |
| `JOB_03_PUBLICATION_MANIFEST.md` | 14780 | `359f65644e67941f02953aa1e3bc0ced7c2821034c5e50b6849165b95184a06d` |
| `JOB_03_REMAINING_LIMITATIONS.md` | 3205 | `20dac8f370e81943972091931b40eec01ff53cf8c9987d18470ad82773cea79f` |
| `JOB_03_VERIFICATION_LOG.txt` | 168311 | `54ac85a15b28d00e9b7a5b1b4210b73b527940779c0cda872956f97033272097` |
| `acceptance/unittest_json.py` | 3214 | `a6bec89e1facfc2080f6c5bf9a5de6acba3d9a6f30c8953cf1f03bc7b4014a83` |
| `docs/audio_playback_architecture.md` | 77251 | `0e178ca6637e7ffacb2e435fcad20c97334906e3e6439fc4d4ee23efa0ed46af` |
| `docs/audio_sheet_adapter_spec.md` | 17281 | `7bbfc41cb991509dd17be12ee9ce6bff13dc3a120a2678ef1d23079412d214c9` |
| `main.py` | 498 | `dd023140dec3456f91d3e84e63cf33c142f2e9c00cf852670f0be259411854fb` |
| `music.txt` | 12682 | `4b0b2b530a2d1dd02fc49d3b4dc21f31f69993b332ffffa694f5d8cb14ec5a4c` |
| `music_gui/__init__.py` | 368 | `d9c24aea668ad67949c37e26ce0a7024c5044055643a09057a56e767eea1f25d` |
| `music_gui/audio_playback.py` | 88363 | `9e6a9254cd691d0d436c04e18f48bc5ccd742558c2bbc3dab5e316c9e6ac412f` |
| `music_gui/coordinates.py` | 9493 | `ce3b0e9614730d1492cb29070a4c29b662c9c5ea3c7df6680d083d3a10899aec` |
| `music_gui/dual_view.py` | 5432 | `bf61dd1a7862a22b90e0f400ada8d1b2709080095a834c3a22b30e1df1b580dd` |
| `music_gui/gui_style.py` | 3033 | `e2c3e39521dcc87083d39bea99e0c52d0850baf51ecb5b5345b47271feed311c` |
| `music_gui/main_window.py` | 67370 | `1a3638df040a7c47bca9510d94639a9145028e09eb3dd074139cf032c66efb53` |
| `music_gui/timeline_canvas.py` | 46989 | `78bd4bb4ab92242c88606eff328c79003ba021da33b43ea5b05c738c37a51a60` |
| `music_model/__init__.py` | 2775 | `408aca6c3303982c99e58ad3afbf4f249ead6a9ebffecaa784596ab2ebb87e0f` |
| `music_model/audio_importer.py` | 25966 | `04e988da66fb1f5c660ee329972bc09ad47794a8d06668d11361ed2c27eaa4a5` |
| `music_model/constant_row.py` | 4002 | `b628527f4be0e9325fbe0557afccace6b5529b51cf2e516f2291a2f885f9b32e` |
| `music_model/datasets.py` | 11139 | `cf14740dc91e5f195dd76d79edaeae38ff1719d132555bcd646f8e7df48747df` |
| `music_model/development_profile.py` | 12919 | `a05371f8e717fed0bb2331f5cecdc453d0f7905da2fdebd3279911be05a6d1ff` |
| `music_model/midi_fixture.py` | 9318 | `e75c77c9e1782a2c9f5893db977ae2c573cc84e52fab13db3979e64a3776d42a` |
| `music_model/midi_importer.py` | 25365 | `c73b2129f4756e7ed7564123b2fb7cf78c408a83ba42e0fbcebc5928020f62c1` |
| `music_model/musicxml_importer.py` | 43754 | `c6b2633726e6d7b7de41609882dafb6896a437c51ebe5b5569ecfda588838803` |
| `music_model/passage_format.py` | 5798 | `f8be30c78b0bf68668772dab4fd071e7d5c2d8d3a1dda606e02b2878a44cbf90` |
| `music_model/song.py` | 11311 | `5f736cedd7ac9fc01a14f8e26a18a32f43afd461ca8e8c0a42627458dbcbe4a2` |
| `music_model/sound_event.py` | 17498 | `6f3538bae275376d42c9bb54b9020b551498fc66f39f03fbc566ba68a6555b85` |
| `music_model/temporary_row.py` | 4326 | `a3a01be5e6bbdc8715fdbdaaec26768bfa96c3b33c535c6e6a0403d77c05e8b4` |
| `music_model/timeline.py` | 11168 | `24c26caae9608d057f0c3f6f4a563551632925db1208930feab8f457d271a3e1` |
| `requirements.txt` | 473 | `826ef9084e2b96642ae96429e2836efa616bbb8157a1ba88d999c52e3b90a240` |
| `tests/__init__.py` | 47 | `ffd670b1284d81e1f8fa515c634b7195f387ddf623599ddce5df09da19bf5088` |
| `tests/fixtures/JOB03_test.wav` | 352844 | `defffd2a0178fb1cd4d0002d2901afc42169782f38966b4b467bbc4232149c70` |
| `tests/test_audio_and_musicxml.py` | 63004 | `24c204c64824ad120cde969242f200ce6e59871675866523196822b2ef421e96` |
| `tests/test_audio_playback.py` | 103754 | `11b0a42cd505943bca9ca4c7afcdecc9b138cd59a351acfdb1db7f11bd8b36fb` |
| `tests/test_development_profile.py` | 12856 | `6ac9035cf70ffd085a6c5b885b6a7730564c2a3b1750f4070345cc113a53b558` |
| `tests/test_group_units.py` | 6681 | `a90ff3011bc4addbbc48f60b546bff30d7bc624a981c5385b62ea2926b40f07b` |
| `tests/test_group_units_gui.py` | 12122 | `1e4bbbde6d1db0d414566139df3872db384ce2b60683390f578018393b142e71` |
| `tests/test_gui_phase2.py` | 11105 | `6e7b0001998deda758e4ff138bf64b4a23f2808473f2ecc98583ff9dd0071793` |
| `tests/test_gui_smoke.py` | 7932 | `681d69796195e9dc3fe438eebf5e7b4f48238bb8bb89c36a1f6230e1e487237b` |
| `tests/test_master_columns_gui.py` | 9115 | `edb7d8f20bd7a0f70ecbb0d2eac939d4c546f0e8266ee95b1c926d37d31a3c4d` |
| `tests/test_midi_and_passage.py` | 13769 | `fa501674ccc8ffb73785802c2124f14b8a23928ff2e52684080ce4c47d928c4d` |
| `tests/test_playback_consolidated.py` | 58730 | `5a6e97d8a48a43f9f8f23c6c013c3fe642b3c9737721d123d8005327f9228491` |
| `tests/test_playback_windows_device.py` | 21444 | `672c73d987b9068a1bfb30f320979d8af8b6039e34e72fc041fe09a7417c7413` |
| `tests/test_song_timeline.py` | 10885 | `9d735e9b7b7b2a46ab3021cea2aef7bfc8f2b30d7344946e31d0bad3ebe6f6c3` |
| `tests/test_timeline_model.py` | 16270 | `712673cee397f0e179a06c5814882933eff222f72cdbfcb4a58ad148d8b58a7f` |
| `tests/test_wav_import_regression.py` | 40636 | `28835ae0f7d3750c278ee6f8c2d84de6ad364e513492e335ec299b52b761b681` |
| `verify_audio_and_sheet_adapters.py` | 52353 | `de0c704ea5f34bf7d56d2661d238d94b52054c6b6392dae8c4c2e57b037bc4f8` |
| `verify_development.py` | 4888 | `1992c91696d3e7137bf8d2a0fac0e799badd40dfc548d4af57c6a887fb2499f0` |
| `verify_group_units.py` | 19522 | `032c004c1d4bc90ea9a9b52b68bdef0e359855d0086a5670d6c912f538426d3c` |
| `verify_midi_import.py` | 9184 | `05d45c2ebe65d259bb8414c8e2d4909c072a0b3719a505d8a19ae1279e0422bd` |
| `verify_playback_transport.py` | 15380 | `6945384b5baf3bfb73d148eefcd2e3b1e37fb61bc328f51b33bd01cd56989f26` |
| `verify_progressive.py` | 7636 | `bf0f6f8e00bff6d8c959c7779a6af8a2603eb4074014ff928bf7407bcffb7b96` |
| `verify_proof.py` | 7155 | `19ffdee6fcd90a55f7761714c0207d11c8088d376144f4528677e3e51faff126` |

## 3. Verification of this tree

All runs used Windows 11 and CPython 3.15.2, with `acceptance/run_acceptance.py --windows-device`. The exit codes are the child processes' own. Details: `JOB_04_VERIFICATION_LOG.txt`.

ChatGPT's expectation was 358 tests: 344 passed and 14 gated device skips, with the device tests 14/14 separately. The table records what was actually obtained.

| Tree | Suite | Device | Scripts | Result |
|---|---|---|---|---|
| **R2 run 1: the R2 tree, with the R1 records** (scratch copy) | run=358 passed=344 skipped=14 failures=0 errors=0 (exit 0) | device {'exit_code': 0, 'run': 14, 'failures': 0, 'errors': 0, 'skipped': 0} | required scripts exit 0: 8/9; row merger OUTSIDE PUBLICATION SCOPE (absent) | ACCEPTANCE CHECKS FAILED; **runner exit 1** |
| **R2 run 2, the confirmation: the final R2 tree** (scratch copy; identical to this archive except the 3 post-run documentation files below) | run=358 passed=344 skipped=14 failures=0 errors=0 (exit 0) | device {'exit_code': 0, 'run': 14, 'failures': 0, 'errors': 0, 'skipped': 0} | required scripts exit 0: 9/9; row merger OUTSIDE PUBLICATION SCOPE (absent) | ACCEPTANCE CHECKS PASSED; **runner exit 0** |

- **R2 run 1 FAILED, and that result stands.**
  - The cause was an A21 access violation (0xC0000005) in `verify_audio_and_sheet_adapters.py` (JOB-02 code; `audio_importer.py:437`).
  - A02, A03, A19 and A22 FAILED because they map that script. Every other check in the run passed.
  - The run is preserved as separate evidence (`%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\r2_acceptance_run_FAILED_20261127T103436Z\`).
  - Run 2 was the planned confirmation of the final tree, made once. It is not an automatic retry.
- **Requirement statuses in a run without the native fault:**
  - A01–A19, A22 and G01–G08 PASS;
  - A20 NO-AUTOMATED-COVERAGE (acoustic synchronization unmeasured);
  - A21 regression detection only (native access violation **unresolved**);
  - G09 NO-AUTOMATED-COVERAGE (a documentation item).
- **R1 evidence** (still valid for the unchanged parts): the rule check with the held-out verifier removed gave `MISSING (required)` and runner exit 1; the held-out sensitivity check found 5 of 6 mutants (log §5.2, §7).
- **A21:** the pure-Python failure and its successful single rerun are preserved as separate evidence files (log §4). Its cause remains unresolved, and there were no automatic retries.
- **No excluded file is required:**
  - the tree has no `verify_row_merger.py`, `results/`, evidence or crash-log files, and passes;
  - no published Python file imports an excluded file (log §12).
- **After the first R2 run, only documentation changed:**
  - the JOB-04 records (completion record, verification log, limitations report, sanitization record);
  - the regenerated `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md`;
  - this manifest.

  The confirmation run used the final tree. After it, exactly three documentation files changed, to record that run:
  - `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md`, regenerated from its report (run 1 failed, so it was not regenerated from run 1);
  - `JOB_04_VERIFICATION_LOG.txt`, which gains §13;
  - this manifest.

  None of them is read by any test or script. The other 84 files are byte-identical to the confirmed tree.
- **Privacy:**
  - no published file contains a personal absolute path;
  - scratch and project paths are written `<scratch>` and `<project>`, and home paths `%USERPROFILE%`;
  - the public remote name `IWatchSheep/music` appears in `JOB_04_BASELINE_INVESTIGATION.md`.
- **Independent re-run:** `python acceptance/run_acceptance.py` on Windows, or `xvfb-run -a python3 acceptance/run_acceptance.py` on Linux. Without a Windows device, the expected result is one more skip than on Windows (the device-dependent GUI cleanup test). This is inferred from JOB-03 and was not run on Linux here.

## 4. Excluded (must remain untracked)

| Category | Files |
|---|---|
| Row-merger experiment | `verify_row_merger.py` |
| Generated research output | `job04_investigation/results/` (now ignored) |
| Temporary crash log | `JOB03_WAV_CRASH_LOG.txt` |
| Review ZIP archives (all preserved) | `JOB_02_INDEPENDENT_REVIEW.zip`; `JOB_03_*.zip` (9); `JOB_04_BASELINE_REVIEW.zip`, `JOB_04_STAGE2A_REVIEW.zip`, `JOB_04_STAGE2B_REVIEW.zip`, `JOB_04_STAGE2B_R2_REVIEW.zip`, `JOB_04_STAGE2B_R3_REVIEW.zip`, `JOB_04_PUBLICATION_REVIEW.zip` (R1), `JOB_04_PUBLICATION_REVIEW_R2.zip` (this review) |
| Generated verification output | `acceptance_results/` (ignored) |
| Caches and environments | `__pycache__/`, `*.pyc`, `.venv/`, `.idea/` (ignored) |
| Evidence outside the repository | `%USERPROFILE%\JOB_04_A21_EVIDENCE_20261127\` (A21 failure and rerun); `%USERPROFILE%\JOB_04_PUBLICATION_R2_BACKUP_20261127\` (unsanitized originals); `%USERPROFILE%\JOB_04_EXPERIMENTAL_BACKUP_20261126_211422\`; the `evidence/` folders inside the earlier review archives |

## 5. Exact staging list and proposed commands (NOT executed; only after final Author authorization)

Staging list (33 paths: 7 modified, 26 new), added by name and never by directory:

```text
.gitignore
JOB_02_COMPLETION_RECORD.md
README.md
acceptance/ACCEPTANCE_COVERAGE_MATRIX.md
acceptance/README.md
acceptance/acceptance_matrix.json
acceptance/run_acceptance.py
music_model/group_discovery.py
music_model/recurrence_discovery.py
tests/test_group_discovery.py
tests/test_group_discovery_stage2a.py
tests/test_group_discovery_stage2b.py
tests/test_group_discovery_stage2b_identity.py
tests/test_group_discovery_stage2b_unique_ids.py
tests/test_group_discovery_stage2c_coverage.py
verify_group_discovery.py
job04_investigation/job04_heldout_audit.py
job04_investigation/README.md
job04_investigation/fixtures.py
job04_investigation/run_stage2b_evaluation.py
job04_investigation/run_baseline_validation.py
job04_investigation/defect_probes.py
job04_investigation/run_stage2b_performance.py
JOB_04_BASELINE_INVESTIGATION.md
JOB_04_STAGE2A_REPORT.md
JOB_04_STAGE2B_SPECIFICATION.md
JOB_04_STAGE2B_REPORT.md
JOB_04_STAGE2B_IDENTITY_REVISION.md
JOB_04_COMPLETION_RECORD.md
JOB_04_VERIFICATION_LOG.txt
JOB_04_REMAINING_LIMITATIONS.md
JOB_04_PATH_SANITIZATION.md
JOB_04_PUBLICATION_MANIFEST.md
```

```powershell
git add -- .gitignore JOB_02_COMPLETION_RECORD.md README.md acceptance/ACCEPTANCE_COVERAGE_MATRIX.md acceptance/README.md acceptance/acceptance_matrix.json acceptance/run_acceptance.py music_model/group_discovery.py music_model/recurrence_discovery.py tests/test_group_discovery.py tests/test_group_discovery_stage2a.py tests/test_group_discovery_stage2b.py tests/test_group_discovery_stage2b_identity.py tests/test_group_discovery_stage2b_unique_ids.py tests/test_group_discovery_stage2c_coverage.py verify_group_discovery.py job04_investigation/job04_heldout_audit.py job04_investigation/README.md job04_investigation/fixtures.py job04_investigation/run_stage2b_evaluation.py job04_investigation/run_baseline_validation.py job04_investigation/defect_probes.py job04_investigation/run_stage2b_performance.py JOB_04_BASELINE_INVESTIGATION.md JOB_04_STAGE2A_REPORT.md JOB_04_STAGE2B_SPECIFICATION.md JOB_04_STAGE2B_REPORT.md JOB_04_STAGE2B_IDENTITY_REVISION.md JOB_04_COMPLETION_RECORD.md JOB_04_VERIFICATION_LOG.txt JOB_04_REMAINING_LIMITATIONS.md JOB_04_PATH_SANITIZATION.md JOB_04_PUBLICATION_MANIFEST.md
git diff --cached --stat        # expect exactly 33 files: 7 modified, 26 new
git status --short              # verify_row_merger.py, the ZIPs and the crash log stay untracked; results/ is ignored
git commit -m "Complete JOB-04 recurrence discovery with documented limitations"
git push origin main
```

## 6. README changes in this tree (applied, authorized)

1. **Line 595:** the Stage 2a factual correction (Milestone 5A, Passage 1). It was authorized earlier and is preserved unchanged.
2. **Line 649:** path sanitization only (`%USERPROFILE%\PycharmProjects\calculator`). See `JOB_04_PATH_SANITIZATION.md`.
3. **Line 714:** the JOB-04 `Current Status` becomes `[COMPLETED WITH DOCUMENTED LIMITATIONS]`, with the limitations disclosed (the text proposed in R1 §6, unchanged).
4. **Line 1018:** in the milestone tree, `JOB-04: Sifter Discovery Engine [COMPLETED WITH DOCUMENTED LIMITATIONS]`.

No other README line changes. Lines 710 and 712 (the original deliverable and verification wording) are kept as historical wording.
