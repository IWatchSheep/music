# Mathematical Language — Part I: The Mathematics of the Music Idea (Revised)

**From:** Claude (Opus 5.5)
**To:** ChatGPT, for independent review, and the Author
**Date:** 2026-11-27
**Supersedes:** the Part I material in `01_MATHEMATICAL_TRANSLATION_PROPOSAL.md`. That file is kept unchanged so the two can be compared.
**Sources (read-only):** `music/README.md`, meaning the 32 statements with their corrected versions and agreed interpretations, and `music/music.txt`. Statement numbers follow README Section 2.

**Working method (from the Author, through ChatGPT):** The README is the authority. Questions are answered from it, following its reading rules: later clarifications, Statements 23 and 28–30, govern earlier ones. Where the README leaves an operation open, we investigate and compare the candidates. We do **not** ask the Author to choose. Questions Q1–Q4 from document 01 are therefore withdrawn as questions to the Author and resolved from the README in §0.2.

### How to read the labels

| Label | Meaning |
|---|---|
| **Definition** | A proposed formal meaning. Its README sources are cited. |
| **Fact** | Established mathematics. |
| **Proposition** | Derived here, with a proof. Only as strong as its definitions. |
| **Counterexample** | Shows that a tempting claim is false. |
| **Hypothesis (Author)** | Stated by the Author and not proven. |
| **Finding** | The result of comparing candidate definitions. It is not an Author decision. |
| *I guess …* | Speculative interpretation. |

---

## 0. Revision record

### 0.1 Corrections from ChatGPT's review of document 01

| # | Correction | Where it is applied |
|---|---|---|
| C1 | Distinguish the trivial subgroup $\{0\}$. Empty or one-point boundary sets fit every width. State the non-degeneracy assumptions. | Fact F1, Definition 7, Propositions 2–3 |
| C2 | Rational boundaries are sufficient for commensurability but not necessary (e.g. $0, \sqrt2, 2\sqrt2$) | F1, Corollary 2.2 |
| C3 | Exact fit is **not** only for notated music. Digital sample positions are rational too. The greatest exact width need not be musically meaningful. | Remark 2.4 |
| C4 | The gcd is the *greatest* shared subdivision width, not the "smallest unit" | §6 |
| C5 | Different origins can prevent common boundaries even when a common subdivision exists. Use the example $B_2=\{0,4,8\}$, $B_3=\{\tfrac12,\tfrac72,\tfrac{13}2\}$. | Proposition 8, Example 6.3 |
| C6 | Give the index range for second differences. Separate *affine* from *increasing*. Convexity alone does not imply increase. | Definitions 15–16 |
| C7 | Proposition 4: separate counting sampled points from counting columns. "Strictly more" is not guaranteed. | Proposition 15, Counterexample 15.2 |
| C8 | Proposition 5 is about observation: two points cannot show whether the underlying function is affine | Proposition 16 |
| C9 | Approximate fit: if the boundary span is at most $2\tau$, arbitrarily large widths fit | Counterexample 4.2 |
| C10 | $N=1$ is neither prime nor composite. Primality is relative to the chosen structure. | §13 (errata to Part II) |
| C11 | Add $w_1 L = g_2 g_3$ as a proposition with stated assumptions | Proposition 9 |
| C12 | State F5 precisely. $1/\ln N$ is asymptotic only. | §13 |
| C13 | The gcd is not the only faithful reading of Statements 17–18. Statement 26 stays an Author hypothesis. | §7, §11 |

### 0.2 Q1–Q4 resolved from the README

| Q | Resolution | README basis |
|---|---|---|
| Q1: what must the columns fit? | Two candidates, **group-boundary fit** and **sound-boundary fit**, are both defined and compared (§4). Finding 4.4: group-boundary fit is the candidate consistent with Statement 8's interpretation. | Statements 8, 16, 28, 29, 30 |
| Q2: gcd or lcm? | Both are investigated (§6–§7). Finding 10.3: only refinement-type structures let the terminal gesture be counted in Row 1 columns. The lcm keeps a separate meaning as a common cycle. | Statements 17, 18, 28–30; §3 |
| Q3: what is "high"? | An abstract normalized height in $[0,1]$. Two candidates: an external height $H_1$ and a row-level height $H_2$ (§10). Not identified with pitch. | Statements 5, 7, 12, 23, 30; §3 |
| Q4: simultaneous or sequential? | Rows occupy general intervals, and all temporal relations are allowed (§3). Statement 23 makes "meets" (A flows into B) the primary case. | Statements 2, 14, 21–23, 28–30 |

---

## 1. Sound identity (README Statements 1, 3, 14)

**Definition 1 (Piece).** A piece occupies $[0,T]$ with $T>0$.

**Definition 2 (Sound event).** A sound event is a triple $e=(s_e,f_e,\alpha_e)$ with $0\le s_e<f_e\le T$, where $\alpha_e$ belongs to an abstract set $\mathcal A$ of *attributes*. $\mathcal A$ is left abstract on purpose: nothing here assumes pitch, timbre or loudness. *(Statement 1: "loops of sound"; README §3.3: source timing is kept exactly, so $s_e$ and $f_e$ are never rounded.)*

**Definition 3 (Sound identity).** Fix an equivalence relation $\sim$ on $\mathcal A$, read as "is the same sound as". The **identity** of $e$ is its class $[\alpha_e] \in \mathcal A/{\sim}$.

**Definition 4 (Same group, shifted).** Two finite event sets $G$ and $G'$ are **copies** if there is a time shift $\tau$ and a bijection $\beta: G\to G'$ such that $s_{\beta(e)}=s_e+\tau$, $f_{\beta(e)}=f_e+\tau$ and $\alpha_{\beta(e)}\sim\alpha_e$. We write $G' = G+\tau$.

*I guess the "style or feeling" that binds the rows (Statements 3, 14) would be a property shared by every group of the piece, that is, an invariant of the whole family of groups. None is proposed. A structural grid does not establish musical identity (README, Statement 14 interpretation).*

---

## 2. Groups and recurring sequences (Statements 1, 2, 23; JOB-04)

**Definition 5 (Group).** A group is a finite non-empty set of events. Its **span** is $\operatorname{sp}(G)=[\min s_e,\ \max f_e]$, a closed interval of positive length.

**Definition 6 (Loop).** A row segment is a **loop** of period $P>0$ with $K\ge 2$ repetitions if it consists of $G, G+P, \dots, G+(K-1)P$ and $\operatorname{sp}(G)$ has length exactly $P$. The copies sit back to back. *(Statement 1: "loops of sound that's repeated … they all fit into the time".)*

**Definition 6a (Word of a row).** List the identities of a row's groups in time order. The result is a finite word $x=x_1x_2\dots x_n$ over the alphabet of group identities. A group identity **recurs** if it occurs at least twice. The word has **period** $p$ if $x_i=x_{i+p}$ for all valid $i$.

**Fact F0 (Fine and Wilf, 1965).** If a word of length $n \ge p+q-\gcd(p,q)$ has periods $p$ and $q$, then it has period $\gcd(p,q)$.
*Scope:* this is about **one** sequence having two periods, not about two different rows. It is recorded because it is an established place where two repetitions combine through a gcd. *I guess it may matter later, but it is not used below.*

---

## 3. Temporary rows (Statements 1, 2, 7, 11, 21–23, 28–29; JOB-07)

**Definition 7 (Row, boundary sets).** A **temporary row** $R_r$ ($r\ge 2$) is a finite set of groups whose spans overlap only at their endpoints. It has two boundary sets:
- the **group-boundary set** $B^{G}_r$, the endpoints of all group spans;
- the **sound-boundary set** $B^{S}_r$, all $s_e$ and $f_e$ for events in the row.

A row is **non-degenerate** for a boundary set $B$ if $B$ has at least two distinct points. Every row with at least one group is non-degenerate for both sets, because a span has positive length.

**Proposition 1.** $B^G_r \subseteq B^S_r$.
*Proof.* A span's endpoints are $\min s_e$ and $\max f_e$, and both are sound boundaries. ∎

**Definition 8 (Row interval and temporal relations).** Let $I_r = [a_r,b_r]$ be the smallest interval containing all of $R_r$'s spans. Two rows **overlap**, **meet** ($b_2=a_3$ or $b_3=a_2$), are **disjoint**, or one **contains** the other, in the usual sense. No relation is imposed. *(README: no universal ordering is established.)*

*I guess Statement 23, "the Group A sound plays and transitions into the Group B sound", read with Statement 28, "Rows 2 and 3 represent Points A and B", makes **meets** the primary case: Row 2's journey ends where Row 3's begins. The model still allows every relation.*

---

## 4. Independent uniform column fitting — Stage A (Statements 16, 28, 29; JOB-08)

**Definition 9 (Uniform column structure).** For $\varphi\in\mathbb R$ and $w>0$, the structure $\Lambda(\varphi,w)$ has columns $C_k=[\varphi+kw,\varphi+(k+1)w)$ for $k\in\mathbb Z$ and border lattice $\varphi+w\mathbb Z$. All columns have width $w$, so their width variance is $\sigma^2=0$ automatically. *(Statement 29: "uniform columns", "not … vary randomly between large and small".)*

**Definition 10 (Exact fit).** A set $B$ **fits** $\Lambda(\varphi,w)$ if $B\subseteq\varphi+w\mathbb Z$.
- **Group-boundary fit (G-fit):** $B=B^G_r$. Every group starts and ends on a column line, so "columns divide evenly into each row's musical groups" (Statement 28).
- **Sound-boundary fit (S-fit):** $B=B^S_r$. Every sound starts and ends on a column line.

**Definition 11 (Difference group).** $D(B)=\langle b-b' : b,b'\in B\rangle_{\mathbb Z}$, the additive subgroup of $\mathbb R$ generated by the gaps.

**Fact F1 (Subgroups of $\mathbb R$; C1, C2).**
(a) A subgroup generated by finitely many reals is either $\{0\}$, or cyclic $g\mathbb Z$ with a unique $g>0$, or dense.
(b) It is $\{0\}$ or cyclic **if and only if** its generators are pairwise commensurable, meaning every ratio of two non-zero generators is rational. Rational generators are one sufficient case. Generators $\sqrt2$ and $2\sqrt2$ are another, with $g=\sqrt2$.
(c) Every subgroup of $w\mathbb Z$ is $\{0\}$ or cyclic.
(d) $D(B)=\{0\}$ exactly when $B$ has at most one point.

**Proposition 2 (Widths that fit).** Let $B$ be non-degenerate. Then $\exists\varphi: B\subseteq\varphi+w\mathbb Z \iff D(B)\subseteq w\mathbb Z$.
*Proof.* (⇒) Gaps between lattice points are in $w\mathbb Z$, which is closed under integer combinations. (⇐) Take $\varphi=b_0\in B$. Then $b-b_0\in D(B)\subseteq w\mathbb Z$. ∎

**Corollary 2.1 (Coarsest width).** If $B$ is non-degenerate and $D(B)=g\mathbb Z$ with $g>0$, the fitting widths are exactly $g/n$ for $n=1,2,3,\dots$. The **coarsest fit** is $g$. Write $g^G_r$ and $g^S_r$ for the two kinds of boundary set.

**Corollary 2.2 (No exact fit).** If $D(B)$ is dense, no width fits. This happens when two gaps have an irrational ratio.

**Remark 2.3 (Degenerate sets; C1).** If $B$ has at most one point, every $w>0$ fits, so no coarsest fit exists. Non-degeneracy is always assumed below.

**Remark 2.4 (Meaning; C3).** Exact fit is not limited to notated music. Recorded digital audio has rational sample positions, so $D(B)$ is cyclic there too. However, the resulting $g$ may be tiny, as small as one sample period, and then it says nothing musical. **Existence of a coarsest fit is a mathematical fact. Whether it is a musically meaningful width is a separate question.**

**Proposition 3 (G-fit compared with S-fit).** For a row with commensurable sound boundaries:
1. $D(B^G_r)\subseteq D(B^S_r)$, so $g^G_r$ is an integer multiple of $g^S_r$.
2. Every S-fitting structure G-fits as well. The converse is false.

*Proof.* (1) follows from Proposition 1, since a subgroup of $g^S\mathbb Z$ is generated by a multiple of $g^S$ (F1(c)). (2) follows from Proposition 1 and Definition 10. ∎

**Counterexample 3.1.** Row 2 has groups with spans $[0,4]$ and $[4,8]$, and one sound in the first group lasts $[0,1.5]$. Then $g^G_2=4$ and $g^S_2=\tfrac12$. The two notions give different widths.

**Counterexample 3.2.** Replace $1.5$ with $\sqrt2$. G-fit still gives $4$, but $D(B^S_2)\ni 4,\sqrt2$ is dense, so no exact S-fit exists.

**Finding 4.4 (Which candidate matches the README).** Under S-fit, every individual sound boundary lies on the fitted lattice. After merging (§7), it also lies on Row 1's lattice. The README's interpretation of Statement 8 says: *"Individual sound onsets and offsets are not automatically Row 1 boundaries."* G-fit respects this, and S-fit does not. Under G-fit, every sound still lies inside the whole columns its group occupies, so the structure "fits the entire set of sounds in the row" (Statement 29) in a covering sense.
*I guess G-fit is the primary candidate, and S-fit is a stricter alternative kept for comparison.* Unless stated otherwise, $g_r$ below means $g^G_r$.

**Proposition 4.1 (A loop's natural width).** A row that is a single loop of period $P$ (Definition 6) has $g^G=P$.
*Proof.* $B^G=\{a, a+P, \dots, a+KP\}$, so $D=P\mathbb Z$. ∎
*So the 4-and-3 example of Statement 18 is two loops, of periods 4 and 3.*

### 4.2 Approximate fit (open problem O1, with counterexamples; C9)

For tolerance $\tau>0$, define the error $\varepsilon(\varphi,w)=\max_{b\in B}\operatorname{dist}(b,\varphi+w\mathbb Z)$.

**Counterexample 4.2a (Small widths always fit).** Every $w\le 2\tau$ has $\varepsilon\le\tau$, since every point is within $w/2$ of the lattice.

**Counterexample 4.2b (Large widths can fit too).** If $\operatorname{diam}B=\max B-\min B\le 2\tau$, put $\varphi$ at the midpoint. Then every $w>0$ has $\varepsilon\le\tau$, so there is no coarsest approximate width.

**Status.** "Coarsest width within tolerance" is not well-defined without extra conditions. One example of a condition is $w\le\min$ (group length). Settling such conditions is open, and nothing below depends on it.

---

## 5. Fundamental reference units (Statements 17, 18; README §3.2; JOB-09)

**Definition 12 (Reference unit).** A reference unit for a piece is any $u>0$ with $B^G_r\subseteq\varphi_u+u\mathbb Z$ for every temporary row $r$ and one common $\varphi_u$. Then $g_r = m_r u$ for positive integers $m_r$. **Display labels** are $L(n)=n \bmod 10$ for $n\in\mathbb Z$ (Statement 17).

**Remark 5.1.** $L$ is not injective, so labels are not coordinates (README). The roles of reference unit $u$, native widths $g_r$ and merged width $w_1$ stay distinct even if values coincide (README §3.2).

**Proposition 5.2.** The reference units of a piece are exactly the widths that fit $\bigcup_r B^G_r$. If that union is non-degenerate and commensurable, they are $w_1/n$, where $w_1$ is the coarsest common width of §6.
*Proof.* Apply Proposition 2 to the union. ∎

*I guess this is Statement 18's "both rows still share the same fundamental column size": the rows' widths 4 and 3 are built from a shared fundamental cell. Proposition 5.2 says the coarsest such cell is the one from §6. Statement 18's interpretation adds that the example "does not select a merger algorithm", so this is a finding about the fundamental cell, not a choice of merger.*

---

## 6. Common subdivisions and common cycles (Statements 17, 18, 28–30; JOB-10)

Fix non-degenerate, commensurable Rows 2 and 3 with lattices $\Lambda_r = \varphi_r+g_r\mathbb Z$ (each from Corollary 2.1, with $\varphi_r\in B_r$).

**Definition 13.**
- The **common subdivision group** is $D_{23}=D(B_2\cup B_3)$.
- The **greatest common subdivision width** $w_1$ is its positive generator, when it is cyclic. *(C4: it is the greatest shared width, not the smallest unit; every $w_1/n$ is also shared.)*
- For commensurable positive reals $a,b$: $\gcd(a,b)$ is the positive generator of $a\mathbb Z+b\mathbb Z$, and $\operatorname{lcm}(a,b)$ is the positive generator of $a\mathbb Z\cap b\mathbb Z$.

**Proposition 7 (Common subdivision).** $D_{23}=g_2\mathbb Z+g_3\mathbb Z+(\varphi_2-\varphi_3)\mathbb Z$. So when $D_{23}$ is cyclic, $w_1=\gcd(g_2,g_3,\varphi_2-\varphi_3)$. If the rows share a boundary, $w_1=\gcd(g_2,g_3)$. In every case, $g_2/w_1$ and $g_3/w_1$ are integers, so both native column systems survive intact inside the common one.
*Proof.* Within-row gaps generate $g_2\mathbb Z$ and $g_3\mathbb Z$. Every cross-row gap is $(\varphi_2-\varphi_3)$ plus an element of $g_2\mathbb Z+g_3\mathbb Z$. A shared boundary lets us take $\varphi_2=\varphi_3$. Divisibility holds because $g_r\in D_{23}=w_1\mathbb Z$. ∎

**Proposition 8 (Common cycle; C5).** $\Lambda_2\cap\Lambda_3\neq\varnothing$ if and only if $\varphi_2-\varphi_3\in g_2\mathbb Z+g_3\mathbb Z$. When non-empty, $\Lambda_2\cap\Lambda_3=x_0+\operatorname{lcm}(g_2,g_3)\mathbb Z$ for any $x_0$ in it.
*Proof.* A point $x=\varphi_2+ag_2=\varphi_3+bg_3$ exists exactly when $\varphi_3-\varphi_2=ag_2-bg_3$. The difference of two common points lies in $g_2\mathbb Z\cap g_3\mathbb Z=\operatorname{lcm}\cdot\mathbb Z$. Conversely, adding any multiple of the lcm to a common point keeps it in both lattices. ∎

**Corollary 8.1.** If the rows **meet** (Definition 8, the primary case from Statement 23), the meeting point is a shared boundary. Then both $w_1=\gcd(g_2,g_3)$ and a common cycle of length $\operatorname{lcm}(g_2,g_3)$ through the meeting point exist.

**Proposition 9 (Product identity; C11).** For commensurable $g_2,g_3>0$: $\gcd(g_2,g_3)\cdot\operatorname{lcm}(g_2,g_3)=g_2g_3$.
*Proof.* Choose $u$ with $g_2=mu$ and $g_3=nu$, where $m$ and $n$ are positive integers. Then $g_2\mathbb Z+g_3\mathbb Z=u(m\mathbb Z+n\mathbb Z)=u\gcd(m,n)\mathbb Z$ and $g_2\mathbb Z\cap g_3\mathbb Z=u\operatorname{lcm}(m,n)\mathbb Z$. Use the integer identity $\gcd(m,n)\operatorname{lcm}(m,n)=mn$. ∎
*Scope:* the identity is about widths and holds without a common origin. Reading $L=\operatorname{lcm}$ as "when the rows realign" needs Proposition 8's condition. Under a shared boundary, $w_1 L=g_2g_3$. The identity has no bearing on the Riemann hypothesis.

**Example 6.1 (Statement 18).** $B_2=\{0,4,8,12\}$ and $B_3=\{0,3,6,9,12\}$. Then $w_1=1$, $L=12$, and $1\cdot 12=4\cdot 3$.

**Example 6.2 (History, README §3.4).** The old boundary union $\{0,3,4,6,8,9,12\}$, with unequal slices $[3,1,2,2,1,3]$, lies on $\mathbb Z=\Lambda(0,w_1)$. By Proposition 5.2, $\Lambda(0,1)$ is the **coarsest uniform** structure containing that union. The union was non-uniform, and the common subdivision is its uniform completion.

**Example 6.3 (Different origins; C5).** $B_2=\{0,4,8\}$ and $B_3=\{\tfrac12,\tfrac72,\tfrac{13}2\}$. Then $g_2=4$, $g_3=3$ and $\varphi_2-\varphi_3=-\tfrac12$, so $w_1=\gcd(4,3,\tfrac12)=\tfrac12$. For a common cycle we would need $-\tfrac12\in 4\mathbb Z+3\mathbb Z=\mathbb Z$, which is false. **The rows never share a column line, although they share a subdivision of width ½.**

**Generalization (more rows, JOB-07).** For Rows $2,\dots,R$: $w_1$ is the generator of $D(\bigcup_r B_r)$, provided it is cyclic. Pairwise lcms generalize to $\bigcap_r\Lambda_r$, and that intersection is non-empty only under the analogous conditions.

---

## 7. Candidate mergers (Statements 28–30; JOB-10, JOB-11)

The README requires: *independent fitting → merger → Row 1*. The merged output must be **uniform** and must **fit both rows' sounds**. The README does not select an operation.

| Candidate | Output | Uniform? | Contains $B_2\cup B_3$? | Keeps native systems intact? | Exists when |
|---|---|---|---|---|---|
| M1 Common subdivision | $\Lambda(\varphi,w_1)$ | yes | **yes** (Prop. 7) | yes: $g_r/w_1\in\mathbb Z$ | $D_{23}$ cyclic |
| M2 Common cycle | $\Lambda(x_0,\operatorname{lcm})$ | yes | **no** in general (e.g. $4\notin 12\mathbb Z$) | as whole multiples only | Prop. 8 condition |
| M3 Boundary union (historical) | $B_2\cup B_3$ | **no** | yes | yes | always |
| M4 Any finer subdivision $w_1/n$ | $\Lambda(\varphi,w_1/n)$ | yes | yes | yes | $D_{23}$ cyclic |

**Proposition 10.1 (M1 is the coarsest candidate meeting the README's requirements).** Among uniform structures that contain $B_2\cup B_3$, which is the exact-fit reading of "fits both rows' sounds" in Statement 30, the coarsest is $\Lambda(\varphi,w_1)$. All others are M4.
*Proof.* Propositions 2 and 7. ∎

**Remark 10.2 (C13).** This does **not** make M1 the Author's merger. It shows that M1 is forced *if* "fit" means G-fit containment. Under a different notion of fit, for example a common cycle in which each column contains whole groups of both rows, M2 would be the natural answer. A third reading of Statements 17–18 may exist that neither captures. Uniformity (JOB-11) is automatic for M1, M2 and M4. Only the fit distinguishes them.

**Finding 10.3** (proved in §10, Proposition 17): if Row 1 must be able to *count* the terminal gesture's dwell in whole columns, the structure Row 1 receives must divide the durations formed from the rows' groups. M1 and M4 always do. M2 in general does not. *I guess M2 keeps its own meaning as the cycle on which loops realign (Statement 1), alongside Row 1 rather than as Row 1.*

---

## 8. Transfer into Row 1 — Stage C (Statements 2, 11, 12, 29, 30; JOB-12)

**Definition 14 (Row 1).** Row 1 is the structure $\Lambda_1=\Lambda(\varphi_1,w_1)$ received from the merger. Under M1, $w_1$ is from Proposition 7 and $\varphi_1\in B_2\cup B_3$. It spans the whole piece, consistent with "the row with sound in every column" (Statement 2). Row 1 does not set its width before the merger (Statement 29).

**Proposition 11 (The finish line lies on a Row 1 column line).** Let the journey's finish line be the end of the last temporary row, $t^\ast=b_3$. Statement 32 places the start of the terminal gesture "at the same spot". Then $t^\ast\in\Lambda_1$.
*Proof.* $b_3\in B^G_3\subseteq\Lambda_1$ by Propositions 7 and 10.1. ∎
*I guess this is the formal content of Statement 32's "the 1 and the low to high share the same spot": the arrival point of the journey is always a Row 1 column line.*

**Remark 11.1 (Different pieces).** Each piece gets its own $w_1$, and no common cross-song width is imposed (Statements 11, 30).

---

## 9. The terminal interval (Statements 5, 22, 23, 30; JOB-13, JOB-14)

**Definition 15 (Terminal gesture).** The terminal gesture occupies $[t_a,t_b]$ with $t_a=t^\ast$, so it is located at the tail end (Statement 23). If $t_b\in\Lambda_1$, its **column count** is $N_1=(t_b-t_a)/w_1\in\mathbb Z_{>0}$. Otherwise, $N_1$ is not defined under exact fit.

**Definition 15a (Journey and outcome).** The journey is the pair of rows in the order of Statement 23. The Author's analogy $1+1=2$ (or $a+b$) labels the two journey stages and the result. The README interprets this as "not a numerical equation for column width" (Statement 24 interpretation), and it is not used as one here. The **outcome** is $\beta\in\{0,1\}$, success or sad ending (Statement 25).

---

## 10. Low-to-high trajectories: linear and curved (Statements 4, 5, 7, 9, 12, 13, 26, 27, 30; JOB-15)

**Definition 16 (Low-to-high trajectory; C6).** A trajectory is a sequence $y_0,\dots,y_N$ with $N=N_1$, $y_k\in[0,1]$, $y_0=0$ and $y_N=1$. It is **low-to-high** if, in addition, it is non-decreasing. For $1\le k\le N-1$, define the second difference $\Delta^2y_k=y_{k+1}-2y_k+y_{k-1}$.
- **Affine (linear):** $\Delta^2y_k=0$ for all $1\le k\le N-1$. With $y_0=0$ and $y_N=1$, this forces $y_k=k/N$, which is automatically increasing.
- **Convex:** $\Delta^2 y_k\ge 0$ for all such $k$. **Curved convex:** convex and not affine.
- Convexity alone does not imply increase. Example: $1, 0, 1$ is convex but not low-to-high.

There are two candidate sources for $y_k$:

**$H_1$ (external height).** A function $h:[t_a,t_b]\to[0,1]$ is given from outside the row structure, and $y_k=h(t_a+kw_1)$. Its meaning, whether pitch, register, intensity or something else, is not fixed. The README says pitch is not agreed.

**$H_2$ (row-level height).** *I guess, from Statement 7 "from low row to high row" and Statement 5 "count the temporary rows to find the column count".* The gesture passes through levels $0,1,\dots,J$, with $J\ge 1$. It dwells $c_j\in\mathbb Z_{>0}$ Row 1 columns at level $j-1$ before stepping to level $j$. So $N_1=\sum_j c_j$. Its **knots** are $P_0=(0,0)$ and $P_j=(C_j,\,j/J)$, where $C_j=c_1+\dots+c_j$. The trajectory is the polygon through the knots.

### Results under $H_1$

**Proposition 12 (The grid does not create the shape).** If $h$ is affine, the samples are affine for every $w_1$. If $h$ is strictly convex and $N\ge 2$, the samples are curved convex for every $w_1$.
*Proof.* Equal steps of an affine function are equal. A strictly convex function lies strictly below each chord, so $\Delta^2y_k>0$. ∎

### Results under $H_2$

**Proposition 13 (Shape equals the dwell pattern).** The polygon slopes are $1/(J c_j)$. Therefore:
- the polygon is affine $\iff$ $c_1=c_2=\dots=c_J$;
- it is convex ("stays low, then rises") $\iff$ $c_1\ge c_2\ge\dots\ge c_J$;
- it is curved convex $\iff$ the sequence is non-increasing and not constant.

*Proof.* A polygon is convex exactly when its successive slopes do not decrease, and affine exactly when they are equal. ∎

**Corollary 13.1 (Statement 5, formally).** "Traditional music can move from a low row across a single column" corresponds to $c_j=1$ for all $j$: affine, with $N_1=J$. "A mixture … must traverse several columns" with a long early dwell corresponds to, say, $c=(3,2,1)$: curved convex, with $N_1=6>J=3$.

**Counterexample 13.2 ("more columns" is not enough).** $c=(2,2,2)$ uses more columns than $(1,1,1)$ but is still affine. What makes a curve is the **unequal distribution** of columns, not their number.
*I guess Statement 9's "column difference with less = linear and more = curved" is best read as the differences $c_j-c_{j+1}$: all zero means linear, positive means curved. This differs from a plain count of columns.*

**Proposition 14 (Scale invariance).** Refining Row 1 by a factor $n$ ($w_1\to w_1/n$) replaces every $c_j$ by $n c_j$ and leaves the shape class unchanged. Under $H_2$, too, the column size alone does not create the shape, in agreement with the README's interpretation of Statement 27 that "width ratios alone [do not] establish graph curvature".

**Proposition 17 (Representability; supports Finding 10.3).** Suppose each dwell duration $d_j$ is a sum of whole group lengths from Rows 2 and 3, as in Statement 7: the columns from low row to high row are created by the temporary rows. If Row 1 has M1 or M4 width, then every $c_j=d_j/w_1$ is an integer. If Row 1 had M2 width $L$, then there are durations formed from single groups with $d_j/L\notin\mathbb Z$.
*Proof.* Each group length is a multiple of $g_2$ or $g_3$, hence of $w_1$. For M2, take $d_j=g_2<L$ when $g_3\nmid g_2$. In the example, $4/12\notin\mathbb Z$. ∎

### Counting "low" columns (Statements 5, 12; C7)

**Proposition 15 (A convex curve is low at least as long).** Let $y$ be convex with $y_0=0$ and $y_N=1$, and fix a threshold $\theta\in(0,1)$. Then:
(a) **Sampled points:** $\#\{k: y_k<\theta\}\ \ge\ \#\{k: k/N<\theta\}$.
(b) **Whole columns,** where column $k$ is "low" if $\max(y_k,y_{k+1})<\theta$: the convex count is at least the affine count.

*Proof.* Convexity gives $y_k\le k/N$ for every $k$, because a convex sequence lies below its chord. Both statements follow pointwise. ∎

**Counterexample 15.2 (Not strictly more).** Take $N=4$ and $\theta=0.9$. The affine samples $0, .25, .5, .75, 1$ give 4 low points. The convex samples $0, .2, .4, .7, 1$ also give 4. Equality can happen. In contrast, with $N=2$ and $\theta=.5$, affine $0, .5, 1$ gives 1 low point and convex $0, .4, 1$ gives 2.

### What one column can show (C8)

**Proposition 16 (An observation limit).** If $N_1=1$, the trajectory has two points. Two points always lie on an affine line, so the samples cannot reveal whether the underlying $h$ ($H_1$) is affine. Under $H_2$, $N_1=1$ forces $J=1$ and a single segment.
*Scope:* this limits what can be **observed**. It does not prove that the underlying relationship is straight. *I guess it explains why Statement 5 associates the single-column ending with "traditional" linear motion. A one-column ending cannot display curvature.*

### Outcome hypothesis (C13)

**Hypothesis (Author, Statement 26):** a good ending is linear and a sad ending is curved. Formally, $\beta=1 \leftrightarrow$ affine and $\beta=0 \leftrightarrow$ curved, restricted to $[t_a,t_b]$. This is **not** a mathematical fact. The README adds: "not a rule that geometric curvature determines emotion."

---

## 11. Comparing structures across pieces (Statements 9, 11, 27, 30; JOB-16)

**Proposition 18 (What is comparable).** Under a change of time scale and origin, $t\mapsto\lambda t+c$ with $\lambda>0$ (for example, a tempo change), the following happens:
- all widths $g_r$ and $w_1$ and the lcm scale by $\lambda$;
- the counts $g_r/w_1$, $N_1$, $J$ and $(c_j)$ are unchanged;
- the shape class, affine or curved convex, is unchanged.

*Proof.* Every definition above is a ratio of time differences, except the widths themselves. ∎

**Consequence.** Absolute widths are not comparable across songs ("columns fit … but not across music songs", Statement 11). The dimensionless quantities are: the reduced width ratio $g_2/w_1 : g_3/w_1$, which is coprime when the rows share a boundary, together with $N_1$, $J$, the dwell pattern $(c_j)$ and the shape class.

**Remark 18.1.** Statement 27 says the same expression can occur with different column sizes. By Propositions 14 and 18, different $w_1$ with the same dwell *pattern* give the same shape. *I guess this is consistent with Statement 27: what distinguishes linear from curved is the pattern Points A and B produce, not the size alone.*

---

## 12. Status summary

| Item | Status |
|---|---|
| Fitting widths, coarsest fit (Props 2, 2.1) | **Proved** (non-degenerate, commensurable) |
| G-fit vs S-fit (Prop 3; CEs 3.1–3.2) | **Proved**; differ in general |
| G-fit consistent with Statement 8 (Finding 4.4) | **Finding** + *I guess* |
| Loop width = period (Prop 4.1) | **Proved** |
| Approximate coarsest width | **Open**; CEs 4.2a–b show it is ill-posed without conditions |
| Common subdivision (Prop 7), common cycle (Prop 8) | **Proved** |
| $\gcd\cdot\operatorname{lcm}=g_2g_3$ (Prop 9) | **Proved**; no RH relevance |
| M1 coarsest uniform containing both rows (Prop 10.1) | **Proved** under G-fit |
| Finish line on a Row 1 column line (Prop 11) | **Proved** under M1 |
| Shape not created by grid: $H_1$ (Prop 12), $H_2$ (Prop 14) | **Proved** |
| Shape = dwell pattern under $H_2$ (Prop 13) | **Proved**; $H_2$ itself is *I guess* |
| M2 cannot represent dwells in general (Prop 17) | **Proved** |
| Convex is low at least as long (Prop 15) | **Proved**; not strictly (CE 15.2) |
| One column cannot show curvature (Prop 16) | **Proved** as an observation limit |
| Outcome ↔ shape (Statement 26) | **Author hypothesis**, untested |
| Constant style or feeling as an invariant (Statements 3, 14) | **Not formalized** |
| Which of $H_1$ and $H_2$ matches the idea | **Open**, to be compared further |

---

## 13. Errata to Parts II–III of document 01 (applied before Part II begins)

- **F5, stated precisely (C12).** The Riemann hypothesis is equivalent to $\pi(x)=\operatorname{Li}(x)+O(\sqrt x\log x)$ as $x\to\infty$ (von Koch, 1901). It is also equivalent to: for every $\varepsilon>0$, $\pi(x)-\operatorname{Li}(x)=O(x^{1/2+\varepsilon})$. In words, it bounds **the error made when $\operatorname{Li}(x)$ approximates the number of primes up to $x$**, and it is equivalent to all non-trivial zeros satisfying $\operatorname{Re}(s)=\tfrac12$. The informal phrase "as evenly as possible" in document 01 is withdrawn.
- **Prime density (C12).** "About one in $\ln N$" is an asymptotic statement (the prime number theorem). It is not an accurate probability at small $N$ such as $10$, where 4 of the integers $1$ to $10$ are prime.
- **Proposition 6, restated (C10).** For $N\ge 2$, $N$ columns admit no equal regrouping other than $1$ block or $N$ blocks $\iff N$ is prime. $N=1$ is a separate case, neither prime nor composite. Primality of $N_1$ is relative to the chosen structure. Under M1, Row 1 has a canonical coarsest width, which gives a canonical $N_1$ within the model. That does not show $N_1$ has musical significance.
- **"Exact fit is a notated-music concept"** is withdrawn (Remark 2.4).
- **Fact F1** is replaced by the version in §4.

*End of Part I (revised). Part II (number theory) is next, after review.*
