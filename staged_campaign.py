#!/usr/bin/env python3
"""Exact enumeration over declared tiny staged-system families.

The campaign is exhaustive only for the explicit catalogs below.  It compares
(1) unique normal forms computed by terminal-set propagation, (2) joinability of
every reachable local peak, and (3) the modular saturation criterion.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path
import time
from typing import Iterable, Iterator

from src.model import chain, powerset, monotone_inflationary_maps
from src.staged_model import AnalysisRule, Program, RewriteRule, StagedInstance
from src.staged_checker import (
    _normal_forms,
    closure_commutes,
    explore,
    guards_persistent,
    local_peaks,
    saturated_rewrite_peaks_join,
)

EXPR = ("var", 0)
ID_B2 = (0, 1, 2, 3)
H_B2 = (1, 1, 3, 3)
Q_B2 = (2, 3, 2, 3)
TOP_B2 = (3, 3, 3, 3)
CANON_B2 = (ID_B2, H_B2, Q_B2, TOP_B2)
CANON_B2_NAMES = ("id", "add-H", "add-Q", "top")
GUARDS_B2 = (
    (False, False, False, False),
    (True, True, True, True),
    (False, True, False, True),
    (False, False, True, True),
    (False, False, False, True),
)
GUARDS_B2_NAMES = ("false", "true", "H", "Q", "H-and-Q")


def guard(mask: int, n: int) -> tuple[bool, ...]:
    return tuple(bool(mask & (1 << i)) for i in range(n))


def program(name: str, rank: int, maps: tuple[tuple[int, ...], ...]) -> Program:
    rules = tuple(AnalysisRule(f"a{i}", "forward" if i % 2 == 0 else "prophecy", table)
                  for i, table in enumerate(maps))
    return Program(name, rank, EXPR, rules)


def instance(name: str, lat, programs, rewrites) -> StagedInstance:
    return StagedInstance(name, lat, 1, EXPR, tuple(programs), tuple(rewrites), 0, lat.bottom,
                          tuple(str(i) for i in range(lat.n)))


def classify(inst: StagedInstance) -> dict[str, bool | int]:
    graph = explore(inst)
    normals = _normal_forms(graph)
    direct = all(len(normals[s]) == 1 for s in graph.states)
    local = True
    peak_count = 0
    # In a finite terminating graph, two states are joinable exactly when
    # their reachable normal-form sets intersect.  Reuse the already computed
    # normal-form table instead of running two descendant BFS traversals for
    # every peak.
    for _, left, right in local_peaks(graph):
        peak_count += 1
        if normals[left.target].isdisjoint(normals[right.target]):
            local = False
    persistent = guards_persistent(inst)[0]
    commutes = closure_commutes(inst)[0]
    sat = saturated_rewrite_peaks_join(inst)[0]
    modular = persistent and commutes and sat
    initial_nf = normals[graph.initial]
    unique_program = len({s[0] for s in initial_nf}) == 1
    return {
        "direct": direct,
        "local": local,
        "modular": modular,
        "persistent": persistent,
        "commutes": commutes,
        "saturated": sat,
        "unique_program": unique_program,
        "state_count": len(graph.states),
        "peak_count": peak_count,
    }


def one_rewrite_family(lat, tag: str) -> Iterator[tuple[str, StagedInstance]]:
    maps = monotone_inflationary_maps(lat)
    for i0, m0 in enumerate(maps):
        for i1, m1 in enumerate(maps):
            progs = (program("p0", 1, (m0,)), program("p1", 0, (m1,)))
            for gmask in range(1 << lat.n):
                g = guard(gmask, lat.n)
                for ti, transfer in enumerate(maps):
                    params = f"m0={i0};m1={i1};g={gmask};t={ti}"
                    rewrites = (RewriteRule("r0", 0, 1, g, transfer),)
                    yield params, instance(tag, lat, progs, rewrites)


def fork_family(lat, tag: str, maps: tuple[tuple[int, ...], ...]) -> Iterator[tuple[str, StagedInstance]]:
    for i0, m0 in enumerate(maps):
        for i1, m1 in enumerate(maps):
            for i2, m2 in enumerate(maps):
                progs = (program("p0", 1, (m0,)), program("p1", 0, (m1,)), program("p2", 0, (m2,)))
                for g0 in range(1 << lat.n):
                    for g1 in range(1 << lat.n):
                        guards = (guard(g0, lat.n), guard(g1, lat.n))
                        for t0, t1 in product(range(len(maps)), repeat=2):
                            rewrites = (
                                RewriteRule("left", 0, 1, guards[0], maps[t0]),
                                RewriteRule("right", 0, 2, guards[1], maps[t1]),
                            )
                            params = f"m={i0},{i1},{i2};g={g0},{g1};t={t0},{t1}"
                            yield params, instance(tag, lat, progs, rewrites)


def diamond_family() -> Iterator[tuple[str, StagedInstance]]:
    lat = powerset(2)
    progs = (
        program("p0", 2, (H_B2, Q_B2)),
        program("p1", 1, (ID_B2, Q_B2)),
        program("p2", 1, (H_B2, ID_B2)),
        program("p3", 0, (ID_B2, ID_B2)),
    )
    options = tuple((gi, ti) for gi in range(len(GUARDS_B2)) for ti in range(len(CANON_B2)))
    for choices in product(options, repeat=4):
        rules = []
        endpoints = ((0, 1), (0, 2), (1, 3), (2, 3))
        for ri, ((src, dst), (gi, ti)) in enumerate(zip(endpoints, choices)):
            rules.append(RewriteRule(f"r{ri}", src, dst, GUARDS_B2[gi], CANON_B2[ti]))
        params = ";".join(f"r{i}=g{gi}/t{ti}" for i, (gi, ti) in enumerate(choices))
        yield params, instance("C-B2-diamond", lat, progs, rules)


def two_analysis_family() -> Iterator[tuple[str, StagedInstance]]:
    lat = powerset(2)
    for a0, a1, b0, b1 in product(range(4), repeat=4):
        progs = (
            program("p0", 1, (CANON_B2[a0], CANON_B2[a1])),
            program("p1", 0, (CANON_B2[b0], CANON_B2[b1])),
        )
        for gmask in range(16):
            g = guard(gmask, 4)
            for ti, transfer in enumerate(CANON_B2):
                params = f"p0={a0},{a1};p1={b0},{b1};g={gmask};t={ti}"
                yield params, instance("D-B2-two-analysis", lat, progs,
                                       (RewriteRule("r0", 0, 1, g, transfer),))


def families():
    c2, c3, b2 = chain(2), chain(3), powerset(2)
    return [
        ("A-C2-one-rewrite", lambda: one_rewrite_family(c2, "A-C2-one-rewrite"), 32),
        ("A-C3-one-rewrite", lambda: one_rewrite_family(c3, "A-C3-one-rewrite"), 1000),
        ("A-B2-one-rewrite", lambda: one_rewrite_family(b2, "A-B2-one-rewrite"), 11664),
        ("B-C2-fork", lambda: fork_family(c2, "B-C2-fork", monotone_inflationary_maps(c2)), 512),
        ("B-B2-fork", lambda: fork_family(b2, "B-B2-fork", CANON_B2), 262144),
        ("C-B2-diamond", diamond_family, 160000),
        ("D-B2-two-analysis", two_analysis_family, 16384),
    ]


def empty_counts() -> dict[str, int]:
    return {
        "instances": 0,
        "direct_confluent": 0,
        "local_peak_confluent": 0,
        "newman_mismatches": 0,
        "modular_true": 0,
        "modular_false_positives": 0,
        "modular_false_negatives": 0,
        "guard_persistent": 0,
        "closure_commuting": 0,
        "saturated_peaks_join": 0,
        "unique_terminal_program": 0,
        "program_only_confluent": 0,
        "reachable_states_total": 0,
        "local_peaks_total": 0,
    }


def run_family(name: str, generator: Iterable[tuple[str, StagedInstance]], expected: int,
               limit: int | None = None) -> tuple[dict[str, int | float | str], dict[str, str]]:
    counts = empty_counts()
    examples: dict[str, str] = {}
    started = time.process_time()
    wall_started = time.perf_counter()
    for params, inst in generator:
        if limit is not None and counts["instances"] >= limit:
            break
        result = classify(inst)
        counts["instances"] += 1
        counts["direct_confluent"] += int(result["direct"])
        counts["local_peak_confluent"] += int(result["local"])
        counts["newman_mismatches"] += int(result["direct"] != result["local"])
        counts["modular_true"] += int(result["modular"])
        counts["modular_false_positives"] += int(result["modular"] and not result["direct"])
        counts["modular_false_negatives"] += int(result["direct"] and not result["modular"])
        counts["guard_persistent"] += int(result["persistent"])
        counts["closure_commuting"] += int(result["commutes"])
        counts["saturated_peaks_join"] += int(result["saturated"])
        counts["unique_terminal_program"] += int(result["unique_program"])
        counts["program_only_confluent"] += int(result["unique_program"] and not result["direct"])
        counts["reachable_states_total"] += int(result["state_count"])
        counts["local_peaks_total"] += int(result["peak_count"])
        categories = {
            "first_nonconfluent": not result["direct"],
            "first_modular_false_negative": result["direct"] and not result["modular"],
            "first_program_only": result["unique_program"] and not result["direct"],
            "first_persistence_failure": not result["persistent"],
            "first_commutation_failure": not result["commutes"],
            "first_saturated_peak_failure": not result["saturated"],
        }
        for key, condition in categories.items():
            if condition and key not in examples:
                examples[key] = params
    if limit is None and counts["instances"] != expected:
        raise RuntimeError(f"{name}: expected {expected} instances, saw {counts['instances']}")
    row: dict[str, int | float | str] = {"family": name, "declared_instances": expected, **counts}
    row["cpu_seconds"] = round(time.process_time() - started, 9)
    row["wall_seconds"] = round(time.perf_counter() - wall_started, 9)
    return row, examples


def run_campaign(out: Path, selected: set[str] | None = None, limit: int | None = None) -> dict:
    """Run the deterministic staged-system family campaign and write its evidence."""
    out.mkdir(parents=True, exist_ok=True)
    selected = selected or set()
    rows = []
    examples = {}
    campaign_cpu = time.process_time()
    campaign_wall = time.perf_counter()
    for name, factory, expected in families():
        if selected and name not in selected:
            continue
        row, found = run_family(name, factory(), expected, limit)
        rows.append(row)
        examples[name] = found
        print(json.dumps({"family": name, "instances": row["instances"],
                          "cpu_seconds": row["cpu_seconds"]}, sort_keys=True), flush=True)
    totals = empty_counts()
    for row in rows:
        for key in totals:
            totals[key] += int(row[key])
    summary = {
        "schema": "pvso-staged-enumeration-1",
        "selection": {
            "families": [row["family"] for row in rows],
            "pilot_limit_per_family": limit,
            "guard_encoding": "all Boolean tables where stated; five named B2 guards in the diamond family",
            "map_encoding": "all monotone inflationary maps where stated; id/add-H/add-Q/top canonical B2 maps where stated",
            "rewrite_graphs": "one edge, rank-one fork, rank-two diamond",
        },
        "totals": totals,
        "cpu_seconds": round(time.process_time() - campaign_cpu, 9),
        "wall_seconds": round(time.perf_counter() - campaign_wall, 9),
        "examples": examples,
        "families": rows,
    }
    (out / "staged-enumeration-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if rows:
        fields = list(rows[0].keys())
        with (out / "staged-enumeration-families.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    (out / "staged-enumeration-examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True) + "\n")
    # Retain raw counterexample rows, but fail if a theorem-instance gate fails.
    if totals["newman_mismatches"] or totals["modular_false_positives"]:
        raise RuntimeError(
            "staged campaign found exact/local disagreement or a modular false positive"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--family", action="append", help="run only the named family")
    parser.add_argument("--limit", type=int, help="pilot limit per selected family")
    args = parser.parse_args()
    run_campaign(args.out, set(args.family or []), args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
