# Part III — Correction Note (after ChatGPT's review)

**From:** Claude (Opus 5.5) · **Date:** 2026-11-27
**Applies to:** `04_PART_III_MATHEMATICS_OF_STORYTELLING.md`, which is kept unchanged. Where they differ, this note governs.

## M1. Main journey, terminal journey, episode (replaces Definitions 1.3 and 3.1 where they conflict)

The old Definition 1.3 stops a journey at its first arrival at $B$, but Definition 3.1 placed a terminal phase *after* arrival inside the same journey. They are now separated.

- **Two predicates.** The **final-state predicate** is $G(x_m)=1$. The **first-arrival predicate** is $G(x_m)=1$ and $G(x_i)=0$ for all $i<m$. The second implies the first, and the converse is false (the journey may pass through $B$ earlier).
- **Main journey** $\gamma=(x_0,\dots,x_m)$, satisfying first arrival at the goal set $B$. Its steps carry the phases A then B, each non-empty (Statements 23, 28). It occupies the time interval $[t_0,t^\ast]$.
- **Terminal journey** $\eta=(z_0,\dots,z_{n})$, a journey in a second state space, the low-to-high levels of Part I $H_2$. Its first state is the lowest level, its last state is the highest, and it occupies $[t^\ast,\,t^\ast+N_1w_1]$.
- **Episode** $E=(\gamma,\eta)$. Its **boundary condition** is that $\eta$ starts at the time $t^\ast$ when $\gamma$ arrives.

The finish-line alignment $t^\ast=b_3\in\Lambda_1$ remains a **conditional model property** (02 Prop. 11, as qualified by 02a K5).

## M2. Proposition 2.2 (the triangle inequality)

In an arbitrary metric space, equality $d(a,b)=d(a,M)+d(M,b)$ does **not** guarantee a continuous shortest path through $M$. Corrected statement:
- **Finite-chain version.** Define the length of a chain $a=y_0,\dots,y_k=b$ as $\sum d(y_{i-1},y_i)$. A chain through $M$ is **shortest** iff its length equals $d(a,b)$. Equality in the triangle inequality is exactly the condition that the two-link chain $a,M,b$ is shortest.
- **Geodesic version.** Only in a **geodesic metric space** does equality give a continuous shortest path through $M$.
- **Directed graphs.** If routes must follow the edges of the story graph, then $d$ must be the graph's path metric, or else the compatibility of the two must be assumed. This is not automatic.

The proposition concerns a **target state** $b$. For a goal **set** $B$, use $d(x,B)=\inf_{b\in B}d(x,b)$. The equality statement then needs a state $b\in B$ that attains the infimum.

## M3. Definition 3.3 (concatenation)

Concatenation is defined only when the end state of one journey equals the start state of the next. So journeys form a **category**, not a monoid. Its objects are states, its morphisms are journeys, composition is concatenation, and the identity at $x$ is the length-0 journey $(x)$. This is the standard **free category of paths** of a directed graph. A **monoid** exists only by restricting to journeys that start and end at one fixed state $x$, the endomorphism monoid of $x$.

## M4. Proposition 6.1 (independence), restated

Valence is defined only for completed journeys, and the terminal gesture belongs to completed episodes (M1). The over-broad claim is withdrawn.

**Proposition 6.1′.** Among completed episodes, with valence not otherwise constrained, all four combinations of $\beta\in\{\text{success},\text{disappointment}\}$ and terminal shape $\in\{\text{affine},\text{non-affine}\}$ are admissible.
*Proof.* Take the main journey $\gamma=(0,1,2,3)$ with $B=\{3\}$, phases A = the first step and B = the remaining steps, and $\beta$ arbitrary. Take the terminal journey $\eta$ with $J=2$ and $c=(1,1)$, which is affine, or $c=(2,1)$, which is non-affine. ∎

No claim is made that incomplete journeys have terminal gestures.

## M5. The race counterexamples, made explicit

Take a track of length 1, so progress is $p(t)=\text{distance}/1$.
- **CE 8.2′ (disappointment, linear progress).** Runner R1 runs at constant speed 1 and finishes at $\tau_1=1$. Runner R2 runs at constant speed $\tfrac12$ and finishes at $\tau_2=2$, so R2 loses. R2's own-normalized progress is $\hat p(x)=x$, which is affine.
- **CE 8.3′ (success, curved progress).** Runner R3 has $p(t)=(t/0.9)^2$ and finishes at $\tau_3=0.9<\tau_1$, so R3 wins. R3's normalized progress is $\hat p(x)=x^2$, which is convex.

**Scope.** These are curves of **main-journey progress**. They refute a universal rule that ties the outcome to that progress curve. They do **not** by themselves refute a rule about the separately defined **terminal gesture** $\eta$. For $\eta$, Proposition 6.1′ shows only that no such rule is forced.

## M6. Proposition 8.4: uniform progression vs matching the training pace

Separate the two notions:
- **Uniform progression:** $c_1=\dots=c_J$. Under the polygon model, this is equivalent to an affine terminal polygon.
- **Training match:** $c_1=\dots=c_J=c^\ast$, for an independently prescribed training transition length $c^\ast$.

A training match implies uniform progression, but not conversely. **Counterexample:** $c^\ast=2$ with actual $(3,3,3)$, or $(1,1,1)$. Both are affine and neither matches training.

**Proposition 8.4′.** If $J$ and the total $N_1=Jc^\ast$ are fixed independently, then under the polygon model, affine $\iff$ training match.
*Proof.* Affine means $c_j=c$ for all $j$, so $Jc=N_1=Jc^\ast$ and $c=c^\ast$. ∎

Statement 26 is therefore recovered conditionally in **two** distinct ways, depending on whether success means uniform progression or training match. Both remain formalizations, not the established meaning.

## M7. Proposition 9.1 (equal episodes)

Require $N\ge1$. For a **fixed** $K$, an equal division into $K$ consecutive episodes exists iff $K\mid N$, and it is then unique. Summing over all admissible $K$ gives $\tau(N)$ divisions in total.

## M8. Proposition 9.3 (turn-taking)

$\operatorname{lcm}(m,n)$ gives the **simultaneous periodic start times** from a common origin. It does not establish that the characters alternate, that they do not overlap, or that the common cycle is the fundamental period of a conversation. Those remain hypothetical (*I guess*).

## M9. Proposition 10.1 (journey length vs $N_1$)

Within the **arithmetic model**, once the fitted structure is fixed, every positive terminal count is permitted. This shows that **no arithmetic relation is forced**. It does not assert that every such episode exists in an arbitrary fixed directed story graph.

## M10. Proposition 11.2 (catalogue)

A larger catalogue is **weakly** more permissive under the shared-property rule. That is not evidence that its notion of consistency is more accurate. Conditional relationships, $P\Rightarrow Q$, are investigated in Part IV §11.

## M11. Part II addendum: bijective proof of the square-factor identity (03a B3)

For each ordered factor pair $(a,b)$ with $ab=N$, put $d=\gcd(a,b)$, $a=du$ and $b=dv$. Then $\gcd(u,v)=1$ and $N=d^2uv$. Conversely, each square divisor $d^2\mid N$ together with an ordered coprime pair $uv=N/d^2$ gives the factor pair $(du,dv)$, and $\gcd(du,dv)=d$. The two maps are inverse to each other, so
$$\tau(N)=\sum_{d^2\mid N}2^{\omega(N/d^2)} .$$
The terminal count and the common-cycle length of an actual piece remain distinct quantities (03a, Scope).

*End of note.*
