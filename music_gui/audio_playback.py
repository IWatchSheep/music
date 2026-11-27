"""Real-time audio playback, timeline transport synchronization, and audio synthesis.

Pure Python standard library implementation:
- wave, struct, math, time for audio synthesis and timing
- ctypes for Windows MCI multimedia audio output (winmm.dll)
- Zero external third-party dependencies

Threading model (JOB-03 consolidated refactor)
----------------------------------------------
There is NO background playback thread.  Periodic transport updates are driven by an
injected ``Scheduler``:

- ``TkScheduler`` runs updates through Tkinter ``after()`` on the GUI thread.
- ``ManualScheduler`` runs updates only when a test explicitly advances it.

A ``PlaybackTransport`` belongs to the thread that created it.  Every lifecycle
operation (load, play, pause, resume, stop, seek, reset, step_tick, close) must be
called on that thread.  The Windows MCI backend records the thread that opened the
device and refuses to send any MCI command from another thread, because MCI string
aliases are thread-affine (reproduced: MCI error 263 from a worker thread).

Components:
1. AudioBackend:
   - WindowsMciAudioBackend: Real-time standard-library MCI playback of PCM WAV audio.
   - SimulatedAudioBackend: Controllable virtual device with simulated startup delay,
     buffer latency, and clock-rate deviation for deterministic testing.
   - NullAudioBackend: Safe fallback when no audio device is available.
2. Scheduler: TkScheduler (GUI) and ManualScheduler (deterministic tests).
3. TransportSnapshot: immutable, coherent published transport state.
4. PlaybackTransport: authoritative transport and synchronization controller.
"""

from __future__ import annotations

import ctypes
import io
import itertools
import logging
import math
import os
import struct
import tempfile
import threading
import time
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from fractions import Fraction
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple, Union

from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent, get_authoritative_exact_timing

_log = logging.getLogger(__name__)


class TransportState(Enum):
    """Lifecycle states of the playback transport."""
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    ERROR = auto()


class AudioBackendStatus(Enum):
    """Operational status of the audio device backend."""
    UNAVAILABLE = auto()
    AVAILABLE = auto()
    FAILED = auto()
    SIMULATED = auto()
    DRIVER_PLAYING = auto()  # Successful driver execution of audio output
    PAUSED = auto()
    STOPPED = auto()

    # Backward compatibility alias
    GENUINELY_PLAYING = DRIVER_PLAYING


class AudioBackendError(RuntimeError):
    """Raised when an audio backend encounters an unrecoverable device or format error."""
    pass


class MciThreadOwnershipError(AudioBackendError):
    """Raised (before reaching MCI) when an MCI command is issued from a non-owner thread.

    The device itself is unaffected, so backend status is never changed by this refusal.
    """
    pass


class TransportThreadError(RuntimeError):
    """Raised when a transport lifecycle operation is called from a non-owner thread."""
    pass


class TransportClosedError(RuntimeError):
    """Raised when a lifecycle operation is attempted on a closed transport."""
    pass


class Clock(ABC):
    """Abstract time source interface."""

    @abstractmethod
    def now_seconds(self) -> float:
        """Return the current time in seconds."""
        pass


class RealClock(Clock):
    """Production time source backed by high-resolution system performance counter."""

    def now_seconds(self) -> float:
        return time.perf_counter()


class TestClock(Clock):
    """Deterministic, controllable virtual time source for automated unit tests."""

    def __init__(self, start_seconds: float = 0.0) -> None:
        self._current_time = float(start_seconds)

    def now_seconds(self) -> float:
        return self._current_time

    def advance(self, delta_seconds: float) -> None:
        """Advance the virtual clock by delta_seconds."""
        if not math.isfinite(delta_seconds) or delta_seconds < 0:
            raise ValueError(f"Clock delta must be a non-negative finite number: {delta_seconds}")
        self._current_time += delta_seconds

    def advance_ms(self, delta_ms: float) -> None:
        """Advance the virtual clock by delta_ms milliseconds."""
        self.advance(delta_ms / 1000.0)

    def set_time(self, time_seconds: float) -> None:
        """Set the absolute virtual clock time."""
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError(f"Clock time must be a non-negative finite number: {time_seconds}")
        self._current_time = float(time_seconds)


# -----------------------------------------------------------------------------
# Schedulers
# -----------------------------------------------------------------------------


class Scheduler(ABC):
    """Single-thread deferred-callback scheduler injected into PlaybackTransport.

    Callbacks run on the scheduler's own thread (the Tk thread for TkScheduler, the
    caller of advance()/run_due() for ManualScheduler).  The transport keeps at most one
    pending handle and invalidates it with a generation token on every relevant
    lifecycle transition, so a callback that has already been dequeued by the event
    loop still cannot act on a stopped, closed or superseded transport.
    """

    @abstractmethod
    def call_later(self, delay_ms: float, callback: Callable[[], None]) -> Any:
        """Schedule callback after delay_ms and return an opaque cancellation handle."""

    @abstractmethod
    def cancel(self, handle: Any) -> None:
        """Cancel a pending callback.  Cancelling an expired handle is harmless."""


@dataclass(eq=False)
class _ManualEntry:
    due_ms: float
    seq: int
    callback: Callable[[], None]
    cancelled: bool = False


class ManualScheduler(Scheduler):
    """Deterministic scheduler: callbacks run only when explicitly advanced.

    If a TestClock is supplied, advance() moves that clock to each callback's due time
    before running it, so scheduled transport updates observe exactly the virtual time
    at which they were due.
    """

    def __init__(self, clock: Optional[TestClock] = None) -> None:
        self._clock = clock
        self._now_ms: float = clock.now_seconds() * 1000.0 if clock is not None else 0.0
        self._entries: List[_ManualEntry] = []
        self._seq = itertools.count()
        self.executed_count: int = 0
        self.scheduled_count: int = 0
        self.cancelled_count: int = 0

    def _current_ms(self) -> float:
        return self._clock.now_seconds() * 1000.0 if self._clock is not None else self._now_ms

    def _set_current_ms(self, value_ms: float) -> None:
        if self._clock is not None:
            if value_ms / 1000.0 > self._clock.now_seconds():
                self._clock.set_time(value_ms / 1000.0)
        else:
            self._now_ms = max(self._now_ms, value_ms)

    def call_later(self, delay_ms: float, callback: Callable[[], None]) -> _ManualEntry:
        entry = _ManualEntry(self._current_ms() + max(0.0, float(delay_ms)), next(self._seq), callback)
        self._entries.append(entry)
        self.scheduled_count += 1
        return entry

    def cancel(self, handle: Any) -> None:
        if isinstance(handle, _ManualEntry) and handle in self._entries:
            self._entries.remove(handle)
            handle.cancelled = True
            self.cancelled_count += 1

    @property
    def pending_count(self) -> int:
        return len(self._entries)

    def _pop_next_due(self, limit_ms: float) -> Optional[_ManualEntry]:
        due = [e for e in self._entries if e.due_ms <= limit_ms + 1e-9]
        if not due:
            return None
        nxt = min(due, key=lambda e: (e.due_ms, e.seq))
        self._entries.remove(nxt)
        return nxt

    def _run(self, entry: _ManualEntry) -> None:
        self.executed_count += 1
        entry.callback()

    def run_due(self, max_callbacks: int = 100000) -> int:
        """Run every callback already due at the current time.  Returns the count run."""
        ran = 0
        while ran < max_callbacks:
            entry = self._pop_next_due(self._current_ms())
            if entry is None:
                break
            self._run(entry)
            ran += 1
        return ran

    def advance(self, delta_ms: float, max_callbacks: int = 100000) -> int:
        """Advance time by delta_ms, running each callback at its due time, in order."""
        if not math.isfinite(delta_ms) or delta_ms < 0:
            raise ValueError(f"Scheduler advance must be a non-negative finite number: {delta_ms}")
        target = self._current_ms() + delta_ms
        ran = 0
        while ran < max_callbacks:
            entry = self._pop_next_due(target)
            if entry is None:
                break
            self._set_current_ms(entry.due_ms)
            self._run(entry)
            ran += 1
        self._set_current_ms(target)
        return ran


class TkScheduler(Scheduler):
    """Scheduler backed by Tkinter ``after()``; callbacks run on the Tk GUI thread."""

    def __init__(self, widget: Any) -> None:
        self._widget = widget
        self._owner_thread_id = threading.get_ident()

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            raise TransportThreadError("TkScheduler used from a thread other than the Tk thread that created it.")

    def call_later(self, delay_ms: float, callback: Callable[[], None]) -> Any:
        self._check_thread()
        return self._widget.after(max(0, int(round(delay_ms))), callback)

    def cancel(self, handle: Any) -> None:
        self._check_thread()
        try:
            self._widget.after_cancel(handle)
        except Exception as ex:  # Widget already destroyed: its event queue cannot run the callback.
            _log.debug("TkScheduler.cancel ignored after widget teardown: %r", ex)


# -----------------------------------------------------------------------------
# Device observation and backends
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceObservation:
    """One acknowledged reading of the audio device.

    position_ms: device position, or None if the device cannot report one.
    mode: device-reported mode string ('playing', 'paused', 'stopped', ...) or None
          when the backend has no independent mode report (simulated/null backends).
    end_of_media: the device stopped by itself at the end of its media.
    unexpected_stop: the device stopped by itself before the end of its media.
    """
    position_ms: Optional[float]
    mode: Optional[str] = None
    end_of_media: bool = False
    unexpected_stop: bool = False


class AudioBackend(ABC):
    """Abstract interface for audio playback devices and sinks."""

    @abstractmethod
    def load_wav_bytes(self, wav_bytes: bytes) -> None:
        """Load PCM WAV audio data into the backend."""
        pass

    @abstractmethod
    def play(self, start_ms: float = 0.0, loop: bool = False) -> None:
        """Begin audio playback from start_ms."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause audio playback."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume audio playback from paused position."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio playback and reset device position."""
        pass

    @abstractmethod
    def get_device_position_ms(self) -> Optional[float]:
        """Query physical hardware or simulated device playback position in milliseconds."""
        pass

    def observe(self) -> DeviceObservation:
        """Return one device observation (exactly one position query).

        Backends without an independent device mode report only the position.
        WindowsMciAudioBackend overrides this to report the acknowledged MCI mode and
        end-of-media evidence.
        """
        return DeviceObservation(position_ms=self.get_device_position_ms())

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if an audio device is available and functional."""
        pass

    @abstractmethod
    def is_genuinely_audible(self) -> bool:
        """Return True if audio is routed to a physical audible output transducer."""
        pass

    @abstractmethod
    def get_status(self) -> AudioBackendStatus:
        """Return current status of backend."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload audio and release backend resources."""
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Return True if backend is actively playing audio."""
        pass

    @property
    @abstractmethod
    def is_paused(self) -> bool:
        """Return True if backend has an existing paused playback session that can be resumed."""
        pass

    @property
    def can_resume(self) -> bool:
        """Return True if backend has an active paused session that can be resumed via resume()."""
        return self.is_paused


class SimulatedAudioBackend(AudioBackend):
    """Deterministic simulated audio device with configurable timing controls."""

    def __init__(
        self,
        startup_delay_ms: float = 0.0,
        buffer_latency_ms: float = 0.0,
        device_clock_rate: float = 1.0,
        clock: Optional[Clock] = None,
    ) -> None:
        self.startup_delay_ms: float = max(0.0, float(startup_delay_ms))
        self.buffer_latency_ms: float = max(0.0, float(buffer_latency_ms))
        self.device_clock_rate: float = max(0.01, float(device_clock_rate))
        self._clock: Clock = clock or RealClock()

        self.loaded_bytes: Optional[bytes] = None
        self.inject_failure: bool = False
        self._status: AudioBackendStatus = AudioBackendStatus.AVAILABLE

        self._is_playing: bool = False
        self._is_paused: bool = False
        self.loop: bool = False

        self._start_time_sec: float = 0.0
        self._start_pos_ms: float = 0.0
        self._current_pos_ms: float = 0.0
        self.playback_log: List[Tuple[str, float]] = []

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @is_playing.setter
    def is_playing(self, val: bool) -> None:
        self._is_playing = bool(val)

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @is_paused.setter
    def is_paused(self, val: bool) -> None:
        self._is_paused = bool(val)

    def set_clock(self, clock: Clock) -> None:
        self._clock = clock

    def load_wav_bytes(self, wav_bytes: bytes) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during load_wav_bytes")
        self.loaded_bytes = wav_bytes
        self.playback_log.append(("load", float(len(wav_bytes))))

    def play(self, start_ms: float = 0.0, loop: bool = False) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during play")
        self.is_playing = True
        self.is_paused = False
        self._is_resumed = False
        self._status = AudioBackendStatus.SIMULATED
        self._start_pos_ms = max(0.0, float(start_ms))
        self._current_pos_ms = self._start_pos_ms
        self._start_time_sec = self._clock.now_seconds()
        self.loop = loop
        self.playback_log.append(("play", self._start_pos_ms))

    def pause(self) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during pause")
        if self.is_playing:
            self._current_pos_ms = self.get_device_position_ms() or self._current_pos_ms
            self.is_playing = False
            self.is_paused = True
            self._status = AudioBackendStatus.PAUSED
            self.playback_log.append(("pause", self._current_pos_ms))

    def resume(self) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during resume")
        if not self.is_paused:
            raise AudioBackendError("Cannot resume: audio backend is not in a paused state.")
        self.is_playing = True
        self.is_paused = False
        self._is_resumed = True
        self._status = AudioBackendStatus.SIMULATED
        self._start_pos_ms = self._current_pos_ms
        self._start_time_sec = self._clock.now_seconds()
        self.playback_log.append(("resume", self._current_pos_ms))

    def stop(self) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during stop")
        self.is_playing = False
        self.is_paused = False
        self._is_resumed = False
        self._status = AudioBackendStatus.STOPPED
        self._current_pos_ms = 0.0
        self.playback_log.append(("stop", 0.0))

    def seek(self, pos_ms: float) -> None:
        if self.inject_failure:
            self._status = AudioBackendStatus.FAILED
            self.is_playing = False
            raise AudioBackendError("Injected failure during seek")
        self._start_pos_ms = max(0.0, float(pos_ms))
        self._current_pos_ms = self._start_pos_ms
        self._start_time_sec = self._clock.now_seconds()
        if not self.is_playing:
            self.is_paused = False
        self.playback_log.append(("seek", self._start_pos_ms))

    def get_device_position_ms(self) -> Optional[float]:
        if not self.is_playing:
            return self._current_pos_ms

        elapsed_sec = (self._clock.now_seconds() - self._start_time_sec) * self.device_clock_rate
        delay = 0.0 if getattr(self, "_is_resumed", False) else self.startup_delay_ms
        elapsed_ms = round(elapsed_sec * 1000.0 - delay, 6)
        if elapsed_ms < 0:
            return self._start_pos_ms
        return self._start_pos_ms + elapsed_ms

    def is_available(self) -> bool:
        return True

    def is_genuinely_audible(self) -> bool:
        return False

    def get_status(self) -> AudioBackendStatus:
        return self._status

    def unload(self) -> None:
        self.stop()
        self.loaded_bytes = None


class NullAudioBackend(AudioBackend):
    """Silent null sink used when audio output hardware is unavailable or disabled."""

    def __init__(self) -> None:
        self._status: AudioBackendStatus = AudioBackendStatus.UNAVAILABLE

    @property
    def is_playing(self) -> bool:
        return False

    @property
    def is_paused(self) -> bool:
        return False

    def load_wav_bytes(self, wav_bytes: bytes) -> None:
        pass

    def play(self, start_ms: float = 0.0, loop: bool = False) -> None:
        pass

    def pause(self) -> None:
        pass

    def resume(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_device_position_ms(self) -> Optional[float]:
        return None

    def is_available(self) -> bool:
        return False

    def is_genuinely_audible(self) -> bool:
        return False

    def get_status(self) -> AudioBackendStatus:
        return self._status

    def unload(self) -> None:
        pass



# Tolerance (integer device milliseconds) for classifying an uncommanded MCI stop as a
# natural end of media.  Real waveaudio devices were observed to stop at exactly
# `status length` (diag_mci_real.py: 1000/1000 and 500/500); one millisecond of slack
# protects against a driver that reports length-1 without hiding a genuine early stop.
MCI_END_OF_MEDIA_TOLERANCE_MS = 1


class WindowsMciAudioBackend(AudioBackend):
    """Audible Windows audio playback backend via standard library ctypes winmm MCI.

    Device facts this backend is built around (reproduced on Windows 10.0.26300):
    - MCI aliases are thread-affine: a command from a thread other than the one that
      opened the alias fails with error 263.  This backend records the opening thread
      and refuses cross-thread commands before they reach MCI.
    - `status length` is an integer millisecond count (observed floor: 22070 frames at
      44.1 kHz = 500.4535 ms reports 500).  `play from`/`seek to` beyond it fail (282).
    - At end of media the device stops itself in mode 'stopped' at position == length.
    - `seek` leaves the device in mode 'stopped'; `stop` does not rewind the position.
    - `pause`/`resume` on a stopped device fail with error 302.

    `is_playing` / `is_paused` report acknowledged commands reconciled with the most
    recent device observation (`observe()` queries `status mode`).  They are not a
    substitute for an observation; the transport observes the device on every update.
    """

    def __init__(self, winmm: Any = None, temp_dir: Optional[str] = None) -> None:
        self._alias: str = f"vmm_audio_{id(self)}"
        self._is_open: bool = False
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._play_requested: bool = False
        self._loop: bool = False
        self._temp_wav_path: Optional[str] = None
        self._temp_dir: Optional[str] = temp_dir
        self._owner_thread_id: Optional[int] = None
        self._device_length_ms: Optional[int] = None
        self._media_duration_ms: Optional[float] = None
        self._end_of_media_latched: bool = False
        self._unexpected_stop_latched: bool = False
        self.last_observation: Optional[DeviceObservation] = None
        self.last_cleanup_errors: List[str] = []

        self._winmm = winmm
        if self._winmm is None and os.name == "nt":
            try:
                self._winmm = ctypes.windll.winmm
            except Exception:
                self._winmm = None

        self._status: AudioBackendStatus = (
            AudioBackendStatus.AVAILABLE if self._winmm is not None else AudioBackendStatus.UNAVAILABLE
        )

    # -- reconciled flags ---------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        """True if play was acknowledged and no later observation showed the device stopped."""
        return self._is_open and self._is_playing

    @property
    def is_paused(self) -> bool:
        """True if pause was acknowledged by a device that was actually playing."""
        return self._is_open and self._is_paused

    @property
    def device_length_ms(self) -> Optional[int]:
        """Integer media length reported by MCI `status length` (None if unknown)."""
        return self._device_length_ms

    @property
    def owner_thread_id(self) -> Optional[int]:
        return self._owner_thread_id

    @property
    def temp_wav_path(self) -> Optional[str]:
        return self._temp_wav_path

    # -- command plumbing ---------------------------------------------------------

    def _check_owner_thread(self, command: str) -> None:
        if self._owner_thread_id is not None and threading.get_ident() != self._owner_thread_id:
            raise MciThreadOwnershipError(
                f"MCI command '{command}' refused: the device was opened on thread {self._owner_thread_id} "
                f"but the command was issued from thread {threading.get_ident()}. Windows MCI aliases are "
                "thread-affine (cross-thread commands fail with MCI error 263)."
            )

    def _command(self, command: str, expect_output: bool = False) -> str:
        """Thread-checked MCI command dispatch.  All backend operations go through here."""
        self._check_owner_thread(command)
        return self._send_mci(command, expect_output)

    def _send_mci(self, command: str, expect_output: bool = False) -> str:
        """Send an MCI command string via winmm.mciSendStringW with strict error checking."""
        if self._winmm is None:
            raise AudioBackendError("Windows Multimedia API (winmm.dll) is not available.")

        buf_size = 256
        buffer = ctypes.create_unicode_buffer(buf_size) if expect_output else None
        ret = self._winmm.mciSendStringW(command, buffer, buf_size if expect_output else 0, None)
        if ret != 0:
            err_buf = ctypes.create_unicode_buffer(256)
            self._winmm.mciGetErrorStringW(ret, err_buf, 256)
            err_msg = err_buf.value or f"Unknown MCI Error {ret}"
            raise AudioBackendError(f"MCI command failed '{command}': {err_msg} (code {ret})")

        return buffer.value if expect_output and buffer else ""

    def _to_device_ms(self, source_ms: float) -> int:
        """Map an exact source coordinate to the nearest valid integer device coordinate.

        Rounding error is at most 0.5 ms.  Coordinates beyond the device length are
        clamped to the length (MCI rejects them with error 282); the transport handles
        any remaining source duration after the media ends as a silent tail.
        """
        dev = max(0, int(round(float(source_ms))))
        if self._device_length_ms is not None:
            dev = min(dev, self._device_length_ms)
        return dev

    def _clear_latches(self) -> None:
        self._end_of_media_latched = False
        self._unexpected_stop_latched = False

    # -- lifecycle ----------------------------------------------------------------

    def load_wav_bytes(self, wav_bytes: bytes) -> None:
        """Load PCM WAV audio into Windows audio device via an application-owned temp file."""
        self.unload()

        if self._winmm is None:
            self._status = AudioBackendStatus.UNAVAILABLE
            return

        fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="music_play_", dir=self._temp_dir)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(wav_bytes)
        except Exception:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            raise
        self._temp_wav_path = temp_path
        self._media_duration_ms = get_wav_duration_ms(wav_bytes) or None

        opened = False
        try:
            # The opening thread becomes the device owner for every later command.
            self._owner_thread_id = threading.get_ident()
            self._send_mci(f'open "{self._temp_wav_path}" type waveaudio alias {self._alias}')
            opened = True
            self._is_open = True
            self._command(f"set {self._alias} time format milliseconds")
            length_str = self._command(f"status {self._alias} length", expect_output=True).strip()
            if not length_str.isdigit():
                raise AudioBackendError(f"MCI reported a non-numeric media length: {length_str!r}")
            self._device_length_ms = int(length_str)
            self._clear_latches()
            self._status = AudioBackendStatus.AVAILABLE
        except Exception as ex:
            if not opened:
                self._is_open = False
            try:
                self.unload()
            except Exception as cleanup_ex:
                ex.add_note(f"additionally, cleanup after failed open failed: {cleanup_ex}")
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to open WAV in Windows audio device: {ex}") from ex

    def play(self, start_ms: float = 0.0, loop: bool = False) -> None:
        self._check_owner_thread("play")
        if not self._is_open:
            self._status = AudioBackendStatus.UNAVAILABLE
            raise AudioBackendError("Cannot play: Windows audio device is not open.")
        self._loop = loop
        seek_int = self._to_device_ms(start_ms)
        try:
            self._command(f"play {self._alias} from {seek_int}")
            self._is_playing = True
            self._is_paused = False
            self._play_requested = True
            self._clear_latches()
            self._status = AudioBackendStatus.DRIVER_PLAYING
        except Exception as ex:
            self._is_playing = False
            self._play_requested = False
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to begin audible playback: {ex}") from ex

    def _query_mode(self) -> str:
        return self._command(f"status {self._alias} mode", expect_output=True).strip().lower()

    def pause(self) -> None:
        self._check_owner_thread("pause")
        if not self._is_open:
            raise AudioBackendError("Cannot pause: Windows audio device is not open.")
        if not self._is_playing:
            return
        try:
            mode = self._query_mode()
            if mode == "stopped":
                # The device already stopped by itself (end of media).  Sending 'pause'
                # would fail with MCI 302; the device is in the requested non-playing
                # condition, but there is no resumable paused session.
                self._is_playing = False
                self._is_paused = False
                self._play_requested = False
                self._status = AudioBackendStatus.STOPPED
                return
            if mode != "paused":
                self._command(f"pause {self._alias}")
            self._is_playing = False
            self._is_paused = True
            self._play_requested = False
            self._status = AudioBackendStatus.PAUSED
        except Exception as ex:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to pause audio device: {ex}") from ex

    def resume(self) -> None:
        self._check_owner_thread("resume")
        if not self._is_open:
            self._status = AudioBackendStatus.UNAVAILABLE
            raise AudioBackendError("Cannot resume: Windows audio device is not open.")
        if not self._is_paused:
            raise AudioBackendError("Cannot resume: Windows audio device is not in a paused state.")
        try:
            mode = self._query_mode()
            if mode == "stopped":
                self._is_paused = False
                raise AudioBackendError(
                    "device reports mode 'stopped', not 'paused'; resume would fail with MCI 302"
                )
            self._command(f"resume {self._alias}")
            self._is_playing = True
            self._is_paused = False
            self._play_requested = True
            self._clear_latches()
            self._status = AudioBackendStatus.DRIVER_PLAYING
        except Exception as ex:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to resume audio device: {ex}") from ex

    def stop(self) -> None:
        self._check_owner_thread("stop")
        if not self._is_open:
            return
        try:
            self._command(f"stop {self._alias}")
            self._is_playing = False
            self._is_paused = False
            self._play_requested = False
            self._clear_latches()
            self._status = AudioBackendStatus.STOPPED
        except Exception as ex:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to stop audio device '{self._alias}': {ex}") from ex

    def seek(self, pos_ms: float) -> None:
        self._check_owner_thread("seek")
        if not self._is_open:
            raise AudioBackendError("Cannot seek: Windows audio device is not open.")
        seek_int = self._to_device_ms(pos_ms)
        try:
            self._command(f"seek {self._alias} to {seek_int}")
            self._clear_latches()
            if self._play_requested:
                # 'seek' leaves the device stopped; restart playback at the new coordinate.
                self._command(f"play {self._alias} from {seek_int}")
                self._is_playing = True
                self._is_paused = False
            else:
                self._is_playing = False
                self._is_paused = False
                self._status = AudioBackendStatus.STOPPED
        except Exception as ex:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"Failed to seek audio device '{self._alias}': {ex}") from ex

    def get_device_position_ms(self) -> Optional[float]:
        """Query authoritative audio hardware device playback position."""
        if not self._is_open:
            return None
        self._check_owner_thread("status position")
        try:
            pos_str = self._command(f"status {self._alias} position", expect_output=True)
            if pos_str and pos_str.strip().isdigit():
                return float(pos_str.strip())
        except Exception as ex:
            if self._is_playing:
                self._status = AudioBackendStatus.FAILED
                raise AudioBackendError(f"Audio device query failed during active playback: {ex}") from ex
            return None
        return None

    def observe(self) -> DeviceObservation:
        """Query `status mode` then `status position` and reconcile the cached flags.

        Mode is queried first: if the media ends between the two queries the device is
        reported as still playing at (or near) its final position, and the next
        observation reports the stop.  The reverse order could pair a pre-end position
        with a post-end 'stopped' mode and misclassify a natural end as an early stop.
        """
        if not self._is_open:
            obs = DeviceObservation(position_ms=None)
            self.last_observation = obs
            return obs
        self._check_owner_thread("status")
        try:
            mode = self._query_mode()
            pos_str = self._command(f"status {self._alias} position", expect_output=True).strip()
        except Exception as ex:
            if self._is_playing:
                self._status = AudioBackendStatus.FAILED
                raise AudioBackendError(f"Audio device query failed during active playback: {ex}") from ex
            obs = DeviceObservation(position_ms=None)
            self.last_observation = obs
            return obs

        if pos_str.isdigit():
            position: Optional[float] = float(pos_str)
        elif self._is_playing:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError(f"MCI reported a non-numeric device position: {pos_str!r}")
        else:
            position = None

        if mode == "playing":
            self._is_playing = True
            self._is_paused = False
        elif mode == "paused":
            self._is_playing = False
            self._is_paused = True
        elif mode == "stopped":
            if self._is_playing:
                # Uncommanded stop: classify with the device's own length.
                length = self._device_length_ms
                if (length is not None and position is not None
                        and position >= length - MCI_END_OF_MEDIA_TOLERANCE_MS):
                    self._end_of_media_latched = True
                    self._status = AudioBackendStatus.STOPPED
                else:
                    self._unexpected_stop_latched = True
                    self._status = AudioBackendStatus.FAILED
            self._is_playing = False
            self._is_paused = False
        # Any other mode string ('seeking', 'not ready', ...) leaves the flags unchanged.

        stopped = mode == "stopped"
        obs = DeviceObservation(
            position_ms=position,
            mode=mode,
            end_of_media=stopped and self._end_of_media_latched,
            unexpected_stop=stopped and self._unexpected_stop_latched,
        )
        self.last_observation = obs
        return obs

    def is_available(self) -> bool:
        return self._winmm is not None

    def is_genuinely_audible(self) -> bool:
        return self._winmm is not None and self._is_open

    def get_status(self) -> AudioBackendStatus:
        return self._status

    def unload(self) -> None:
        """Stop and close the MCI device and remove this backend's own temp WAV file.

        Every step is attempted.  Failures are recorded in `last_cleanup_errors` and
        raised together afterwards; a failed close leaves the alias marked open (and its
        file in place, since MCI may still hold it) so a later unload can retry.
        Only the file this backend created is ever removed.
        """
        errors: List[str] = []
        if self._is_open:
            self._check_owner_thread("unload")
            try:
                self._command(f"stop {self._alias}")
            except Exception as ex:
                errors.append(f"stop: {ex}")
            try:
                self._command(f"close {self._alias}")
            except Exception as ex:
                errors.append(f"close: {ex}")
            else:
                self._is_open = False
                self._owner_thread_id = None
                self._device_length_ms = None
            self._is_playing = False
            self._is_paused = False
            self._play_requested = False
            self._clear_latches()

        if not self._is_open:
            self._owner_thread_id = None
            if self._temp_wav_path:
                if os.path.exists(self._temp_wav_path):
                    try:
                        os.remove(self._temp_wav_path)
                    except OSError as ex:
                        errors.append(f"remove temp WAV {self._temp_wav_path!r}: {ex}")
                if not os.path.exists(self._temp_wav_path):
                    self._temp_wav_path = None
            self._media_duration_ms = None
            if self._winmm is not None and not errors:
                self._status = AudioBackendStatus.AVAILABLE

        self.last_cleanup_errors = errors
        if errors:
            self._status = AudioBackendStatus.FAILED
            raise AudioBackendError("Audio device cleanup incomplete: " + "; ".join(errors))

    def close(self) -> None:
        """Alias for unload(): release the MCI device and the temp WAV file."""
        self.unload()


# Backward compatibility alias
WindowsWaveBackend = WindowsMciAudioBackend


def get_wav_duration_ms(wav_bytes: bytes) -> float:
    """Derive authentic duration in milliseconds from PCM WAV header."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            if framerate > 0:
                return (nframes * 1000.0) / framerate
    except Exception:
        pass
    return 0.0


def synthesize_song_audio(
    events: List[SoundEvent],
    total_duration_ms: int,
    sample_rate: int = 44100,
) -> bytes:
    """Synthesize multi-voice polyphonic audio from sound events.

    Uses authoritative exact rational timing from get_authoritative_exact_timing().
    Applies 5ms linear attack/decay anti-clipping envelopes and dynamic normalization.
    """
    total_sec = max(0.001, total_duration_ms / 1000.0)
    total_samples = int(math.ceil(total_sec * sample_rate))
    if total_samples <= 0:
        total_samples = 1

    buffer = [0.0] * total_samples
    attack_samples = max(1, int(0.005 * sample_rate))
    decay_samples = max(1, int(0.005 * sample_rate))

    for event in events:
        # Strict validation of authoritative rational timing
        start_sec_frac, end_sec_frac, _ = get_authoritative_exact_timing(event, unit="sec")

        # Direct rational quantization to discrete sample indices
        start_idx = max(0, int(round(start_sec_frac * sample_rate)))
        end_idx = min(total_samples, int(round(end_sec_frac * sample_rate)))
        note_len = end_idx - start_idx
        if note_len <= 0:
            continue

        # Pitch determination
        pitch = 60.0
        if event.height is not None:
            pitch = float(event.height)
        elif event.attributes and "midi_pitch" in event.attributes:
            pitch = float(event.attributes["midi_pitch"])

        freq = 440.0 * (2.0 ** ((pitch - 69.0) / 12.0))
        freq = max(20.0, min(10000.0, freq))

        phase_inc = 2.0 * math.pi * freq / sample_rate
        cur_phase = 0.0

        for i in range(note_len):
            env = 1.0
            if i < attack_samples:
                env = float(i) / attack_samples
            rem = note_len - 1 - i
            if rem < decay_samples:
                env = min(env, float(rem) / decay_samples)

            sample_val = env * math.sin(cur_phase) * 0.3
            buffer[start_idx + i] += sample_val
            cur_phase += phase_inc

    # Anti-clipping dynamic normalization
    max_val = max(abs(x) for x in buffer) if buffer else 0.0
    norm_factor = 1.0
    if max_val > 0.95:
        norm_factor = 0.95 / max_val

    # 16-bit PCM pack
    pcm_frames = bytearray()
    for sample in buffer:
        scaled = max(-32767, min(32767, int(sample * norm_factor * 32767.0)))
        pcm_frames.extend(struct.pack("<h", scaled))

    # Encapsulate in valid WAV container
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_frames)

    return wav_io.getvalue()



# -----------------------------------------------------------------------------
# Transport snapshots
# -----------------------------------------------------------------------------

_TRANSPORT_IDS = itertools.count(1)


@dataclass(frozen=True)
class TransportSnapshot:
    """Immutable, coherent publication of committed transport state.

    transport_id: identity of the PlaybackTransport that produced it.
    source_id:    increments on every load_timeline(); identifies the loaded source.
    epoch:        increments on every coordinate discontinuity (load, seek, stop, reset,
                  start from STOPPED/ERROR, loop wrap).  Within one epoch the published
                  position of a PLAYING transport never decreases.
    sequence:     strictly increasing per transport.  A consumer that has rendered
                  sequence N must reject any later-arriving snapshot with sequence <= N.
    state, position_ms, active_event_ids: committed together in one transaction;
                  active_event_ids is exactly {e : start(e) <= position_ms < end(e)}.
    """
    transport_id: int
    source_id: int
    epoch: int
    sequence: int
    state: TransportState
    position_ms: float
    active_event_ids: FrozenSet[str]
    total_duration_ms: float
    looping: bool
    reason: str

    def supersedes(self, other: Optional["TransportSnapshot"]) -> bool:
        """True if this snapshot should replace `other` in a consumer's view."""
        if other is None or other.transport_id != self.transport_id:
            return True
        return self.sequence > other.sequence


# Completion tolerance (ms).  Progress p has reached the source end T iff  p >= T - tol.
#
# The thirteenth revision tested  round(p, 6) >= T, rounding only the left side.  When T is not a
# multiple of 1e-6 ms (almost every PCM duration frames*1000/rate) and p is exactly T, which is
# what confirmed end-of-media yields, round(p, 6) can fall below T and completion never happens
# (22,071 frames @ 44.1 kHz: round(500.4761904761905, 6) = 500.47619 < T).
# tol = 5e-7 ms makes the comparison symmetric.  For every T that IS a multiple of 1e-6 ms (all
# integer-ms durations and all six-decimal test durations) it accepts exactly the progress values
# the old predicate accepted, apart from exact half-way ties.  It is about 45,000x smaller than one
# 44.1 kHz sample period (22.7 us) and 2,000,000x smaller than the 1 ms MCI resolution.  It never
# changes T or any source coordinate; it only decides the comparison.
_COMPLETION_TOLERANCE_MS = 5e-7


class PlaybackTransport:
    """Authoritative playback transport and synchronization controller.

    Owned by the thread that constructs it (the Tk thread in the GUI).  Periodic
    updates are driven by the injected Scheduler; there is no internal thread.
    """

    def __init__(
        self,
        timeline: Optional[Any] = None,
        wav_bytes: Optional[bytes] = None,
        audio_backend: Optional[AudioBackend] = None,
        clock: Optional[Clock] = None,
        tick_interval_ms: int = 15,
        synthesize: bool = True,
        buffer_latency_ms: float = 0.0,
        scheduler: Optional[Scheduler] = None,
    ) -> None:
        self._owner_thread_id: int = threading.get_ident()
        self.transport_id: int = next(_TRANSPORT_IDS)
        self.clock: Clock = clock or RealClock()
        if audio_backend is None:
            mci = WindowsMciAudioBackend()
            audio_backend = mci if mci.is_available() else SimulatedAudioBackend()
        self.audio_backend: AudioBackend = audio_backend
        if hasattr(self.audio_backend, "set_clock"):
            self.audio_backend.set_clock(self.clock)
        self.tick_interval_ms: int = max(5, int(tick_interval_ms))
        self.buffer_latency_ms: float = max(0.0, float(buffer_latency_ms))
        # Default: an inert manual scheduler.  Nothing advances unless the owner drives it.
        self._scheduler_is_default: bool = scheduler is None
        self._warned_undriven: bool = False
        self.scheduler: Scheduler = scheduler if scheduler is not None else ManualScheduler()

        self._lock = threading.RLock()
        self._state: TransportState = TransportState.STOPPED
        self._software_pos_ms: float = 0.0
        self._paused_device_pos_ms: Optional[float] = None
        self._paused_audible_pos_ms: Optional[float] = None
        self._drain_start_clock_sec: Optional[float] = None
        self._tail_anchor: Optional[Tuple[float, float]] = None
        self._total_duration_ms: float = 0.0
        self._media_duration_ms: float = 0.0
        self._loop: bool = False
        self._closed: bool = False

        self._events: List[SoundEvent] = []
        self._intervals: List[Tuple[float, float, SoundEvent]] = []
        self._active_event_ids: FrozenSet[str] = frozenset()

        self._clock_start_sec: float = 0.0
        self._transport_start_ms: float = 0.0
        self._segment_start_ms: float = 0.0

        # Audio source tracking
        self._is_synthesized: bool = True
        self._wav_bytes: Optional[bytes] = None

        # Publication identity
        self._source_id: int = 0
        self._epoch: int = 0
        self._sequence: int = 0
        self._last_snapshot: Optional[TransportSnapshot] = None

        # Scheduled update bookkeeping: at most one pending handle, generation-guarded.
        self._tick_handle: Any = None
        self._tick_generation: int = 0

        # Callbacks
        self._tick_callbacks: List[Callable[[float, Set[str]], None]] = []
        self._snapshot_callbacks: List[Callable[[TransportSnapshot], None]] = []
        self._state_callbacks: List[Callable[[TransportState], None]] = []
        self._end_callbacks: List[Callable[[], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []

        self._publish("init")
        if timeline is not None or wav_bytes is not None:
            self.load_timeline(timeline, wav_bytes=wav_bytes, synthesize=synthesize)

    # -------------------------------------------------------------------------
    # Ownership & lifecycle guards
    # -------------------------------------------------------------------------

    def _require_owner(self, operation: str) -> None:
        if threading.get_ident() != self._owner_thread_id:
            raise TransportThreadError(
                f"PlaybackTransport.{operation}() called from thread {threading.get_ident()}; the transport "
                f"is owned by thread {self._owner_thread_id}. All lifecycle operations and device access "
                "must run on the owning (GUI) thread."
            )

    def _require_usable(self, operation: str) -> None:
        if self._closed:
            raise TransportClosedError(f"PlaybackTransport.{operation}() called after close().")
        self._require_owner(operation)

    @property
    def owner_thread_id(self) -> int:
        return self._owner_thread_id

    @property
    def is_closed(self) -> bool:
        return self._closed

    # -------------------------------------------------------------------------
    # Properties & Status
    # -------------------------------------------------------------------------

    @property
    def state(self) -> TransportState:
        with self._lock:
            return self._state

    @property
    def snapshot(self) -> Optional[TransportSnapshot]:
        """Last published authoritative snapshot.  Performs no device I/O."""
        with self._lock:
            return self._last_snapshot

    @property
    def source_id(self) -> int:
        with self._lock:
            return self._source_id

    @property
    def has_pending_tick(self) -> bool:
        with self._lock:
            return self._tick_handle is not None

    @property
    def position_ms(self) -> float:
        """Live authoritative playback position in milliseconds.

        While PLAYING this performs one device observation (owner thread only) and
        raises AudioBackendError if the device cannot be read; it never substitutes a
        software estimate silently and never changes transport state.  While STOPPED,
        PAUSED or ERROR it returns the committed coordinate.  Consumers that must not
        perform device I/O (the GUI) use `snapshot` instead.
        """
        with self._lock:
            return self.estimated_audible_position_ms

    @property
    def software_transport_position_ms(self) -> float:
        """Position derived strictly from the monotonic software clock."""
        with self._lock:
            if self._state in (TransportState.PAUSED, TransportState.ERROR) and self._paused_audible_pos_ms is not None:
                return self._paused_audible_pos_ms
            return self._calculate_software_position_ms()

    @property
    def device_position_ms(self) -> Optional[float]:
        """Hardware playback position queried from audio device."""
        with self._lock:
            if self._state in (TransportState.PAUSED, TransportState.ERROR) and self._paused_device_pos_ms is not None:
                return self._paused_device_pos_ms
            return self.audio_backend.get_device_position_ms()

    def _stationary_position_ms(self) -> float:
        """Committed coordinate of a non-PLAYING transport (no device I/O)."""
        if self._state in (TransportState.PAUSED, TransportState.ERROR) and self._paused_audible_pos_ms is not None:
            return self._paused_audible_pos_ms
        return self._software_pos_ms

    def _query_device_and_audible_progress(
        self, record_drain_latch: bool = False
    ) -> Tuple[Optional[float], float]:
        """Observe the device once and compute the authoritative audible position.

        Returns:
            (device_pos, raw_audible_ms) where raw_audible_ms is un-clamped and un-looped.

        Raises:
            AudioBackendError: if the observation fails, if an available backend
                unexpectedly reports no position, if the position is invalid (NaN, inf,
                negative), or if the device stopped by itself before the end of its media.
        """
        # Silent tail: the device finished its media but the source continues (the
        # timeline extends past the audio).  Progress follows the transport clock.
        if self._tail_anchor is not None:
            anchor_sec, anchor_pos = self._tail_anchor
            elapsed_ms = max(0.0, (self.clock.now_seconds() - anchor_sec) * 1000.0)
            return (None, anchor_pos + elapsed_ms)

        try:
            obs = self.audio_backend.observe()
        except Exception as ex:
            raise AudioBackendError(f"Audio backend query failed: {ex}") from ex

        dev_pos = obs.position_ms
        if obs.unexpected_stop:
            raise AudioBackendError(
                f"Audio device stopped unexpectedly at device position {dev_pos} ms, before the end of its media"
                f" (device length {getattr(self.audio_backend, 'device_length_ms', None)} ms)."
            )

        if dev_pos is None:
            if self.audio_backend.is_available() and not isinstance(self.audio_backend, NullAudioBackend):
                raise AudioBackendError("Unexpected loss of device coordinates: backend returned None while available")
            # Legitimate headless / NullAudioBackend fallback
            elapsed_sec = self.clock.now_seconds() - self._clock_start_sec
            sw_pos = self._transport_start_ms + (elapsed_sec * 1000.0)
            return (None, sw_pos)

        if not math.isfinite(dev_pos) or dev_pos < 0:
            raise AudioBackendError(f"Invalid device position returned by backend: {dev_pos}")

        if obs.end_of_media and self._media_duration_ms > dev_pos:
            # The device has rendered its whole media.  Its integer coordinate is a floor of
            # the exact media duration; completion evidence lets us use the exact value.
            dev_pos = self._media_duration_ms

        # Valid numeric device position
        base_audible = max(self._segment_start_ms, dev_pos - self.buffer_latency_ms)
        if self.buffer_latency_ms > 0.0 and self._total_duration_ms > 0 and dev_pos >= self._total_duration_ms:
            if self._drain_start_clock_sec is None:
                if record_drain_latch:
                    self._drain_start_clock_sec = self.clock.now_seconds()
                drain_elapsed = 0.0
            else:
                drain_elapsed = max(0.0, (self.clock.now_seconds() - self._drain_start_clock_sec) * 1000.0)
            drained_audible = (self._total_duration_ms - self.buffer_latency_ms) + drain_elapsed
            audible = max(base_audible, drained_audible)
        else:
            if record_drain_latch:
                self._drain_start_clock_sec = None
            audible = base_audible

        audible = max(self._segment_start_ms, audible)

        if obs.end_of_media:
            audible = max(audible, self._software_pos_ms if self._state == TransportState.PLAYING else audible)
            if not self._has_reached_end(audible) and record_drain_latch:
                self._tail_anchor = (self.clock.now_seconds(), audible)
        return (dev_pos, audible)

    @property
    def estimated_audible_position_ms(self) -> float:
        """Authoritative audible position accounting for hardware buffer latency."""
        with self._lock:
            if self._state == TransportState.PLAYING:
                device_pos, audible = self._query_device_and_audible_progress(record_drain_latch=False)
                if self._total_duration_ms > 0:
                    return min(audible, self._total_duration_ms)
                return audible
            return self._stationary_position_ms()

    @property
    def total_duration_ms(self) -> float:
        with self._lock:
            return self._total_duration_ms

    @property
    def media_duration_ms(self) -> float:
        """Exact duration of the loaded PCM media (frames / rate), 0.0 if none."""
        with self._lock:
            return self._media_duration_ms

    @property
    def is_looping(self) -> bool:
        with self._lock:
            return self._loop

    @property
    def is_synthesized_audio(self) -> bool:
        with self._lock:
            return self._is_synthesized

    @property
    def active_event_ids(self) -> Set[str]:
        with self._lock:
            return set(self._active_event_ids)

    # -------------------------------------------------------------------------
    # Transaction helpers
    # -------------------------------------------------------------------------

    def _new_epoch(self) -> None:
        self._epoch += 1

    def _set_stationary(self, state: TransportState, position_ms: float, device_pos: Optional[float] = None) -> None:
        """Commit a non-PLAYING state at an achieved coordinate.  Cancels scheduled updates."""
        self._state = state
        self._software_pos_ms = position_ms
        self._tail_anchor = None
        if state == TransportState.STOPPED:
            self._paused_audible_pos_ms = None
            self._paused_device_pos_ms = None
            self._drain_start_clock_sec = None
        else:
            self._paused_audible_pos_ms = position_ms
            self._paused_device_pos_ms = device_pos
        self._update_active_events(position_ms)
        self._cancel_tick()

    def _fail(
        self,
        error: Exception,
        preserved_position_ms: float,
        device_pos: Optional[float] = None,
        attempt_shutdown: bool = True,
    ) -> Exception:
        """Commit ERROR at a preserved, previously achieved coordinate.

        If the backend may still be producing audio, a controlled shutdown (backend.stop)
        is attempted.  The original failure is preserved; a secondary shutdown failure is
        attached to it (`secondary_shutdown_error` and an exception note) rather than
        replacing it.  Software rollback is never taken as evidence of device rollback.
        """
        if attempt_shutdown and getattr(self.audio_backend, "is_playing", False):
            try:
                self.audio_backend.stop()
            except Exception as secondary:
                try:
                    error.secondary_shutdown_error = secondary  # type: ignore[attr-defined]
                    error.add_note(f"Controlled audio shutdown after the failure also failed: {secondary}")
                except Exception:
                    pass
                _log.warning("Controlled audio shutdown after transport failure failed: %r", secondary)
        self._set_stationary(TransportState.ERROR, preserved_position_ms, device_pos)
        return error

    def _publish(self, reason: str) -> TransportSnapshot:
        """Build and record one immutable snapshot from committed state (call under lock)."""
        self._sequence += 1
        snap = TransportSnapshot(
            transport_id=self.transport_id,
            source_id=self._source_id,
            epoch=self._epoch,
            sequence=self._sequence,
            state=self._state,
            position_ms=self._software_pos_ms,
            active_event_ids=self._active_event_ids,
            total_duration_ms=self._total_duration_ms,
            looping=self._loop,
            reason=reason,
        )
        self._last_snapshot = snap
        return snap

    def _deliver(
        self,
        snap: TransportSnapshot,
        notify_state: bool = False,
        end: bool = False,
        error: Optional[Exception] = None,
    ) -> None:
        """Deliver one snapshot (outside the lock).  Reads nothing but the snapshot."""
        if notify_state:
            for cb in list(self._state_callbacks):
                self._invoke(cb, snap.state)
        for cb in list(self._snapshot_callbacks):
            self._invoke(cb, snap)
        for cb in list(self._tick_callbacks):
            self._invoke(cb, snap.position_ms, set(snap.active_event_ids))
        if end:
            for cb in list(self._end_callbacks):
                self._invoke(cb)
        if error is not None:
            for cb in list(self._error_callbacks):
                self._invoke(cb, error)

    @staticmethod
    def _invoke(cb: Callable[..., None], *args: Any) -> None:
        try:
            cb(*args)
        except Exception:
            _log.exception("PlaybackTransport callback %r raised", cb)

    # -------------------------------------------------------------------------
    # Scheduled updates
    # -------------------------------------------------------------------------

    def _ensure_tick_scheduled(self) -> None:
        if self._closed or self._state != TransportState.PLAYING or self._tick_handle is not None:
            return
        generation = self._tick_generation
        self._tick_handle = self.scheduler.call_later(
            self.tick_interval_ms, lambda: self._on_scheduled_tick(generation)
        )

    def _cancel_tick(self) -> None:
        self._tick_generation += 1
        handle, self._tick_handle = self._tick_handle, None
        if handle is not None:
            try:
                self.scheduler.cancel(handle)
            except Exception as ex:
                # The generation token already invalidates the callback.
                _log.warning("Scheduler cancel failed (callback invalidated by generation): %r", ex)

    def _on_scheduled_tick(self, generation: int) -> None:
        with self._lock:
            if generation != self._tick_generation:
                return  # Obsolete callback from a superseded playback session.
            self._tick_handle = None
            if self._closed or self._state != TransportState.PLAYING:
                return
        try:
            self.step_tick()
        except AudioBackendError as ex:
            _log.debug("Scheduled transport update ended in ERROR: %r", ex)
        except Exception:
            _log.exception("Scheduled transport update raised unexpectedly")
        finally:
            with self._lock:
                if not self._closed and self._state == TransportState.PLAYING:
                    self._ensure_tick_scheduled()

    # -------------------------------------------------------------------------
    # Timeline & Audio Loading
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_events(timeline: Any) -> List[SoundEvent]:
        events: List[SoundEvent] = []
        if timeline is not None:
            if hasattr(timeline, "events"):
                raw_evts = timeline.events
                events = list(raw_evts.values()) if isinstance(raw_evts, dict) else list(raw_evts)
            elif hasattr(timeline, "rows"):
                rows_val = timeline.rows
                row_iter = rows_val.values() if hasattr(rows_val, "values") else rows_val
                for r in row_iter:
                    events.extend(r.events)
            elif isinstance(timeline, list):
                events = list(timeline)
        return events

    def load_timeline(
        self,
        timeline: Any = None,
        wav_bytes: Optional[bytes] = None,
        synthesize: bool = True,
    ) -> None:
        """Load a timeline or raw PCM WAV into the transport.

        Strictly validates timing of all events using get_authoritative_exact_timing()
        BEFORE touching the current source, so a malformed source leaves the previous
        source intact.  Derives authentic duration from WAV frame count if provided,
        preserving trailing silence.  Releases the previous source's device resources.
        """
        self._require_usable("load_timeline")

        # 1. Validate and prepare the new source (pure computation, no state changes).
        events = self._extract_events(timeline)
        intervals: List[Tuple[float, float, SoundEvent]] = []
        max_end = 0
        for e in events:
            # Raises ValueError if rational timing attributes are malformed/incomplete
            start_frac, end_frac, _ = get_authoritative_exact_timing(e)
            intervals.append((float(start_frac), float(end_frac), e))
            if e.end_time_ms > max_end:
                max_end = e.end_time_ms
        sorted_events = sorted(events, key=lambda e: (e.start_time_ms, e.end_time_ms, e.event_id))
        order = {id(e): i for i, e in enumerate(sorted_events)}
        intervals.sort(key=lambda it: order[id(it[2])])

        wav_dur_ms = get_wav_duration_ms(wav_bytes) if wav_bytes is not None else 0.0
        timeline_dur = float(getattr(timeline, "total_duration_ms", 0.0) or 0.0) if timeline is not None else 0.0
        total = max(float(max_end), timeline_dur, float(wav_dur_ms))

        if wav_bytes is not None:
            is_synth, audio = False, wav_bytes
        elif synthesize and sorted_events:
            is_synth, audio = True, synthesize_song_audio(sorted_events, int(math.ceil(total)))
        else:
            is_synth, audio = False, None

        # 2. Stop the current source (a failure leaves the old source in ERROR and raises).
        self.stop()

        # 3. Replace the source and its device resources.
        load_error: Optional[Exception] = None
        with self._lock:
            self._cancel_tick()
            try:
                self.audio_backend.unload()
            except Exception as ex:
                load_error = ex
            self._source_id += 1
            self._new_epoch()
            self._events = sorted_events
            self._intervals = intervals
            self._total_duration_ms = total
            self._is_synthesized = is_synth
            self._wav_bytes = audio
            self._media_duration_ms = get_wav_duration_ms(audio) if audio is not None else 0.0
            self._segment_start_ms = 0.0
            self._transport_start_ms = 0.0
            if load_error is None and audio is not None:
                try:
                    self.audio_backend.load_wav_bytes(audio)
                except Exception as ex:
                    load_error = ex
            if load_error is not None:
                err = self._fail(load_error, 0.0, attempt_shutdown=False)
                snap = self._publish("load_failed")
            else:
                self._set_stationary(TransportState.STOPPED, 0.0)
                snap = self._publish("load")
        if load_error is not None:
            self._deliver(snap, notify_state=True, error=err)
            raise err
        self._deliver(snap)

    def close(self) -> None:
        """Release all playback resources.  Idempotent.

        Cancels and invalidates scheduled updates, stops active audio, unloads the
        device (closing MCI and removing this transport's temp WAV), and detaches all
        callbacks.  Every step is attempted; failures are raised together afterwards.
        """
        if self._closed:
            return
        self._require_owner("close")
        errors: List[str] = []
        with self._lock:
            self._closed = True
            self._cancel_tick()
            try:
                if self._state != TransportState.STOPPED or getattr(self.audio_backend, "is_playing", False) \
                        or getattr(self.audio_backend, "is_paused", False):
                    self.audio_backend.stop()
            except Exception as ex:
                errors.append(f"stop: {ex}")
            try:
                self.audio_backend.unload()
            except Exception as ex:
                errors.append(f"unload: {ex}")
            self._state = TransportState.STOPPED
            self._software_pos_ms = 0.0
            self._paused_audible_pos_ms = None
            self._paused_device_pos_ms = None
            self._tail_anchor = None
            self._active_event_ids = frozenset()
            self._wav_bytes = None
            self._tick_callbacks.clear()
            self._snapshot_callbacks.clear()
            self._state_callbacks.clear()
            self._end_callbacks.clear()
            self._error_callbacks.clear()
        if errors:
            raise AudioBackendError("PlaybackTransport.close() incomplete: " + "; ".join(errors))

    # -------------------------------------------------------------------------
    # Transport Controls
    # -------------------------------------------------------------------------

    def play(self) -> None:
        """Begin or resume playback conditional on backend success."""
        self._require_usable("play")
        err: Optional[Exception] = None
        with self._lock:
            if self._state == TransportState.PLAYING:
                return
            if self._total_duration_ms <= 0:
                return

            prev_state = self._state
            pre_play_pos = self._stationary_position_ms()
            is_resuming = (prev_state == TransportState.PAUSED)

            if is_resuming:
                start_audible = self._paused_audible_pos_ms if self._paused_audible_pos_ms is not None else self._software_pos_ms
                start_device = self._paused_device_pos_ms if self._paused_device_pos_ms is not None else start_audible
            else:
                target_start = 0.0 if self._software_pos_ms >= self._total_duration_ms else self._software_pos_ms
                start_audible = target_start
                start_device = target_start

            # Operation must succeed before transitioning state
            try:
                can_resume = is_resuming and getattr(self.audio_backend, "is_paused", False)
                if can_resume and hasattr(self.audio_backend, "resume"):
                    self.audio_backend.resume()
                else:
                    self.audio_backend.play(start_ms=start_device, loop=self._loop)
            except Exception as ex:
                err = self._fail(ex, pre_play_pos)
                snap = self._publish("play_failed")
            else:
                if not is_resuming:
                    self._new_epoch()
                self._segment_start_ms = start_audible
                self._clock_start_sec = self.clock.now_seconds()
                self._transport_start_ms = start_audible
                self._software_pos_ms = start_audible
                self._paused_device_pos_ms = None
                self._paused_audible_pos_ms = None
                self._tail_anchor = None

                # Re-anchor drain start clock if resuming during buffer drainage
                if self.buffer_latency_ms > 0.0 and self._total_duration_ms > 0 and start_device >= self._total_duration_ms:
                    drained_so_far = max(0.0, start_audible - (self._total_duration_ms - self.buffer_latency_ms))
                    self._drain_start_clock_sec = self.clock.now_seconds() - (drained_so_far / 1000.0)
                else:
                    self._drain_start_clock_sec = None

                self._state = TransportState.PLAYING
                self._update_active_events(start_audible)
                self._cancel_tick()
                self._ensure_tick_scheduled()
                if self._scheduler_is_default and not isinstance(self.clock, TestClock) and not self._warned_undriven:
                    self._warned_undriven = True
                    _log.warning(
                        "PlaybackTransport is playing with a real clock but no injected scheduler: periodic "
                        "updates (playhead, completion, looping) will not run unless step_tick() is called. "
                        "Inject TkScheduler(widget) for GUI use."
                    )
                snap = self._publish("play")

        self._deliver(snap, notify_state=True, error=err)
        if err is not None:
            raise err

    def pause(self) -> None:
        """Pause playback, preserving authoritative position without cursor jumps."""
        self._require_usable("pause")
        err: Optional[Exception] = None
        with self._lock:
            if self._state != TransportState.PLAYING:
                return

            device_pos: Optional[float] = None
            audible_pos: float = self._software_pos_ms

            # 1. Query device & audible progress consistently
            try:
                device_pos, raw_audible = self._query_device_and_audible_progress(record_drain_latch=True)
            except Exception as ex:
                err = ex
                device_pos = None
                audible_pos = self._software_pos_ms
            else:
                if self._total_duration_ms > 0:
                    audible_pos = min(raw_audible, self._total_duration_ms)
                else:
                    audible_pos = raw_audible

            # 2. Attempt backend.pause()
            try:
                self.audio_backend.pause()
            except Exception as ex:
                if err is None:
                    err = ex
                else:
                    err = AudioBackendError(f"{err}; additionally backend.pause failed: {ex}")

            # 3. State transition based on outcome
            if err is not None:
                err = self._fail(err, audible_pos, device_pos=device_pos)
                snap = self._publish("pause_failed")
            else:
                self._set_stationary(TransportState.PAUSED, audible_pos, device_pos)
                snap = self._publish("pause")

        self._deliver(snap, notify_state=True, error=err)
        if err is not None:
            raise err

    def resume(self) -> None:
        """Resume playback from paused position conditional on backend success."""
        self._require_usable("resume")
        with self._lock:
            paused = self._state == TransportState.PAUSED
        if paused:
            self.play()

    def _stop_like(self, operation: str) -> None:
        self._require_usable(operation)
        err: Optional[Exception] = None
        with self._lock:
            query_error: Optional[Exception] = None
            if self._state == TransportState.PLAYING:
                try:
                    _, raw = self._query_device_and_audible_progress(record_drain_latch=False)
                    pre_pos = min(raw, self._total_duration_ms) if self._total_duration_ms > 0 else raw
                except Exception as ex:
                    query_error = ex
                    pre_pos = self._software_pos_ms
            else:
                pre_pos = self._stationary_position_ms()
            try:
                self.audio_backend.stop()
            except Exception as ex:
                if query_error is not None:
                    ex.add_note(f"The pre-{operation} device position query also failed: {query_error}")
                err = self._fail(ex, pre_pos, attempt_shutdown=False)
                snap = self._publish(f"{operation}_failed")
            else:
                self._new_epoch()
                self._segment_start_ms = 0.0
                self._set_stationary(TransportState.STOPPED, 0.0)
                snap = self._publish(operation)

        self._deliver(snap, notify_state=True, error=err)
        if err is not None:
            raise err

    def stop(self) -> None:
        """Stop playback and reset transport position conditional on backend success."""
        self._stop_like("stop")

    def reset(self) -> None:
        """Controlled recovery and teardown from any state.

        Attempts backend.stop(). If backend shutdown fails, maintains ERROR state,
        preserves position, dispatches error callback, and re-raises the exception.
        Only transitions to STOPPED when device shutdown succeeds.
        """
        self._stop_like("reset")

    def seek(self, target_ms: float) -> None:
        """Seek transport position to target_ms. Rejects non-finite values."""
        if not math.isfinite(target_ms):
            raise ValueError(f"Seek target must be a finite number: {target_ms}")
        self._require_usable("seek")

        err: Optional[Exception] = None
        notify_state = False
        with self._lock:
            clamped_target = max(0.0, min(float(target_ms), self._total_duration_ms))
            prev_state = self._state
            query_error: Optional[Exception] = None
            if prev_state == TransportState.PLAYING:
                try:
                    _, raw = self._query_device_and_audible_progress(record_drain_latch=False)
                    pre_seek_pos = min(raw, self._total_duration_ms) if self._total_duration_ms > 0 else raw
                except Exception as ex:
                    # Only needed if the seek fails: the last committed coordinate is preserved
                    # and this query failure is attached to the seek failure.
                    query_error = ex
                    pre_seek_pos = self._software_pos_ms
            else:
                pre_seek_pos = self._stationary_position_ms()

            try:
                # If recovering from ERROR, establish a verified non-playing backend condition first
                if prev_state == TransportState.ERROR:
                    self.audio_backend.stop()
                    if getattr(self.audio_backend, "is_playing", False):
                        raise AudioBackendError("Backend stop failed to establish a non-playing state.")

                if hasattr(self.audio_backend, "seek"):
                    self.audio_backend.seek(clamped_target)
                elif self._state == TransportState.PLAYING:
                    self.audio_backend.play(start_ms=clamped_target, loop=self._loop)
            except Exception as ex:
                if query_error is not None:
                    ex.add_note(f"The pre-seek device position query also failed: {query_error}")
                err = self._fail(ex, pre_seek_pos, attempt_shutdown=(prev_state == TransportState.PLAYING))
                notify_state = True
                snap = self._publish("seek_failed")
            else:
                self._new_epoch()
                self._segment_start_ms = clamped_target
                self._software_pos_ms = clamped_target
                self._transport_start_ms = clamped_target
                self._clock_start_sec = self.clock.now_seconds()
                self._drain_start_clock_sec = None
                self._tail_anchor = None

                # Explicit recovery transition from ERROR to PAUSED upon successful seek
                if self._state == TransportState.ERROR:
                    self._state = TransportState.PAUSED
                    notify_state = True

                if self._state == TransportState.PAUSED:
                    self._paused_device_pos_ms = clamped_target
                    self._paused_audible_pos_ms = clamped_target

                self._update_active_events(clamped_target)
                snap = self._publish("seek")

        self._deliver(snap, notify_state=notify_state, error=err)
        if err is not None:
            raise err

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable loop playback mode."""
        with self._lock:
            self._loop = bool(enabled)

    # -------------------------------------------------------------------------
    # Active Event Detection & Tick Processing
    # -------------------------------------------------------------------------

    def step_tick(self, delta_ms: Optional[float] = None) -> float:
        """Execute one transport update: observe the device once and commit one snapshot.

        Called by the scheduler on the owner thread, or directly by tests.
        """
        self._require_usable("step_tick")
        notify_state = False
        notify_end = False
        err: Optional[Exception] = None

        with self._lock:
            if self._state != TransportState.PLAYING:
                return self._stationary_position_ms()

            if delta_ms is not None:
                if isinstance(self.clock, TestClock):
                    self.clock.advance_ms(delta_ms)
                else:
                    self._transport_start_ms += delta_ms

            # Device-aware progress query: single authoritative progress snapshot per update
            try:
                _, current_progress_ms = self._query_device_and_audible_progress(record_drain_latch=True)
            except Exception as ex:
                err = self._fail(ex, self._software_pos_ms)
                notify_state = True
                snap = self._publish("tick_failed")
            else:
                # End-of-piece and loop decisions governed by authoritative progress snapshot
                if self._has_reached_end(current_progress_ms):
                    if self._loop:
                        # Continuous loop: preserve remainder from authoritative progress
                        remainder_ms = self._loop_remainder_ms(current_progress_ms)
                        try:
                            self.audio_backend.play(start_ms=remainder_ms, loop=True)
                        except Exception as ex:
                            err = self._fail(ex, self._total_duration_ms)
                            notify_state = True
                            snap = self._publish("loop_failed")
                        else:
                            self._new_epoch()
                            self._software_pos_ms = remainder_ms
                            self._segment_start_ms = remainder_ms
                            self._clock_start_sec = self.clock.now_seconds()
                            self._transport_start_ms = remainder_ms
                            self._drain_start_clock_sec = None
                            self._tail_anchor = None
                            self._update_active_events(remainder_ms)
                            snap = self._publish("loop")
                    else:
                        # Natural end of piece reached
                        self._software_pos_ms = self._total_duration_ms
                        self._drain_start_clock_sec = None
                        try:
                            self.audio_backend.stop()
                        except Exception as ex:
                            # Natural completion MUST NOT suppress backend stop failure
                            err = self._fail(ex, self._total_duration_ms, attempt_shutdown=False)
                            snap = self._publish("end_failed")
                        else:
                            self._set_stationary(TransportState.STOPPED, self._total_duration_ms)
                            notify_end = True
                            snap = self._publish("end")
                        notify_state = True
                else:
                    self._software_pos_ms = current_progress_ms
                    self._update_active_events(current_progress_ms)
                    snap = self._publish("tick")

        self._deliver(snap, notify_state=notify_state, end=notify_end, error=err)
        if err is not None:
            raise err
        return snap.position_ms

    def _has_reached_end(self, progress_ms: float) -> bool:
        """Completion predicate: progress has reached the exact source end T (see _COMPLETION_TOLERANCE_MS)."""
        total = self._total_duration_ms
        return total > 0 and progress_ms >= total - _COMPLETION_TOLERANCE_MS

    def _loop_remainder_ms(self, progress_ms: float) -> float:
        """Next-cycle start for progress that has reached T.

        Progress beyond T keeps its remainder (p mod T), rounded to 1e-6 ms as in the thirteenth
        revision.  Progress that reached T from below, within the tolerance, has no remainder:
        p mod T would be ~T and would restart the device at the end.  A remainder that is itself
        within the tolerance of T is likewise a full cycle, so it also restarts at 0.
        """
        total = self._total_duration_ms
        if progress_ms < total:
            return 0.0
        remainder = round(progress_ms % total, 6)
        return 0.0 if remainder >= total - _COMPLETION_TOLERANCE_MS else remainder

    def get_active_events_at(self, position_ms: float) -> List[SoundEvent]:
        """Return all sound events active at position_ms under half-open interval [start, end)."""
        return [e for (st, et, e) in self._intervals if st <= position_ms < et]

    def _calculate_software_position_ms(self) -> float:
        if self._state == TransportState.PLAYING:
            elapsed_sec = self.clock.now_seconds() - self._clock_start_sec
            raw_ms = self._transport_start_ms + (elapsed_sec * 1000.0)
            if self._total_duration_ms > 0:
                if self._loop:
                    return raw_ms % self._total_duration_ms
                return min(raw_ms, self._total_duration_ms)
            return raw_ms
        return self._software_pos_ms

    def _update_active_events(self, position_ms: float) -> None:
        self._active_event_ids = frozenset(e.event_id for e in self.get_active_events_at(position_ms))

    # -------------------------------------------------------------------------
    # Callbacks & Synchronization
    # -------------------------------------------------------------------------

    def add_tick_callback(self, callback: Callable[[float, Set[str]], None]) -> None:
        """Receive (position_ms, active_event_ids) of every published snapshot."""
        self._tick_callbacks.append(callback)

    def add_snapshot_callback(self, callback: Callable[[TransportSnapshot], None]) -> None:
        """Receive every published immutable TransportSnapshot."""
        self._snapshot_callbacks.append(callback)

    def add_state_callback(self, callback: Callable[[TransportState], None]) -> None:
        self._state_callbacks.append(callback)

    def add_end_callback(self, callback: Callable[[], None]) -> None:
        self._end_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[Exception], None]) -> None:
        self._error_callbacks.append(callback)

    def register_tick_callback(self, callback: Callable[[float, Set[str]], None]) -> None:
        self.add_tick_callback(callback)

    def register_snapshot_callback(self, callback: Callable[[TransportSnapshot], None]) -> None:
        self.add_snapshot_callback(callback)

    def register_state_callback(self, callback: Callable[[TransportState], None]) -> None:
        self.add_state_callback(callback)

    def register_end_callback(self, callback: Callable[[], None]) -> None:
        self.add_end_callback(callback)

    def register_error_callback(self, callback: Callable[[Exception], None]) -> None:
        self.add_error_callback(callback)
