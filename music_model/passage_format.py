"""Reproducible JSON musical passage format.

Provides deterministic serialization and deserialization between SongTimeline
models and JSON data files.

Supports:
- Song identification, title, tempo metadata, and notes.
- Temporary sound groups / rows with custom labels.
- Sound events with start_time_ms, end_time_ms, label, height, and attributes
  (pitch, velocity, channel, track, original ticks, etc.).
- Preserves exact millisecond intervals and object identity upon round-trip.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from music_model.song import SongTimeline
from music_model.sound_event import SoundEvent
from music_model.temporary_row import TemporaryRow

FORMAT_VERSION: str = "1.0"


def song_to_dict(song: SongTimeline) -> Dict[str, Any]:
    """Serialize a SongTimeline into a structured dictionary."""
    rows_data: List[Dict[str, Any]] = []
    for row in song.rows:
        rows_data.append({
            "row_id": row.row_id,
            "label": row.label,
        })

    events_data: List[Dict[str, Any]] = []
    for event in song.all_events:
        evt_dict: Dict[str, Any] = {
            "event_id": event.event_id,
            "row_id": event.row_id,
            "start_time_ms": event.start_time_ms,
            "end_time_ms": event.end_time_ms,
            "label": event.label,
        }
        if event.height is not None:
            evt_dict["height"] = event.height
        if event.sound_ref is not None:
            evt_dict["sound_ref"] = event.sound_ref
        if event.attributes:
            evt_dict["attributes"] = event.attributes
        events_data.append(evt_dict)

    # Sort events deterministically by start_time_ms, end_time_ms, event_id
    events_data.sort(key=lambda e: (e["start_time_ms"], e["end_time_ms"], e["event_id"]))

    return {
        "version": FORMAT_VERSION,
        "song_id": song.song_id,
        "title": song.title,
        "tempo_bpm": song.tempo_bpm,
        "description": song.description,
        "rows": rows_data,
        "events": events_data,
    }


def song_from_dict(data: Dict[str, Any]) -> SongTimeline:
    """Deserialize a structured dictionary into a SongTimeline.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict for passage data, got {type(data).__name__}")

    version = data.get("version", FORMAT_VERSION)
    song_id = data.get("song_id")
    if not song_id or not isinstance(song_id, str):
        raise ValueError(f"Missing or invalid 'song_id': {song_id!r}")

    title = data.get("title", song_id)
    tempo_bpm = data.get("tempo_bpm")
    description = data.get("description", "")

    song = SongTimeline(
        song_id=song_id,
        title=title,
        tempo_bpm=tempo_bpm,
        description=description,
    )

    # Register temporary rows
    rows_list = data.get("rows", [])
    if isinstance(rows_list, list):
        for r_entry in rows_list:
            if isinstance(r_entry, dict) and "row_id" in r_entry:
                r_id = r_entry["row_id"]
                r_lbl = r_entry.get("label", "")
                if song.get_row(r_id) is None:
                    song.create_row(row_id=r_id, label=r_lbl)

    # Register sound events
    events_list = data.get("events", [])
    if not isinstance(events_list, list):
        raise ValueError(f"'events' must be a list, got {type(events_list).__name__}")

    for idx, e_entry in enumerate(events_list):
        if not isinstance(e_entry, dict):
            raise ValueError(f"Event entry {idx} must be a dict, got {type(e_entry).__name__}")

        e_id = e_entry.get("event_id")
        r_id = e_entry.get("row_id")
        s_ms = e_entry.get("start_time_ms")
        e_ms = e_entry.get("end_time_ms")

        if not e_id or not isinstance(e_id, str):
            raise ValueError(f"Event {idx}: missing or invalid 'event_id'")
        if not r_id or not isinstance(r_id, str):
            raise ValueError(f"Event {idx}: missing or invalid 'row_id'")
        if s_ms is None or e_ms is None:
            raise ValueError(f"Event {idx} ({e_id}): missing start_time_ms or end_time_ms")

        lbl = e_entry.get("label", "")
        h = e_entry.get("height")
        s_ref = e_entry.get("sound_ref")
        attrs = e_entry.get("attributes", {})

        # Ensure row exists
        if song.get_row(r_id) is None:
            song.create_row(row_id=r_id)

        event = SoundEvent(
            event_id=e_id,
            row_id=r_id,
            start_time_ms=s_ms,
            end_time_ms=e_ms,
            label=lbl,
            sound_ref=s_ref,
            attributes=dict(attrs) if isinstance(attrs, dict) else {},
            height=h,
        )
        song.add_event(event)

    return song


def song_to_json(song: SongTimeline, indent: int = 2) -> str:
    """Serialize a SongTimeline into a JSON string."""
    return json.dumps(song_to_dict(song), indent=indent)


def song_from_json(json_str: str) -> SongTimeline:
    """Deserialize a JSON string into a SongTimeline."""
    data = json.loads(json_str)
    return song_from_dict(data)


def save_song_to_file(song: SongTimeline, filepath: str) -> None:
    """Save a SongTimeline to a JSON file on disk."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(song_to_json(song, indent=2))


def load_song_from_file(filepath: str) -> SongTimeline:
    """Load a SongTimeline from a JSON file on disk."""
    with open(filepath, "r", encoding="utf-8") as f:
        return song_from_json(f.read())
