"""Closed-certificate verifier for finite staged systems.

This module intentionally does not import the search/exploration implementation
in :mod:`staged_checker`.  It replays supplied transitions and proof paths from
the JSON instance, checks that the listed graph is exactly closed under all
rules, checks an acyclic reachability witness for every listed state, and checks
every local peak path.  It performs no fixed-point, reachability, join, or normal-
form search of its own.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable

from .staged_model import StagedInstance

State = tuple[int, int]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _remaining_heights(instance: StagedInstance) -> tuple[int, ...]:
    """Compute the lattice coheight table from the explicit order relation."""
    lat = instance.lattice
    memo: dict[int, int] = {}

    def visit(x: int) -> int:
        if x in memo:
            return memo[x]
        strict = [y for y in range(lat.n) if x != y and lat.le(x, y)]
        memo[x] = 0 if not strict else 1 + max(visit(y) for y in strict)
        return memo[x]

    return tuple(visit(x) for x in range(lat.n))


def _measure(instance: StagedInstance, state: State, rem: tuple[int, ...]) -> int:
    span = max(rem) + 1
    program, fact = state
    return instance.programs[program].rank * span + rem[fact]


def _event_transition(instance: StagedInstance, state: State, event: Any) -> tuple[State, str | None, str]:
    _require(isinstance(event, dict), "event must be an object")
    kind, rule = event.get("kind"), event.get("rule")
    _require(kind in {"analysis", "rewrite"}, "invalid event kind")
    _require(type(rule) is int, "event rule must be an integer")
    program, fact = state
    if kind == "analysis":
        rules = instance.programs[program].analyses
        _require(0 <= rule < len(rules), "analysis event is not enabled")
        selected = rules[rule]
        target_fact = selected.table[fact]
        _require(target_fact != fact, "analysis event is not enabled")
        if "name" in event:
            _require(event["name"] == selected.name, "event name mismatch")
        if "direction" in event:
            _require(event["direction"] == selected.direction, "event direction mismatch")
        return (program, target_fact), selected.direction, selected.name

    _require(0 <= rule < len(instance.rewrites), "rewrite event is not enabled")
    selected = instance.rewrites[rule]
    _require(selected.source == program and selected.guard[fact], "rewrite event is not enabled")
    if "name" in event:
        _require(event["name"] == selected.name, "event name mismatch")
    return (selected.target, selected.transfer[fact]), None, selected.name


def _successor_signatures(instance: StagedInstance, state: State) -> list[tuple[Any, ...]]:
    program, fact = state
    out: list[tuple[Any, ...]] = []
    for ai, rule in enumerate(instance.programs[program].analyses):
        target_fact = rule.table[fact]
        if target_fact != fact:
            out.append(("analysis", ai, state, (program, target_fact), rule.name, rule.direction))
    for ri, rule in enumerate(instance.rewrites):
        if rule.source == program and rule.guard[fact]:
            out.append(("rewrite", ri, state, (rule.target, rule.transfer[fact]), rule.name, None))
    return out


def _truth_tables(instance: StagedInstance) -> dict[str, Any]:
    source = instance.source_truth_table()
    tables = instance.program_truth_tables()
    rewrite_rows = []
    for ri, rewrite in enumerate(instance.rewrites):
        preserves = tables[rewrite.source] == tables[rewrite.target]
        rewrite_rows.append({
            "rule": ri,
            "name": rewrite.name,
            "source": instance.programs[rewrite.source].name,
            "target": instance.programs[rewrite.target].name,
            "preserves": preserves,
        })
    return {
        "source_truth_table": list(source),
        "program_truth_tables": [list(t) for t in tables],
        "all_programs_source_equivalent": all(t == source for t in tables),
        "all_rewrites_preserve_observation": all(row["preserves"] for row in rewrite_rows),
        "rewrites": rewrite_rows,
    }


def _peak_kind(a: tuple[Any, ...], b: tuple[Any, ...]) -> str:
    if a[0] == "analysis" and b[0] == "analysis":
        return "analysis/analysis"
    if a[0] == "rewrite" and b[0] == "rewrite":
        return "rewrite/rewrite"
    return "analysis/rewrite"


def verify_confluence_certificate(instance: StagedInstance, cert: Any) -> dict[str, Any]:
    """Replay a closed confluence certificate without graph or join search."""
    _require(isinstance(cert, dict), "certificate must be an object")
    _require(cert.get("schema") == "pvso-confluence-certificate-1", "wrong certificate schema")
    _require(cert.get("instance") == instance.name, "instance name mismatch")
    rem = _remaining_heights(instance)
    _require(cert.get("remaining_heights") == list(rem), "remaining-height mismatch")

    states_raw, edges_raw = cert.get("states"), cert.get("edges")
    _require(isinstance(states_raw, list) and states_raw, "invalid state list")
    _require(isinstance(edges_raw, list), "invalid edge list")
    _require(len(states_raw) <= len(instance.programs) * instance.lattice.n, "too many states")

    states: list[State] = []
    seen_states: set[State] = set()
    outgoing_ids: list[list[int]] = []
    parent_edges: list[int | None] = []
    for sid, row in enumerate(states_raw):
        _require(isinstance(row, dict) and row.get("id") == sid, "noncanonical state id")
        p, f = row.get("program"), row.get("fact")
        _require(type(p) is int and 0 <= p < len(instance.programs), "invalid state program")
        _require(type(f) is int and 0 <= f < instance.lattice.n, "invalid state fact")
        state = (p, f)
        _require(state not in seen_states, "duplicate state")
        seen_states.add(state)
        states.append(state)
        _require(row.get("measure") == _measure(instance, state, rem), "state measure mismatch")
        out = row.get("outgoing")
        _require(isinstance(out, list) and all(type(i) is int for i in out), "invalid outgoing list")
        outgoing_ids.append(out)
        parent = row.get("parent_edge")
        _require(parent is None or type(parent) is int, "invalid parent edge")
        parent_edges.append(parent)

    initial_id = cert.get("initial_state")
    _require(type(initial_id) is int and 0 <= initial_id < len(states), "invalid initial-state id")
    _require(states[initial_id] == (instance.initial_program, instance.initial_fact), "initial state mismatch")
    _require(parent_edges[initial_id] is None, "initial state must not have a parent")

    edge_sigs: list[tuple[Any, ...]] = []
    for eid, row in enumerate(edges_raw):
        _require(isinstance(row, dict) and row.get("id") == eid, "noncanonical edge id")
        src, dst = row.get("source"), row.get("target")
        _require(type(src) is int and 0 <= src < len(states), "invalid edge source")
        _require(type(dst) is int and 0 <= dst < len(states), "invalid edge target")
        event = {
            "kind": row.get("kind"), "rule": row.get("rule"),
            "name": row.get("name"), "direction": row.get("direction"),
        }
        target, direction, name = _event_transition(instance, states[src], event)
        _require(target == states[dst], "edge target mismatch")
        _require(row.get("direction") == direction, "edge direction mismatch")
        sig = (row.get("kind"), row.get("rule"), states[src], target, name, direction)
        _require(_measure(instance, target, rem) < _measure(instance, states[src], rem),
                 "edge does not decrease the ranking measure")
        edge_sigs.append(sig)

    assigned: list[int] = []
    for sid, state in enumerate(states):
        expected = _successor_signatures(instance, state)
        actual_ids = outgoing_ids[sid]
        _require(len(actual_ids) == len(set(actual_ids)), "duplicate outgoing edge id")
        _require(all(0 <= eid < len(edge_sigs) for eid in actual_ids), "outgoing edge id out of range")
        actual = [edge_sigs[eid] for eid in actual_ids]
        _require(actual == expected, "outgoing transition set mismatch")
        _require(all(edge_sigs[eid][2] == state for eid in actual_ids), "outgoing edge has wrong source")
        assigned.extend(actual_ids)
    _require(sorted(assigned) == list(range(len(edge_sigs))), "edge is missing or multiply assigned")

    # Acyclic parent witnesses establish reachability of every state.  Exact
    # successor coverage then establishes closure and hence equality with the
    # reachable graph.
    reached = {initial_id}
    for sid in range(len(states)):
        if sid == initial_id:
            continue
        parent = parent_edges[sid]
        _require(type(parent) is int and 0 <= parent < len(edge_sigs), "missing parent witness")
        src_id, dst_id = edges_raw[parent]["source"], edges_raw[parent]["target"]
        _require(dst_id == sid, "parent edge does not target the state")
        _require(src_id in reached, "parent witness is not acyclic/reachable")
        reached.add(sid)
    _require(len(reached) == len(states), "not every state has a reachability witness")

    terminals = cert.get("terminals")
    _require(isinstance(terminals, list) and all(type(i) is int for i in terminals), "invalid terminal list")
    expected_terminals = [sid for sid, out in enumerate(outgoing_ids) if not out]
    _require(terminals == expected_terminals, "terminal list mismatch")

    closures_raw = cert.get("closures")
    expected_pairs = [(p, f) for p in range(len(instance.programs)) for f in range(instance.lattice.n)]
    _require(isinstance(closures_raw, list) and len(closures_raw) == len(expected_pairs),
             "closure coverage mismatch")
    for row, pair in zip(closures_raw, expected_pairs):
        _require(isinstance(row, dict) and (row.get("program"), row.get("fact")) == pair,
                 "noncanonical closure row")
        program, current = pair
        trace = row.get("trace")
        _require(isinstance(trace, list) and all(type(i) is int for i in trace), "invalid closure trace")
        rules = instance.programs[program].analyses
        for ai in trace:
            _require(0 <= ai < len(rules), "closure trace rule out of range")
            target = rules[ai].table[current]
            _require(target != current, "closure trace contains a stutter")
            current = target
        _require(all(rule.table[current] == current for rule in rules), "closure trace does not end fixed")
        _require(row.get("final") == current, "closure final mismatch")

    peaks_raw = cert.get("peaks")
    _require(isinstance(peaks_raw, list), "invalid peak list")
    expected_peaks = [(sid, l, r) for sid, out in enumerate(outgoing_ids) for l, r in combinations(out, 2)]
    _require(len(peaks_raw) == len(expected_peaks), "peak coverage mismatch")
    for row, expected in zip(peaks_raw, expected_peaks):
        _require(isinstance(row, dict), "invalid peak row")
        sid, left_id, right_id = expected
        _require((row.get("state"), row.get("left_edge"), row.get("right_edge")) == expected,
                 "noncanonical peak row")
        left, right = edge_sigs[left_id], edge_sigs[right_id]
        _require(row.get("kind") == _peak_kind(left, right), "peak kind mismatch")
        join_id = row.get("join")
        _require(type(join_id) is int and 0 <= join_id < len(states), "invalid peak join")
        for start_edge_id, field in ((left_id, "left_path"), (right_id, "right_path")):
            path = row.get(field)
            _require(isinstance(path, list) and all(type(i) is int for i in path), "invalid join path")
            current = edge_sigs[start_edge_id][3]
            for eid in path:
                _require(0 <= eid < len(edge_sigs), "join path edge out of range")
                _require(edge_sigs[eid][2] == current, "join path is disconnected")
                current = edge_sigs[eid][3]
            _require(current == states[join_id], "join path ends at the wrong state")

    semantics = _truth_tables(instance)
    _require(cert.get("semantics") == semantics, "semantic table mismatch")
    expected_claims = {
        "terminating": True,
        "locally_confluent": True,
        "globally_confluent": True,
        "unique_terminal_state": len(terminals) == 1,
        "all_rewrites_preserve_observation": semantics["all_rewrites_preserve_observation"],
    }
    _require(cert.get("claims") == expected_claims, "claim summary mismatch")
    return {
        "valid": True,
        "states": len(states),
        "edges": len(edge_sigs),
        "peaks": len(peaks_raw),
        "terminals": len(terminals),
        "all_declared_rewrites_preserve_observation": semantics["all_rewrites_preserve_observation"],
        "terminal_programs_source_equivalent": all(
            semantics["program_truth_tables"][states[sid][0]] == semantics["source_truth_table"]
            for sid in terminals
        ),
    }


def _replay(instance: StagedInstance, events: Iterable[Any]) -> State:
    state = (instance.initial_program, instance.initial_fact)
    events = tuple(events)
    _require(len(events) <= 2 * (len(instance.programs) * instance.lattice.n + len(instance.rewrites) + 1),
             "overlong event trace")
    for event in events:
        state = _event_transition(instance, state, event)[0]
    return state


def verify_nonconfluence_witness(instance: StagedInstance, witness: Any) -> dict[str, Any]:
    """Replay two supplied terminal executions and compare their endpoints."""
    _require(isinstance(witness, dict), "witness must be an object")
    _require(witness.get("schema") == "pvso-nonconfluence-witness-1", "wrong witness schema")
    _require(witness.get("instance") == instance.name, "instance name mismatch")
    left_events, right_events = witness.get("left"), witness.get("right")
    _require(isinstance(left_events, list) and isinstance(right_events, list), "invalid witness paths")
    left, right = _replay(instance, left_events), _replay(instance, right_events)
    _require(witness.get("left_terminal") == list(left), "left terminal mismatch")
    _require(witness.get("right_terminal") == list(right), "right terminal mismatch")
    _require(not _successor_signatures(instance, left) and not _successor_signatures(instance, right),
             "witness path is not terminal")
    _require(left != right, "witness terminals are identical")
    return {
        "valid": True,
        "left_terminal": list(left),
        "right_terminal": list(right),
        "different_programs": left[0] != right[0],
    }
