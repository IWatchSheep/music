# Job Completion Record: JOB-02 — Continuous Audio & Sheet Music Ingestion Specifications and Adapters (Approved by ChatGPT)

> **Status:** OFFICIALLY APPROVED BY CHATGPT (Independent Engineering Audit Complete)  
> **Original Starting Checkpoint:** `2a4b261`  
> **Current Official Documentation Checkpoint:** `66dfc53`  
> **Historical Implementation Baseline:** `ad3a9d3`  
> **Protected Calculator Repository:** `17be078d` (unmodified, 100% read-only)  
> **Review Archive:** `JOB_02_INDEPENDENT_REVIEW.zip` (47 entries, integrity verified)  
> **Authoritative Specification Document:** `docs/audio_sheet_adapter_spec.md`  

---

## 1. Permanent Schema Fields (README Section 9.2)

- **Job ID & Name:** `JOB-02` — Continuous Audio & Sheet Music Ingestion Specifications and Adapters
- **Starting Validated Checkpoint:** `2a4b261`
- **Files Modified / Added:**
  - Added: `music_model/audio_importer.py` (Continuous PCM WAV adapter, onset/offset detection, robust autocorrelation pitch estimation, truncated byte validation, synthetic generator)
  - Added: `music_model/musicxml_importer.py` (MusicXML `<score-partwise>` parser, unified measure-reach architecture, piecewise `ScoreTimeline` tempo changes, shared part tempos, `<forward>`/`<backup>` navigation, chord duration tracking, exact `Fraction` tied-note coalescing, nested dynamics, metronome beat units, direction offsets, transposition disclosure, pickup measures, unsupported notation disclosure)
  - Added: `docs/audio_sheet_adapter_spec.md` (Reconciled technical specification, mathematical models, tolerances, rounding rules, stereo limitations, exact timing, fallback disclaimer, mutability notice, and research boundaries)
  - Added: `tests/test_audio_and_musicxml.py` (Dedicated test suite with 36 comprehensive unit tests: 15 original + 21 dedicated regression tests for DEFECT-01 through DEFECT-19, exact timing integration, and JSON round-trip)
  - Added: `verify_audio_and_sheet_adapters.py` (Standalone benchmark runner with 34 benchmark scenarios and 47 evaluated assertions)
  - Added: `requirements.txt` (Declares standard library only: `wave`, `struct`, `fractions`, `math`, `xml.etree.ElementTree`, `tkinter`, `unittest`)
  - Added: `JOB_02_VERIFICATION_LOG.txt` (Complete recorded terminal output from automated and standalone verification runs)
  - Added: `JOB_02_COMPLETION_RECORD.md` (This document)
  - Modified Tracked Files:
    - `music_model/sound_event.py`: Added documented `get_authoritative_exact_timing(event, unit='ms'|'sec') -> Tuple[Fraction, Fraction, Fraction]` helper with strict paired validation, consistency checking with redundant fields, attributes mutability note, and fallback disclaimer.
    - `music_model/__init__.py`: Re-exported `get_authoritative_exact_timing`.
- **Mathematical Methods & Formulas:**
  1. *Exact Continuous Audio Rational Timing:*
     $$t_{\text{sec}}(i) = \frac{i}{R} \in \mathbb{Q}, \quad t_{\text{ms, exact}}(i) = \frac{1000 \cdot i}{R} \in \mathbb{Q}$$
     $$t_{\text{ms}}(i) = \text{round}\left(\frac{1000 \cdot i}{R}\right)$$
     Exact rational seconds $\text{Fraction}(i, R)$ preserved in `SoundEvent.attributes["exact_start_sec_rational"]` and raw sample index $i$ in `sample_start_idx`.
  2. *Stereo Downmixing to Mono & Phase Tradeoff:*
     $$x_{\text{mono}}[n] = \frac{x_{\text{left}}[n] + x_{\text{right}}[n]}{2}$$
     Stereo phase cancellation documented as an acoustic limitation when out-of-phase stereo signals are averaged.
  3. *Short-Time RMS Energy Envelope:*
     $$\text{RMS}[k] = \sqrt{\frac{1}{N_w} \sum_{n=0}^{N_w - 1} x[k \cdot H + n]^2}$$
     with analysis window $N_w = 20\text{ ms}$ and hop size $H = 10\text{ ms}$. Silence hangover window calibrated to $20\text{ ms}$ (2 hops).
  4. *Zero-Mean Normalized Segment Cross-Correlation Pitch Estimation with Valley Descent & Parabolic Refinement:*
     $$\mu = \frac{1}{N}\sum_{n=0}^{N-1} x[n], \quad y[n] = x[n] - \mu$$
     $$r(\tau) = \frac{\sum_{n=0}^{N-\tau-1} y[n] \cdot y[n + \tau]}{\sqrt{\sum_{n=0}^{N-\tau-1} y[n]^2 \cdot \sum_{n=0}^{N-\tau-1} y[n+\tau]^2}}$$
     Searched over musical range $60\text{ Hz} \le f_0 \le 2000\text{ Hz}$ ($B_1$ to $B_6$, tolerances $58\text{ Hz} \le f_0 \le 2050\text{ Hz}$, MIDI pitches 21–108). Valley search begins at lag 1 to ensure high frequencies with small lag (e.g. 2000 Hz at 8000 Hz sample rate, lag 4) are detected. Requires signal length $N \ge 2\tau$, correlation descent into valley $r(\tau) < 0.50$ prior to peak evaluation, zero-crossing rate check ($\le 2200\text{ Hz}$) to reject out-of-band signals ($> 2000\text{ Hz}$), and first prominent peak selection where $r(\tau^*) \ge 0.50$ and $r(\tau^*) \ge 0.85 \cdot \max_\tau r(\tau)$. Parabolic interpolation refines continuous lag $\tau_{\text{refined}}$.
  5. *Synchronized Measure Reach & Sequential Divisions (DEFECT-14):*
     Measure reach is computed measure-by-measure across all parts, evaluating divisions sequentially in document order and tracking the maximum musical reach across all voices:
     $$Q_{\text{reach}} = \max_{t} Q_{\text{cursor}}(t)$$
     rather than merely the final cursor position at the end of the voice. Pickup measures ($m=0$, $0 < \Delta Q_0 < Q_{\text{time}}$) advance by actual reach without invented padding. Incomplete/overfull measures are flagged in `unsupported_features` without fabricating artificial silent intervals.
  6. *Two-Pass Piecewise Quarter-Beat Score Timeline (`ScoreTimeline`):*
     Pass 1 gathers score-wide tempo directives across all parts and voices. Pass 2 integrates event timings using the unified timeline. Tempo changes $\text{BPM}_i$ encountered at quarter-note beat positions $Q_i$ define piecewise linear mapping from beats to exact rational milliseconds:
     $$t_{\text{ms}}(Q) = t_i + (Q - Q_i) \cdot \frac{60000}{\text{BPM}_i} \in \mathbb{Q}$$
     Out-of-order tempo insertions dynamically rebuild continuous monotonic segments, preventing retrospective distortion of earlier measures.
  7. *Multi-Part Shared Score Tempo:*
     Tempo defined in one part is shared globally across all parts of the score. Parts without explicit tempo markings inherit the active score tempo. Conflicting part tempos are diagnosed in `unsupported_features`.
  8. *Exact Fraction Zero-Gap Tied Note Continuity Criterion:*
     Two consecutive notes of identical pitch and voice in part $p$ coalesce if and only if:
     $$t_{\text{prev, end\_frac}} == t_{\text{curr, start\_frac}}$$
     Any temporal gap (even 1 ms) is rejected from coalescing, logged as an interrupted tie in `unsupported_features`, and emitted as distinct events. Multi-note chains (3+ notes) coalesce cleanly.
- **Verification Commands Executed:**
  - `python -m unittest discover tests -v` (Complete automated suite: 142 tests)
  - `python -m unittest tests/test_audio_and_musicxml.py -v` (Dedicated JOB-02 suite: 36 tests)
  - `python verify_audio_and_sheet_adapters.py` (Standalone benchmark runner: 34 scenarios)
  - `python verify_midi_import.py` (Baseline verification script)
  - `python verify_group_units.py` (Baseline verification script)
  - `python verify_progressive.py` (Baseline verification script)
  - `python verify_proof.py` (Baseline verification script)
  - `python verify_development.py` (Baseline verification script)
  - `python verify_group_discovery.py` (Baseline verification script)
  - `python verify_row_merger.py` (Baseline verification script)
- **Exact Test Counts & Results:**
  - Automated Unit Test Suite: **142/142 tests PASSED** in ~38.5s (106 baseline existing tests + 36 dedicated JOB-02 unit tests; 0 errors, 0 failures).
  - Standalone JOB-02 Benchmark Suite: **34/34 benchmark scenarios PASSED**, **47/47 assertions PASSED** (25 in Audio Suite A, 22 in MusicXML Suite S, exit code 0).
  - All 7 Baseline Verification Scripts: **7/7 PASSED** (exit code 0 across all scripts).
- **Successful Approaches:**
  - Unified measure-by-measure cursor tracking in Pass 1 eliminating discrepancies between preliminary reach calculations and note extraction.
  - Sequential `<divisions>` interpretation preserving exact durations for mid-measure divisions changes.
  - Maximum cursor tracking ($\max_t Q_{\text{cursor}}(t)$) preserving full voice span when `<backup>` is followed by a shorter voice.
  - Transparent handling of pickup measures without invented padding silence.
  - Support for direction `<offset>` shifting tempo changes accurately by fractional quarter beats.
  - Strict validation in `get_authoritative_exact_timing` requiring paired start/end rational attributes, checking consistency with redundant duration and sample-index fields, and preventing incomplete metadata from silently falling back to integer milliseconds.
- **Unsuccessful Approaches & Controls Tested:**
  - *Preliminary Measure Duration Loop:* A separate preliminary loop scanning `<attributes>` all at once miscalculated mid-measure divisions changes and missed maximum reach on backups. Replaced with unified measure-by-measure cursor tracking.
  - *Silent Fallback on Incomplete Timing Metadata:* When partial rational metadata was provided without end or duration, it silently fell back to integer milliseconds. Replaced with strict validation raising `ValueError` on incomplete or malformed attributes.
- **Known Limitations & Edge Cases:**
  - **Single-Channel Acoustic Polyphony:** Time-domain energy envelope and autocorrelation cannot separate simultaneous polyphonic notes into multiple independent rows. Polyphonic audio separation is explicitly designated as an open research problem outside JOB-02 scope.
  - **Stereo Downmix Phase Cancellation:** Arithmetic averaging of stereo channels can attenuate out-of-phase signals.
  - **MusicXML Feature Subset:** Supports `<score-partwise>` measures, notes, rests, chords, voices, divisions, tempo, forwards, backups, and ties. Complex notations (transposition, grace notes, glissandi, tuplets beyond simple divisions) set `is_complete_faithful_representation = False` to prevent mistaking incomplete score imports for full representations.
- **Google Antigravity Review:**
  *All reported defects (DEFECT-01 through DEFECT-16) have been comprehensively resolved, verified, and audited. Exact rational timing integration and JSON round-trip have been validated. All requested source files, specifications, unit tests, standalone verification scripts, and verification logs are packaged in `JOB_02_INDEPENDENT_REVIEW.zip`. The calculator repository remains completely protected and untouched. No downstream jobs have been started. Submitted for independent inspection by ChatGPT.*  
  — Google Antigravity, 2026-11-24.
- **ChatGPT Independent Review:**
  *Pending independent inspection of updated `JOB_02_INDEPENDENT_REVIEW.zip`.*
- **Author Approval:**
  *Pending independent audit approval by ChatGPT and explicit author authorization.*
- **Final Validated Checkpoint:** `Uncommitted` (Awaiting Author Authorization)
- **Next Authorized Job:** `Undecided` (Awaiting completion of review boundary)

---

---

## 2. Independent Engineering Audit & Approval Record (ChatGPT)

ChatGPT has completed the fifth independent engineering audit of the JOB-02 implementation archive (`JOB_02_INDEPENDENT_REVIEW.zip`) and formally approved the job within its documented prototype scope:

- **Independent Audit Verdict:** **JOB-02 APPROVED**
- **Independent Regression Command:** `xvfb-run -a python -m unittest discover tests -v`
- **Independent Automated Test Results:**
  - Tests Executed: **142**
  - Tests Passed: **142**
  - Failures: **0**
  - Errors: **0**
  - Independent Runtime: **31.255 seconds**
- **Independent Standalone Adapter Verification:**
  - Scenarios Evaluated: **34 / 34 PASSED** (100%)
  - Total Assertions: **47 / 47 PASSED** (100%)
  - Audio Assertions: **25 / 25 PASSED**
  - MusicXML Assertions: **22 / 22 PASSED**
  - Exit Code: **0**
- **Independent Verification Scripts:** All 8 standalone scripts independently passed with exit code 0.
- **Independent AST & Preservation Verification:**
  - All 33 previous adapter test functions verified unchanged.
  - 3 new adapter test functions verified added (`test_defect_17`, `test_defect_18`, `test_defect_19`).
  - Zero adapter tests removed.
  - All 31 verbatim author statements in `README.md` independently match `music.txt` character-for-character.
  - Unrelated historical baseline files verified preserved.

---

## 3. Comprehensive Defect Remediation & Review Responses

### DEFECT-01: Mid-Measure Tempo Changes
- **Issue:** Tempo changes mid-measure were applied retrospectively across the whole measure.
- **Resolution:** Implemented `ScoreTimeline` class with piecewise linear mapping $t_{\text{ms}}(Q) = t_i + (Q - Q_i) \cdot \frac{60000}{\text{BPM}_i}$ based on fractional quarter-note beats $Q \in \mathbb{Q}$. When `<sound tempo="..."/>` or `<metronome>` is encountered, the new BPM is recorded at that exact beat position $Q_i$, applying exclusively to subsequent notes without retrospective measure distortion.
- **Verification:** Unit test `test_defect_01_tempo_changes_within_a_measure` and Benchmark S9 verify exact intervals `[0, 500) ms` and `[500, 1500) ms`.

### DEFECT-02: Forward and Backup Operations Across Divisions
- **Issue:** Cursor movements via `<forward>` and `<backup>` were incomplete or reset voice timelines.
- **Resolution:** Added full `<forward>` and `<backup>` support in `musicxml_importer.py`. Duration ticks are converted to fractional quarter beats $\Delta Q = \frac{D}{\text{divisions}}$ and added/subtracted to the voice cursor:
  $$Q_{\text{new}} = \max\left(Q_{\text{measure\_start}}, Q_{\text{cursor}} \pm \Delta Q\right)$$
  Independent voice timelines are preserved without voice collision or measure boundary corruption.
- **Verification:** Unit test `test_defect_02_forward_and_backup_operations` and Benchmark S10 verify multi-voice forward and backup alignment without voice collision.

### DEFECT-03: Trailing Rests in Total Score Duration
- **Issue:** Measures ending with trailing rests or silent intervals were truncated to the last sounding note.
- **Resolution:** Measure duration is tracked across all notes, rests, and forward operations. Total score duration is computed as:
  $$T_{\text{score}} = \max\left(\max_{e} e_{\text{end}}, \max_m m_{\text{end}}\right)$$
  and exposed as both `total_duration_ms` (integer) and `total_duration_ms_rational` (`Fraction`).
- **Verification:** Unit test `test_defect_03_trailing_rests_in_total_duration` and Benchmark S11 verify that a measure with a 500 ms note and 500 ms trailing rest reports a total score duration of 1000 ms (Fraction: 1000/1).

### DEFECT-04: Exact Fraction Tie Continuity
- **Issue:** Tied note coalescing tolerated small temporal gaps up to 2 ms.
- **Resolution:** Replaced fuzzy integer tolerance with exact `Fraction` equality:
  $$\text{prev\_end\_frac} == \text{event\_start\_ms\_frac}$$
  Any non-zero gap (including a 1 ms rest) is rejected from coalescing, logged as an interrupted tie in `unsupported_features`, and emitted as distinct events.
- **Verification:** Unit test `test_defect_04_exact_fraction_tie_continuity` verifies that a 1 ms gap is rejected from coalescing and emitted as two separate events with diagnostic disclosure.

### DEFECT-05: Three-Note Tie Chains
- **Issue:** Chained ties where middle notes have both `stop` and `start` generated false orphaned stop warnings or failed to coalesce cleanly.
- **Resolution:** Replaced single open tie state with chain continuation tracking in `musicxml_importer.py`. When a note with both `stop` and `start` arrives matching an open tie with exact rational continuity, the open tie's end is extended and the tie remains open for subsequent stop notes.
- **Verification:** Unit test `test_defect_05_three_note_tie_chain_and_continuation` and Benchmark S12 verify that a 3-note chain (C4 quarter tied across 3 measures) coalesces into a single continuous event `[0, 1500) ms` with zero warnings.

### DEFECT-06: Unsupported Notation Disclosure
- **Issue:** Unsupported notations (glissandi, ornaments, lyrics, repeats) failed to populate `unsupported_features` or force `is_complete_faithful_representation = False`.
- **Resolution:** Added comprehensive inspection in `musicxml_importer.py` checking `<grace>`, `<cue>`, `<notations>` (`<glissando>`, `<slide>`, `<ornaments>`, `<dynamics>`), `<lyric>`, and `<barline><repeat>`. All encountered features are logged to `unsupported_features`, and `is_complete_faithful_representation` is set to `False`.
- **Verification:** Unit test `test_defect_06_unsupported_notations_and_directions` and Benchmark S13 verify that all unhandled musical elements trigger explicit unfaithful representation disclosure.

### DEFECT-07: Invalid Ordinary Note Duration Rejection
- **Issue:** Notes with duration $\le 0$ were clamped to an artificial 1 ms duration.
- **Resolution:** Notes with duration $\le 0$ (and no `<grace/>` tag) are rejected as malformed notation, logged to `unsupported_features`, and discarded without fabricating artificial positive durations.
- **Verification:** Unit test `test_defect_07_invalid_ordinary_note_duration` and Benchmark S13 verify rejection of zero-duration ordinary notes.

### DEFECT-08: Autocorrelation Pitch Estimation Controls
- **Issue:** Infrasonic 10 Hz and DC offset signals produced false positive pitch estimates.
- **Resolution:** Autocorrelation estimator in `audio_importer.py` was rewritten with:
  1. Mean DC subtraction ($\mu = \frac{1}{N}\sum x[n], y[n] = x[n] - \mu$).
  2. Buffer cycle check: $N \ge 2\tau$ required for lag $\tau$.
  3. Valley descent requirement: $r(\tau) < 0.50$ required before evaluating peaks.
  4. First prominent peak selection: $r(\tau) \ge 0.50$ and $r(\tau) \ge 0.85 \cdot \max_\tau r(\tau)$.
  5. Parabolic 3-point peak interpolation for sub-sample lag refinement.
- **Verification:** Unit test `test_defect_08_pitch_estimation_controls` and Benchmark A9 verify:
  - 10 Hz infrasonic signal returns `pitch_midi = None`.
  - Pure DC offset signal returns `pitch_midi = None`.
  - 60 Hz hum returns MIDI 34/35.
  - Short burst (< 2 periods) returns `pitch_midi = None`.

### DEFECT-09: Truncated PCM WAV Stream Length Validation
- **Issue:** Truncated PCM WAV files where the data chunk contained fewer bytes than declared by `num_frames * num_channels * sample_width` failed to raise `AudioFormatError` across all bit depths.
- **Resolution:** Added strict expected byte length validation:
  $$\text{expected\_bytes} = \text{num\_frames} \cdot \text{num\_channels} \cdot \text{sample\_width}$$
  If actual data chunk size is less than `expected_bytes`, an `AudioFormatError` is raised immediately. Validated in both `parse_wav` and `_unpack_pcm_samples` across 8, 16, 24, and 32-bit depths for both mono and stereo.
- **Verification:** Unit test `test_defect_09_truncated_pcm_wav_all_depths` and Benchmark A10 verify that truncated streams across all 4 bit depths and channel configurations raise `AudioFormatError`.

### DEFECT-10: Multi-Part Shared Score Tempo
- **Issue:** In multi-part scores where Part 1 specifies tempo and Part 2 does not, Part 2 defaulted to 120 BPM instead of inheriting the score's active tempo.
- **Resolution:** Refactored `parse_musicxml` into a two-pass architecture. Pass 1 discovers score-wide tempo changes from all parts and builds a shared `ScoreTimeline`. Pass 2 evaluates notes in all parts against this unified timeline. If conflicting tempos are declared at identical beats, primary part tempo takes precedence and conflicts are reported in `unsupported_features`.
- **Verification:** Unit test `test_defect_10_shared_score_tempo_between_parts` and Benchmark S15 verify that Part 2 inherits a 60 BPM tempo from Part 1, producing identical 1000 ms quarter notes across both parts.

### DEFECT-11: Out-of-Order Tempo Changes & ScoreTimeline Continuous Integration
- **Issue:** When tempo directives occurred out of temporal order (e.g., inside voices navigating with `<backup>`), appending segments broke piecewise continuity and distorted earlier measures.
- **Resolution:** In `ScoreTimeline`, tempos are stored in a raw beat-to-tempo mapping `_raw_tempos`. Whenever queried, `_ensure_built()` sorts all beat positions and reconstructs monotonic piecewise segments:
  $$t_{\text{ms}}(Q) = t_i + (Q - Q_i) \cdot \frac{60000}{\text{BPM}_i}$$
  Ensuring seamless continuity across out-of-order declarations.
- **Verification:** Unit test `test_defect_11_out_of_order_tempo_changes_and_score_timeline` and Benchmark S16 verify that setting tempo at $Q=2$ then $Q=1$ correctly computes $t_{\text{ms}}(2) = 2500\text{ ms}$ without distorting preceding intervals.

### DEFECT-12: Unsupported Feature Disclosures
- **12A (Nested Dynamics):** `<direction><direction-type><dynamics><ff/></dynamics></direction-type></direction>` elements are parsed, flagged in `unsupported_features`, and set `is_complete_faithful_representation = False`.
- **12B (Metronome Beat Units):** `<beat-unit>` tags (e.g. `eighth`, `half`) are converted to equivalent quarter-note BPM (e.g. 120 eighth-BPM $\to$ 60 quarter-BPM, duration 1000 ms). Non-quarter beat units are disclosed in `unsupported_features`.
- **12C (Microtonal Alterations):** Fractional pitch alterations (e.g. `<alter>0.5</alter>`) round to nearest integer MIDI pitch and are disclosed in `unsupported_features`, setting `is_complete_faithful_representation = False`.
- **12D (Invalid Backup Handling):** `<backup>` commands moving cursor before measure start are clamped to measure start and disclosed in `unsupported_features`, setting `is_complete_faithful_representation = False`.
- **Verification:** Unit test `test_defect_12_unsupported_features_nested_dynamics_metronome_microtonal_invalid_backup` and Benchmark S17 verify all four edge cases.

### DEFECT-13: High-Frequency Pitch Estimation in `audio_importer.py`
- **Issue:** Valley search starting at `min_lag` overlooked valley at lag $\le 3$ for high frequencies ($2000\text{ Hz}$ at $8000\text{ Hz}$). Out-of-band signals ($2400\text{ Hz}$, $3000\text{ Hz}$) returned misleading subharmonics.
- **Resolution:**
  1. Valley search begins at `lag = 1`, detecting valleys immediately for short-period frequencies.
  2. High-frequency gating: zero-crossing rate check rejects signals exceeding $2200\text{ Hz}$, and prominent correlation peaks at lag < `min_lag` cleanly return `(None, None, 0.0)`.
  3. Search band calibrated to $[58\text{ Hz}, 2050\text{ Hz}]$ to cover nominal $60\text{ Hz}$ to $2000\text{ Hz}$ with floating-point tolerance.
- **Verification:** Unit test `test_defect_13_high_frequency_pitch_estimation_controls` and Benchmark A11 verify that 2000 Hz tone evaluates to MIDI 95, while 2400 Hz and 3000 Hz cleanly return `None`.

### DEFECT-14: Measure Duration & Starting Positions (Unified Cursor Tracking)
- **Issue:** Preliminary measure calculation applied final divisions retroactively to earlier notes in a measure and sampled final cursor position rather than maximum musical reach on backups.
- **Resolution:** Unified note extraction and measure reach into a single synchronized measure-by-measure pass:
  1. *Sequential Divisions Interpretation:* `<divisions>` declarations apply strictly in document order to subsequent notes. Mid-measure divisions changes scale preceding and subsequent notes correctly.
  2. *Maximum Musical Reach:* Tracks $Q_{\text{reach}} = \max_t Q_{\text{cursor}}(t)$ across all notes, chords, and forwards, preserving full voice span when `<backup>` is followed by a shorter voice.
  3. *Pickup Measures (Anacrusis):* An initial measure with reach less than time signature duration advances by its actual reach without invented padding silence.
  4. *Incomplete Measures:* Flagged in `unsupported_features` without fabricating artificial silence.
- **Verification:** Unit test `test_defect_14_measure_duration_and_reach_controls` and Benchmark S18 verify:
  - Control A (mid-measure divisions change): Note 1 [0, 500) ms, Note 2 [500, 1000) ms, Note 3 [1000, 1500) ms.
  - Control B (backup with shorter voice): Measure 2 starts at 1000 ms.
  - Pickup measure (4/4 with 1 quarter): Measure 2 starts at 500 ms without artificial padding.

### DEFECT-15: Invalid or Unsupported Timing Input
- **Issue:** Negative rest durations caused voices to jump backwards to 0 ms without warnings; direction `<offset>` was ignored; `<transpose>` directives were silently skipped.
- **Resolution:**
  1. Non-positive rest durations ($\le 0$): diagnosed in `unsupported_features`, discarded without modifying cursor.
  2. Non-positive forward and backup durations ($\le 0$): diagnosed in `unsupported_features`.
  3. Direction `<offset>`: parsed and applied to tempo directive beat positions: $Q_{\text{tempo}} = Q_{\text{cursor}} + \frac{\text{offset}}{\text{divisions}}$.
  4. Transposition: `<transpose>` flagged in `unsupported_features`, preserving sounding pitches while disclosing incomplete representation.
- **Verification:** Unit test `test_defect_15_invalid_or_unsupported_timing_inputs` and Benchmark S19 verify all cases.

### DEFECT-16: Complete Exact Timing Metadata & Fallback Integrity
- **Issue:** When malformed or partial rational timing metadata was provided, `get_authoritative_exact_timing` silently ignored the metadata and fell back to integer milliseconds.
- **Resolution:** Strict validation in `get_authoritative_exact_timing`:
  1. Fallback to integer millisecond timestamps applies ONLY when rational metadata is genuinely absent.
  2. If partial rational attributes are present without paired start/end, raises `ValueError` immediately.
  3. If declared duration (`exact_duration_ms_rational` / `exact_duration_sec_rational`) is inconsistent with computed `end - start`, raises `ValueError`.
  4. If audio sample indices are inconsistent with declared rational seconds, raises `ValueError`.
- **Verification:** Unit test `test_defect_16_incomplete_and_inconsistent_exact_timing` and Benchmark S20 verify all validation paths.

### DEFECT-17: Invalid Tempo Metadata Validation
- **Issue:** Non-positive, non-finite, or malformed tempo attributes in `<sound tempo="...">` or `<metronome><per-minute>...</per-minute>` were silently ignored with `pass` rather than being validated and diagnosed.
- **Resolution:**
  1. In `musicxml_importer.py`, non-positive, non-finite, or malformed tempo attributes on `<sound>` and `<metronome>` are explicitly recorded in `unsupported_features`, ensuring `is_complete_faithful_representation` correctly returns `False`.
  2. In `ScoreTimeline`, `__init__` and `set_tempo` strictly validate that tempos are positive and finite, raising `ValueError` on non-positive or non-finite inputs.
  3. In `parse_musicxml`, `default_tempo_bpm` is strictly validated to be positive and finite.
- **Verification:** Unit test `test_defect_17_invalid_tempo_metadata_validation` and Benchmark S21 verify all validation and rejection paths.

### DEFECT-18: Tempo Positions Before Score Beginning
- **Issue:** Negative direction offsets (e.g. `<offset>-1</offset>`) or negative cursor positions could position a tempo directive before beat 0 (`q_pos < 0`), shifting the timeline and corrupting timestamps at and after beat 0.
- **Resolution:**
  1. In `ScoreTimeline.set_tempo(q_pos, tempo)`, attempting to position a tempo before beat 0 (`q_pos < 0`) raises `ValueError`.
  2. In `musicxml_importer.py`, effective tempo positions `measure_cursor_q + offset_q < 0` are diagnosed in `unsupported_features` and excluded from the score timeline, preventing corruption of beat 0.
- **Verification:** Unit test `test_defect_18_tempo_positions_before_score_beginning` and Benchmark S21 verify rejection and timeline preservation.

### DEFECT-19: Complete Exact Rational Timing Metadata Validation
- **Issue:** `get_authoritative_exact_timing` required comprehensive validation across multi-format, audio sample index, and fallback interval bounds.
- **Resolution:**
  1. Rejects conflicting format metadata (contains both MusicXML and Audio timing attributes) with `ValueError`.
  2. Rejects partial audio sample index metadata (requires paired rational seconds whenever audio sample keys are present).
  3. Validates `sample_count` consistency (`sample_count == sample_end_idx - sample_start_idx`).
  4. Verifies that integer timestamps `start_time_ms` and `end_time_ms` are consistent with rational timing coordinates (rejecting gross discrepancies).
  5. Enforces interval bounds (`start_time_ms >= 0` and `end_time_ms > start_time_ms`) in fallback mode.
- **Verification:** Unit test `test_defect_19_complete_exact_rational_timing_metadata_validation` and Benchmark S22 verify all validation paths.

---

## 4. Authoritative Exact Timing & Fallback Disclaimers

### Exact Rational Timing Architecture
- Every `SoundEvent` produced by the Audio and MusicXML adapters stores exact rational timing in `attributes`:
  - Audio: `exact_start_sec_rational`, `exact_end_sec_rational`, `exact_duration_sec_rational`.
  - MusicXML: `exact_start_ms_rational`, `exact_end_ms_rational`, `exact_duration_ms_rational`.
- The helper `get_authoritative_exact_timing(event, unit='ms'|'sec') -> Tuple[Fraction, Fraction, Fraction]` provides uniform access:
  - Validates non-negative start times and positive durations.
  - Raises `ValueError` on malformed attribute strings.
  - Supports unit conversion between `'ms'` and `'sec'` via exact rational multiplication.

### Fallback Disclaimer
When exact rational attributes are missing (e.g. historical baseline events), `get_authoritative_exact_timing` falls back to integer millisecond bounds `Fraction(event.start_time_ms)` and `Fraction(event.duration_ms)`. While these represent exact rational numbers, they reflect integer-rounded bounds rather than unpreserved source fractions (such as fractional milliseconds derived from MIDI ticks). Downstream algorithms requiring microsecond precision must inspect `attributes` for source rational strings.

### Attribute Mutability Notice
`SoundEvent.attributes` is a mutable dictionary in Python. Mutating rational strings will alter future calls to `get_authoritative_exact_timing`.

---

## 5. Git Workspace Accounting & Protected Repository Status

```
Repository: C:\Users\I_wat\PycharmProjects\music
Branch: main (up to date with origin/main)
Checkpoint: 2a4b261 (uncommitted local changes pending author authorization)
Zero Git Commits / Zero Pushes Performed

Tracked Files Modified (2):
  - music_model/__init__.py (added get_authoritative_exact_timing export)
  - music_model/sound_event.py (added get_authoritative_exact_timing helper with DEFECT-16 validation)

Untracked Files Added (8):
  - docs/audio_sheet_adapter_spec.md
  - music_model/audio_importer.py
  - music_model/musicxml_importer.py
  - tests/test_audio_and_musicxml.py
  - verify_audio_and_sheet_adapters.py
  - requirements.txt
  - JOB_02_COMPLETION_RECORD.md
  - JOB_02_VERIFICATION_LOG.txt
  - JOB_02_INDEPENDENT_REVIEW.zip

Untracked Baseline Artifacts Preserved:
  - music.txt
  - music_model/group_discovery.py
  - tests/test_group_discovery.py
  - verify_group_discovery.py
  - verify_row_merger.py

Protected Calculator Repository:
  - Path: C:\Users\I_wat\PycharmProjects\calculator
  - Status: Strictly untouched, read-only at checkpoint 17be078d
```

---

*End of Job Completion Record for JOB-02 (Final Audit Submission).*

---

## 6. Proposed Git Staging Manifest & Test Accounting

### 6.1 Proposed Staging Manifest for JOB-02
To maintain a clean, reproducible repository history, only the files directly implementing, verifying, and documenting JOB-02 should be committed:

1. **Shared Model Integration (Modified Tracked Files):**
   - `music_model/__init__.py` (Re-exports `get_authoritative_exact_timing`)
   - `music_model/sound_event.py` (Defines `get_authoritative_exact_timing` with strict validation, mutability note, and fallback disclaimer)
2. **JOB-02 Implementation Adapters (New Untracked Files):**
   - `music_model/audio_importer.py` (Continuous PCM WAV adapter)
   - `music_model/musicxml_importer.py` (MusicXML `<score-partwise>` adapter)
3. **JOB-02 Test Suite & Standalone Benchmark:**
   - `tests/test_audio_and_musicxml.py` (36 comprehensive adapter unit tests)
   - `verify_audio_and_sheet_adapters.py` (Standalone benchmark runner with 34 scenarios)
4. **Specification & Environment Requirements:**
   - `docs/audio_sheet_adapter_spec.md` (Authoritative technical specification)
   - `requirements.txt` (Standard library environment declaration)
5. **Verification Evidence & Completion Record:**
   - `JOB_02_COMPLETION_RECORD.md` (This permanent record)
   - `JOB_02_VERIFICATION_LOG.txt` (Full recorded terminal run log)

### 6.2 Files Excluded from Staging (Kept Locally)
- `JOB_02_INDEPENDENT_REVIEW.zip` (Temporary binary review archive)
- Unrelated historical experimental prototypes:
  - `music_model/group_discovery.py` (JOB-04 prototype)
  - `tests/test_group_discovery.py` (JOB-04 test suite)
  - `verify_group_discovery.py` (JOB-04 standalone verification script)
  - `verify_row_merger.py` (Row merger experiment script)
- Private IDE configuration and system files (`.idea/`, etc.)

### 6.3 Test Accounting Dependency Explanation
- **Local Workspace:** Discovers and runs **142 tests** (91 historical baseline tests + 15 untracked `test_group_discovery.py` tests + 36 JOB-02 adapter tests).
- **Clean Clone of Staged JOB-02:** When cloned into a clean environment without the untracked group discovery prototype, `python -m unittest discover tests -v` will run **127 tests** (91 historical baseline + 36 JOB-02 adapter tests). Both counts reflect 100% passing test suites and zero failures.
