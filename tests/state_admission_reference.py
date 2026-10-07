"""Independent literal finite reference for admitted JSON tables, not a parser.

No production imports, historical verifier copy, private paths, or graph search
helpers. Enumerate P x F and compute a relation's transitive closure directly.
The graph reference is deliberately limited to 64 declared pairs. The separate
all-pairs duplicate oracle also handles the bounded 2,048-row admission probes.
"""
from itertools import combinations, product


def order(raw):
    lattice = raw["lattice"]
    kind = lattice["kind"]
    if kind == "chain":
        n = lattice["size"]
        return [[x <= y for y in range(n)] for x in range(n)]
    if kind == "powerset":
        n = 1 << lattice["bits"]
        return [[x & y == x for y in range(n)] for x in range(n)]
    if kind == "explicit":
        rows = lattice["upper"]
        return [[bool(row & (1 << y)) for y in range(len(rows))] for row in rows]
    raise ValueError("unsupported reference lattice")


def coheights(raw):
    le = order(raw)
    heights = [0] * len(le)
    # Synchronous longest-path relaxation, independent of recursive production.
    for _ in range(len(le)):
        heights = [max([0] + [1 + heights[y] for y in range(len(le))
                              if x != y and le[x][y]]) for x in range(len(le))]
    return heights


def first_duplicate(pairs):
    """First duplicate's row, using literal pair comparisons, not a seen set."""
    return next((later for later in range(len(pairs))
                 for earlier in range(later) if pairs[earlier] == pairs[later]), None)


def evaluate(node, bits):
    op = node[0]
    if op == "const":
        return node[1]
    if op == "var":
        return bits[node[1]]
    if op == "not":
        return int(not evaluate(node[1], bits))
    left, right = evaluate(node[1], bits), evaluate(node[2], bits)
    if op == "and":
        return int(bool(left) and bool(right))
    if op == "or":
        return int(bool(left) or bool(right))
    if op == "xor":
        return int(bool(left) != bool(right))
    raise ValueError("unsupported reference expression")


def literal_reference(raw):
    le = order(raw)
    programs, n = raw["programs"], len(le)
    states = list(product(range(len(programs)), range(n)))
    if len(states) > 64:
        raise ValueError("literal graph reference is bounded to 64 declared pairs")
    index = {state: i for i, state in enumerate(states)}
    names = [p.get("name", f"p{i}") for i, p in enumerate(programs)]

    def resolve(value):
        return names.index(value) if isinstance(value, str) else value

    adjacency = {}
    for p, f in states:
        edges = []
        for ai, analysis in enumerate(programs[p]["analyses"]):
            target = analysis["table"][f]
            if target != f:
                edges.append(("analysis", ai, (p, f), (p, target),
                              analysis.get("name", f"a{ai}"),
                              analysis.get("direction", "auxiliary")))
        for ri, rewrite in enumerate(raw.get("rewrites", [])):
            if resolve(rewrite["source"]) == p and rewrite["guard"][f]:
                edges.append(("rewrite", ri, (p, f),
                              (resolve(rewrite["target"]), rewrite["transfer"][f]),
                              rewrite.get("name", f"r{ri}"), None))
        adjacency[(p, f)] = edges

    relation = [{i} | {index[e[3]] for e in adjacency[s]} for i, s in enumerate(states)]
    for middle in range(len(states)):
        for start in range(len(states)):
            if middle in relation[start]:
                relation[start] |= relation[middle]
    initial_program = resolve(raw.get("initial_program", 0))
    initial_fact = raw.get("initial_fact", raw["lattice"].get("bottom", 0))
    reachable = {states[i] for i in relation[index[(initial_program, initial_fact)]]}
    terminal = {s for s in reachable if not adjacency[s]}
    confluent = all(len({states[i] for i in relation[index[s]]} & terminal) == 1
                    for s in reachable)
    peaks = [(s, a, b) for s in sorted(reachable)
             for a, b in combinations(adjacency[s], 2)]
    unjoinable = sum(not (relation[index[a[3]]] & relation[index[b[3]]])
                     for _, a, b in peaks)
    closures = {}
    for p, f in states:
        fixed = [x for x in range(n) if le[f][x]
                 and all(a["table"][x] == x for a in programs[p]["analyses"])]
        least = [x for x in fixed if all(le[x][y] for y in fixed)]
        if len(least) != 1:
            raise ValueError("admitted reference maps must have a unique least closure")
        closures[(p, f)] = least[0]

    environments = [tuple((env >> bit) & 1 for bit in range(raw["inputs"]))
                    for env in range(1 << raw["inputs"])]
    source = [evaluate(raw["source_expression"], env) for env in environments]
    tables = [[evaluate(p["expression"], env) for env in environments] for p in programs]
    rewrite_rows = [{"rule": ri, "name": r.get("name", f"r{ri}"),
                     "source": names[resolve(r["source"])], "target": names[resolve(r["target"])],
                     "preserves": tables[resolve(r["source"])] == tables[resolve(r["target"])]}
                    for ri, r in enumerate(raw.get("rewrites", []))]
    semantics = {"source_truth_table": source, "program_truth_tables": tables,
                 "all_programs_source_equivalent": all(t == source for t in tables),
                 "all_rewrites_preserve_observation": all(r["preserves"] for r in rewrite_rows),
                 "rewrites": rewrite_rows}
    return {"reachable": reachable, "adjacency": adjacency, "terminal": terminal,
            "confluent": confluent, "unjoinable": unjoinable, "peaks": len(peaks),
            "edges": sum(len(adjacency[s]) for s in reachable),
            "closures": closures, "semantics": semantics}
