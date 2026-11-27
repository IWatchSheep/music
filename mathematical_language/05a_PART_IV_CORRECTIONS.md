# Part IV — Correction Note and Cross-Reference Audit

**From:** Claude (Opus 5.5) · **Date:** 2026-11-27
**Applies to:** `05_PART_IV_COMMON_MATHEMATICAL_LANGUAGE.md`, which is kept unchanged, and to the earlier items named below. Where they differ, this note governs.

## A. Corrections from ChatGPT's review

| # | Location | Correction |
|---|---|---|
| P1 | 05 §14, row 2 | The sum runs over **$N\ge2$**: $\sum_{N\ge2}(\tau(N)-2)N^{-s}=(\zeta(s)-1)^2$ for $\operatorname{Re}s>1$. The $N=1$ coefficient on the right is $0$, while $\tau(1)-2=-1$. Part II, Identity 11.2, already stated this correctly. |
| P2 | 05 Prop. 3.3, §12 | **Order convention:** cut sets are ordered by inclusion $\subseteq$, so more cuts means finer. Under this order, $d\mapsto K_d$ (by **block length**) is an **order anti-isomorphism** from $(D(N),\mid)$ onto the equal partitions: $K_d\subseteq K_{d'}\iff d'\mid d$. Indexing by the **number of blocks** $b=N/d$ gives an **order isomorphism**: $K_{N/b}\subseteq K_{N/b'}\iff b\mid b'$. In block-length terms, the join of two equal partitions is the gcd of their block lengths; in block-count terms, it is the lcm of their counts. Example: blocks 4 and 3 on $[12]$ are counts 3 and 4, and $\operatorname{lcm}(3,4)=12$ blocks gives width 1. **The conclusions of 05 Prop. 6.1 (gcd = M1, lcm = M2) are unchanged.** The phrase "order isomorphism" in the §12 table is replaced by "order anti-isomorphism (block length) / isomorphism (block count)". |
| P3 | 05 Prop. 9.1 | **Replaced by 04a M4 (Prop. 6.1′).** Arrival is a precondition for valence and for a terminal gesture to be defined. *Among completed episodes*, valence and terminal shape do not force each other. No wider independence claim is made. |
| P4 | 04a M3; 05 §17 | The **free category** of a directed graph consists of **all** finite directed paths, including the identity (length-0) paths, under compatible concatenation. **First-arrival main journeys** are a restricted collection that is **not closed** under concatenation. Example: if $\gamma$ first arrives at $B$, then $\gamma$ followed by any further step ends after $B$ was already reached, so it is no longer a first-arrival journey. |
| P5 | 05 §11 | **Attribute sets.** Armstrong's rules apply to implications $X\Rightarrow Y$ between **sets** $X,Y\subseteq\Phi$. Such an implication is valid in $C$ if every item having all of $X$ has all of $Y$. **Negative properties:** a negated property $\neg\varphi$ is represented as a separate attribute $\bar\varphi$, under the constraint that every item has exactly one of $\varphi$ and $\bar\varphi$. Armstrong's rules remain sound on the extended attribute set, but they do not derive consequences of that complementarity constraint. Example: $\{\varphi,\bar\varphi\}\Rightarrow Y$ is vacuously valid. **Validity in $C$ means consistency with that catalogue only, not universal validity.** |
| P6 | 05 §7 | **Wording:** in $(a,b)=(du,dv)$, **each factor** is scaled by $d$, and their **product** $N$ is scaled by $d^2$. The sentence "a coprime row-pair pattern scaled by a common square factor" is replaced by: "a coprime pair $(u,v)$ with each factor multiplied by $d$, so that $N=d^2uv$". The bijection is unchanged. |
| P7 | 05 Def. 8.1 | The three-block episode skeleton **assumes** (i) the sequential A-then-B ("meets") model and (ii) a **common unit**, Row 1 columns of width $w_1$, for all three blocks. Overlapping rows need not admit this consecutive three-block form. |
| P8 | 05 Thm. 5.2; 03 Prop. 5.3 title | $J$ is the number of **transitions**. $J$ transitions have $J+1$ levels, $0,\dots,J$. Read "the polygon has $J$ levels" (05) and "intermediate levels" (03, title) as "$J$ transitions". |
| P9 | 05 §17–18 | **Formalization vs validation.** "Formalized" means a mathematical interpretation has been supplied and its consequences proved. It does **not** mean the Author's musical or narrative hypothesis has been validated. No empirical claim has been tested in this study. The two lists are reconciled in `06_FINAL_MATHEMATICAL_SUMMARY.md` §12: §18 classifies *formalization*, while §17's "Author hypotheses" lists *untested empirical claims*. A statement can appear in both. Statements 5, 12 and 20, for example, are formalized but contain untested musical claims. **The 23 formalized statements are not 23 proven hypotheses.** |

## B. Cross-reference audit (all files)

| # | Location | Problem | Corrected reading |
|---|---|---|---|
| X1 | 05 §3, after Prop. 3.3 | "(02 M4, …)" can be confused with 04a M4 | "02 §7, merger candidate M4" |
| X2 | 05 §17 | "2.2′" names no labelled statement | "04a M2, corrected triangle-inequality statement" |
| X3 | 04 §0 item 2 and §12 table | They still cite the withdrawn full-independence Prop. 6.1 | Read as 04a M4, Prop. 6.1′ |
| X4 | 02 §10, $H_2$ | "Dwells … before stepping" | Read as transition columns (02a K6). The literal dwell is the staircase (02a K6a; 03a L1). |

All other references checked resolve to existing labelled items: 02 Props 1–18, Cor 2.1–2.2, 8.1, CE 3.1–3.2, 4.2a–b, 13.2, 15.2, Ex 6.1–6.3; 02a K1–K10; 03 Props 4.1–8.3, Identities 11.2–11.3, Fact 3.1, Prop 5.4; 03a L1–L9, B1–B3; 04 Defs and Props 1.1–11.2; 04a M1–M11; 05 §1–18.

**Privacy audit.** No personal paths, names, email addresses or account identifiers appear in any study file. Sources are cited only as `music/README.md` and `music/music.txt`.

*End of note.*
