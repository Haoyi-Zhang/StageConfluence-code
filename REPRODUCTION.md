# Reproduction

## Environment

Required:

- Python 3.10 or newer;
- Linux/POSIX with Python `resource` support for the default complete driver,
  or Windows with the explicit `--portable` option;
- no third-party Python packages;
- enough writable space for about 10 MiB of outputs.

The driver starts at most one child at a time. Default execution refuses to
start without POSIX limits; the explicit Windows portable option runs the same
scientific plan while recording that those caps are unavailable.

## Tests

```sh
python -m unittest discover -s tests -v
```

Expected: 96 tests, zero failures and zero errors. The six-method standalone
suite is `python -B tests/state_admission_regression.py`. Run both under `-O`
as well; these are mode checks, not additional scientific systems.

## Named staged evidence

```sh
python staged_check.py analyze staged_cases/S01.json
python -B staged_check.py certify staged_cases/S01.json --out ../stageconfluence-smoke/S01-certificate.json
python -B staged_check.py verify-certificate staged_cases/S01.json ../stageconfluence-smoke/S01-certificate.json

python -B staged_check.py witness staged_cases/S02.json --out ../stageconfluence-smoke/S02-witness.json
python -B staged_check.py verify-witness staged_cases/S02.json ../stageconfluence-smoke/S02-witness.json
```

Choose a fresh writable output directory outside the checkout; replace
`../stageconfluence-smoke` consistently if needed. Named-case checks do not
require POSIX resource support. The `/tmp/` paths below are POSIX examples.

`S01` is the positive bidirectional diamond. `S02` is a rewrite-peak failure. Other retained cases are documented in `staged_cases/` and `results/staged/case-summary.json`.

## Complete deterministic reproduction

```sh
# Choose a new directory; do not delete an existing result tree.
sh reproduce.sh /tmp/prophecy-results
python compare_results.py evidence/current/normal /tmp/prophecy-results
```

Rerun the same command after interruption. A step is skipped only when its
current source/input, command/interpreter/scope and output-byte bindings agree,
and every declared sentinel parses. `--force` ignores completion records.

Expected deterministic comparison:

```json
{
  "deterministic_files_compared": 132,
  "equal": true,
  "resources_compared": false
}
```

The historical 94-file set includes exact inputs, legacy chunks and totals, primary staged family rows, seven isolated parts plus the aggregate of the separate classifier, named analyses, certificates, witnesses, mutation rows, semantic pairs and the then-current test-name summary. CPU, wall-time and peak-RSS fields are excluded.

The current set has 132 deterministic files, adding ordered admission and
saturated/full proof comparisons to the original selection. Timing ratios,
host metadata and interpreter mode are excluded from equality but retained as
raw measurements; decisions and serialized proof sizes are compared. Original
94-file historical results are not silently relabeled current.

On Windows use `python -B reproduce.py OUTPUT --portable`. All 24 stages run,
but POSIX CPU/address-space limits and cumulative child accounting are absent;
the driver records nulls and retains the 240-second child wall timeout. It does
not emulate Linux or execute a native compiler integration.

Recovery binds source/input bytes, exact argv, Python version/mode, execution
scope and every stage-produced file, not just parseable sentinels. Current
raw runs are under `evidence/current/normal` and `evidence/current/optimized`.
The original test-name summary and historical result files remain untouched.

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
unit tests (current)           96 / 96
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

The original `results/reproduction/comparison.json` and 81-test summary remain
historical. Current local normal/optimized runs compare equal on 132 files;
93 original non-test scientific files also compare equal. A current Linux run
is still required for the unchanged POSIX limit mechanism on this version.

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
