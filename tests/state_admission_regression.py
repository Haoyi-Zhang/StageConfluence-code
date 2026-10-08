"""Portable, finite, untimed regression for ordered certificate admission.

Run this file directly from any working directory. No campaign/driver imports,
subprocesses, writes, network, or private snapshot dependencies. Deliberately
not named test_*.py: the retained 81-test inventory/results remain historical.
Admission-only probes must fail at the root-ID sentinel, not count as proofs.
"""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from state_admission_reference import coheights, first_duplicate, literal_reference
from src.staged_model import load_staged_instance
from src.staged_checker import analyze_staged
from src.staged_certificate import make_confluence_certificate, make_nonconfluence_witness
from src.staged_verify import verify_confluence_certificate, verify_nonconfluence_witness

COUNTS: dict[str, int] = {}


def count(key):
    COUNTS[key] = COUNTS.get(key, 0) + 1


def chain_case(programs=1, facts=2, *, advance=False, rewrites=False, rank=None):
    table = [min(f + 1, facts - 1) if advance else f for f in range(facts)]
    return {
        "name": f"chain-{programs}-{facts}-{advance}-{rewrites}-{rank}",
        "lattice": {"kind": "chain", "size": facts}, "inputs": 1,
        "source_expression": ["var", 0], "initial_program": 0, "initial_fact": 0,
        "programs": [{"name": f"p{p}", "rank": (programs - p - 1) if rank is None
                      else (rank if p == 0 else 0), "expression": ["var", 0],
                      "analyses": [{"name": "a", "direction": "forward", "table": table}]}
                     for p in range(programs)],
        "rewrites": [{"name": f"r{p}", "source": p, "target": p + 1,
                      "guard": [True] * facts, "transfer": list(range(facts))}
                     for p in range(programs - 1)] if rewrites else [],
    }


def domains():
    cases = [(name, json.loads((ROOT / "staged_cases" / f"{name}.json").read_text(encoding="utf-8")))
             for name in ("S01", "S02", "S03", "S04", "S07", "S08", "S09", "S10", "S11")]
    cases.extend([
        ("64-fact-positive", chain_case(facts=64, advance=True)),
        ("32-program-positive", chain_case(programs=32, facts=1, rewrites=True)),
        ("rank-1024", chain_case(programs=2, facts=2, advance=True, rewrites=True, rank=1024)),
    ])
    repeated = chain_case(facts=2, advance=True)
    repeated["programs"][0]["analyses"] = [
        {"name": f"a{i}", "direction": ("forward", "prophecy", "history", "auxiliary")[i % 4],
         "table": [1, 1]} for i in range(16)]
    cases.append(("16-analyses-same-target", repeated))
    repeated = chain_case(programs=2, facts=1, rewrites=True)
    repeated["rewrites"] = [dict(repeated["rewrites"][0], name=f"r{i}") for i in range(64)]
    cases.append(("64-rewrites-same-target", repeated))
    explicit = chain_case(facts=5)
    explicit["lattice"] = {"kind": "explicit", "name": "M3-test",
                            "upper": [31, 18, 20, 24, 16], "bottom": 0, "top": 4}
    explicit["programs"][0]["analyses"][0]["table"] = [4] * 5
    cases.append(("explicit-M3", explicit))
    return cases


def probe(raw, pairs):
    heights = coheights(raw)
    span = max(heights) + 1
    return {"schema": "pvso-confluence-certificate-1", "instance": raw["name"],
            "remaining_heights": heights, "initial_state": -1, "edges": [],
            "states": [{"id": sid, "program": p, "fact": f,
                        "measure": raw["programs"][p]["rank"] * span + heights[f],
                        "outgoing": [], "parent_edge": None}
                       for sid, (p, f) in enumerate(pairs)]}


def admission_cases():
    raw = chain_case(programs=2, facts=2)
    instance = load_staged_instance(raw)
    alphabet = list(itertools.product(range(2), repeat=2))
    for length in range(1, 5):
        for word in itertools.product(alphabet, repeat=length):
            error = "duplicate state" if first_duplicate(word) is not None else "invalid initial-state id"
            yield f"word-{word}", instance, probe(raw, word), error

    unique = [(0, 0), (0, 1), (1, 0), (1, 1)]
    malformed = [False, True, 0.0, 1.0, None, [], {}, "0", -1, 2]
    for sid in (0, 1, 3):
        for field, message in (("program", "invalid state program"), ("fact", "invalid state fact")):
            for value in malformed:
                cert = probe(raw, unique)
                cert["states"][sid][field] = value
                yield f"coordinate-{sid}-{field}-{value!r}", instance, cert, message
    for sid in (1, 2, 3):
        for field, value in (("measure", -1), ("outgoing", None), ("parent_edge", [])):
            cert = probe(raw, unique)
            cert["states"][sid].update(program=0, fact=0)
            cert["states"][sid][field] = value
            yield f"duplicate-before-{sid}-{field}", instance, cert, "duplicate state"
    for field, value, error in (("id", -1, "noncanonical state id"),
                              ("program", [], "invalid state program"),
                              ("fact", {}, "invalid state fact"),
                              ("measure", -1, "state measure mismatch"),
                              ("outgoing", [False], "invalid outgoing list"),
                              ("parent_edge", False, "invalid parent edge")):
        cert = probe(raw, unique)
        cert["states"][0][field] = value
        cert["states"][1].update(program=0, fact=0)
        yield f"earlier-error-{field}", instance, cert, error
    for field, value, error in (("id", [], "noncanonical state id"),
                              ("program", {}, "invalid state program"),
                              ("fact", [], "invalid state fact")):
        cert = probe(raw, unique)
        cert["states"][1].update(program=0, fact=0)
        cert["states"][1][field] = value
        cert["states"][1]["measure"] = -1
        yield f"invalid-before-duplicate-{field}", instance, cert, error

    cap_raw = chain_case(programs=32, facts=64)
    cap_instance = load_staged_instance(cap_raw)
    pairs = list(itertools.product(range(32), range(64)))
    if first_duplicate(pairs) is not None:
        raise RuntimeError("literal product unexpectedly contains a duplicate")
    yield "cap-2048-unique", cap_instance, probe(cap_raw, pairs), "invalid initial-state id"
    for sid in (1, 1024, 2047):
        repeated = pairs.copy()
        repeated[sid] = repeated[0]
        if first_duplicate(repeated) != sid:
            raise RuntimeError("literal duplicate oracle disagrees with fixture")
        yield f"cap-duplicate-{sid}", cap_instance, probe(cap_raw, repeated), "duplicate state"
    cert = probe(cap_raw, pairs)
    cert["states"][-1]["fact"] = []
    yield "cap-malformed-last", cap_instance, cert, "invalid state fact"
    cert = probe(cap_raw, pairs + [pairs[0]])
    cert["states"][0]["program"] = []
    yield "cap-2049-before-row-errors", cap_instance, cert, "too many states"
    for field, value, error in (("states", [], "invalid state list"),
                              ("states", {}, "invalid state list"),
                              ("edges", None, "invalid edge list")):
        cert = probe(raw, unique)
        cert[field] = value
        yield f"invalid-container-{field}-{value}", instance, cert, error


def certificate_mutations(cert):
    for field in ("schema", "instance", "remaining_heights", "initial_state", "states", "edges",
                  "terminals", "closures", "peaks", "semantics", "claims"):
        damaged = copy.deepcopy(cert)
        del damaged[field]
        yield f"missing-{field}", damaged
    for sid, _ in enumerate(cert["states"]):
        fields = {"id": -1, "program": [], "fact": {}, "measure": -1,
                  "outgoing": [False], "parent_edge": False}
        for field, value in fields.items():
            damaged = copy.deepcopy(cert)
            damaged["states"][sid][field] = value
            yield f"state-{sid}-{field}", damaged
        if sid:
            damaged = copy.deepcopy(cert)
            damaged["states"][sid].update(program=cert["states"][0]["program"],
                                          fact=cert["states"][0]["fact"])
            yield f"state-{sid}-duplicate", damaged
    for eid, _ in enumerate(cert["edges"]):
        for field, value in (("id", -1), ("source", False), ("target", -1), ("kind", "bad"),
                             ("rule", False), ("name", "bad"), ("direction", "bad")):
            damaged = copy.deepcopy(cert)
            damaged["edges"][eid][field] = value
            yield f"edge-{eid}-{field}", damaged
    for sid, row in enumerate(cert["states"]):
        if row["outgoing"]:
            damaged = copy.deepcopy(cert)
            damaged["states"][sid]["outgoing"] *= 2
            yield f"duplicate-outgoing-{sid}", damaged
        if len(row["outgoing"]) > 1:
            damaged = copy.deepcopy(cert)
            damaged["states"][sid]["outgoing"].reverse()
            yield f"reordered-outgoing-{sid}", damaged
    for cid, _ in enumerate(cert["closures"]):
        for field, value in (("program", -1), ("fact", -1), ("final", -1), ("trace", [False])):
            damaged = copy.deepcopy(cert)
            damaged["closures"][cid][field] = value
            yield f"closure-{cid}-{field}", damaged
    for pid, _ in enumerate(cert["peaks"]):
        for field, value in (("state", -1), ("left_edge", -1), ("right_edge", -1), ("kind", "bad"),
                             ("join", False), ("left_path", [-1]), ("right_path", [False])):
            damaged = copy.deepcopy(cert)
            damaged["peaks"][pid][field] = value
            yield f"peak-{pid}-{field}", damaged
    for field in cert["semantics"]:
        damaged = copy.deepcopy(cert)
        del damaged["semantics"][field]
        yield f"semantics-{field}", damaged
    for field in cert["claims"]:
        damaged = copy.deepcopy(cert)
        damaged["claims"][field] = not damaged["claims"][field]
        yield f"claims-{field}", damaged


def witness_mutations(instance, witness):
    for field in ("schema", "instance", "left", "right", "left_terminal", "right_terminal"):
        damaged = copy.deepcopy(witness)
        del damaged[field]
        yield f"missing-{field}", damaged
    damaged = copy.deepcopy(witness)
    damaged["right"] = copy.deepcopy(damaged["left"])
    damaged["right_terminal"] = copy.deepcopy(damaged["left_terminal"])
    yield "identical-terminals", damaged
    for field in ("left", "right"):
        for event in ({"kind": "invalid", "rule": 0}, {"kind": "analysis", "rule": False},
                      {"kind": "analysis", "rule": -1}, {"kind": "rewrite", "rule": 999}):
            damaged = copy.deepcopy(witness)
            damaged[field] = [event]
            yield f"bad-event-{field}-{event}", damaged
        damaged = copy.deepcopy(witness)
        bound = 2 * (len(instance.programs) * instance.lattice.n + len(instance.rewrites) + 1)
        damaged[field] = [{}] * (bound + 1)
        yield f"overlong-{field}", damaged


class AdmissionRegression(unittest.TestCase):
    def test_literal_finite_domains_and_evidence(self):
        for name, raw in domains():
            with self.subTest(name=name):
                instance = load_staged_instance(raw)
                literal = literal_reference(raw)
                report = analyze_staged(instance, include_peak_paths=True)
                self.assertEqual({tuple(s) for s in report["reachable_states"]}, literal["reachable"])
                self.assertEqual(report["reachable_state_count"], len(literal["reachable"]))
                self.assertEqual(report["edge_count"], literal["edges"])
                self.assertEqual({tuple(s) for s in report["terminal_states"]}, literal["terminal"])
                self.assertEqual(report["global_confluence"], literal["confluent"])
                self.assertEqual(report["exact_local_peak_criterion"], literal["unjoinable"] == 0)
                self.assertEqual(report["unjoinable_local_peak_count"], literal["unjoinable"])
                self.assertEqual(len(report["peaks"]), literal["peaks"])
                cert = make_confluence_certificate(instance)
                witness = make_nonconfluence_witness(instance)
                self.assertEqual(cert is not None, literal["confluent"])
                self.assertEqual(witness is not None, not literal["confluent"])
                if cert is not None:
                    result = verify_confluence_certificate(instance, cert)
                    self.assertEqual(result, {"valid": True, "states": len(literal["reachable"]),
                                              "edges": literal["edges"], "peaks": literal["peaks"],
                                              "terminals": len(literal["terminal"]),
                                              "all_declared_rewrites_preserve_observation": literal["semantics"]["all_rewrites_preserve_observation"],
                                              "terminal_programs_source_equivalent": all(
                                                  literal["semantics"]["program_truth_tables"][p] == literal["semantics"]["source_truth_table"]
                                                  for p, _ in literal["terminal"])})
                    self.assertEqual(cert["semantics"], literal["semantics"])
                    self.assertEqual(cert["remaining_heights"], coheights(raw))
                    pairs = [(r["program"], r["fact"]) for r in cert["states"]]
                    self.assertIsNone(first_duplicate(pairs))
                    for sid, row in enumerate(cert["states"]):
                        actual = [(cert["edges"][i]["kind"], cert["edges"][i]["rule"], pairs[sid],
                                   pairs[cert["edges"][i]["target"]], cert["edges"][i]["name"],
                                   cert["edges"][i]["direction"]) for i in row["outgoing"]]
                        self.assertEqual(actual, literal["adjacency"][pairs[sid]])
                    self.assertEqual([(r["program"], r["fact"]) for r in cert["closures"]],
                                     list(itertools.product(range(len(instance.programs)), range(instance.lattice.n))))
                    for row in cert["closures"]:
                        self.assertEqual(row["final"], literal["closures"][(row["program"], row["fact"])])
                    count("positive_certificates")
                else:
                    self.assertTrue(verify_nonconfluence_witness(instance, witness)["valid"])
                    self.assertIn(tuple(witness["left_terminal"]), literal["terminal"])
                    self.assertIn(tuple(witness["right_terminal"]), literal["terminal"])
                    self.assertNotEqual(witness["left_terminal"], witness["right_terminal"])
                    count("negative_witnesses")
                count("literal_domains")

    def test_exhaustive_words_malformed_precedence_and_cap(self):
        for label, instance, cert, error in admission_cases():
            with self.subTest(label=label):
                with self.assertRaises(ValueError) as caught:
                    verify_confluence_certificate(instance, cert)
                self.assertEqual(str(caught.exception), error)
                count("admission_probes")

    def test_positive_certificate_mutations(self):
        raw = dict(domains())["S01"]
        instance = load_staged_instance(raw)
        cert = make_confluence_certificate(instance)
        self.assertIsNotNone(cert)
        for label, damaged in certificate_mutations(cert):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    verify_confluence_certificate(instance, damaged)
                count("positive_mutations")

    def test_negative_witness_mutations_and_trace_cap(self):
        for name, raw in domains():
            instance = load_staged_instance(raw)
            witness = make_nonconfluence_witness(instance)
            if witness is None:
                continue
            for label, damaged in witness_mutations(instance, witness):
                with self.subTest(name=name, label=label):
                    with self.assertRaises(ValueError):
                        verify_nonconfluence_witness(instance, damaged)
                    count("negative_mutations")

    def test_existing_equality_admission_and_call_isolation(self):
        raw = dict(domains())["S01"]
        instance = load_staged_instance(raw)
        cert = make_confluence_certificate(instance)
        self.assertIsNotNone(cert)
        altered = copy.deepcopy(cert)
        for rows in (altered["states"], altered["edges"]):
            for i, row in enumerate(rows):
                row["id"] = bool(i) if i < 2 else float(i)
        for row in altered["states"]:
            row["measure"] = float(row["measure"])
            row["extra-uninterpreted-field"] = []
        expected = verify_confluence_certificate(instance, cert)
        self.assertEqual(verify_confluence_certificate(instance, altered), expected)
        self.assertEqual(verify_confluence_certificate(instance, cert), expected)
        other = load_staged_instance(chain_case(facts=1))
        other_cert = make_confluence_certificate(other)
        self.assertTrue(verify_confluence_certificate(other, other_cert)["valid"])
        self.assertEqual(verify_confluence_certificate(instance, cert), expected)
        self.assertEqual(cert, make_confluence_certificate(instance))
        count("equality_and_isolation_groups")

    def test_verifier_remains_search_free(self):
        instance = load_staged_instance(dict(domains())["S01"])
        cert = make_confluence_certificate(instance)
        self.assertIsNotNone(cert)
        forbidden = AssertionError("verifier called a producer/search helper")
        with patch("src.staged_checker.explore", side_effect=forbidden), \
             patch("src.staged_checker.join_paths", side_effect=forbidden), \
             patch("src.staged_certificate.explore", side_effect=forbidden), \
             patch("src.staged_certificate.join_paths", side_effect=forbidden):
            self.assertTrue(verify_confluence_certificate(instance, cert)["valid"])
        count("search_free_groups")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionRegression))
    print(json.dumps({"tests": result.testsRun, "successful": result.wasSuccessful(), "finite_counts": COUNTS}, sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
