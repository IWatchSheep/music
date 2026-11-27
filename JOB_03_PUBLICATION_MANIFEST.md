# JOB-03 Publication Manifest (revision 2)

**Status:** proposed for publication. ChatGPT is to review `JOB_03_PUBLICATION_REVIEW.zip`, then the Author gives final authorization. **Nothing has been staged, committed or pushed.**
**Prepared:** 2026-11-27 (UTC) by Claude Opus 5.5. This follows ChatGPT's final engineering acceptance and the Author's authorization of the runner, README.md and .gitignore changes.
**This file is part of the publication** and is the record of the JOB-03 publication boundary. Its Git-state section describes the state *before* the commit.

## 1. Git state before the commit

- **Branch:** `main`. **Starting checkpoint (HEAD):** `f7042f91068c154ab9f9ec703dac8e6dd84b32d2`.
- **JOB-03 implementation baseline:** `9965050b50ceb41d5c04384a488a8f1debb9a643`.
- **Index:** empty.
- **Modified tracked files (7):** the 5 production files, `README.md` and `.gitignore`.
- **New files for the commit:** 17, counting this manifest.
- **Untracked and excluded:** everything in §4.

## 2. The publication tree (61 files) = the commit result

The commit changes **24 files**: **7 modified** and **17 new**. The other **37 tracked files are unchanged**.

`JOB_03_PUBLICATION_REVIEW.zip` contains exactly these 61 files at their publication paths, and nothing else.

### 2.1 Files changed by the commit (24)

| File | Bytes | Change | SHA-256 |
|---|---:|---|---|
| `.gitignore` | 100 | MODIFIED (tracked) | `ea4db0b6d2a727c60ff17f4a45ce74cb86280db4bb98f984f0ed6bf697ce3773` |
| `README.md` | 114127 | MODIFIED (tracked) | `2d2fcf5479be882b5b6aa815028a8dadb74e6a10bc5a1bbf7298f4d453912d42` |
| `music_gui/coordinates.py` | 9493 | MODIFIED (tracked) | `ce3b0e9614730d1492cb29070a4c29b662c9c5ea3c7df6680d083d3a10899aec` |
| `music_gui/main_window.py` | 67370 | MODIFIED (tracked) | `1a3638df040a7c47bca9510d94639a9145028e09eb3dd074139cf032c66efb53` |
| `music_gui/timeline_canvas.py` | 46989 | MODIFIED (tracked) | `78bd4bb4ab92242c88606eff328c79003ba021da33b43ea5b05c738c37a51a60` |
| `music_model/song.py` | 11311 | MODIFIED (tracked) | `5f736cedd7ac9fc01a14f8e26a18a32f43afd461ca8e8c0a42627458dbcbe4a2` |
| `music_model/timeline.py` | 11168 | MODIFIED (tracked) | `24c26caae9608d057f0c3f6f4a563551632925db1208930feab8f457d271a3e1` |
| `music_gui/audio_playback.py` | 88363 | NEW | `9e6a9254cd691d0d436c04e18f48bc5ccd742558c2bbc3dab5e316c9e6ac412f` |
| `verify_playback_transport.py` | 15380 | NEW | `6945384b5baf3bfb73d148eefcd2e3b1e37fb61bc328f51b33bd01cd56989f26` |
| `tests/test_audio_playback.py` | 103754 | NEW | `11b0a42cd505943bca9ca4c7afcdecc9b138cd59a351acfdb1db7f11bd8b36fb` |
| `tests/test_playback_consolidated.py` | 58730 | NEW | `5a6e97d8a48a43f9f8f23c6c013c3fe642b3c9737721d123d8005327f9228491` |
| `tests/test_playback_windows_device.py` | 21444 | NEW | `672c73d987b9068a1bfb30f320979d8af8b6039e34e72fc041fe09a7417c7413` |
| `tests/test_wav_import_regression.py` | 40636 | NEW | `28835ae0f7d3750c278ee6f8c2d84de6ad364e513492e335ec299b52b761b681` |
| `tests/fixtures/JOB03_test.wav` (binary) | 352844 | NEW | `defffd2a0178fb1cd4d0002d2901afc42169782f38966b4b467bbc4232149c70` |
| `acceptance/run_acceptance.py` | 16813 | NEW | `2708ed9d9e7144d0d65b364eb3c419017a2590619c94adf5a2998be98234b3fe` |
| `acceptance/unittest_json.py` | 3214 | NEW | `a6bec89e1facfc2080f6c5bf9a5de6acba3d9a6f30c8953cf1f03bc7b4014a83` |
| `acceptance/acceptance_matrix.json` | 26759 | NEW | `78e8cbb4abd6dbec8c829c83372517e2bf07c33a583c0b085f034777fce06265` |
| `acceptance/README.md` | 4261 | NEW | `a19e5a311addbcf6cf0d97c5ca0d39d4f1745b12f3e08b08820726498e085d42` |
| `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md` | 26079 | NEW | `9171ba46032c3e83ce4d529016ebed7f716724d6529dded9ac5e2a5d4198a8a4` |
| `docs/audio_playback_architecture.md` | 77251 | NEW | `0e178ca6637e7ffacb2e435fcad20c97334906e3e6439fc4d4ee23efa0ed46af` |
| `JOB_03_COMPLETION_RECORD.md` | 52735 | NEW | `810d98e5ad545cfbf1f566cb1bf2f34b715e19fba1f726bb185a607a87d3a448` |
| `JOB_03_VERIFICATION_LOG.txt` | 168311 | NEW | `54ac85a15b28d00e9b7a5b1b4210b73b527940779c0cda872956f97033272097` |
| `JOB_03_REMAINING_LIMITATIONS.md` | 3205 | NEW | `20dac8f370e81943972091931b40eec01ff53cf8c9987d18470ad82773cea79f` |
| `JOB_03_PUBLICATION_MANIFEST.md` | — | NEW | (this file; a file cannot contain its own hash; reported with the archive) |

What changed, by category:
- **Production:** 5 modified files, plus 1 new file (`music_gui/audio_playback.py`). No mathematical algorithm changed; `audio_importer.py`, `constant_row.py` and `development_profile.py` are identical to HEAD.
- **Tests:** 4 new test modules, plus the fixture `tests/fixtures/JOB03_test.wav` (the Author's controlled file, byte-identical to the original).
- **Verification:** 1 new standalone script, `verify_playback_transport.py`.
- **Acceptance package:** 5 new files in `acceptance/`, including the authorized required/optional script correction.
- **Documentation and records:** the architecture document, the completion record, the verification log, the remaining-limitations report and this manifest.
- **Authorized edits to tracked files:**
  - `README.md`: exactly 4 lines (690, 700, 1016, 1017). JOB-02 → `[COMPLETED]`. JOB-03 → `[COMPLETED WITH DOCUMENTED LIMITATIONS]`, referencing `JOB_03_REMAINING_LIMITATIONS.md` and disclosing both the unmeasured acoustic synchronization and the unresolved native access violation. Every Author statement and every other job status is unchanged.
  - `.gitignore`: one line added, `acceptance_results/`. All existing rules are preserved.
- **Unchanged:** `music.txt` (not modified).

### 2.2 Unchanged tracked files (37; identical to HEAD)

| File | Bytes | SHA-256 |
|---|---:|---|
| `JOB_02_COMPLETION_RECORD.md` | 34098 | `03275d27f8e70be43e5a419bbc5854707949b0fdcf8d4a37ad5a6075c9771c8f` |
| `JOB_02_VERIFICATION_LOG.txt` | 38061 | `552d20a26b332429ba7242e1ea0464af34419634e24edf08f50d48b04f1152b7` |
| `docs/audio_sheet_adapter_spec.md` | 17281 | `7bbfc41cb991509dd17be12ee9ce6bff13dc3a120a2678ef1d23079412d214c9` |
| `main.py` | 498 | `dd023140dec3456f91d3e84e63cf33c142f2e9c00cf852670f0be259411854fb` |
| `music.txt` | 12682 | `4b0b2b530a2d1dd02fc49d3b4dc21f31f69993b332ffffa694f5d8cb14ec5a4c` |
| `music_gui/__init__.py` | 368 | `d9c24aea668ad67949c37e26ce0a7024c5044055643a09057a56e767eea1f25d` |
| `music_gui/dual_view.py` | 5432 | `bf61dd1a7862a22b90e0f400ada8d1b2709080095a834c3a22b30e1df1b580dd` |
| `music_gui/gui_style.py` | 3033 | `e2c3e39521dcc87083d39bea99e0c52d0850baf51ecb5b5345b47271feed311c` |
| `music_model/__init__.py` | 2775 | `408aca6c3303982c99e58ad3afbf4f249ead6a9ebffecaa784596ab2ebb87e0f` |
| `music_model/audio_importer.py` | 25966 | `04e988da66fb1f5c660ee329972bc09ad47794a8d06668d11361ed2c27eaa4a5` |
| `music_model/constant_row.py` | 4002 | `b628527f4be0e9325fbe0557afccace6b5529b51cf2e516f2291a2f885f9b32e` |
| `music_model/datasets.py` | 11139 | `cf14740dc91e5f195dd76d79edaeae38ff1719d132555bcd646f8e7df48747df` |
| `music_model/development_profile.py` | 12919 | `a05371f8e717fed0bb2331f5cecdc453d0f7905da2fdebd3279911be05a6d1ff` |
| `music_model/midi_fixture.py` | 9318 | `e75c77c9e1782a2c9f5893db977ae2c573cc84e52fab13db3979e64a3776d42a` |
| `music_model/midi_importer.py` | 25365 | `c73b2129f4756e7ed7564123b2fb7cf78c408a83ba42e0fbcebc5928020f62c1` |
| `music_model/musicxml_importer.py` | 43754 | `c6b2633726e6d7b7de41609882dafb6896a437c51ebe5b5569ecfda588838803` |
| `music_model/passage_format.py` | 5798 | `f8be30c78b0bf68668772dab4fd071e7d5c2d8d3a1dda606e02b2878a44cbf90` |
| `music_model/sound_event.py` | 17498 | `6f3538bae275376d42c9bb54b9020b551498fc66f39f03fbc566ba68a6555b85` |
| `music_model/temporary_row.py` | 4326 | `a3a01be5e6bbdc8715fdbdaaec26768bfa96c3b33c535c6e6a0403d77c05e8b4` |
| `requirements.txt` | 473 | `826ef9084e2b96642ae96429e2836efa616bbb8157a1ba88d999c52e3b90a240` |
| `tests/__init__.py` | 47 | `ffd670b1284d81e1f8fa515c634b7195f387ddf623599ddce5df09da19bf5088` |
| `tests/test_audio_and_musicxml.py` | 63004 | `24c204c64824ad120cde969242f200ce6e59871675866523196822b2ef421e96` |
| `tests/test_development_profile.py` | 12856 | `6ac9035cf70ffd085a6c5b885b6a7730564c2a3b1750f4070345cc113a53b558` |
| `tests/test_group_units.py` | 6681 | `a90ff3011bc4addbbc48f60b546bff30d7bc624a981c5385b62ea2926b40f07b` |
| `tests/test_group_units_gui.py` | 12122 | `1e4bbbde6d1db0d414566139df3872db384ce2b60683390f578018393b142e71` |
| `tests/test_gui_phase2.py` | 11105 | `6e7b0001998deda758e4ff138bf64b4a23f2808473f2ecc98583ff9dd0071793` |
| `tests/test_gui_smoke.py` | 7932 | `681d69796195e9dc3fe438eebf5e7b4f48238bb8bb89c36a1f6230e1e487237b` |
| `tests/test_master_columns_gui.py` | 9115 | `edb7d8f20bd7a0f70ecbb0d2eac939d4c546f0e8266ee95b1c926d37d31a3c4d` |
| `tests/test_midi_and_passage.py` | 13769 | `fa501674ccc8ffb73785802c2124f14b8a23928ff2e52684080ce4c47d928c4d` |
| `tests/test_song_timeline.py` | 10885 | `9d735e9b7b7b2a46ab3021cea2aef7bfc8f2b30d7344946e31d0bad3ebe6f6c3` |
| `tests/test_timeline_model.py` | 16270 | `712673cee397f0e179a06c5814882933eff222f72cdbfcb4a58ad148d8b58a7f` |
| `verify_audio_and_sheet_adapters.py` | 52353 | `de0c704ea5f34bf7d56d2661d238d94b52054c6b6392dae8c4c2e57b037bc4f8` |
| `verify_development.py` | 4888 | `1992c91696d3e7137bf8d2a0fac0e799badd40dfc548d4af57c6a887fb2499f0` |
| `verify_group_units.py` | 19522 | `032c004c1d4bc90ea9a9b52b68bdef0e359855d0086a5670d6c912f538426d3c` |
| `verify_midi_import.py` | 9184 | `05d45c2ebe65d259bb8414c8e2d4909c072a0b3719a505d8a19ae1279e0422bd` |
| `verify_progressive.py` | 7636 | `bf0f6f8e00bff6d8c959c7779a6af8a2603eb4074014ff928bf7407bcffb7b96` |
| `verify_proof.py` | 7155 | `19ffdee6fcd90a55f7761714c0207d11c8088d376144f4528677e3e51faff126` |

## 3. Verification of this tree

All runs were on Windows with CPython 3.15.2, using `acceptance/run_acceptance.py --windows-device`. The exit codes are the child Python processes' own.

| Tree | Suite | Device | Scripts | Runner |
|---|---|---|---|---|
| **Exact publication tree** (scratch copy of these 61 files) | 278 run, **264 passed, 14 skipped**, 0 failures or errors | 14/14 | 7/7 required exit 0; 2 optional `OUTSIDE PUBLICATION SCOPE (absent)` | **exit 0**, ACCEPTANCE CHECKS PASSED |
| Complete local project (including the unpublished JOB-04 and row-merger files) | 293 run, 279 passed, 14 skipped, 0 failures or errors | 14/14 | 7/7 required, plus 2/2 optional (present) exit 0 | exit 0 |

- **Requirements on the publication tree:** A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE (acoustic synchronization unmeasured); A21 regression detection only (native access violation **unresolved**).
- **Rule checks:**
  - a missing required script gives FAIL and exit 1;
  - a present optional script that fails gives FAIL and exit 1;
  - an absent optional script is reported as outside scope;
  - a present optional script that passes gives PASS.
- **After the verified run, only documentation changed:**
  - `JOB_03_COMPLETION_RECORD.md` and `JOB_03_VERIFICATION_LOG.txt` (results recorded);
  - `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md` (regenerated from that run's report);
  - `acceptance/README.md` (describes the script rule);
  - this manifest.

  No code, test, fixture, runner or matrix file changed after the run.
- **Sanitized before staging (Author-authorized, 2026-11-27):** personal absolute Windows paths in the JOB-03 documentation were replaced with the generic placeholders `<project>`, `%USERPROFILE%` and `%TEMP%` (24 occurrences: 2 in JOB_03_COMPLETION_RECORD.md, 19 in JOB_03_VERIFICATION_LOG.txt, 3 in this manifest). Only path prefixes changed: applying the replacement rules to the original files reproduces the sanitized files exactly. No test outcome, production code or test file was changed; the hashes above are the post-sanitization values. The unsanitized originals are preserved locally outside the repository. The pre-existing calculator-repository path at README.md line 649, already published at HEAD, is outside the four authorized README lines and was left unchanged.
- **Independent re-run:** `python acceptance/run_acceptance.py` on Windows, or `xvfb-run -a python3 acceptance/run_acceptance.py` on Linux. Without a Windows device, expect 278 run, 263 passed, 15 skipped (the extra skip is the device-dependent GUI cleanup test), with the two optional scripts reported as outside scope.

## 4. Excluded (must remain untracked)

| Category | Files |
|---|---|
| Temporary crash log | `JOB03_WAV_CRASH_LOG.txt` |
| Review ZIP archives | `JOB_02_INDEPENDENT_REVIEW.zip`, `JOB_03_INDEPENDENT_REVIEW.zip`, `JOB_03_CONSOLIDATED_REFACTOR_REVIEW.zip`, `JOB_03_CONSOLIDATED_REFACTOR_REVIEW_R2.zip`, `JOB_03_WAV_CRASH_REVIEW.zip`, `JOB_03_WAV_CRASH_REVIEW_R2.zip`, `JOB_03_WAV_CRASH_REVIEW_R3.zip`, `JOB_03_ACCEPTANCE_REVIEW.zip`, `JOB_03_PUBLICATION_REVIEW.zip` |
| Generated verification output | `acceptance_results/` (now ignored) |
| Caches and environments | `__pycache__/`, `*.pyc`, `.venv/`, `.idea/` (ignored) |
| JOB-04 group discovery | `music_model/group_discovery.py`, `tests/test_group_discovery.py`, `verify_group_discovery.py` |
| Row-merger experiment | `verify_row_merger.py` |
| Evidence outside the repository | `%USERPROFILE%\JOB_03_WAV_CRASH_EVIDENCE\`, `%USERPROFILE%\JOB_03_CONSOLIDATED_EVIDENCE\`, `%USERPROFILE%\JOB_03_REV13_BACKUP_20261126_065003\` |

- **Boundary check:** no published file imports the excluded JOB-04 or row-merger files.
- **Noted for reviewers:** some records cite evidence paths outside the repository (`JOB_03_WAV_CRASH_EVIDENCE/...`). Those files are preserved locally and inside the earlier review archives; they are not part of the publication.

## 5. Proposed commands (NOT executed; only after final Author authorization)

```powershell
git add .gitignore README.md
git add music_gui/coordinates.py music_gui/main_window.py music_gui/timeline_canvas.py music_model/song.py music_model/timeline.py
git add music_gui/audio_playback.py verify_playback_transport.py
git add tests/test_audio_playback.py tests/test_playback_consolidated.py tests/test_playback_windows_device.py tests/test_wav_import_regression.py tests/fixtures/JOB03_test.wav
git add acceptance/run_acceptance.py acceptance/unittest_json.py acceptance/acceptance_matrix.json acceptance/README.md acceptance/ACCEPTANCE_COVERAGE_MATRIX.md
git add docs/audio_playback_architecture.md JOB_03_COMPLETION_RECORD.md JOB_03_VERIFICATION_LOG.txt JOB_03_REMAINING_LIMITATIONS.md JOB_03_PUBLICATION_MANIFEST.md
git diff --cached --name-only    # must list exactly the 24 files of section 2.1
git status --short               # JOB-04/row-merger files, ZIPs and the crash log must remain untracked
```

Files are named explicitly; never use `git add .` or `git add -A`. The commit message and the push are confirmed by the Author at that time.
