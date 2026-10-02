"""Exact finite checks for a fixed analysis with one irreversible emission slot."""
from __future__ import annotations
from collections import deque
from typing import Any, Sequence
from .model import Instance, Lattice, truth_table


def fact_reachability(bottom: int, maps: Sequence[Sequence[int]]):
    queue = deque([bottom])
    parents: dict[int, tuple[int, int] | None] = {bottom: None}
    edges: dict[int, tuple[tuple[int, int], ...]] = {}
    while queue:
        x = queue.popleft()
        out = []
        for i, f in enumerate(maps):
            y = f[x]
            if y != x:
                out.append((i, y))
                if y not in parents:
                    parents[y] = (x, i)
                    queue.append(y)
        edges[x] = tuple(out)
    return parents, edges


def least_common_fixed_point(lat: Lattice, maps: Sequence[Sequence[int]]) -> int:
    """Small oracle: inspect every lattice element, not any worklist trace."""
    fixed = [x for x in range(lat.n) if all(f[x] == x for f in maps)]
    least = [x for x in fixed if all(lat.le(x, y) for y in fixed)]
    if len(least) != 1:
        raise ValueError("no unique least common fixed point")
    return least[0]


def round_robin(start: int, maps: Sequence[Sequence[int]], n: int):
    x, events = start, []
    for _ in range(n):
        changed = False
        for i, f in enumerate(maps):
            if f[x] != x:
                x = f[x]
                events.append({"op": "apply", "map": i})
                changed = True
        if not changed:
            return x, events
    raise ValueError("round-robin bound exceeded; assumptions may not hold")


def terminal_oracle(bottom: int, maps: Sequence[Sequence[int]],
                    guard: Sequence[bool], emissions: Sequence[Any]):
    """Independent full product-state BFS. None means uncommitted.

    The supplied emissions must be hashable and cannot be None. The public
    instance parser uses syntax strings, so None is unambiguous.
    """
    initial = (bottom, None)
    seen, queue = {initial}, deque([initial])
    terminals = set()
    edge_count = 0
    while queue:
        x, code = queue.popleft()
        out = [(f[x], code) for f in maps if f[x] != x]
        if code is None and guard[x]:
            out.append((x, emissions[x]))
        edge_count += len(out)
        if not out:
            terminals.add((x, code))
        for s in out:
            if s not in seen:
                seen.add(s)
                queue.append(s)
    return terminals, len(seen), edge_count


def synthesize_guards(lat: Lattice, maps, emissions):
    parents, edges = fact_reachability(lat.bottom, maps)
    reachable = set(parents)
    mu = least_common_fixed_point(lat, maps)
    target = emissions[mu]
    safe = {x for x in reachable if emissions[x] == target}
    bad = reachable - safe
    reverse = {x: set() for x in reachable}
    for x, outs in edges.items():
        for _, y in outs:
            reverse[y].add(x)
    can_reach_bad = set(bad)
    todo = list(bad)
    while todo:
        y = todo.pop()
        for x in reverse[y]:
            if x not in can_reach_bad:
                can_reach_bad.add(x)
                todo.append(x)
    persistent = reachable - can_reach_bad
    # A stronger, sometimes unnecessarily restrictive order-upward condition.
    order_safe = {x for x in reachable if all(not lat.le(x, y) for y in bad)}
    return mu, reachable, safe, persistent, order_safe


def factor_terminals(instance: Instance):
    lat, maps, codes = instance.lattice, instance.maps, instance.codes()
    parents, _ = fact_reachability(lat.bottom, maps)
    mu = least_common_fixed_point(lat, maps)
    result = {(mu, codes[x]) for x in parents if instance.guard[x]}
    if not instance.guard[mu]:
        result.add((mu, None))
    return result


def analyze(instance: Instance) -> dict[str, Any]:
    instance.validate()
    lat, maps, codes = instance.lattice, instance.maps, instance.codes()
    actual, states, edges = terminal_oracle(lat.bottom, maps, instance.guard, codes)
    predicted = factor_terminals(instance)
    if actual != predicted:
        raise AssertionError("factorization disagrees with the full-state oracle")
    mu, reachable, safe, persistent, order_safe = synthesize_guards(lat, maps, codes)
    artifacts = sorted({code for _, code in actual if code is not None})
    complete = all(code is not None for _, code in actual)
    source = truth_table(instance.source, instance.inputs)
    semantics = {code: truth_table(expr, instance.inputs)
                 for code, expr in zip(codes, instance.emissions)}
    preserving = all(semantics[code] == source for code in artifacts) if artifacts else None
    semantic_values = tuple(truth_table(e, instance.inputs) for e in instance.emissions)
    _, _, semantic_safe, semantic_persistent, _ = synthesize_guards(lat, maps, semantic_values)
    final_preserving = semantic_values[mu] == source
    return {
        "name": instance.name, "least_fixed_point": mu,
        "reachable_fact_states": sorted(reachable),
        "full_state_count": states, "transition_count_with_rule_labels": edges,
        "terminal_count": len(actual), "terminal_artifacts": artifacts,
        "all_maximal_progress_runs_complete": complete,
        "unique_syntactic_output_for_all_runs": complete and len(artifacts) == 1,
        "completed_runs_preserve_source": preserving,
        "source_truth_table": list(source),
        "final_output_preserves_source": final_preserving,
        "complete_source_preserving_guard_exists": final_preserving,
        "maximal_final_semantics_guard_reachable": sorted(semantic_safe),
        "maximal_persistent_final_semantics_guard_reachable": sorted(semantic_persistent),
        "maximal_safe_guard_reachable": sorted(safe),
        "maximal_persistent_safe_guard_reachable": sorted(persistent),
        "order_upward_safe_guard_reachable": sorted(order_safe),
        "factorization_matches_product_oracle": True,
    }


def prefix_events(parents, x):
    rev = []
    while parents[x] is not None:
        prev, rule = parents[x]
        rev.append({"op": "apply", "map": rule})
        x = prev
    return list(reversed(rev))


def make_witness(instance: Instance) -> dict[str, Any] | None:
    instance.validate()
    lat, maps, codes = instance.lattice, instance.maps, instance.codes()
    parents, _ = fact_reachability(lat.bottom, maps)
    mu = least_common_fixed_point(lat, maps)
    if not instance.guard[mu]:
        cert = {"case": instance.name, "kind": "incomplete",
                "runs": [prefix_events(parents, mu)]}
    else:
        bad = next((x for x in sorted(parents)
                    if instance.guard[x] and codes[x] != codes[mu]), None)
        if bad is not None:
            final, suffix = round_robin(bad, maps, lat.n)
            if final != mu:
                raise AssertionError("unexpected suffix fixed point")
            cert = {"case": instance.name, "kind": "different_syntax",
                    "runs": [prefix_events(parents, bad) + [{"op": "emit"}] + suffix,
                             prefix_events(parents, mu) + [{"op": "emit"}]]}
        else:
            source = truth_table(instance.source, instance.inputs)
            wrong = next((x for x in sorted(parents) if instance.guard[x]
                          and truth_table(instance.emissions[x], instance.inputs) != source), None)
            if wrong is None:
                return None
            _, suffix = round_robin(wrong, maps, lat.n)
            cert = {"case": instance.name, "kind": "wrong_semantics",
                    "runs": [prefix_events(parents, wrong) + [{"op": "emit"}] + suffix]}
    verify_witness(instance, cert)
    return cert


def verify_witness(instance: Instance, certificate: Any) -> dict[str, Any]:
    """Replay every event; do not call reachability or fixed-point synthesis."""
    instance.validate()
    if not isinstance(certificate, dict) or certificate.get("case") != instance.name:
        raise ValueError("certificate case mismatch")
    kind = certificate.get("kind")
    if kind not in {"incomplete", "different_syntax", "wrong_semantics"}:
        raise ValueError("unknown certificate kind")
    runs = certificate.get("runs")
    expected = 2 if kind == "different_syntax" else 1
    if not isinstance(runs, list) or len(runs) != expected:
        raise ValueError("wrong number of runs")
    outputs = []
    codes = instance.codes()
    for events in runs:
        if not isinstance(events, list) or len(events) > instance.lattice.n:
            raise ValueError("invalid or overlong progress trace")
        state, code = instance.lattice.bottom, None
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            if event.get("op") == "apply":
                rule = event.get("map")
                if type(rule) is not int or not 0 <= rule < len(instance.maps):
                    raise ValueError("invalid map index")
                target = instance.maps[rule][state]
                if target == state:
                    raise ValueError("trace contains a nonprogress application")
                state = target
            elif event.get("op") == "emit":
                if code is not None or not instance.guard[state]:
                    raise ValueError("illegal or repeated emission")
                code = codes[state]
            else:
                raise ValueError("unknown event")
        if any(f[state] != state for f in instance.maps):
            raise ValueError("trace is not terminal: analysis progress remains")
        if code is None and instance.guard[state]:
            raise ValueError("trace is not terminal: emission remains")
        outputs.append((state, code))
    if kind == "incomplete" and outputs[0][1] is not None:
        raise ValueError("claimed incomplete run has an artifact")
    if kind == "different_syntax":
        if any(code is None for _, code in outputs) or outputs[0][1] == outputs[1][1]:
            raise ValueError("runs do not witness two distinct completed outputs")
    if kind == "wrong_semantics":
        code = outputs[0][1]
        if code is None:
            raise ValueError("semantic witness has no artifact")
        expr = instance.emissions[codes.index(code)]
        if truth_table(expr, instance.inputs) == truth_table(instance.source, instance.inputs):
            raise ValueError("artifact is semantically equivalent to the source")
    return {"valid": True, "kind": kind,
            "terminal_states": [{"fact": x, "artifact": code} for x, code in outputs]}
