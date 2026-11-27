<!-- Snapshot of the acceptance run on the exact proposed JOB-03 publication tree (Windows, --windows-device, 2026-11-27T04:49:10Z). Regenerate with acceptance/run_acceptance.py. -->

# JOB-03 Acceptance Report (20261127T044910Z)

- Python: `3.15.2` on `Windows-11-10.0.26300-SP0`
- **Overall: ACCEPTANCE CHECKS PASSED**
- Complete suite: run 278, **passed 264, skipped 14**, failures 0, errors 0 (python exit code 0)
- Real Windows device tests: run 14, failures 0, errors 0, skipped 0 (python exit code 0)
- Standalone scripts: verify_audio_and_sheet_adapters.py = 0, verify_development.py = 0, verify_group_units.py = 0, verify_midi_import.py = 0, verify_playback_transport.py = 0, verify_progressive.py = 0, verify_proof.py = 0, verify_group_discovery.py = OUTSIDE PUBLICATION SCOPE (absent), verify_row_merger.py = OUTSIDE PUBLICATION SCOPE (absent)

> Simulated and device timing figures are software/driver measurements, not acoustic measurements.

## Requirements

| ID | Requirement | Automated (this run) | Windows device | Author observation | Remaining unverified |
|---|---|---|---|---|---|
| A01 | Author's actual JOB03_test.wav is the regression fixture (PCM mono 16-bit 44.1 kHz, 176,400 frames, SHA-256 pinned) | **PASS** (1/1 tests) | n/a | Author heard four different-sounding beeps from JOB03_test.wav (expected original audio). | — |
| A02 | JOB03_test.wav (four continuous pitches) imports through the GUI as exactly ONE continuous sound event covering 0-4000 ms (documented JOB-02 silence-based segmentation; pitch E4) | **PASS** (2/2 tests; required scripts 1/1) | n/a | Author marked 'Sound events: UNSURE' (did not know how to count events); now covered automatically. | — |
| A03 | Four notes separated by silence are detected as four events with expected pitches (JOB-02 tolerances: exact MIDI, frequency within 1 %, boundaries within 20 ms) | **PASS** (1/1 tests; required scripts 1/1) | PASS | — | — |
| A04 | Original PCM recording preserved: the exact file bytes are the playback source and the bytes handed to the device | **PASS** (4/4 tests) | PASS | Audible playback PASS; Author heard the original four beeps. | — |
| A05 | GUI stays responsive during WAV analysis (handler returns < 0.5 s; Tk loop gap < 0.5 s) | **PASS** (2/2 tests) | n/a | GUI responsiveness PASS. | — |
| A06 | Correct dataset identity and audio-source badge after WAV import | **PASS** (3/3 tests) | n/a | Dataset name PASS; Audio badge PASS. | — |
| A07 | Natural completion at the exact source duration (including fractional-ms durations); cursor rests at the end with no highlight | **PASS** (7/7 tests; required scripts 1/1) | PASS | Natural completion PASS. | — |
| A08 | A stale WAV result is rejected after another source or mode is selected (latest selection wins); a single analysis worker at a time | **PASS** (5/5 tests) | n/a | Author marked 'Stale WAV import: UNSURE'; covered deterministically (gate-controlled worker completion). | — |
| A09 | A stale analysis error shows no dialog; a current analysis error is still reported and leaves the previous source intact | **PASS** (3/3 tests) | n/a | — | — |
| A10 | Non-selections do not cancel a pending import (cancelled dialog; display-only Row 1 toggle) | **PASS** (2/2 tests) | n/a | — | — |
| A11 | Row 1 display change preserves the audio source (PCM bytes, synthesis flag, dataset, badge, events, transport state/position) while stopped, playing and paused; the Row 1 display itself changes; equivalent for MusicXML and MIDI; one transport load per import | **PASS** (3/3 tests; required scripts 1/1) | n/a | Row 1 while playing PASS; Row 1 while paused PASS. | — |
| A12 | Playback state, cursor position and highlighted events agree with one coherent transport snapshot (half-open intervals, polyphony) | **PASS** (13/13 tests; required scripts 1/1) | PASS | WAV re-test step 3 (playhead advances and stops at 4.000 s) reported PASS as 'Natural completion'. | Visual/audio synchronization as perceived (see A20). |
| A13 | Pause and resume (pause holds the coordinate; resume continues from it; rapid cycles) | **PASS** (7/7 tests; required scripts 1/1) | PASS | Row 1 while paused PASS (pause used during the re-test). | Audible stop/restart of sound on pause/resume not separately reported (optional physical observation P1). |
| A14 | Seek while stopped, paused and playing (clamping, failed seek never publishes the destination) | **PASS** (8/8 tests; required scripts 1/1) | PASS | — | Audible result of dragging the seek slider not reported (optional physical observation P2). |
| A15 | Looping restarts from 0 each cycle without error, including fractional durations (restart is NOT seamless) | **PASS** (5/5 tests; required scripts 1/1) | PASS | — | Audible loop gap not observed by the Author (optional physical observation P3); known non-seamless restart. |
| A16 | Source replacement releases the previous source (MCI alias closed, temp WAV removed, view reset) | **PASS** (5/5 tests) | PASS | Source replacement PASS. | — |
| A17 | Shutdown: closing the window stops audio, closes the device, removes the temp WAV, and ignores pending/obsolete analysis | **PASS** (4/4 tests) | PASS | Shutdown PASS. | Closing while sound is audibly playing not specifically reported (optional physical observation P4). |
| A18 | Thread ownership: only the Tk thread drives the transport and the MCI device; cross-thread commands are refused | **PASS** (4/4 tests) | PASS | — | — |
| A19 | Synthesized (MusicXML/MIDI) playback uses exact source timing; failure states are coherent; no cumulative software drift | **PASS** (5/5 tests; required scripts 3/3) | n/a | Author reported MusicXML import and playback work (2026-11-26). | — |
| A20 | Physical acoustic synchronization of sound and picture (<= 20 ms engineering target) | **NO-AUTOMATED-COVERAGE** (0/0 tests) | n/a | — | No acoustic or microphone measurement exists; cannot be established by software tests. |
| A21 | Native access violation (2026-11-26 08:30) - root cause | **PASS (regression only; see remaining_unverified)** (1/1 tests) | n/a | Latest Author WAV re-test completed without a crash (this does not establish elimination). | UNRESOLVED: native memory corruption source (CPython 3.15.2 defect vs. system/driver instability) not established; the child-process test only detects a crash if one occurs in that run. |
| A22 | No regression of previously accepted behaviour (complete suite; the seven required standalone verification scripts; the two unpublished experimental scripts only when present) | **PASS** (1/1 tests; required scripts 7/7; optional scripts: verify_group_discovery.py=OUTSIDE PUBLICATION SCOPE (absent), verify_row_merger.py=OUTSIDE PUBLICATION SCOPE (absent)) | PASS | — | — |

## Test mapping

### A01 — PASS
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_fixture_is_the_authors_file`

### A02 — PASS
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`
- [pass] `tests.test_wav_import_regression.TestNonSilentImportInChildProcess.test_author_equivalent_file_imports_without_crashing`
- [exit 0] script `verify_audio_and_sheet_adapters.py`

### A03 — PASS
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_import_play_complete_and_replace_source`
- [exit 0] script `verify_audio_and_sheet_adapters.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciNonSilentWavImport.test_gui_imports_non_silent_wav_into_real_device_and_releases_it`

### A04 — PASS
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_import_play_complete_and_replace_source`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_normal_import_publishes_exactly_once`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_04_pcm_wav_duration_and_trailing_silence`
- [device: pass] `tests.test_playback_windows_device.TestRealMciNonSilentWavImport.test_gui_imports_non_silent_wav_into_real_device_and_releases_it`

### A05 — PASS
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_import_play_complete_and_replace_source`
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`

### A06 — PASS
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`
- [pass] `tests.test_wav_import_regression.TestRow1SourcePreservation.test_wav_pcm_survives_row1_toggles_in_every_transport_state`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_normal_import_publishes_exactly_once`

### A07 — PASS
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`
- [pass] `tests.test_playback_consolidated.TestD2FractionalDurationCompletion.test_fractional_22070_frame_wav_completes_at_exact_duration`
- [pass] `tests.test_playback_consolidated.TestD2FractionalDurationCompletion.test_exact_1000_ms_control_completes`
- [pass] `tests.test_playback_consolidated.TestD2CompletionPredicateAcrossDurations.test_natural_completion_for_every_case`
- [pass] `tests.test_playback_consolidated.TestD2CompletionPredicateAcrossDurations.test_no_premature_completion_without_evidence`
- [pass] `tests.test_playback_consolidated.TestD7GuiSnapshotRendering.test_natural_completion_and_stop`
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_10_natural_end_of_piece`
- [exit 0] script `verify_playback_transport.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2_fractional_22070_frame_wav_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2b_fractional_22071_frame_wav_rounding_down_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2c_fractional_48khz_wav_rounding_down_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r3_exact_1000ms_control_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciThroughMusicGUI.test_gui_end_to_end_playback_completion_and_teardown`

### A08 — PASS
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_progressive_selection_discards_obsolete_success`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_mode_without_transport_reload_also_supersedes`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_musicxml_source_loaded_during_analysis_is_kept`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_new_import_refused_while_obsolete_worker_computes_then_allowed`
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_second_open_while_analysing_is_refused_not_queued`

### A09 — PASS
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_obsolete_failure_shows_no_dialog_and_keeps_badge`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_current_failure_is_still_reported`
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_analysis_error_is_reported_on_tk_thread`

### A10 — PASS
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_cancelled_dialog_is_not_a_source_selection`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_row1_toggle_is_not_a_source_selection`

### A11 — PASS
- [pass] `tests.test_wav_import_regression.TestRow1SourcePreservation.test_wav_pcm_survives_row1_toggles_in_every_transport_state`
- [pass] `tests.test_wav_import_regression.TestRow1SourcePreservation.test_musicxml_and_midi_sources_survive_row1_toggles`
- [pass] `tests.test_wav_import_regression.TestRow1SourcePreservation.test_genuine_source_selection_still_replaces_wav`
- [exit 0] script `verify_development.py`

### A12 — PASS
- [pass] `tests.test_audio_playback.TestGUIPlaybackIntegration.test_16_timeline_canvas_playhead_cursor_rendering`
- [pass] `tests.test_audio_playback.TestGUIPlaybackIntegration.test_17_active_sound_bar_highlighting_and_restoration`
- [pass] `tests.test_audio_playback.TestGUIPlaybackIntegration.test_18_main_window_transport_wiring`
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_07_exact_event_boundaries_half_open_interval`
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_08_simultaneous_polyphony`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_09_single_device_query_and_atomic_snapshot_agreement`
- [pass] `tests.test_audio_playback.TestWindowsMciCommandControlPath.test_08_visual_callbacks_and_active_event_membership_consistency`
- [pass] `tests.test_playback_consolidated.TestD5CoherentSnapshots.test_every_snapshot_is_internally_coherent_and_ordered`
- [pass] `tests.test_playback_consolidated.TestD5CoherentSnapshots.test_tick_callback_payload_comes_from_one_snapshot`
- [pass] `tests.test_playback_consolidated.TestD7GuiSnapshotRendering.test_stale_and_foreign_snapshots_are_rejected`
- [pass] `tests.test_playback_consolidated.TestHalfOpenMembershipDuringPlayback.test_boundaries_adjacent_overlapping_silence_and_completion`
- [pass] `tests.test_playback_consolidated.TestHalfOpenMembershipDuringPlayback.test_exact_rational_boundaries_are_respected`
- [pass] `tests.test_wav_import_regression.TestAuthorControlledWavFixture.test_actual_file_gui_import_one_event_pcm_and_natural_completion`
- [exit 0] script `verify_playback_transport.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r1_ordinary_playback_advances_without_mci_263`
- [device: pass] `tests.test_playback_windows_device.TestRealMciThroughMusicGUI.test_gui_end_to_end_playback_completion_and_teardown`

### A13 — PASS
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_03_pause_without_unwanted_advancement`
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_04_resume_from_exact_position`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_05_rapid_pause_resume_cycles`
- [pass] `tests.test_audio_playback.TestWindowsMciCommandControlPath.test_02_pause_and_resume_issue_appropriate_commands`
- [pass] `tests.test_playback_consolidated.TestD1ThreadOwnership.test_pause_halts_device_after_scheduled_updates`
- [pass] `tests.test_playback_consolidated.TestD3DeviceStateReconciliation.test_resume_refuses_to_send_302_when_device_not_paused`
- [pass] `tests.test_playback_consolidated.TestD4D6Scheduling.test_rapid_pause_play_keeps_at_most_one_pending_update`
- [exit 0] script `verify_playback_transport.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r4_pause_halts_device_and_resume_continues`

### A14 — PASS
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_06_forward_and_backward_seeking`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_10_seek_stopped_playing_paused_boundaries_and_zero_latency`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_09a_failed_seek_preserves_consistent_coordinates_and_visual_position`
- [pass] `tests.test_playback_consolidated.TestD3DeviceStateReconciliation.test_seek_while_paused_leaves_device_stopped_and_resume_uses_play_from`
- [pass] `tests.test_playback_consolidated.TestD3DeviceStateReconciliation.test_seek_while_playing_restarts_device`
- [pass] `tests.test_playback_consolidated.TestD3DeviceStateReconciliation.test_seek_beyond_device_length_is_clamped_not_282`
- [pass] `tests.test_playback_consolidated.TestD7GuiSnapshotRendering.test_seek_while_stopped_and_paused`
- [pass] `tests.test_playback_consolidated.TestTransactionsAndRecovery.test_failed_seek_while_playing_never_publishes_destination`
- [exit 0] script `verify_playback_transport.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r5_seek_while_paused_then_play`

### A15 — PASS
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_09_loop_boundaries`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_05_continuous_loop_remainder_preservation`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_10a_loop_restart_source_audio_preservation`
- [pass] `tests.test_playback_consolidated.TestD2CompletionPredicateAcrossDurations.test_looping_for_every_case`
- [pass] `tests.test_playback_consolidated.TestD2FractionalDurationCompletion.test_fractional_duration_looping`
- [exit 0] script `verify_playback_transport.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r6_fractional_duration_looping`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r6b_rounding_down_fractional_duration_looping`

### A16 — PASS
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_import_play_complete_and_replace_source`
- [pass] `tests.test_wav_import_regression.TestRow1SourcePreservation.test_genuine_source_selection_still_replaces_wav`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_04_stale_audio_cleanup_on_new_source`
- [pass] `tests.test_playback_consolidated.TestD8ResourceCleanup.test_load_replace_and_close_release_device_and_temp_files`
- [pass] `tests.test_playback_consolidated.TestD7GuiSnapshotRendering.test_source_replacement_resets_view`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r9_source_replacement_releases_previous_device`
- [device: pass] `tests.test_playback_windows_device.TestRealMciNonSilentWavImport.test_gui_imports_non_silent_wav_into_real_device_and_releases_it`

### A17 — PASS
- [pass] `tests.test_playback_consolidated.TestD7GuiSnapshotRendering.test_application_shutdown_closes_transport_and_cancels_updates`
- [pass] `tests.test_playback_consolidated.TestD8ResourceCleanup.test_close_while_playing_stops_then_closes`
- [pass] `tests.test_wav_import_regression.TestGuiWavImportPath.test_window_destroyed_during_analysis_ignores_result`
- [pass] `tests.test_wav_import_regression.TestStaleWavImportLifecycle.test_shutdown_with_obsolete_worker_running`
- [device: pass] `tests.test_playback_consolidated.TestD8GuiTeardownReleasesItsOwnTempWav.test_destroy_removes_the_application_temp_wav`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r8_close_releases_device_and_temp_file`
- [device: pass] `tests.test_playback_windows_device.TestRealMciThroughMusicGUI.test_gui_end_to_end_playback_completion_and_teardown`

### A18 — PASS
- [pass] `tests.test_playback_consolidated.TestD1ThreadOwnership.test_backend_refuses_cross_thread_commands_with_explicit_error`
- [pass] `tests.test_playback_consolidated.TestD1ThreadOwnership.test_transport_rejects_lifecycle_calls_from_non_owner_thread`
- [pass] `tests.test_playback_consolidated.TestD4D6Scheduling.test_tk_scheduler_drives_transport_on_tk_thread`
- [pass] `tests.test_playback_consolidated.TestD4D6Scheduling.test_obsolete_callback_cannot_restart_stopped_or_superseded_transport`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r7_cross_thread_command_is_refused_device_unaffected`

### A19 — PASS
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_14_preservation_of_exact_source_timing_metadata`
- [pass] `tests.test_audio_playback.TestDeterministicTransportControls.test_15_absence_of_cumulative_transport_drift`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_03_synthesizer_uses_rational_timing`
- [pass] `tests.test_audio_playback.TestDefectRegressions.test_defect_08_failure_state_transitions`
- [pass] `tests.test_playback_consolidated.TestTransactionsAndRecovery.test_failed_pause_shuts_audio_down_and_preserves_coordinate`
- [exit 0] script `verify_playback_transport.py`
- [exit 0] script `verify_audio_and_sheet_adapters.py`
- [exit 0] script `verify_midi_import.py`

### A20 — NO-AUTOMATED-COVERAGE

### A21 — PASS (regression only; see remaining_unverified)
- [pass] `tests.test_wav_import_regression.TestNonSilentImportInChildProcess.test_author_equivalent_file_imports_without_crashing`

### A22 — PASS
- [pass] `ALL (complete suite)`
- [exit 0] script `verify_audio_and_sheet_adapters.py`
- [exit 0] script `verify_development.py`
- [exit 0] script `verify_group_units.py`
- [exit 0] script `verify_midi_import.py`
- [exit 0] script `verify_playback_transport.py`
- [exit 0] script `verify_progressive.py`
- [exit 0] script `verify_proof.py`
- [optional; exit OUTSIDE PUBLICATION SCOPE (absent)] script `verify_group_discovery.py`
- [optional; exit OUTSIDE PUBLICATION SCOPE (absent)] script `verify_row_merger.py`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r1_ordinary_playback_advances_without_mci_263`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2_fractional_22070_frame_wav_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2b_fractional_22071_frame_wav_rounding_down_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r2c_fractional_48khz_wav_rounding_down_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r3_exact_1000ms_control_completes`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r4_pause_halts_device_and_resume_continues`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r5_seek_while_paused_then_play`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r6_fractional_duration_looping`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r6b_rounding_down_fractional_duration_looping`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r7_cross_thread_command_is_refused_device_unaffected`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r8_close_releases_device_and_temp_file`
- [device: pass] `tests.test_playback_windows_device.TestRealMciDevice.test_r9_source_replacement_releases_previous_device`
- [device: pass] `tests.test_playback_windows_device.TestRealMciNonSilentWavImport.test_gui_imports_non_silent_wav_into_real_device_and_releases_it`
- [device: pass] `tests.test_playback_windows_device.TestRealMciThroughMusicGUI.test_gui_end_to_end_playback_completion_and_teardown`

## Skipped tests in the complete suite

- `tests.test_playback_windows_device.TestRealMciDevice.test_r1_ordinary_playback_advances_without_mci_263`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r2_fractional_22070_frame_wav_completes`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r2b_fractional_22071_frame_wav_rounding_down_completes`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r2c_fractional_48khz_wav_rounding_down_completes`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r3_exact_1000ms_control_completes`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r4_pause_halts_device_and_resume_continues`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r5_seek_while_paused_then_play`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r6_fractional_duration_looping`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r6b_rounding_down_fractional_duration_looping`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r7_cross_thread_command_is_refused_device_unaffected`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r8_close_releases_device_and_temp_file`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciDevice.test_r9_source_replacement_releases_previous_device`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciNonSilentWavImport.test_gui_imports_non_silent_wav_into_real_device_and_releases_it`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)
- `tests.test_playback_windows_device.TestRealMciThroughMusicGUI.test_gui_end_to_end_playback_completion_and_teardown`: real-device tests are opt-in: set MUSIC_REAL_AUDIO_TESTS=1 (Windows only)

## Optional physical observations (need speakers; not required for automated acceptance)

- P1: Press Space during WAV playback: sound stops; press again: sound resumes (a small ~20 ms forward step of the playhead is a known limitation).
- P2: Drag the seek slider while playing: sound continues from the new position.
- P3: Enable Loop: playback restarts from the beginning; a short audible gap at the restart is a known limitation.
- P4: Close the window while sound is playing: sound stops and the application exits.
