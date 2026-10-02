# Methods

## Research design

The study began with the proposed claim that alternating forward and prophecy-variable analyses should converge to a schedule-independent optimized program. A two-state one-slot counterexample showed that fact convergence alone cannot establish syntactic uniqueness. The question was then reformulated around code-changing systems, where analysis and rewrite steps are both scheduler choices.

Ten substantively different formulations were compared before scientific lock. The retained fragment uses a finite lattice, a finite residual-program catalog, globally monotone inflationary analysis updates, arbitrary finite rewrite guards, globally monotone inflationary fact transfers and a strict natural-number rewrite rank. The exact and modular confluence statements were separated so that the modular condition could be falsified without invalidating the exact theorem.

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

All scientific executables are single-threaded. `reproduce.py` launches one child at a time under a 3 GiB address-space cap and 180-second CPU cap. It sets deterministic Python hash behavior and suppresses bytecode generation. After a child succeeds, the driver structurally parses its declared JSON/CSV sentinels and atomically writes a completion record bound to that exact set. Resumption skips a step only when both the record and every sentinel remain valid; partial nonempty output is not completion.

A preliminary design ran the legacy and staged campaigns in one long-lived interpreter. It was abandoned after allocator and garbage-collection state caused substantial cross-campaign slowdown. Process isolation fixed the engineering problem without changing inputs or results. Failed or partial outputs are not included in claims.

## Literature method

Closest work was read for definitions and guarantee boundaries before the theorem was locked. Metadata, venue, pages and persistent identifiers were cross-checked against publisher, DOI, arXiv, DBLP, library or author records where available. The calibration inventory includes 13 TOPLAS articles, influential rewriting/data-flow foundations and adjacent staging, compiler-validation and prophecy/history work. `literature/inspection.md` records technical roles, `literature/reference-audit.csv` records citation-level metadata, and `literature/identifier-audit.csv` records one verification source and field-level agreement for all 49 cited entries.

## Generative-AI involvement

Generative AI was used substantially in research-question refinement, literature triage, proof development, code and test construction, experiment execution and interpretation, manuscript drafting, artifact organization and self-audit. It was not merely a grammar tool. No external person was contacted and no private data, external compute service, external model API, GPU or autonomous submission workflow was used. Human authors must independently verify and accept responsibility before external use.
