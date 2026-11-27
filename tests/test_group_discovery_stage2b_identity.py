"""JOB-04 Stage 2b identity-contract tests (ChatGPT Stage 2b audit, sections 4-6).

Stream identity, anonymous-event identity and input-order determinism, the public event-reference
contract, configuration validation, and bounded versus unrestricted search completeness.
Each test was run against the pre-correction engine (negative baseline recorded in the evidence).
"""

from __future__ import annotations

import unittest
from fractions import Fraction
from types import SimpleNamespace as NS

from music_model.recurrence_discovery import discover_sound_groups


def note(s, e, p, eid=None, voice=None):
    kw = {"start_ms": s, "end_ms": e, "pitch": p}
    if eid is not None:
        kw["event_id"] = eid
    if voice is not None:
        kw["voice"] = voice
    return NS(**kw)


def phrase_twice(prefix=None, voice=None, gap=1000):
    out = []
    for rep in range(2):
        for k, p in enumerate((60, 62, 64)):
            t = rep * gap + k * 100
            out.append(note(t, t + 100, p, None if prefix is None else f"{prefix}{rep}{k}", voice))
    return out


class TestStreamIdentity(unittest.TestCase):
    def test_auditor_reproduction_empty_voice_is_unspecified(self):
        notes = [note(i * 10, i * 10 + 5, 60 + i, f"{v!s}-{i}", v) for v in (None, "") for i in range(3)]
        r = discover_sound_groups({"r": notes}, methods=("exact",))
        # Policy: '' means unspecified voice (= None).  The six notes form ONE stream; it contains
        # simultaneous notes, so it is polyphonic and is reported, not separated by invention.
        self.assertEqual([(s.voice_id, s.status, s.note_count) for s in r.streams], [(None, "polyphonic_unsupported", 6)])
        self.assertEqual(r.families, ())

    def test_whitespace_voice_is_unspecified(self):
        r = discover_sound_groups({"r": phrase_twice("a", voice="  ")}, methods=("exact",))
        self.assertEqual([(s.voice_id, s.status) for s in r.streams], [(None, "monophonic")])
        self.assertEqual(len(r.families), 1)

    def test_unspecified_and_named_voices_never_share_a_key(self):
        # A real voice named "" cannot exist (normalized to unspecified); a voice named "None" is distinct from None.
        a = phrase_twice("u")                       # unspecified voice, 2 occurrences
        b = phrase_twice("n", voice="None")         # voice literally named "None", 2 occurrences
        r = discover_sound_groups({"r": a + b}, methods=("exact",))
        self.assertEqual([s.voice_id for s in r.streams], [None, "None"])
        # Select the 3-note phrase family (identical streams also yield longer cross-stream families).
        f = [x for x in r.families if x.length == 3 and x.occurrences[0].pitches == (60, 62, 64)][0]
        self.assertEqual(f.independent_occurrence_count, 4)
        self.assertEqual(sorted((o.voice_id or "<unspecified>", o.start_index) for o in f.occurrences),
                         [("<unspecified>", 0), ("<unspecified>", 3), ("None", 0), ("None", 3)])


class TestIdentityContract(unittest.TestCase):
    def test_anonymous_ids_invariant_under_input_reversal(self):
        notes = phrase_twice()                      # no event_id supplied
        r1 = discover_sound_groups({"r": notes}, methods=("exact",))
        r2 = discover_sound_groups({"r": list(reversed(notes))}, methods=("exact",))
        self.assertEqual([o.event_ids for o in r1.families[0].occurrences],
                         [o.event_ids for o in r2.families[0].occurrences])
        self.assertEqual(r1.families, r2.families)
        self.assertEqual(r1.streams, r2.streams)

    def test_generated_ids_are_flagged_and_supplied_ids_preserved(self):
        mixed = phrase_twice("s")
        mixed[1] = note(mixed[1].start_ms, mixed[1].end_ms, mixed[1].pitch)          # one anonymous event
        r = discover_sound_groups({"r": mixed}, methods=("exact",))
        refs = r.families[0].occurrences[0].events
        self.assertEqual([(x.event_id_generated, x.event_id.startswith("s")) for x in refs],
                         [(False, True), (True, False), (False, True)])

    def test_duplicate_supplied_ids_rejected_when_configured(self):
        notes = phrase_twice("d")
        notes[4] = note(notes[4].start_ms, notes[4].end_ms, notes[4].pitch, "d00")    # duplicate of notes[0]
        with self.assertRaises(ValueError):
            discover_sound_groups({"r": notes}, methods=("exact",), duplicate_event_ids="error")

    def test_duplicate_ids_disambiguated_by_default(self):
        # Default 'disambiguate' (not 'error') keeps the existing Stage 2b tests, whose fixtures reuse ids,
        # unchanged; nothing is discarded and the disambiguation is reported.
        notes = phrase_twice("d")
        notes[4] = note(notes[4].start_ms, notes[4].end_ms, notes[4].pitch, "d00")
        r = discover_sound_groups({"r": notes}, methods=("exact",))
        ids = [x.event_id for o in r.families[0].occurrences for x in o.events]
        self.assertEqual(len(ids), len(set(ids)))                                       # unique keys
        self.assertTrue(any("duplicate event id" in n for n in r.search_notes))
        dup = [x for o in r.families[0].occurrences for x in o.events if x.supplied_event_id == "d00"]
        self.assertEqual(len(dup), 2)                                                   # nothing discarded


class TestPublicEventReferences(unittest.TestCase):
    def test_occurrence_events_recover_source_and_provenance(self):
        notes = phrase_twice("e")
        notes[0].pitch = Fraction(181, 3)
        notes[3].pitch = Fraction(181, 3)
        r = discover_sound_groups({"r": notes}, methods=("exact",))
        o = r.families[0].occurrences[0]
        ref = o.events[0]
        self.assertIs(ref.source, notes[0])
        self.assertEqual((ref.chronological_index, ref.input_index), (0, 0))
        self.assertEqual((ref.exact_start_ms, ref.exact_end_ms, ref.timing_source), (Fraction(0), Fraction(100), "ms_field"))
        self.assertEqual((ref.pitch, ref.pitch_exact, ref.pitch_kind, ref.pitch_source, ref.pitch_estimated),
                         (Fraction(181, 3), Fraction(181, 3), "rational", "pitch", False))
        self.assertEqual(tuple(x.event_id for x in o.events), o.event_ids)

    def test_input_index_excluded_from_result_equality(self):
        notes = phrase_twice("e")
        r1 = discover_sound_groups({"r": notes}, methods=("exact",))
        r2 = discover_sound_groups({"r": list(reversed(notes))}, methods=("exact",))
        self.assertNotEqual(r1.families[0].occurrences[0].events[0].input_index,
                            r2.families[0].occurrences[0].events[0].input_index)
        self.assertEqual(r1.families, r2.families)


class TestConfigAndSearchScope(unittest.TestCase):
    def test_malformed_numeric_parameters_rejected(self):
        for bad in ({"min_length": 3.5}, {"min_length": True}, {"max_length": 4.0}, {"max_windows": "100"},
                    {"min_occurrences": 2.0}, {"methods": ()}, {"methods": ("exact", 3)},
                    {"duplicate_event_ids": "ignore"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                discover_sound_groups({"r": []}, **bad)

    def test_bounded_versus_unrestricted_completeness(self):
        notes = phrase_twice("b")
        full = discover_sound_groups({"r": notes}, methods=("exact",))
        self.assertTrue(full.search_complete and full.unrestricted_search_complete)
        bounded = discover_sound_groups({"r": notes}, methods=("exact",), max_length=3)
        self.assertTrue(bounded.search_complete)                       # complete within configured bounds
        self.assertFalse(bounded.unrestricted_search_complete)         # longer windows exist but were excluded
        scope = dict((m, rest) for m, *rest in bounded.search_scope)
        self.assertEqual(scope["exact"][:3], [3, 3, 6])                # min, max searched, longest run


if __name__ == "__main__":
    unittest.main()
