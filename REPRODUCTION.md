# Reproduction

## Environment

Required:

- Linux or another POSIX system that supports Python `resource` limits;
- Python 3.10 or newer;
- no third-party Python packages;
- enough writable space for about 10 MiB of outputs.

The full driver is single-worker and starts at most one child process at a time. It refuses to start without POSIX resource limits. Individual model, classifier, evidence-generation helpers and unit tests remain importable on other standard-library Python platforms; that does not make the full POSIX driver portable.

## Tests

```sh
python -m unittest discover -s tests -v
```

Expected: 81 tests, zero failures and zero errors.

## Named staged evidence

```sh
python staged_check.py analyze staged_cases/S01.json
python staged_check.py certify staged_cases/S01.json --out /tmp/S01-certificate.json
python staged_check.py verify-certificate staged_cases/S01.json /tmp/S01-certificate.json

python staged_check.py witness staged_cases/S02.json --out /tmp/S02-witness.json
python staged_check.py verify-witness staged_cases/S02.json /tmp/S02-witness.json
```

`S01` is the positive bidirectional diamond. `S02` is a rewrite-peak failure. Other retained cases are documented in `staged_cases/` and `results/staged/case-summary.json`.

## Complete deterministic reproduction

```sh
# Choose a new directory; do not delete an existing result tree.
sh reproduce.sh /tmp/prophecy-results
python compare_results.py results /tmp/prophecy-results
```

An external execution wrapper may terminate a long command even though every child is below its individual limit. The driver is intentionally resumable. Rerun the exact same `sh reproduce.sh /tmp/prophecy-results` command until it exits successfully. A step is skipped only when every declared JSON/CSV sentinel parses and an atomically written completion record names that exact sentinel set; a nonempty partial file alone is never sufficient. `python reproduce.py /tmp/prophecy-results --force` discards prior completion records and reruns every component.

Expected deterministic comparison:

```json
{
  "deterministic_files_compared": 94,
  "equal": true,
  "resources_compared": false
}
```

The 94-file set includes exact inputs, legacy chunks and totals, primary staged family rows, seven isolated parts plus the aggregate of the separate classifier, named analyses, certificates, witnesses, mutation rows, semantic pairs and the full test-name summary. CPU, wall-time and peak-RSS fields are excluded.

## Principal retained totals

```text
staged systems                 451736
reachable states              2294095
reachable local peaks         1077936
exactly confluent              207069
Newman mismatches              0
modular true                  134977
modular false positives        0
modular false negatives       72092
unique terminal program       235741
program-only                   28672
mutations rejected             72 / 72
separate field comparisons   4065624 / 4065624
unit tests                     81 / 81
legacy one-slot instances     2560900
legacy formula mismatches      0
Boolean expression pairs       3136
```

## Comparing two fresh runs

```sh
sh reproduce.sh /tmp/prophecy-run-a
sh reproduce.sh /tmp/prophecy-run-b
python compare_results.py /tmp/prophecy-run-a /tmp/prophecy-run-b
```

The retained `results/reproduction/comparison.json` records the historical equality of two independently populated directories before the seven additional regressions. It is not a fresh run of the current suite. The current test-name summary is updated separately; a new complete POSIX driver run is needed to re-establish full 94-file equality for the current tree.

## Automated finite checks

`.github/workflows/scientific-checks.yml` is for the flat standalone artifact repository. On pushes to `main` or manual dispatch it runs the full finite driver and deterministic comparison on Ubuntu 24.04. The scientific command group has a 600-second wall bound, a 3 GiB address-space bound and an outer CPU limit; each driver child additionally has its existing CPU/address-space caps and a 240-second wall timeout. Failures propagate and raw outputs are uploaded even on failure. Preparing this workflow is not evidence that it has run remotely.

## Interpreting failures

- Parser failure: the input is outside the declared finite monotone/ranked fragment.
- Unit-test failure: a local definition or boundary check regressed.
- Primary/separate-classifier mismatch: two implementations disagree on a named finite property; do not use aggregate claims until reconciled.
- Campaign aggregate mismatch: a family generator or classification changed.
- Fresh certificate rejected by replay: producer and independent consumer disagree on coverage or a represented proof obligation.
- Deterministic comparison failure: regenerated scientific evidence differs from the packet; do not use manuscript counts until reconciled.
- Resource-record difference only: expected across hosts and not a scientific mismatch.

A successful run establishes reproduction of this implementation and its retained finite evidence. It does not constitute independent peer review, a proof-assistant theorem or validation of a production compiler.
