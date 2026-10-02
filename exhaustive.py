#!/usr/bin/env python3
"""Deterministic bounded enumeration of maps, emitters, and guards.

The product-state oracle enumerates reachable states, not schedule prefixes.
This is sufficient because the admitted progress relation is acyclic.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import resource
import time
from src.model import named_lattice, monotone_inflationary_maps
from src.checker import (fact_reachability, least_common_fixed_point,
                         terminal_oracle, synthesize_guards)

FIELDS = ["lattice", "first_map", "second_map", "cases", "incomplete_cases",
          "complete_unique_cases", "complete_multiple_cases", "formula_mismatches",
          "maximal_guard_checks", "persistent_guard_checks",
          "strict_transition_guard_advantage_emitters"]


def mask_of(xs):
    return sum(1 << x for x in xs)


def check_pair(lat, maps, first, second):
    parents, edges = fact_reachability(lat.bottom, maps)
    mu = least_common_fixed_point(lat, maps)
    n = lat.n
    guards = [tuple(bool(g & (1 << x)) for x in range(n)) for g in range(1 << n)]
    row = dict.fromkeys(FIELDS, 0)
    row.update(lattice=lat.name, first_map=first, second_map=second)
    for e in range(1 << n):
        emissions = tuple((e >> x) & 1 for x in range(n))
        _, _, safe, persistent, order_safe = synthesize_guards(lat, maps, emissions)
        union_safe, union_persistent = 0, 0
        if persistent != order_safe:
            if not order_safe <= persistent:
                raise AssertionError("order-safe region is not contained in transition-safe region")
            row["strict_transition_guard_advantage_emitters"] += 1
        for g, guard in enumerate(guards):
            terminals, _, _ = terminal_oracle(lat.bottom, maps, guard, emissions)
            expected = {(mu, emissions[x]) for x in parents if guard[x]}
            if not guard[mu]:
                expected.add((mu, None))
            row["cases"] += 1
            if terminals != expected:
                row["formula_mismatches"] += 1
                raise AssertionError((lat.name, first, second, e, g, terminals, expected))
            complete = all(code is not None for _, code in terminals)
            if not complete:
                row["incomplete_cases"] += 1
            elif len(terminals) == 1:
                row["complete_unique_cases"] += 1
                reachable_guard = mask_of(x for x in parents if guard[x])
                union_safe |= reachable_guard
                closed = all(not guard[x] or all(guard[y] for _, y in edges[x]) for x in parents)
                if closed:
                    union_persistent |= reachable_guard
            else:
                row["complete_multiple_cases"] += 1
        if union_safe != mask_of(safe):
            raise AssertionError("maximal guard synthesis disagrees with all-guard enumeration")
        if union_persistent != mask_of(persistent):
            raise AssertionError("persistent guard synthesis disagrees with all-guard enumeration")
        row["maximal_guard_checks"] += 1
        row["persistent_guard_checks"] += 1
    return row


def resource_limits():
    # One process, one logical CPU. No children and no network operations.
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (180, 185))


def run_chunk(name, start, stop, out):
    resource_limits()
    wall, cpu = time.perf_counter(), time.process_time()
    lat = named_lattice(name)
    lat.validate()
    funcs = monotone_inflationary_maps(lat)
    if not 0 <= start < stop <= len(funcs):
        raise ValueError(f"require 0 <= start < stop <= {len(funcs)}")
    rows = []
    for i in range(start, stop):
        for j, g in enumerate(funcs):
            rows.append(check_pair(lat, (funcs[i], g), i, j))
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{name}-{start:03d}-{stop:03d}"
    path = out / (stem + ".csv")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metrics = {"lattice": name, "map_count": len(funcs), "first_map_start": start,
               "first_map_stop": stop, "map_pairs": len(rows),
               "cases": sum(r["cases"] for r in rows),
               "wall_seconds": time.perf_counter() - wall,
               "cpu_seconds": time.process_time() - cpu,
               "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "workers": 1, "children": 0, "timeouts": 0,
               "selection": "all ordered map pairs in the specified outer-index range; all binary emitters and guards",
               "seeds": None}
    (out / (stem + ".json")).write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lattice", required=True, choices=["C1", "C2", "C3", "C4", "C5", "B2", "M3", "N5"])
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run_chunk(args.lattice, args.start, args.stop, args.out)
