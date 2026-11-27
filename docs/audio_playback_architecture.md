# JOB-03 — Real-Time Audio Playback and Synchronized Visual Transport Architecture

**Repository:** `music`  
**Starting Implementation Baseline:** `9965050b50ceb41d5c04384a488a8f1debb9a643`  
**Current Documentation Checkpoint:** `f7042f91068c154ab9f9ec703dac8e6dd84b32d2`  
**Previous Documentation Checkpoint:** `66dfc53`  
**Job Identifier:** `JOB-03`  
**Module:** `music_gui.audio_playback`  
**Implementation status:** thirteenth revision plus the consolidated architectural correction for defects D1–D8 (Section 7). Uncommitted; under independent review. The Author's interactive checks (Section 5) are pending.

> [!IMPORTANT]
> Section 7 supersedes every statement in Sections 1–6 about a background timer thread, thread joins, or thread-safe cross-thread dispatch. There is no playback thread. Where Sections 2.7–2.12 write `_notify_tick(x)`, read "publish one immutable `TransportSnapshot` at coordinate x" (Section 7.2); the coordinate rules themselves are unchanged.

---

## 1. Overview and Engineering Objectives

JOB-03 establishes the foundational audio playback and visual transport engine for the Visual Music Machine. In previous milestones (JOB-01, JOB-02), the application established the variable-width master column timeline model, the musical development carrier (Row 1), and bounded import adapters for MIDI, MusicXML, and PCM WAV audio.

JOB-03 introduces:
1. **Multi-Tier Timing Hierarchy & Authoritative Transport Position:**
   - `software_transport_position_ms`: Monotonically advancing software clock time.
   - `device_position_ms`: Hardware/driver device position queried directly from Windows winmm MCI.
   - `estimated_audible_position_ms`: Authoritative audible position accounting for hardware buffer latency:
     $$t_{\text{audible}} = \max(S, t_{\text{device}} - \text{buffer\_latency\_ms})$$
   Visual transport and playhead track the authoritative audible position, eliminating drift.
2. **Buffer Latency Completion & Drainage Continuity:**
   Distinguishes device processing completion ($t_{\text{device}} \ge T_{\text{total}}$), estimated audible completion ($t_{\text{audible}} \ge T_{\text{total}}$), and physical acoustic completion. When the device reaches the end of the waveform, the transport smoothly drains the remaining hardware buffer without artificial terminal cursor jumps. Continuous loop boundaries preserve remainders ($t_{\text{loop}} = t_{\text{raw}} \pmod{T_{\text{total}}}$).
3. **Explicit Coherent Failure State Machine (`TransportState.ERROR`):**
   Distinguishes confirmed playback from uncertain device states. All transport operations (`play`, `pause`, `stop`, `seek`, `step_tick`) fail safe into `TransportState.ERROR`, preserve the last valid playback position, cancel the single scheduled update, attempt controlled audio shutdown where audio may still be playing, and publish one immutable snapshot plus the error notification on the owning thread (Section 7.3).
4. **Unified Timing and Error-Handling Acquisition (`_query_device_and_audible_progress`):**
   A single, consistent internal mechanism eliminates fragmented timing logic across properties, tick loops, and pause/resume transitions. It acquires raw device coordinates, validates finite/non-negative numbers, handles intentional headless fallback, applies buffer latency subtraction, and governs wall-clock buffer drainage.
5. **Natural Completion & Pause Integrity:**
   - When pausing during capped buffer drainage, the exact elapsed drainage progress is captured without backward jumps. On resume, the drain clock is re-anchored seamlessly.
   - Rejects non-finite coordinates (`NaN`, `inf`, `-inf`), negative positions, unexpected `None`, or query exceptions into `TransportState.ERROR` without silent software clock fallbacks.
   - Eliminates `UnboundLocalError` on combined query and backend pause failure.
6. **Single Authoritative Update Snapshot (DEFECT-09 Resolution):**
   `step_tick()` acquires exactly one authoritative position snapshot per transport update. That atomic coordinate is used consistently across end-of-piece / loop decisions, stored transport state (`_software_pos_ms`), half-open active-event membership (`_update_active_events`), visual playhead callback dispatch (`_notify_tick`), and the tick return value. No redundant backend sampling occurs within a single update.
7. **Deterministic Seek & Resume Semantics with Buffer Latency (DEFECT-10 Resolution):**
   Explicitly defines coordinate mappings across `STOPPED`, `PLAYING`, and `PAUSED` states. Distinguishes requested timeline coordinate ($T$), backend source coordinate ($T$), and estimated audible coordinate. Models the physical buffer-fill interval $[S, S + L]$ where the DAC output is held at the segment start coordinate $S$ while hardware FIFO buffers fill, advancing smoothly at $\text{dev\_pos} - L$ once filled. Source audio is never skipped to force visual alignment, eliminating backward jumps on seek and resume.
8. **Loop Restart Source Audio Preservation (DEFECT-10A Resolution):**
   Loop restarts restart the backend at the intended source coordinate ($S = \text{remainder\_ms}$) without skipping buffer latency. Both visual transport and backend device coordinate restart at the exact remainder coordinate (e.g. 0.0 ms $\to$ 0.0 ms), preserving all source audio and modeling the initial buffer-fill interval consistently across loop cycles.
9. **Seek Failure Coordinate & Callback Integrity (DEFECT-09A Resolution):**
   When a seek operation fails, the transport preserves the last valid playback position across the internal state, ERROR state reporting, active-event membership, and visual playhead callbacks (`_notify_tick(pre_seek_pos)`). Unachieved seek targets are never published to listeners.
10. **Failed Stop and Reset Coordinate & Callback Integrity (DEFECT-09B Resolution):**
    When backend `stop()` fails during a `stop()` or `reset()` operation, the transport transitions to `TransportState.ERROR`, preserves the last valid playback coordinate across internal state and active-event membership, and notifies visual listeners of the preserved coordinate (`self._notify_tick(pre_stop_pos)`). Unachieved zero-position destinations are never published to listeners upon shutdown failure.
11. **Systematic Lifecycle Transaction Integrity (DEFECT-09C, DEFECT-09D, DEFECT-09E Resolutions):**
    A strict internal transaction discipline is enforced across all transport operations (`play`, `pause`, `resume`, `seek`, `stop`, `reset`, natural completion, loop restart):
    - Proposed destinations (e.g. replay restart at 0.0 ms, loop remainder at $t_{\text{remainder}}$) are never committed to transport state before backend hardware confirmation.
    - On backend failure during `pause()`, the acquired authoritative coordinate is preserved, active events are recomputed at that coordinate, and visual listeners receive a consistent snapshot (`(t_{\text{pos}}, \text{active_events})`) (DEFECT-09C).
    - On backend failure during loop restart, the completed cycle coordinate ($T_{\text{total}}$) is preserved, active events at $T_{\text{total}}$ are computed, and the unachieved next-cycle remainder is suppressed (DEFECT-09D).
    - On backend failure during replay from completion, the completed coordinate ($T_{\text{total}}$) is preserved rather than prematurely resetting to 0.0 ms (DEFECT-09E).
12. **Explicit Recovery Transitions from ERROR State (DEFECT-09F Resolution):**
    When the transport is in `TransportState.ERROR`, calling `seek(target)` executes an explicit supported recovery transition: attempting backend seek, updating all coordinate latches (`_paused_device_pos_ms`, `_paused_audible_pos_ms`, `_software_pos_ms`, `_segment_start_ms`), transitioning to `TransportState.PAUSED`, updating active events, and notifying visual listeners of the achieved target. Subsequent `play()` resumes cleanly.
13. **Loop Remainder Commitment Separation (DEFECT-09G Resolution):**
    Estimated audible position in the current playback cycle is bounded by track duration ($T_{\text{total}}$). Modulo remainder arithmetic is never committed or published until `step_tick()` executes the backend restart transaction (`backend.play(start_ms=remainder_ms, loop=True)`). If `pause()`, `stop()`, or query occurs after the device reaches the boundary but before restart, the completed cycle coordinate ($T_{\text{total}}$) is preserved, preventing premature publication of uncommitted next-cycle coordinates.
14. **Verified Non-Playing Backend Condition on ERROR Recovery (DEFECT-09H Resolution):**
    In `seek(target)` when recovering from `TransportState.ERROR`, an explicit recovery transaction is executed: attempting `backend.stop()` to establish and verify an acknowledged non-playing backend condition. If `backend.stop()` fails (e.g. backend failure unresolved), recovery is immediately aborted: state remains `TransportState.ERROR`, coordinates remain preserved at `pre_seek_pos`, visual listeners receive `pre_seek_pos`, error callback is dispatched, and `AudioBackendError` is re-raised. The transport never falsely claims to be `PAUSED`. If both `stop()` and `backend.seek(clamped_target)` succeed, state recovers to `TransportState.PAUSED`, all coordinate latches synchronize to `clamped_target`, active events update, and visual listeners receive `clamped_target`. Subsequent clock advances verify device position remains stable at `clamped_target` without creeping or runaway playback.
15. **Explicit Backend Control-Path & Resumption Contract (DEFECT-09I Resolution):**
    Establishes an explicit backend contract across `AudioBackend`, `WindowsMciAudioBackend`, `SimulatedAudioBackend`, and `NullAudioBackend` that distinguishes:
    - An existing paused device playback session that can be resumed (`is_paused == True`).
    - A stopped device positioned at a requested source coordinate (`is_paused == False, is_playing == False`).
    - An active playback session (`is_playing == True`).
    - An unavailable or failed backend (`is_available == False` or `AudioBackendStatus.FAILED`).
    - An intentional headless or simulated playback mode (`NullAudioBackend` or `SimulatedAudioBackend`).
    When resuming playback in `PlaybackTransport.play()`, `can_resume = is_resuming and getattr(self.audio_backend, "is_paused", False)`. If the backend is not in an active paused session (e.g. following stop-and-seek recovery or paused seek), `self.audio_backend.play(start_ms=start_device, loop=self._loop)` is executed, issuing `play <alias> from <target>` to Windows MCI rather than silently returning without playing. Furthermore, `resume()` explicitly raises `AudioBackendError` if invoked when not in a paused state, preventing any silent no-op from falsely advancing transport state to `PLAYING`.
16. **Dual Audio Playback Modes:**
    - *Authentic PCM WAV Mode:* Directly streams recorded waveforms (e.g. from imported WAV files) without degradation or unnecessary re-synthesis, deriving authentic duration from frame count and rate (`(nframes * 1000.0) / framerate`) to preserve trailing silence.
    - *Polyphonic Symbolic Synthesis Mode:* An in-memory standard-library synthesizer generating band-limited sine waveforms with 5 ms attack/decay envelopes and anti-clipping normalization from authoritative exact rational timing (`get_authoritative_exact_timing()`) using direct rational sample quantization.
17. **Decoupled Deterministic Testing:** An injectable `Clock` (`RealClock`, `TestClock`), `Scheduler` (`TkScheduler`, `ManualScheduler`) and `AudioBackend` (`WindowsMciAudioBackend`, `SimulatedAudioBackend`, `NullAudioBackend`) hierarchy permitting headless, deterministic unit testing with zero `time.sleep()` delays, simulated startup delays, buffer offsets, and clock deviation. `WindowsMciAudioBackend` also accepts an injected `winmm` object, so the production backend can be tested against a behavioural model of the MCI driver (Section 7.7).
18. **Interactive GUI Transport & File Import Workflows:** A responsive control toolbar hosting Play, Pause, Stop, Seek Slider, Elapsed/Total Time display, Loop toggle, and Audio Mode badge, coupled with animated playhead cursor line/marker, real-time active sound bar border highlighting on `TimelineCanvas`, and File menu import workflows for WAV and MusicXML with automatic unloading of previous audio.

---

## 2. Mathematical Timing & Drift Architecture

### 2.1 Multi-Tier Timing & Single Authoritative Monotonic Coordinate

In computer music and multimedia systems, dual clocks (e.g. relying on separate audio sample counting and GUI frame timer loops) inevitably diverge due to hardware clock drift, buffer quantization, and thread scheduling jitter.

JOB-03 establishes a single authoritative time coordinate linked to audio device progress:
$$t = t_0 + (T_{\text{clock}} - T_{\text{start}}) \times 1000$$
where:
- $t$ is the current authoritative playback position in milliseconds.
- $t_0$ is the transport timestamp at which playback or resume began.
- $T_{\text{clock}}$ is the instantaneous high-resolution timestamp (via `time.perf_counter()` in production or `TestClock.now_seconds()` in tests).
- $T_{\text{start}}$ is the reference clock timestamp captured at the moment playback was initiated.

The multi-tier timing interface exposes:
1. `software_transport_position_ms`: Monotonically advancing software transport position.
2. `device_position_ms`: Hardware device position queried via `mciSendStringW(status <alias> position)`.
3. `estimated_audible_position_ms`: Authoritative audible position accounting for buffer latency.

> [!NOTE]
> Physical acoustic synchronization requires external acoustic sensors and physical audio measurement apparatus; this architecture treats 20 ms as an experimental target for software transport dispatch, active query, and seek execution overhead.

### 2.2 Buffer Latency at Completion & Drainage Continuity

In real audio hardware, three distinct completion milestones exist:
1. **Device Processing Completion:** The audio feeder finishes submitting samples up to song duration $T_{\text{total}}$ to the driver buffer ($t_{\text{device}} \ge T_{\text{total}}$).
2. **Estimated Audible Completion:** The audio samples drain from the driver/hardware FIFO buffer into the digital-to-analog converter over `buffer_latency_ms` ($t_{\text{audible}} \ge T_{\text{total}}$).
3. **Physical Acoustic Completion:** Physical sound waves propagate from the speaker transducers into the room.

When `buffer_latency_ms > 0`:
- When device position reaches $T_{\text{total}}$ (e.g. 1000 ms with 20 ms buffer latency), audible position is at $1000 - 20 = 980\text{ ms}$.
- Playback does NOT abruptly terminate with a 21 ms cursor jump. Instead, the transport continues in `PLAYING` state while the buffer drains smoothly:
  - At $t_{\text{device}} = 1000\text{ ms}$, visible position is $980\text{ ms}$.
  - Over the next $20\text{ ms}$, visible position advances smoothly ($981, 982, \dots, 999, 1000\text{ ms}$) via wall-clock elapsed drain time:
    $$t_{\text{audible}} = \max\left(t_{\text{device}} - \text{buffer\_latency\_ms}, (T_{\text{total}} - \text{buffer\_latency\_ms}) + \text{drain\_elapsed}\right)$$
  - When $t_{\text{audible}} = 1000\text{ ms}$, estimated audible completion occurs, and transport transitions to `STOPPED` (or wraps loop).
- At loop boundaries with buffer latency, the transport restarts the backend feeder at $t_{\text{remainder}}$ without skipping audio.

### 2.3 Frozen Pause Snapshot & Authoritative Pause/Resume State

When playback is paused, the transport queries the authoritative device position and buffer latency, freezing them into `_paused_device_pos_ms` and `_paused_audible_pos_ms`:
$$t_{\text{frozen\_device}} = t_{\text{device}}, \quad t_{\text{frozen\_audible}} = t_{\text{audible}}$$

This guarantees:
- **No Backward Jumps during Buffer Drainage:** Captures the full drained audible position (e.g. freezing at 990 ms rather than jumping backward to 980 ms).
- **No Software Clock Jumps:** Position does not snap forward to unrendered software clock time.
- **Exact Active Event Recalculation:** Active sound events during pause are evaluated against $t_{\text{frozen\_audible}}$.
- **Drain Clock Re-Anchoring on Resume:** When resuming during buffer drainage, `_drain_start_clock_sec` is re-anchored based on `drained_so_far`, ensuring seamless continuation to natural completion or loop wrap.

### 2.4 Half-Open Active Event Interval

For any sound event $E$ spanning interval $[t_{\text{start}}, t_{\text{end}})$:
$$\text{Active}(E, t) \iff t_{\text{start}} \le t < t_{\text{end}}$$

At boundary $t = t_0$:
- Any ending sound event with $t_{\text{end}} = t_0$ becomes inactive.
- Any beginning sound event with $t_{\text{start}} = t_0$ becomes active.
- Overlapping events across distinct rows remain simultaneously active (polyphony).

### 2.5 Continuous Loop Remainder Preservation

When looping is enabled and transport advances past song duration $T_{\text{total}}$:
$$t_{\text{remainder}} = t_{\text{raw}} \pmod{T_{\text{total}}}$$
The transport continues playback from $t_{\text{remainder}}$. This is the coordinate rule; it is not a claim of acoustically seamless looping. On the Windows MCI device the media stops itself at its end, so no remainder is observable and the restart is from $0$ with a measured gap (Section 7.8, item 4).

### 2.6 Cumulative Drift Elimination Benchmark

In continuous verification (`verify_playback_transport.py` Scenario 6), the transport was stepped across 10,000 discrete intervals of $0.1\text{ ms}$ (total $1,000.0\text{ ms}$). The measured discrepancy between the authoritative transport position and theoretical time was:
$$\Delta t_{\text{drift}} < 10^{-10}\text{ ms} \quad (0.0000\text{ picoseconds})$$
Interpretation: `TestClock` and `SimulatedAudioBackend` derive position from the same clock, so zero drift holds by construction. The benchmark verifies that the arithmetic does not accumulate error; it is not a measurement of device or acoustic drift (Section 7.8).

### 2.7 Atomic Transport Update Snapshot (DEFECT-09 Resolution)

When audio hardware positions advance rapidly or when testing with advancing query-counting backends, sampling the device multiple times within a single tick update introduces state tearing. In `PlaybackTransport.step_tick()`:
- Exactly one query is dispatched to `_query_device_and_audible_progress(record_drain_latch=True)`.
- The resulting authoritative progress coordinate $t_{\text{snapshot}}$ is captured as the single source of truth for the entire update.
- $t_{\text{snapshot}}$ governs:
  1. End-of-piece and continuous loop boundary detection.
  2. Stored transport position `_software_pos_ms = t_{\text{snapshot}}`.
  3. Active event interval membership `_update_active_events(t_{\text{snapshot}})`.
  4. Visual playhead callback delivery `_notify_tick(t_{\text{snapshot}})`.
  5. Tick function return value `return t_{\text{snapshot}}`.
Where a continuous loop initiates a new backend cycle, the loop remainder is explicitly defined as the new segment snapshot without re-sampling.

### 2.8 Seek and Resume Semantics Across Transport States (DEFECT-10 Resolution)

When seeking with hardware buffer latency $L = \text{buffer\_latency\_ms} > 0$, three coordinate spaces interact:
1. **Requested Timeline Coordinate ($T$):** The timeline point selected by user interaction, script, or seek slider.
2. **Backend Source Coordinate ($T$):** The byte/sample offset where the audio backend begins streaming audio. Source audio is never skipped ($T_{\text{source}} = T$).
3. **Estimated Audible Coordinate ($t_{\text{audible}}$):** The acoustic position reaching the listener's ears.

When a playback segment begins or seeks to start coordinate $S$:
- During the hardware buffer-fill interval ($t_{\text{device}} \in [S, S + L]$), samples $[S, S + L]$ are entering the hardware FIFO. The acoustic output at the DAC is held at segment start:
  $$t_{\text{audible}} = S$$
- Once the buffer is full ($t_{\text{device}} \ge S + L$), the audible sound emerges smoothly from the speaker:
  $$t_{\text{audible}} = t_{\text{device}} - L$$
- The unified audible position formula is:
  $$t_{\text{audible}} = \max(S, t_{\text{device}} - L)$$

Behavior across states:
- **STOPPED:** `seek(T)` sets `_software_pos_ms = T` and `_segment_start_ms = T`. State remains `STOPPED`. Subsequent `play()` begins from $S = T$.
- **PLAYING:** `seek(T)` updates backend source to $T$, sets $S = T$, and delivers $T$ to playhead and callbacks without backward jumps.
- **PAUSED:** `seek(T)` sets `_paused_audible_pos_ms = T`, `_paused_device_pos_ms = T`, and `_segment_start_ms = T`. Position reports $T$.
- **RESUME:** `resume()` after paused seek begins from $S = T$. During buffer-fill interval $[T, T + L]$, position reports $T$. No backward jump (e.g. from 600 ms to 580 ms) occurs upon resume.
- **Boundary Conditions:** Positions near track start ($T < L$) and track end ($T > T_{\text{total}} - L$) remain strictly non-decreasing and complete cleanly without cursor regressions.
- **Zero-Latency Controls:** When $L = 0$, $t_{\text{audible}} = t_{\text{device}}$, and all state transitions are instantaneous.

### 2.9 Loop Restart Source Audio Preservation (DEFECT-10A Resolution)

When a loop boundary is crossed, the backend must not skip audio to artificially match buffer latency.
In `step_tick()`:
$$t_{\text{start\_device}} = t_{\text{remainder}}$$
The audio backend is instructed to begin playing from $t_{\text{remainder}}$. At the instant of restart:
- Both visual transport and backend device start at $t_{\text{remainder}}$ (e.g. 0.0 ms $\to$ 0.0 ms).
- Segment start coordinate is set: $S = t_{\text{remainder}}$.
- Buffer-fill interval $[S, S + L]$ holds audible coordinate at $S$ while hardware FIFO buffers fill, before advancing at $t_{\text{device}} - L$.
- No source audio is skipped or dropped.

### 2.10 Failed Seek Coordinate & Callback Integrity (DEFECT-09A Resolution)

When a backend seek operation raises an exception:
- State transitions to `TransportState.ERROR`.
- The authoritative coordinate prior to the failed seek (`pre_seek_pos`) is preserved in `_software_pos_ms` and `_paused_audible_pos_ms`.
- Active events are evaluated at `pre_seek_pos`.
- Visual callbacks are notified with `pre_seek_pos` (`self._notify_tick(pre_seek_pos)`).
- Error callbacks receive the exception.
- The unachieved seek target coordinate is never delivered to visual callbacks.

### 2.11 Failed Stop and Reset Coordinate & Callback Integrity (DEFECT-09B Resolution)

When a backend stop or reset operation raises an exception:
- State transitions to `TransportState.ERROR`.
- The authoritative coordinate prior to the failed stop/reset (`pre_stop_pos` or `pre_reset_pos`) is preserved in `_software_pos_ms` and `_paused_audible_pos_ms`.
- Active events are evaluated and maintained at the preserved coordinate.
- Visual callbacks are notified with the preserved coordinate (`self._notify_tick(pre_stop_pos)`).
- Error callbacks receive the exception.
- The unachieved 0.0 ms target coordinate is never delivered to visual callbacks.
- On successful stop or reset, state transitions to `TransportState.STOPPED`, position is set to 0.0 ms, active events are updated to 0.0 ms, and visual callbacks receive 0.0 ms.

### 2.12 Systematic Lifecycle Transaction Discipline (DEFECT-09C, DEFECT-09D, DEFECT-09E Resolutions)

All lifecycle operations adhere to a unified transaction discipline:
1. **Acquire/Preserve Valid Snapshot:** Capture authoritative valid coordinate prior to the operation (`pre_operation_pos`).
2. **Calculate Proposed Destination:** Derive intended target ($T_{\text{target}}$) without mutating stored coordinates.
3. **Attempt Backend Hardware Operation:** Execute backend call inside controlled `try...except`.
4. **Commit On Success:** Mutate `_software_pos_ms`, segment coordinates, and state only after backend hardware confirmation.
5. **Rollback On Failure:**
   - Transition to `TransportState.ERROR`.
   - Preserve valid authoritative coordinate in `_software_pos_ms` and `_paused_audible_pos_ms`.
   - Recompute active events at the preserved coordinate.
   - Dispatch the preserved coordinate to visual callbacks (`self._notify_tick(delivered_pos)`).
   - Dispatch error notification and re-raise exception.

### 2.13 Verified Non-Playing Backend Condition on ERROR Recovery (DEFECT-09H Resolution)

When recovering from `TransportState.ERROR` via `seek(target)`, the transport must establish that the audio hardware is in a verified non-playing condition before transitioning to `TransportState.PAUSED`. If a prior `stop()` or teardown failure left the backend in an unacknowledged or actively playing condition, reporting `PAUSED` would create a severe contract violation where the transport claims to be paused while the backend continues outputting sound and advancing hardware device position.

The transport enforces an explicit two-stage recovery transaction (Option B):
1. **Enforce Backend Silence:** Call `self.audio_backend.stop()` to halt any active playback and verify that `backend.is_playing == False`.
2. **Abort On Stop Failure:** If `stop()` raises `AudioBackendError`, the recovery transaction is immediately aborted: the transport state remains `TransportState.ERROR`, internal coordinates remain preserved at `pre_seek_pos`, active events remain evaluated at `pre_seek_pos`, visual listeners receive `pre_seek_pos`, registered error callbacks are notified, and `AudioBackendError` is re-raised. The transport never falsely transitions to `PAUSED`.
3. **Commit On Dual Success:** If `stop()` succeeds and `backend.seek(clamped_target)` succeeds: both required hardware operations succeeded; state transitions cleanly to `TransportState.PAUSED`, all coordinate latches (`_paused_device_pos_ms`, `_paused_audible_pos_ms`, `_software_pos_ms`, `_segment_start_ms`) synchronize to `clamped_target`, active events update to `clamped_target`, and visual listeners receive `clamped_target`. Clock advances verify that device position remains locked at `clamped_target` without advancing until playback is explicitly resumed.

### 2.14 Explicit Backend Session Contract & Resumption from Recovery (DEFECT-09I Resolution)

In multimedia hardware drivers such as Windows MCI waveaudio, hardware playback modes possess distinct control requirements:
1. **Paused Session Mode:** Initiated strictly via `pause <alias>` during active playback. The hardware preserves its streaming context and can be resumed via `resume <alias>`.
2. **Stopped and Positioned Mode:** Initiated when the device is stopped via `stop <alias>` and positioned via `seek <alias> to <target>`. In this mode, the device driver is not in a paused playback session. Calling `resume <alias>` is invalid and cannot restart audio streaming; playback must be initiated via `play <alias> from <target>`.
3. **Active Playback Mode:** Initiated via `play <alias> from <target>` or `resume <alias>`. `is_playing` reports `True`.
4. **Unavailable or Failed Mode:** Driver is closed, failed, or uninitialized.
5. **Headless / Simulated Mode:** Controlled timing via virtual clock.

Prior to DEFECT-09I, `PlaybackTransport.play()` defaulted `getattr(backend, "is_paused", True)` to `True` when resuming from `PAUSED` state. In Windows MCI, following stop-and-seek recovery from `ERROR`, the device was stopped and positioned at the target, but `_is_paused` was `False`. Consequently, `resume()` was called, which silently returned without issuing any MCI command, yet `PlaybackTransport` transitioned to `PLAYING`.

Under DEFECT-09I resolution:
- All `AudioBackend` implementations expose explicit `@property def is_playing(self) -> bool` and `@property def is_paused(self) -> bool`.
- `WindowsMciAudioBackend.resume()` and `SimulatedAudioBackend.resume()` explicitly raise `AudioBackendError` if invoked when `is_paused` is `False`. Silent no-ops are completely eliminated.
- In `PlaybackTransport.play()`, resumption checks `can_resume = is_resuming and getattr(self.audio_backend, "is_paused", False)`. When recovering from `ERROR` or when seeking while stopped, `is_paused` is `False`, ensuring that `backend.play(start_ms=start_device, loop=self._loop)` is executed, sending `play <alias> from <target>` directly to the driver.
- In `PlaybackTransport.seek()`, recovery from `ERROR` executes `self.audio_backend.stop()`, verifies that `self.audio_backend.is_playing == False`, and executes `self.audio_backend.seek(clamped_target)`.
- The architecture strictly distinguishes:
  1. *Command Acknowledgement:* The backend command executed without throwing an exception.
  2. *Backend-Maintained State:* Internal driver state flags (`is_playing`, `is_paused`, status) confirm state consistency.
  3. *Physical Acoustic Observation:* Physical audio propagation from speakers, requiring human ear or microphone observation.

---

## 3. Audio Backend Architecture & Failure State Machine

### 3.1 Architecture Hierarchy

```
 owner thread (Tk main thread in the GUI) ─ every arrow below runs on it
┌──────────────────────────────────────────────────────────────┐
│                      PlaybackTransport                       │
│  - owner-thread guard on every lifecycle operation           │
│  - one device observation per update (_query_device_...)     │
│  - transaction helpers: _set_stationary / _fail / _publish   │
│  - immutable TransportSnapshot per commit (seq, epoch, ...)  │
│  - at most one pending scheduled update (generation token)   │
│  - exact source timing; half-open active-event membership    │
│  - device end-of-media -> exact media end; silent tail       │
│  - close(): cancel, stop, unload, detach callbacks           │
│  - callbacks: snapshot, tick(t, ids), state, end, error      │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
 ┌─────▼─────┐       ┌─────▼─────┐        ┌──────▼───────┐
 │   Clock   │       │ Scheduler │        │ AudioBackend │
 └─────┬─────┘       └─────┬─────┘        └──────┬───────┘
       ├─ RealClock        ├─ TkScheduler        ├─ WindowsMciAudioBackend (observe(): mode + position)
       └─ TestClock        └─ ManualScheduler    ├─ SimulatedAudioBackend
                                                 └─ NullAudioBackend
```

### 3.2 Unified Coordinate Acquisition (`_query_device_and_audible_progress`)

To ensure complete mathematical and state consistency, all transport operations rely on `_query_device_and_audible_progress(record_drain_latch)`:
1. Takes one `backend.observe()` (one position query; for Windows MCI also the acknowledged device mode, Section 7.4). Exceptions are caught and wrapped in `AudioBackendError`. An observed unexpected early stop raises `AudioBackendError`. Observed end-of-media replaces the floored integer device position with the exact media duration. During a silent tail (timeline longer than the media) progress follows the transport clock without device queries.
2. Validates coordinate integrity: rejects `NaN`, `inf`, `-inf`, or negative coordinates with `AudioBackendError`.
3. Handles intentional headless fallback: if backend is `NullAudioBackend` or not available, returns software clock time.
4. Detects unexpected coordinate loss: if an available backend unexpectedly returns `None`, raises `AudioBackendError`.
5. Calculates buffer latency subtraction with segment start bounding ($\max(S, \text{dev\_pos} - L)$) and smooth wall-clock buffer drainage.

### 3.3 Explicit Coherent Failure State (`TransportState.ERROR`)

When any backend operation fails during active playback, seeking, pausing, stopping, or ticking:
1. **State Transition:** The transport transitions immediately to `TransportState.ERROR`.
2. **Device Status:** Backend sets `AudioBackendStatus.FAILED` and clears `is_playing = False`.
3. **Position Preservation:** The last valid playback position is preserved in `position_ms` and `_software_pos_ms`, preventing resets or wild jumps.
4. **Scheduled Update Cancelled; Controlled Shutdown:** The single pending scheduled update is cancelled and its generation invalidated. If the backend may still be producing audio (`is_playing`), `backend.stop()` is attempted. A secondary shutdown failure is attached to the original error (`secondary_shutdown_error` and an exception note); it does not replace it.
5. **Notification:** One immutable snapshot of the ERROR state is published, then the error callbacks are dispatched, all on the owner thread.
6. **No False Reports:** A failed `stop()` does NOT transition to `STOPPED` or report position 0.0; a failed natural completion does NOT dispatch `on_playback_ended`; a failed `seek()` does NOT report or publish the unachieved seek target coordinate.
7. **Controlled Teardown & Recovery:** Calling `transport.reset()` provides clean device teardown from `ERROR` to `STOPPED`; calling `transport.play()` attempts clean restart from the preserved position once device issues are resolved.

### 3.4 Windows MCI Audio Backend (`WindowsMciAudioBackend`)

Windows audio playback is implemented natively via the standard library using `ctypes.windll.winmm.mciSendStringW`:
- **Zero Third-Party Dependencies:** Pure standard library.
- **Asynchronous Output:** Uses Windows MCI waveaudio driver for non-blocking playback.
- **Cross-Platform Initialization:** Initialized to `AVAILABLE` on Windows with `winmm`, and `UNAVAILABLE` on non-Windows platforms.
- **Device Position:** Queries `status <alias> mode` and then `status <alias> position` (integer milliseconds) from the driver, on the owner thread only.
- **Lifecycle Control:** Full support for `open`, `play from <ms>`, `pause`, `resume`, `seek`, `stop`, and `close`.
- **Reproduced device facts** that the backend is built around are listed in Section 7.4.

### 3.5 Explicit Lifecycle State-Transition Matrix

The following specification matrix governs all transport states and lifecycle operations:

| Current State | Operation | Permitted? | Backend Operation Executed | Position On Success | Resulting State On Success | Preserved Position On Failure | Resulting State On Failure | Callbacks Dispatched |
|---|---|---|---|---|---|---|---|---|
| **STOPPED** | `play()` | Yes | `backend.play(start_ms=S, loop)` | $S$ ($0$ or seek pos) | `PLAYING` | Pre-op pos ($0.0$) | `ERROR` | StateChanged, Tick($S$), Error if fail |
| **STOPPED** | `pause()` | No-op | None | $0.0$ | `STOPPED` | N/A | N/A | None |
| **STOPPED** | `resume()` | No-op | None | $0.0$ | `STOPPED` | N/A | N/A | None |
| **STOPPED** | `seek(T)` | Yes | `backend.seek(T)` | $T$ | `STOPPED` | Pre-op pos | `ERROR` | StateChanged (if fail), Tick, Error if fail |
| **STOPPED** | `stop()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | Pre-op pos | `ERROR` | Tick, StateChanged, Error if fail |
| **STOPPED** | `reset()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | Pre-op pos | `ERROR` | Tick, StateChanged, Error if fail |
| **STOPPED** | `step_tick()` | No-op | None | Current pos | `STOPPED` | N/A | N/A | None |
| **PLAYING** | `play()` | No-op | None | Current pos | `PLAYING` | N/A | N/A | None |
| **PLAYING** | `pause()` | Yes | `backend.pause()` | $t_{\text{audible}}$ | `PAUSED` | $t_{\text{audible}}$ | `ERROR` | StateChanged, Tick($t_{\text{audible}}$), Error if fail |
| **PLAYING** | `resume()` | No-op | None | Current pos | `PLAYING` | N/A | N/A | None |
| **PLAYING** | `seek(T)` | Yes | `backend.seek(T)` (or replay) | $T$ | `PLAYING` | Pre-seek pos | `ERROR` | Tick($T$ or pre), Error if fail |
| **PLAYING** | `stop()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | Pre-stop pos | `ERROR` | Tick, StateChanged, Error if fail |
| **PLAYING** | `reset()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | Pre-reset pos | `ERROR` | Tick, StateChanged, Error if fail |
| **PLAYING** | `step_tick()` (linear) | Yes | Query dev pos | $t_{\text{snapshot}}$ | `PLAYING` | Pre-tick pos | `ERROR` | Tick($t_{\text{snapshot}}$), Error if query fail |
| **PLAYING** | `step_tick()` (natural end) | Yes | `backend.stop()` | $T_{\text{total}}$ | `STOPPED` | $T_{\text{total}}$ | `ERROR` | End & Tick (success), Error & Tick (fail) |
| **PLAYING** | `step_tick()` (loop wrap) | Yes | `backend.play(start_ms=rem)` | $t_{\text{rem}}$ | `PLAYING` | $T_{\text{total}}$ | `ERROR` | Tick($t_{\text{rem}}$ or $T_{\text{total}}$), Error if fail |
| **PAUSED** | `play()` / `resume()` | Yes | `backend.resume()` (or play) | $t_{\text{paused}}$ | `PLAYING` | $t_{\text{paused}}$ | `ERROR` | StateChanged, Tick($t_{\text{paused}}$), Error if fail |
| **PAUSED** | `pause()` | No-op | None | $t_{\text{paused}}$ | `PAUSED` | N/A | N/A | None |
| **PAUSED** | `seek(T)` | Yes | `backend.seek(T)` | $T$ | `PAUSED` | Pre-seek pos | `ERROR` | Tick($T$ or pre), Error if fail |
| **PAUSED** | `stop()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | $t_{\text{paused}}$ | `ERROR` | Tick, StateChanged, Error if fail |
| **PAUSED** | `reset()` | Yes | `backend.stop()` | $0.0$ | `STOPPED` | $t_{\text{paused}}$ | `ERROR` | Tick, StateChanged, Error if fail |
| **PAUSED** | `step_tick()` | No-op | None | $t_{\text{paused}}$ | `PAUSED` | N/A | N/A | None |
| **ERROR** | `play()` | Yes (recover) | `backend.play(start_ms=pos)` | Target start | `PLAYING` | Pre-play pos | `ERROR` | StateChanged, Tick, Error if fail |
| **ERROR** | `pause()` | No-op | None | Current pos | `ERROR` | N/A | N/A | None |
| **ERROR** | `resume()` | No-op | None | Current pos | `ERROR` | N/A | N/A | None |
| **ERROR** | `seek(T)` | Yes (recover) | `backend.stop()` then `backend.seek(T)` | $T$ | `PAUSED` | Pre-seek pos | `ERROR` | StateChanged, Tick, Error if fail |
| **ERROR** | `stop()` | Yes (recover) | `backend.stop()` | $0.0$ | `STOPPED` | Pre-stop pos | `ERROR` | StateChanged, Tick, Error if fail |
| **ERROR** | `reset()` | Yes (recover) | `backend.stop()` | $0.0$ | `STOPPED` | Pre-reset pos | `ERROR` | StateChanged, Tick, Error if fail |
| **ERROR** | `step_tick()` | No-op | None | Preserved pos | `ERROR` | N/A | N/A | None |
| **PLAYING** | `step_tick()` (device end-of-media observed) | Yes | `backend.stop()` (or `play from 0` when looping) | exact $T_{\text{total}}$ (or $0$) | `STOPPED` (or `PLAYING`) | $T_{\text{total}}$ | `ERROR` | End & snapshot (success), Error & snapshot (fail) |
| **PLAYING** | `step_tick()` (device stopped early) | Yes | none (device already stopped) | N/A | N/A | last committed pos | `ERROR` | StateChanged, snapshot, Error |
| **any** | `load_timeline()` | Yes | `stop()`, `unload()`, `load_wav_bytes()` | $0.0$ | `STOPPED` | $0.0$ (new source) | `ERROR` | snapshot (`load` / `load_failed`), Error if fail |
| **any** | `close()` | Yes (idempotent) | cancel update, `stop()`, `unload()` | N/A | closed | N/A | closed; aggregated error raised | none (callbacks detached) |

All operations except the read-only properties raise `TransportThreadError` when called from a thread other than the transport's owner, and `TransportClosedError` after `close()`. Every row that lists a Tick also publishes exactly one `TransportSnapshot`.

---

## 4. Visual Transport & GUI Integration

### 4.1 Transport Control Bar

A persistent, non-clipping dark control bar (`#0f172a`) is placed above the summary banner in `MusicGUI`. It holds Play, Pause, Stop, the Loop toggle, the time label (`mm:ss.mmm / mm:ss.mmm`), the audio mode badge, a draggable seek slider and Space/Escape shortcuts. The File menu offers "Open Audio WAV..." and "Open MusicXML...". `MusicGUI` owns one `PlaybackTransport` for its lifetime. The transport is created on the Tk thread with `RealClock()` and `TkScheduler(self)`, and the window registers exactly two callbacks: `_on_transport_snapshot` and `_on_transport_error`. Loading a new source (view switch, file import) calls `load_timeline()`, which replaces the source and releases the previous device resources.

### 4.2 Snapshot Rendering and Cursor Policy

Every published `TransportSnapshot` is rendered in every transport state, not only PLAYING. The slider, the elapsed-time label, the playhead cursor, the active-event highlighting and the button states all come from the same immutable snapshot.

**Cursor policy (applied consistently):**
- **Idle rest state = STOPPED at exactly 0 ms.** The cursor and highlighting are cleared, the slider is at 0 and the label reads `00:00.000`. This covers start-up, a successful Stop or Reset, a newly loaded source, and a seek to 0 while stopped.
- **Every other snapshot shows the cursor** at `snapshot.position_ms` and highlights exactly `snapshot.active_event_ids`. This includes PLAYING, PAUSED and ERROR, a seek while STOPPED to a non-zero position, and STOPPED at $T_{\text{total}}$ after natural completion, where under half-open membership no event is highlighted.
- Highlighting is shown if and only if the cursor is shown.
- Auto-scroll follows the cursor only while PLAYING.
- In the dual, duck and groups views no cursor is drawn, as before. An idle snapshot still clears any cursor left on the canvas.

**Stale-notification rejection.** `_on_transport_snapshot` discards three kinds of snapshot:
1. A snapshot from a transport other than the window's current one.
2. A snapshot from a superseded source (`source_id`).
3. A snapshot that does not supersede the last rendered one (`sequence` not greater).

**Failure display.** After a failed operation the ERROR snapshot keeps the cursor at the preserved coordinate, the Play button turns red, and the error callback writes the message into the audio badge. `on_transport_stop()` no longer clears the cursor itself; the transport's snapshot decides. A failed seek moves the slider back to the preserved coordinate. Mode-switch stops go through `on_transport_stop()`, so a device failure there is displayed instead of raising inside a Tk callback.

**Shutdown.** `MusicGUI.destroy()` calls `transport.close()` before tearing down the widgets (Section 7.6). A cleanup failure is logged, not hidden.

### 4.3 Timeline Canvas Playhead & Event Highlighting

- **Playhead Cursor:** Rendered as a distinct vertical crimson line (`#dc2626`, width 2.5) spanning the canvas height, capped with a crimson down-pointing locator arrow at the time header.
- **Active Sound Bar Highlighting:** Bars whose event IDs are in the snapshot's `active_event_ids` get a crimson border (`#dc2626`, width 3.5). Their original border colour and width are restored when they leave the set.
- **Redraw:** After a canvas redraw the cursor is re-applied with the last snapshot's own IDs. These come from exact-rational membership, not an integer-millisecond re-derivation from the timeline.
- **Smooth Auto-Scroll:** If the playhead advances past the visible horizontal viewport, `xview_moveto` scrolls the canvas while keeping the pinned left row badges stationary.

---

## 5. Author-Operated Manual Playback Verification Procedure

> [!IMPORTANT]
> Physical acoustic sound reproduction through hardware speakers requires direct human ear or microphone observation. The automated evidence column below comes from simulated backends, a behavioural MCI model, and the real Windows MCI device playing **silent** WAV data. None of it establishes what is heard or how sound and picture line up. Author results from the 2026-11-26 WAV re-test are recorded in the last column. The acceptance coverage matrix (`acceptance/acceptance_matrix.json`, run with `acceptance/run_acceptance.py`) maps every check to its automated tests; the remaining physical-only observations are optional (`JOB_03_REMAINING_LIMITATIONS.md`).

Follow this step-by-step verification procedure:

```powershell
python main.py
```

### Verification Checklist & Attribution Status

| # | Test Action | Expected Behavior | Automated evidence (not acoustic) | Author Direct Verification Status |
|---|---|---|---|---|
| 1 | **Audible Synthesized Playback** | Click **▶ Play** (or press **Space**). Audible sine tone sounds from speakers with smooth 5ms attack/decay envelopes. | Synthesized waveform verified; 0 digital clipping; real device reaches mode `playing` without MCI 263 (R1) | Author reported MusicXML import and playback work (2026-11-26); not separately re-tested |
| 2 | **Visual Cursor Advancement** | Playhead cursor advances across canvas; active sound bar borders turn bold crimson (`#dc2626`). | Snapshots every ~16 ms on the real device; GUI renders them; highlighted IDs equal snapshot membership (R10, D7 tests) | Covered by the Author's WAV re-test (playhead advances and stops at 4.000 s: PASS, 2026-11-26) |
| 3 | **Pause & Resume** | Press **Space** mid-playback; the sound stops and the cursor freezes. Press **Space** again; playback resumes. | Real device enters mode `paused` and its position stays fixed (R4). Known: the device coordinate steps about 18–35 ms forward across `pause`, so the cursor advances by that amount at the first update after resume (Section 7.8, item 3) | Row 1 toggled while paused: PASS (2026-11-26). Audible stop/resume not separately reported (optional P1) |
| 4 | **Interactive Seeking** | Drag horizontal seek slider across timeline or click position; release slider. | Seek in STOPPED, PAUSED and PLAYING renders the new coordinate and highlighting (D7 tests, R5) | Not reported; automated coverage A14 (optional P2) |
| 5 | **Natural Completion** | Allow playback to reach the end without Loop enabled. | Real device completes at the exact source duration, including fractional-ms WAVs; cursor rests at the end with no highlight (R2, R3, R10) | **PASS** (Author, 2026-11-26) |
| 6 | **Looping** | Check **Loop** checkbox; let playback reach end. | Transport restarts at 0 each cycle without error (R6). The restart is **not** seamless: 58–86 ms per cycle beyond the media duration was measured across 9 suite runs (Section 7.8, item 4) | Not reported; automated coverage A15 (optional P3) |
| 7 | **Original WAV Playback** | Select `File -> Open Audio WAV...` and choose a PCM WAV file. | Resubmission 3: import now succeeds (row-id fix; it previously always failed) and analysis runs in the background. The badge shows `[Audio: Analysing WAV...]` (about 26 s for a 4 s sustained file) while the window stays responsive, then `[Audio: Authentic PCM WAV]`. The original PCM is played. Legato notes without silence appear as **one** event (JOB-02 rule). Non-integer-ms durations complete (D2). | **PASS** (Author, 2026-11-26): import, responsiveness, dataset name, badge, audible original audio (four beeps) |
| 8 | **MusicXML Synthesis** | Select `File -> Open MusicXML...` and choose a score file. | Previous source unloaded (alias reused, previous temp WAV removed: R9, D8 tests); score notes synthesized | Author reported MusicXML import and playback work (2026-11-26) |
| 9 | **Input Source Switching** | Switch between Progressive Refitting, Duck Flight, and MIDI modes using top buttons. | Previous transport stops; the `load` snapshot resets slider, label and cursor (D7 test) | Source replacement **PASS** (Author, 2026-11-26) |
| 10 | **Clean Application Exit** | Close the application window while playback is actively playing. | `destroy()` closes the transport: pending update cancelled, device stopped and closed, own temp WAV removed (R10, D8 tests). There is no playback thread to terminate. | Shutdown **PASS** (Author, 2026-11-26); closing while audibly playing not specifically reported (optional P4) |

---

## 6. Verification & Benchmark Results

The complete verification record, with commands, exit codes, counts and real-device measurements, is in `JOB_03_VERIFICATION_LOG.txt`. Summary at the time of writing:

### 6.1 Automated Unit & Integration Tests

- `python -m unittest discover tests -v`: **272 tests; 259 passed, 13 skipped, 0 failures, exit code 0** (resubmission 2; resubmission 1 was 260 / 250 / 10).
  - The 206 pre-existing tests all pass, and **none was modified**: 64 in `tests/test_audio_playback.py`, 15 group-discovery tests and 127 baseline tests.
  - `tests/test_playback_consolidated.py`: 53 deterministic regression tests for D1–D8 (44 from resubmission 1 + 9 completion-predicate tests containing 672 subtests: 200 playback scenarios and 472 predicate-equivalence checks), run against the behavioural MCI driver model, the simulator and the GUI.
  - `tests/test_playback_windows_device.py`: 13 opt-in real-device tests, **skipped** unless `MUSIC_REAL_AUDIO_TESTS=1`.
- `MUSIC_REAL_AUDIO_TESTS=1 python -m unittest tests.test_playback_windows_device -v`: **13 passed, 0 skipped, exit code 0** on the real Windows MCI device with silent PCM WAV (final run).
- A defect re-introduction check (14 mutations, one or more per defect, including the thirteenth-revision completion predicate) confirmed that each fix is detected by the new tests when it is reverted.

### 6.2 Standalone Verification Script (`verify_playback_transport.py`)

- **8 / 8 scenarios, 44 / 44 assertions, exit code 0.** Assertions are unchanged from the thirteenth revision; only the printed wording of Scenarios 6 and 7 was corrected (Section 7.8).
- All eight scenarios use `TestClock` and `SimulatedAudioBackend`. They measure simulated timing and software execution cost, not physical audio output.

---

## 7. Consolidated Architectural Correction (Defects D1–D8)

The JOB-03 investigation reproduced eight defects in the thirteenth revision. The most severe, D1: with the real Windows device, playback entered ERROR about 15 ms after Play, the playhead stayed at 0 while the audio played on, and Pause could not stop it. The correction below replaces the playback threading, notification and device-reconciliation model. The timing mathematics, exact source timing, half-open membership, synthesis and failure-coordinate semantics of Sections 2–3 are preserved.

### 7.1 Scheduler and Thread Ownership (D1, D4, D6)

- **No playback thread.** Periodic updates are scheduled through an injected `Scheduler`:
  - `TkScheduler(widget)` uses `widget.after()`, so updates run on the Tk thread.
  - `ManualScheduler([test_clock])` runs updates only when `advance()` or `run_due()` is called, moving the `TestClock` to each due time.
  - A transport constructed without a scheduler gets an inert `ManualScheduler`. If it is played with a real clock, a warning is logged, because nothing will then advance it automatically.
- **Owner thread.** The transport records the thread that constructed it. `load_timeline`, `play`, `pause`, `resume`, `stop`, `seek`, `reset`, `step_tick` and `close` raise `TransportThreadError` on any other thread.
- **MCI device ownership.** The backend records the thread that opened the alias. Every MCI command, including open, play, pause, resume, seek, status queries, stop and close, is checked before it is sent. A cross-thread command raises `MciThreadOwnershipError` without reaching MCI and without changing backend status. (Real MCI answers such a command with error 263.)
- **At most one pending update.** `_ensure_tick_scheduled()` schedules only if no handle is pending. Every transition out of PLAYING cancels the handle and increments a generation token. A callback that has already been dequeued by the event loop checks the token and returns without effect, so an obsolete callback cannot restart or advance a stopped, closed or superseded session.
- **Replay at completion.** Natural completion cancels the update before notifications are delivered. A `play()` made from inside the end notification therefore schedules its own single update, and the finishing callback does not add a second (D6).
- **GUI thread budget, measured on the real device.** A transport update (two MCI status queries plus membership) took 0.23 ms on average and at most 0.41 ms. Updates arrived every 16.1 ms on average, at most 26.5 ms apart. During playback in `MusicGUI`, 1 ms Tk timers were late by a median of 0.01 ms, p95 0.27 ms and at most 8.4 ms (n = 523). With a 5,000-event timeline on the simulator an update took a median of 0.12 ms and at most 0.39 ms, because the exact event intervals are converted once at load.

### 7.2 Immutable Authoritative Snapshots (D5)

`TransportSnapshot` is a frozen dataclass with these fields:
- `transport_id`, `source_id`, `epoch`, `sequence`;
- `state`, `position_ms`, `active_event_ids` (a `frozenset`);
- `total_duration_ms`, `looping`, `reason`.

- Each commit sets the committed coordinate (`_software_pos_ms`) and recomputes membership at that same coordinate. It then builds one snapshot from the committed values under the lock.
- Delivery runs outside the lock. In order: state callbacks if applicable, snapshot callbacks, tick callbacks, end callbacks, error callbacks. Delivery reads only the snapshot, with no device query and no re-read of mutable state. Tick callbacks keep their `(position_ms, active_ids)` signature, and both values come from the snapshot.
- `sequence` increases strictly for each transport. A callback that changes the transport during delivery causes later callbacks to receive the newer snapshot first. Consumers reject the older one with `snapshot.supersedes(last)`, which `MusicGUI` does.
- `epoch` increments at every coordinate discontinuity: load, seek, stop, reset, start from STOPPED or ERROR, and loop wrap. Within an epoch the position of a PLAYING transport never decreases.
- `transport.snapshot` returns the last published snapshot without device I/O. The GUI uses only snapshots.
- `position_ms` and `estimated_audible_position_ms` remain live device queries while PLAYING, because the 206 existing tests require them to track device progress between updates. They now raise `AudioBackendError` if the device cannot be read, where previously they silently fell back to software time. A read never changes transport state.

### 7.3 Lifecycle Transactions (D3, D5)

Shared helpers replace the copy-pasted failure blocks:
- `_set_stationary(state, pos, device_pos)` commits STOPPED, PAUSED or ERROR at an achieved coordinate, recomputes membership and cancels the scheduled update.
- `_fail(error, preserved_pos, ...)` commits ERROR at a previously achieved coordinate. If the backend may still be producing audio, it first attempts controlled shutdown (`backend.stop()`). A secondary shutdown failure is attached to the original error, not substituted for it.
- `_publish(reason)` and `_deliver(snapshot, ...)` build and deliver exactly one snapshot per operation.

These invariants are preserved and exercised by the unchanged tests:
- A proposed destination is never published before the backend succeeds.
- A failure preserves a valid documented coordinate.
- State, position, membership and notifications agree.
- Recovery from ERROR requires backend acknowledgement: a successful `stop()` with `is_playing == False` before a recovery seek.
- Software rollback is not taken as evidence of device rollback.

A failed pre-operation position query is attached as an exception note when the operation itself fails (stop, reset, seek).

`load_timeline()` validates and prepares the new source before touching the current one, so a malformed source leaves the previous source intact. It then stops, unloads and loads. A device failure during load leaves the new source's metadata in place in ERROR at 0, with its partially opened resources released.

### 7.4 Device State Reconciliation and Exact Completion (D2, D3)

Device facts reproduced on this Windows machine with silent WAV data (`diag_mci_real.py`, `probe_mci_facts.py`, `probe_pause_position.py`):

| Fact | Observation |
|---|---|
| Thread affinity | Commands from a thread other than the opener fail with 263 |
| Length | `status length` is the floor of the exact duration: 22,070 frames at 44.1 kHz = 500.4535 ms reports `500` |
| End of media | The device stops itself: mode `stopped`, position equal to `length` |
| `seek` | Leaves the device in mode `stopped`, including when it was playing |
| `stop` | Does not rewind the position |
| `pause` / `resume` on a stopped device | Error 302 |
| `play from` / `seek to` beyond `length` | Error 282 |
| `pause` while paused | Accepted |
| `play from` while paused or playing | Restarts at the given position |
| Position while playing | Integer ms, about 3–35 ms behind wall time since `play` (startup latency) |

How the backend uses these facts:
- `WindowsMciAudioBackend.observe()` queries `status mode` first and then `status position`. Mode comes first deliberately: if the media ends between the two queries, the device is seen as still playing at its final position, and the next observation reports the stop. The reverse order could pair a pre-end position with a post-end `stopped` mode and misclassify a natural end as an early stop.
- An uncommanded `stopped` while `is_playing` is classified with the device's own length. If position ≥ length − 1 ms (`MCI_END_OF_MEDIA_TOLERANCE_MS`), it is **end of media**; otherwise it is an **unexpected early stop**. Both are latched until the next play, resume, seek or stop.
- Observations reconcile `is_playing` and `is_paused`, so the cached flags no longer contradict the device after end of media (D3).
- `pause()` checks the device mode itself and sends no `pause` to a stopped device. `resume()` refuses to send `resume` unless the device reports `paused`. So neither command can produce 302.
- **Exact completion.** When end of media is observed, the transport replaces the floored device position with the exact media duration $\text{frames} \times 1000 / \text{rate}$. Completion is then decided against the exact source duration with the symmetric predicate of Section 7.9. The 22,070-frame (round-up) and 22,071-frame and 4,801-frame @ 48 kHz (round-down) WAVs complete at their exact durations on the real device and under the model; the 1,000 ms control completes at 1,000 ms.
- **Unexpected early stop** puts the transport in ERROR at the last committed coordinate. The error message reports the device position and length. It is never reported as completion.
- **Silent tail.** If the source is longer than the media (for example a timeline event ending after the WAV), progress continues on the transport clock from the reached media end until $T_{\text{total}}$, then completes normally. It starts from the larger of the exact media end and the last committed position, so it never moves backwards.

### 7.5 Exact Source Timing versus Integer Device Coordinates

- **Source coordinates are never changed for the device.** Event timing stays exact: membership uses the exact rational interval endpoints, converted once at load and compared with the same float semantics as before. $T_{\text{total}}$ and seek targets keep their exact values; seeking to 1234.4 ms publishes 1234.4 ms.
- **Device commands.** `play from` and `seek to` use $n = \min(\text{round}(t), L)$, where $L$ is `status length`. The rounding error is at most 0.5 ms. Clamping to $L$ prevents error 282. Any source time beyond $L$ is handled as the silent tail.
- **Positions during playback** are the device's integer readings, bounded below by the segment start $S$ (exact): $t = \max(S, t_{\text{device}} - L_{\text{buf}})$, unchanged from Section 2.8. Before the first device advance the published value may therefore be the exact $S$ (e.g. 250.4) and then the integer device value (e.g. 251). The quantisation error is below 1 ms plus the 0.5 ms command rounding.
- **At completion** the exact media duration replaces the floored integer, so the published end coordinate is exact.
- **Production buffer latency** is 0 (`buffer_latency_ms=0.0`). The buffer-drainage model of Section 2.2 is exercised only by tests.

### 7.6 Resource Ownership and Cleanup (D8)

- **Temp WAV files.** `WindowsMciAudioBackend` creates exactly one temp WAV per loaded source, through `tempfile.mkstemp` with prefix `music_play_` and an optional `temp_dir`. `unload()`/`close()` stops and closes the alias and removes **only that file**. Every step is attempted. Failures are collected in `last_cleanup_errors` and raised together.
- **Failed close.** A failed `close` leaves the alias marked open, and its file in place because MCI may still hold it, so a later unload can retry.
- **Failed open.** A failed open after the temp file is written removes the file and closes any opened alias.
- **Transport close.** `PlaybackTransport.close()` is idempotent. It cancels and invalidates the scheduled update, stops audio if any may be active, unloads the device, detaches all callbacks, and raises an aggregated error if any step failed. Afterwards every lifecycle operation raises `TransportClosedError`.
- **Source replacement** (`load_timeline`) stops and unloads the previous source, so the alias is closed and reopened and the previous temp file removed, before loading the new one.
- **Application shutdown.** `MusicGUI.destroy()` calls `close()`.
- **Measured.** A full run of the refactored test suite leaves 0 new temp WAVs in `%TEMP%`. The pre-change run of the thirteenth-revision suite left 20.
- **Existing temp files.** The 463 temp WAVs found by the investigation were not touched; only files proven to be created by this work's own diagnostic runs were removed (see the verification log).

### 7.7 Verification Model (Simulator Realism)

- `tests/test_playback_consolidated.py` contains `FakeWinmm`, a behavioural model of `winmm.mciSendStringW` and `mciGetErrorStringW`. It encodes the facts in the Section 7.4 table and adds fault injection (failing commands, early stop).
  - The production `WindowsMciAudioBackend`, including `_send_mci` and its ctypes buffers, runs unmodified against it, driven by a `TestClock` and `ManualScheduler`.
  - The model was checked against the facts recorded on the real device, and each D1–D8 fix was reverted one at a time to confirm that the new tests fail without it.
- `SimulatedAudioBackend` is unchanged, because 64 existing tests define its behaviour.
- `tests/test_playback_windows_device.py` (opt-in) drives the real device through the production configuration with silent WAV in a test-owned temp directory. Its measurements are printed with a `[measure]` prefix.

### 7.8 Remaining Physical Synchronization Limitations

These are established limits of what was verified, not defects that were hidden.

1. **No acoustic measurement exists.** All device evidence uses silent WAV data and MCI's own reported coordinates. Agreement between published and device positions (about 15 ms, which is the time since the last update) is software/device agreement. Whether the cursor matches what is heard, and the ≤ 20 ms JOB-03 engineering target for audio/visual synchronization, can only be judged by the Author's checks or a loopback/microphone measurement.
2. **Startup latency.** After `play`, the device position lags wall time by about 30 ms (measured). The cursor follows the device coordinate, not wall time. From `play()` to the completion notification, wall time exceeded the exact duration by 43–92 ms in 8 of 9 real-device suite runs (R2, R3), and by 242–368 ms in the one degraded run (item 7). That figure includes startup latency and up to one update interval.
3. **Pause discontinuity (open question).** Immediately after `pause`, MCI reports a position about 17–35 ms *ahead* of the last reading taken while playing (5 of 5 probe trials: 296 → 321; R4 across runs: steps of 18–29 ms, e.g. 302 → 331 and 300 → 321). It resumes from that later coordinate after about 30 ms more startup latency. The transport keeps the pre-pause observed coordinate, as required by DEFECT-06 (no jump at pause). The published cursor therefore steps forward by that amount (19–34 ms measured) at the first update after resume.

   I guess this is driver buffering: the during-play reading is the rendered position and the post-pause reading is the submitted position. If so, the roughly 18–35 ms of audio between them may be skipped on resume. This has not been established. The alternatives are:
   - (a) commit the post-pause device coordinate, which moves the jump to pause time;
   - (b) resume with `play from <paused transport coordinate>` instead of `resume`, which may replay about 17–35 ms of audio.

   Either changes behaviour that existing tests define, so neither was adopted without acoustic evidence and review.
4. **Loop restart is not seamless.** The MCI media stops itself at its end, so the transport restarts from 0 on the next update. The gap is at most one update interval (about 16 ms) plus device restart latency (about 30 ms). Measured per-cycle wall time beyond the exact duration is 58–86 ms, an upper bound on the gap. The remainder-preserving loop arithmetic (Section 2.5) applies only to backends that report positions past the end, such as the simulator.
5. **MCI integer milliseconds.** Positions are integer ms. Command coordinates are rounded (≤ 0.5 ms) and clamped to the floored media length. The exact media end is recovered only at completion.
6. **Benchmarks.** `verify_playback_transport.py` uses `TestClock` and `SimulatedAudioBackend` throughout.
   - Scenario 6 (drift) is zero by construction.
   - Scenario 7 measures `seek()` plus membership cost on the simulator, which is software execution time.
   - Neither is evidence of audio/visual synchronization.
7. **Timing under system load (1 of 11 real-device suite runs failed).** In one run (`outputs/windows_real_device_tests_FAILED_run_2026-11-26T0736.txt`), every timing degraded 4–6× at once: 8 updates instead of about 25 in 400 ms, completion detected 242–368 ms late, 2 loop cycles instead of 3 in 1.8 s, and Tk timer lateness up to 52 ms. Two tests failed their update-count thresholds (R1 ≥ 10 updates, R6 ≥ 3 loops). No correctness assertion that ran failed: no error, exact completion, monotone positions. Repeating the identical code immediately afterwards passed 5 of 5 times, and so did the final run, and the instrumented diagnostic showed `step_tick` under 1 ms with 15.2 ms intervals. I guess the cause was external CPU or audio-subsystem load (the IDE was the dominant CPU consumer), but this was not proven. The thresholds were kept, and the tests now print their measurements before asserting, so any recurrence is diagnosable. A single-thread Tk design cannot deliver updates when the Tk loop itself is starved; it degrades to fewer, later updates and does not produce wrong coordinates.
8. **Blocking cost of user commands on the GUI thread** (measured, `outputs/mci_command_cost.txt`):
   - periodic updates (`status` mode and position): ≤ 1.3 ms (≤ 5.4 ms near end of media);
   - `pause` about 6 ms; `play from` about 16 ms (max 25);
   - `stop` while playing about 44 ms (max 62);
   - `seek` while playing about 55 ms (max 60), plus `play from`.

   A Stop or a seek during playback therefore freezes the window for up to about 60–75 ms. A possible optimization, not adopted, is a seek while playing as a single `play from N`: the device was observed to restart at N in that case, which would cut the cost to about 16 ms.

### 7.9 Completion Predicate Correction (independent audit, resubmission 2)

ChatGPT's independent audit found that fractional-duration completion was still not correct for all durations. The thirteenth-revision predicate `round(p, 6) >= T`, which resubmission 1 preserved, rounds only the left side. Confirmed end of media yields p = T exactly. Whenever `round(T, 6) < T`, completion and loop restart therefore never happened; 22,071 frames at 44.1 kHz is an example (T = 500.4761904761905, `round(T, 6)` = 500.47619). The 22,070-frame case had passed only because its duration rounds up. This was reproduced under the MCI model, under a simulator capped at the exact T (backend-independent), and on the real device with the resubmission-1 module (`outputs/round_down_real_device.txt`).

Correction, localized to `PlaybackTransport`:
- `_has_reached_end(p)` is the single completion predicate, used by natural completion, loop restart and the silent-tail decision. It holds when `p >= T - 5e-7` ms.
- The comparison is symmetric. For every T that is a multiple of 1e-6 ms (all integer-ms and six-decimal durations) it accepts exactly what the old predicate accepted, apart from exact half-way ties; this was verified on a grid. It is about 45,000× smaller than one 44.1 kHz sample and 2,000,000× smaller than the 1 ms MCI resolution.
- T and every source coordinate stay unrounded. The published end coordinate is exactly T.
- `_loop_remainder_ms(p)` keeps `p mod T` (as before) only for p ≥ T. Progress that reached T from below, within the tolerance, restarts at 0. Without this, `p mod T ≈ T` would restart the device just before its end.
- Completion still requires evidence. Progress stuck 10 ns (20× the tolerance) or 1 ms short of T does not complete.

Note on buffer latency: the drain clock starts when end of media is *observed*, up to one update after it happened. With nonzero latency, completion can therefore arrive up to two update intervals after the device's floored length. Production latency is 0.

### 7.10 WAV Import Path (Author manual verification, resubmission 3)

During interactive verification the Author found that **Open Audio WAV** fails for every file, and that the controlled test WAV crashes the application with an access violation. The full investigation is in `JOB_03_WAV_CRASH_EVIDENCE/WAV_CRASH_INVESTIGATION.md` (also in the review archive).

**Defects found and corrected** (all in `music_gui/main_window.py`, a JOB-03 file; `music_model/audio_importer.py` (JOB-02) is unchanged):

1. **Row-id mismatch.** The handler added importer events, labelled `row_id="row_audio"`, to a row created as `"Row 2"`. `TemporaryRow.add_event` rejects that, so WAV import never succeeded, whatever the file. The handler now passes `row_id=WAV_IMPORT_ROW_ID` ("Row 2") to the importer.
2. **Analysis on the Tk thread.** The JOB-02 analysis is pure-Python and `O(N × lags)`; it took about 26 s for the Author's 4-second legato file. It ran inside the Tk callback, so Windows declared the window hung: the Author's session shows AppHang events and two hung-window closures. It now runs on a daemon worker thread (`_WavImportJob`):
   - The thread touches no widget, transport or device.
   - `_poll_wav_import` (Tk `after`) applies the result on the Tk thread, which owns the transport and the MCI device, as Section 7.1 requires.
   - The original PCM bytes become the playback source.
   - A second open during analysis is refused with a message, not queued.
   - An analysis error is reported on the Tk thread and leaves the previous source untouched.
   - `destroy()` invalidates an unfinished analysis and cancels its poll.

   Measured during analysis: the largest Tk event-loop gap was about 128 ms, and the window was never reported hung under visible-window, real-dialog, user-input conditions.

3. **Stale asynchronous import (found by ChatGPT's audit of resubmission 3; corrected).** A WAV analysis started before the Author selected another source or mode still published its result when it finished. The newer selection was overwritten while the GUI still showed the new mode. The lifecycle policy is now:
   - **Latest selection wins.** `_source_generation` is incremented on every source or mode selection, through two funnels:
     - `_set_active_mode_button`, called by every `show_*_mode`, including Dual, Duck and Groups, which do not reload the transport;
     - `_sync_transport_with_current_timeline`, through which every source is installed.
   - **Authority is separate from lifetime.** A job may publish only while it is `_wav_import_job` and its `generation` equals `_source_generation` (`_has_publish_authority`). `_supersede_pending_wav_import` withdraws that authority and cancels the poll.
     - The worker thread is never terminated; it finishes and its result is discarded.
     - An obsolete success changes no timeline, transport or badge.
     - An obsolete failure shows no dialog.
     - The "Analysing" badge is replaced at once by the truthful badge for the current transport; the saved-badge restore was removed.
   - **No accumulation.** At most one analysis computes at a time.
     - While a pending import has authority, a second open is refused (as before).
     - While a superseded worker is still computing, a new open is refused with a message, not queued.
   - **Unchanged rules.** Tk-thread ownership, original PCM bytes and source timing are unchanged. `destroy()` supersedes any pending import, so teardown is unaffected by a running worker.
   - **Not a selection.** A cancelled file dialog, or a failed MusicXML/MIDI/JSON load, selects nothing, so the import still publishes.
   - **Row 1 toggle (policy revised by item 4).** The resubmission-4 toggle reloaded the source, so it also superseded a pending import. Item 4 makes the toggle display-only, so it is **no longer a source selection**: a pending import keeps its authority and publishes under the Row 1 mode in force when it completes.

4. **Row 1 source preservation (ChatGPT audit of resubmission 4; corrected).** Row 1 is a mathematical representation of the current source, not a source.
   - **Defect.** `_toggle_constant_row_mode` re-ran `show_midi_mode(current_song)` in MIDI mode, and `_update_summary()` elsewhere. `_update_summary()` always ended by reloading the transport. Every toggle therefore:
     - replaced an imported WAV's original PCM with synthesized audio;
     - stopped playback and reset the position to 0;
     - renamed WAV and MusicXML datasets to `Imported: <file>`, with the badge following the new audio.

     The WAV and MusicXML installers also loaded the transport twice: once through `_update_summary()`, then explicitly.
   - **Correction** (`music_gui/main_window.py` only; Row 1 algorithms unchanged):
     - `_refresh_summary_display()` updates the banner labels and never touches the transport.
     - `_update_summary()` = display refresh + `_sync_transport_with_current_timeline()`. It is kept for genuine source selections, and all its existing callers are such selections.
     - The Row 1 toggle calls only the display refresh. In MIDI mode it relabels the existing button in place (`_btn_row1_toggle`).
     - The canvases redraw via `set_constant_row_mode`, which re-applies the playback cursor.
     - Transport state, position, snapshot, PCM bytes, event identity and timing, dataset identity and badge are untouched. Duck and dual modes already refreshed labels only.
     - The WAV and MusicXML installers call the display refresh, then sync **once**: original PCM for WAV, synthesized audio for MusicXML.

**The access violation.** It is memory corruption below the Python level, observed as corrupted float objects during the long analysis loop; in one reproduction the fault was at `PyNumber_Multiply`. Pure-Python project code cannot cause it, and the generator expression in the traceback is where the corrupted objects are used, not the defect. Its source is **not established**: it is either a layout-dependent CPython 3.15.2 defect or system instability (this machine recorded kernel bugchecks 0x0A, 0xD1 and 0xF5 between 2026-11-21 and 2026-11-26). Both fatal occurrences happened while the GUI was frozen by the synchronous analysis, a state the correction removes. The underlying corruption source is not removed by any project code change, so a crash cannot be claimed impossible.

**Supported interpreter configuration (as verified):** CPython 3.15.2 release build, Windows x64, GIL enabled, JIT disabled (the default), launched either as `.venv\Scripts\python.exe` or as `C:\Program Files\Python315\python.exe` (same build). No other CPython version was available on this machine for comparison.

**Unchanged JOB-02 behaviour (documented, not altered):**
- Legato notes without a silence of at least 20 ms below 5 % of peak form **one** energy event; the Author's file yields one event at E4.
- Analysis time grows as `O(N × lags)` per event.
- A bit-identical faster formulation of the three sums was verified, but it was not applied because it changes the JOB-02 file.
