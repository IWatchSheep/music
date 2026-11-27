"""JOB-04 Stage 2b: global uniqueness of reported event identifiers (ChatGPT Revision 2 audit).

Disambiguation must reserve every original, generated and newly assigned key before allocating a
'#dupK' suffix; unique supplied ids are kept; supplied ids are preserved in EventRef.supplied_event_id.
"""

from __future__ import annotations

import random
import unittest
from types import SimpleNamespace as NS

from music_model.recurrence_discovery import discover_sound_groups


def notes_with_ids(ids, row_offset=0, voice=None, pitches=(60, 61, 62)):
    out = []
    for i, e in enumerate(ids):
        kw = {"start_ms": i * 10, "end_ms": i * 10 + 5, "pitch": pitches[i % len(pitches)]}
        if e is not None:
            kw["event_id"] = e
        if voice is not None:
            kw["voice"] = voice
        out.append(NS(**kw))
    return out


def all_ids(result):
    return [e for s in result.streams for e in s.event_ids]


def supplied_by_reported(result):
    """Map reported key -> supplied id, from every occurrence EventRef (exact method, all families)."""
    m = {}
    for f in result.all_families:
        for o in f.occurrences:
            for x in o.events:
                m[x.event_id] = (x.supplied_event_id, x.event_id_generated)
    return m


class TestGlobalIdentifierUniqueness(unittest.TestCase):
    def assertUnique(self, result):
        ids = all_ids(result)
        self.assertEqual(len(ids), len(set(ids)), ids)

    def test_auditor_reproduction_existing_suffix_reserved(self):
        r = discover_sound_groups({"r": notes_with_ids(["x", "x", "x#dup1", "a", "b", "c"])}, methods=("exact",))
        self.assertUnique(r)
        self.assertEqual(r.streams[0].event_ids, ("x#dup2", "x#dup3", "x#dup1", "a", "b", "c"))

    def test_multiple_occupied_suffixes(self):
        ids = ["y", "y", "y#dup1", "y#dup2", "y#dup3", "q"]
        r = discover_sound_groups({"r": notes_with_ids(ids)}, methods=("exact",))
        self.assertUnique(r)
        self.assertEqual(r.streams[0].event_ids, ("y#dup4", "y#dup5", "y#dup1", "y#dup2", "y#dup3", "q"))

    def test_collision_with_generated_anonymous_identifier(self):
        gen0 = "anon|row='r'|voice=None|0"
        notes = notes_with_ids([None, "a", gen0, "b", "c", "d"])   # supplied id equals the generated key of note 0
        r = discover_sound_groups({"r": notes}, methods=("exact",))
        self.assertUnique(r)
        self.assertNotIn(gen0, all_ids(r))                          # both colliding keys were replaced
        self.assertEqual(sum(1 for e in all_ids(r) if e.startswith(gen0 + "#dup")), 2)

    def test_reversed_input_gives_identical_identifiers(self):
        ids = ["x", "x", "x#dup1", None, "x#dup2", "a"]
        a = discover_sound_groups({"r": notes_with_ids(ids)}, methods=("exact",))
        b = discover_sound_groups({"r": list(reversed(notes_with_ids(ids)))}, methods=("exact",))
        self.assertUnique(a)
        self.assertEqual(all_ids(a), all_ids(b))
        self.assertEqual(a.all_families, b.all_families)

    def test_collisions_across_rows_and_voices(self):
        rows = {
            "r1": notes_with_ids(["z", "z#dup1", "k"], voice="1") + notes_with_ids(["z", "m", "n"], voice="2"),
            "r2": notes_with_ids(["z", "z#dup2", "p"]),
        }
        r = discover_sound_groups(rows, methods=("exact",))
        self.assertUnique(r)
        ids = all_ids(r)
        for kept in ("z#dup1", "z#dup2", "k", "m", "n", "p"):     # unique supplied ids are preserved
            self.assertIn(kept, ids)
        self.assertNotIn("z", ids)
        self.assertEqual(sorted(e for e in ids if e.startswith("z#dup") and e not in ("z#dup1", "z#dup2")),
                         ["z#dup3", "z#dup4", "z#dup5"])

    def test_supplied_ids_preserved_in_event_refs(self):
        notes = notes_with_ids(["x", "x", "x#dup1", "x", "x", "x#dup1"], pitches=(60, 61, 62))
        r = discover_sound_groups({"r": notes}, methods=("exact",))
        self.assertUnique(r)
        refs = supplied_by_reported(r)
        self.assertTrue(refs)
        self.assertTrue(all(sup in ("x", "x#dup1") and not gen for sup, gen in refs.values()))

    def test_strict_mode_rejects_each_collision_kind(self):
        cases = [
            {"r": notes_with_ids(["x", "x", "x#dup1"])},
            {"r": notes_with_ids([None, "anon|row='r'|voice=None|0", "b"])},
            {"r1": notes_with_ids(["z", "a", "b"]), "r2": notes_with_ids(["z", "c", "d"])},
        ]
        for rows in cases:
            with self.assertRaises(ValueError):
                discover_sound_groups(rows, methods=("exact",), duplicate_event_ids="error")

    def test_randomized_uniqueness_property(self):
        rng = random.Random(20261127)
        pool = ["x", "x#dup1", "x#dup2", "x#dup1#dup1", "y", "anon|row='r'|voice=None|0", None]
        for _ in range(200):
            ids = [rng.choice(pool) for _ in range(rng.randint(1, 9))]
            r = discover_sound_groups({"r": notes_with_ids(ids)}, methods=("exact",))
            self.assertUnique(r)
            supplied = [e for e in ids if e is not None]
            uniques = {e for e in supplied if supplied.count(e) == 1}
            gens = {f"anon|row='r'|voice=None|{k}" for k in range(len(ids))}
            for e in uniques - gens:                             # a unique, non-colliding supplied id is kept
                self.assertIn(e, all_ids(r))


if __name__ == "__main__":
    unittest.main()
