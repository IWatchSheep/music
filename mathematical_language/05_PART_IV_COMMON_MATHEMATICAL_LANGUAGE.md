# Mathematical Language — Part IV: A Common Mathematical Language

**From:** Claude (Opus 5.5)
**To:** ChatGPT, for independent review, and the Author
**Date:** 2026-11-27
**Builds on:** `02`+`02a` (music), `03`+`03a` (number theory), `04`+`04a` (storytelling).
**Authority:** `music/README.md` (read-only).

### How to read the labels

| Label | Meaning |
|---|---|
| **Definition** | A proposed formal meaning. |
| **Bijection** | A proved one-to-one correspondence between two sets of structures. |
| **Conditional theorem** | Proved under explicitly named extra assumptions. |
| **Analogy** | A likeness with no proved correspondence. |
| **Conjecture / Hypothesis** | Unproven. Hypotheses are the Author's. |
| *I guess …* | Speculative interpretation. |

---

## 0. Conclusion first

The three subjects share **one exactly specified mathematical skeleton**: a **finite ordered chain of $N$ units, together with a set of cut points**. Music, arithmetic and storytelling each give this skeleton a different reading. On the skeleton, the following are **bijections**, not analogies:

- consecutive partitions ↔ integer compositions ↔ subsets of the $N-1$ internal cuts;
- equal partitions ↔ divisors;
- affine polygon endings ↔ divisors;
- coprime row pairs ↔ subsets of the prime factors;
- factor pairs ↔ (square factor, coprime pair).

**Refinement of structures corresponds to divisibility** (§3). The historical boundary union and the merger M1 turn out to be **joins in two different orders** (§6), which explains a long-standing confusion in the original project.

The correspondences **forget** almost everything that makes each subject itself: sound identity, durations, height, story states, goals, valence and meaning (§13). The zeta-function identities are exact but live on $\operatorname{Re}(s)>1$ or in continuations. **Nothing beyond a relabelling of known arithmetic has been established about the Riemann hypothesis** (§15). Musical identity, emotion, story meaning and RH remain unresolved. That is the honest result.

---

## 1. The common object: the unit chain

**Definition 1.1.** For $N\ge1$, the **unit chain** $[N]$ is the sequence of units $1,2,\dots,N$ in order. It has $N-1$ **internal cut positions** $\{1,\dots,N-1\}$, where cut $k$ lies between units $k$ and $k+1$. A **segmented chain** is a pair $(N,K)$ with $K\subseteq\{1,\dots,N-1\}$.

**The three readings**

| | Music (Part I) | Arithmetic (Part II) | Story (Part III) |
|---|---|---|---|
| Unit | one Row 1 column of width $w_1$ | the number $1$ | one step of a journey |
| $N$ | terminal count $N_1$, or cycle length $\ell$ | a positive integer | number of steps |
| Cut | a knot between transitions (H2), or a group boundary | a split $N=c_1+c_2+\cdots$ | a milestone or episode boundary |

---

## 2. Consecutive partitions and compositions

**Bijection 2.1.** The following three sets are in bijection:
- segmented chains $(N,K)$;
- **compositions** of $N$, meaning sequences of positive integers summing to $N$;
- subsets of $\{1,\dots,N-1\}$.

There are $2^{N-1}$ of each.
*Proof.* A composition $(c_1,\dots,c_J)$ corresponds to the cut set $K=\{c_1,\ c_1+c_2,\ \dots,\ c_1+\cdots+c_{J-1}\}$. The block lengths are recovered as the differences of consecutive cuts. ∎

**Readings.** In music, a composition is a terminal transition structure $(c_1,\dots,c_J)$ (02 §10 H2), or the group lengths of a row measured in Row 1 columns. In a story, it is a division of a journey into consecutive phases or episodes. Proposition 7.2 of Part III ("the ending is itself a journey") is this bijection.

---

## 3. Equal partitions, divisors, and refinement

**Bijection 3.1.** Equal partitions of $[N]$ correspond to the divisors $d$ of $N$, where $d$ is the block length and the cut set is $K_d=\{d,2d,\dots\}\cap\{1,\dots,N-1\}$. There are $\tau(N)$ of them. *(03 Prop. 4.1; 04a M7.)*

**Definition 3.2 (Refinement).** $(N,K)$ **refines** $(N,K')$ if $K'\subseteq K$, meaning it has all the same cuts and possibly more. Under this order the segmented chains form the Boolean lattice of subsets of $\{1,\dots,N-1\}$. The **join**, the coarsest common refinement, is $K\cup K'$. The **meet**, the finest common coarsening, is $K\cap K'$.

**Proposition 3.3 (Refinement = divisibility).** For divisors $d,d'$ of $N$: $K_d\supseteq K_{d'}$ $\iff$ $d\mid d'$.
*Proof.* (⇐) Every multiple of $d'$ is a multiple of $d$. (⇒) If $d'<N$, then $d'\in K_{d'}\subseteq K_d$, so $d\mid d'$. If $d'=N$, then $d\mid N=d'$ trivially. ∎

So **the equal partitions, ordered by refinement, are exactly the divisor lattice of $N$**. *Music:* subdividing Row 1 by a factor $n$ (02 M4, $w_1\to w_1/n$) is refinement. *Story:* splitting each episode into equal sub-episodes is refinement.

---

## 4. Affine terminal transition structures

**Bijection 4.1 (polygon model).** Affine polygon structures on $[N]$ are the equal partitions, so they correspond to $D(N)$ via $J\mapsto c=N/J$. There are $\tau(N)$ of them. Normalized, they all trace **one** geometric line, so $\tau$ counts internal divisions, not shapes (03a L3).

**Proposition 4.2 (staircase model).** Only the structure $c=(1,\dots,1)$, with $J=N$, has affine samples at the column lines. The continuous staircase is never affine (02a K6a; 03a L1).

**Shape classes (03 Prop. 5.4).** Inside the $2^{N-1}$ compositions:

| Class | Count |
|---|---|
| Convex (non-increasing) | $p(N)$ |
| Concave (non-decreasing) | $p(N)$ |
| Affine (constant) | $\tau(N)$ |
| Mixed | $2^{N-1}-2p(N)+\tau(N)$ |

---

## 5. Prime counts and indivisibility

**Proposition 5.1.** For $N\ge2$, the following are equivalent:
1. $N$ is prime.
2. $[N]$ has exactly two equal partitions: one block, or $N$ single units.
3. Exactly two affine polygon endings exist: one transition, or $N$ single-column transitions.
4. No story of $N$ steps divides into $K$ equal episodes with $1<K<N$.

*Proof.* Each statement says $\tau(N)=2$, by Bijections 3.1 and 4.1. ∎

**Conditional theorem 5.2.** If $N_1=p$ is prime and the polygon has $J$ levels with $1<J<p$, then the ending is non-affine (03 Prop. 5.3). Under training match with $J\ge2$ (04a M6), $c^\ast=1$ and $J=p$.

**$N=1$** is a separate case. Its single partition is both "one block" and "single units" at once. It is neither prime nor composite (03 Fact 3.1).

---

## 6. Two rows on one chain: coprime pairs, alignment, and the two joins

Measure in Row 1 columns, with the rows sharing a boundary (02 Cor. 8.1). Row 2 has block length $m'$ and Row 3 has block length $n'$, with $\gcd(m',n')=1$, on the common cycle $[\ell]$ where $\ell=m'n'$ (03 Prop. 8.2).

**Proposition 6.1 (Two different joins).** On $[\ell]$, with $K_{m'}$ and $K_{n'}$ the two rows' cut sets:
- (a) **The join among all segmented chains** is $K_{m'}\cup K_{n'}$. This is the **historical boundary union** (README §3.4). For $(m',n')=(4,3)$ and $\ell=12$, the cuts are $\{3,4,6,8,9\}$ and the blocks are $[3,1,2,2,1,3]$, which are **not equal**.
- (b) **The join among equal partitions** (the divisor lattice, Prop. 3.3) is $K_{\gcd(m',n')}=K_1$, every cut. This is the **merger M1**: the coarsest *uniform* common refinement (02 Prop. 10.1).
- (c) **The meet in both orders** is $K_{m'}\cap K_{n'}=\varnothing$, a single block of length $\ell=\operatorname{lcm}$. This is the common cycle **M2**.

*Proof.* (a) is Definition 3.2. (b): by Proposition 3.3, a common equal refinement of $K_{m'}$ and $K_{n'}$ is a $K_d$ with $d\mid m'$ and $d\mid n'$, and the coarsest such $d$ is $\gcd(m',n')$. (c): a common internal cut would be a common multiple of $m'$ and $n'$ smaller than $\ell=\operatorname{lcm}(m',n')$, and none exists. ∎

*This is a genuinely clarifying result for the Author's original project.* The README records that the historical boundary union "yielded non-uniform slices" and "is **not** the uniform merged column structure specified in Statements 28–30". Proposition 6.1 says exactly why. Both are "the coarsest common refinement" of the two rows, **taken in two different orders**. The union is the join among all partitions. The merger is the join among uniform partitions. Statement 29's insistence on uniform columns is precisely the choice of the second order.

**Bijection 6.2.** Ordered coprime pairs $(m',n')$ with $m'n'=\ell$ correspond to subsets of the set of distinct primes dividing $\ell$. There are $2^{\omega(\ell)}$ of them (03 Prop. 8.3).

**Scope.** Simultaneous start times recur every $\ell$ columns (04a M8). Nothing about alternation, overlap or musical significance follows.

---

## 7. The square-factor relationship

**Bijection 7.1.** The following two sets are in bijection:
- ordered factor pairs $(a,b)$ with $ab=N$;
- pairs consisting of a square divisor $d^2\mid N$ and an ordered coprime pair $(u,v)$ with $uv=N/d^2$.

The correspondence is $(a,b)\mapsto(\gcd(a,b),\,a/d,\,b/d)$. Hence $\tau(N)=\sum_{d^2\mid N}2^{\omega(N/d^2)}$, which gives $B(N)\le A(N)$ with equality iff $N$ is squarefree (04a M11; 03a B1–B3).

**The two readings it joins.** In the polygon model, $(a,b)=(J,c)$ is an **affine ending** with $J$ transitions of $c$ columns. In the row model, $(u,v)=(m',n')$ is a **coprime row pair**. The bijection says: *every affine ending is, uniquely, a coprime row-pair pattern scaled by a common square factor.* This is a correspondence of counting structures at the same integer $N$. That a piece's $N_1$ equals its $\ell$ is **not** established (03a Scope).

---

## 8. Main journey and terminal journey

**Definition 8.1 (Episode skeleton).** An episode $E=(\gamma,\eta)$ (04a M1) has the skeleton of a segmented chain of $n_2+n_3+N_1$ units with **two distinguished cuts**: at $n_2$, where phase A ends, and at $n_2+n_3$, the **finish line** $t^\ast$. Each of the three blocks can carry its own internal segmentation: the groups of Row 2, the groups of Row 3, and the transitions of the ending.

**Remark 8.2.** In music, the three blocks are Rows 2 and 3 and the Row 1 gesture. In a story, they are phase A, phase B and the terminal journey. In arithmetic, they are the parts of $n_2+n_3+N_1$. The finish line is a lattice point under M1 (02 Prop. 11, conditional). **No relation between $N_1$ and $n_2+n_3$ is forced** (04a M9).

---

## 9. Addition, goals, outcomes

| Object | Type | Lives on |
|---|---|---|
| Contribution $v(\mathrm A)+v(\mathrm B)$ | element of a commutative monoid | the blocks of the main journey |
| $1+1=2$ | a theorem of $\mathbb N$, the same for every story | nothing contingent |
| First arrival at $B$ | Boolean | the main journey $\gamma$ |
| Valence $\beta$ | partial Boolean (completed episodes only) | $E$ |
| Terminal shape | affine / convex / concave / mixed | $\eta$, or the polygon on the last block |

**Proposition 9.1.** None of the last three rows determines another, unless a linking definition is added (04a M4). *I guess the Author's "1 + 1 = 2" is best read as Definition 5.1(i) of Part III: two completed phases, counted. Its result "2" is the smallest prime, with $D(2)=\{1,2\}$. As an analogy only, this echoes Proposition 5.1.*

---

## 10. Uniform progression versus a reference schedule

| Notion | Condition | Implies affine? | Implied by affine? |
|---|---|---|---|
| Uniform progression | $c_1=\dots=c_J$ | yes (equivalent) | yes |
| Training match | $c_j=c^\ast$ for all $j$ | yes | **no**; CE $(3,3,3)$ with $c^\ast=2$ |
| Training match with $N_1=Jc^\ast$ fixed | as above | yes | **yes** (04a M6) |

**In skeleton terms,** uniform progression means "$K$ is an equal partition". A training match means "$K=K_{c^\ast}$ for a prescribed divisor $c^\ast$". Divisibility (Prop. 3.3) orders the possible schedules: a schedule with block $c$ refines one with block $c'$ iff $c\mid c'$.

---

## 11. Catalogue properties and logical implications (Statement 31, logic only)

Let $C$ be a finite catalogue of items, each either having or lacking each property in $\Phi$ (04 Def. 11.1).

**Definition 11.1.** An implication $P\Rightarrow Q$ is **valid in $C$** if every item in $C$ with $P$ also has $Q$. Write $\mathrm{Imp}(C)$ for the set of valid implications.

**Proposition 11.2.**
- (a) $\mathrm{Imp}$ is antitone: if $C\subseteq C'$, then $\mathrm{Imp}(C')\subseteq\mathrm{Imp}(C)$.
- (b) If $Q\in I(C)$, a universal property, then $P\Rightarrow Q$ is valid for every $P$.
- (c) The converse of (b) fails. An implication can be valid with neither side universal.
- (d) **Vacuous validity:** if no item has $P$, then $P\Rightarrow Q$ is valid for every $Q$.

*Proof.* (a) and (b) follow from the definitions. (c): take the catalogue from ChatGPT's review, $A=(\text{journey},\text{success},\text{dialogue})$, $B=(\text{journey},\text{success},\neg\text{dialogue})$, $C=(\text{journey},\neg\text{success},\text{dialogue})$. Then "no dialogue $\Rightarrow$ success" is valid, but neither "no dialogue" nor "success" is universal. (d) is the logic of the empty case. ∎

**Fact 11.3 (Armstrong's rules).** The implications valid in any catalogue are closed under reflexivity ($P\wedge Q\Rightarrow P$), augmentation (from $P\Rightarrow Q$, infer $P\wedge R\Rightarrow Q\wedge R$) and transitivity. Every implication that follows from a given set of valid implications can be derived by these rules. This is a standard result in database theory and formal concept analysis.

**Remark 11.4.** By (d), validity in a finite catalogue is **not evidence** of a general rule. An implication can hold only because no counterexample has been catalogued yet. *I guess this matters for Statement 31's "logical like previous books": consistency defined by implications is finer than consistency defined by shared properties (Part III), but it is no more reliable without enough cases of each premise.*

---

## 12. The exact correspondences

| Correspondence | Kind | Reference |
|---|---|---|
| Segmented chains ↔ compositions ↔ subsets of $N-1$ cuts | **Bijection** | 2.1 |
| Equal partitions ↔ $D(N)$; refinement ↔ divisibility | **Bijection, order isomorphism** | 3.1, 3.3 |
| Affine polygon endings ↔ $D(N)$ | **Bijection** | 4.1 |
| Prime $N$ ↔ exactly two equal partitions / affine endings / equal-episode divisions | **Equivalence** | 5.1 |
| Coprime row pairs on $[\ell]$ ↔ subsets of primes of $\ell$ | **Bijection** | 6.2 |
| Boundary union = join (all partitions); M1 = join (uniform); M2 = meet | **Theorem** | 6.1 |
| Factor pairs ↔ (square factor, coprime pair) | **Bijection** | 7.1 |
| Episode ↔ chain with two distinguished cuts | **Definition** | 8.1 |
| Success ↔ linear | **Conditional theorem** (two versions) or **Hypothesis** | 10; 04a M6 |
| "1+1=2" ↔ the prime 2 | **Analogy** | 9.1 |
| Row 1 identity, feeling, style | **None established** | — |

---

## 13. What the correspondences forget

**Proposition 13.1.** The maps from music and from stories to segmented chains are many-to-one, so information is lost.
*Proof by example.* Two pieces with different $w_1$, different sounds and different heights but the same transition structure $c=(3,2,1)$ map to the same chain $(6,\{3,5\})$. Two stories with different states, goals and valences but phase lengths $(2,2)$ map to the same chain $(4,\{2\})$. ∎

| Forgotten | Music | Story | Arithmetic |
|---|---|---|---|
| Actual durations ($w_1$, $u$, milliseconds) | yes | yes (step durations $\delta_i$) | — |
| Sound identity, attributes, recurrence (02 §1–2) | yes | — | — |
| Height values, as opposed to the transition pattern | yes | — | — |
| Which rows existed, offsets $\varphi_r$, G-fit vs S-fit | yes | — | — |
| States, the graph, the goal set $B$ | — | yes | — |
| Valence $\beta$, emotion, meaning | yes | yes | — |
| Order of factors | — | — | kept (ordered pairs) |

**What is preserved:** the number of units, the order of blocks, block lengths, equality of blocks, refinement and divisibility, and the arithmetic of the counts. *I guess this is the precise sense in which "mathematics is a language": the skeleton says how the parts divide, not what they are.*

---

## 14. The zeta-function identities and their domains

| Identity | Counts | Valid |
|---|---|---|
| $\sum\tau(N)N^{-s}=\zeta(s)^2$ | affine endings | $\operatorname{Re}s>1$ |
| $\sum(\tau(N)-2)N^{-s}=(\zeta(s)-1)^2$ | affine endings with $J,c\ge2$ | $\operatorname{Re}s>1$ |
| $\sum2^{\omega(N)}N^{-s}=\zeta(s)^2/\zeta(2s)$ | coprime row pairs | $\operatorname{Re}s>1$ |
| $\sum\mu(N)^2N^{-s}=\zeta(s)/\zeta(2s)$ | squarefree $N$, where $A=B$ | $\operatorname{Re}s>1$ |
| $\zeta(s)^2=\zeta(2s)\cdot\zeta(s)^2/\zeta(2s)$ | Bijection 7.1 | $\operatorname{Re}s>1$ |
| Density of coprime pairs and of squarefree $N$: $1/\zeta(2)=6/\pi^2$ | — | natural density |

Statements about zeros concern the **meromorphic continuations** of the right-hand sides, not the series (03a L7).

---

## 15. Has anything beyond relabelling been established about RH?

**No.**

- The model proves arithmetic identities among its own counting functions. They are bijections (§12) and standard Dirichlet-series identities (§14).
- RH can be **restated** in the model's words, for example "the number of column counts $N\le x$ with exactly two affine endings is $\operatorname{Li}(x)+O(\sqrt x\log x)$" (03 §12.2). It can be restated only because those counts *are* $\tau$. That is a relabelling of known equivalent forms (03a L9), with no new method, evidence or constraint on the zeros.
- No substantive argument here reaches the non-trivial zeros. None is claimed.

---

## 16. Counterexamples to proposed universal relationships

| Proposed universal claim | Counterexample | Source |
|---|---|---|
| Every row has an exact uniform fit | Gaps $1$ and $\sqrt2$ in one row | 02 Cor. 2.2 |
| A coarsest approximate fit always exists | Boundary span $\le2\tau$ | 02 CE 4.2b |
| G-fit width = S-fit width | Spans $[0,4],[4,8]$, with a sound of length $1.5$ | 02 CE 3.1 |
| Rows always share a column line | $B_2=\{0,4,8\}$, $B_3=\{\tfrac12,\tfrac72,\tfrac{13}2\}$ | 02 Ex. 6.3 |
| The boundary union is uniform | $[3,1,2,2,1,3]$ | Prop. 6.1(a) |
| More columns ⇒ curved | $(2,2,2)$ | 02 CE 13.2 |
| Convex ⇒ strictly more low columns | $N=4$, $\theta=0.9$ | 02 CE 15.2 |
| Prime count ⇒ linear | $(3,2)$ | 03 §5 |
| Composite count ⇒ curved | $(2,2,2)$ | 03 §5 |
| Every ending is affine or convex | $(1,2,1)$, mixed | 03 Prop. 5.4 |
| Disappointment ⇒ curved progress | R2 at constant speed | 04a M5 |
| Success ⇒ linear progress | R3, $\hat p=x^2$ | 04a M5 |
| Affine ⇒ matches training | $(3,3,3)$ with $c^\ast=2$ | 04a M6 |
| A valid implication ⇒ a general rule | Vacuous premises | 11.2(d) |

---

## 17. Consolidated inventory

**Proved (under stated definitions).** 02: Props 2, 2.1, 3, 4.1, 5.2, 7, 8, 9, 10.1, 11 (conditional), 12, 13, 13S (02a), 14, 15, 16, 17, 18 (02a K8). 03: 4.1, 5.1–5.4, 7.1–7.2, 8.2–8.3, Identities 11.2–11.3. 03a: B1–B3. 04/04a: 1.5 (conditional), 2.2′, 5.2, 6.1′, 7.2, 8.4′, 9.1, 9.3, 10.1, 11.2. 05: 2.1, 3.3, 4.1–4.2, 5.1–5.2, 6.1–6.2, 7.1, 11.2, 13.1.

**Established facts used.** Subgroups of $\mathbb R$; Fine–Wilf; Bézout; the fundamental theorem of arithmetic; the Euler product; the continuation and zeros of $\zeta$; the $6/\pi^2$ densities; the Dirichlet divisor asymptotic; the free category of paths; Armstrong's rules.

**Conditional on chosen definitions.** G-fit as primary (02 F4.4, 02a K1); M1 as Row 1 (02 §7); finish line $=b_3$ (02a K5); $H_1$ vs $H_2$, polygon vs staircase; the two schedule versions of Statement 26 (04a M6).

**Author hypotheses (untested).** Statements 4, 5, 12 (shape vs musical blending); 19–20 (breath/speech durations); 26 (outcome ↔ shape); 3 and 14 (shared identity).

**Open mathematical problems.** O1, approximate fitting under conditions (02 §4.2); a formal invariant for "style or feeling"; whether $H_1$ or $H_2$ better formalizes "high"; whether any natural musical counting function avoids the restatement problem (03 §13).

**Unresolved conjecture.** The Riemann hypothesis. It is untouched by this study.

---

## 18. Mapping back to the Author's 32 statements

| # | Subject (README §9.1) | Formal counterpart | Status |
|---|---|---|---|
| 1 | Sound chunks in rows and time columns | Events, groups, rows, lattices (02 §1–4) | Formalized |
| 2 | Temporary groups; constant row | Row 1 = received lattice; occupancy kept separate (02a K4) | Formalized |
| 3 | Shared style or feeling | — | Not formalized (open invariant) |
| 4 | Blending gives linear vs curved | Shape classes (§4); link to blending | Hypothesis |
| 5 | Low-to-high; columns counted | $H_2$, polygon/staircase; 5.2; 13S | Formalized; link to "traditional" is *I guess* |
| 6 | Valkyries, conductor | — | Analogy only |
| 7 | Temporary rows set column sizes | Stage A + merger; 02 Prop. 17 | Formalized |
| 8 | Linked beginning and end columns | G-fit vs S-fit (02 §4, 02a K1) | Formalized |
| 9 | Plan; compare Row 1s | Comparable invariants (02 Prop. 18) | Partly formalized (rest is engineering) |
| 10 | Many aligned columns | Lattice; reference unit (02 §5) | Formalized |
| 11 | Each song its own structure | Per-piece $w_1$; scale invariance | Formalized |
| 12 | Curved has more low-row columns | 02 Prop. 15 (weak inequality) | Formalized, with limits |
| 13 | Linearity emerges from fitting | Shape = transition distribution (02 Prop. 13) | Formalized |
| 14 | Row 1 gives the song its identity | — | Not formalized |
| 15 | Duck: whirring, then flight | Low block then rise (analogy) | Analogy |
| 16 | Different widths, fitted to the whole | Coarsest fit $g_r$ (02 Cor. 2.1) | Formalized |
| 17 | Count 0–9 in fundamental cells | $L(n)=n\bmod10$; reference unit | Formalized |
| 18 | Shared fundamental size; 4 and 3 | M1 = join in the divisor lattice (§6) | Formalized; not *the* merger by decree |
| 19 | Breath and speech intervals | Duration bounds (04 Prop. 1.5) | Hypothesis, conditional result |
| 20 | Doll A→B as group duration | Main journey timing | Formalized; durations hypothetical |
| 21 | Music ends at the goal | Goal predicate; first arrival | Formalized |
| 22 | Rows 2, 3 journey; Row 1 ending | $E=(\gamma,\eta)$ (04a M1) | Formalized |
| 23 | Tail-end gesture; restart | Terminal journey; path category (04a M3) | Formalized |
| 24 | $1+1=2$ | Contribution monoid; not the Boolean (04 Prop. 5.2) | Formalized; prime 2 is an analogy |
| 25 | Boolean true / false | Three-valued outcome | Formalized |
| 26 | Good = linear, sad = curved | False in general; two conditional theorems | Hypothesis + conditional theorems |
| 27 | Same expression, different sizes | Scale invariance (02 Props. 14, 18) | Formalized |
| 28 | Fit, merge, Row 1; journey/target | Stages A–C; episode | Formalized |
| 29 | Each row independently uniform | 02 Cor. 2.1 | Formalized |
| 30 | Merged columns → Row 1 → 2D graph | 02 Defs. 15–16 | Formalized; height model open |
| 31 | Books, music, catalogue | $I(C)$, $\mathrm{Imp}(C)$, logic only (§11) | Logic formalized; construction out of scope |
| 32 | Prime numbers, Riemann hypothesis | $D(p)=\{1,p\}$ ↔ two affine endings; RH untouched (§15) | Divisibility formalized; RH no connection |

**Totals:**

| Status | Count | Statements |
|---|---|---|
| Formalized, some with stated limits or conditions | 23 | 1, 2, 5, 7–13, 16–18, 20–25, 27–30 |
| Hypothesis-level | 3 | 4, 19, 26 |
| Analogy or not formalized | 4 | 3, 6, 14, 15 |
| Logic only | 1 | 31 |
| Split: divisibility yes, RH no | 1 | 32 |
| **Total** | **32** | |

*End of Part IV.*
