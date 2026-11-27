# JOB-03 Remaining Limitations (2026-11-26)

These are preserved as documented. None is claimed to be fixed by the acceptance package.

## Unresolved

1. **Native access violation (2026-11-26 08:30; also 2026-11-25 03:25).**
   - It is memory corruption below the Python level. The line-438 generator expression in the traceback is where corrupted objects were used, not the defect.
   - Its source is **not established**. Either:
     - a defect in CPython 3.15.2; or
     - system or driver instability: kernel bugchecks 0x0A, 0xD1 and 0xF5 were recorded between 11-21 and 11-26.
   - The Author's latest WAV re-test completed without a crash. That does **not** show the corruption is gone.
   - The background analysis thread keeps the window responsive. It gives no process isolation.
   - Further investigation needs separate Author authorization. The options are:
     - administrator access to the minidumps;
     - a memory test (requires a reboot);
     - a second CPython version.
   - Evidence: `JOB_03_WAV_CRASH_EVIDENCE/WAV_CRASH_INVESTIGATION.md`.

## Not measurable by software

2. **Acoustic synchronization is unmeasured.** No microphone or acoustic measurement exists, so the ≤ 20 ms engineering target is unverified. What has been measured instead (none of it acoustic):
   - device startup is about 30 ms;
   - completion is observed 43–92 ms after play time plus the exact duration.

   See architecture §7.8.

## Documented behaviour (accepted limitations)

3. **Pause discontinuity.** The MCI device position steps about 18–35 ms forward across `pause` (20 ms in the latest run), so the cursor jumps by that much at the first update after resume.
4. **Looping is not seamless.** The restart is from 0, with a gap. The per-cycle overrun measured 58–86 ms historically and 75.7–78.7 ms in the latest run.
5. **Brief GUI blocking.** User transport commands block the Tk thread for 6–75 ms; stop and seek while playing are the costliest. Periodic updates take ≤ 1.3 ms.
6. **Integer-ms device coordinates.** MCI reports integer milliseconds, and commands round by ≤ 0.5 ms. The source timing and the published end coordinate stay exact.
7. **JOB-02 segmentation (unchanged by design).**
   - Notes without a silence of at least 20 ms below 5 % of peak form **one** event. `JOB03_test.wav` therefore yields one 0–4000 ms event (E4).
   - Analysis is `O(N × lags)`: about 26–30 s for 4 s of sustained audio.
8. **One analysis at a time.** While a superseded analysis is still computing, a new WAV import is refused with a message; it is not queued.
9. **Real-device suite timing sensitivity.** One of 11 historical runs failed two update-count thresholds during a system-wide timing slowdown. The correctness assertions held, and the log is preserved.

## Physical observations not separately reported (optional; need speakers)

These do not block automated acceptance. The corresponding software behaviour is covered by tests (matrix A13–A15, A17).

- P1: the sound stops on pause and resumes on resume.
- P2: the sound continues from the new position after seeking.
- P3: loop restart, including its audible gap.
- P4: closing the window while sound is audible.
