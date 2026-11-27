# Mathematical Language — Final Mathematical Summary

**A self-contained entry point to the study.** It incorporates every correction note (02a, 03a, 04a, 05a). Proofs and longer arguments are in the detailed documents, which are cited as `02 §x` and so on. Where this summary and an earlier document differ, **this summary and the correction notes govern**.

**Date:** 2026-11-27 · **Written by:** Claude (Opus 5.5), with independent review by ChatGPT, for the Author.

---

## 0. Purpose and scope

The Author stopped the original music-machine project and asked for its ideas to be expressed **in mathematics as a language**: describing them, not building them.

The **source authority** is `music/README.md`: the Author's 32 statements, their corrected versions and agreed interpretations, read with its rules (later clarifications, Statements 23 and 28–30, govern earlier ones). The README and `music.txt` were not changed. Where the README leaves an operation open, the study **compared candidate definitions** instead of asking the Author again.

**This study contains:** definitions, established facts, propositions with proofs, counterexamples, and clearly labelled hypotheses and *I guess* interpretations.

**It contains no:** software, algorithms meant to be run, audio processing, machine construction, AI development or automated storytelling.

### How to read the labels

| Label | Meaning |
|---|---|
| **Definition** | A proposed formal meaning |
| **Fact** | Established mathematics |
| **Proposition / Theorem** | Proved here, under the stated definitions |
| **Conditional theorem** | Proved under explicitly named extra assumptions |
| **Bijection** | A proved one-to-one correspondence |
| **Counterexample** | Refutes a universal claim |
| **Analogy** | A likeness without proof |
| **Hypothesis** | The Author's, untested |
| **Conjecture** | Open mathematics (here, only RH) |

**Formalization is not validation.** Formalizing a statement means supplying a mathematical interpretation and proving its consequences. **No empirical claim about music, emotion or stories has been tested in this study** (§13).

---

## 1. Notation

| Symbol | Meaning |
|---|---|
| $[0,T]$ | time span of a piece |
| $e=(s_e,f_e,\alpha_e)$ | sound event: start, finish, abstract attribute |
| $B^G_r,\ B^S_r$ | group-boundary and sound-boundary sets of Row $r$ |
| $D(B)$ | difference group: integer combinations of gaps in $B$ |
| $\Lambda(\varphi,w)=\varphi+w\mathbb Z$ | uniform column lattice: offset $\varphi$, width $w$ |
| $g_r$ | coarsest fitting width of Row $r$ |
| $w_1$ | merged width received by Row 1 (candidate M1) |
| $\ell$ | common cycle in Row 1 columns |
| $u$ | external reference unit |
| $N_1$ | number of Row 1 columns in the terminal gesture |
| $J,\ c_j$ | number of transitions (with $J+1$ levels); columns used by transition $j$ |
| $[N],\ K$ | unit chain of $N$ units; set of internal cuts $K\subseteq\{1,\dots,N-1\}$ |
| $K_d$ | cut set of the equal partition with block length $d$ |
| $\tau(N),\ \omega(N),\ p(N)$ | number of divisors; of distinct prime factors; of partitions of $N$ |
| $\mu$ | Möbius function |
| $\gamma,\ \eta,\ E$ | main journey, terminal journey, episode $E=(\gamma,\eta)$ |
| $\beta$ | valence (success or disappointment), defined only on completed episodes |

---

## 2. The four parts

| Part | Document(s) | Principal result |
|---|---|---|
| I · Music | 02 + 02a | Uniform lattices; independent fitting; merger as a forced common refinement; terminal trajectories |
| II · Number theory | 03 + 03a | Divisors ↔ linear endings; coprime row pairs; square-factor decomposition; ζ identities; RH verdict |
| III · Storytelling | 04 + 04a | Main and terminal journeys; outcomes; Statement 26 refuted in general and recovered conditionally; catalogue logic |
| IV · Common language | 05 + 05a | The unit chain; exact bijections; two joins; what is forgotten |

---

## 3. Part I — Independent fitting and the uniform merger

**Exact fit (Definition).** A boundary set $B$ fits $\Lambda(\varphi,w)$ if $B\subseteq\varphi+w\mathbb Z$.
- **G-fit** uses group boundaries. It is the primary candidate, consistent with Statement 8: individual sounds are not automatically Row 1 boundaries.
- **S-fit** uses sound boundaries. It is a stricter candidate, retained and not prohibited.

**Proposition (02 Prop. 2, Cor. 2.1).** Let $B$ have at least two points. Then $B$ fits some $\Lambda(\varphi,w)$ iff $D(B)\subseteq w\mathbb Z$. If the gaps are commensurable, $D(B)=g\mathbb Z$ and the fitting widths are exactly $g/n$. **Each row therefore has a unique coarsest uniform width $g_r$.**
- Incommensurable gaps give no exact fit.
- One-point sets fit every width.
- Rational data always fit, but $g$ may be musically meaningless (02 Remark 2.4).

**G-fit vs S-fit (02 Prop. 3).** $g^G_r$ is a multiple of $g^S_r$, and the two can differ (CE 3.1).

**Merger (02 Props. 7–9; 05 Prop. 6.1).**
- **M1, common subdivision:** $w_1=\gcd(g_2,g_3,\varphi_2-\varphi_3)$. With a shared boundary this is $\gcd(g_2,g_3)$. Both native systems survive intact inside it.
  - **Existence (F2):** this greatest positive common subdivision exists **only when $g_2$, $g_3$ and $\varphi_2-\varphi_3$ are commensurable**, so that $D(B_2\cup B_3)$ is cyclic. For incommensurable widths or offset differences, no positive common subdivision exists (02 Prop. 7; Fact F1 in 02 §4).
- **M2, common cycle:** the lattices meet iff $\varphi_2-\varphi_3\in g_2\mathbb Z+g_3\mathbb Z$, and then they meet every $\operatorname{lcm}(g_2,g_3)$.
- **Product identity:** $\gcd\cdot\operatorname{lcm}=g_2g_3$.
- **M1 is the coarsest uniform structure containing both rows' boundaries** (02 Prop. 10.1). This is a consequence of the exact-fit definition, not a decree.
- **Different origins** can share a subdivision ($\tfrac12$) and yet never share a column line: $B_2=\{0,4,8\}$, $B_3=\{\tfrac12,\tfrac72,\tfrac{13}2\}$.

**Row 1 (02 Def. 14; 02a K4–K5).** Row 1 receives $\Lambda_1=\Lambda(\varphi_1,w_1)$ and covers the piece. Coverage is not occupancy (sound in every column). Under M1, the finish line $t^\ast=b_3$ lies on $\Lambda_1$. This is **conditional** on that formalization of Statement 32.

**Approximate fit (02 §4.2).** It is ill-posed without extra conditions. Small widths always fit (CE 4.2a), and a short span lets every width fit (CE 4.2b). This is an open problem.

---

## 4. Part I — Terminal trajectories: polygon and staircase

A **low-to-high trajectory** is $y_0=0\le y_1\le\dots\le y_{N}=1$ with $N=N_1$. It is **affine** if $\Delta^2y_k=y_{k+1}-2y_k+y_{k-1}=0$ for $1\le k\le N-1$. It is **convex** if $\Delta^2y_k\ge0$. Convexity alone does not imply increase. "Curved" means **non-affine**.

**Height models.**
- $H_1$: an external height $h$, not identified with pitch.
- $H_2$: a row-level height with $J$ transitions using $c_1,\dots,c_J$ columns. This has two representations:

| Representation | Construction | Affine exactly when |
|---|---|---|
| **Polygon** | linear interpolation between the knots $(C_j,j/J)$ | all $c_j$ equal (02 Prop. 13) |
| **Staircase** | constant during each transition, then a jump | **samples** affine iff all $c_j=1$; the continuous staircase is never affine (02a K6a; 03a L1) |

*I guess:* the staircase is closer to the literal movement in Statement 5, and the polygon is closer to the 2D graph in Statement 30. Both are kept.

**Results.**
- **For the polygon, the grid does not create the shape.** Refining $w_1$ multiplies every $c_j$ by $n$, and the polygon's shape class is unchanged (02 Prop. 14). Under $H_1$, sampling an unchanged underlying trajectory more finely preserves affine and strictly convex classes (02 Prop. 12). **This invariance does not hold for staircase samples (F1):** $(1,1)$ has affine staircase samples, but its refinement $(2,2)$ does not. This does not contradict the polygon result.
- **A convex trajectory has at least as many low samples as the line.** Equality is possible (02 Prop. 15, CE 15.2). Counting *whole* columns as low needs interpolation or monotonicity (02a K7).
- **One column cannot display curvature.** Two points are always collinear. This is a limit on observation, not proof of straightness (02 Prop. 16).
- **The M2 width cannot in general count the transitions** of an ending formed from the rows' groups (02 Prop. 17).
- **Scale invariance under $t\mapsto\lambda t+c$**, applied to the whole structure and to $h$: the counts and shape classes are invariant. Absolute widths can be compared numerically; the README only says no common width is *imposed* (02a K8).

---

## 5. Part II — Divisibility, primes, coprime pairs

**Equal partitions and linear endings (03 §4–5; 03a L3).**
- The equal regroupings of $N$ columns correspond to the divisors of $N$, so there are $\tau(N)$ of them.
- The affine polygon structures are $(J,c)$ with $Jc=N$, also $\tau(N)$ of them. All trace **one** normalized line, so $\tau$ counts internal divisions, not shapes.

**Primes.** For $N\ge2$: $N$ is prime $\iff$ there are exactly two equal regroupings $\iff$ exactly two affine structures, $(1,p)$ and $(p,1)$. *I guess this is the exact form of Statement 32's "divided by nothing but 1 and itself".* $N=1$ is neither prime nor composite.

**Forced non-affinity.** A linear polygon needs $J\mid N_1$. If $N_1=p$ is prime and $1<J<p$, the ending is non-affine (03 Prop. 5.3).

**Shape counts** among the $2^{N-1}$ compositions:
- convex: $p(N)$;
- concave: $p(N)$;
- affine: $\tau(N)$;
- mixed: $2^{N-1}-2p(N)+\tau(N)$. The first mixed case is $(1,2,1)$, at $N=4$.

**gcd and lcm.**
- **Bézout:** $\gcd=ag_2+bg_3$ for some integers $a,b$. *I guess* this is an analogy for Statement 12's "row addition".
- **Exponents:** M1 takes the minimum exponent of each prime and M2 the maximum.
- **A reduced ratio is always coprime.** That is not evidence of anything special, though the ratio still records relative size (03a L5).
- **Coprimality depends on the unit chosen** (03 Prop. 7.2).

**Row pairs (03 Prop. 8.2–8.3).** In Row 1 units with a shared boundary, $m'=g_2/w_1$ and $n'=g_3/w_1$ are coprime and $\ell=m'n'$. There are $B(\ell)=2^{\omega(\ell)}$ such ordered pairs: each prime power of $\ell$ goes wholly to one row.

**Square factors (03a B1–B3; 04a M11).** Write $A(N)=\tau(N)$.
- $B(N)\le A(N)$, with equality **iff $N$ is squarefree**.
- **Bijection:** $(a,b)\mapsto(d,u,v)$ with $d=\gcd(a,b)$ and $a=du$, $b=dv$, $\gcd(u,v)=1$, $N=d^2uv$. Hence $A(N)=\sum_{d^2\mid N}B(N/d^2)$.

**Scope.** Comparing $A$ and $B$ at the same $N$ does not assume that a piece's $N_1$ equals its $\ell$.

---

## 6. Part II — Zeta identities, with domains

| Identity | Counts | Valid for |
|---|---|---|
| $\zeta(s)=\sum n^{-s}=\prod_p(1-p^{-s})^{-1}$ | (Euler product) | $\operatorname{Re}s>1$ |
| $\sum_{N\ge1}\tau(N)N^{-s}=\zeta(s)^2$ | affine endings | $\operatorname{Re}s>1$ |
| $\sum_{N\ge2}(\tau(N)-2)N^{-s}=(\zeta(s)-1)^2$ | affine endings with $J,c\ge2$; coefficient $0$ iff $N$ prime | $\operatorname{Re}s>1$ |
| $\sum_{N\ge1}2^{\omega(N)}N^{-s}=\zeta(s)^2/\zeta(2s)$ | coprime row pairs | $\operatorname{Re}s>1$ |
| $\sum_{N\ge1}\mu(N)^2N^{-s}=\zeta(s)/\zeta(2s)$ | squarefree $N$, where $A=B$ | $\operatorname{Re}s>1$ |
| density of coprime pairs $=$ density of squarefree integers $=1/\zeta(2)=6/\pi^2$ | — | natural density |
| $\sum_{N\le x}\tau(N)=x\ln x+(2\gamma-1)x+O(\sqrt x)$ | linear endings up to $x$ | Dirichlet (1849) |

The series converge only for $\operatorname{Re}s>1$. Statements about zeros concern the **meromorphic continuations** of the right-hand sides. Zeros pass to a counting series only through a specific identity, with possible cancellations or poles checked (03a L7–L8).

---

## 7. Part III — Journeys, episodes, outcomes

**Story space and paths.** A directed graph $(S,\to)$. **All** finite paths, including the length-0 identity paths, form the **free category** under compatible concatenation. **The loops at each fixed state form a monoid under compatible concatenation** (F3; 04a M3; 05a P4).

**Main journey $\gamma$.** A path whose last state is the **first arrival** in the goal set $B$. This is stronger than "the final state lies in $B$". The steps of $\gamma$ carry phase A (Row 2), then phase B (Row 3). First-arrival journeys are **not closed** under concatenation.

**Terminal journey $\eta$.** A low-to-high path through the levels of $H_2$, occupying $[t^\ast,t^\ast+N_1w_1]$ and starting when $\gamma$ arrives.

**Episode $E=(\gamma,\eta)$.** In the sequential A-then-B model with the common unit $w_1$, its skeleton is a chain of $n_2+n_3+N_1$ units with distinguished cuts at $n_2$ and at the finish line (05a P7). **No relation between $N_1$ and $n_2+n_3$ is forced** within the arithmetic model (04a M9).

**Addition.** A contribution $v(\mathrm A)+v(\mathrm B)$ takes values in a commutative monoid: a count, a duration, a progress or a distance. In metric terms, $d(a,b)=d(a,M)+d(M,b)$ means the chain $a,M,b$ is shortest. A continuous geodesic through $M$ follows only in a geodesic space (04a M2).

**$1+1=2$ vs the Boolean.** "$1+1=2$" is true in every story, so it cannot be the outcome (04 Prop. 5.2).

**Outcomes.** There are three: incomplete; or completed with $\beta$ = success; or completed with $\beta$ = disappointment. Statement 25 has a sad ending still reach Point B.

**Proposition 6.1′ (04a M4).** Among completed episodes, all four combinations of $\beta$ and affine/non-affine terminal shape are admissible. **Neither forces the other.**

**Race (04a M5).** Each counterexample is about main-journey progress:
- R2 runs at constant speed $\tfrac12$ and loses: linear progress.
- R3, with $p=(t/0.9)^2$, finishes at $0.9<1$ and wins: convex progress.

These refute rules tied to the progress curve. They do not refute a separately defined rule about $\eta$.

**Uniform progression vs training (04a M6).**
- Uniform ($c_j$ all equal) $\iff$ affine polygon.
- A training match ($c_j=c^\ast$) implies affine, but not conversely: $(3,3,3)$ with $c^\ast=2$ is affine and does not match.
- With $N_1=Jc^\ast$ fixed, affine $\iff$ training match.

These are the **two conditional versions** of Statement 26. In general, Statement 26 does not hold.

**Equal episodes and turn-taking.**
- For fixed $K$, an equal division of $N\ge1$ steps into $K$ episodes exists iff $K\mid N$, and it is unique. There are $\tau(N)$ in total.
- Periods $m,n$ from a common origin start together every $\operatorname{lcm}(m,n)$. Alternation, non-overlap and conversational meaning are **not** implied (04a M7–M8).

**Catalogue logic (Statement 31, logic only; 05 §11; 05a P5).**
- Shared properties $I(C)$ and valid implications $\mathrm{Imp}(C)$, between attribute *sets*, are both antitone in $C$.
- An implication can be valid with neither side universal.
- Vacuous validity occurs when no item has the premise.
- Negative properties are represented as complementary attributes.
- Armstrong's rules are sound.
- **Validity in $C$ means consistency with that catalogue, not universal truth.**

---

## 8. Part IV — The common language

**The unit chain** $[N]$ with a cut set $K$ is read as columns (music), units of $1$ (arithmetic) or steps (story).

**Order convention:** cut sets are ordered by inclusion, so more cuts means finer.

| Correspondence | Kind |
|---|---|
| Cut sets $K$ ↔ compositions of $N$ ↔ subsets of $\{1,\dots,N-1\}$; there are $2^{N-1}$ | **Bijection** |
| Equal partitions ↔ $D(N)$ | **Bijection**: an order *anti*-isomorphism by block length, an isomorphism by block count (05a P2) |
| Affine polygon endings ↔ $D(N)$ | **Bijection** |
| $N$ prime ⟺ exactly two of each of the above | **Equivalence** |
| Coprime pairs with product $\ell$ ↔ subsets of the primes of $\ell$ | **Bijection** |
| Factor pairs ↔ (square factor, coprime pair) | **Bijection** |
| Episode ↔ chain with two distinguished cuts (sequential model) | **Definition** |
| "$1+1=2$" ↔ the prime $2$, $D(2)=\{1,2\}$ | **Analogy** only |

**Theorem (05 Prop. 6.1): the two joins.** On $[\ell]$ with rows of block lengths $m',n'$:

| Operation | Ordered set | Result for $(4,3)$ on $[12]$ |
|---|---|---|
| Historical **boundary union** | join among *all* partitions, $K_{m'}\cup K_{n'}$ | $[3,1,2,2,1,3]$, unequal |
| **M1** | join among *equal* partitions, $K_{\gcd}$ | width $\gcd=1$ |
| **M2** | meet, $K_{m'}\cap K_{n'}=\varnothing$ | one block, $\operatorname{lcm}=12$ |

**This is why the original project's boundary merger never gave uniform columns.** It solved the right problem in the wrong ordered set. Statement 29's demand for uniform columns is exactly the choice of the equal-partition order.

---

## 9. What the correspondences forget

The maps to the unit chain are many-to-one (05 Prop. 13.1).

**Preserved:** the number of units, the order of blocks, block lengths, equality of blocks, refinement and divisibility, and the counts.

**Forgotten:**
- actual durations ($w_1$, $u$, milliseconds) and step durations;
- sound identity and attributes;
- height values;
- which rows existed, their offsets, and whether fitting was G-fit or S-fit;
- story states, the graph and the goal;
- valence, emotion and meaning.

*The skeleton says how things divide, not what they are.*

---

## 10. Proven results (under stated assumptions)

| Area | Results |
|---|---|
| Fitting | 02 Props 1–3, 4.1 (declared period; fundamental period under 03a L2), 5.2 |
| Merger | 02 Props 7–9, 10.1; 05 Prop 6.1 |
| Row 1 | 02 Prop 11 (conditional, 02a K5) |
| Trajectories | 02 Props 12–18; 02a 13S |
| Number theory | 03 Props 4.1, 5.1–5.4, 7.1–7.2, 8.2–8.3; Identities 11.2–11.3; 03a B1–B3; 04a M11 |
| Stories | 04 Props 1.5 (conditional), 5.2, 7.2, 9.1, 9.3, 10.1, 11.2; 04a M2, M4 (6.1′), M6 (8.4′) |
| Common language | 05 Bijections 2.1, 3.1, 4.1, 6.2, 7.1; Props 3.3 (with 05a P2), 5.1, 6.1, 11.2, 13.1 |

---

## 11. Counterexamples

| Universal claim | Counterexample | Source |
|---|---|---|
| Every row has an exact uniform fit | gaps $1$ and $\sqrt2$ | 02 Cor 2.2 |
| A coarsest approximate fit exists | span $\le2\tau$ | 02 CE 4.2b |
| G-fit width = S-fit width | sound $[0,1.5]$ in $[0,4]$ | 02 CE 3.1 |
| Rows always share a column line | origins $0$ and $\tfrac12$ | 02 Ex 6.3 |
| The boundary union is uniform | $[3,1,2,2,1,3]$ | 05 Prop 6.1(a) |
| More columns ⇒ curved | $(2,2,2)$ | 02 CE 13.2 |
| Convex ⇒ strictly more low samples | $N=4$, $\theta=0.9$ | 02 CE 15.2 |
| Prime count ⇒ linear | $(3,2)$ | 03 §5 |
| Composite count ⇒ curved | $(2,2,2)$ | 03 §5 |
| Every ending is affine or convex | $(1,2,1)$ | 03 Prop 5.4 |
| Disappointment ⇒ curved progress | R2 | 04a M5 |
| Success ⇒ linear progress | R3 | 04a M5 |
| Affine ⇒ matches training | $(3,3,3)$, $c^\ast=2$ | 04a M6 |
| First-arrival journeys compose | $\gamma$ followed by a step | 05a P4 |
| Valid in the catalogue ⇒ general rule | vacuous premise | 05 Prop 11.2(d) |

---

## 12. The 32 statements: formalization and validation

**Formalization:**
- **F** — formalized: an interpretation was supplied and its consequences proved;
- **H** — hypothesis-level: a conditional formal result only;
- **A** — analogy, or not formalized;
- **L** — logic only;
- **S** — split.

**Empirical claim:**
- **none** — the statement is a design or structural statement;
- **untested** — the statement makes a musical, narrative or emotional claim that this study did not test.

| # | Subject | Formal counterpart | Form. | Empirical |
|---|---|---|---|---|
| 1 | Sound chunks in rows and columns | events, groups, rows, lattices | F | none |
| 2 | Temporary groups; constant row | Row 1 = received lattice (occupancy separate) | F | none |
| 3 | Shared style or feeling | — | A | untested |
| 4 | Blending → linear vs curved | shape classes | H | untested |
| 5 | Low-to-high; column counts | $H_2$, polygon and staircase | F | untested ("traditional" vs "mixed") |
| 6 | Valkyries, conductor | — | A | untested |
| 7 | Rows set column sizes | Stage A + merger; 02 Prop 17 | F | untested (direction of size difference) |
| 8 | Linked columns | G-fit vs S-fit | F | none |
| 9 | Plan; compare Row 1s | comparable invariants | F (partly) | none |
| 10 | Many aligned columns | lattice, reference unit | F | none |
| 11 | Each song its own structure | per-piece $w_1$; scale invariance | F | none |
| 12 | Curved has more low columns | 02 Prop 15 (weak inequality) | F | untested |
| 13 | Linearity emerges from fitting | shape = transition distribution | F | untested |
| 14 | Row 1 gives the song identity | — | A | untested |
| 15 | Duck analogy | low block then rise | A | — |
| 16 | Widths fitted to whole rows | coarsest fit $g_r$ | F | none |
| 17 | 0–9 counting | $L(n)=n\bmod10$, reference unit | F | none |
| 18 | Shared fundamental size; 4 and 3 | M1 = join among equal partitions | F | none |
| 19 | Breath and speech intervals | duration bounds (conditional) | H | untested |
| 20 | Doll A→B as group duration | main-journey timing | F | untested (durations) |
| 21 | Music ends at the goal | goal predicate; first arrival | F | untested |
| 22 | Rows 2–3 journey; Row 1 ending | $E=(\gamma,\eta)$ | F | none |
| 23 | Tail-end gesture; restart | terminal journey; path category | F | none |
| 24 | $1+1=2$ | contribution monoid; not the Boolean | F | none |
| 25 | Boolean true / false | three-valued outcome | F | none |
| 26 | Good = linear, sad = curved | false in general; two conditional theorems | H | untested |
| 27 | Same expression, different sizes | scale invariance | F | untested |
| 28 | Fit, merge, Row 1 | Stages A–C; episode | F | none |
| 29 | Rows independently uniform | 02 Cor 2.1 | F | none |
| 30 | Merged columns → Row 1 → 2D graph | trajectories; height model open | F | none |
| 31 | Books, music, catalogue | $I(C)$, $\mathrm{Imp}(C)$ | L | out of scope |
| 32 | Primes, RH | $D(p)$ ↔ two affine structures; RH untouched | S | — |

**Totals:**

| | Count |
|---|---|
| F (formalized) | 23 |
| H (hypothesis-level) | 3 |
| A (analogy / not formalized) | 4 |
| L (logic only) | 1 |
| S (split) | 1 |
| **Total** | **32** |
| Untested empirical claims | 13: Statements 3, 4, 5, 6, 7, 12, 13, 14, 19, 20, 21, 26, 27 |
| Empirically validated claims | **0** |

---

## 13. Formalization versus empirical validation

- **What this study did:** it supplied precise mathematical meanings for the Author's ideas, proved what follows from them, and found where they fail (counterexamples) and under what conditions they hold (conditional theorems).
- **What it did not do:** test any claim about real music, listeners, emotions or stories. Whether "modern" music produces non-affine endings, whether breath sets group lengths, and whether sad endings are curved all remain **untested hypotheses**. The mathematics now states exactly what such a test would have to measure.
- **"23 formalized" ≠ "23 proven hypotheses."**

---

## 14. The Riemann hypothesis

**Statement (Riemann, 1859; unproven).** Every non-trivial zero of the continued $\zeta$ has real part $\tfrac12$. Equivalently (von Koch, 1901), $\pi(x)=\operatorname{Li}(x)+O(\sqrt x\log x)$, a bound on **the error made when $\operatorname{Li}(x)$ approximates the number of primes**.

**What the study established:**
- divisibility relations (prime $N_1$ ↔ exactly two affine structures);
- coprime and square-factor bijections;
- the density $6/\pi^2$;
- exact Dirichlet-series identities on $\operatorname{Re}s>1$.

**What it did not establish:** any constraint on the non-trivial zeros. RH can be **restated** in the model's words, for example "column counts with exactly two affine endings number $\operatorname{Li}(x)+O(\sqrt x\log x)$". That is possible only because those counts *are* the divisor function, so it is a **relabelling of known equivalent forms**, with no new method or evidence.

**Conclusion: no new result concerning the Riemann hypothesis has been established.**

---

## 15. Open problems (mathematical)

1. **Approximate fitting:** which extra conditions make a coarsest approximate width well defined (02 §4.2)?
2. **"Style or feeling" (Statements 3, 14):** what formal invariant could express it?
3. **$H_1$ vs $H_2$, polygon vs staircase:** which best formalizes "high"? They give different prime–linearity behaviour.
4. **The restatement problem:** is there a natural musical counting function whose Dirichlet series is not elementarily built from $\zeta$ (03 §13)?

## 16. Final qualifications from ChatGPT's publication review

These also amend the detailed documents.

| # | Qualification | Amends |
|---|---|---|
| F1 | Refinement invariance of shape holds for the polygon (and for unchanged underlying $H_1$ trajectories), not for staircase samples. Counterexample: $(1,1)\to(2,2)$. | 02 Prop. 14 scope; 06 §4 |
| F2 | The M1 merger exists only under commensurability of $g_2$, $g_3$ and $\varphi_2-\varphi_3$ | 06 §3; restates 02 Prop. 7 |
| F3 | "The loops at each fixed state form a monoid." No exclusivity claim is made. | 04a M3; 06 §7 |

*End of the final summary. The original music machine remains stopped. Any future implementation would be a separate decision and a separate project.*
