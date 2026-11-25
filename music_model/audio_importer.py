"""Audio ingestion adapter and candidate onset/offset discovery.

This module implements a prototype adapter for uncompressed PCM WAV audio,
converting continuous audio recordings into discrete SoundEvent intervals
within the music project's architecture.

Design Principles:
- Preserves raw audio samples, sample rate, and exact sample indices.
- Converts sample indices to milliseconds using exact rational arithmetic (Fraction).
- Exact rational coordinates (sample index / sample rate) are preserved in
  SoundEvent attributes alongside integer millisecond interval boundaries.
- Signal processing methods (energy envelope, thresholding, autocorrelation pitch)
  are documented as candidate exploratory approaches, not definitive musical truths.
- Autocorrelation pitch estimation removes DC offset, requires a descent into a valley
  before accepting a periodic local peak, and validates sufficient cycles in the buffer.
- Robustly rejects malformed, compressed, or truncated audio formats with AudioFormatError.
- Authoritative exact rational timing is accessible via get_authoritative_exact_timing().
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from music_model.sound_event import SoundEvent, get_authoritative_exact_timing


class AudioFormatError(ValueError):
    """Raised when an audio file cannot be parsed or uses an unsupported format."""


@dataclass(frozen=True)
class AudioProperties:
    """Metadata describing the PCM audio format."""

    sample_rate: int
    num_channels: int
    sample_width_bytes: int
    num_frames: int

    @property
    def duration_seconds(self) -> Fraction:
        """Exact duration in seconds as a rational fraction."""
        if self.sample_rate <= 0:
            return Fraction(0, 1)
        return Fraction(self.num_frames, self.sample_rate)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return float(self.duration_seconds * 1000)


@dataclass
class AudioData:
    """Uncompressed PCM audio data with normalized floating-point samples [-1.0, 1.0]."""

    properties: AudioProperties
    samples: List[float]  # Mono or downmixed normalized samples [-1.0, 1.0]
    raw_frames: bytes = field(repr=False)

    @property
    def sample_rate(self) -> int:
        return self.properties.sample_rate

    @property
    def num_frames(self) -> int:
        return self.properties.num_frames

    def sample_to_exact_sec_fraction(self, sample_idx: int) -> Fraction:
        """Convert a sample index to exact rational seconds."""
        if self.properties.sample_rate <= 0:
            return Fraction(0, 1)
        return Fraction(sample_idx, self.properties.sample_rate)

    def sample_to_exact_ms_fraction(self, sample_idx: int) -> Fraction:
        """Convert a sample index to exact rational milliseconds."""
        return self.sample_to_exact_sec_fraction(sample_idx) * 1000

    def sample_to_ms(self, sample_idx: int) -> int:
        """Convert a sample index to integer milliseconds using Python's round() ties-to-even behavior."""
        rational_ms = self.sample_to_exact_ms_fraction(sample_idx)
        return int(round(float(rational_ms)))


@dataclass(frozen=True)
class AudioOnsetCandidate:
    """A discovered candidate sound interval within raw audio."""

    start_sample: int
    end_sample: int
    start_ms: int
    end_ms: int
    start_sec_fraction: Fraction
    end_sec_fraction: Fraction
    peak_amplitude: float
    rms_energy: float
    estimated_pitch_hz: Optional[float] = None
    estimated_midi_pitch: Optional[int] = None
    confidence: float = 1.0


def parse_wav(source: Union[str, bytes, BinaryIO]) -> AudioData:
    """Parse an uncompressed PCM WAV file or byte stream into AudioData.

    Args:
        source: File path (str), byte buffer (bytes), or file-like object (BinaryIO).

    Returns:
        AudioData containing parsed samples and format properties.

    Raises:
        AudioFormatError: If the WAV is corrupt, non-PCM, truncated, or uses unsupported parameters.
    """
    file_obj: BinaryIO
    if isinstance(source, str):
        try:
            file_obj = open(source, "rb")
        except OSError as exc:
            raise AudioFormatError(f"Failed to open audio file {source}: {exc}") from exc
    elif isinstance(source, bytes):
        file_obj = io.BytesIO(source)
    else:
        file_obj = source

    try:
        with wave.open(file_obj, "rb") as wav_file:
            num_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            num_frames = wav_file.getnframes()
            comptype = wav_file.getcomptype()

            if comptype != "NONE":
                raise AudioFormatError(
                    f"Unsupported compressed WAV type: {comptype}. Only uncompressed PCM is supported."
                )
            if num_channels not in (1, 2):
                raise AudioFormatError(
                    f"Unsupported channel count: {num_channels}. Only mono (1) and stereo (2) are supported."
                )
            if sample_width not in (1, 2, 3, 4):
                raise AudioFormatError(
                    f"Unsupported sample width: {sample_width} bytes ({sample_width * 8} bits)."
                )
            if sample_rate <= 0:
                raise AudioFormatError(f"Invalid sample rate: {sample_rate} Hz.")

            expected_bytes = num_frames * num_channels * sample_width
            raw_frames = wav_file.readframes(num_frames)

            # Validate frame length against expected raw byte count (DEFECT-09)
            if len(raw_frames) < expected_bytes:
                raise AudioFormatError(
                    f"Truncated WAV stream: header declares {num_frames} frames "
                    f"({expected_bytes} bytes for {num_channels}ch, {sample_width}B/sample), "
                    f"but only {len(raw_frames)} bytes were available."
                )

    except (wave.Error, EOFError, struct.error) as exc:
        raise AudioFormatError(f"Corrupt or invalid WAV header/stream: {exc}") from exc
    finally:
        if isinstance(source, str):
            file_obj.close()

    # Unpack raw PCM bytes into normalized float samples [-1.0, 1.0]
    samples = _unpack_pcm_samples(raw_frames, num_channels, sample_width, num_frames)

    props = AudioProperties(
        sample_rate=sample_rate,
        num_channels=num_channels,
        sample_width_bytes=sample_width,
        num_frames=num_frames,
    )
    return AudioData(properties=props, samples=samples, raw_frames=raw_frames)


def _unpack_pcm_samples(
    raw_frames: bytes, num_channels: int, sample_width: int, num_frames: int
) -> List[float]:
    """Unpack raw PCM frames to mono-downmixed normalized float samples [-1.0, 1.0]."""
    expected_bytes = num_frames * num_channels * sample_width
    if len(raw_frames) < expected_bytes:
        raise AudioFormatError(
            f"Truncated PCM sample buffer: expected {expected_bytes} bytes for {num_frames} frames, "
            f"received {len(raw_frames)} bytes."
        )

    total_samples = num_frames * num_channels
    mono_samples: List[float] = [0.0] * num_frames

    if sample_width == 1:
        # 8-bit unsigned PCM: values 0..255, midpoint at 128
        raw_vals = struct.unpack(f"{total_samples}B", raw_frames[:total_samples])
        if num_channels == 1:
            for i in range(num_frames):
                mono_samples[i] = (raw_vals[i] - 128) / 128.0
        else:
            for i in range(num_frames):
                left = (raw_vals[i * 2] - 128) / 128.0
                right = (raw_vals[i * 2 + 1] - 128) / 128.0
                mono_samples[i] = (left + right) * 0.5

    elif sample_width == 2:
        # 16-bit signed PCM: values -32768..32767
        raw_vals = struct.unpack(f"<{total_samples}h", raw_frames[: total_samples * 2])
        if num_channels == 1:
            for i in range(num_frames):
                mono_samples[i] = raw_vals[i] / 32768.0
        else:
            for i in range(num_frames):
                left = raw_vals[i * 2] / 32768.0
                right = raw_vals[i * 2 + 1] / 32768.0
                mono_samples[i] = (left + right) * 0.5

    elif sample_width == 3:
        # 24-bit signed PCM: 3 bytes per sample, little-endian
        step = 3 * num_channels
        for i in range(num_frames):
            offset = i * step
            b = raw_frames[offset : offset + 3]
            val = int.from_bytes(b, byteorder="little", signed=True)
            left = val / 8388608.0
            if num_channels == 2:
                b_r = raw_frames[offset + 3 : offset + 6]
                val_r = int.from_bytes(b_r, byteorder="little", signed=True)
                right = val_r / 8388608.0
                mono_samples[i] = (left + right) * 0.5
            else:
                mono_samples[i] = left

    elif sample_width == 4:
        # 32-bit signed PCM
        raw_vals = struct.unpack(f"<{total_samples}i", raw_frames[: total_samples * 4])
        if num_channels == 1:
            for i in range(num_frames):
                mono_samples[i] = raw_vals[i] / 2147483648.0
        else:
            for i in range(num_frames):
                left = raw_vals[i * 2] / 2147483648.0
                right = raw_vals[i * 2 + 1] / 2147483648.0
                mono_samples[i] = (left + right) * 0.5

    return mono_samples


class AudioOnsetDetector:
    """Candidate onset/offset discovery engine using short-term RMS energy and peak tracking.

    Predefined Theoretical Tolerance:
    - Hop size: default 10 ms.
    - Window size: default 20 ms.
    - Analysis frame resolution limit: +/- hop_size_ms (typically +/- 10 ms).
    - Predefined acceptance tolerance against continuous ground truth: delta <= window_size_ms (20 ms).
    - Silence hangover: default 20 ms (2 hop frames) to avoid boundary chatter.
    """

    def __init__(
        self,
        window_size_ms: float = 20.0,
        hop_size_ms: float = 10.0,
        energy_threshold: float = 0.05,
        min_event_duration_ms: float = 30.0,
        min_silence_duration_ms: float = 20.0,
    ) -> None:
        self.window_size_ms = window_size_ms
        self.hop_size_ms = hop_size_ms
        self.energy_threshold = energy_threshold
        self.min_event_duration_ms = min_event_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms

    def detect_candidates(self, audio: AudioData) -> List[AudioOnsetCandidate]:
        """Detect continuous sound intervals above the candidate energy threshold."""
        sample_rate = audio.sample_rate
        samples = audio.samples
        total_samples = len(samples)

        if total_samples == 0 or sample_rate <= 0:
            return []

        window_samples = max(1, int(round(self.window_size_ms * sample_rate / 1000.0)))
        hop_samples = max(1, int(round(self.hop_size_ms * sample_rate / 1000.0)))
        min_event_samples = int(round(self.min_event_duration_ms * sample_rate / 1000.0))
        min_silence_samples = int(round(self.min_silence_duration_ms * sample_rate / 1000.0))

        num_frames = (total_samples - window_samples) // hop_samples + 1
        if num_frames <= 0:
            return []

        frame_rms: List[float] = []
        for f in range(num_frames):
            start = f * hop_samples
            chunk = samples[start : start + window_samples]
            sq_sum = sum(x * x for x in chunk)
            rms = math.sqrt(sq_sum / len(chunk))
            frame_rms.append(rms)

        max_rms = max(frame_rms) if frame_rms else 0.0
        if max_rms <= 1e-9:
            return []

        active_threshold = max(self.energy_threshold, max_rms * self.energy_threshold)

        intervals: List[Tuple[int, int]] = []
        in_sound = False
        onset_frame = 0
        silence_count = 0
        silence_frame_threshold = max(1, int(round(min_silence_samples / hop_samples)))

        for f, rms in enumerate(frame_rms):
            if not in_sound:
                if rms >= active_threshold:
                    in_sound = True
                    onset_frame = f
                    silence_count = 0
            else:
                if rms < active_threshold:
                    silence_count += 1
                    if silence_count >= silence_frame_threshold or f == num_frames - 1:
                        offset_frame = f - silence_count
                        start_sample = onset_frame * hop_samples
                        end_sample = min(total_samples, (offset_frame * hop_samples) + window_samples)
                        if (end_sample - start_sample) >= min_event_samples:
                            intervals.append((start_sample, end_sample))
                        in_sound = False
                        silence_count = 0
                else:
                    silence_count = 0

        if in_sound:
            start_sample = onset_frame * hop_samples
            end_sample = total_samples
            if (end_sample - start_sample) >= min_event_samples:
                intervals.append((start_sample, end_sample))

        candidates: List[AudioOnsetCandidate] = []
        for start_s, end_s in intervals:
            start_ms = audio.sample_to_ms(start_s)
            end_ms = audio.sample_to_ms(end_s)
            start_sec_frac = audio.sample_to_exact_sec_fraction(start_s)
            end_sec_frac = audio.sample_to_exact_sec_fraction(end_s)

            if end_ms <= start_ms:
                end_ms = start_ms + 1

            chunk = samples[start_s:end_s]
            peak = max(abs(x) for x in chunk) if chunk else 0.0
            rms = math.sqrt(sum(x * x for x in chunk) / len(chunk)) if chunk else 0.0

            pitch_hz, midi_pitch, pitch_conf = _estimate_pitch_autocorrelation(chunk, sample_rate)

            candidates.append(
                AudioOnsetCandidate(
                    start_sample=start_s,
                    end_sample=end_s,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    start_sec_fraction=start_sec_frac,
                    end_sec_fraction=end_sec_frac,
                    peak_amplitude=peak,
                    rms_energy=rms,
                    estimated_pitch_hz=pitch_hz,
                    estimated_midi_pitch=midi_pitch,
                    confidence=pitch_conf if midi_pitch is not None else min(1.0, peak / (max_rms + 1e-9)),
                )
            )

        return candidates


def _estimate_pitch_autocorrelation(
    samples: List[float], sample_rate: int
) -> Tuple[Optional[float], Optional[int], float]:
    r"""Candidate pitch estimation via normalized autocorrelation over musical pitch range (C2-C7).

    Mathematical Formulation (Reconciled):
    Computes zero-mean normalized cross-correlation across overlapping window segments:
        r(\tau) = \frac{\sum_{n=0}^{N-\tau-1} y[n] \cdot y[n + \tau]}{\sqrt{\sum_{n=0}^{N-\tau-1} y[n]^2 \cdot \sum_{n=0}^{N-\tau-1} y[n+\tau]^2}}
    where y[n] = x[n] - \mu is the centered discrete signal.

    Robust Controls (DEFECT-08 & DEFECT-13):
    - DC offset removal (zero-mean centering). Pure DC signals yield zero AC energy and return None.
    - Out-of-band high frequency detection: signals with zero-crossing rate exceeding 2200 Hz
      or prominent correlation peaks at lag < min_lag (above 2000 Hz) are rejected cleanly as out-of-band.
    - Valley detection across [1, max_lag]: requires correlation to descend into a valley (r < 0.50)
      before candidate peaks are accepted, preventing monotonic decay of out-of-band infrasonic signals (10 Hz).
    - True local peak picking in [min_lag, max_lag]: requires corr[lag] > corr[lag-1] and corr[lag] >= corr[lag+1].
    - First prominent peak selection: selects the fundamental period within 85% of global peak correlation.
    - Parabolic interpolation around the peak for sub-sample lag refinement.
    - Sufficient cycle check: requires at least 2 full cycles in the analysis buffer (n >= 2 * lag).
    - Validated musical pitch range: [60 Hz, 2000 Hz] corresponding to MIDI pitches 21-108.

    Returns:
        (estimated_frequency_hz, estimated_midi_pitch, confidence) or (None, None, 0.0).
        Unknown, unpitched, ambiguous, or out-of-band signals return None.
    """
    if len(samples) < 64 or sample_rate <= 0:
        return None, None, 0.0

    n = len(samples)

    # 1. DC Removal (Zero-mean centering)
    mean_val = sum(samples) / n
    centered = [x - mean_val for x in samples]

    # Total energy check
    total_energy = sum(x * x for x in centered)
    if total_energy <= 1e-9:
        # Constant DC or silent signal has zero AC energy
        return None, None, 0.0

    # Quick zero-crossing rate check to reject out-of-band high frequencies (> 2200 Hz)
    zc_count = sum(1 for i in range(1, n) if (centered[i] >= 0) != (centered[i - 1] >= 0))
    approx_freq_zcr = (zc_count / (2.0 * (n - 1))) * sample_rate
    if approx_freq_zcr > 2200.0:
        return None, None, 0.0

    # Musical pitch search band: ~58 Hz to 2050 Hz (covering 60 Hz to 2000 Hz nominal musical pitch)
    min_lag = max(2, int(round(sample_rate / 2050.0)))
    max_lag = min(n // 2, int(round(sample_rate / 58.0)))

    if min_lag >= max_lag:
        return None, None, 0.0

    # 2. Compute normalized autocorrelation for lags from 1 up to max_lag + 1
    corr = [0.0] * (max_lag + 2)
    for lag in range(1, max_lag + 2):
        if lag >= n:
            break
        dot = sum(centered[i] * centered[i + lag] for i in range(n - lag))
        e1 = sum(centered[i] * centered[i] for i in range(n - lag))
        e2 = sum(centered[i + lag] * centered[i + lag] for i in range(n - lag))
        denom = math.sqrt(e1 * e2)
        corr[lag] = dot / denom if denom > 1e-9 else 0.0

    # 3. Valley Detection starting from lag 1 (DEFECT-13)
    found_valley = False
    valley_threshold = 0.50
    min_val_seen = 1.0

    # Check for prominent peak below min_lag indicating out-of-band fundamental (> 2000 Hz)
    for lag in range(1, min_lag):
        if corr[lag] < min_val_seen:
            min_val_seen = corr[lag]
        if min_val_seen <= valley_threshold:
            found_valley = True
        if found_valley and corr[lag] > corr[lag - 1] and corr[lag] >= corr[lag + 1] and corr[lag] >= 0.60:
            # Out-of-band high frequency signal (> 2000 Hz)
            return None, None, 0.0

    peaks: List[Tuple[float, float]] = []

    for lag in range(min_lag, max_lag + 1):
        c = corr[lag]
        if c < min_val_seen:
            min_val_seen = c
        if min_val_seen <= valley_threshold:
            found_valley = True

        if found_valley and corr[lag] > corr[lag - 1] and corr[lag] >= corr[lag + 1]:
            if corr[lag] >= 0.50 and n >= 2 * lag:
                # Refine lag using parabolic interpolation
                y0 = corr[lag - 1]
                y1 = corr[lag]
                y2 = corr[lag + 1]
                denom_p = 2 * (y0 - 2 * y1 + y2)
                delta = (y0 - y2) / denom_p if abs(denom_p) > 1e-9 else 0.0
                delta = max(-0.5, min(0.5, delta))
                refined_lag = lag + delta
                peaks.append((refined_lag, y1))

    if not peaks:
        return None, None, 0.0

    # 4. Pick First Prominent Peak (Fundamental Frequency)
    max_c = max(p[1] for p in peaks)
    chosen_lag: Optional[float] = None
    chosen_corr = 0.0

    for r_lag, c_val in peaks:
        if c_val >= 0.85 * max_c and c_val >= 0.50:
            chosen_lag = r_lag
            chosen_corr = c_val
            break

    if chosen_lag is not None and chosen_corr >= 0.50:
        freq_hz = sample_rate / chosen_lag
        if 58.0 <= freq_hz <= 2050.0:
            midi_pitch = int(round(69.0 + 12.0 * math.log2(freq_hz / 440.0)))
            if 21 <= midi_pitch <= 108:
                return round(freq_hz, 2), midi_pitch, round(chosen_corr, 4)

    return None, None, 0.0


def import_audio_to_sound_events(
    source: Union[str, bytes, BinaryIO],
    row_id: str = "row_audio",
    detector: Optional[AudioOnsetDetector] = None,
    sound_ref: Optional[str] = None,
) -> List[SoundEvent]:
    """Ingest a PCM WAV audio source into validated SoundEvent instances."""
    audio = parse_wav(source)
    if detector is None:
        detector = AudioOnsetDetector()

    candidates = detector.detect_candidates(audio)
    events: List[SoundEvent] = []

    ref_str = sound_ref or (source if isinstance(source, str) else "audio_buffer")

    for idx, c in enumerate(candidates, start=1):
        event_id = f"{row_id}_evt_{idx:04d}"
        attrs: Dict[str, Any] = {
            "source_type": "audio_wav",
            "boundary_type": "detected_acoustic_candidate",
            "sample_rate": audio.sample_rate,
            "sample_start_idx": c.start_sample,
            "sample_end_idx": c.end_sample,
            "sample_count": c.end_sample - c.start_sample,
            "exact_start_sec_rational": str(c.start_sec_fraction),
            "exact_end_sec_rational": str(c.end_sec_fraction),
            "exact_duration_sec_rational": str(c.end_sec_fraction - c.start_sec_fraction),
            "peak_amplitude": round(c.peak_amplitude, 4),
            "rms_energy": round(c.rms_energy, 4),
            "confidence": round(c.confidence, 4),
            "pitch_detected": c.estimated_midi_pitch is not None,
        }
        if c.estimated_midi_pitch is not None:
            attrs["pitch_midi"] = c.estimated_midi_pitch
            attrs["frequency_hz"] = c.estimated_pitch_hz
        else:
            attrs["pitch_midi"] = None
            attrs["frequency_hz"] = None

        event = SoundEvent(
            event_id=event_id,
            row_id=row_id,
            start_time_ms=c.start_ms,
            end_time_ms=c.end_ms,
            label=f"Audio Segment {idx}" + (f" (MIDI {c.estimated_midi_pitch})" if c.estimated_midi_pitch else " (Unpitched/Ambiguous)"),
            sound_ref=ref_str,
            attributes=attrs,
            height=float(c.estimated_midi_pitch) if c.estimated_midi_pitch is not None else None,
        )
        events.append(event)

    return events


def generate_synthetic_wav(
    sample_rate: int = 44100,
    channels: int = 1,
    sample_width: int = 2,
    events: Optional[List[Tuple[int, int, float, float]]] = None,
    noise_bursts: Optional[List[Tuple[int, int, float]]] = None,
    total_duration_ms: int = 1000,
) -> bytes:
    """Generate in-memory PCM WAV bytes containing synthetic sine-wave tone bursts or white noise."""
    if events is None:
        events = [(100, 300, 440.0, 0.8)]
    if noise_bursts is None:
        noise_bursts = []

    num_frames = int(round(total_duration_ms * sample_rate / 1000.0))
    buffer = [0.0] * num_frames

    for start_ms, dur_ms, freq, amp in events:
        start_f = int(round(start_ms * sample_rate / 1000.0))
        dur_f = int(round(dur_ms * sample_rate / 1000.0))
        end_f = min(num_frames, start_f + dur_f)
        for f in range(start_f, end_f):
            t = (f - start_f) / float(sample_rate)
            buffer[f] += amp * math.sin(2.0 * math.pi * freq * t)

    # Add deterministic white noise bursts if specified
    rng = random.Random(42)
    for start_ms, dur_ms, amp in noise_bursts:
        start_f = int(round(start_ms * sample_rate / 1000.0))
        dur_f = int(round(dur_ms * sample_rate / 1000.0))
        end_f = min(num_frames, start_f + dur_f)
        for f in range(start_f, end_f):
            buffer[f] += amp * (rng.random() * 2.0 - 1.0)

    # Clamp buffer to [-1.0, 1.0]
    for i in range(num_frames):
        buffer[i] = max(-1.0, min(1.0, buffer[i]))

    out = io.BytesIO()
    with wave.open(out, "wb") as wav_out:
        wav_out.setnchannels(channels)
        wav_out.setsampwidth(sample_width)
        wav_out.setframerate(sample_rate)
        wav_out.setnframes(num_frames)

        raw_frames = bytearray()
        if sample_width == 1:
            for s in buffer:
                byte_val = max(0, min(255, int(round(s * 127.0 + 128.0))))
                for _ in range(channels):
                    raw_frames.append(byte_val)
        elif sample_width == 2:
            for s in buffer:
                int_val = max(-32768, min(32767, int(round(s * 32767.0))))
                packed = struct.pack("<h", int_val)
                for _ in range(channels):
                    raw_frames.extend(packed)
        elif sample_width == 3:
            for s in buffer:
                int_val = max(-8388608, min(8388607, int(round(s * 8388607.0))))
                packed = int_val.to_bytes(3, byteorder="little", signed=True)
                for _ in range(channels):
                    raw_frames.extend(packed)
        elif sample_width == 4:
            for s in buffer:
                int_val = max(-2147483648, min(2147483647, int(round(s * 2147483647.0))))
                packed = struct.pack("<i", int_val)
                for _ in range(channels):
                    raw_frames.extend(packed)

        wav_out.writeframes(bytes(raw_frames))

    return out.getvalue()
