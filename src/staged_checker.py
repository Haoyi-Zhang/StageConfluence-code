"""Exact exploration and modular confluence checks for finite staged systems."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable

from .staged_model import StagedInstance

State = tuple[int, int]  # (program index, fact index)


@dataclass(frozen=True)
class Transition:
    kind: str
    rule: int
    source: State
    target: State
    name: str
    direction: str | None = None

    def signature(self) -> tuple[Any, ...]:
        return (self.kind, self.rule, self.source, self.target, self.name, self.direction)

    def event(self) -> dict[str, Any]:
        ans: dict[str, Any] = {"kind": self.kind, "rule": self.rule, "name": self.name}
        if self.direction is not None:
            ans["direction"] = self.direction
        return ans


def remaining_heights(instance: StagedInstance) -> tuple[int, ...]:
    lat = instance.lattice
    memo: dict[int, int] = {}

    def visit(x: int) -> int:
        if x in memo:
            return memo[x]
        strict = [y for y in range(lat.n) if x != y and lat.le(x, y)]
        memo[x] = 0 if not strict else 1 + max(visit(y) for y in strict)
        return memo[x]

    return tuple(visit(x) for x in range(lat.n))


def measure(instance: StagedInstance, state: State, rem: tuple[int, ...] | None = None) -> int:
    rem = rem or remaining_heights(instance)
    span = max(rem) + 1
    program, fact = state
    return instance.programs[program].rank * span + rem[fact]


def analysis_transitions(instance: StagedInstance, state: State) -> tuple[Transition, ...]:
    program, fact = state
    out: list[Transition] = []
    for ai, rule in enumerate(instance.programs[program].analyses):
        target_fact = rule.table[fact]
        if target_fact != fact:
            out.append(Transition("analysis", ai, state, (program, target_fact), rule.name, rule.direction))
    return tuple(out)


def rewrite_transitions(instance: StagedInstance, state: State) -> tuple[Transition, ...]:
    program, fact = state
    out: list[Transition] = []
    for ri, rule in enumerate(instance.rewrites):
        if rule.source == program and rule.guard[fact]:
            out.append(Transition("rewrite", ri, state, (rule.target, rule.transfer[fact]), rule.name, None))
    return tuple(out)


def successors(instance: StagedInstance, state: State) -> tuple[Transition, ...]:
    return analysis_transitions(instance, state) + rewrite_transitions(instance, state)


def apply_event(instance: StagedInstance, state: State, event: dict[str, Any]) -> Transition:
    if not isinstance(event, dict) or event.get("kind") not in {"analysis", "rewrite"}:
        raise ValueError("invalid event")
    rule = event.get("rule")
    if type(rule) is not int:
        raise ValueError("event rule must be an integer")
    options = analysis_transitions(instance, state) if event["kind"] == "analysis" else rewrite_transitions(instance, state)
    for transition in options:
        if transition.rule == rule:
            if "name" in event and event["name"] != transition.name:
                raise ValueError("event name mismatch")
            return transition
    raise ValueError("event is not enabled")


def replay_events(instance: StagedInstance, start: State, events: Iterable[dict[str, Any]]) -> State:
    state = start
    limit = len(instance.programs) * instance.lattice.n + len(instance.rewrites) + 1
    events_tuple = tuple(events)
    if len(events_tuple) > limit * 2:
        raise ValueError("overlong event trace")
    for event in events_tuple:
        state = apply_event(instance, state, event).target
    return state


@dataclass(frozen=True)
class Graph:
    initial: State
    states: tuple[State, ...]
    adjacency: dict[State, tuple[Transition, ...]]
    parent: dict[State, tuple[State, Transition] | None]


def explore(instance: StagedInstance) -> Graph:
    initial = (instance.initial_program, instance.initial_fact)
    queue: deque[State] = deque([initial])
    seen = {initial}
    order: list[State] = []
    adjacency: dict[State, tuple[Transition, ...]] = {}
    parent: dict[State, tuple[State, Transition] | None] = {initial: None}
    bound = len(instance.programs) * instance.lattice.n
    while queue:
        state = queue.popleft()
        order.append(state)
        edges = successors(instance, state)
        adjacency[state] = edges
        for edge in edges:
            if edge.target not in seen:
                seen.add(edge.target)
                parent[edge.target] = (state, edge)
                queue.append(edge.target)
        if len(seen) > bound:
            raise AssertionError("finite state bound exceeded")
    return Graph(initial, tuple(order), adjacency, parent)


def parent_path(graph: Graph, target: State) -> tuple[Transition, ...]:
    if target not in graph.parent:
        raise ValueError("target is not reachable")
    rev: list[Transition] = []
    state = target
    while graph.parent[state] is not None:
        prev, edge = graph.parent[state]  # type: ignore[misc]
        rev.append(edge)
        state = prev
    rev.reverse()
    return tuple(rev)


def descendants(graph: Graph, start: State) -> tuple[dict[State, int], dict[State, tuple[State, Transition] | None]]:
    queue: deque[State] = deque([start])
    dist = {start: 0}
    parent: dict[State, tuple[State, Transition] | None] = {start: None}
    while queue:
        state = queue.popleft()
        for edge in graph.adjacency[state]:
            if edge.target not in dist:
                dist[edge.target] = dist[state] + 1
                parent[edge.target] = (state, edge)
                queue.append(edge.target)
    return dist, parent


def path_from_parent(parent: dict[State, tuple[State, Transition] | None], target: State) -> tuple[Transition, ...]:
    rev: list[Transition] = []
    state = target
    while parent[state] is not None:
        prev, edge = parent[state]  # type: ignore[misc]
        rev.append(edge)
        state = prev
    rev.reverse()
    return tuple(rev)


def join_paths(graph: Graph, left: State, right: State) -> tuple[State, tuple[Transition, ...], tuple[Transition, ...]] | None:
    dl, pl = descendants(graph, left)
    dr, pr = descendants(graph, right)
    common = set(dl).intersection(dr)
    if not common:
        return None
    join = min(common, key=lambda s: (dl[s] + dr[s], max(dl[s], dr[s]), s[0], s[1]))
    return join, path_from_parent(pl, join), path_from_parent(pr, join)


def analysis_closure_trace(instance: StagedInstance, program: int, fact: int) -> tuple[int, tuple[int, ...]]:
    """Deterministic fair iteration; result is the least common fixed point above fact."""
    state = fact
    trace: list[int] = []
    rules = instance.programs[program].analyses
    # Every strict application decreases remaining height; at most h strict events.
    while True:
        changed = False
        for ai, rule in enumerate(rules):
            target = rule.table[state]
            if target != state:
                state = target
                trace.append(ai)
                changed = True
        if not changed:
            break
    return state, tuple(trace)


def analysis_closure(instance: StagedInstance, program: int, fact: int) -> int:
    return analysis_closure_trace(instance, program, fact)[0]


def _normal_forms(graph: Graph) -> dict[State, frozenset[State]]:
    memo: dict[State, frozenset[State]] = {}

    def visit(state: State) -> frozenset[State]:
        if state in memo:
            return memo[state]
        edges = graph.adjacency[state]
        if not edges:
            memo[state] = frozenset((state,))
        else:
            values: set[State] = set()
            for edge in edges:
                values.update(visit(edge.target))
            memo[state] = frozenset(values)
        return memo[state]

    for state in graph.states:
        visit(state)
    return memo


def peak_kind(a: Transition, b: Transition) -> str:
    if a.kind == "analysis" and b.kind == "analysis":
        return "analysis/analysis"
    if a.kind == "rewrite" and b.kind == "rewrite":
        return "rewrite/rewrite"
    return "analysis/rewrite"


def local_peaks(graph: Graph) -> tuple[tuple[State, Transition, Transition], ...]:
    ans: list[tuple[State, Transition, Transition]] = []
    for state in graph.states:
        for left, right in combinations(graph.adjacency[state], 2):
            ans.append((state, left, right))
    return tuple(ans)


def guards_persistent(instance: StagedInstance) -> tuple[bool, tuple[dict[str, Any], ...]]:
    failures: list[dict[str, Any]] = []
    for ri, rewrite in enumerate(instance.rewrites):
        for fact in range(instance.lattice.n):
            if not rewrite.guard[fact]:
                continue
            for ai, analysis in enumerate(instance.programs[rewrite.source].analyses):
                target = analysis.table[fact]
                if not rewrite.guard[target]:
                    failures.append({"rewrite": ri, "analysis": ai, "fact": fact, "target": target})
    return not failures, tuple(failures)


def closure_commutes(instance: StagedInstance) -> tuple[bool, tuple[dict[str, Any], ...]]:
    failures: list[dict[str, Any]] = []
    for ri, rewrite in enumerate(instance.rewrites):
        for fact in range(instance.lattice.n):
            if not rewrite.guard[fact]:
                continue
            src_closed = analysis_closure(instance, rewrite.source, fact)
            early = analysis_closure(instance, rewrite.target, rewrite.transfer[fact])
            late = analysis_closure(instance, rewrite.target, rewrite.transfer[src_closed])
            if early != late:
                failures.append({
                    "rewrite": ri,
                    "fact": fact,
                    "source_closure": src_closed,
                    "early_target_closure": early,
                    "late_target_closure": late,
                })
    return not failures, tuple(failures)


@dataclass(frozen=True)
class SaturatedGraph:
    initial: State
    states: tuple[State, ...]
    adjacency: dict[State, tuple[Transition, ...]]


def saturated_graph(instance: StagedInstance) -> SaturatedGraph:
    initial = (instance.initial_program, analysis_closure(instance, instance.initial_program, instance.initial_fact))
    queue: deque[State] = deque([initial])
    seen = {initial}
    order: list[State] = []
    adjacency: dict[State, tuple[Transition, ...]] = {}
    while queue:
        state = queue.popleft()
        order.append(state)
        program, fact = state
        out: list[Transition] = []
        for ri, rewrite in enumerate(instance.rewrites):
            if rewrite.source == program and rewrite.guard[fact]:
                target_fact = analysis_closure(instance, rewrite.target, rewrite.transfer[fact])
                target = (rewrite.target, target_fact)
                out.append(Transition("rewrite", ri, state, target, rewrite.name, None))
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        adjacency[state] = tuple(out)
    return SaturatedGraph(initial, tuple(order), adjacency)


def saturated_rewrite_peaks_join(instance: StagedInstance) -> tuple[bool, tuple[dict[str, Any], ...]]:
    sat = saturated_graph(instance)
    graph = Graph(sat.initial, sat.states, sat.adjacency, {sat.initial: None})
    # Rank decreases on every saturated edge, so the graph terminates.  Two
    # branch targets join iff they share a reachable normal form.  Computing
    # the table once avoids repeated descendant searches while preserving the
    # exact relation-level test.
    normals = _normal_forms(graph)
    failures: list[dict[str, Any]] = []
    for state in sat.states:
        for left, right in combinations(sat.adjacency[state], 2):
            if normals[left.target].isdisjoint(normals[right.target]):
                failures.append({"state": list(state), "left_rule": left.rule, "right_rule": right.rule})
    return not failures, tuple(failures)


def semantic_report(instance: StagedInstance) -> dict[str, Any]:
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


def analyze_staged(instance: StagedInstance, include_peak_paths: bool = False) -> dict[str, Any]:
    graph = explore(instance)
    rem = remaining_heights(instance)
    height = max(rem)
    measure_failures = []
    for state in graph.states:
        for edge in graph.adjacency[state]:
            if measure(instance, edge.target, rem) >= measure(instance, edge.source, rem):
                measure_failures.append({"source": list(edge.source), "target": list(edge.target)})
    normals = _normal_forms(graph)
    terminals = tuple(state for state in graph.states if not graph.adjacency[state])
    peak_rows: list[dict[str, Any]] = []
    peak_counts = {"analysis/analysis": 0, "analysis/rewrite": 0, "rewrite/rewrite": 0}
    unjoinable = 0
    for state, left, right in local_peaks(graph):
        kind = peak_kind(left, right)
        peak_counts[kind] += 1
        joined = join_paths(graph, left.target, right.target)
        row: dict[str, Any] = {
            "state": list(state),
            "kind": kind,
            "left": left.event(),
            "right": right.event(),
            "joinable": joined is not None,
        }
        if joined is None:
            unjoinable += 1
        elif include_peak_paths:
            join, lp, rp = joined
            row.update({
                "join": list(join),
                "left_path": [e.event() for e in lp],
                "right_path": [e.event() for e in rp],
            })
        peak_rows.append(row)
    persistent, persistence_failures = guards_persistent(instance)
    commutes, commutation_failures = closure_commutes(instance)
    sat_join, sat_failures = saturated_rewrite_peaks_join(instance)
    exact = unjoinable == 0
    globally_confluent = all(len(normals[state]) == 1 for state in graph.states)
    initial_normals = normals[graph.initial]
    terminal_programs = {state[0] for state in initial_normals}
    sem = semantic_report(instance)
    reachable_rewrite_rules = sorted({edge.rule for state in graph.states for edge in graph.adjacency[state]
                                      if edge.kind == "rewrite"})
    tables = instance.program_truth_tables()
    source_table = instance.source_truth_table()
    reachable_rulewise_preservation = all(
        tables[instance.rewrites[ri].source] == tables[instance.rewrites[ri].target]
        for ri in reachable_rewrite_rules
    )
    unique_terminal_program_source_equivalent = (
        len(terminal_programs) == 1 and tables[next(iter(terminal_programs))] == source_table
    )
    analysis_directions = sorted({a.direction for p in instance.programs for a in p.analyses})
    return {
        "schema": "pvso-analysis-1",
        "instance": instance.as_summary(),
        "analysis_directions": analysis_directions,
        "reachable_state_count": len(graph.states),
        "reachable_states": [list(s) for s in graph.states],
        "edge_count": sum(len(graph.adjacency[s]) for s in graph.states),
        "fact_height": height,
        "termination_measure_valid": not measure_failures,
        "termination_measure_failures": measure_failures,
        "terminal_states": [list(s) for s in terminals],
        "initial_normal_forms": [list(s) for s in sorted(initial_normals)],
        "unique_terminal_state": len(initial_normals) == 1,
        "unique_terminal_program": len(terminal_programs) == 1,
        "local_peak_counts": peak_counts,
        "unjoinable_local_peak_count": unjoinable,
        "exact_local_peak_criterion": exact,
        "global_confluence": globally_confluent,
        "newman_equivalence_holds": exact == globally_confluent,
        "guard_persistence": persistent,
        "guard_persistence_failures": list(persistence_failures),
        "closure_commutation": commutes,
        "closure_commutation_failures": list(commutation_failures),
        "saturated_rewrite_peaks_join": sat_join,
        "saturated_rewrite_peak_failures": list(sat_failures),
        "modular_saturation_criterion": persistent and commutes and sat_join,
        "semantic_preservation": {
            **sem,
            "reachable_rewrite_rules": reachable_rewrite_rules,
            "reachable_rewrites_preserve_observation": reachable_rulewise_preservation,
            "unique_terminal_program_source_equivalent": unique_terminal_program_source_equivalent,
        },
        "schedule_independent_source_equivalent_program": unique_terminal_program_source_equivalent,
        "peaks": peak_rows,
    }


def find_two_terminal_paths(instance: StagedInstance) -> tuple[tuple[Transition, ...], tuple[Transition, ...]] | None:
    graph = explore(instance)
    terminals = [s for s in graph.states if not graph.adjacency[s]]
    if len(terminals) < 2:
        return None
    # Deterministically prefer different residual programs, then different states.
    for left, right in combinations(terminals, 2):
        if left[0] != right[0]:
            return parent_path(graph, left), parent_path(graph, right)
    return parent_path(graph, terminals[0]), parent_path(graph, terminals[1])
