# Methods

## Research design

The study began with the proposed claim that alternating forward and prophecy-variable analyses should converge to a schedule-independent optimized program. A two-state one-slot counterexample showed that fact convergence alone cannot establish syntactic uniqueness. The question was then reformulated around code-changing systems, where analysis and rewrite steps are both scheduler choices.

The retained fragment has a finite lattice and residual catalog, globally
monotone inflationary analyses and transfers, arbitrary finite guards, and
strict natural rewrite ranks. Exact confluence and sufficient modular premises
are separated. The historical design-choice record is not experimental or
independent novelty evidence.

## Proof method

Termination uses a lexicographic quantity encoded as a natural: program rank multiplied by one more than the maximum lattice coheight, plus current coheight. Analysis steps strictly increase facts and lower coheight; rewrites lower rank by at least one. Per-program closure follows from finiteness, monotonicity and inflationarity. Newman's lemma supplies the exact local-to-global confluence step after termination is established.

The modular proof normalizes analysis around rewrites. Guard persistence keeps a rewrite enabled while source analysis advances. Closure commutation equates normalization after rewriting now with normalization after closing the source first. Saturated local confluence joins rewrite/rewrite peaks after every program state is analysis-closed. The paper proves a simulation from arbitrary full paths to the saturated rewrite system and then lifts saturated confluence back to the full relation.

Program uniqueness and source preservation are proved separately. This prevents a confluent but wrong transformation from being counted as correct and prevents equal final syntax with unequal facts from being counted as state confluence.

## Executable method

All semantic objects are finite tables. Parsers validate lattice laws, map dimensions, global monotonicity, inflationarity and rewrite-rank decrease before classification. The generator explores the exact rooted graph, computes normal-form sets, checks reachable local peaks, computes deterministic per-program closures, and checks GP, CC and SLC.

The positive certificate contains explicit states, edges, root-parent information, remaining heights, measure values, complete outgoing-edge records, closure traces, local-peak records, join paths and residual truth tables. The replay verifier does not search for reachable states, fixed points, joins or normal forms; it checks the supplied finite object and its exact edge coverage. Negative witnesses supply two replayable terminal traces and their distinguishing state or program component. Separately, `independent_audit.py` reimplements transition enumeration, rooted reachability, terminal propagation, local-peak joining, closure, GP, CC, SLC and program projection without importing the primary checker; it shares the finite dataclasses and declared family generator.

## Enumeration

Seven staged families enumerate all table combinations declared by their generators. They cover one-rewrite chains over two- and three-element fact domains, rank-one forks, a rank-two diamond and a two-analysis family. The selection is fixed in `staged_campaign.py`; no random seed, sampling or post-result tuning is used.

The one-slot control enumerates ordered pairs of monotone inflationary maps on eight named lattices, all Boolean guard tables and all selected emitters. A separate residual-language experiment enumerates 56 at-most-one-operator expressions over two variables and constants.

Counts are exact for these catalogs. Catalog size is not presented as practical workload breadth or proof of the general theorem.

## Negative controls and attacks

Named cases independently remove a rewrite-diamond leg, break closure commutation and make a guard disappear. Additional cases show confluence without semantic preservation, confluence outside the modular fragment, program uniqueness without state confluence and an unreachable bad rule. Invalid inputs exercise nonmonotone analysis, noninflationary transfer and nondecreasing rank rejection.

A mutation campaign changes 72 claim-critical fields while preserving parseability. All are rejected by replay. This campaign attacks coverage, edge identity, rank/coheight values, parent evidence, closure traces, peak records, join paths, semantic tables, terminal traces and claim summaries.

## Resource and recovery method

The 24-stage driver launches one child at a time and propagates optimization
mode. Default POSIX execution retains CPU/address-space limits; explicit
portable Windows execution has a child wall timeout without those caps.
Completion records bind source/input bytes, Python version/mode, argv,
execution scope and all produced files. Structural parsing alone is not
completion. Resource observations and scientific equality remain distinct.

A preliminary design ran the legacy and staged campaigns in one long-lived interpreter. It was abandoned after allocator and garbage-collection state caused substantial cross-campaign slowdown. Process isolation fixed the engineering problem without changing inputs or results. Failed or partial outputs are not included in claims.

## Literature method

The dated literature record preserves the earlier calibration scope. Current
metadata tables cover the 52 existing references; local agreement does not
certify 52 freshly read full texts. Current primary passages and inaccessible
material are listed in `literature/inspection.md`. Saturated certificates
instantiate normalization and confluence, not a new general principle or a
verified kernel. Same-table direct classification and full-graph proof routes
prevent compression from being presented as an invented speedup.
