# Music Project: Sound Groups, Fundamental Columns, and Musical Expression

> **A Collaborative Reference for the Author, ChatGPT, and Google Antigravity**  
> **Repository:** `IWatchSheep/music`  
> **Baseline Checkpoint:** `ad3a9d3`  
> **Calculator Reference Checkpoint:** `17be078d` (unmodified, 100% read-only)

---

## Section 1 — Project Introduction

This project investigates the author's theory of musical architecture: sound groups occupy temporary rows, and the organization of those rows translates into the constant Row 1.

**Current author-approved design direction (Statements 28 and 29):**

1. Row 2 has its own uniform column width, fitted to the entire set of sounds in Row 2.
2. Row 3 independently has its own uniform column width, fitted to the entire set of sounds in Row 3. Its width may differ from Row 2's width.
3. Rows 2 and 3 fit together using their respective uniform column structures, preserving both structures and the original musical timing.
4. The result of fitting the two rows together translates into constant Row 1. The mathematical translation rule and resulting Row 1 column structure remain open research questions; no greatest-common-divisor, boundary-union, or single uniform Row 1 rule is assumed.
5. A finer shared reference grid can be used to express timing, as in Statement 18, but it must not replace the independently fitted column structure of either temporary row.
6. In the author's expressive hypothesis, Rows 2 and 3 represent the journey (1 + 1), while Row 1 represents the goal or result (= 2), associated with the terminal low-to-high sound described in *Ride of the Valkyries*. Statement 23 locates that sound at the tail end of the action.

The relationship of this architecture to musical identity, breathing and speech, linear versus curved expression, and Boolean outcomes remains a research hypothesis. The published implementation is a historical baseline; it has not yet been shown to implement Statement 29.

---

## Section 2 — The Author's 29 Original Statements

The following 29 statements are drawn directly from the authoritative source file `music.txt`. Each statement is presented in three parts:
- **A. Original Statement — Author's Exact Words:** Copied verbatim without alterations, omissions, or spelling corrections.
- **B. Grammar-Corrected Version:** Rewritten for grammatical clarity while strictly preserving the author's meaning and terminology.
- **C. Proposed Interpretation — Awaiting Joint Review:** A newly written explanation distinguishing verified mathematics from hypotheses, with tentative ideas explicitly labeled as guesses.

---

### Statement 1

#### A. Original Statement — Author's Exact Words
> "with music if you use rows and columns. you have loops of sound that's repeated. then you have other sound that's repeated. they all fit into the time the sound is played. if the time the sound is played is split into columns then the row can hold the chunks of sound"

#### B. Grammar-Corrected Version
> With music, if you use rows and columns, you have loops of sound that repeat, alongside other sounds that repeat. All of them fit into the duration during which the sound is played. If the playback duration is divided into columns, then each row can hold those chunks of sound.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author introduces the foundational visual and conceptual framework of the project: organizing musical audio along a two-dimensional grid of rows and columns.
- **Role of Rows & Columns:** Horizontal rows represent distinct instruments, voices, or recurring loops. Vertical columns divide physical playback time into measurable slices. Chunks of sound (sound groups) are placed within rows across these time columns.
- **Status:** Established structural concept. Implemented in the timeline engine and visual canvas.

---

### Statement 2

#### A. Original Statement — Author's Exact Words
> "i was thinking of constant columns to show the time the music is played. then filling in the columns with sound that belongs in groups. then the single group goes through the row and columns and then it goes to a different group and there might be a single column that stays in the two groups maybe in a separate row where like math we join rows the row with the constant sound between groups stays in the columns with sound each loop and the next row is the group filling the columns with sound unique to the group. then you could have the row with the sound in every row be constant but the group be temporary for the time the group is played."

#### B. Grammar-Corrected Version
> I was thinking of constant columns to show the time during which music is played, and then filling those columns with sounds that belong in groups. A single group moves through the row and columns, and then transitions to a different group. A single column might stay constant between two groups—perhaps in a separate row where, like in mathematics, we join rows together. The row holding the constant sound between groups remains in the columns across each loop, while the next row contains groups filling the columns with sounds unique to that group. Thus, the row with sound in every column remains constant, while the groups are temporary for the duration they are played.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author distinguishes between two distinct kinds of rows: **temporary rows** that contain finite, changing groups of sound, and a **constant row** that persists across the piece and mathematically joins the rows together.
- **Role of Rows & Columns:** Temporary rows (Rows 2, 3, etc.) hold localized sound events that begin and end. The constant row (Row 1) remains active across all columns, unifying the separate temporary groups through a process analogous to mathematical row addition.
- **Status:** Established architectural foundation. Implemented as Row 1 (constant carrier) and Rows 2+ (temporary voice rows).

---

### Statement 3

#### A. Original Statement — Author's Exact Words
> "the constant sound could be the style or feeling scary or happy jaws in water or valkyries in the sky sound, not just a constant sound in every row. that binds the rows together."

#### B. Grammar-Corrected Version
> The constant sound could be the style or feeling—scary or happy, Jaws in water or Valkyries in the sky sound—not just a constant sound in every row. That binds the rows together.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author clarifies that the "constant sound" in Row 1 does not need to be a monotonous drone or static pitch. Instead, it can represent the thematic identity, mood, or overarching expressive feeling that binds the entire composition together (citing the menacing motif of *Jaws* in water or the soaring energy of *Valkyries* in the sky).
- **Hypothesis vs. Mathematics:** The structural binding is mathematical (boundary union); the thematic/emotional binding is an aesthetic quality expressed through that structure.
- **Status:** Established conceptual interpretation.

---

### Statement 4

#### A. Original Statement — Author's Exact Words
> "i think the constant row is created by the temporary rows. the temporary rows create a linear graph line when the music is not blended with other kinds of musical styles but when its joined with multiple musical styles the constant graph line changes from linear to curved. this is why modern music is curved constant line but traditional rock music like led zeplin stairway to heaven or the beach boys or old fashioned music like that has a linear constant line and modern rap and music has a curved constant line. but to see how the musical rows that are temporary function to create this difference in the constant musical row idk how to do yet."

#### B. Grammar-Corrected Version
> I think the constant row is created by the temporary rows. These temporary rows create a linear graph line when the music is not blended with other kinds of musical styles; however, when multiple styles join together, the constant graph line shifts from linear to curved. This is why modern music has a curved constant line, whereas traditional rock music (such as Led Zeppelin's *Stairway to Heaven*, the Beach Boys, or older music) has a linear constant line, and modern rap and blended music have a curved constant line. Exactly how the temporary musical rows function to create this difference in the constant musical row, I do not know how to do yet.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The constant row is emergent: it is created from the interaction of the temporary rows. The author introduces the hypothesis that unblended traditional styles exhibit a "linear" progression, while multi-genre modern music exhibits a "curved" progression.
- **Author's Later Clarification:** In Statement 27, the author clarifies that "linear vs. curved" is not simply a curve drawn through pitch values, but is created by different column sizes (group widths) expressing an action.
- **Status:** Core research hypothesis. Awaiting formal classification benchmarks.

---

### Statement 5

#### A. Original Statement — Author's Exact Words
> "i think music that's able to go low to high is traditional, but a music that has to go low stay low on the time line to go high is a mixture of musical styles. counting columns and rows the traditional music can go low row to single column but a mixture of musical style has to go several columns to go as low. then you count the temporary rows to find the column count on how row to column low to high is measured."

#### B. Grammar-Corrected Version
> I think music that is able to move directly from low to high is traditional, whereas music that must stay low on the timeline before rising represents a mixture of musical styles. Counting columns and rows, traditional music can move from a low row across a single column, but a mixture of musical styles must traverse several columns to reach that depth. You then count the temporary rows to determine the column count for how the row-to-column progression from low to high is measured.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author associates the speed and trajectory of low-to-high progression with musical genre organization. Direct progression across few columns characterizes traditional forms, whereas lingering in the lower register across multiple columns indicates hybrid or modern styles.
- **I Guess:** *I guess the author is observing that traditional pieces often resolve gestures with direct, prompt transitions, whereas complex modern arrangements dwell in prolonged bass grooves or transitional vamps before making a melodic rise.*
- **Status:** Exploratory metric hypothesis.

---

### Statement 6

#### A. Original Statement — Author's Exact Words
> "classical music ride of  valkyries has the sound of low to high. the orchestrator swinging his stick would show that sound easily i think."

#### B. Grammar-Corrected Version
> Classical music, such as *Ride of the Valkyries*, has that low-to-high sound. A conductor swinging their baton would illustrate that sound easily, I think.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** *Ride of the Valkyries* serves as the author's primary musical archetype for clear, physical, directional progression from low to high. The visual motion of the conductor's baton mirrors the physical ascent of the musical gesture.
- **Status:** Illustrative reference piece.

---

### Statement 7

#### A. Original Statement — Author's Exact Words
> "the columns of time from low row to high row is made by the temporary rows. but the number of columns is not static its able to be changed by the temporary rows to fit the sound of the temporary rows. look at the temporary rows music is groups of sound that fit together, these create the columns that the row that is constant goes from low to high and because the columns are changed by the temporary rows one classical traditional column might be smaller than a mixed column made from modern music."

#### B. Grammar-Corrected Version
> The columns of time from low row to high row are created by the temporary rows. The number of columns is not static; it can be changed by the temporary rows to fit their sound. Looking at the temporary rows, music consists of groups of sound that fit together. These create the columns through which the constant row progresses from low to high. Because columns are refitted by the temporary rows, a classical or traditional column might be smaller than a mixed column in modern music.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** Column boundaries are dynamic rather than rigid. They are derived from the sound groups present in the temporary rows. As groups change length, the resulting column boundaries adapt.
- **Status:** Verified mathematical property of progressive refitting. Implemented in `music_model/timeline.py`.

---

### Statement 8

#### A. Original Statement — Author's Exact Words
> "the sound in the row is made from linked columns the beginning column the ending column hold the sound the columns fit the temporary rows together. these columns fit together to create the constant row column size."

#### B. Grammar-Corrected Version
> The sound within a row is formed from linked columns: the beginning column and ending column contain the sound, fitting the temporary rows together. These columns combine to establish the column dimensions of the constant row.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** Every sound event has an onset boundary (beginning column) and an offset boundary (ending column). The collection of these intervals across temporary rows defines the composite column widths of Row 1.
- **Status:** Verified mathematical foundation.

---

### Statement 9

#### A. Original Statement — Author's Exact Words
> "you should ask google antigravity for help coming up with a plan. first there is the temporary sounds that fit columns and these columns fit the constant row and constant row is compared to constant row to find the column different with less = linear and more = curved graph. but before all that we need to use the rows and columns and for that maybe we need to reuse the calculator project. to get the gui and rows and columns. just add a musical variation on it to plug in music to the rows and columns."

#### B. Grammar-Corrected Version
> You should ask Google Antigravity for help coming up with a plan. First, there are the temporary sounds that fit columns, and these columns fit the constant row. Constant row is then compared to constant row to find the column difference, with less meaning a linear graph and more meaning a curved graph. But before all that, we need to use the rows and columns, and for that maybe we need to reuse the calculator project to get the GUI and rows and columns, just adding a musical variation on it to plug in music to the rows and columns.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author outlines the project development plan: first build a stable GUI grid adapted from the calculator architecture to visualize rows and columns, then implement progressive group refitting, and finally analyze linear vs. curved differences.
- **Repository Boundary:** The calculator project (`C:\Users\I_wat\PycharmProjects\calculator`) is strictly protected at commit `17be078d` and is 100% read-only. Architecture concepts were adapted cleanly in the music project without modifying the calculator codebase.
- **Status:** Completed development milestone.

---

### Statement 10

#### A. Original Statement — Author's Exact Words
> "i think the rows are supposed to be many many columns wide and in those many columns we fill in the sounds hear from the music playing. the idea is the number of columns functions with the musical sheet music. i look at the rows now and they are not many columns and the columns are not aligned."

#### B. Grammar-Corrected Version
> I think the rows are supposed to be many, many columns wide, and across those many columns we fill in the sounds heard from the music playing. The idea is that the number of columns corresponds with the musical sheet music. Looking at the rows now, they do not have many columns, and the columns are not aligned.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author observed that an early prototype had too few columns and suffered from misaligned vertical boundaries. Musical passages require a fine-grained grid spanning dozens or hundreds of columns aligned across all rows.
- **Status:** Resolved in Milestone 3 by the implementation of unified master column time alignments in `music_gui/timeline_canvas.py`.

---

### Statement 11

#### A. Original Statement — Author's Exact Words
> "the row 2 makes columns fit the music group. row 3 makes the columns refit the musical group. then row 1 fits rows 1 and 2 musical group. music 2 repeats the process making row 1 a different number of columns. in both music songs the columns fit rows 1, 2, 3, but not across music songs. this way you can measure the linear and curved by seeing the traditional vs the non-traditional/modern, to see the column number reasoning the columns fit together across constant rows but they don't share the linear or curved structure."

#### B. Grammar-Corrected Version
> Row 2 creates columns to fit its musical group. Row 3 then refits the columns to fit its own musical group. Then Row 1 fits the musical groups of Rows 2 and 3 [clarified by the author in Statements 28 and 29; original statement retained]. Song 2 repeats the process, giving its Row 1 a different number of columns. In both songs, the columns fit Rows 1, 2, and 3, but not across different songs. This way you can measure linear versus curved by seeing traditional versus non-traditional/modern music, to see the column number reasoning where columns fit together across constant rows, but they do not share the same linear or curved structure.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author specifies two vital principles:
  1. **Progressive Refitting:** Groups are added row by row, with the master grid updating progressively.
  2. **Song Independence:** Each song possesses its own authentic column system derived from its own notes; grids are never shared or forced across different songs.
- **Author clarification:** Statements 28 and 29 resolve the intended order: Rows 2 and 3 first fit together using their independently established column structures, and the result translates into Row 1.
- **Status:** Mathematically verified and automated in `tests/test_song_timeline.py`.

---

### Statement 12

#### A. Original Statement — Author's Exact Words
> "the idea is row 1 is constant and goes into different rows as row addition so the columns blend music together. then column numbers in rows 2 and 3 etc setup the column size for row 1. then to show the difference between modern and classical traditional rock music, vs modern music you measure to see if the columns in the modern are more to connect to the old. the curved has more on the lower row hence it has more columns connecting to the row vs the traditional that goes in linear."

#### B. Grammar-Corrected Version
> The idea is that Row 1 is constant and goes into different rows through row addition, so the columns blend the music together. Then the column numbers in Rows 2, 3, and so on set up the column size for Row 1. Then, to show the difference between modern and classical traditional rock music versus modern music, you measure to see whether the columns in the modern music are more numerous to connect to the old. The curved music has more on the lower row; hence, it has more columns connecting to the row, compared to traditional music, which proceeds in a linear way.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** Row 1 connects to temporary rows through mathematical union ("row addition"). The author suggests that pieces with more activity or events on lower rows generate more boundary transitions, creating more composite columns in Row 1.
- **I Guess:** *I guess the author is observing that when lower rows contain more frequent transitions or events, they generate a denser set of connecting column boundaries in Row 1.*
- **Status:** Established structural concept.

---

### Statement 13

#### A. Original Statement — Author's Exact Words
> "its the meaning of linear which grows from the row and column and is formed from the groups of sounds fitting columns together to form the structure of the row 1 that is the sound carried from row to row."

#### B. Grammar-Corrected Version
> It is the meaning of linearity that emerges from the rows and columns, formed by sound groups fitting columns together to establish the structure of Row 1, which represents the sound carried from row to row.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** I guess linearity may emerge from the way the independently fitted row structures combine. This remains untested.
- **Status:** Core theoretical principle.

---

### Statement 14

#### A. Original Statement — Author's Exact Words
> "the sound in a group is distinct from a different sound in a group but they share something from the row 1 that changes the music somehow. i think the fact that row one can change the music to go low to high. without row 1 the groups don't have a unique id to go from low to high like ride of the valkyries.you have one part of ride of the valkyries and another but there is no low to high and then the song is lost but with low to high you have the song."

#### B. Grammar-Corrected Version
> The sound in one group is distinct from the sound in another group, but they share an underlying element from Row 1 that shapes the music. I think it is the fact that Row 1 enables the music to progress from low to high. Without Row 1, the individual groups lack a cohesive identity to move from low to high as in *Ride of the Valkyries*. You can have one part of *Ride of the Valkyries* and another part, but without that low-to-high progression, the identity of the song is lost. With the low-to-high progression, you have the song.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** I guess the groups may share musical identity. Statements 23, 28 and 29 associate Row 1 with the terminal result, rather than necessarily a gradual rise throughout the journey.
- **Status:** Established conceptual definition of Row 1's carrier role.

---

### Statement 15

#### A. Original Statement — Author's Exact Words
> "the sound before is low its like the whirring sound imaging a duck running on water then as the duck takes flight that is the high sound."

#### B. Grammar-Corrected Version
> The sound before is low, like a whirring noise—imagine a duck running across water—and then, as the duck takes flight, that is the high sound.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author provides a vivid physical metaphor for developmental progression:
  1. *Low Whirring:* Grounded, continuous rhythmic pattering (running on water).
  2. *High Flight:* Airborne lift-off and release into the upper register.
- **Status:** Primary physical analogy for musical progression in Row 1.

---

### Statement 16

#### A. Original Statement — Author's Exact Words
> "it looks like the columns are different sizes on different rows. and not all the same size and fit into the music they describe. the columns fit the entire group of sound in the song and then multiple groups fit together and this is how they form the contstant row 1 that blends into the rows 2 and 3 etc by being able to go from low to high sound similar to a duck running on water then with a whirrring foot on water sound to flapping in the air and flying sound similar to the ride of the valkyries sound."

#### B. Grammar-Corrected Version
> It looks as though the columns have different widths on different rows, rather than sharing a consistent size that fits the music they describe. The columns should fit the entire group of sounds in the song, and multiple groups then fit together. This is how they form the constant Row 1, which blends into Rows 2, 3, and onward by moving from low to high—similar to a duck running across water with a whirring foot-on-water sound before flapping into the air and taking flight, like the sound in *Ride of the Valkyries*.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author identifies that visual groups appear with different physical widths across rows. These multi-column groups fit together to shape Row 1, which carries the duck-flight progression.
- **Status:** Clarified and mathematically formalized in Statements 17 and 18.

---

### Statement 17

#### A. Original Statement — Author's Exact Words
> "look at the difference in column size for master column width. i think your not using a row and column you can fill in with the difference column size. counting column in row like base counting system 0 to 9, over and over to make one column width. and repeating this to make different songs column width for all columns the same size. instead i think your using one column and trying to resize it."

#### B. Grammar-Corrected Version
> Look at the difference in column size for the master column width. I think you are not using a row and column system that you can fill in with the different column sizes. Count columns in a row like a base counting system from 0 to 9, over and over, to make one column width, and repeat this to make different songs' column width, with all columns being the same size. Instead, I think you are using one column and trying to resize it.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** A major mathematical turning point. The author corrects the assistants: the program must not dynamically stretch or resize the fundamental grid cells. Instead, a song has a single, fixed **fundamental column width** ($u$). Time is partitioned into equal reference cells labeled cyclically `0` through `9`. Different group sizes are built by combining multiple fundamental cells, not by resizing individual cells.
- **Status:** Core mathematical axiom of the project.

---

### Statement 18

#### A. Original Statement — Author's Exact Words
> "did you rewrite your ideas before where the width was different to now the width is the same? the idea is the width is what groups together left to right in the row to fit the songs group sound, then you take that row of columns and a new row with different column width but both rows share the same fundamental column size making the two columns width. you have one row be a width column like 4 and another row with a width column of 3 and then you take the size 4 column and make it to size 3 column but that might not fit the sound so you make it work so the two columns share a same column design but they fit the song group that is a different length. then these multiple rows make up the top row the constant row column width that fits all rows. does that make sense?"

#### B. Grammar-Corrected Version
> Did you rewrite your earlier ideas, where widths were different, so that now all widths are forced to be identical? The idea is that fundamental cells group together from left to right within a row to accommodate a song's group sound. When you take that row and add a new row with a different group width, both rows still share the same fundamental column size. For instance, one row has a group width of 4 units, and another row has a group width of 3 units. Forcing a size-4 group into a size-3 group would distort the sound; instead, both rows share the same fundamental column design while fitting groups of different lengths. These multiple rows then determine the column structure of the top constant Row 1, which reconciles all rows. Does that make sense?

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The definitive reconciliation of uniform reference cells and variable sound groups:
  1. **Shared Base Grid:** All rows share the same fundamental unit $u$ (e.g., $100\text{ ms}$ or sixteenth note).
  2. **Multi-Unit Groups:** Row 2 uses groups of $4u$; Row 3 uses groups of $3u$. Neither row's notes are distorted or forced into the other's size.
  3. **Row 1 Composite Union:** The boundaries of both rows combine in Row 1 ($B = \{0, 3, 4, 6, 8, 9, 12\}$), creating composite segments of widths $[3u, 1u, 2u, 2u, 1u, 3u]$.
- **Status:** Verified mathematical proof in `verify_group_units.py` and automated unit tests.

---

### Statement 19

#### A. Original Statement — Author's Exact Words
> "fyi i think sound especially music fits into intervals the person can speak and breath. if you measure the time of breath and speaking and estimate how that is being conveyed to the listener you might be able to group sound better."

#### B. Grammar-Corrected Version
> For your information, I think sound—especially music—fits into intervals during which a person can speak and breathe. If you measure the duration of breathing and speaking, and estimate how that is conveyed to the listener, you might be able to group sounds more effectively.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** I guess breathing and speech cadence could help explain grouping and perception; the author proposes this as a research direction.
- **Scientific Boundary:** Detecting rests or gaps in a constructed musical passage is a programmatic heuristic. It tests against designer-specified score reference boundaries, but does not constitute direct measurement of biological breathing or independent human phrase perception.
- **Status:** Exploratory grouping hypothesis.

---

### Statement 20

#### A. Original Statement — Author's Exact Words
> "if you imagine the breathing speech time fitting in a doll going from point a to point b this might be the duration of the music being expressed as a group."

#### B. Grammar-Corrected Version
> If you imagine the duration of breathing and speech fitting into an animated doll moving from Point A to Point B, this might represent the duration of the music being expressed as a group.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author links breath/speech duration to physical character motion: a musical sound group corresponds to the time required for an animated character ("doll") to execute an action from Point A to Point B.
- **I Guess:** *I guess the author is proposing that musical phrasing functions like an animation storyboard: each sound group is scaled to give a character enough temporal space to complete a physical gesture or deliver a line of dialogue.*
- **Status:** Foundational concept for the Storyboard Benchmark.

---

### Statement 21

#### A. Original Statement — Author's Exact Words
> "yes, as dolls move and are animated they are given a band to play music to them to enhance the effect being displayed. if you can find the doll you can be sure the music that portrays them is near there and ends when the doll has move to point b or done what they set out to do maybe have a conversation."

#### B. Grammar-Corrected Version
> Yes, as dolls move and are animated, an accompanying band plays music for them to enhance the action being displayed. If you identify the doll, you can be sure the music portraying them is closely aligned, ending when the doll has moved to Point B or accomplished what they set out to do, such as having a conversation.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author elaborates the "musical band" metaphor: distinct musical voices accompany distinct animated characters. The musical accompaniment tracks the character's purposeful action and concludes when that action (walking, handing an object, speaking) reaches its destination.
- **Status:** Conceptual basis for multi-row conversational benchmarks.

---

### Statement 22

#### A. Original Statement — Author's Exact Words
> "maybe the low to high sound marks the end of the doll going from point a to b or the music playing for the doll there. then there is a association with low to high being in the constant row 1, and then rows 2 and 3 might be point a to point b that fixes row 1."

#### B. Grammar-Corrected Version
> Maybe the low-to-high sound marks the conclusion of the doll moving from Point A to Point B, or the end of the music playing for the doll at that point. There is an association with low-to-high motion existing in the constant Row 1, while Rows 2 and 3 might represent the journey from Point A to Point B that establishes Row 1.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author begins connecting the low-to-high sound with action completion: rather than being a continuous slope, the low-to-high sound signals the arrival at Point B. Rows 2 and 3 represent the ongoing journey, while Row 1 captures the completed result.
- **Status:** Refined and clarified immediately in Statement 23.

---

### Statement 23

#### A. Original Statement — Author's Exact Words
> "no, the low to high is at the tail end of the music. it signifies the end of the music playing for the doll. then you start over at the group a sound playing into group b sound playing that blends into the end of the doll action that is the low to high sound. if you see a animal bite a itch like a cat they jerk at the itch they nibble on it then they are done. like that."

#### B. Grammar-Corrected Version
> No, the low-to-high sound occurs at the tail end of the music. It signifies the conclusion of the music playing for the doll. You then start over: the Group A sound plays and transitions into the Group B sound, which blends into the completion of the doll's action marked by that low-to-high sound. For example, when an animal reacts to an itch, such as a cat: it jerks toward the itch, nibbles on it, and then it is done. It is just like that.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** A crucial author correction. The assistants had previously guessed that low-to-high was a gradual rise spanning the whole movement. The author explicitly rejects this:
  1. Earlier groups (Group A, Group B) accompany the unfolding action (e.g., cat jerking, nibbling).
  2. The low-to-high gesture is a **localized terminal punctuation mark** at the very tail end, signaling completion of the action.
  3. The cycle then restarts for the next action.
- **Status:** Author-verified correction. Governs terminal gesture detection.

---

### Statement 24

#### A. Original Statement — Author's Exact Words
> "is the music in rows 2 and 3 repeating to show motion from point a to point b. 1 + 1 is 2. the logic translates to sound. the 2 is low to high, the 1 and 1 is what leads to the high of 2 low to 2 at = 2. if not 1 and 1 then a + b = 2 the high from low to high is 2. make up something for a and b."

#### B. Grammar-Corrected Version
> Is the music in Rows 2 and 3 repeating to show motion from Point A to Point B? $1 + 1 = 2$. The logic translates to sound. The '2' is the low-to-high sound; the '1 + 1' is what leads to the high of 2 (from low to 2 at '= 2'). If not $1 + 1$, then $a + b = 2$, where the high from low to high is 2. Make up something for $a$ and $b$.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author raises an exploratory question connecting the developmental rows with an arithmetic metaphor: $1 + 1 = 2$ (or $a + b = 2$).
  - The operands ($1$ and $1$, or $a$ and $b$) represent the developmental sound groups in Rows 2 and 3 accompanying the motion from Point A toward Point B.
  - The sum ($= 2$) represents the terminal low-to-high resolution that marks the arrival at Point B.
- **I Guess:** *I guess the author's suggestion to "make up something for a and b" invites us to test multi-stage actions (such as two steps in a task or two turns in a dialogue) that precede the terminal resolution.*
- **Status:** Exploratory research hypothesis.

---

### Statement 25

#### A. Original Statement — Author's Exact Words
> "the sound of 1 and 1 is a journey from point a to point b. the = 2 is the fruit the harvest the win of getting to point b. it is a bool = true. but if its bool = true then some sad songs could also be bool = false to show getting to point b results in a sad note. like the aww sound."

#### B. Grammar-Corrected Version
> The sound of $1 + 1$ is a journey from Point A to Point B. The '= 2' is the fruit, the harvest, the win of getting to Point B. It is a Boolean `true`. But if it is a Boolean `true`, then some sad songs could also be a Boolean `false` to show that getting to Point B results in a sad note, like the 'aww' sound.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author introduces Boolean outcomes for musical endings:
  - Reaching Point B successfully represents the fruit, harvest, or win (`bool = true`).
  - Reaching Point B with failure, loss, or disappointment results in a sad note (`bool = false`, like an "aww" sound).
- **Scientific Boundary:** The musical mechanism expressing `bool = false` (whether a descending gesture, harmonic suspension, or unexpected pause) is an empirical hypothesis to be tested, not a predetermined rule. A successful action could also have a solemn expression, and an unsuccessful action could have an energetic one.
- **Status:** Exploratory narrative hypothesis.

---

### Statement 26

#### A. Original Statement — Author's Exact Words
> "maybe the good ending is linear low to high and the sad is curved low to high. you can start a track race equal to everyone but end way behind and be curved low to high at the end but linear at the start and during training."

#### B. Grammar-Corrected Version
> Maybe the good ending is a linear low-to-high, and the sad ending is a curved low-to-high. You can start a track race equal to everyone, but end up way behind and be curved low-to-high at the end, even if you were linear at the start and during training.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Explanation:** The author uses a track race analogy to explore how outcomes relate to linear versus curved trajectories. A runner starts equal to the field, but finishes far behind, resulting in a curved low-to-high shape at the end.
- **I Guess:** *I guess the runner falling behind corresponds to pacing hesitation or dwelling in transitional columns, causing the progression to stretch out rather than moving directly to the finish.*
- **Status:** Exploratory narrative hypothesis.

---

### Statement 27

#### A. Original Statement — Author's Exact Words
> "the idea was the same thing was being expressed but the point a and b created different column sizes that shows the linear from curved low to high."

#### B. Grammar-Corrected Version
> The idea was that the same thing was being expressed, but Point A and Point B created different column sizes, which shows the linear from curved low-to-high.

#### C. Proposed Interpretation — Awaiting Joint Review
- **Later author clarification:** Read this historical interpretation in light of Statements 28 and 29. Independently fitted uniform row columns must be preserved, and their translation into Row 1 remains open. Any incompatible earlier interpretation is superseded.
- **Explanation:** The author's definitive clarification of "linear vs. curved." It does **not** refer to a line drawn through pitch centroids. Instead:
  - The same underlying action and musical motive can be expressed with different group-column organizations.
  - I guess regular group widths might be perceived as direct pacing; this is not established.
  - I guess uneven group durations might affect perceived pacing; Statement 29 does not permit arbitrary changes in the uniform column size within a temporary row.
- **Scientific Boundary:** Whether listeners actually perceive regular group widths as "linear" and irregular widths as "curved" or "sad" is a hypothesis to be evaluated through independent listening trials.
- **Status:** Foundational hypothesis for the Stage 2 Column-Width Benchmark.

---

### Statement 28

#### A. Original Statement — Author's Exact Words
> "row 2 and 3 fit together first using columns that divide into each row music group evenly. the columns uniform in size fit the row 2, then row 3 then they merge so the uniform column size fits rows 2 and 3 then this uniform column size goes into row 1 the constant row size. the row 2 and 3 is the point a and b the 1 plus 1 then the row 1 is the goal target the sum of 1 and 1 it is the low to high crescendo heard in ride of the valkyries song."

#### B. Grammar-Corrected Version
> Rows 2 and 3 fit together first, using columns that divide evenly into each row's musical groups. The uniform-sized columns fit Row 2, then Row 3. They merge so that the uniform column size fits both rows, and this uniform column size then goes into Row 1, the constant row. Rows 2 and 3 represent Points A and B, the 1 plus 1. Row 1 represents the goal or target, the sum of 1 and 1: the low-to-high crescendo heard in *Ride of the Valkyries*.

#### C. Proposed Interpretation — Read with Statement 29
- The author establishes the order: fit the temporary rows together first, then translate into Row 1. Statement 29 clarifies that each temporary row first has its own uniform column size, not one size imposed on both rows.
- The journey/result analogy is the author's research hypothesis. The exact mathematical translation remains unresolved.

---

### Statement 29

#### A. Original Statement — Author's Exact Words
> "no, i said the rows 2 and 3 each have their own unique set of uniform columns that fit the entire set of sounds in the row. not that the column size is random large or small in the rows 2 and 3 and row 1 fits a uniform column size to fit both rows. the rows 2 and 3 fit together first using each of their uniform column size then this translates into the row 1."

#### B. Grammar-Corrected Version
> No, I said that Rows 2 and 3 each have their own unique set of uniform columns that fit the entire set of sounds in the row. I did not mean that the column sizes in Rows 2 and 3 vary randomly between large and small, or that Row 1 uses a uniform column size to fit both rows. Rows 2 and 3 fit together first, using their respective uniform column sizes, and this then translates into Row 1.

#### C. Proposed Interpretation — ChatGPT Agreement, Awaiting Antigravity Review
- Each temporary row has a uniform column width fitted to the entire set of sounds in that row. The widths may differ between rows, but are not arbitrarily varied within either row.
- Fit Rows 2 and 3 together using their original uniform column structures before deriving Row 1. Do not replace either structure with a shared finest subdivision or assume Row 1 imposes one common uniform width.
- I guess a mathematical representation that retains each row's width, boundaries, and timing while expressing their interaction could help investigate the translation into Row 1. No specific translation algorithm is agreed yet.
- Statement 28's journey/result relationship remains the author's expressive hypothesis. Statement 29 supersedes incompatible earlier assistant interpretations.

---

## Section 3 — Shared Mathematical Model

### Current design — independent uniform row structures

For illustration only, let Row 2 have column width 4u and Row 3 have column width 3u over a duration of 12u. Here u is a timing reference, not the column width of either row.

```
Row 2: [   4u   ][   4u   ][   4u   ]
Row 3: [  3u  ][  3u  ][  3u  ][  3u  ]
                Fit together
                      |
                      v
Row 1: Translation result (structure not yet determined)
```

The fitting operation must preserve the two independently established column systems. How to derive the width of each row from its entire set of sounds, how to reconcile the rows, and how that reconciliation translates into Row 1 remain open tasks. No particular Row 1 subdivision is established by this example.

### Historical mathematical reference — not the Statement 29 translation

The earlier boundary-union calculation below is valid arithmetic and was reported as verified in the baseline code. It is retained for comparison, not as the agreed definition of the new Row 1 architecture.

```
[VERIFIED STRUCTURAL BOUNDARY MODEL]
Historical boundary union: [ Seg 1 (3u) ][S2(1u)][ Seg 3 (2u) ][ Seg 4 (2u) ][S5(1u)][ Seg 6 (3u) ]
--------------------------------------------------------------------------------
Fundamental Grid:         [ 0 ][ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ][ 9 ][ 0 ][ 1 ] (12 EQUAL CELLS)
--------------------------------------------------------------------------------
Row 2 (Regular 4u Groups):[======= Group 1 (4u) =======][======= Group 2 (4u) =======][======= Group 3 (4u) =======]
Row 3 (Regular 3u Groups):[==== Grp A (3u) ====][==== Grp B (3u) ====][==== Grp C (3u) ====][==== Grp D (3u) ====]

[CONCEPTUAL ILLUSTRATION — EXPRESSIVE LAYER HYPOTHESIS]
Expressive Journey Arc:   [-------- Journey: 1 + 1 (Developmental Groups) --------][= 2: Tail-End Resolution]
(Note: Expressive arc and terminal placement are conceptual hypotheses, not mathematical axioms of Row 1 segments.)
```

### 1. Fundamental Unit ($u$) as a Reference Framework
- Within any given song, time is referenced against equal-duration intervals of duration $u \in \mathbb{R}^+$ (e.g., $100.0\text{ ms}$).
- These fundamental cells serve as analytical and visual reference columns, not physically indivisible musical quanta.
- Fundamental cells are indexed with discrete coordinates $n \in \{0, 1, \dots, N-1\}$, representing continuous intervals $[n \cdot u, (n+1) \cdot u)$.
- Display coordinates cycle through `0, 1, 2, ..., 9, 0, 1...` ($L(n) = n \pmod{10}$).
- Reference cells remain uniform. They are not a replacement for each temporary row’s independently fitted uniform columns.

### 2. Multi-Unit and Fractional Sound Groups in Temporary Rows
- Temporary rows (Rows 2, 3, etc.) contain sound groups spanning fundamental units.
- Sound groups may span whole integer multiples of fundamental units (e.g., Row 2 spanning $4u = 400\text{ ms}$, Row 3 spanning $3u = 300\text{ ms}$).
- Sound groups may also span exact fractional units (such as $0.50u = 50\text{ ms}$ or $7.50u = 750\text{ ms}$) whenever authentic musical phrasing or off-grid note intervals occur.
- Groups fit their musical material without distorting notes or forcing one row’s width onto another. These examples concern reference units, not a prescription for the row-fitting algorithm.

### 3. Historical Composite Boundary Union
- In the historical model, composite boundaries ($B$) were derived from the mathematical union of all start and end boundaries across all temporary rows:
  $$B = \bigcup_{r \ge 2} \left( \bigcup_{i} \{ \text{start}(G_{r, i}), \text{end}(G_{r, i}) \} \right)$$
- For regular 4-unit groups in Row 2 and regular 3-unit groups in Row 3 over a 12-unit interval:
  - Row 2 boundaries: $\{0, 4, 8, 12\}$
  - Row 3 boundaries: $\{0, 3, 6, 9, 12\}$
  - Historical composite boundaries: $\{0, 3, 4, 6, 8, 9, 12\}$
  - Historical composite segment widths: $[3u, 1u, 2u, 2u, 1u, 3u]$
- **Important Mathematical Observation (Counterexample to Uniformity):** Even when individual contributing rows have perfectly regular groups ($[4, 4, 4]$ and $[3, 3, 3, 3]$), Row 1 is composite and non-uniform ($[3, 1, 2, 2, 1, 3]$) due to the phase mismatch between periods of 4 and 3.

### 4. Preservation of Source Musical Timing
- Original MIDI ticks and rational tempo maps (`Fraction`) are preserved as exact source ground truth.
- Continuous floating-point timestamps are derived coordinates; floating-point millisecond representations are maintained without destructive grid snapping.
- Notes that start or end between fundamental cell borders retain their authentic continuous timings.

---

## Section 4 — Research Hypotheses

The following questions represent active research hypotheses. They are investigated through controlled experiments but are **not** assumed to be proven axioms:

1. **Physiological and Narrative Grouping:** Musical groups reflect the natural duration of human breathing and speech cadence, scaled to provide the time needed for animated characters to complete actions from Point A to Point B.
2. **The Terminal Low-to-High Gesture:** The low-to-high sound is a localized terminal punctuation mark at the tail end of an action, signaling arrival at Point B.
3. **The $1 + 1 = 2$ Arithmetic of Song:** Rows 2 and 3 represent the developmental journey ($1 + 1$ or $a + b$), while the terminal gesture represents the outcome ($= 2$).
4. **Boolean Outcomes:** Successful arrival at Point B evaluates to `bool = true` (the harvest/win), whereas disappointment evaluates to `bool = false` (a sad note or "aww" sound). The musical manifestation of these outcomes is an open question, not a fixed pitch rule.
5. **Column-Width-Defined Pacing (Linear vs. Curved):**
   - *Regular Contributing Rows:* I guess uniform group widths may influence perceived pacing.
   - *Irregular Contributing Rows:* I guess differences in group durations may influence perceived pacing. The within-row column size remains uniform under Statement 29.
   - *Separation of Mathematics from Emotion:* Mathematical column variance is measured objectively; whether listeners hear variance as "sad," "curved," or "hesitant" is tested independently through listening trials.

---

## Section 5 — Experiments and Verification

All implementations are subject to strict automated verification and zero-regression standards:

### 1. Completed Baseline Modules (Historical Checkpoint `ad3a9d3`)
- `music_model/timeline.py`: Dynamic column derivation and active row tracking.
- `music_model/midi_importer.py`: Pure-Python SMF Type 0/1 MIDI parser with rational tempo map arithmetic.
- `music_model/passage_format.py`: Lossless JSON passage interchange format.
- `music_gui/timeline_canvas.py`: Multi-row Tkinter visual canvas with unified master column alignment.
- **Automated Tests:** 91 baseline tests passing.

### 2. Milestone 4A: Fundamental Column Units (Verified)
- `verify_group_units.py`: Standalone mathematical proof modeling Statement 18:
  - 12 uniform fundamental cells with cyclic `0–9` indexing.
  - Multi-unit sound groups ($4u$ and $3u$).
  - Derived composite Row 1 segments ($[3u, 1u, 2u, 2u, 1u, 3u]$).
  - Preservation of continuous off-grid note timings.

### 3. Milestone 5A: Sifter Discovery Benchmark (locally reported; independent source review pending)
- `music_model/group_discovery.py` & `verify_group_discovery.py`:
  - **4 Candidate Sifters:** Sifter A (Breath/Rest), Sifter B (Motoric Rhythm), Sifter C (Melodic Contour), Sifter D (Cross-Row Hand-off).
  - **2 Controls:** Control 1 (Fixed-Width Slicing) and Control 2 (Fair 100-seed Monte Carlo Random Baseline matching exact sifter boundary counts).
  - **Maximum-Cardinality 1-to-1 Bipartite Matching:** Augmenting-path algorithm provably finding maximum true positives without greedy blocking.
  - **Internal Boundary Benchmark:** Evaluates strictly internal boundaries ($0 < t < T$), eliminating artificial score inflation from endpoint matching:
    - *Passage 1 (Synthetic Orchestral Duck Flight, $N=6$ internal refs, $\tau = \pm 60\text{ ms}$):* Sifter B (Motoric) had internal precision $50.0\%$, recall $66.7\%$, $F_1 = 0.571$ vs. 100-seed random baseline $0.125 \pm 0.119$.
    - *Passage 2 (Contrapuntal Non-Symmetric Phrasing, $N=6$ internal refs, $\tau = \pm 60\text{ ms}$):* Sifter A (Breath/Rest) had internal precision $100.0\%$, recall $100.0\%$, $F_1 = 1.000$ vs. 100-seed random baseline $0.217 \pm 0.158$.
    - *Passage 3 (Negative Control, $N=0$ internal refs):* Sifters A, B, C, D discovered 0 false internal boundaries (passage-level zero false alarms, $FP = 0$), while Fixed-Width (400ms) produced 3 false boundaries.
  - **Sub-Unit Precision:** Formatted with exact floating/rational precision; $50\text{ ms}$ intervals display cleanly as `(0.50u) [Sub-Unit < 1u]`.
- **Automated Tests:** 15 unit tests in `tests/test_group_discovery.py` passing in $0.004\text{ s}$. Total local project test suite: **106/106 tests reported passing by Antigravity**. The additional 15 tests have not been independently reproduced by ChatGPT.

---

## Section 6 — Project Roadmap

### Stage 1: Milestone 5A Finalization (reported complete locally)
- [x] Maximum-cardinality bipartite matching verification.
- [x] Strictly internal boundary evaluation.
- [x] 100-seed fair Monte Carlo random baseline.
- [x] Passage-level zero-false-alarm negative control evaluation.
- [x] Exact fractional sub-unit representation.

### Stage 2: Two-Row Column-Width Benchmark (Active Design / Next Step)
- [ ] First establish and test independent uniform column structures for the entire sound set in each temporary row, as specified in Statement 29.
- [ ] Investigate how the two structures fit together without replacing either one, and how the result translates into Row 1. Do not assume a boundary union or a common uniform width is the solution.
- [ ] Preserve the historical 4u/3u boundary-union example as a comparison control only. Raw cross-song column counts may depend on duration, tempo, number of rows, and reference unit.
- [ ] Review the following historical benchmark plan against Statement 29 before implementation.
- [ ] Implement `music_model/group_timing_benchmark.py`:
  - **Experiment A (Mathematical Grouping Control):** Byte-for-byte identical MIDI events; evaluating Row 1 column-width variance under regular vs. irregular grouping annotations.
  - **Experiment B (Audible Musical Timing Control):** Identical pitch sequence and motive; altering actual physical note onsets to evaluate audible pacing differences.
  - **Explicit Terminal Gesture:** Identical $[1000, 1200)\text{ ms}$ low-to-high cadence in both versions.
- [ ] Implement `tests/test_group_timing_benchmark.py` and `verify_group_timing_benchmark.py`.

### Stage 3: Two-Doll Storyboard Benchmark
- [ ] Model conversational turn-taking and physical hand-offs between two animated characters.
- [ ] Measure cross-row boundary alignment against character action completion.

### Stage 4: Boolean Outcome and Emotional Ending Benchmark
- [ ] Implement comparative tests evaluating `bool = true` vs. `bool = false` terminal cadences across varying action contexts.
- [ ] Conduct empirical listening trials testing listener perception of linear vs. curved pacing.

---

## Section 7 — Research Rules and Preservation

To maintain scientific integrity across all human and AI contributors, the following principles are mandatory:

1. **Preserve the Author's Words:** The author's original words in `music.txt` are the permanent foundation of the project. They must never be altered, silently corrected, or omitted.
2. **Explicit Labeling of Guesses:** Any interpretation, hypothesis, or speculative extrapolation by an AI assistant must be explicitly prefixed with `"I guess ..."` (or `"i guess ..."`), keeping hypotheses strictly separated from mathematical facts.
3. **Strict Separation of Repositories:** The Calculator repository (`C:\Users\I_wat\PycharmProjects\calculator`) is permanently protected at commit `17be078d`. It must never be edited, staged, committed, or pushed.
4. **Preserve Validated Code & Zero Regression:** All 106 automated unit tests and standalone verification scripts must continue passing with exit code 0 before any new work is approved.
5. **No Destructive Quantization:** Never alter, shift, or round raw MIDI ticks, tempo fractions, or continuous audio timestamps to force them onto visual display grids.
6. **Transparent Reporting of Controls:** When evaluating algorithms against controls, report both successes and failures honestly. Synthetic benchmarks must never be claimed to prove how all music works.
7. **No Unprompted Git Commits:** Do not stage, commit, or push changes without explicit, unanimous authorization from the author.
8. **Accurate Tracking of Local Workspace State:** Acknowledge all untracked files honestly; do not claim the working tree is clean when local experimental or draft files are present.
