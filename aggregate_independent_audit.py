#!/usr/bin/env python3
"""Aggregate process-isolated independent-classifier audit parts."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from staged_campaign import families


EXPECTED = {name: declared for name, _, declared in families()}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aggregate(parts: Path, out: Path) -> dict[str, object]:
    summaries = sorted(parts.glob("*/independent-audit-summary.json"))
    if not summaries:
        raise ValueError("no independent-audit parts found")
    rows_by_family: dict[str, dict[str, str]] = {}
    resources: list[dict[str, object]] = []
    examples: list[dict[str, object]] = []

    for summary_path in summaries:
        summary = load_json(summary_path)
        if summary.get("schema") != "pvso-independent-audit-1":
            raise ValueError(f"wrong part schema: {summary_path}")
        if summary.get("pilot_limit_per_family") is not None:
            raise ValueError(f"pilot-limited part cannot enter the final aggregate: {summary_path}")
        csv_path = summary_path.with_name("independent-audit-families.csv")
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            raise ValueError(f"each isolated part must contain exactly one family: {csv_path}")
        row = rows[0]
        family = row["family"]
        if family in rows_by_family:
            raise ValueError(f"duplicate audit family: {family}")
        if family not in EXPECTED:
            raise ValueError(f"unknown audit family: {family}")
        declared = EXPECTED[family]
        if int(row["declared_instances"]) != declared:
            raise ValueError(f"declared count mismatch for {family}")
        if int(row["range_start"]) != 0 or int(row["range_stop_exclusive"]) != declared:
            raise ValueError(f"incomplete audit range for {family}")
        if int(row["instances_checked"]) != declared:
            raise ValueError(f"incomplete checked count for {family}")
        rows_by_family[family] = row
        examples.extend(summary.get("mismatch_examples", []))
        resource_path = summary_path.with_name("independent-audit-resources.json")
        resources.append(load_json(resource_path))

    if set(rows_by_family) != set(EXPECTED):
        missing = sorted(set(EXPECTED) - set(rows_by_family))
        extra = sorted(set(rows_by_family) - set(EXPECTED))
        raise ValueError(f"audit family coverage mismatch; missing={missing}; extra={extra}")

    order = [name for name, _, _ in families()]
    rows = [rows_by_family[name] for name in order]
    instances = sum(int(row["instances_checked"]) for row in rows)
    comparisons = sum(int(row["field_comparisons"]) for row in rows)
    instance_mismatches = sum(int(row["instances_with_mismatch"]) for row in rows)
    field_mismatches = sum(int(row["field_mismatches"]) for row in rows)
    fields = [name.removeprefix("mismatch_") for name in rows[0] if name.startswith("mismatch_")]

    summary: dict[str, object] = {
        "schema": "pvso-independent-audit-aggregate-1",
        "families": order,
        "parts": len(summaries),
        "fields_compared": fields,
        "instances_checked": instances,
        "field_comparisons": comparisons,
        "instances_with_mismatch": instance_mismatches,
        "field_mismatches": field_mismatches,
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
        "process_isolation": (
            "Each family is audited in a fresh bounded child process so allocator and garbage-collector "
            "state from a large family cannot distort or stall a later family."
        ),
        "claim_boundary": (
            "Agreement cross-checks two implementations over the declared finite families; "
            "it is not a proof-assistant verification of the general metatheory."
        ),
    }
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "independent-audit-summary.json", summary)
    with (out / "independent-audit-families.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    write_json(out / "independent-audit-resources.json", {
        "parts": len(resources),
        "cumulative_cpu_seconds": sum(float(row.get("cpu_seconds", 0.0)) for row in resources),
        "cumulative_wall_seconds": sum(float(row.get("wall_seconds", 0.0)) for row in resources),
        "maximum_part_peak_rss_kib": max(int(row.get("peak_rss_kib", 0)) for row in resources),
        "workers_per_part": 1,
        "maximum_concurrent_parts": 1,
        "note": "Resource totals sum isolated part bodies; scientific aggregate fields are deterministic.",
    })
    if field_mismatches:
        raise RuntimeError(f"independent audit aggregate contains {field_mismatches} field mismatches")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.parts, args.out)
    print(json.dumps({
        "instances_checked": result["instances_checked"],
        "field_comparisons": result["field_comparisons"],
        "field_mismatches": result["field_mismatches"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
