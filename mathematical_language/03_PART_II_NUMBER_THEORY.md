# Mathematical Language — Part II: Number Theory and the Riemann Hypothesis

**From:** Claude (Opus 5.5)
**To:** ChatGPT, for independent review, and the Author
**Date:** 2026-11-27
**Builds on:** `02_PART_I_MATHEMATICS_OF_MUSIC.md`, as corrected by `02a_PART_I_CORRECTIONS.md`.
**Authority for the Author's ideas:** `music/README.md`, Statements 17–18 and 28–32 and Section 11 (read-only).

### How to read the labels

| Label | Meaning |
|---|---|
| **Fact** | Established number theory, with a standard source. |
| **Proposition** | Derived here, with a proof. |
| **Identity** | An exact equation between two descriptions of the same quantity. |
| **Restatement** | A logically equivalent rewording of a known statement. It adds no new mathematical information. |
| **Analogy** | A likeness without equivalence. |
| **Conjecture** | Unproven. |
| *I guess …* | Speculative interpretation. |

---

## 0. Summary: how far the connection reaches

1. **Divisibility is the natural language of Part I.** Equal regroupings of $N_1$ columns are indexed by the divisors of $N_1$ (§4). Linear endings under the polygon model are also indexed by the divisors of $N_1$ (§5). So for a prime count $p$, the two divisors in $D(p)=\{1,p\}$ correspond **exactly** to the two possible linear endings (Proposition 5.2). *I guess this is the most faithful exact form of Statement 32 that the model supports.*
2. **Rows 2 and 3 enter through gcd, lcm and coprime factorization** (§6–§8). Measured in Row 1 columns, the two native widths are coprime and their product is the common cycle (Proposition 8.2).
3. **The zeta function genuinely appears.** It appears in the density $1/\zeta(2)$ of coprime pairs (§10) and in two exact Dirichlet-series identities (§11): $\zeta(s)^2$ counts linear endings, and $\zeta(s)^2/\zeta(2s)$ counts row-width pairs by their common cycle.
4. **None of this establishes a connection to the zeros.** Those series have zeros *because they are built from* $\zeta$. Rewriting the Riemann hypothesis in the model's vocabulary is possible (§12.2), but it is a **restatement**: a relabelling of divisor counting, with no new leverage. **The established relationship stops at divisibility, $\zeta(2)$, and formal identities among Dirichlet series.** Nothing in the row structure constrains where the non-trivial zeros lie.

---

## 1. Positive integers and divisibility

**Definition 1.1.** For positive integers $a$ and $n$, **$a$ divides $n$** ($a\mid n$) if $n=ab$ for some positive integer $b$. The **divisor set** is $D(n)=\{a: a\mid n\}$, and the **divisor count** is $\tau(n)=|D(n)|$.

**Fact 1.2.** $\tau$ is **multiplicative**: $\tau(mn)=\tau(m)\tau(n)$ when $\gcd(m,n)=1$. If $n=\prod p^{a_p}$, then $\tau(n)=\prod(a_p+1)$.

**Fact 1.3 (Divisibility as an order).** Under divisibility, the positive integers form a lattice. The meet of $m$ and $n$ is $\gcd(m,n)$ and the join is $\operatorname{lcm}(m,n)$. Writing $m=\prod p^{a_p}$ and $n=\prod p^{b_p}$:
$$\gcd(m,n)=\prod p^{\min(a_p,b_p)},\qquad \operatorname{lcm}(m,n)=\prod p^{\max(a_p,b_p)}.$$

---

## 2. Prime and composite column counts

**Definition 2.1.** An integer $N\ge2$ is **prime** if $\tau(N)=2$, so $D(N)=\{1,N\}$. It is **composite** if $\tau(N)\ge3$.

**Fact 2.2 (Fundamental theorem of arithmetic).** Every $N\ge2$ is a product of primes, uniquely up to order.

In Part I, $N_1=(t_b-t_a)/w_1$ is the number of Row 1 columns in the terminal gesture (02, Definition 15; 02a, K5). **$N_1$ is a positive integer. It is never assumed to be prime** (README Section 11.2.4).

---

## 3. The special role of the number 1

**Fact 3.1.** $1$ is neither prime nor composite. $D(1)=\{1\}$, $\tau(1)=1$, and $1$ divides every integer. Excluding $1$ from the primes is what makes the factorization in Fact 2.2 unique.

The number $1$ appears in Part I in several distinct roles, which must not be confused:

| Role | Where | Meaning |
|---|---|---|
| Finish line | Statement 32; 02 Prop. 11 | The README's reading: the endpoint at Point B, "the 1" |
| $N_1=1$ | 02 Prop. 16 | A one-column ending, which cannot show curvature |
| $J=1$ | §5 | A single transition from low to high |
| $c_j=1$ | 02a K6a | A transition that takes one column |
| $w_1$ in its own unit | §8 | Measured in Row 1 columns, a Row 1 column has length $1$ |
| $\gcd=1$ | §7 | Coprimality of the reduced native widths |

*I guess the README's reading, finish line = 1, is the primary one for Statement 32. The other roles are mathematical places where 1 also appears. They are recorded, not substituted for the Author's meaning.*

---

## 4. Equal-block factorization of the terminal columns

**Proposition 4.1.** The ways to divide $N$ consecutive columns into equal blocks of whole columns correspond one-to-one with $D(N)$: block size $d$ gives $N/d$ blocks. The number of ways is $\tau(N)$.
*Proof.* Equal blocks of $d$ columns tile $N$ columns exactly when $d\mid N$. ∎

**Corollary 4.2.** For $N\ge2$, the only equal regroupings are "one block" and "$N$ single columns" $\iff$ $N$ is prime. For $N=1$, there is only one regrouping, and the two cases coincide.

**Remark 4.3 (Relative to the structure).** $N_1$ depends on the width Row 1 receives. Under M1, the coarsest common subdivision, $N_1$ is canonical within the model. Refining by a factor $n\ge2$ multiplies $N_1$ by $n$ and destroys primality. Primality of $N_1$ is therefore a property of *(piece, model, M1)*, and it is not shown to be musically significant.

---

## 5. Linear endings and divisors: $N_1=Jc$

This section uses the row-level height $H_2$ from 02 §10, as corrected in 02a K6/K6a. Transition $j$ uses $c_j\in\mathbb Z_{>0}$ columns, there are $J$ equal-height transitions, and $N_1=c_1+\dots+c_J$. A finite sequence $(c_1,\dots,c_J)$ of positive integers with sum $N$ is a **composition** of $N$ into $J$ parts.

**Proposition 5.1 (ChatGPT; polygon model).** The polygon is affine $\iff$ all $c_j$ equal a common $c$, and then $N_1=Jc$. Consequently:
1. **Affine polygon structures with total $N$ correspond one-to-one with $D(N)$,** via $J\mapsto c=N/J$. There are $\tau(N)$ of them.
2. **If $N_1=p$ is prime**, the only affine structures are $(J,c)=(1,p)$ and $(p,1)$.
3. **If, in addition, $J\ge2$**, the only affine structure is $J=p$ with $c=1$.

*Proof.* The first sentence is 02, Proposition 13. Then (1) holds because $J$ determines $c=N/J$, which must be an integer. (2) and (3) follow from $D(p)=\{1,p\}$. ∎

**Proposition 5.2 (The divisors of $p$ are the two linear endings).** For prime $N_1=p$, the map $J\mapsto(J,\,p/J)$ is a bijection
$$D(p)=\{1,p\}\ \longleftrightarrow\ \{\text{one transition across all } p \text{ columns},\ \ p \text{ single-column transitions}\}.$$
*I guess this is an exact form of Statement 32's "can't be divided by anything but itself". The divisor $1$ is the single undivided rise, and the divisor $p$ is the fully stepwise rise. The README's own reading of the "1" as the finish line (Fact 3.1 table) is a separate, co-located role.*

**Proposition 5.3 (A prime count with intermediate levels forces curvature).** A linear polygon exists only if $J\mid N_1$. In particular, if $N_1=p$ is prime and $1<J<p$, then **every** structure is curved: convex, concave or mixed.
*Proof.* This is Proposition 5.1 with $J\notin D(p)$. ∎
*Example:* with $p=5$ and $J=2$, the compositions $(4,1),(3,2),(2,3),(1,4)$ are all curved.

**Counterexamples (ChatGPT; limits of 5.1–5.3).**
- A prime count does not force linearity: $(3,2)$ has $N=5$ and is convex.
- A composite count does not force curvature: $(2,2,2)$ has $N=6$ and is affine.

**Primality and curvature are different properties.** They are related exactly through the divisibility condition $J\mid N_1$.

**Staircase version (02a, K6a).** Under the staircase representation, "affine" holds iff all $c_j=1$, so $N_1=J$. That is possible for every $N_1$, prime or not. **The prime–linearity link of Propositions 5.1–5.3 holds for the polygon model, not the staircase model.** This is one concrete way the two representations differ.

**Proposition 5.4 (Counting all shapes).** Fix the total $N$ and let $J$ vary. Let $p(N)$ be the number of partitions of $N$, that is, the number of compositions with non-increasing parts. Then:

| Shape (polygon) | Condition on $c$ | Number of structures |
|---|---|---|
| all | any composition | $2^{N-1}$ |
| convex (includes affine) | non-increasing | $p(N)$ |
| concave (includes affine) | non-decreasing | $p(N)$ |
| affine | constant | $\tau(N)$ |
| mixed (neither) | — | $2^{N-1}-2p(N)+\tau(N)$ |

*Proof.* There are $2^{N-1}$ compositions of $N$ (a standard fact). Non-increasing compositions are partitions, and reversing them gives the non-decreasing ones. A composition is both non-increasing and non-decreasing iff it is constant. The mixed count follows by inclusion–exclusion. ∎
*Check:* $N=3$ gives $4-6+2=0$ mixed. $N=4$ gives $8-10+3=1$ mixed, namely $(1,2,1)$. *(Confirms 02a K9.)*
*Observation:* $\tau(N)$ grows slower than any power of $N$, while $2^{N-1}$ grows exponentially. As $N$ grows, linear endings become a vanishing fraction of all endings. This is pure counting. It is not a musical probability, because no probability model of music is assumed.

---

## 6. Greatest common divisors and least common multiples

The rows are as in 02 §6, with native widths $g_2$ and $g_3$, commensurable.

**Fact 6.1 (Bézout).** For positive integers $m$ and $n$, there are integers $a$ and $b$ with $am+bn=\gcd(m,n)$. For commensurable reals, the same holds with $\gcd(g_2,g_3)=ag_2+bg_3$. This is the definition used in 02, Definition 13.

*Example:* $1=1\cdot4+(-1)\cdot3$.
*I guess this gives a precise sense to Statement 12's "Row 1 … goes into different rows through row addition". The Row 1 width is an integer combination, sums and differences, of the native widths. This is an analogy for the Author's phrase, not its established meaning.*

**Fact 6.2.** $\gcd(m,n)\operatorname{lcm}(m,n)=mn$. With Fact 1.3, this follows from $\min(a,b)+\max(a,b)=a+b$, which gives a second proof of 02, Proposition 9.

**Example 6.3 (Exponents).** Take $g_2=12$ and $g_3=18$ in some unit $u$. Then $12=2^2 3$ and $18=2\cdot3^2$, so $\gcd=2\cdot3=6$ and $\operatorname{lcm}=2^2 3^2=36$, and $6\cdot36=12\cdot18$. **The merger M1 takes the minimum exponent of each prime, and the cycle M2 takes the maximum** (Fact 1.3).

---

## 7. Reduced ratios and coprimality

**Proposition 7.1 (Reduction artifact; README Section 11.2.2).** For any positive integers $m$ and $n$, the reduced pair $m'=m/\gcd(m,n)$ and $n'=n/\gcd(m,n)$ is coprime. Finding that a reduced ratio is coprime therefore carries **no information**.

**Proposition 7.2 (Coprimality depends on the unit).** Let $g_2$ and $g_3$ be commensurable with a shared boundary, and let $w_1=\gcd(g_2,g_3)$. In the unit $u=w_1/k$, for $k\in\mathbb Z_{>0}$, we have $\gcd(g_2/u,\ g_3/u)=k$. So the rows are coprime in the unit $w_1$, and have gcd $k$ in the unit $w_1/k$.
*Proof.* $g_r/u=k\,g_r/w_1$, and $\gcd(k m',k n')=k\gcd(m',n')=k$. ∎

**Consequence.** "Rows 2 and 3 are coprime" is meaningful only relative to a unit fixed *outside* the merger, such as a MIDI tick, a beat or a 100 ms reference cell (02 §5). Every number-theoretic statement about $g_2$ and $g_3$ in §10–§11 must name its unit.

---

## 8. Factorization in Row 1 units: how Rows 2 and 3 enter

**Definition 8.1.** Measure in **Row 1 columns**, with $u=w_1$. Write $m'=g_2/w_1$ and $n'=g_3/w_1$, and let $\ell=\operatorname{lcm}(g_2,g_3)/w_1$ be the common cycle in Row 1 columns. The rows share a boundary, which is the primary case from Statement 23 (02, Corollary 8.1).

**Proposition 8.2.** $\gcd(m',n')=1$ and $\ell=m'n'$.
*Proof.* Coprimality is Proposition 7.2 with $k=1$. Then $\operatorname{lcm}(m',n')=m'n'/\gcd(m',n')=m'n'$, and the lcm scales with the unit. ∎

**Proposition 8.3 (Which pairs of rows give a cycle $\ell$).** The ordered pairs $(m',n')$ of coprime positive integers with $m'n'=\ell$ correspond to the ways of giving each prime power of $\ell$ entirely to one row. There are $2^{\omega(\ell)}$ of them, where $\omega(\ell)$ is the number of distinct primes dividing $\ell$.
*Proof.* Coprimality means no prime divides both. Fact 2.2 then makes each full prime power go to exactly one of $m'$ and $n'$. ∎
*Example:* $\ell=12=2^2\cdot3$ has $\omega=2$, giving 4 pairs: $(1,12),(12,1),(4,3),(3,4)$. The pair $(2,6)$ is excluded, because it is not coprime and would mean a different $w_1$.

*I guess this is the clearest answer the model gives to "how would Rows 2 and 3 fit" (Statement 32). Measured in Row 1's own columns, the two temporary rows split the primes of the common cycle between them, with no prime shared. This is a structural fact of arithmetic. It is not yet related to the Riemann hypothesis.*

---

## 9. The Euler product

**Fact 9.1 (Euler).** For complex $s$ with $\operatorname{Re}(s)>1$:
$$\zeta(s)=\sum_{n=1}^\infty n^{-s}=\prod_{p\ \text{prime}}\big(1-p^{-s}\big)^{-1}.$$
Both sides converge absolutely. Their equality is the analytic form of unique factorization (Fact 2.2): expanding each factor $1+p^{-s}+p^{-2s}+\dots$ and multiplying out produces every $n^{-s}$ exactly once.

**Fact 9.2.** $\zeta$ extends to a meromorphic function on $\mathbb C$ whose only pole is a simple pole at $s=1$. It has **trivial zeros** at $-2,-4,-6,\dots$, and all other zeros, the **non-trivial** ones, lie in the strip $0<\operatorname{Re}(s)<1$. The Euler product itself converges only for $\operatorname{Re}(s)>1$, so **it does not describe the zeros**. They lie where the product is not available.

---

## 10. Coprimality and $\zeta(2)$

**Fact 10.1.** Let $C(X)=\#\{(m,n): 1\le m,n\le X,\ \gcd(m,n)=1\}$. Then $C(X)/X^2\to 1/\zeta(2)=6/\pi^2\approx0.6079$. More generally, the density of pairs with $\gcd=d$ is $1/(d^2\zeta(2))$.
*Sketch of the reason (heuristic; the rigorous proof uses Möbius inversion):* both numbers are divisible by $p$ "with probability" $1/p^2$, and multiplying over primes gives $\prod_p(1-p^{-2})=1/\zeta(2)$ by Fact 9.1 at $s=2$.

**Application to the model, with its conditions stated.** Fix an external unit $u$ (Proposition 7.2), and suppose the two native widths $m=g_2/u$ and $n=g_3/u$ ranged uniformly over $\{1,\dots,X\}$. Then the fraction of pairs whose merged width $w_1$ equals $u$ itself tends to $6/\pi^2$. **This is a statement about a probability model that we choose. It is not a property of music.** No distribution of row widths in actual music is established.

**This is where the honest relationship with $\zeta$ from Rows 2 and 3 stops: at the value $\zeta(2)$, a single point on the real axis.** The Riemann hypothesis concerns the zeros, which lie in the critical strip.

---

## 11. Two exact identities linking the model to $\zeta(s)$

**Definition 11.1.** A **Dirichlet series** is $F(s)=\sum_{N\ge1}a_N N^{-s}$. Multiplying two such series corresponds to **Dirichlet convolution**: $(a*b)_N=\sum_{Jc=N}a_Jb_c$.

**Identity 11.2 (Linear endings).** Let $a_N=\tau(N)$ be the number of affine polygon structures with total $N$ (Proposition 5.1). Then for $\operatorname{Re}(s)>1$:
$$\sum_{N\ge1}\tau(N)\,N^{-s}=\zeta(s)^2,$$
and, counting only the structures with $J\ge2$ and $c\ge2$ (neither a single transition nor single-column transitions),
$$\sum_{N\ge2}\big(\tau(N)-2\big)N^{-s}=\big(\zeta(s)-1\big)^2 .$$
*Proof.* $\tau(N)=\sum_{Jc=N}1$, so $\tau=\mathbf 1*\mathbf 1$ and its series is $\zeta\cdot\zeta$. For the second identity, $\zeta(s)-1=\sum_{n\ge2}n^{-s}$, and its square counts the factorizations $N=Jc$ with $J,c\ge2$. That number is $\tau(N)-2$ for $N\ge2$, and the $N=1$ term is $0$. ∎
**Consequence:** for $N\ge2$, the coefficient of $N^{-s}$ in $(\zeta(s)-1)^2$ is zero $\iff N$ is prime. *The primes are exactly the column counts that have no linear ending other than the two extreme ones.*

**Identity 11.3 (Row pairs by common cycle).** Proposition 8.3 counts $2^{\omega(\ell)}$ row pairs with cycle $\ell$. For $\operatorname{Re}(s)>1$:
$$\sum_{\ell\ge1}2^{\omega(\ell)}\,\ell^{-s}=\frac{\zeta(s)^2}{\zeta(2s)} .$$
*Proof.* Both sides are multiplicative, so compare Euler factors. On the left, the factor at $p$ is $1+2\sum_{k\ge1}p^{-ks}=\dfrac{1+p^{-s}}{1-p^{-s}}$. On the right, it is $\dfrac{1-p^{-2s}}{(1-p^{-s})^2}=\dfrac{1+p^{-s}}{1-p^{-s}}$. ∎ (This is a standard identity; see Hardy & Wright, *An Introduction to the Theory of Numbers*, ch. XVII.)

**Fact 11.4 (Dirichlet, 1849).** $\sum_{N\le x}\tau(N)=x\ln x+(2\gamma-1)x+O(\sqrt x)$, where $\gamma$ is Euler's constant. *In model terms:* the total number of linear terminal structures with at most $x$ columns has this size.

---

## 12. The Riemann hypothesis, and whether the model reaches it

**Conjecture 12.1 (Riemann hypothesis; Riemann, 1859).** Every non-trivial zero $\rho$ of $\zeta$ satisfies $\operatorname{Re}(\rho)=\tfrac12$.

Two established equivalent forms:
- (von Koch, 1901) $\pi(x)=\operatorname{Li}(x)+O(\sqrt x\,\log x)$, where $\pi(x)$ is the number of primes up to $x$ and $\operatorname{Li}(x)=\int_2^x dt/\ln t$.
- For every $\varepsilon>0$: $\pi(x)-\operatorname{Li}(x)=O(x^{1/2+\varepsilon})$.

In words, RH bounds **the error made when $\operatorname{Li}(x)$ approximates the number of primes up to $x$**.

**Status:** unproven. Hardy (1914) proved that infinitely many zeros lie on the line. Extensive numerical verifications have found no counterexample.

### 12.2 Restatements in the model's vocabulary (no new content)

Using Identity 11.2, "$N$ is prime" is equivalent to "$N\ge2$ has exactly two linear endings". So:

**Restatement 12.2.** Let $\Pi(x)$ be the number of column counts $2\le N\le x$ that admit exactly two affine polygon endings. Then RH $\iff \Pi(x)=\operatorname{Li}(x)+O(\sqrt x\log x)$.

**Restatement 12.3.** The non-trivial zeros of the series counting linear endings, $\zeta(s)^2$, are exactly those of $\zeta(s)$, each with doubled multiplicity. So RH $\iff$ the non-trivial zeros of the series counting linear endings lie on $\operatorname{Re}(s)=\tfrac12$.

**Why these are not a connection.** Both statements are true only because "number of linear endings" *was shown to equal* the divisor function $\tau$. Any vocabulary that reproduces divisor counting would give the same restatements. They give **no new method, evidence or constraint**. The difficulty of RH is untouched: it is a statement about the asymptotic distribution of the primes, and the musical model only renames divisibility. Any musical object counted by $\tau$, by $2^{\omega}$ or by other arithmetic functions would inherit the same zeros in the same way.

### 12.4 What a catalogue of pieces could and could not show

The README's Section 11.3 proposes cataloguing $N_1$ values across real pieces.
- **Could show:** whether observed $N_1$ values, native-width ratios or shapes are distributed differently from a stated random control. That is an empirical question about music.
- **Could not show:** anything about RH. Whether a particular integer is prime is fixed by arithmetic, so observing it as a column count adds no number-theoretic information. RH is a statement about limits as $x\to\infty$, and no finite catalogue of integers bears on it.

### 12.5 Answer to item 12 of the assignment

**No established mathematical connection exists between the proposed row structure and the non-trivial zeros of $\zeta$.** The established relationships are:

| Level | Relationship | Status |
|---|---|---|
| Divisibility | Regroupings ↔ $D(N_1)$; linear endings ↔ $D(N_1)$; prime $N_1$ ↔ exactly two linear endings | **Proved** (Props. 4.1, 5.1–5.3) |
| gcd and lcm | M1 = min of exponents, M2 = max; coprime split of the cycle | **Proved** (Fact 1.3, Prop. 8.2–8.3) |
| $\zeta(2)$ | Density $6/\pi^2$ of merged width = unit, under a chosen model | **Fact**, conditional on a probability model |
| $\zeta(s)$ identities | $\zeta^2$, $(\zeta-1)^2$, $\zeta^2/\zeta(2s)$ | **Identities** (Re $s>1$) |
| Zeros / RH | Rewritable in model words | **Restatement only**; no connection |

*I guess the Author's intuition in Statement 32 lands best at the divisibility level (Proposition 5.2). There it is exact: the "1 and itself" of a prime column count are precisely the two ways the ending can be linear. That is a real, if modest, mathematical fact about the proposed model. It is not a step toward the Riemann hypothesis, and this document does not claim it is.*

---

## 13. Open questions for Part II review

1. Is the polygon model ($H_2$) or the staircase model (02a, K6a) the better reading of Statements 5 and 7? The prime–linearity link exists only in the polygon model. *To be decided from the README by comparison, not by asking the Author.*
2. Is there any natural musical structure counted by an arithmetic function whose Dirichlet series is **not** built from $\zeta$ in an elementary way, so that the restatement problem of §12.2 would not apply? None is known to me.
3. Should Part III (storytelling) reuse the divisor structure, with the journey split into $J$ equal steps? *I guess possibly. To be investigated there, not assumed here.*

*End of Part II.*
