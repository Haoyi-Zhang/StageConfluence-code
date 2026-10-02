"""Finite code-changing bidirectional staged systems.

The module defines a closed JSON model for finite lattices, residual Boolean
programs, monotone/inflationary forward or prophecy analyses, and rank-decreasing
semantics-preserving rewrite candidates.  Inputs never execute code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import (
    Lattice,
    MAX_INPUTS,
    expression,
    integer,
    load_lattice,
    syntax_key,
    truth_table,
    validate_maps,
)

MAX_PROGRAMS = 32
MAX_ANALYSES_PER_PROGRAM = 16
MAX_REWRITES = 64
MAX_RANK = 1024
ALLOWED_DIRECTIONS = {"forward", "prophecy", "history", "auxiliary"}


@dataclass(frozen=True)
class AnalysisRule:
    name: str
    direction: str
    table: tuple[int, ...]


@dataclass(frozen=True)
class Program:
    name: str
    rank: int
    expression: tuple
    analyses: tuple[AnalysisRule, ...]


@dataclass(frozen=True)
class RewriteRule:
    name: str
    source: int
    target: int
    guard: tuple[bool, ...]
    transfer: tuple[int, ...]


@dataclass(frozen=True)
class StagedInstance:
    name: str
    lattice: Lattice
    inputs: int
    source_expression: tuple
    programs: tuple[Program, ...]
    rewrites: tuple[RewriteRule, ...]
    initial_program: int
    initial_fact: int
    fact_labels: tuple[str, ...]

    def validate(self) -> None:
        self.lattice.validate()
        integer(self.inputs, 0, MAX_INPUTS, "input count")
        if not 1 <= len(self.programs) <= MAX_PROGRAMS:
            raise ValueError("invalid program count")
        if len({p.name for p in self.programs}) != len(self.programs):
            raise ValueError("program names must be unique")
        expression(self.source_expression, self.inputs)
        for pi, program in enumerate(self.programs):
            integer(program.rank, 0, MAX_RANK, f"program {pi} rank")
            expression(program.expression, self.inputs)
            if not 1 <= len(program.analyses) <= MAX_ANALYSES_PER_PROGRAM:
                raise ValueError(f"program {pi}: invalid analysis-rule count")
            if len({a.name for a in program.analyses}) != len(program.analyses):
                raise ValueError(f"program {pi}: analysis names must be unique")
            for ai, analysis in enumerate(program.analyses):
                if analysis.direction not in ALLOWED_DIRECTIONS:
                    raise ValueError(f"program {pi} analysis {ai}: invalid direction")
                validate_maps(self.lattice, (analysis.table,))
        if not 0 <= self.initial_program < len(self.programs):
            raise ValueError("invalid initial program")
        if not 0 <= self.initial_fact < self.lattice.n:
            raise ValueError("invalid initial fact")
        if not 0 <= len(self.rewrites) <= MAX_REWRITES:
            raise ValueError("invalid rewrite count")
        if len({r.name for r in self.rewrites}) != len(self.rewrites):
            raise ValueError("rewrite names must be unique")
        for ri, rewrite in enumerate(self.rewrites):
            if not 0 <= rewrite.source < len(self.programs):
                raise ValueError(f"rewrite {ri}: invalid source")
            if not 0 <= rewrite.target < len(self.programs):
                raise ValueError(f"rewrite {ri}: invalid target")
            if self.programs[rewrite.target].rank >= self.programs[rewrite.source].rank:
                raise ValueError(f"rewrite {ri}: rank does not strictly decrease")
            if len(rewrite.guard) != self.lattice.n or any(type(v) is not bool for v in rewrite.guard):
                raise ValueError(f"rewrite {ri}: guard must contain one Boolean per fact")
            validate_maps(self.lattice, (rewrite.transfer,))
        if len(self.fact_labels) != self.lattice.n:
            raise ValueError("fact-label count mismatch")
        if len(set(self.fact_labels)) != len(self.fact_labels):
            raise ValueError("fact labels must be unique")

    def program_index(self, name: str) -> int:
        for i, program in enumerate(self.programs):
            if program.name == name:
                return i
        raise ValueError(f"unknown program {name}")

    def source_truth_table(self) -> tuple[int, ...]:
        return truth_table(self.source_expression, self.inputs)

    def program_truth_tables(self) -> tuple[tuple[int, ...], ...]:
        return tuple(truth_table(p.expression, self.inputs) for p in self.programs)

    def as_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lattice": self.lattice.name,
            "facts": self.lattice.n,
            "programs": len(self.programs),
            "rewrites": len(self.rewrites),
            "initial": [self.programs[self.initial_program].name, self.fact_labels[self.initial_fact]],
        }


def _table(raw: Any, n: int, label: str) -> tuple[int, ...]:
    if not isinstance(raw, list) or len(raw) != n:
        raise ValueError(f"{label}: expected a table of length {n}")
    return tuple(integer(v, 0, n - 1, f"{label} value") for v in raw)


def _guard(raw: Any, n: int, label: str) -> tuple[bool, ...]:
    if not isinstance(raw, list) or len(raw) != n or any(type(v) is not bool for v in raw):
        raise ValueError(f"{label}: expected {n} Boolean values")
    return tuple(raw)


def load_staged_instance(raw: Any) -> StagedInstance:
    if not isinstance(raw, dict):
        raise ValueError("instance must be an object")
    lattice = load_lattice(raw.get("lattice"))
    inputs = integer(raw.get("inputs"), 0, MAX_INPUTS, "input count")
    source_expr = expression(raw.get("source_expression"), inputs)
    programs_raw = raw.get("programs")
    if not isinstance(programs_raw, list) or not 1 <= len(programs_raw) <= MAX_PROGRAMS:
        raise ValueError("invalid program list")

    programs: list[Program] = []
    names: dict[str, int] = {}
    for pi, prow in enumerate(programs_raw):
        if not isinstance(prow, dict):
            raise ValueError("program must be an object")
        name = str(prow.get("name", f"p{pi}"))
        if name in names:
            raise ValueError("program names must be unique")
        names[name] = pi
        analyses_raw = prow.get("analyses")
        if not isinstance(analyses_raw, list) or not 1 <= len(analyses_raw) <= MAX_ANALYSES_PER_PROGRAM:
            raise ValueError(f"program {name}: invalid analyses")
        analyses: list[AnalysisRule] = []
        for ai, arow in enumerate(analyses_raw):
            if not isinstance(arow, dict):
                raise ValueError("analysis must be an object")
            analyses.append(AnalysisRule(
                name=str(arow.get("name", f"a{ai}")),
                direction=str(arow.get("direction", "auxiliary")),
                table=_table(arow.get("table"), lattice.n, f"analysis {name}/{ai}"),
            ))
        programs.append(Program(
            name=name,
            rank=integer(prow.get("rank"), 0, MAX_RANK, f"program {name} rank"),
            expression=expression(prow.get("expression"), inputs),
            analyses=tuple(analyses),
        ))

    rewrites_raw = raw.get("rewrites", [])
    if not isinstance(rewrites_raw, list) or len(rewrites_raw) > MAX_REWRITES:
        raise ValueError("invalid rewrite list")
    rewrites: list[RewriteRule] = []
    for ri, rrow in enumerate(rewrites_raw):
        if not isinstance(rrow, dict):
            raise ValueError("rewrite must be an object")
        src_raw, dst_raw = rrow.get("source"), rrow.get("target")
        source = names.get(src_raw) if isinstance(src_raw, str) else src_raw
        target = names.get(dst_raw) if isinstance(dst_raw, str) else dst_raw
        if type(source) is not int or type(target) is not int:
            raise ValueError(f"rewrite {ri}: unknown program name")
        rewrites.append(RewriteRule(
            name=str(rrow.get("name", f"r{ri}")),
            source=source,
            target=target,
            guard=_guard(rrow.get("guard"), lattice.n, f"rewrite {ri} guard"),
            transfer=_table(rrow.get("transfer"), lattice.n, f"rewrite {ri} transfer"),
        ))

    initial_program_raw = raw.get("initial_program", 0)
    initial_program = names.get(initial_program_raw) if isinstance(initial_program_raw, str) else initial_program_raw
    if type(initial_program) is not int:
        raise ValueError("unknown initial program")
    labels_raw = raw.get("fact_labels")
    if labels_raw is None:
        fact_labels = tuple(str(i) for i in range(lattice.n))
    elif isinstance(labels_raw, list) and len(labels_raw) == lattice.n:
        fact_labels = tuple(str(v) for v in labels_raw)
    else:
        raise ValueError("invalid fact labels")

    instance = StagedInstance(
        name=str(raw.get("name", "staged-case")),
        lattice=lattice,
        inputs=inputs,
        source_expression=source_expr,
        programs=tuple(programs),
        rewrites=tuple(rewrites),
        initial_program=integer(initial_program, 0, len(programs) - 1, "initial program"),
        initial_fact=integer(raw.get("initial_fact", lattice.bottom), 0, lattice.n - 1, "initial fact"),
        fact_labels=fact_labels,
    )
    instance.validate()
    return instance


def expression_key(instance: StagedInstance, program: int) -> str:
    return syntax_key(instance.programs[program].expression)
