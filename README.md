# Confluence Certificates for Bidirectional Staged Optimization — artifact

This directory is a standalone reproducibility repository for the finite model and evidence in the accompanying paper. It does not depend on `paper/` or on a parent directory.

## What is implemented

The repository contains two related models.

1. **Code-changing staged systems** are the main result. A state is a residual program plus a lattice fact. Program-indexed analysis updates are monotone and inflationary. Guarded fact transfers are monotone and inflationary, and every rewrite strictly decreases a declared program rank. The code explores the rooted graph, checks exact and modular confluence properties, emits positive certificates or terminal-fork witnesses, and replays those objects using a separate verifier.
2. **One-slot irreversible emission** is a negative control inherited from the pilot. It demonstrates that convergence of analysis facts alone does not guarantee unique residual syntax.

The analysis labels `forward`, `prophecy`, `history`, and `auxiliary` are documentary. The implementation checks their tables, not a language-level operational interpretation of those labels.

## Principal results

Retained deterministic outputs under `results/` report:

- 451,736 staged systems, 2,294,095 reachable states and 1,077,936 local peaks;
- 207,069 exactly confluent systems, with zero disagreement between unique-normal-form and local-peak checks;
- 134,977 systems satisfying guard persistence, closure commutation and saturated local confluence;
- zero modular false positives and 72,092 modular false negatives;
- 235,741 systems with a unique terminal program, including 28,672 program-only cases;
- five replayed positive certificates, four replayed negative witnesses and 72/72 rejected single-field mutations;
- zero disagreement in 4,065,624 field comparisons by a separately implemented classifier;
- 74 passing unit tests;
- 2,560,900 one-slot control instances with zero exact-formula mismatch; and
- 3,136 ordered Boolean-expression pairs, including 476 different-syntax/equal-semantics pairs.

These counts are exhaustive only for the explicitly declared finite catalogs. They are not evidence about all finite lattices or production compiler workloads.

## Fast checks

From this directory:

```sh
python -m unittest discover -s tests -v
python staged_check.py analyze staged_cases/S01.json
python staged_check.py certify staged_cases/S01.json --out /tmp/S01-certificate.json
python staged_check.py verify-certificate staged_cases/S01.json /tmp/S01-certificate.json
python staged_check.py witness staged_cases/S02.json --out /tmp/S02-witness.json
python staged_check.py verify-witness staged_cases/S02.json /tmp/S02-witness.json
```

## Complete reproduction

Use a new output directory:

```sh
sh reproduce.sh /tmp/prophecy-results
python compare_results.py results /tmp/prophecy-results
```

The driver launches a fixed sequence of bounded children, never more than one at once. Each child receives a 3 GiB address-space limit and a 180-second CPU limit. The output directory is resumable: rerun the same command after interruption. A step is skipped only when every declared JSON/CSV sentinel parses and an atomically written completion record names that exact set. A partial nonempty file is not a completion signal; use `python reproduce.py OUTPUT --force` to rerun every component.

Expected comparison:

```json
{
  "deterministic_files_compared": 94,
  "equal": true,
  "resources_compared": false
}
```

Resource records are excluded from equality because host timing and peak RSS are observations, not deterministic evidence.

## Repository map

- `src/staged_model.py`: validated finite staged-system representation and parser.
- `src/staged_checker.py`: rooted exploration, closures and exact/modular classifications.
- `src/staged_certificate.py`: certificate and witness generation.
- `src/staged_verify.py`: search-free replay of explicit positive and negative evidence.
- `staged_check.py`: command-line interface for one staged instance.
- `staged_campaign.py`: seven-family exact enumeration by the primary classifier.
- `independent_audit.py`, `aggregate_independent_audit.py`: separately implemented nine-field cross-check over all seven families.
- `staged_evidence.py`: named evidence and mutation campaign.
- `staged_cases/`: nine retained staged inputs plus rejected invalid inputs.
- `src/model.py`, `src/checker.py`, `check.py`, `exhaustive.py`, `collect.py`: one-slot negative control.
- `tests/`: 74 unit, boundary, replay, recovery and mutation tests.
- `proofs/`: detailed handwritten mathematical arguments.
- `results/`: retained deterministic outputs and separately labeled resource records.
- `claim_evidence_ledger.csv`: material claims linked to proofs, code and raw evidence.
- `external_resources.csv`: scholarly/template resources and integration boundaries.
- `literature/`: source-inspection notes and bibliographic audit.

## Trusted computing base

The positive verifier parses the same instance format but does not call the generator’s reachability, fixed-point, join-path or normal-form search. It reconstructs every listed state and outgoing edge, checks rooted parent evidence and closure of the graph, verifies the rank/coheight measure on all edges, replays supplied closure and join paths, checks peak coverage and evaluates every declared Boolean truth table. A second classifier independently implements transition enumeration, reachability, terminal propagation, peak joining, closure, GP, CC, SLC and program projection; it shares only the finite dataclasses and declared family generator with the primary campaign. These separations limit but do not eliminate common-mode bugs.

The mutation campaign is finite and selected. Rejecting all mutants is evidence that represented obligations are exercised, not a proof that the verifier is complete or bug-free.

## Scope and non-claims

The artifact does not implement BuildIt or Nexis, does not claim correspondence to an unrestricted source language, and does not report optimization speedups. General theorems are handwritten rather than proof-assistant checked. No external solver, model API, private data, live service or GPU is used.

Original code and generated examples are covered by `LICENSE`. Scholarly papers and the ACM template remain under their own terms and are cited or accompanied by their supplied notice; no paper PDFs or font files are redistributed.
