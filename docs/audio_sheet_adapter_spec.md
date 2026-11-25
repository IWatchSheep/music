# Music Project — Continuous Audio & Sheet Music Ingestion Specification (JOB-02)

> **Document Status:** Technical research specification and adapter architecture for JOB-02.  
> **Repository:** `IWatchSheep/music`  
> **Authoritative Documentation Baseline:** `2a4b261`  
> **Historical Implementation Baseline:** `ad3a9d3`  
> **Protected Calculator Repository:** `17be078d` (unmodified, 100% read-only)

---

## 1. Executive Summary & Objective

This specification documents the architecture, data representations, mathematical formulas, and prototype adapter interfaces for ingesting:
1. **Continuous Recorded Audio:** Uncompressed linear PCM WAV streams (`music_model/audio_importer.py`).
2. **Digital Sheet Music:** MusicXML `<score-partwise>` documents (`music_model/musicxml_importer.py`).

### Architectural Scope and Boundaries
- **Production Status:** Standard MIDI (`music_model/midi_importer.py`) and reproducible JSON (`music_model/passage_format.py`) remain the authoritative production input formats for the project.
- **Experimental Status:** Audio and MusicXML adapters are experimental prototypes. They investigate how acoustic recordings and symbolic scores map into the project's non-destructive `SoundEvent` representation.
- **No Premature Assumptions:** Synthetic onset detection does not claim to solve general polyphonic music transcription. Silence in an audio track is not asserted as proof of biological breathing. Notated sheet-music timing is strictly distinguished from expressive human performance timing.

---

## 2. Audio Ingestion Architecture (`music_model/audio_importer.py`)

### 2.1 Supported Audio Formats & Preconditions
The prototype audio adapter targets standard uncompressed linear Pulse-Code Modulation (PCM) RIFF WAV files:
- **Encoding:** Uncompressed PCM (`WAVE_FORMAT_PCM`, `comptype == 'NONE'`).
- **Bit Depths:** 8-bit unsigned PCM, 16-bit signed PCM (standard CD quality), 24-bit signed PCM, and 32-bit signed PCM. Strict stream length validation checks that data chunk size equals `num_frames * num_channels * sample_width`. Truncated or corrupted streams raise `AudioFormatError` (DEFECT-09).
- **Channel Configurations:** 1 channel (Mono) and 2 channels (Stereo). Stereo audio is downmixed to mono for energy analysis via arithmetic average:
  $$x_{\text{mono}}[n] = \frac{x_{\text{left}}[n] + x_{\text{right}}[n]}{2}$$
  *Known Limitation / Tradeoff:* Downmixing stereo to mono by arithmetic average can cause partial or complete phase cancellation for signals with out-of-phase stereo components. Downstream production audio systems should analyze channels independently or apply energy-preserving spatial transforms.
- **Sample Rates:** Any positive sample rate $R > 0\text{ Hz}$ (e.g., $16000\text{ Hz}$, $22050\text{ Hz}$, $44100\text{ Hz}$, $48000\text{ Hz}$).
- **Unsupported Formats (Clean Rejection):** Lossy compressed audio (MP3, AAC, OGG), ADPCM, IEEE Float WAV, and corrupted RIFF headers raise `AudioFormatError` immediately.

### 2.2 Mathematical Formulas & Exact Timing Preservation
Let $R$ be the sample rate in Hz (samples per second), and $i$ be the zero-based discrete sample index ($0 \le i < N_{\text{total}}$).

1. **Exact Rational Time Coordinates:**
   The continuous timestamp in seconds is an exact rational fraction:
   $$t_{\text{sec}}(i) = \frac{i}{R} \in \mathbb{Q}, \quad t_{\text{ms, exact}}(i) = \frac{1000 \cdot i}{R} \in \mathbb{Q}$$
   To satisfy the integer millisecond contract of the historical `SoundEvent` class (`start_time_ms`, `end_time_ms`), interval boundaries are converted via Python's standard `round()` function:
   $$t_{\text{ms}}(i) = \text{round}\left(\frac{1000 \cdot i}{R}\right)$$
   *Rounding Specification:* Python's `round()` uses round-half-to-even (banker's rounding). For exact half-integers (e.g., 0.5, 1.5), values round to the nearest even integer.

2. **Permanent Rational Preservation in Attributes:**
   To guarantee that rounding does not destroy source precision, every `SoundEvent` preserves exact rational coordinates and raw sample bounds in its `attributes` dictionary:
   - `sample_start_idx`: Exact starting sample index $i_{\text{start}}$.
   - `sample_end_idx`: Exact ending sample index $i_{\text{end}}$.
   - `exact_start_sec_rational`: String representation of $\text{Fraction}(i_{\text{start}}, R)$.
   - `exact_end_sec_rational`: String representation of $\text{Fraction}(i_{\text{end}}, R)$.
   - `exact_duration_sec_rational`: String representation of $\text{Fraction}(i_{\text{end}} - i_{\text{start}}, R)$.
   - `boundary_type`: `"detected_acoustic_candidate"`.
   Subsequent mathematical models can perform calculations using these exact rational coordinates without accumulated rounding error.

3. **Short-Time RMS Energy Envelope:**
   For analysis window $N_w$ (default $20\text{ ms}$, $N_w = \text{round}(0.020 \cdot R)$) and hop size $H$ (default $10\text{ ms}$, $H = \text{round}(0.010 \cdot R)$):
   $$\text{RMS}[k] = \sqrt{\frac{1}{N_w} \sum_{n=0}^{N_w - 1} x[k \cdot H + n]^2}$$

4. **Candidate Onset/Offset Discovery & Predefined Tolerances:**
   - **Theoretical Resolution Limit:** Because analysis frames advance by hop size $H = 10\text{ ms}$ with window size $N_w = 20\text{ ms}$, the theoretical temporal resolution boundary is bounded by $N_w = 20\text{ ms}$.
   - **Predefined Acceptance Tolerance:** Any continuous onset or offset falling within an analysis frame is accepted if measured error $\Delta t \le 20\text{ ms}$.
   - **Observed Benchmark Error:** For non-window-aligned signals (e.g., an onset at 123 ms), discrete windowing introduces discretization shifts of up to 17 ms, which remains strictly within the $\le 20\text{ ms}$ acceptance tolerance.
   - **Hangover Window:** Offset detection requires energy to remain below threshold for $T_{\text{silence}} \ge 20\text{ ms}$ (2 consecutive hops) to prevent spurious boundary chatter while avoiding excessive trailing overhang.

5. **Robust Candidate Pitch Estimation (Normalized Autocorrelation):**
   Fundamental frequency $f_0$ is estimated via zero-mean normalized segment cross-correlation across overlapping windows:
   $$\mu = \frac{1}{N}\sum_{n=0}^{N-1} x[n], \quad y[n] = x[n] - \mu$$
   $$r(\tau) = \frac{\sum_{n=0}^{N-\tau-1} y[n] \cdot y[n + \tau]}{\sqrt{\sum_{n=0}^{N-\tau-1} y[n]^2 \cdot \sum_{n=0}^{N-\tau-1} y[n+\tau]^2}}$$
   - **DC Removal & AC Energy Check:** Pure DC signals or silent buffers yield AC energy $\le 10^{-9}$ and return `(None, None, 0.0)` cleanly.
   - **Out-of-Band High-Frequency Rejection (DEFECT-13):** High frequencies with zero-crossing rate $> 2200\text{ Hz}$ or correlation peaks below `min_lag` ($> 2000\text{ Hz}$) cleanly return `None` rather than generating spurious subharmonics.
   - **Musical Pitch Band & Search Range:** Nominal search range $60\text{ Hz} \le f_0 \le 2000\text{ Hz}$ with boundary tolerances ($58\text{ Hz} \le f_0 \le 2050\text{ Hz}$, corresponding to MIDI pitches 21–108).
   - **Valley Descent Requirement:** Valley search begins at $\text{lag} = 1$ to ensure high frequencies with very small periods ($2000\text{ Hz}$ at $8000\text{ Hz}$ sample rate, period $\approx 4$ samples) are detected. Correlation must descend into a valley ($r(\tau) < 0.50$) before any candidate peak is accepted, rejecting monotonic infrasonic signals (10 Hz).
   - **First Prominent Peak Selection:** Selects the fundamental period satisfying $r(\tau) \ge 0.50$ and $r(\tau) \ge 0.85 \cdot \max_{\tau} r(\tau)$.
   - **Parabolic Interpolation:** 3-point parabolic peak interpolation refines discrete lag $\tau^*$:
     $$\Delta \tau = \frac{r(\tau^* - 1) - r(\tau^* + 1)}{2(r(\tau^* - 1) - 2r(\tau^*) + r(\tau^* + 1))}, \quad \tau_{\text{refined}} = \tau^* + \Delta \tau, \quad f_0 = \frac{R}{\tau_{\text{refined}}}$$
   - **Buffer Sufficiency Check:** Requires at least 2 full cycles in the analysis buffer ($N \ge 2\tau$); shorter buffers return `None`.

---

## 3. Digital Sheet Music Architecture (`music_model/musicxml_importer.py`)

### 3.1 Supported MusicXML Subset & Piecewise Score Timeline
The prototype sheet-music adapter targets standard MusicXML `<score-partwise>` documents:
- **Synchronized Measure Reach & Starting Positions (DEFECT-14):**
  Measure durations and synchronized starting positions are computed measure-by-measure across all score parts using identical, unified cursor tracking:
  - *Sequential Divisions Interpretation:* `<divisions>` declarations apply sequentially in document order within a measure. A mid-measure divisions change (e.g., from 1 to 2) correctly scales preceding notes by 1 and subsequent notes by 2 without retroactively distorting earlier notes in the measure.
  - *Maximum Musical Reach:* Measure reach is the maximum musical cursor position reached across all voices, forwards, chords, and notes:
    $$Q_{\text{reach}} = \max_{t} Q_{\text{cursor}}(t)$$
    rather than merely the final cursor position at the end of the voice. A voice backed up to accommodate a shorter second voice preserves the full reach of the longer voice, preventing subsequent measures from overlapping preceding notes.
  - *Pickup Measures (Anacrusis):* An incomplete initial measure ($m=0$ or measure number "0") with reach $0 < \Delta Q_0 < Q_{\text{time}}$ is treated as an authentic pickup measure. Its duration is strictly $\Delta Q_0$, advancing directly to measure 1 without inventing artificial padding silence.
  - *Incomplete / Overfull Measures:* When a measure in the middle of a piece ($m > 0$) has reach $\Delta Q_m \ne Q_{\text{time}}$, the anomaly is flagged in `unsupported_features`, setting `is_complete_faithful_representation = False`. The measure's duration is strictly its actual musical reach $\Delta Q_m$, ensuring no artificial silence is invented or fabricated.
- **Two-Pass Architecture & ScoreTimeline Rebuilding (DEFECT-11):**
  1. *Pass 1 (Score-Wide Timeline & Measure Extraction):* Gathers notes, directions, forwards, backups, and tempo directives measure-by-measure across all parts.
  2. *Pass 2 (Integration & Coalescing):* Rebuilds continuous integrated timestamps via `ScoreTimeline`:
     $$t_{\text{ms}}(Q) = t_{i} + (Q - Q_i) \cdot \frac{60000}{\text{BPM}_i} \in \mathbb{Q}$$
     Out-of-order tempo insertions dynamically rebuild continuous monotonic segments, preventing retrospective distortion of earlier measures.
- **Multi-Part Shared Score Tempo (DEFECT-10):**
  Tempo definitions established in one part are shared across all score parts. Parts lacking local tempo markings inherit the score's active tempo timeline. If conflicting tempos are specified at the identical beat position across different parts, the primary part tempo governs and conflicting tempo declarations are diagnosed in `unsupported_features`.
- **Direction Offsets, Transposition & Invalid Input Handling (DEFECT-15):**
  - *Direction `<offset>`:* When `<direction>` contains `<offset>D</offset>`, the tempo directive applies at $Q_{\text{cursor}} + \frac{D}{\text{divisions}}$, accurately shifting the tempo change forward or backward in score time.
  - *Transposition Notation:* Transposition directives (`<transpose><chromatic>...</chromatic></transpose>`) are disclosed in `unsupported_features`, setting `is_complete_faithful_representation = False` while preserving sounding pitches.
  - *Non-Positive Rests/Forwards/Backups:* Rests, forward, or backup elements with duration $\le 0$ are diagnosed in `unsupported_features` and discarded without corrupting voice cursors or moving cursors backwards.
- **Exact Fraction Zero-Gap Continuity for Ties:**
  Tied notes require exact mathematical continuity:
  $$t_{\text{prev, end\_frac}} == t_{\text{curr, start\_frac}}$$
  Any temporal gap is rejected from coalescing, flagged as an interrupted tie in `unsupported_features`, and emitted as distinct events.
- **Chained Multi-Note Ties:**
  Three or more tied notes coalesce into a single continuous `SoundEvent`, preserving origin metadata.
- **Unsupported Feature Disclosure (DEFECT-12):**
  - *Nested Dynamics (12A):* `<direction><direction-type><dynamics><ff/></dynamics></direction-type></direction>` elements are parsed, flagged in `unsupported_features`, and set `is_complete_faithful_representation = False`.
  - *Metronome Beat Units (12B):* `<beat-unit>` tags (e.g., `eighth`, `half`) are converted to equivalent quarter-note BPM (e.g., 120 eighth-BPM $\to$ 60 quarter-BPM). Non-quarter beat units are disclosed in `unsupported_features`.
  - *Microtonal Alterations (12C):* Fractional pitch alterations (e.g. `<alter>0.5</alter>`) round to nearest integer MIDI pitch and are disclosed in `unsupported_features`, setting `is_complete_faithful_representation = False`.
  - *Invalid Backups:* `<backup>` moving before measure start is clamped to measure start and disclosed in `unsupported_features`.
  - *Grace, Cue, Ornaments, Lyrics:* Recorded in `unsupported_features`.

### 3.2 Exact Rational Timing Preservation & Strict Integrity (DEFECT-16)
1. **Division to Millisecond Conversion:**
   Given tempo $\text{BPM}$ and divisions per quarter note $\text{div}$:
   $$\Delta t_{\text{ms}} = D \cdot \frac{60000}{\text{BPM} \cdot \text{div}} \in \mathbb{Q}$$
   Durations are accumulated using `fractions.Fraction` across all measures, ensuring zero cumulative drift.
2. **Permanent Preservation in Attributes:**
   Every `SoundEvent` carries:
   - `exact_start_ms_rational`: String of $\text{Fraction}$.
   - `exact_end_ms_rational`: String of $\text{Fraction}$.
   - `exact_duration_ms_rational`: String of $\text{Fraction}$.
   - `is_complete_faithful_representation`: Boolean flag ensuring downstream callers do not mistake incomplete scores for complete representations.
3. **Authoritative Exact Timing Helper & Validation (DEFECT-16):**
   The function `get_authoritative_exact_timing(event, unit='ms'|'sec') -> Tuple[Fraction, Fraction, Fraction]` retrieves exact rational `(start, end, duration)` from attributes:
   - *Strict Paired Validation:* MusicXML requires paired `exact_start_ms_rational` and `exact_end_ms_rational`. Audio requires paired `exact_start_sec_rational` and `exact_end_sec_rational`. Partial, unpaired, or malformed metadata raises `ValueError` immediately.
   - *Consistency Checking:* If redundant duration (`exact_duration_ms_rational` / `exact_duration_sec_rational`) is supplied, it must equal `end - start`. If audio sample indices are supplied, they must be consistent with declared rational seconds: $\frac{\text{sample\_start\_idx}}{\text{sample\_rate}} == \text{start\_sec}$.
   - *Fallback Contract:* Fallback to integer millisecond bounds applies ONLY when authoritative rational metadata is genuinely absent. It reflects integer bounds rather than unpreserved source fractions.
   - *Attribute Mutability:* In Python, `SoundEvent.attributes` is a mutable dictionary. Modifying rational strings directly will change downstream calculations.

---

## 4. Integration with SoundEvent Architecture

| Field | Source from Audio Importer | Source from MusicXML Importer |
|---|---|---|
| `event_id` | `{row_id}_evt_{idx:04d}` | `{row_id}_evt_{idx:04d}` |
| `row_id` | `row_audio` (or user-specified) | `row_xml_p{part}_v{voice}` |
| `start_time_ms` | Rounded integer ms | Rounded integer ms |
| `end_time_ms` | Rounded integer ms | Rounded integer ms |
| `label` | `Audio Segment {idx}` | `{step}{alter}{octave} (m.{measure})` |
| `sound_ref` | File path or audio buffer name | `xml_measure_{measure_number}` |
| `height` | Pitch MIDI (if detected) or `None` | Pitch MIDI (integer) |
| `attributes` | `source_type`: "audio_wav"<br>`sample_rate`: int<br>`sample_start_idx`: int<br>`sample_end_idx`: int<br>`exact_start_sec_rational`: str<br>`exact_end_sec_rational`: str<br>`exact_duration_sec_rational`: str<br>`boundary_type`: "detected_acoustic_candidate"<br>`peak_amplitude`: float<br>`rms_energy`: float<br>`confidence`: float<br>`pitch_detected`: bool | `source_type`: "musicxml"<br>`pitch_midi`: int<br>`pitch_step`: str<br>`pitch_octave`: int<br>`pitch_alter`: int<br>`measure_number`: int<br>`voice`: int<br>`is_tied`: bool<br>`exact_start_ms_rational`: str<br>`exact_end_ms_rational`: str<br>`exact_duration_ms_rational`: str<br>`is_complete_faithful_representation`: bool |

---

## 5. Experimental Uncertainties & Research Boundaries

1. **Audio Polyphony:**
   *I guess short-term RMS energy envelope tracking is suitable for solo melodic gestures, but separating multi-instrument polyphony into distinct temporary rows will require multi-band spectral decomposition in future research.*
2. **Score Time vs. Expressive Performance Time:**
   MusicXML represents symbolic, nominal score time. Authentic musical performance includes continuous human expressive variations (rubato). The sheet-music adapter preserves score time faithfully, leaving performance timing to empirical investigation.
3. **Acoustic Pauses vs. Biological Respiration:**
   *I guess breath pauses in singing and acoustic gaps in instruments indicate phrase boundaries, but an acoustic silent gap alone cannot be claimed to prove human biological breathing.*
