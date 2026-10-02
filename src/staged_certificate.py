"""Certificate and counterexample generation for finite staged systems.

Verification lives in :mod:`staged_verify`, which deliberately does not import
the search implementation used here.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from .staged_checker import (
    Graph,
    State,
    Transition,
    analysis_closure_trace,
    analyze_staged,
    explore,
    find_two_terminal_paths,
    join_paths,
    local_peaks,
    measure,
    peak_kind,
    remaining_heights,
    semantic_report,
)
from .staged_model import StagedInstance
from .staged_verify import verify_confluence_certificate, verify_nonconfluence_witness


def _state_key(state: State) -> str:
    return f"{state[0]}:{state[1]}"


def _events(path: tuple[Transition, ...]) -> list[dict[str, Any]]:
    return [edge.event() for edge in path]


def make_confluence_certificate(instance: StagedInstance) -> dict[str, Any] | None:
    report = analyze_staged(instance)
    if not report["exact_local_peak_criterion"]:
        return None
    graph = explore(instance)
    rem = remaining_heights(instance)
    state_ids = {state: i for i, state in enumerate(graph.states)}
    edges: list[Transition] = []
    edge_ids: dict[tuple[Any, ...], int] = {}
    outgoing: dict[State, list[int]] = {s: [] for s in graph.states}
    for state in graph.states:
        for edge in graph.adjacency[state]:
            eid = len(edges)
            edges.append(edge)
            edge_ids[edge.signature()] = eid
            outgoing[state].append(eid)

    states_json = []
    for state in graph.states:
        parent = graph.parent[state]
        parent_edge = None if parent is None else edge_ids[parent[1].signature()]
        states_json.append({
            "id": state_ids[state],
            "program": state[0],
            "fact": state[1],
            "measure": measure(instance, state, rem),
            "parent_edge": parent_edge,
            "outgoing": outgoing[state],
        })
    edges_json = [{
        "id": i,
        "kind": edge.kind,
        "rule": edge.rule,
        "name": edge.name,
        "direction": edge.direction,
        "source": state_ids[edge.source],
        "target": state_ids[edge.target],
    } for i, edge in enumerate(edges)]

    peaks_json = []
    for state, left, right in local_peaks(graph):
        joined = join_paths(graph, left.target, right.target)
        if joined is None:
            raise AssertionError("certificate requested for a nonconfluent graph")
        join, left_path, right_path = joined
        peaks_json.append({
            "state": state_ids[state],
            "kind": peak_kind(left, right),
            "left_edge": edge_ids[left.signature()],
            "right_edge": edge_ids[right.signature()],
            "join": state_ids[join],
            "left_path": [edge_ids[e.signature()] for e in left_path],
            "right_path": [edge_ids[e.signature()] for e in right_path],
        })

    closures = []
    for program in range(len(instance.programs)):
        for fact in range(instance.lattice.n):
            final, trace = analysis_closure_trace(instance, program, fact)
            closures.append({"program": program, "fact": fact, "final": final, "trace": list(trace)})

    sem = semantic_report(instance)
    terminals = [state_ids[s] for s in graph.states if not graph.adjacency[s]]
    return {
        "schema": "pvso-confluence-certificate-1",
        "instance": instance.name,
        "initial_state": state_ids[graph.initial],
        "remaining_heights": list(rem),
        "states": states_json,
        "edges": edges_json,
        "terminals": terminals,
        "closures": closures,
        "peaks": peaks_json,
        "semantics": sem,
        "claims": {
            "terminating": True,
            "locally_confluent": True,
            "globally_confluent": True,
            "unique_terminal_state": len(terminals) == 1,
            "all_rewrites_preserve_observation": sem["all_rewrites_preserve_observation"],
        },
    }



def make_nonconfluence_witness(instance: StagedInstance) -> dict[str, Any] | None:
    paths = find_two_terminal_paths(instance)
    if paths is None:
        return None
    left, right = paths
    left_terminal = left[-1].target if left else (instance.initial_program, instance.initial_fact)
    right_terminal = right[-1].target if right else (instance.initial_program, instance.initial_fact)
    return {
        "schema": "pvso-nonconfluence-witness-1",
        "instance": instance.name,
        "left": _events(left),
        "right": _events(right),
        "left_terminal": list(left_terminal),
        "right_terminal": list(right_terminal),
    }
