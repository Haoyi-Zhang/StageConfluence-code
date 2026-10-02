"""Finite lattices and a total, pure Boolean residual language.

This is an executable finite model, not a proof-assistant formalization.
No external packages, code execution from inputs, or network access are used.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import json
from typing import Any, Iterable

MAX_STATES = 64
MAX_MAPS = 32
MAX_INPUTS = 8
MAX_EXPR_NODES = 1024
MAX_EXPR_DEPTH = 32


def integer(x: Any, lo: int, hi: int, label: str) -> int:
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError(f"{label}: expected integer in [{lo}, {hi}]")
    return x


@dataclass(frozen=True)
class Lattice:
    name: str
    upper: tuple[int, ...]
    bottom: int
    top: int

    @property
    def n(self) -> int:
        return len(self.upper)

    def le(self, x: int, y: int) -> bool:
        return bool(self.upper[x] & (1 << y))

    def validate(self) -> None:
        n = integer(self.n, 1, MAX_STATES, "lattice size")
        integer(self.bottom, 0, n - 1, "bottom")
        integer(self.top, 0, n - 1, "top")
        for row in self.upper:
            integer(row, 0, (1 << n) - 1, "order row")
        for x in range(n):
            if not self.le(x, x):
                raise ValueError("order is not reflexive")
            if not self.le(self.bottom, x) or not self.le(x, self.top):
                raise ValueError("invalid bottom/top")
            for y in range(n):
                if x != y and self.le(x, y) and self.le(y, x):
                    raise ValueError("order is not antisymmetric")
                if self.le(x, y) and self.upper[y] & ~self.upper[x]:
                    raise ValueError("order is not transitive")
        for x in range(n):
            for y in range(n):
                ups = [z for z in range(n) if self.le(x, z) and self.le(y, z)]
                lows = [z for z in range(n) if self.le(z, x) and self.le(z, y)]
                if sum(all(self.le(z, w) for w in ups) for z in ups) != 1:
                    raise ValueError("pair has no unique least upper bound")
                if sum(all(self.le(w, z) for w in lows) for z in lows) != 1:
                    raise ValueError("pair has no unique greatest lower bound")

    def as_dict(self) -> dict[str, Any]:
        return {"kind": "explicit", "name": self.name, "upper": list(self.upper),
                "bottom": self.bottom, "top": self.top}


def chain(n: int) -> Lattice:
    integer(n, 1, MAX_STATES, "chain size")
    return Lattice(f"C{n}", tuple(sum(1 << y for y in range(x, n)) for x in range(n)), 0, n - 1)


def powerset(bits: int) -> Lattice:
    integer(bits, 0, 6, "powerset bits")
    n = 1 << bits
    return Lattice(f"B{bits}", tuple(sum(1 << y for y in range(n) if x & y == x)
                                   for x in range(n)), 0, n - 1)


def named_lattice(name: str) -> Lattice:
    if name in {"C1", "C2", "C3", "C4", "C5"}:
        return chain(int(name[1:]))
    if name in {"B2", "B3"}:
        return powerset(int(name[1:]))
    # M3: bottom, three incomparable atoms, top.
    if name == "M3":
        return Lattice(name, (31, 18, 20, 24, 16), 0, 4)
    # N5: bottom < a < b < top and bottom < c < top.
    if name == "N5":
        return Lattice(name, (31, 22, 20, 24, 16), 0, 4)
    raise ValueError(f"unknown lattice {name}")


def load_lattice(raw: Any) -> Lattice:
    if not isinstance(raw, dict):
        raise ValueError("lattice must be an object")
    kind = raw.get("kind")
    if kind == "chain":
        lat = chain(integer(raw.get("size"), 1, MAX_STATES, "size"))
    elif kind == "powerset":
        lat = powerset(integer(raw.get("bits"), 0, 6, "bits"))
    elif kind == "explicit":
        upper = raw.get("upper")
        if not isinstance(upper, list) or not 1 <= len(upper) <= MAX_STATES:
            raise ValueError("invalid explicit order size")
        n = len(upper)
        lat = Lattice(str(raw.get("name", "explicit")),
                      tuple(integer(x, 0, (1 << n) - 1, "order row") for x in upper),
                      integer(raw.get("bottom"), 0, n - 1, "bottom"),
                      integer(raw.get("top"), 0, n - 1, "top"))
    else:
        raise ValueError("unknown lattice encoding")
    lat.validate()
    return lat


def validate_maps(lat: Lattice, maps: tuple[tuple[int, ...], ...]) -> None:
    integer(len(maps), 1, MAX_MAPS, "map count")
    for i, f in enumerate(maps):
        if len(f) != lat.n:
            raise ValueError(f"map {i}: incorrect table length")
        for x, v in enumerate(f):
            integer(v, 0, lat.n - 1, f"map {i} value")
            if not lat.le(x, v):
                raise ValueError(f"map {i}: noninflationary at {x}")
        for x in range(lat.n):
            for y in range(lat.n):
                if lat.le(x, y) and not lat.le(f[x], f[y]):
                    raise ValueError(f"map {i}: nonmonotone at {x} <= {y}")


def monotone_inflationary_maps(lat: Lattice) -> tuple[tuple[int, ...], ...]:
    """Exact enumeration, intended only for the supplied small lattices."""
    if lat.n > 8:
        raise ValueError("enumeration is restricted to at most 8 lattice elements")
    choices = [[y for y in range(lat.n) if lat.le(x, y)] for x in range(lat.n)]
    pairs = [(x, y) for x in range(lat.n) for y in range(lat.n) if lat.le(x, y)]
    return tuple(f for f in product(*choices) if all(lat.le(f[x], f[y]) for x, y in pairs))


def expression(raw: Any, inputs: int) -> tuple:
    """Validate before interpretation. Only the six documented AST forms exist."""
    count = 0
    def walk(node: Any, depth: int) -> tuple:
        nonlocal count
        count += 1
        if count > MAX_EXPR_NODES or depth > MAX_EXPR_DEPTH:
            raise ValueError("expression exceeds structural bound")
        if not isinstance(node, (list, tuple)) or not node or not isinstance(node[0], str):
            raise ValueError("invalid expression node")
        tag = node[0]
        if tag == "const" and len(node) == 2:
            return (tag, integer(node[1], 0, 1, "constant"))
        if tag == "var" and len(node) == 2:
            if inputs == 0:
                raise ValueError("variable in an input-free expression")
            return (tag, integer(node[1], 0, inputs - 1, "variable"))
        if tag == "not" and len(node) == 2:
            return (tag, walk(node[1], depth + 1))
        if tag in {"and", "or", "xor"} and len(node) == 3:
            return (tag, walk(node[1], depth + 1), walk(node[2], depth + 1))
        raise ValueError("unknown expression form or arity")
    return walk(raw, 0)


def evaluate(expr: tuple, env: int) -> int:
    tag = expr[0]
    if tag == "const":
        return expr[1]
    if tag == "var":
        return (env >> expr[1]) & 1
    if tag == "not":
        return 1 - evaluate(expr[1], env)
    a, b = evaluate(expr[1], env), evaluate(expr[2], env)
    if tag == "and":
        return a & b
    if tag == "or":
        return a | b
    if tag == "xor":
        return a ^ b
    raise ValueError("unvalidated expression")


def truth_table(expr: tuple, inputs: int) -> tuple[int, ...]:
    return tuple(evaluate(expr, env) for env in range(1 << inputs))


def syntax_key(expr: tuple) -> str:
    return json.dumps(expr, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class Instance:
    name: str
    lattice: Lattice
    maps: tuple[tuple[int, ...], ...]
    map_names: tuple[str, ...]
    guard: tuple[bool, ...]
    emissions: tuple[tuple, ...]
    inputs: int
    source: tuple

    def validate(self) -> None:
        self.lattice.validate()
        validate_maps(self.lattice, self.maps)
        if len(self.map_names) != len(self.maps):
            raise ValueError("map-name count mismatch")
        if len(self.guard) != self.lattice.n or any(type(x) is not bool for x in self.guard):
            raise ValueError("guard must contain one Boolean per lattice element")
        if len(self.emissions) != self.lattice.n:
            raise ValueError("emission table length mismatch")
        integer(self.inputs, 0, MAX_INPUTS, "input count")
        expression(self.source, self.inputs)
        for expr in self.emissions:
            expression(expr, self.inputs)

    def codes(self) -> tuple[str, ...]:
        return tuple(syntax_key(e) for e in self.emissions)


def load_instance(raw: Any) -> Instance:
    if not isinstance(raw, dict):
        raise ValueError("instance must be an object")
    lat = load_lattice(raw.get("lattice"))
    inputs = integer(raw.get("inputs"), 0, MAX_INPUTS, "input count")
    rows = raw.get("maps")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_MAPS:
        raise ValueError("invalid map list")
    maps, names = [], []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("table"), list):
            raise ValueError("map must have a table")
        if len(row["table"]) != lat.n:
            raise ValueError("map table length mismatch")
        maps.append(tuple(integer(x, 0, lat.n - 1, "map value") for x in row["table"]))
        names.append(str(row.get("name", f"rule{i}")))
    guards = raw.get("guard")
    emits = raw.get("emissions")
    if not isinstance(guards, list) or not isinstance(emits, list):
        raise ValueError("guard and emissions must be arrays")
    if len(guards) != lat.n or len(emits) != lat.n:
        raise ValueError("state table length mismatch")
    ans = Instance(str(raw.get("name", "case")), lat, tuple(maps), tuple(names),
                   tuple(guards), tuple(expression(e, inputs) for e in emits),
                   inputs, expression(raw.get("source"), inputs))
    ans.validate()
    return ans
