# JOB-04 Stage 2b: Mathematical Specification of `discover_sound_groups()`

**Implementation:** `music_model/recurrence_discovery.py`. The entry point is also exposed as `music_model.group_discovery.discover_sound_groups`.
**Status:** candidate methods for independent review. These are mathematical pattern matches, **not** verified musical phrase identification.
**Out of scope:** row assignment, column fitting, the merger, Row 1 and graph classification. The legacy Row 1 derivation is not used.

## 1. Input contract (Stage 2a, extended in Stage 2b)

Every note passes through `group_discovery.normalize_note`, which produces:

| Field | Definition |
|---|---|
| `source`, `event_id`, `input_index` | the original object, its id (or `row#index`), and its position in the input |
| `row_id`, `voice_id` | the row key, and the explicit source voice (`voice` attribute or `attributes["voice"]`; MusicXML provides it). **Voice policy:** None, `""` and whitespace-only values all mean *unspecified* and become None. Any other value is compared by its string form, so `1` and `"1"` are the same voice and a voice named `"None"` is distinct from None. |
| `supplied_event_id` | the event id given by the source (non-empty), otherwise None |
| `start`, `end` | **exact** `Fraction` milliseconds (§1.1) |
| `timing_source` | `musicxml_exact_rational`, `audio_exact_rational`, `integer_ms_fallback` (SoundEvent without exact rationals) or `ms_field` |
| `pitch` | the stored value, unchanged (int, Fraction or float); None means unpitched |
| `pitch_exact` | `Fraction(pitch)`: the exact value of the stored number, used as the comparison key |
| `pitch_kind` | `integer`, `rational`, `binary_float` or `none` |
| `pitch_estimated` | True when the source is an acoustic estimate (`source_type == "audio_wav"`) |

### 1.1 Numeric representation and bounds
- **Timing:**
  - A SoundEvent goes through the authoritative accessor `get_authoritative_exact_timing`. Other objects go through `Fraction(value)`, which is exact for int, Fraction and binary float.
  - Tick-only timing is rejected (`AmbiguousTimingError`).
  - Requirements: `0 ≤ start < end ≤ 10¹² ms`, finite, not boolean.
- **Pitch:**
  - `PITCH_MIN = −10 000 ≤ pitch_exact ≤ PITCH_MAX = 10 000`, finite, not boolean.
  - Bounds are checked on the exact `Fraction` **before** any float conversion, so huge integers are rejected with `NoteTimingError` rather than raising `OverflowError`.
- **Exactness:**
  - Integers and Fractions are compared exactly; for example, 181/3 ≠ 60.333…, and 60 + 10⁻²⁰ ≠ 60.
  - A float is compared by its exact binary value, so two equal floats always match, but 0.1 + 0.2 does not equal 0.3.
  - No tolerance and no rounding are applied anywhere in Stage 2b.
- **Violations:** sifters and discovery raise `NoteTimingError`; `diagnose_passage_timing` counts the note and never raises.

## 2. Streams

- **Definition.** A stream is the set of notes sharing `(row_id, voice_id)`, ordered chronologically by `(start, end, event_id, input_index)`. Position k in this order is the note's **chronological index**, and it is the index convention used for occurrences.
- **Monophonic.** A stream is monophonic iff, for every note, `start ≥ max(end of all earlier notes)`.
- **Polyphonic streams** (chords, or a sustained note under others in the same stream without voice information) are **not searched**: no melodic order is invented for them. They appear in `streams` with `status="polyphonic_unsupported"`, and every one of their events appears in `exclusions` for every method, with the reason.
- **Cross-stream matching.** Windows from different streams (rows or voices) are compared with each other.

## 3. Windows and features

A window `W = (s, i, n)` is the notes at positions `i … i+n−1` of stream `s`. It is reported as the half-open index range `[i, i+n)`. With onsets oₖ, ends eₖ and pitch keys pₖ, its derived features are (all exact):

| Feature | Definition | Length |
|---|---|---|
| P, pitches | (pᵢ, …, pᵢ₊ₙ₋₁) | n |
| D, durations | (eₖ − oₖ) | n |
| Q, inter-onset intervals | (oₖ₊₁ − oₖ), for k = i … i+n−2 | n−1 |
| I, pitch intervals | (pₖ₊₁ − pₖ) | n−1 |
| C, direction contour | (sign Iₖ) ∈ {−1, 0, +1} | n−1 |

Relative onsets are the partial sums of Q, and rests inside a window are represented by Q differing from D. Source information is never modified: features are computed from the normalized fields, and occurrences keep the event ids and exact pitches of their own notes.

## 4. Candidate methods (relations)

Two windows of equal length n are related under a method iff their signatures are **equal** (exactly):

| Method | Signature | Default | Interpretation |
|---|---|---|---|
| `exact` | (P, D, Q) | yes | The same absolute pitches, durations and relative onsets; any time displacement |
| `transposition` | (I, D, Q) | yes | Strict transposition: the same intervals and rhythm. Each occurrence records `transposition_semitones = pᵢ(occ) − pᵢ(ref)`, and its own absolute pitches are kept. |
| `interval_only` | (I) | optional | The same intervals, rhythm **not** compared; weaker than `transposition` |
| `rhythm` | (D, Q) | yes | Exact rhythm, independent of pitch. **Unpitched notes are allowed.** |
| `rhythm_proportional` | (D/d₀, Q/d₀), with d₀ the first duration | optional | Rhythm up to one exact scale factor, `scale_factor = d₀(occ)/d₀(ref)` (a Fraction). Scale 1 coincides with exact rhythm. |
| `contour` | (C) | yes | Direction sequence only, including repeated pitches (0). **Weak:** not evidence of melodic identity. |

- **The reference occurrence** for displacements and scales is the family's first occurrence in output order.
- **Pitch-based methods** (`exact`, `transposition`, `interval_only` and `contour`) search maximal runs of pitched notes. An unpitched note ends a run, and its events are listed in `exclusions` for those methods.
- **No timing tolerance exists.** Tolerance-based matching is not implemented. If it is added later, it must be a separately configured and separately evaluated method.

## 5. Families, occurrences, nesting and counting policy

- **Family.** For each method and each length n, from `min_length` (default 3) up to `max_length` (default: the longest searchable run), the windows are grouped by signature. A group is a **family** when its **independent occurrence count** is at least `min_occurrences` (default 2).
- **Independent occurrence count.** The maximum number of pairwise non-overlapping occurrences, computed per stream by the greedy earliest-end rule (optimal for equal-length intervals) and summed over streams.
- **Overlap policy.** All occurrences are listed, including overlapping ones, and each lists the positions it overlaps (`overlaps_with`). Overlapping occurrences do **not** count as independent repetitions. A signature with at least 2 raw occurrences but fewer than `min_occurrences` independent ones is reported in `rejected_candidates`, with its counts; it is never dropped silently.
- **Nesting.** A family F of length n is **nested** (`is_maximal=False`) when a family G of the same method and length n+1 has the same number of occurrences and contains every occurrence of F, one note longer on the left or the right. `nested_in` lists such parents.
  - Nested families are always computed. `include_nested=False` hides them from `families` but keeps them in `all_families`, with a note.
  - A shorter repeat with **more** occurrences than any extension is maximal in its own right.
- **Stricter-method equivalence.** `same_occurrences_as` lists the stricter methods that have a family with an identical occurrence set at the same length. For example, a rhythm family that is also an exact family has `("exact", "transposition")`.
- **Identity.** `family_key` is the method, the length and the canonical feature sequence in readable text, for example `exact|n=4|pitches=(60,62,64,60)|durations_ms=(250,250,250,500)|ioi_ms=(250,250,250)`. It is not a hash, and it is not the discovery order.
- **Stream keys.** The internal key is `(row, 0, "")` for an unspecified voice and `(row, 1, voice)` for a named voice, so they never collide. Sorting, independent-occurrence counting, nesting and stricter-method equivalence all use this key.
- **Determinism contract.**
  - **Order:** methods, then descending length, then `family_key`. Occurrences are ordered by stream key, then chronological start index.
  - **Chronological order within a stream** is `(start, end, pitch key, supplied event id, input position)`. Input position matters only for notes identical in all the earlier fields.
  - **Guarantee:** for the same notes (the same objects or equal content) in any input order and any row-dictionary order, the result is **equal**: families, occurrences, event keys and stream reports. Two fields are excluded from equality because they describe how the caller built the input: `EventRef.input_index` and `EventRef.source`.
  - **Event keys:**
    - a supplied non-empty `event_id` is kept exactly;
    - an anonymous event gets the generated key `anon|row=<row>|voice=<voice>|<chronological index>` (`event_id_generated=True`);
    - generated keys are stable under input reordering, but they are **not persistent identities**: inserting or removing an earlier note in the same stream changes them. Callers that need persistent identity must supply event ids.
  - **Duplicate keys** (a supplied id used twice, or a supplied id equal to a generated key): the default `duplicate_event_ids="disambiguate"` keeps every **unique** key unchanged and retires each duplicated key.
    1. All keys in the input are reserved first: unique, duplicated, supplied and generated.
    2. Visiting the duplicates in (row, voice, chronological) order, each receives `<id>#dupK`, where K ≥ 1 is the smallest value whose key is not yet reserved. The new key is reserved immediately.
    3. Every reported event key is therefore **globally unique within the result**, which the engine asserts. For example, `x, x, x#dup1` becomes `x#dup2, x#dup3, x#dup1`.

    The original key stays in `supplied_event_id`, the disambiguation is reported in `search_notes`, and nothing is discarded. `duplicate_event_ids="error"` raises `ValueError` instead.

## 6. Search limits and complexity

- **Window count.** Per method, the windows examined are `Σₙ Σ_runs max(0, len − n + 1) = O(L²)` for a run of L notes. Each signature costs O(n), so the worst case is **O(L³)** time and O(L²) signatures in memory per length.
- **The `max_windows` limit** (default 500 000 per method) is checked **before** each length. If the next length would exceed it, the search stops at a whole length, sets `search_complete=False`, and writes the searched and unsearched length ranges to `search_notes`. It never truncates silently.
- **Completeness has two levels.**
  - `search_complete` means every window within the **configured bounds** (`min_length`..`max_length`) was examined.
  - `unrestricted_search_complete` additionally means `max_length` excluded no searchable window.
  - `search_scope` lists, per method, `(method, min_length, max_length_searched, longest_searchable_run, status)`. The status is `complete`, `bounded_by_max_length` or `stopped_by_max_windows`.
- **Configuration validation.**
  - `min_length`, `min_occurrences` and `max_windows` (and `max_length` when given) must be `int`, not `bool` or `float`.
  - `include_nested` must be `bool`.
  - `methods` must be a non-empty sequence of known method names.
  - `duplicate_event_ids` must be `disambiguate` or `error`.
  - Anything else raises `ValueError`.
- **Recommended for long inputs:** `max_length`. Measured timings are in the Stage 2b report.

## 7. Output (`DiscoveryResult`)

| Field | Content |
|---|---|
| `config` | the `DiscoveryConfig` used |
| `families` / `all_families` | `RecurrenceFamily` objects (see §5) |
| `streams` | `StreamReport`: row, voice, note count, status, unpitched count, event ids in chronological order |
| `exclusions` | `(event_id, row, voice, method, reason)` for polyphonic and unpitched exclusions |
| `rejected_candidates` | overlapping-only signatures, with their raw and independent counts |
| `search_complete`, `unrestricted_search_complete`, `search_scope`, `search_notes`, `windows_examined` | search accounting (§6) |

Each `RecurrenceFamily` contains:
- `family_key`, `method`, `length` and `features`;
- `occurrences`;
- `independent_occurrence_count`, `is_maximal`, `nested_in` and `same_occurrences_as`;
- `parameters`: the displacements or scale factors;
- `interpretation` and `limitations`. The limitations cover overlaps, the weakness of contour matches, and acoustically estimated pitches.

**Lookup contract.** Every occurrence carries `events`: one `EventRef` per note, in chronological order, containing:
- `event_id` (the reported key), `supplied_event_id` and `event_id_generated`;
- `row_id`, `voice_id`, `chronological_index` and `input_index`;
- `exact_start_ms`/`exact_end_ms` and `timing_source`;
- `pitch` (the stored value), `pitch_exact`, `pitch_kind`, `pitch_source`, `pitch_estimated` and `label`;
- `source`, the **original object** passed in.

A downstream consumer therefore recovers each original event, its timing and its pitch provenance directly. `input_index` is the position in the caller's row list, and both it and `source` are excluded from equality.

Each `Occurrence` contains:
- the row and voice;
- `start_index`/`end_index` (half-open, chronological);
- the `event_ids`, `exact_start_ms`/`exact_end_ms` (Fractions) and `timing_sources`;
- the occurrence's own exact pitches;
- `transposition_semitones` or `scale_factor`, where applicable;
- `overlaps_with`.

## 8. Known limitations

- **Polyphonic streams without voice information are excluded entirely.** No voice-separation method is implemented.
- **Exact equality means performed recordings will rarely match.** For example, WAV-derived integer-ms timing with jitter is not matched. Tolerance-based or quantized matching would be a separate, explicitly evaluated method.
- **Contour, and short rhythm patterns, recur by chance.** On the passages built to contain no recurrence, contour produced 5 and 3 incidental families (Stage 2b report).
- **A maximal repeat may be longer than the intended phrase.** In "X Y X Y", the maximal exact repeat is "X Y", and X and Y appear as nested families. Deciding which level is "the phrase" is a musical judgement outside this method.
- **The search is cubic in the worst case.** Long passages need `max_length` or `max_windows`.
