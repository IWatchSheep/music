# Job Completion Record: JOB-03 — Real-Time Audio Playback and Synchronized Visual Transport

> **Status:** **JOB-03 ACCEPTED WITH DOCUMENTED LIMITATIONS by ChatGPT (independent final engineering acceptance, 2026-11-26) — AWAITING AUTHOR PUBLICATION AUTHORIZATION.** Author manual re-test: 10 PASS, 2 UNSURE (now covered by automated tests), 0 failures. Limitations: `JOB_03_REMAINING_LIMITATIONS.md`. Not yet published: nothing staged, committed or pushed.  
> **Original Starting Implementation Baseline:** `9965050b50ceb41d5c04384a488a8f1debb9a643`  
> **Current Official Documentation Checkpoint:** `f7042f91068c154ab9f9ec703dac8e6dd84b32d2`  
> **Previous Documentation Checkpoint:** `66dfc53`  
> **Current Working State:** Uncommitted working tree (nothing staged, committed or pushed)  
> **Protected Calculator Repository:** `17be078d` (not accessed or modified by this work)  
> **Review Archives:** `JOB_03_ACCEPTANCE_REVIEW.zip` (final acceptance package, current; SHA-256 86dacc89…384f423c); `JOB_03_WAV_CRASH_REVIEW.zip`, `_R2.zip`, `_R3.zip` (WAV corrections, preserved unchanged); `JOB_03_CONSOLIDATED_REFACTOR_REVIEW_R2.zip` (resubmission 2, preserved unchanged); `JOB_03_CONSOLIDATED_REFACTOR_REVIEW.zip` (resubmission 1, preserved unchanged); `JOB_03_INDEPENDENT_REVIEW.zip` (thirteenth revision, preserved unchanged)  
> **Implementer of the correction:** Claude Opus 5.5 (PyCharm terminal), 2026-11-26  
> **Architecture & Manual Guide:** `docs/audio_playback_architecture.md` (Section 7 describes the correction)  
> **Thirteenth-revision backup (outside repository):** `%USERPROFILE%\JOB_03_REV13_BACKUP_20261126_065003`  
> **Evidence workspace (outside repository):** `%USERPROFILE%\JOB_03_CONSOLIDATED_EVIDENCE`  

---

## 1. Permanent Schema Fields (README Section 9.2)

- **Job ID & Name:** `JOB-03` — Real-Time Audio Playback and Synchronized Visual Transport
- **Starting Validated Checkpoint:** `9965050`
- **Current Documentation Baseline:** `f7042f9`
- **Files Modified / Added:**
  - Added: `music_gui/audio_playback.py` (Transport state machine with explicit `TransportState.ERROR`, unified timing helper `_query_device_and_audible_progress`, single atomic update snapshot per tick update, segment start coordinate tracking across seek/resume without backward jumps, zero source audio skipping on loop restart, systematic lifecycle transaction discipline across play, pause, seek, stop, reset, and loop restart (DEFECT-09A, DEFECT-09B, DEFECT-09C, DEFECT-09D, DEFECT-09E), `Clock` abstraction, `AudioBackend` hierarchy with `WindowsMciAudioBackend`, `SimulatedAudioBackend`, and `NullAudioBackend`, multi-tier timing distinguishing software/device/audible positions, frozen position preservation during pause/resume, re-anchoring of buffer drainage on resume, device-governed completion and loop transitions, failure-safe state machine with deadlock-free thread joins, error callback dispatch, rejection of non-finite/negative coordinates and query exceptions during pause, cross-platform backend status initialization, polyphonic sine audio synthesizer with direct rational sample quantization and 5 ms anti-clipping envelopes, monotonic position tracking, half-open interval active sound event queries, seeking, and thread-safe callbacks)
  - Added: `tests/test_audio_playback.py` (Automated suite of 64 unit & integration tests covering all 15 deterministic controls, playhead cursor rendering, active sound bar boundary highlighting and outline restoration, Tkinter GUI transport bar wiring, 9 targeted regression tests for DEFECT-01 through DEFECT-05, 9 targeted regression tests for DEFECT-06 through DEFECT-08, 3 targeted regression tests for fourth audit items, 3 targeted regression tests for fifth audit items, 3 targeted regression tests for sixth audit items, 2 targeted regression tests for seventh audit items (DEFECT-10A, DEFECT-09A), 1 targeted regression test for eighth audit items (DEFECT-09B), 3 targeted regression tests for ninth audit items (DEFECT-09C, DEFECT-09D, DEFECT-09E), 2 targeted regression tests for tenth audit items (DEFECT-09F, DEFECT-09G), 1 targeted regression test for eleventh audit items (DEFECT-09H), 1 targeted regression test for twelfth audit items (DEFECT-09I Windows MCI recovery resumption), and 9 targeted deterministic command-level control path tests using production WindowsMciAudioBackend (TestWindowsMciCommandControlPath))
  - Added: `verify_playback_transport.py` (Standalone benchmark runner evaluating 8 benchmark scenarios, drift elimination benchmark, software synchronization latency, and polyphonic WAV synthesis, with 44/44 assertions verified)
  - Added: `docs/audio_playback_architecture.md` (Comprehensive architecture documentation, mathematical models, timing specifications, MCI driver details, multi-tier timing, explicit failure recovery state machine, author-operated interactive manual verification checklist with honest attribution, and recorded simulator results)
  - Added: `JOB_03_VERIFICATION_LOG.txt` (Full recorded terminal execution logs from automated test runs, dedicated benchmark runner, and all 9 standalone verification scripts)
  - Added: `JOB_03_COMPLETION_RECORD.md` (This document)
  - Added: `JOB_03_INDEPENDENT_REVIEW.zip` (Review archive containing all 51 production files, tests, scripts, and documentation)
  - Consolidated correction (2026-11-26), changes relative to the thirteenth revision:
    - `music_gui/audio_playback.py` (refactored): background `TransportTimer` thread removed; `Scheduler` / `TkScheduler` / `ManualScheduler`; owner-thread guards; `TransportSnapshot`; shared `_set_stationary` / `_fail` / `_publish` / `_deliver` transaction helpers; `DeviceObservation` and `WindowsMciAudioBackend.observe()` (mode + position reconciliation, end-of-media / early-stop latches); exact media-end completion; silent tail; integer-ms command clamping; `close()`; `MciThreadOwnershipError`, `TransportThreadError`, `TransportClosedError`; injectable `winmm` and `temp_dir`. Unchanged byte-for-byte: `SimulatedAudioBackend`, `NullAudioBackend`, `get_wav_duration_ms`, `synthesize_song_audio`.
    - `music_gui/main_window.py`: single snapshot renderer with stale rejection and a documented cursor policy; `TkScheduler`; `close()` on `destroy()`; error-surfacing slider and mode-switch stops.
    - `music_gui/timeline_canvas.py`: redraw re-applies the snapshot's own active IDs.
    - `verify_playback_transport.py`: printed wording of Scenarios 6 and 7 corrected; assertions and counters unchanged.
    - Added `tests/test_playback_consolidated.py` (44 deterministic D1–D8 tests, including the `FakeWinmm` behavioural model of MCI).
    - Added `tests/test_playback_windows_device.py` (10 opt-in real-device tests, silent WAV).
    - Updated `docs/audio_playback_architecture.md`, this record, and `JOB_03_VERIFICATION_LOG.txt`.
    - **No existing test was modified.** `music_model/*` and `music_gui/coordinates.py` are unchanged relative to the thirteenth revision. `README.md`, `music.txt`, group discovery and row merger are untouched.
  - Modified Tracked Files:
    - `music_gui/coordinates.py`: Extended `time_to_x` to accept float or int millisecond timestamps.
    - `music_gui/timeline_canvas.py`: Added `find_playback_cursor()`, `clear_playback_cursor()`, `set_playback_cursor(position_ms, active_event_ids, auto_scroll)`, original border tracking dictionary (`_sound_bar_original_borders`), playhead cursor rendering, crimson boundary highlighting (`outline="#dc2626", width=3.5`), and auto-scrolling.
    - `music_gui/main_window.py`: Added dark transport control toolbar (`#0f172a`), Play, Pause, Stop, Loop toggle, Time label (`mm:ss.mmm`), Audio Mode badge (`[Audio: Synthesized]` vs `[Audio: PCM WAV]`), error surfacing badge styling (`[Audio: Device Error]`) via `_handle_audio_error()`, draggable seek slider, spacebar / escape keyboard shortcuts, File menu import options ("Open Audio WAV..." and "Open MusicXML..."), thread-safe asynchronous GUI dispatch, clean destruction teardown, and transport reinitialization across view switches.
    - `music_model/timeline.py`: Added `get_active_events_at(time_ms)` evaluating half-open interval active events $[t_{\text{start}}, t_{\text{end}})$.
    - `music_model/song.py`: Delegated `SongTimeline.get_active_events_at(time_ms)` to underlying timeline.
- **Mathematical Methods & Formulas:**
  1. *Multi-Tier Timing Hierarchy & Single Authoritative Monotonic Coordinate:*
     $$t = t_0 + (T_{\text{clock}} - T_{\text{start}}) \times 1000$$
     Distinguishes three explicit timing tiers:
     - `software_transport_position_ms`: Monotonically advancing software clock time.
     - `device_position_ms`: Hardware/driver device position queried directly from audio hardware via standard-library ctypes winmm MCI.
     - `estimated_audible_position_ms`: Authoritative audible position accounting for hardware buffer latency:
       $$t_{\text{audible}} = \max(S, t_{\text{device}} - \text{buffer\_latency\_ms})$$
     Visual transport and playhead track the authoritative audible position, eliminating drift.
  2. *Single Authoritative Update Snapshot (DEFECT-09 Resolution):*
     In `step_tick()`, exactly ONE device query is dispatched per update. The single resulting progress coordinate $t_{\text{snapshot}}$ is delivered atomically to end-of-piece decisions, stored transport state, half-open active-event membership, visual playhead callback, and tick return value.
  3. *Seek and Resume Coordinate Semantics Across States (DEFECT-10 Resolution):*
     When a segment begins or seeks to start coordinate $S$:
     - During the buffer-fill interval ($t_{\text{device}} \in [S, S + L]$), DAC output is held at $S$: $t_{\text{audible}} = S$.
     - Once filled ($t_{\text{device}} \ge S + L$), audible output advances smoothly: $t_{\text{audible}} = t_{\text{device}} - L$.
     - Unified formula: $t_{\text{audible}} = \max(S, t_{\text{device}} - L)$.
     - Eliminates unexplained backward jumps upon resume after paused seek.
     - Source audio is never skipped to force visual alignment.
  4. *Loop Restart Source Audio Preservation (DEFECT-10A Resolution):*
     Loop restarts begin the backend at the intended source coordinate $t_{\text{start\_device}} = t_{\text{remainder}}$ without skipping buffer latency. Both visual transport and backend device coordinate restart at the exact remainder coordinate (e.g. 0.0 ms $\to$ 0.0 ms), preserving all source audio and applying the buffer-fill model consistently across loop boundaries.
  5. *Failed Seek Coordinate & Callback Integrity (DEFECT-09A Resolution):*
     When a backend seek operation fails, the transport preserves the last valid playback position across the internal state, ERROR state reporting, active-event membership, and visual playhead callbacks (`_notify_tick(pre_seek_pos)`). Unachieved seek targets are never published to listeners.
  6. *Failed Stop and Reset Coordinate & Callback Integrity (DEFECT-09B Resolution):*
     When backend `stop()` fails during a `stop()` or `reset()` operation, the transport transitions to `TransportState.ERROR`, preserves the last valid playback coordinate across internal state and active-event membership, and notifies visual listeners of the preserved coordinate (`self._notify_tick(pre_stop_pos)`). Unachieved zero-position destinations are never published to listeners upon shutdown failure.
  7. *Buffer Latency at Completion & Smooth Buffer Drainage (Capped & Uncapped):*
     Distinguishes device processing completion ($t_{\text{device}} \ge T_{\text{total}}$), estimated audible completion ($t_{\text{audible}} \ge T_{\text{total}}$), and physical acoustic completion.
     When $t_{\text{device}}$ reaches $T_{\text{total}}$, audible sound is at $T_{\text{total}} - \text{buffer\_latency\_ms}$. For devices where device position caps at $T_{\text{total}}$, the transport drains the buffer continuously using elapsed drain wall clock time:
     $$t_{\text{audible}} = \max\left(t_{\text{device}} - \text{buffer\_latency\_ms}, (T_{\text{total}} - \text{buffer\_latency\_ms}) + \text{drain\_elapsed}\right)$$
     reaching $T_{\text{total}}$ smoothly without terminal cursor jumps or stalls.
  8. *Authoritative Frozen Pause Snapshot & Drain Clock Re-Anchoring:*
     Upon pause, the transport captures and freezes:
     $$t_{\text{frozen\_device}} = t_{\text{device}}, \quad t_{\text{frozen\_audible}} = t_{\text{audible}}$$
     preventing software clock jumps and backward jumps during buffer drainage (e.g., preserving 990 ms). On resume, `_drain_start_clock_sec` is re-anchored based on `drained_so_far`, ensuring seamless continuation to natural completion or loop wrap.
  9. *Device-Governed Natural Completion and Loop Decisions:*
     When audio hardware/driver is active:
     $$\text{Complete} \iff \text{round}(t_{\text{audible}}, 6) \ge T_{\text{total}}$$
     Ensuring playback does not terminate prematurely at software clock time when the audio device is delayed by startup overhead or running at non-unity clock rates.
  10. *Half-Open Active Event Interval Semantics:*
     $$\text{Active}(E, t) \iff t_{\text{start}} \le t < t_{\text{end}}$$
     Strict boundary rule: at exact boundary $t = t_0$, an ending event transitions to inactive and an abutting beginning event transitions to active in the exact same tick.
  11. *Continuous Loop Remainder Preservation:*
      $$t_{\text{loop}} = t_{\text{raw}} \pmod{T_{\text{total}}}$$
      This is the coordinate rule for backends that report progress past the end (the simulator). The Windows MCI device stops itself at end of media, so no remainder exists there: the transport restarts from 0, and the restart is not acoustically seamless (measured upper bound 58–86 ms per cycle; architecture Section 7.8).
  12. *Polyphonic Sine Tone Synthesis & Dynamic Headroom Normalization:*
      $$f = 440.0 \times 2^{(p - 69) / 12}$$
      Linear 5 ms attack and decay envelopes applied at event boundaries to suppress high-frequency acoustic transients. Exact rational sample bounds:
      $$n_{\text{start}} = \text{round}(t_{\text{start, rational}} \times \text{sample\_rate}), \quad n_{\text{end}} = \text{round}(t_{\text{end, rational}} \times \text{sample\_rate})$$
      Floating-point polyphonic mixing normalized by:
      $$A_{\text{norm}} = \frac{0.95}{\max_i |x_i|}$$
      to ensure zero digital clipping in 16-bit signed PCM WAV output.
  13. *Cumulative Drift Elimination Benchmark:*
      $$\Delta t_{\text{drift}} < 10^{-10}\text{ ms} \quad (0.0000\text{ picoseconds})$$
      verified across 10,000 discrete micro-steps of size $0.1\text{ ms}$. *(Zero by construction: `TestClock` and the simulator share one clock. This checks arithmetic accumulation only.)*
  14. *Software Transport Dispatch Latency (simulated backend; thirteenth-revision figures):*
      Evaluated over 1,000 transport seek/active query iterations:
      - Mean Latency: $0.0119\text{ ms}$
      - 99th Percentile Latency: $0.0161\text{ ms}$
      - Peak Latency: $0.2085\text{ ms}$
      - Target (Software Dispatch Overhead $\le 20.0\text{ ms}$): **PASSED** with substantial margin.
      *(Note: Physical acoustic synchronization requires external acoustic measurement sensors; this benchmark strictly measures software dispatch, query, and event calculation overhead).*
- **Verification Commands Executed (consolidated correction, 2026-11-26, Windows NT 10.0.26300, project `.venv` Python 3.15.2):**
  - `python -m unittest discover tests -v`
  - `MUSIC_REAL_AUDIO_TESTS=1 python -m unittest tests.test_playback_windows_device -v` (real Windows MCI device, silent PCM WAV)
  - All 9 standalone verification scripts (`verify_proof.py`, `verify_progressive.py`, `verify_development.py`, `verify_midi_import.py`, `verify_group_units.py`, `verify_group_discovery.py`, `verify_row_merger.py`, `verify_audio_and_sheet_adapters.py`, `verify_playback_transport.py`)
  - Defect re-introduction check (`JOB_03_CONSOLIDATED_EVIDENCE/mutation_check.py`)
  - The preserved original diagnostics, against both the thirteenth revision and the new code, plus the adapted diagnostics (`JOB_03_CONSOLIDATED_EVIDENCE/run_original_diagnostics.py`, `adapted_diagnostics/`)
- **Exact Test Counts & Results (consolidated correction):**
  - Full suite (resubmission 2, final): **272 tests: 259 passed, 13 skipped, 0 failures, 0 errors, exit code 0** (49.2 s). Resubmission 1 was 260 / 250 / 10.
    - 206 pre-existing tests: 206 passed, 0 modified (127 published baseline + 15 experimental group discovery + 64 dedicated JOB-03).
    - 53 deterministic D1–D8 tests (`tests/test_playback_consolidated.py`; 44 + 9 completion-predicate tests with 672 subtests): 53 passed.
    - 13 opt-in real-device tests (`tests/test_playback_windows_device.py`): **skipped** in this run (opt-in), and reported separately below.
  - Dedicated playback tests: 64 existing + 53 new = **117 passed** in the full run; plus 13 real-device tests run separately.
  - Real-device integration (final): **13 / 13 passed, 0 skipped, exit code 0.** Ordinary playback advances beyond the first update interval without MCI 263 (26 updates in 400 ms; mean update interval 15.3 ms). Round-down fractional WAVs complete at their exact durations: 22,071 frames @ 44.1 kHz at 500.4761904761905 ms, 4,801 @ 48 kHz at 100.02083333333333 ms. Over 11 real-device suite runs this session, 10 passed and 1 failed (see Known Limitations).
  - Standalone scripts: **9 / 9 exit code 0.**
  - Benchmark: **8 / 8 scenarios, 44 / 44 assertions** (simulated timing; Scenario 7 mean 0.0063 ms, p99 0.0088 ms of software dispatch time on the simulator).
  - Defect re-introduction: **14 / 14 mutations detected** (including the restored thirteenth-revision predicate: 88 subcase failures); control run passes; production files hash-verified as restored.
  - `%TEMP%\music_play_*.wav` count unchanged by the full suite (489 → 489).
- **Consolidated Architectural Correction: Defects D1–D8 (2026-11-26):**
  The JOB-03 investigation found that with the real Windows audio device ordinary playback failed, even though all 206 tests passed. The eight-step correction approved by ChatGPT and authorized by the Author was implemented. For each defect, the negative baseline is the preserved original diagnostic re-run today against the thirteenth revision (`outputs/original_diagnostics_rerun.txt`).

  | Defect | Thirteenth revision (reproduced again today) | Corrected behaviour (evidence) |
  |---|---|---|
  | **D1** MCI thread ownership | ERROR about 15 ms after Play, MCI 263 from the `TransportTimer` thread; device still `playing`; Pause ignored | No playback thread. Tk-thread scheduler. Real device: PLAYING, 24 updates in 400 ms, no error (R1). Pause puts the device in `paused` (R4). Cross-thread commands are refused before reaching MCI, without changing status (R7, D1 tests). A query failure during playback now also stops the audio (D1 test). |
  | **D2** fractional-duration completion | 22,070-frame WAV: PLAYING forever at 500.000 ms, 0 end callbacks (`diag_mci_real2 (b)`) | The **same unmodified script** gives STOPPED at 500.454 ms with 1 end callback. Real device R2: completes at exactly 500.453515 ms; R3 control at 1000 ms; fractional looping R6. Early stop is distinguished from end of media (D2 tests). |
  | **D3** flags vs device | `is_playing` stayed true after end of media; pause/resume gave 302 | `observe()` reconciles flags with `status mode`; `pause` and `resume` check the mode first. No 302 under the driver model; `seek` while paused leaves the device stopped and resume uses `play from` (D3 tests, R5). |
  | **D4** duplicate timers | 2 live `TransportTimer` threads after rapid pause/play | No threads exist. At most one pending update across 200 rapid pause/play cycles (D4 test). Adapted diagnostic: thread count unchanged and update spacing about 16 ms. |
  | **D5** incoherent notifications | Last delivered (464.1 ms, {E0}) although E1 is active there; out of order | Immutable snapshot per commit. 0 snapshots disagree with their own position. Out-of-order arrival is rejected by `sequence` (D5 tests, adapted diagnostic (b)). |
  | **D6** replay loses its timer | PLAYING with no tick thread, never completes | Replay from inside the end notification owns one update and completes again (D6 tests, adapted diagnostic (c)). Obsolete callbacks are rejected by generation. |
  | **D7** GUI snapshot handling | Seek while stopped not shown; seek while paused ignored; completion left at 2985 ms with Sound A lit; queued tick survived Stop | Every snapshot is rendered under the documented cursor policy. All four original cases give AGREE in `diag_gui_adapted.py`. Stale, foreign-transport and stale-source snapshots are rejected (D7 tests). |
  | **D8** resource leakage | Temp WAV kept after stop; `destroy()` never unloaded; rev13 suite left 20 temp WAVs per run | `close()` and `destroy()` release the alias and this application's own temp WAV. Source replacement releases the previous one; a failed open cleans up; a failed close can be retried (D8 tests, R8, R9). The refactored suite leaves 0. |

  - **Existing tests:** none modified. The old `MockMciBackend` (which answers every `status` with a position) keeps working because unknown mode strings cause no reconciliation. Realism is added by the new `FakeWinmm` model instead.
  - **Benchmark script:** only the printed wording of Scenarios 6 and 7 changed, so that it no longer presents simulated figures as synchronization measurements. Assertions and counters are byte-identical.
  - **Public behaviour changed deliberately:**
    1. `position_ms` / `estimated_audible_position_ms` raise on a device read failure while PLAYING, instead of silently returning software time.
    2. Lifecycle calls from a non-owner thread raise `TransportThreadError`.
    3. A transport built without a scheduler does not advance by itself; a warning is logged when it plays on a real clock.
    4. `load_timeline` validates the new source before stopping the current one.
  - **Problems found during this work and resolved:**
    1. The first defect re-introduction run was invalid: it ran from `tests/`, so every "caught" was an import error. Fixed, and a control run was added.
    2. Two candidate mutations were equivalent, i.e. they produced no behavioural change. They were replaced.
    3. One genuine test gap (the backend-level D3 guard) was found and covered.
    4. A refused cross-thread call was marking the backend FAILED. Fixed: ownership is now checked before any status-changing handler.
    5. A units error in a real-device measurement (seconds printed as ms) was fixed.
    6. My own diagnostic and mutation runs leaked temp WAVs. Only files with exact before/after proof were removed; the rest are listed for the Author. Runs are now isolated to dedicated TEMP folders.
    7. An `sed` edit converted `main_window.py` to LF line endings; it was restored to the working tree's CRLF.
  - **Resubmission 2: completion predicate (ChatGPT independent audit, 2026-11-26).** The retained thirteenth-revision predicate `round(p, 6) >= T` rounded only one side, so durations with `round(T, 6) < T` (e.g. 22,071 frames at 44.1 kHz, 4,801 at 48 kHz) never completed or looped. This was reproduced under the MCI model, a capped simulator, and the real device with the resubmission-1 module. The fix is a single symmetric predicate `p >= T - 5e-7` ms and a loop-remainder rule for progress reached from below (architecture §7.9). Added: 9 deterministic tests (672 subtests: 200 playback scenarios and 472 predicate-equivalence checks) covering round-up, round-down and exact durations, a 151-frame sweep, sample rates 8–96 kHz, nonzero buffer latency, completion and looping, premature-completion guards, and equivalence with the old predicate where it was well-defined. Also 3 real-device tests (22,071 @ 44.1 kHz, 4,801 @ 48 kHz, 22,071 loop) and 2 mutations (old predicate: 88 subcase failures; old remainder: caught). In `tests/test_playback_consolidated.py` (a resubmission-1 file) the harness gained an optional `buffer_latency_ms` argument; no existing assertion changed.
  - **Open question for review (not changed):** MCI reports a position about 17–35 ms ahead immediately after `pause`, so the cursor steps forward by that amount (19–34 ms measured) at the first update after resume. See architecture Section 7.8, item 3, for the options. An acoustic check is needed before choosing one.
- **Audit Defect Resolutions (Twelfth Independent Audit):**
  - **DEFECT-09I (Windows Backend Does Not Resume After Successful Recovery):**
    - Root cause: In `PlaybackTransport.play()`, `getattr(self.audio_backend, "is_paused", True)` defaulted to `True` because `WindowsMciAudioBackend` did not expose a public `is_paused` attribute (it used `_is_paused`). Following stop-and-seek recovery from `ERROR`, the Windows MCI device was stopped and positioned at the target (`_is_paused == False`). When `transport.play()` was called, it invoked `self.audio_backend.resume()`. In `WindowsMciAudioBackend.resume()`, `if not self._is_paused: return` silently returned without issuing any MCI command, yet `PlaybackTransport` transitioned to `PLAYING`.
    - Correction:
      1. Established explicit backend contract: Added abstract properties `@property def is_playing(self) -> bool` and `@property def is_paused(self) -> bool` to `AudioBackend`, implemented across `WindowsMciAudioBackend`, `SimulatedAudioBackend`, and `NullAudioBackend`.
      2. Eliminated silent no-ops: In both `WindowsMciAudioBackend.resume()` and `SimulatedAudioBackend.resume()`, calling `resume()` when `not self.is_paused` explicitly raises `AudioBackendError`, preventing any silent return from falsely claiming playback.
      3. Explicit resumption check: In `PlaybackTransport.play()`, `can_resume = is_resuming and getattr(self.audio_backend, "is_paused", False)`. When recovering from `ERROR` or seeking while stopped, `is_paused` is `False`, ensuring that `self.audio_backend.play(start_ms=start_device, loop=self._loop)` is executed, sending `play <alias> from <target>` directly to the Windows MCI driver.
      4. Explicit non-playing condition check: In `PlaybackTransport.seek()`, when recovering from `ERROR`, `self.audio_backend.stop()` is called and `self.audio_backend.is_playing == False` is explicitly verified before calling `self.audio_backend.seek(clamped_target)`.
      5. Explicit verification distinctions: Accurately distinguish command acknowledgement (`backend.stop()` executing without exception), backend-maintained state verification (`backend.is_playing == False`), and physical acoustic observation (physical sound propagation requiring human/sensor verification).
      6. Command-level regression coverage: Added 10 new tests (1 defect regression test + 9 deterministic command-level control path tests in `TestWindowsMciCommandControlPath` verifying initial play, pause/resume, failed stop, recovery seek failure, recovery stop/seek order, recovery play, failed play coordinate preservation, visual callback consistency, and buffer latency source coordinate preservation). Dedicated test suite increased to 64 tests; full regression suite increased to 206 tests.
- **Audit Defect Resolutions (Eleventh Independent Audit):**
  - **DEFECT-09H (ERROR Recovery Reports PAUSED While Backend Continues Playing):**
    - Root cause: In `seek()`, when recovering from `TransportState.ERROR`, the transport was committing `TransportState.PAUSED` and position without establishing that the backend was actually in a non-playing condition. If a prior `stop()` or teardown failure left the backend actively playing (`backend.is_playing == True`), calling `seek(500)` reported `PAUSED` at 500 ms while the backend continued advancing audio output (e.g. to 550 ms).
    - Correction (Option B - Explicit Recovery Transaction): In `seek()`, when in `TransportState.ERROR`, the transport executes an explicit two-stage recovery transaction:
      1. Attempt `self.audio_backend.stop()` to establish and verify an acknowledged non-playing backend condition (`backend.is_playing == False`).
      2. If `stop()` fails (e.g. backend failure unresolved), the recovery transaction is immediately aborted: state remains `TransportState.ERROR`, coordinates remain preserved at `pre_seek_pos`, visual listeners receive `pre_seek_pos`, error callback is dispatched, and `AudioBackendError` is re-raised. The transport never falsely claims to be `PAUSED`.
      3. If `stop()` succeeds and `backend.seek(clamped_target)` succeeds: both required hardware operations succeeded; state transitions cleanly to `TransportState.PAUSED`, all coordinate latches (`_paused_device_pos_ms`, `_paused_audible_pos_ms`, `_software_pos_ms`, `_segment_start_ms`) synchronize to `clamped_target`, active events update, and visual listeners receive `clamped_target`. Subsequent clock advances verify device position remains stable at `clamped_target` without creeping or runaway playback.
- **Audit Defect Resolutions (Tenth Independent Audit):**
  - **DEFECT-09F (Successful Seek in ERROR State Produces Conflicting Coordinates):**
    - Root cause: In `seek()`, when backend seek succeeded while in `TransportState.ERROR`, `_software_pos_ms` was updated to the seek target (e.g. 500 ms) and visual listeners were notified of 500 ms, but `_paused_audible_pos_ms` remained latched at the old error coordinate (100 ms). Consequently, `position_ms` returned 100 ms while visual callbacks received 500 ms.
    - Correction: Defined an explicit supported recovery transition from `TransportState.ERROR` to `TransportState.PAUSED` upon successful seek. All coordinate latches (`_paused_device_pos_ms`, `_paused_audible_pos_ms`, `_software_pos_ms`, `_segment_start_ms`) are updated to the target coordinate, active events are recomputed at the target, and visual listeners are notified. If backend seek fails, the transport remains in `ERROR` with preserved coordinates.
  - **DEFECT-09G (Failed Pause at an Unprocessed Loop Boundary):**
    - Root cause: In `position_ms` and `pause()`, modulo remainder arithmetic (`raw_audible % total_duration_ms`) was computed independently of the actual loop restart transaction. When the device crossed track duration (e.g. 1005 ms) before `step_tick()` executed the loop restart transaction, `pause()` published an uncommitted 5 ms remainder.
    - Correction: Progress in the current cycle is strictly bounded by `_total_duration_ms` until `step_tick()` executes the backend restart transaction (`backend.play(start_ms=remainder_ms, loop=True)`). If `pause()` or query occurs after the device reaches the boundary, the completed cycle coordinate ($T_{\text{total}}$) is preserved, preventing premature publication of next-cycle coordinates.
- **Audit Defect Resolutions (Ninth Independent Audit):**
  - **DEFECT-09C (Failed Pause Leaves Stale Active Events):**
    - Root cause: In `pause()`, when backend pause failed (`AudioBackendError`), `_software_pos_ms` was set to the acquired audible position (e.g. 200 ms) but `_update_active_events(audible_pos)` was omitted, leaving stale active events from earlier ticks.
    - Correction: Recomputed active events at `audible_pos` and dispatched `_notify_tick(audible_pos)` upon pause failure, delivering a consistent visual snapshot and active-event state.
  - **DEFECT-09D (Failed Loop Restart Publishes Unachieved Destination):**
    - Root cause: In `step_tick()`, `_software_pos_ms` and `snapshot_pos` were assigned the proposed loop remainder (e.g. 5 ms) before calling `backend.play(loop=True)`. When the restart failed, the unachieved remainder was published as the achieved position.
    - Correction: Separated completion observation from proposed remainder. On backend restart failure, the completed cycle coordinate ($T_{\text{total}}$) is preserved, active events at $T_{\text{total}}$ are evaluated, and $T_{\text{total}}$ is delivered to visual listeners, strictly suppressing the rejected remainder.
  - **DEFECT-09E (Failed Replay Loses Completed Position):**
    - Root cause: In `play()`, when replaying from completed state ($t \ge T_{\text{total}}$), `_software_pos_ms` was set to 0.0 before `backend.play()` succeeded. When the backend failed, the completed coordinate was lost.
    - Correction: Separated target restart coordinate ($0.0$) from current position (`pre_play_pos`). If `backend.play()` fails, `_software_pos_ms`, `_paused_audible_pos_ms`, and active events retain `pre_play_pos` ($T_{\text{total}}$), delivering $T_{\text{total}}$ to visual listeners.
- **Audit Defect Resolutions (Eighth Independent Audit):**
  - **DEFECT-09B (Failed Stop and Reset Publish Incorrect Visual Coordinates):**
    - Root cause: In `stop()` and `reset()`, when backend shutdown failed (`AudioBackendError`), the transport transitioned to `TransportState.ERROR` and preserved the last coordinate internally, but unconditionally called `self._notify_tick(0.0)`.
    - Correction: Unified lifecycle invariant across `stop()` and `reset()`.
      - On backend shutdown failure: state transitions to `TransportState.ERROR`, last valid authoritative coordinate (`pre_stop_pos` / `pre_reset_pos`) is preserved in `_software_pos_ms` and `_paused_audible_pos_ms`, active events are maintained at the preserved coordinate, visual listeners are notified of the preserved coordinate (`self._notify_tick(pre_stop_pos)`), and backend error is dispatched. Unachieved zero-position destinations are never published upon failed shutdown.
      - On successful shutdown: state transitions to `TransportState.STOPPED`, position is set to 0.0, active events are updated to 0.0, and visual listeners are notified of 0.0.
    - Verified across failed `stop()` and `reset()` from `PLAYING` and `PAUSED` states, active-event agreement, error callback dispatch, and subsequent successful recovery.
- **Audit Defect Resolutions (Seventh Independent Audit):**
  - **DEFECT-10A (Loop Restart Skips Source Audio):**
    - `step_tick()` restarts the audio backend at `start_device = remainder_ms` without adding buffer latency.
    - Preserves all source audio at loop restarts (e.g. 0.0 ms visual transport $\to$ 0.0 ms backend source coordinate).
    - Applies the physical buffer-fill interval $[remainder\_ms, remainder\_ms + L]$ consistently across loop cycles.
    - Verified across zero and nonzero latency, exact loop boundaries, nonzero loop remainders, and repeated loop cycles.
  - **DEFECT-09A (Failed Seek Sends Incorrect Visual Position):**
    - Fixed unconditional `self._notify_tick(clamped_target)` execution during seek.
    - On seek failure, the authoritative pre-seek coordinate (`pre_seek_pos`) is preserved across stored transport position, ERROR state reporting, active-event membership, and visual playhead callbacks (`self._notify_tick(pre_seek_pos)`).
    - An unachieved seek target is never published as an achieved coordinate.
    - Verified for failed seeks during STOPPED, PLAYING, and PAUSED states, verifying active-event membership and visual callback agreement.
- **Author-Operated Manual Playback Verification Procedure & Attribution Status:**
  - *Attribution Note:* Physical acoustic sound reproduction through speakers requires direct human ear or microphone observation. While all underlying software timing, MCI command dispatch, waveform generation, and drift benchmarks have been verified programmatically on local Windows, direct manual confirmation by the Author remains pending.
  - The 10-step checklist in Section 5 of `docs/audio_playback_architecture.md` is provided for the Author to execute interactively via PowerShell `python main.py`. The automated evidence for each check is listed there, from simulated backends, the MCI model and the silent real device. It does not establish what is heard. All 10 checks are **Pending Author Verification**. *(Correction to the thirteenth-revision statement "Pre-verified simulator results are PASS across all 10 checks": with the real device, checks 2–6 and 10 could not have passed in that revision; see D1.)*
- **Known Limitations & Scope Boundaries:**
  - No acoustic measurement exists. Audio/visual synchronization and the ≤ 20 ms engineering target remain unverified physically (architecture Section 7.8).
  - Device startup latency is about 30 ms. Completion was observed 43–92 ms after play-time plus the exact duration (8 of 9 runs; 242–368 ms in the degraded run). MCI positions are integer ms; command rounding is ≤ 0.5 ms, clamped to the floored media length.
  - Loop restart on MCI is from 0 with a gap; per-cycle overrun measured at 58–86 ms (an upper bound on the gap). It is not seamless.
  - Pause discontinuity of about 18–35 ms in MCI's reported position (open question above).
  - Production buffer latency is 0; the drainage model is exercised by tests only.
  - **Real-device suite: 1 of 11 runs failed** two update-count thresholds during a system-wide timing degradation. Correctness assertions held, and 5 immediate repetitions and the final run passed. The failed log is preserved. See architecture Section 7.8, item 7.
  - User commands block the GUI thread for 6–75 ms (stop and seek while playing are the costliest); periodic updates take ≤ 1.3 ms (architecture Section 7.8, item 8).
  - Audio playback uses pure standard-library capabilities (`ctypes` winmm MCI, `wave`, and sine synthesis). Advanced multi-timbral physical modeling synthesis remains in downstream jobs.
  - Protected calculator repository (`17be078d`) remains untouched and 100% read-only.
  - Downstream jobs (JOB-04 onwards), Statement 31 (future literature/AI repository), and Statement 32 (future mathematical research) remain strictly out of scope.
- **Google Antigravity Review:**
  *JOB-03 audit corrections for the twelfth audit are complete. All 64 dedicated audio playback tests pass, all 206 automated test suite tests pass, all 9 standalone verification scripts exit with code 0, and the review archive `JOB_03_INDEPENDENT_REVIEW.zip` has been verified for zip integrity. Zero unauthorized git operations were performed. Submitted for final approval by ChatGPT and the Author.*  
  — Google Antigravity, 2026-11-25.
- **Claude Opus 5.5 Implementation Statement (2026-11-26):**
  *The consolidated D1–D8 correction is implemented and engineering-verified as recorded above and in `JOB_03_VERIFICATION_LOG.txt`, including the real Windows MCI device with silent audio. This is not a claim that JOB-03 is finished: physical synchronization, loop and pause behaviour as heard, and the Author's ten checks remain open. No files were staged, committed or pushed; README.md, music.txt, the calculator repository, group discovery and the row merger were not modified; JOB-04 was not started.*
- **Author Manual Verification: WAV Import Crash (resubmission 3, 2026-11-26):**
  - *Root-cause evidence:* see `docs/audio_playback_architecture.md` §7.10 and `review/wav_crash_evidence/WAV_CRASH_INVESTIGATION.md` in `JOB_03_WAV_CRASH_REVIEW.zip`.
  - *Deterministic defect (fixed):* `_on_open_wav_file` added importer events labelled `row_audio` to the row `Row 2`. `TemporaryRow.add_event` rejected them, so WAV import never succeeded for any file.
  - *Hang (fixed):* the roughly 26 s JOB-02 analysis ran on the Tk thread, so Windows declared the window hung. Both fatal access violations observed happened in that state. The analysis now runs on a worker thread, and the result is applied on the Tk thread.
  - *Access violation (cause not established):* it is native memory corruption, not a defect in the line-438 generator expression. Two candidates remain: a CPython 3.15.2 defect, or system instability. The machine recorded kernel bugchecks 0x0A, 0xD1 and 0xF5 between 11-21 and 11-26.
  - *Files changed:* only `music_gui/main_window.py` (JOB-03), plus tests. `music_model/audio_importer.py` (JOB-02) was **not changed**: no defect was found in it.
  - *Limitation (unchanged JOB-02 behaviour):* the Author's legato file yields **one** event (E4), not four notes. The four-pitch requirement is verified with a gapped fixture of the same notes.
  - *Verification (2026-11-26 19:09–19:13):*
    - Focused tests: 5/5.
    - Full suite: 278 tests OK, 14 skipped (the 272 prior tests plus 6 new).
    - Real-device suite: 14/14.
    - Standalone scripts: 9/9 exit 0.
    - The Author's own interactive re-check is **pending**.
  - *Test accounting correction:* the run above reported "278 tests OK (skipped=14)". That means **264 passed and 14 skipped**; the 14 skipped tests are the gated real-device tests, which passed separately (14/14).
- **Stale Asynchronous WAV Import Correction (resubmission 4, 2026-11-26):**
  - *Defect (ChatGPT audit, reproduced here before the fix):* a WAV analysis started before another source or mode was selected still published when it finished. Example: Progressive Refitting stays selected, but its dataset is replaced by `Imported WAV: delayed.wav`.
  - *Correction:* in `music_gui/main_window.py` only; the full policy is in `docs/audio_playback_architecture.md` §7.10 item 3.
    - Source-selection generation, with publishing authority kept separate from worker lifetime.
    - Obsolete success and failure are both discarded silently; the badge is refreshed truthfully.
    - At most one analysis worker at a time; no thread termination.
    - `destroy()` supersedes any pending import.
  - Files left unchanged: `audio_importer.py`, `audio_playback.py`, README.md and music.txt.
  - *Tests:* 9 deterministic, gate-controlled lifecycle tests in `tests/test_wav_import_regression.py` (`TestStaleWavImportLifecycle`).
    - Against the pre-fix code, 7 of the 9 fail or error.
    - The 2 that pass on both are guards against over-invalidation (cancelled dialog; current failure still reported).
    - All 278 previous test IDs are preserved.
  - *Verification (2026-11-26 19:25–19:30):*
    - Focused: 14/14.
    - Full suite: 287 run, **273 passed, 14 skipped**, 0 failures or errors.
    - Real-device suite: 14/14.
    - Standalone scripts: 9/9 exit 0.
  - *Observed, pre-existing, not changed (outside this correction's scope):* after a WAV import, the Row 1 toggle calls `show_midi_mode(self.current_song)`.
    - The view re-renders as `Imported: <file>`, and the transport reloads **synthesized** audio in place of the original PCM (`probe_row1_toggle_after_wav_output.txt`).
    - The same code path exists in R2.
  - *Native memory corruption:* still **unresolved**. The worker thread gives responsiveness, not process isolation.
  - *ChatGPT audit:* stale-import correction **accepted** (independent run: 287 run, 272 passed, 15 skipped on Linux; 273 passed, 14 skipped on Windows).
- **Row 1 Source Preservation Correction (resubmission 5, 2026-11-26):**
  - *Defect (negative baseline `probe_row1_source_matrix_BEFORE.txt`):* every Row 1 toggle reloaded the transport.
    - The WAV's original PCM became synthesized audio.
    - Playback stopped and returned to 0 ms.
    - The dataset was renamed `Imported: <file>` for WAV and MusicXML.
    - WAV and MusicXML imports each loaded the transport twice.
  - *Correction:* in `music_gui/main_window.py` only; details in `docs/audio_playback_architecture.md` §7.10 item 4.
    - The display refresh (`_refresh_summary_display`) is separated from source installation (`_update_summary`).
    - The Row 1 toggle is display-only.
    - Each import does a single transport load.
    - Row 1 algorithms, `audio_importer.py`, `audio_playback.py`, README.md and music.txt are unchanged.
  - *Policy change:* the Row 1 toggle no longer supersedes a pending WAV import (item 3 revised).
  - *Tests:* 4 new deterministic tests (`TestRow1SourcePreservation` ×3; `TestStaleWavImportLifecycle.test_row1_toggle_is_not_a_source_selection`).
    - Against the pre-correction code, all 4 fail.
    - With the import-count assertions relaxed, the two toggle tests still fail. The genuine-replacement guard passes on both versions, as intended.
    - All 287 previous test IDs are preserved.
  - *After the correction (`probe_row1_source_matrix_AFTER.txt`):* 0 transport loads per toggle, for WAV, MusicXML and MIDI, while stopped, playing and paused. PCM, state, position, dataset and badge are preserved, and the Row 1 display changes as expected.
  - *Verification (2026-11-26 19:41–19:46; actual Python exit codes, all 0):*
    - Focused: 18/18.
    - Full suite: 291 run, **277 passed, 14 skipped**.
    - Real-device suite: 14/14.
    - Standalone scripts: 9/9.
  - *Still pending:* the Author's manual WAV re-test and interactive playback checks. The native access violation remains **unresolved**.
- **Author Verification and Automated Acceptance Package (2026-11-26):**
  - *Author re-test:* 10 PASS, 2 UNSURE (sound-event count; stale import), 0 failures. The Author heard four different beeps, the expected original audio. Both UNSURE items are now covered automatically (matrix A02, A08–A10).
  - *New automated coverage (tests only, no production change):* the Author's **actual** `JOB03_test.wav` is now a fixture, `tests/fixtures/JOB03_test.wav`, with its SHA-256 pinned. Two new tests in `TestAuthorControlledWavFixture`:
    - the fixture's identity and header, and that it matches the generated equivalent to within 1 LSB;
    - the GUI import, which yields exactly one event (0–4000 ms, samples 0–176,400, E4).
  - The second test also confirms:
    - the dataset name and badge;
    - the original PCM bytes, as the playback source and on the device's temp file;
    - the playhead and highlighted event during playback;
    - natural completion at exactly 4000.0 ms, with no highlight at the end.
  - *Acceptance package:* `acceptance/run_acceptance.py`, `acceptance/unittest_json.py`, `acceptance/acceptance_matrix.json` (requirements A01–A22, optional physical observations P1–P4), `acceptance/README.md` and `acceptance/ACCEPTANCE_COVERAGE_MATRIX.md` (Windows run snapshot); limitations in `JOB_03_REMAINING_LIMITATIONS.md`. The runner:
    - uses the standard library only and has no absolute paths;
    - runs each step in a child process and records that process's own exit code;
    - keeps the opt-in device tests in a separate step;
    - fails on unknown matrix ids or unexpected skips. A negative check (`acceptance_runner_negative_check.txt`) confirmed a failing test and a typo'd id produce FAIL and exit code 1.
  - *Windows acceptance run (2026-11-27 04:19 UTC, `--windows-device`):*
    - Suite: 293 run, **279 passed, 14 skipped**, 0 failures or errors (exit 0).
    - Device tests: 14/14 (exit 0).
    - Scripts: 9/9 exit 0.
    - Requirements: A01–A19 and A22 PASS; A20 (acoustic synchronization) NO-AUTOMATED-COVERAGE; A21 (native access violation) regression only, **unresolved**.
    - Runner exit code 0.
  - Section 5 of the architecture documentation now records the Author's results.
  - Production code, mathematical algorithms, `audio_importer.py`, README.md and music.txt are unchanged.
- **Publication Preparation (Author authorization of 2026-11-26, ChatGPT recommendation):**
  - *Acceptance runner scope correction* (acceptance package only; no production code):
    - The seven required scripts always run, and a missing or failing one fails acceptance.
    - `verify_group_discovery.py` (JOB-04) and `verify_row_merger.py` run only when present, and a present failure still fails. When absent, they are reported as `OUTSIDE PUBLICATION SCOPE (absent)`.
    - Requirement A22 lists the seven required scripts plus the two as `optional_scripts`.
    - The four cases of the rule were checked in a scratch project (`scope_fix_negative_checks.txt`): missing required → FAIL / exit 1; present optional failing → FAIL / exit 1; otherwise PASS / exit 0.
  - *Verified against both trees* (Windows, `--windows-device`, actual Python exit codes, `scope_fix_verification_output.txt`):
    - **Complete local project:** suite 293 run, 279 passed, 14 skipped, 0 failures; device 14/14; 7/7 required and 2/2 optional (present) scripts exit 0; runner exit 0.
    - **Exact proposed publication tree** (61 files, no JOB-04 or row-merger files): suite 278 run, **264 passed, 14 skipped**, 0 failures; device 14/14; 7/7 required scripts exit 0; both optional reported `OUTSIDE PUBLICATION SCOPE (absent)`; A01–A19 and A22 PASS, A20 NO-AUTOMATED-COVERAGE, A21 regression only; runner exit 0.
  - *README.md* (authorized; 4 lines changed, all other content and every Author statement preserved):
    - JOB-02 → `[COMPLETED]`.
    - JOB-03 → `[COMPLETED WITH DOCUMENTED LIMITATIONS]`, referencing `JOB_03_REMAINING_LIMITATIONS.md`, and disclosing both the unmeasured acoustic synchronization and the unresolved native access violation. This is applied in the job list (lines 690, 700) and the milestone tree (lines 1016–1017).
    - All other job statuses are unchanged.
  - *Other files:* `.gitignore` gains `acceptance_results/`, with all existing rules preserved. `music.txt` is unchanged.
  - *Manifest and archive:* `JOB_03_PUBLICATION_MANIFEST.md` (revised; now part of the publication tree) and `JOB_03_PUBLICATION_REVIEW.zip`, which contains exactly the proposed publication tree.
  - *Publication status:* **not** staged, committed or pushed, pending ChatGPT's review of the publication package and the Author's final authorization.
- **ChatGPT Independent Review:**
  *Resubmission 1 (`JOB_03_CONSOLIDATED_REFACTOR_REVIEW.zip`): architectural direction accepted; localized completion-predicate correction required. Resubmission 2 (`JOB_03_CONSOLIDATED_REFACTOR_REVIEW_R2.zip`): followed by Author manual verification, which found the WAV import failure and crash. WAV crash review (`JOB_03_WAV_CRASH_REVIEW.zip`): row-id and responsiveness corrections accepted; stale-import correction required. `JOB_03_WAV_CRASH_REVIEW_R2.zip`: stale-import correction accepted; Row 1 source-preservation correction required. `JOB_03_WAV_CRASH_REVIEW_R3.zip` (SHA-256 1ef7ab9b…40f64eb), 2026-11-26: **APPROVED FOR AUTHOR-OPERATED MANUAL PLAYBACK VERIFICATION**; no further production correction requested. Final JOB-03 acceptance and publication remain pending. The native access violation remains unresolved (root cause neither identified nor eliminated).*
  *`JOB_03_ACCEPTANCE_REVIEW.zip` (749,550 bytes, 94 entries, SHA-256 86dacc8970c9022cbca67f5af4fe55a59f891485c8b199b800856be0384f423c), 2026-11-26: **JOB-03 ACCEPTED WITH DOCUMENTED LIMITATIONS — AWAITING AUTHOR PUBLICATION AUTHORIZATION.**
  - ChatGPT ran it from a freshly extracted archive with `xvfb-run -a python acceptance/run_acceptance.py` (Linux, CPython 3.13.5).
    - Results: 293 run, 278 passed, 15 skipped (the 14 opt-in device tests and the device-dependent GUI cleanup test), 0 failures or errors.
    - All nine scripts exited 0, and the runner exited 0.
    - Requirements: A01–A19 and A22 PASS; A20 NO-AUTOMATED-COVERAGE; A21 regression detection only.
  - All 64 manifest hashes match, and production sources are unchanged relative to R3.
  - The Windows evidence (279 passed, 14 skipped; device 14/14) was inspected. The auditor did not run the physical Windows audio device tests.
  - No further production changes and no further extensive manual verification were requested.
  - The following must stay distinct, and none may be overstated:
    - automated software verification;
    - recorded Windows device verification;
    - the Author's listening observations;
    - unmeasured physical acoustic synchronization: the ≤ 20 ms target is **not** claimed;
    - unresolved native memory corruption: elimination is **not** claimed.*
- **Author Approval:**
  *ChatGPT engineering acceptance granted (2026-11-26). Explicit Author authorization to publish (stage, commit, push) and to update README.md is **pending**. The proposed publication manifest is in `JOB_03_PUBLICATION_MANIFEST.md`. README.md, .gitignore and acceptance-runner changes authorized and applied (publication preparation, 2026-11-26); final authorization to stage, commit and push is **pending** ChatGPT's review of `JOB_03_PUBLICATION_REVIEW.zip`.*
- **Final Validated Checkpoint:** `Uncommitted` (Awaiting Author Authorization)
- **Next Authorized Job:** `Undecided` (Awaiting completion of review boundary)
