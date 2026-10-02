# Literature inspection and calibration record

Access date: 2026-09-19. This file records the technical role and inspected boundary of the literature used to frame the paper. Citation metadata is listed in `reference-audit.csv`; `identifier-audit.csv` records one verification source and field-level agreement for all 49 cited entries. No paper PDF is redistributed.

## Closest prophecy/history work

### BuildIt

Ajay Brahmakshatriya, Saman Amarasinghe and Martin Rinard, *Backwards Data-Flow Analysis Using Prophecy Variables in the BuildIt System*, arXiv:2601.02653v2 (2026).

Inspected material included the operational prophecy extension, prediction/check discipline, preservation/progress statements, repeated forward execution and the least-satisfying-facts discussion. The paper already combines prophecy variables and repeated forward execution in a staged code-generation system. Those mechanisms are prior work and are not included in this project's novelty claim.

### Nexis

Martin Rinard, *Program Analysis with Prophecy and History Variables in the Nexis Compiler*, arXiv:2607.23033v1 (2026).

Inspected material included the prophecy/history DSL, generated solver architecture, relationship between reference and worklist solvers, validity/extremality claims, dependence-ordered solving and the stated machine-checked optimization results. The present project does not claim the first verified prophecy/history implementation, the first correctness proof for the cited optimizations, or a replacement for those language-level proofs.

### Operational prophecy/history analysis

Martin Rinard and Austin Gadient, *Dataflow Analysis With Prophecy and History Variables*, arXiv:2007.12015 (2020), was inspected for its use of lattice-valued prophecy/history variables, augmented operational semantics and preservation/progress style reasoning. Abadi and Lamport and Zhang et al. were inspected as state-machine/concurrency prophecy foundations rather than compiler-confluence results.

## TOPLAS calibration set (13 articles)

The following complete articles or complete accessible technical versions were used to calibrate argument structure, theorem-to-algorithm connection, evaluation breadth and limitation placement. The project uses their explanatory patterns, not their wording or section outlines.

1. **Nielson 1985 — Program Transformations in a Denotational Setting.** Transformation correctness depends on the direction and strength of analysis information; motivates separating code transformation from data-flow solution.
2. **Ryder and Paull 1988 — Incremental Data-Flow Analysis.** Long-form algorithmic paper connecting formal affected regions, update algorithms and empirical/structural reasoning.
3. **Burke 1990 — Interval-Based Exhaustive and Incremental Interprocedural Analysis.** Separates exhaustive and incremental guarantees and states exactness conditions.
4. **Wegman and Zadeck 1991 — Constant Propagation with Conditional Branches.** Shows how a lattice analysis becomes a concrete transformation while retaining conservative claims.
5. **Hudak and Young 1991 — Collecting Interpretations of Expressions.** Uses semantic interpretation to connect execution observations and static information.
6. **Cytron et al. 1991 — SSA and Control Dependence.** Exemplifies a formal graph property paired with a practical construction and detailed complexity/evidence.
7. **Knoop, Rüthing and Steffen 1994 — Optimal Code Motion.** Distinguishes optimality, safety and computational construction.
8. **Click and Cooper 1995 — Combining Analyses, Combining Optimizations.** Directly motivates careful treatment of interacting analysis/optimization schedules.
9. **Masticola, Marlowe and Ryder 1995 — Multisource and Bidirectional Data Flow.** Establishes prior lattice treatment of information arriving in multiple directions; this project does not claim to invent bidirectional abstract interpretation.
10. **Acar, Blelloch and Harper 2006 — Adaptive Functional Programming.** Calibrates change propagation, stability assumptions and theorem/system separation.
11. **Karkare and Khedker 2007 — Call-String Bound.** Demonstrates a precise bounded theorem whose assumptions and impact remain explicit.
12. **Kalvala, Warburton and Lacey 2009 — Transformations with Temporal-Logic Side Conditions.** Calibrates rule-side-condition formalization and correctness boundaries.
13. **Liu, Stoller and Lin 2017 — From Clarity to Efficiency.** Shows a transformation narrative from high-level program to efficient result with correctness and empirical roles kept distinct.

Pattern extracted: state assumptions before the principal theorem; give one running example; connect the theorem to an executable construction; distinguish exact from sufficient criteria; report negative and boundary cases; keep implementation evidence from replacing semantic proof.

## Influential foundations (at least five)

- Kildall 1973 and Cousot & Cousot 1977/1979: monotone fixed-point and abstract-interpretation foundations.
- Kam & Ullman 1977: monotone data-flow frameworks.
- Newman 1942, Rosen 1973 and Huet 1980: termination, local confluence, Church–Rosser and critical-pair reasoning.
- Baader & Nipkow 1998 and Terese 2003: standard rewriting terminology and proof organization.

These sources support classical premises and proof patterns. No classical theorem is renamed as a new contribution.

## Adjacent PL and compiler work (more than five)

- Davies & Pfenning 1996; Taha & Sheard 2000; Carette, Kiselyov & Shan 2009; Rompf & Odersky 2010; Jones, Gomard & Sestoft 1993: staging and partial evaluation boundaries.
- Lerner, Grove & Chambers 2002: composed analyses that transform graphs, provisional transformations and explicit termination discussion.
- Knoop, Rüthing & Steffen 1992; Tristan & Leroy 2009: code motion and verified validation.
- Reps, Horwitz & Sagiv 1995; Sagiv, Reps & Horwitz 1996: precise interprocedural fixed-point/reachability formulations.
- Tate et al. 2009 and Willsey et al. 2021: equality saturation as a contrasting strategy that delays extraction rather than committing irreversible rank-decreasing rewrites.
- Necula 2000; Pnueli, Siegel & Singerman 1998; Leroy 2009 (CACM and JAR): translation validation and verified compiler boundaries.

Pattern extracted: expose the trusted computing base; distinguish generation from validation; state semantic observations; do not infer correctness from convergence; pair a positive pipeline with explicit counterexamples.

## Metadata and access discipline

Every bibliography entry has a citation-audit row and an identifier-audit row with authors, year, venue or book record, persistent identifier, verification source, field-level agreement and notes. Metadata discrepancies found during audit were resolved or documented. In particular, Tristan and Leroy's PLDI paper is pp. 316–326, the TAMC prophecy paper is pp. 61–71, the 2009 TOPLAS entries use article numbers plus full page extents, the archival record for *Data Flow Analysis* lists Uday Khedker/Amitabha Sanyal/Bageshri Karkare while a current publisher page uses Sathe, and the Cooper--Torczon print year is distinguished from the platform's online date. Publisher, DOI, arXiv, DBLP, library and author records were preferred; secondary mirrors served only as corroboration.

## Remaining epistemic boundary

Literature comparison supports the stated non-overlap, but no internal self-audit can prove field-wide novelty. A human PL expert should repeat the closest-work search before external submission, especially for work published after 2026-09-19. This is an external-use check, not an unfinished artifact component.
