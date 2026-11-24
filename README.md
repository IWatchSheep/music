# Music as Linked Sound Rows and Variable Time Columns

An experimental Python project for studying how groups of sounds create a musical timeline and a continuous, measurable musical pattern.

## The author's idea — rewritten for clarity

*This section restates the author's ideas in clearer language for programmers and AI assistants. It is an interpretation, not a replacement for the original statements in the following section.*

### 1. Music as rows of sound and columns of time

Music contains many sounds and repeating loops. I imagine organizing these sounds into **rows** and organizing time into **columns**. Each row holds a sound or a related group of sounds, including chunks that repeat. The rows can overlap because different groups may play at the same time.

### 2. Temporary sound groups and connections between groups

Some rows exist only while a particular musical group is playing. When one group ends and another begins, a sound or musical idea may continue between them. That continuing element connects the groups. I want the system to represent both the sounds unique to each temporary group and the sounds or relationships shared across groups.

### 3. The constant row is a musical identity, not necessarily a repeating recording

What remains recognizable across groups may be a **feeling or musical style**—for example, the suspense associated with *Jaws* or the powerful, sweeping character of *Ride of the Valkyries*. It does not have to be one identical note, loop, or instrument playing all the time. The connections among the changing sounds may create that recognizable musical identity.

### 4. The constant row emerges from the temporary rows

I do not want to impose the constant row first. I think the sounds in the temporary rows **produce** it. By measuring how groups enter, overlap, repeat, connect, and move from low to high, we might be able to calculate one continuous line that describes the larger musical movement.

### 5. A hypothesis about straight and curved musical movement

I suspect that some traditional musical passages move from low to high more directly, while passages combining several musical styles may stay at a lower level longer or move through more intermediate stages. On a graph, I imagine the first kind sometimes looking more linear and the second more curved. I think of examples such as *Stairway to Heaven*, the Beach Boys, orchestral music, and modern rap, but I do not yet know how to measure the difference. **These genre comparisons are questions for the experiment, not facts the program should assume.**

### 6. The temporary rows determine the size and number of time columns

The columns should **not** all have a fixed duration. Groups of sounds determine where useful time boundaries occur. A short, direct musical event may need a narrow column. A longer combination of overlapping sound events may span a larger interval or create several linked columns. We should count the columns, measure their actual durations, and count which temporary rows contribute to the low-to-high movement.

### 7. Every sound links a beginning column to an ending column

A sound is held between its starting and ending boundaries. Different sounds can start and end at different times, so their linked intervals overlap. Combining the boundaries from the temporary rows gives the music a shared column structure. The durations and contributions of those combined columns then determine how the constant row is measured.

### 8. What I want to discover

I want to find a mathematical rule that starts with **temporary groups of real sounds**, derives their **linked, variable-width time columns**, and calculates the **constant musical row** from them. Then I want to test whether the resulting line, and its low-to-high transitions, reveal meaningful differences between musical passages and styles. I do not yet know the correct musical measurements or combination rule; discovering them is the purpose of the project.

## Original explanation — author's own words

The following eight statements are preserved **verbatim and in the order originally given**, including the author's wording, spelling, and punctuation. They are the source ideas for the technical model below. The comparisons between musical styles are hypotheses to be investigated, not established findings.

### Original statement 1

> with music if you use rows and columns. you have loops of sound that's repeated. then you have other sound that's repeated. they all fit into the time the sound is played. if the time the sound is played is split into columns then the row can hold the chunks of sound

### Original statement 2

> i was thinking of constant columns to show the time the music is played. then filling in the columns with sound that belongs in groups. then the single group goes through the row and columns and then it goes to a different group and there might be a single column that stays in the two groups maybe in a separate row where like math we join rows the row with the constant sound between groups stays in the columns with sound each loop and the next row is the group filling the columns with sound unique to the group. then you could have the row with the sound in every row be constant but the group be temporary for the time the group is played.

### Original statement 3

> the constant sound could be the style or feeling scary or happy jaws in water or valkyries in the sky sound, not just a constant sound in every row. that binds the rows together.

### Original statement 4

> i think the constant row is created by the temporary rows. the temporary rows create a linear graph line when the music is not blended with other kinds of musical styles but when its joined with multiple musical styles the constant graph line changes from linear to curved. this is why modern music is curved constant line but traditional rock music like led zeplin stairway to heaven or the beach boys or old fashioned music like that has a linear constant line and modern rap and music has a curved constant line. but to see how the musical rows that are temporary function to create this difference in the constant musical row idk how to do yet.

### Original statement 5

> i think music that's able to go low to high is traditional, but a music that has to go low stay low on the time line to go high is a mixture of musical styles. counting columns and rows the traditional music can go low row to single column but a mixture of musical style has to go several columns to go as low. then you count the temporary rows to find the column count on how row to column low to high is measured.

### Original statement 6

> classical music ride of  valkyries has the sound of low to high. the orchestrator swinging his stick would show that sound easily i think.

### Original statement 7

> the columns of time from low row to high row is made by the temporary rows. but the number of columns is not static its able to be changed by the temporary rows to fit the sound of the temporary rows. look at the temporary rows music is groups of sound that fit together, these create the columns that the row that is constant goes from low to high and because the columns are changed by the temporary rows one classical traditional column might be smaller than a mixed column made from modern music.

### Original statement 8

> the sound in the row is made from linked columns the beginning column the ending column hold the sound the columns fit the temporary rows together. these columns fit together to create the constant row column size.

## Simple explanation — what this project should do

**Start with sounds, not a pre-made grid.** Each sound has a beginning and an ending, and belongs to a temporary musical row or group. Gather the beginnings and endings of all the sounds to build time columns whose widths are determined by the music itself. Keep track of which rows are active in each column. Then calculate a continuous **constant row** that represents some measurable aspect of how the combined music changes over time.

For the first experiment, the constant row can simply count how many groups are active in each interval. That demonstrates the mechanics, but it is **not yet** a measurement of musical feeling or style. Later, test pitch movement, sound intensity, rhythm, and other features to discover which—if any—help express the author's idea of musical movement from low to high and straight versus curved progression.

**Instructions to another AI or programmer:** Preserve the original statements above, treat the rewritten section as an interpretation, and do not assume the proposed genre distinctions are already proven. Build the smallest testable program first: sound intervals → sorted boundaries → variable-width columns → active temporary rows → calculated constant row → graph. Verify each step with small examples before analyzing recordings.

The following technical sections provide one proposed implementation and questions still to investigate.

## The idea

Music contains temporary groups of related sounds. Each sound begins at one point in time and ends at another. Those beginnings and endings **link time columns**. When all the sound groups are considered together, their linked boundaries determine the columns needed to describe the complete piece of music.

The columns are **not required to have a fixed width**. A short musical event can create a narrow column; a longer interval without a new beginning or ending can create a wider one. A sound can continue through multiple columns without being restarted or copied.

From these temporary rows and their shared timeline, the program calculates a **constant row**: a continuous sequence of measurements describing the combined music as it changes from low to high, or along other musical dimensions. Here, *constant* means that this derived row persists across the whole analyzed passage—not that its value, pitch, or sound remains constant.

The proposed structure is:

```text
Temporary rows of related sounds
              |
              v
Each sound links a start time to an end time
              |
              v
Collect and order the linked boundaries
              |
              v
Variable-width time columns emerge
              |
              v
Measure contributions of temporary rows in each interval
              |
              v
A continuous derived ('constant') musical row
```

## Research question

Can the timing and overlap of temporary sound groups help explain the differences we hear between different kinds of musical passages?

One initial hypothesis is that some passages make rapid low-to-high transitions across short musical intervals, whereas passages combining several musical styles may take longer or follow a more gradual, curved path. Classical orchestral music (for example, the dramatic rises in Wagner's *Ride of the Valkyries*), older rock, and contemporary music offer possible material for comparison.

**This is a hypothesis, not an established distinction between genres.** Classical and traditional music can also have long, complex transitions; contemporary music can have abrupt ones. The program must measure actual passages without assuming a genre's graph shape in advance.

## Vocabulary

| Term | Meaning |
| --- | --- |
| **Sound event** | A note, recorded audio chunk, or other event with a beginning and ending time. |
| **Temporary row** | A related group or sequence of sound events that is active only for part of the passage. |
| **Boundary** | A time when a sound event begins or ends. |
| **Time column** | An interval between two consecutive boundaries. Its duration may differ from other columns. |
| **Linked columns** | The start and end boundaries connected by a sound event. The sound occupies the interval between them. |
| **Constant row** | A continuous, calculated musical measurement covering the analyzed passage, derived from temporary rows. |
| **Low / high** | A measurement to be defined for an experiment: pitch, loudness, energy, register, texture, or another property. These are not interchangeable. |

## Example: sound groups create their own columns

Suppose three temporary rows contain these events, with time in seconds:

| Temporary row | Start | End | Musical contribution (example) |
| --- | ---: | ---: | --- |
| Sound A | 0 | 3 | Sustained low sound |
| Sound B | 1 | 5 | Another sound joins |
| Sound C | 2 | 4 | A higher layer appears |

The combined boundary times are:

```text
0, 1, 2, 3, 4, 5 seconds
```

Those boundaries create five columns, without choosing their widths ahead of time:

| Time column | Active temporary rows | Number of active rows |
| --- | --- | ---: |
| [0, 1) | A | 1 |
| [1, 2) | A, B | 2 |
| [2, 3) | A, B, C | 3 |
| [3, 4) | B, C | 2 |
| [4, 5) | B | 1 |

The resulting count series is `1, 2, 3, 2, 1`. This is a **first demonstration of combining rows**, not a claim that the count is the music's pitch or emotional character. Sound events can cross several column boundaries without their underlying recordings being split.

For a variable-width demonstration, change the event boundaries to `0, 0.25, 1.5, 3, 5`. The resulting columns then have durations of `0.25`, `1.25`, `1.5`, and `2` seconds.

## The mathematical model

### 1. Represent sounds as intervals

For sound event `i`, store:

```text
sound_i = (start_i, end_i, musical_features_i, temporary_row_id)
```

Require `start_i < end_i`. Keep every sound's original interval even when other sounds enter or leave.

### 2. Derive the variable time columns

Collect every start and end time, sort the unique boundaries, and call them:

```text
t_0 < t_1 < ... < t_m
```

Column `j` is the half-open interval `[t_j, t_(j+1))`, with duration:

```text
duration_j = t_(j+1) - t_j
```

A sound is active in a column when its interval covers that column. For a first implementation, the column boundaries come from **all** event starts and ends. Later experiments can merge nearby boundaries or recognize higher-level musical groups.

### 3. Build a constant row from temporary rows

Let `R_i(j)` describe the contribution of temporary row `i` in column `j`. An initial calculation is:

```text
C_j = sum(R_i(j) for every temporary row i)
```

If each active row contributes `1`, `C_j` counts active rows. More musical versions might use pitch register, energy, note-onset density, timbral features, or weighted combinations. Different measurements should be kept as **separate constant rows** until there is a justified way to combine them.

### 4. Measure changes against actual time

Because column durations are variable, count and slope are different measurements:

```text
number_of_columns = m
transition_duration = end_time - start_time
```

For adjacent measurements, a time-aware rate of change is:

```text
slope_j = (C_(j+1) - C_j) / (center_(j+1) - center_j)
```

where `center_j` is the midpoint of column `j`. Changing slopes can indicate a curved trajectory. A simple count of active sounds is a stepwise series; any smooth curve fitted to it is a **visualization or model**, not the raw sound itself.

## First Python experiment: no music files required

Begin with synthetic sound events so the algorithm can be verified independently of audio analysis.

Suggested initial data structure:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SoundEvent:
    row: str
    start: float
    end: float
    label: str


events = [
    SoundEvent("A", 0.0, 3.0, "low sustained sound"),
    SoundEvent("B", 1.0, 5.0, "second layer"),
    SoundEvent("C", 2.0, 4.0, "higher layer"),
]
```

Build the program in small verified milestones:

1. **Event intervals.** Load events; reject negative durations and invalid times; print each row's start and end.
2. **Boundary extraction.** Collect, sort, and deduplicate start/end times; derive the time columns and their widths.
3. **Row-to-column mapping.** Report which temporary rows are active in each interval, including overlaps and continuing sounds.
4. **First constant row.** Calculate the number of active temporary rows in each column and graph it against actual time.
5. **Low-to-high measurement.** Define *one* low/high dimension (such as pitch register or energy), calculate it from synthetic values, and compare fast versus gradual transitions.
6. **Real musical data.** Only after the synthetic tests pass, analyze a short permitted recording or a user-created sequence. Extract sound-event boundaries or approximations and compare them to the synthetic model.
7. **Comparative study.** Analyze multiple passages with the same measurement method and report column widths, transition times, row overlap, and graph shapes. Do not assign genre labels based on curve shape alone.

## Important tests

- One event creates exactly one column covering its interval.
- Two adjacent events produce the correct shared boundary.
- Overlapping events create all required boundaries and active-row combinations.
- Long sounds remain active across intermediate boundaries introduced by other sounds.
- Changing event duration changes column widths without changing unrelated event data.
- Simultaneous starts or ends do not create zero-width columns.
- Empty input returns an empty timeline, not an invented graph.
- Constant-row measurements agree with hand-calculated examples.
- Results use actual elapsed time when comparing transitions; uneven column widths must not be treated as equal.
- Repeated runs with identical input produce identical results.

When using floating-point timestamps, adopt a documented tolerance or an integer time unit (for example, milliseconds) so nearly identical boundaries do not create accidental tiny columns.

## Questions to investigate later

- What makes several sounds belong to the same temporary group: matching rhythm, harmony, phrase, timbre, or a user-defined label?
- Should overlapping groups share boundaries, or should a higher-level group define larger columns that contain smaller event columns?
- Which measurement best represents the perceived low-to-high motion: pitch, intensity, energy, or a combination?
- Does a row that recurs later count as one group with gaps or several temporary groups linked by identity?
- Do differences in column durations and row overlap correlate with perceived musical style across a representative set of passages?
- Can a conductor's gestures provide useful event or phrase boundaries without assuming baton height directly equals pitch?

## Project principles

1. **Sounds determine the timeline.** Do not impose equal-width analysis columns in the core event model.
2. **Events are linked intervals.** Store beginnings and endings; do not copy a sound for every column it spans.
3. **Temporary rows create the constant row.** Derive continuous measurements from their contributions instead of inventing a constant track.
4. **Define every measurement.** Low/high must refer to a specified measurable property.
5. **Separate evidence from hypotheses.** Do not assume that traditional music is linear or mixed-style music is curved.
6. **Test small examples first.** Preserve expected outputs and regression tests as the project grows.
7. **Keep source recordings and generated analyses separate.** Only include audio that you have permission to use.

## Initial scope

This repository begins as a **mathematical music-structure experiment**, not a full music editor, audio player, or genre classifier. The first goal is to prove that sound events can generate variable-width columns and that temporary rows can be combined into a meaningful, inspectable measurement over time.

**Status:** Design proposal — implementation not yet started.
