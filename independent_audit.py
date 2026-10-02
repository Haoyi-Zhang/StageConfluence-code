#!/usr/bin/env python3
"""Cross-check the staged classifier with a separately implemented exact oracle.

The oracle deliberately imports neither ``src.staged_checker`` nor any of its
transition, closure, normal-form, peak, or saturation helpers.  It shares the
validated finite model and the declared family generator with the primary
campaign, then independently rebuilds every reachable graph and every modular
obligation.  Agreement is implementation evidence, not a mechanized proof.
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
import json
from pathlib import Path
import resource
import time
from typing import Iterable

from src.staged_model import StagedInstance
from staged_campaign import classify as primary_classify
from staged_campaign import families

State = tuple[int, int]
Edge = tuple[str, int, State]
FIELDS = (
    "direct",
    "local",
    "modular",
    "persistent",
    "commutes",
    "saturated",
    "unique_program",
    "state_count",
    "peak_count",
)


def successors(instance: StagedInstance, state: State) -> tuple[Edge, ...]:
    """Enumerate enabled transitions without using the primary checker."""
    program, fact = state
    result: list[Edge] = []
    for index, rule in enumerate(instance.programs[program].analyses):
        target = rule.table[fact]
        if target != fact:
            result.append(("analysis", index, (program, target)))
    for index, rule in enumerate(instance.rewrites):
        if rule.source == program and rule.guard[fact]:
            result.append(("rewrite", index, (rule.target, rule.transfer[fact])))
    return tuple(result)


def reachable_graph(instance: StagedInstance) -> tuple[State, tuple[State, ...], dict[State, tuple[Edge, ...]]]:
    initial = (instance.initial_program, instance.initial_fact)
    queue = [initial]
    seen = {initial}
    order: list[State] = []
    adjacency: dict[State, tuple[Edge, ...]] = {}
    cursor = 0
    while cursor < len(queue):
        state = queue[cursor]
        cursor += 1
        order.append(state)
        edges = successors(instance, state)
        adjacency[state] = edges
        for _, _, target in edges:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    if len(order) > len(instance.programs) * instance.lattice.n:
        raise AssertionError("finite state bound exceeded in independent oracle")
    return initial, tuple(order), adjacency


def terminal_sets(
    states: tuple[State, ...], adjacency: dict[State, tuple[Edge, ...]]
) -> dict[State, frozenset[State]]:
    memo: dict[State, frozenset[State]] = {}
    active: set[State] = set()

    def visit(state: State) -> frozenset[State]:
        if state in memo:
            return memo[state]
        if state in active:
            raise AssertionError("cycle found by independent oracle")
        active.add(state)
        edges = adjacency[state]
        if not edges:
            value = frozenset((state,))
        else:
            terminals: set[State] = set()
            for _, _, target in edges:
                terminals.update(visit(target))
            value = frozenset(terminals)
        active.remove(state)
        memo[state] = value
        return value

    for state in states:
        visit(state)
    return memo


def closure(instance: StagedInstance, program: int, fact: int) -> int:
    """Fair cyclic closure, independently written and cycle guarded."""
    current = fact
    seen = {current}
    while True:
        changed = False
        for rule in instance.programs[program].analyses:
            target = rule.table[current]
            if target != current:
                current = target
                changed = True
                if current in seen:
                    raise AssertionError("analysis cycle found by independent oracle")
                seen.add(current)
        if not changed:
            return current


def guard_persistent(instance: StagedInstance) -> bool:
    for rewrite in instance.rewrites:
        for fact, enabled in enumerate(rewrite.guard):
            if not enabled:
                continue
            for analysis in instance.programs[rewrite.source].analyses:
                if not rewrite.guard[analysis.table[fact]]:
                    return False
    return True


def all_closures(instance: StagedInstance) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(closure(instance, program, fact) for fact in range(instance.lattice.n))
        for program in range(len(instance.programs))
    )


def closure_commutes(instance: StagedInstance, closed: tuple[tuple[int, ...], ...]) -> bool:
    for rewrite in instance.rewrites:
        for fact, enabled in enumerate(rewrite.guard):
            if not enabled:
                continue
            source_closed = closed[rewrite.source][fact]
            early = closed[rewrite.target][rewrite.transfer[fact]]
            late = closed[rewrite.target][rewrite.transfer[source_closed]]
            if early != late:
                return False
    return True


def saturated_graph(
    instance: StagedInstance,
    closed: tuple[tuple[int, ...], ...],
) -> tuple[State, tuple[State, ...], dict[State, tuple[Edge, ...]]]:
    initial = (
        instance.initial_program,
        closed[instance.initial_program][instance.initial_fact],
    )
    queue = [initial]
    seen = {initial}
    order: list[State] = []
    adjacency: dict[State, tuple[Edge, ...]] = {}
    cursor = 0
    while cursor < len(queue):
        state = queue[cursor]
        cursor += 1
        order.append(state)
        program, fact = state
        edges: list[Edge] = []
        for index, rewrite in enumerate(instance.rewrites):
            if rewrite.source == program and rewrite.guard[fact]:
                target = (
                    rewrite.target,
                    closed[rewrite.target][rewrite.transfer[fact]],
                )
                edges.append(("rewrite", index, target))
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        adjacency[state] = tuple(edges)
    return initial, tuple(order), adjacency


def saturated_peaks_join(
    instance: StagedInstance, closed: tuple[tuple[int, ...], ...]
) -> bool:
    _, states, adjacency = saturated_graph(instance, closed)
    normals = terminal_sets(states, adjacency)
    for state in states:
        for left, right in combinations(adjacency[state], 2):
            if normals[left[2]].isdisjoint(normals[right[2]]):
                return False
    return True


def independent_classify(instance: StagedInstance) -> dict[str, bool | int]:
    initial, states, adjacency = reachable_graph(instance)
    normals = terminal_sets(states, adjacency)
    direct = all(len(normals[state]) == 1 for state in states)
    local = True
    peak_count = 0
    for state in states:
        for left, right in combinations(adjacency[state], 2):
            peak_count += 1
            if normals[left[2]].isdisjoint(normals[right[2]]):
                local = False
    persistent = guard_persistent(instance)
    closed = all_closures(instance)
    commutes = closure_commutes(instance, closed)
    saturated = saturated_peaks_join(instance, closed)
    initial_normals = normals[initial]
    return {
        "direct": direct,
        "local": local,
        "modular": persistent and commutes and saturated,
        "persistent": persistent,
        "commutes": commutes,
        "saturated": saturated,
        "unique_program": len({state[0] for state in initial_normals}) == 1,
        "state_count": len(states),
        "peak_count": peak_count,
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit_family(
    name: str,
    instances: Iterable[tuple[str, StagedInstance]],
    declared: int,
    limit: int | None,
    start: int = 0,
    stop: int | None = None,
) -> tuple[dict[str, int | str], list[dict[str, object]]]:
    if start < 0 or (stop is not None and stop < start):
        raise ValueError("invalid audit range")
    effective_stop = declared if stop is None else min(stop, declared)
    checked = 0
    mismatches = 0
    field_mismatches = {field: 0 for field in FIELDS}
    examples: list[dict[str, object]] = []
    for index, (parameters, instance) in enumerate(instances):
        if index < start:
            continue
        if index >= effective_stop:
            break
        if limit is not None and checked >= limit:
            break
        primary = primary_classify(instance)
        oracle = independent_classify(instance)
        checked += 1
        differences = [field for field in FIELDS if primary[field] != oracle[field]]
        if differences:
            mismatches += 1
            for field in differences:
                field_mismatches[field] += 1
            if len(examples) < 20:
                examples.append({
                    "family": name,
                    "parameters": parameters,
                    "fields": differences,
                    "primary": {field: primary[field] for field in differences},
                    "oracle": {field: oracle[field] for field in differences},
                })
    expected_checked = effective_stop - start
    if limit is not None:
        expected_checked = min(expected_checked, limit)
    if checked != expected_checked:
        raise RuntimeError(f"{name}: expected {expected_checked} instances in range, saw {checked}")
    row: dict[str, int | str] = {
        "family": name,
        "declared_instances": declared,
        "range_start": start,
        "range_stop_exclusive": start + checked,
        "instances_checked": checked,
        "instances_with_mismatch": mismatches,
        "field_comparisons": checked * len(FIELDS),
        "field_mismatches": sum(field_mismatches.values()),
    }
    row.update({f"mismatch_{field}": field_mismatches[field] for field in FIELDS})
    return row, examples


def run(
    out: Path,
    selected: set[str] | None = None,
    limit: int | None = None,
    start: int = 0,
    stop: int | None = None,
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    selected = selected or set()
    if (start or stop is not None) and len(selected) != 1:
        raise ValueError("--start/--stop require exactly one --family")
    rows: list[dict[str, int | str]] = []
    examples: list[dict[str, object]] = []
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    for name, factory, declared in families():
        if selected and name not in selected:
            continue
        row, found = audit_family(name, factory(), declared, limit, start, stop)
        rows.append(row)
        examples.extend(found)
        print(json.dumps({
            "family": name,
            "instances_checked": row["instances_checked"],
            "field_mismatches": row["field_mismatches"],
        }, sort_keys=True), flush=True)

    summary: dict[str, object] = {
        "schema": "pvso-independent-audit-1",
        "families": [row["family"] for row in rows],
        "pilot_limit_per_family": limit,
        "requested_range": [start, stop],
        "fields_compared": list(FIELDS),
        "instances_checked": sum(int(row["instances_checked"]) for row in rows),
        "field_comparisons": sum(int(row["field_comparisons"]) for row in rows),
        "instances_with_mismatch": sum(int(row["instances_with_mismatch"]) for row in rows),
        "field_mismatches": sum(int(row["field_mismatches"]) for row in rows),
        "mismatch_examples": examples,
        "shared_components": [
            "finite model dataclasses",
            "declared family generator",
        ],
        "separately_implemented_components": [
            "transition enumeration",
            "rooted reachability",
            "terminal-set propagation",
            "local-peak joinability",
            "analysis closure",
            "guard persistence",
            "closure commutation",
            "saturated rewrite graph",
            "terminal-program projection",
        ],
        "claim_boundary": (
            "Agreement cross-checks two implementations over the declared finite families; "
            "it is not a proof-assistant verification of the general metatheory."
        ),
    }
    write_json(out / "independent-audit-summary.json", summary)
    fields = list(rows[0].keys()) if rows else ["family"]
    with (out / "independent-audit-families.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_json(out / "independent-audit-resources.json", {
        "cpu_seconds": time.process_time() - started_cpu,
        "wall_seconds": time.perf_counter() - started_wall,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
    })
    if summary["field_mismatches"]:
        raise RuntimeError(f"independent audit found {summary['field_mismatches']} field mismatches")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--family", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    args = parser.parse_args()
    run(args.out, set(args.family or []), args.limit, args.start, args.stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
