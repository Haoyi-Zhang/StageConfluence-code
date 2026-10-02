#!/usr/bin/env python3
"""Generate retained case reports, certificates, witnesses, and mutation evidence."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import resource
import time
from pathlib import Path
from typing import Any, Callable

from src.staged_model import load_staged_instance
from src.staged_checker import analyze_staged
from src.staged_certificate import make_confluence_certificate, make_nonconfluence_witness
from src.staged_verify import verify_confluence_certificate, verify_nonconfluence_witness

POSITIVE = ("S01", "S07", "S08", "S09", "S11")
NEGATIVE = ("S02", "S03", "S04", "S10")
ALL_CASES = ("S01", "S02", "S03", "S04", "S07", "S08", "S09", "S10", "S11")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def expect_rejection(label: str, verify: Callable[[Any], Any], value: Any,
                     rows: list[dict[str, Any]]) -> None:
    try:
        verify(value)
    except ValueError as exc:
        rows.append({"mutation": label, "rejected": True, "diagnostic": str(exc)})
        return
    rows.append({"mutation": label, "rejected": False, "diagnostic": "accepted"})
    raise RuntimeError(f"mutation unexpectedly accepted: {label}")


def mutation_campaign(instance, certificate, witnesses: dict[str, tuple[Any, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    verify_cert = lambda c: verify_confluence_certificate(instance, c)

    def mutate(label: str, change: Callable[[Any], None]) -> None:
        value = copy.deepcopy(certificate)
        change(value)
        expect_rejection(label, verify_cert, value, rows)

    mutate("certificate/instance", lambda c: c.__setitem__("instance", "not-the-instance"))
    mutate("certificate/remaining-height", lambda c: c["remaining_heights"].__setitem__(0, 999))
    for i in range(len(certificate["states"])):
        mutate(f"state/{i}/measure", lambda c, i=i: c["states"][i].__setitem__("measure", c["states"][i]["measure"] + 1))
    for i, edge in enumerate(certificate["edges"]):
        other = (edge["target"] + 1) % len(certificate["states"])
        mutate(f"edge/{i}/target", lambda c, i=i, other=other: c["edges"][i].__setitem__("target", other))
    for i, state in enumerate(certificate["states"]):
        if state["outgoing"]:
            mutate(f"state/{i}/outgoing-coverage", lambda c, i=i: c["states"][i]["outgoing"].pop())
        if i != certificate["initial_state"]:
            mutate(f"state/{i}/parent", lambda c, i=i: c["states"][i].__setitem__("parent_edge", None))
    for i, row in enumerate(certificate["closures"]):
        alternate = (row["final"] + 1) % instance.lattice.n
        if alternate != row["final"]:
            mutate(f"closure/{i}/final", lambda c, i=i, alternate=alternate: c["closures"][i].__setitem__("final", alternate))
    for i, row in enumerate(certificate["peaks"]):
        other = (row["join"] + 1) % len(certificate["states"])
        mutate(f"peak/{i}/join", lambda c, i=i, other=other: c["peaks"][i].__setitem__("join", other))
    for i, table in enumerate(certificate["semantics"]["program_truth_tables"]):
        if table:
            mutate(f"semantics/program/{i}/bit0",
                   lambda c, i=i: c["semantics"]["program_truth_tables"][i].__setitem__(
                       0, 1 - c["semantics"]["program_truth_tables"][i][0]))
    mutate("claims/global-confluence", lambda c: c["claims"].__setitem__("globally_confluent", False))

    for name, (neg_instance, witness) in witnesses.items():
        verify_wit = lambda w, inst=neg_instance: verify_nonconfluence_witness(inst, w)
        value = copy.deepcopy(witness)
        value["left_terminal"][1] = (value["left_terminal"][1] + 1) % neg_instance.lattice.n
        if value["left_terminal"] == witness["left_terminal"]:
            value["left_terminal"][0] = (value["left_terminal"][0] + 1) % len(neg_instance.programs)
        expect_rejection(f"witness/{name}/terminal", verify_wit, value, rows)
        side = "left" if witness["left"] else "right"
        if witness[side]:
            value = copy.deepcopy(witness)
            value[side][0]["rule"] = 999
            expect_rejection(f"witness/{name}/event", verify_wit, value, rows)
    return rows


def generate_evidence(cases: Path, out: Path) -> dict[str, Any]:
    """Generate deterministic case reports, certificates, witnesses, and mutations."""
    out.mkdir(parents=True, exist_ok=True)

    instances = {name: load_staged_instance(load(cases / f"{name}.json")) for name in ALL_CASES}
    summary_rows: list[dict[str, Any]] = []
    certificates: dict[str, Any] = {}
    witnesses: dict[str, tuple[Any, Any]] = {}

    for name in ALL_CASES:
        instance = instances[name]
        report = analyze_staged(instance, include_peak_paths=True)
        dump(out / "cases" / f"{name}-analysis.json", report)
        kind, verified = "analysis-only", False
        if name in POSITIVE:
            cert = make_confluence_certificate(instance)
            if cert is None:
                raise RuntimeError(f"{name}: expected a confluence certificate")
            result = verify_confluence_certificate(instance, cert)
            dump(out / "certificates" / f"{name}-certificate.json", cert)
            dump(out / "certificates" / f"{name}-verification.json", result)
            certificates[name], kind, verified = cert, "confluence-certificate", True
        elif name in NEGATIVE:
            witness = make_nonconfluence_witness(instance)
            if witness is None:
                raise RuntimeError(f"{name}: expected a nonconfluence witness")
            result = verify_nonconfluence_witness(instance, witness)
            dump(out / "witnesses" / f"{name}-witness.json", witness)
            dump(out / "witnesses" / f"{name}-verification.json", result)
            witnesses[name], kind, verified = (instance, witness), "nonconfluence-witness", True
        summary_rows.append({
            "case": name,
            "instance": instance.name,
            "evidence": kind,
            "verified": verified,
            "reachable_states": report["reachable_state_count"],
            "edges": report["edge_count"],
            "local_peaks": sum(report["local_peak_counts"].values()),
            "state_confluent": report["global_confluence"],
            "unique_terminal_program": report["unique_terminal_program"],
            "modular_criterion": report["modular_saturation_criterion"],
            "source_equivalent_program": report["schedule_independent_source_equivalent_program"],
        })

    mutations = mutation_campaign(instances["S01"], certificates["S01"], witnesses)
    with (out / "mutation-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("mutation", "rejected", "diagnostic"))
        writer.writeheader(); writer.writerows(mutations)
    mutation_summary = {
        "schema": "pvso-mutation-campaign-1",
        "mutations": len(mutations),
        "rejected": sum(bool(row["rejected"]) for row in mutations),
        "accepted": sum(not bool(row["rejected"]) for row in mutations),
        "basis": "single-field mutations of S01 certificate and all retained negative witnesses",
    }
    dump(out / "mutation-summary.json", mutation_summary)

    with (out / "case-summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader(); writer.writerows(summary_rows)
    dump(out / "case-summary.json", {
        "schema": "pvso-case-evidence-1",
        "cases": summary_rows,
        "positive_certificates": list(POSITIVE),
        "negative_witnesses": list(NEGATIVE),
        "mutation_summary": mutation_summary,
    })
    print(json.dumps({"cases": len(summary_rows), **mutation_summary}, sort_keys=True))
    return {"cases": len(summary_rows), **mutation_summary}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("staged_cases"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started_cpu, started_wall = time.process_time(), time.perf_counter()
    generate_evidence(args.cases, args.out)
    dump(args.out / "staged-evidence-resources.json", {
        "cpu_seconds": time.process_time() - started_cpu,
        "wall_seconds": time.perf_counter() - started_wall,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
        "children": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
