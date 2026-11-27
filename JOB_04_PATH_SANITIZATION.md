# JOB-04 Publication: Path Sanitization Record (2026-11-27)

**Authorization:** ChatGPT recommended it in the JOB-04 publication audit, and the Author approved it on 2026-11-27 before the R2 package was built.
**Scope:** only the path text in two tracked files, both already published at HEAD `e1a11e7`. No historical test result, measured value, Author statement or job status was changed by this sanitization.

## Rule

One literal replacement, applied to the whole file:

| Replaced | With |
|---|---|
| `C:\Users\<Author's Windows user name>` | `%USERPROFILE%` |

Only that prefix changes; the remainder of each path (for example `\PycharmProjects\calculator`) is kept.

## Occurrences (3)

| File | Line | Path after sanitization | Context |
|---|---:|---|---|
| `JOB_02_COMPLETION_RECORD.md` | 299 | `%USERPROFILE%\PycharmProjects\music` | Recorded verification environment: "Repository:" |
| `JOB_02_COMPLETION_RECORD.md` | 327 | `%USERPROFILE%\PycharmProjects\calculator` | Protected calculator repository: "Path:" |
| `README.md` | 649 | `%USERPROFILE%\PycharmProjects\calculator` | Strict Separation of Repositories (README §8) |

Neither file contains any other personal absolute path after the replacement.

## Hashes (working-copy bytes)

| File | Before | After |
|---|---|---|
| `JOB_02_COMPLETION_RECORD.md` | 34 098 B, `03275d27f8e70be43e5a419bbc5854707949b0fdcf8d4a37ad5a6075c9771c8f` (= HEAD) | 34 096 B, `85a2c80efe79c306f084b15d140535cb692d162a17807f4896290d09fe0de194` |
| `README.md` | 114 340 B, `76487e5600b5d8b2155b3e19d2b72a0eb9557b436537bb5d0f67d17bcddea55b` (HEAD + the authorized Stage 2a correction) | see the manifest: this file also carries the two authorized JOB-04 status lines (714 and 1018) |

## Verification

- **`JOB_02_COMPLETION_RECORD.md`:** applying the rule to the original reproduces the published file exactly. Only lines 299 and 327 differ.
- **`README.md`:** applying the rule to the original changes only line 649. The only other lines that differ from the original are 714 and 1018: the authorized JOB-04 status change, recorded in `JOB_04_PUBLICATION_MANIFEST.md` §2.1. Line 595, the Stage 2a correction, is preserved.
- The check output is in `JOB_04_VERIFICATION_LOG.txt` §10.

## Originals preserved (outside the repository)

The unsanitized originals are kept at `%USERPROFILE%\JOB_04_PUBLICATION_R2_BACKUP_20261127\`, with `SHA256SUMS.txt`. That folder also holds the pre-R2 `.gitignore` and `acceptance_matrix.json`. They are not part of the publication.

## Already sanitized elsewhere

- The JOB-03 records were sanitized in the JOB-03 publication.
- The JOB-04 records contain no personal absolute paths; scratch and project paths appear as `<scratch>` and `<project>`.
- The public GitHub remote name `IWatchSheep/music` (in `JOB_04_BASELINE_INVESTIGATION.md`) is not a local path and is unchanged.
