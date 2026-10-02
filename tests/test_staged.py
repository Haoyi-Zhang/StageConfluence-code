"""Tests for code-changing staged confluence, certificates, and boundaries."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from src.staged_model import load_staged_instance
from src.staged_checker import (
    analysis_closure,
    analyze_staged,
    explore,
    measure,
    remaining_heights,
    successors,
)
from src.staged_certificate import (
    make_confluence_certificate,
    make_nonconfluence_witness,
    verify_confluence_certificate,
    verify_nonconfluence_witness,
)
from independent_audit import independent_classify
from staged_campaign import classify as primary_classify

ROOT = Path(__file__).resolve().parents[1]


def raw(name: str, invalid: bool = False):
    base = ROOT / "staged_cases"
    if invalid:
        base = base / "invalid"
    return json.loads((base / f"{name}.json").read_text())


def case(name: str):
    return load_staged_instance(raw(name))


class StagedStatements(unittest.TestCase):
    def test_separate_classifier_agrees_on_named_boundary_cases(self):
        for name in ("S01", "S02", "S03", "S04", "S07", "S08", "S09", "S10", "S11"):
            instance = case(name)
            self.assertEqual(primary_classify(instance), independent_classify(instance), name)

    def test_confluent_bidirectional_diamond(self):
        report = analyze_staged(case("S01"))
        self.assertTrue(report["termination_measure_valid"])
        self.assertTrue(report["exact_local_peak_criterion"])
        self.assertTrue(report["global_confluence"])
        self.assertTrue(report["newman_equivalence_holds"])
        self.assertTrue(report["modular_saturation_criterion"])
        self.assertTrue(report["schedule_independent_source_equivalent_program"])
        self.assertEqual(report["terminal_states"], [[3, 3]])
        self.assertEqual(report["local_peak_counts"], {
            "analysis/analysis": 1,
            "analysis/rewrite": 2,
            "rewrite/rewrite": 1,
        })

    def test_unjoined_rewrite_peak(self):
        report = analyze_staged(case("S02"))
        self.assertTrue(report["guard_persistence"])
        self.assertTrue(report["closure_commutation"])
        self.assertFalse(report["saturated_rewrite_peaks_join"])
        self.assertFalse(report["exact_local_peak_criterion"])
        self.assertFalse(report["unique_terminal_program"])

    def test_closure_commutation_is_independent_obligation(self):
        report = analyze_staged(case("S03"))
        self.assertTrue(report["guard_persistence"])
        self.assertFalse(report["closure_commutation"])
        self.assertTrue(report["saturated_rewrite_peaks_join"])
        self.assertFalse(report["global_confluence"])

    def test_guard_persistence_is_independent_obligation(self):
        report = analyze_staged(case("S04"))
        self.assertFalse(report["guard_persistence"])
        self.assertTrue(report["closure_commutation"])
        self.assertTrue(report["saturated_rewrite_peaks_join"])
        self.assertFalse(report["global_confluence"])

    def test_semantics_is_separate_from_confluence(self):
        report = analyze_staged(case("S07"))
        self.assertTrue(report["global_confluence"])
        self.assertTrue(report["modular_saturation_criterion"])
        self.assertFalse(report["semantic_preservation"]["all_rewrites_preserve_observation"])
        self.assertFalse(report["schedule_independent_source_equivalent_program"])

    def test_modular_criterion_is_not_necessary(self):
        report = analyze_staged(case("S08"))
        self.assertTrue(report["global_confluence"])
        self.assertFalse(report["guard_persistence"])
        self.assertFalse(report["modular_saturation_criterion"])
        self.assertTrue(report["schedule_independent_source_equivalent_program"])

    def test_state_confluence_stronger_than_program_confluence(self):
        report = analyze_staged(case("S10"))
        self.assertFalse(report["unique_terminal_state"])
        self.assertTrue(report["unique_terminal_program"])
        self.assertFalse(report["global_confluence"])
        self.assertTrue(report["schedule_independent_source_equivalent_program"])

    def test_rooted_semantics_ignores_unreachable_bad_rule(self):
        report = analyze_staged(case("S11"))
        self.assertTrue(report["global_confluence"])
        self.assertFalse(report["semantic_preservation"]["all_rewrites_preserve_observation"])
        self.assertTrue(report["semantic_preservation"]["reachable_rewrites_preserve_observation"])
        self.assertTrue(report["semantic_preservation"]["unique_terminal_program_source_equivalent"])
        self.assertTrue(report["schedule_independent_source_equivalent_program"])

    def test_rank_measure_strictly_decreases(self):
        for name in ("S01", "S02", "S03", "S04", "S07", "S08", "S09", "S10", "S11"):
            instance = case(name)
            rem = remaining_heights(instance)
            graph = explore(instance)
            for state in graph.states:
                for edge in graph.adjacency[state]:
                    self.assertLess(measure(instance, edge.target, rem), measure(instance, state, rem))

    def test_analysis_closure_is_fixed(self):
        for name in ("S01", "S09"):
            instance = case(name)
            for p in range(len(instance.programs)):
                for fact in range(instance.lattice.n):
                    closed = analysis_closure(instance, p, fact)
                    self.assertFalse(any(e.kind == "analysis" for e in successors(instance, (p, closed))))

    def test_invalid_noninflationary_transfer(self):
        with self.assertRaisesRegex(ValueError, "noninflationary"):
            load_staged_instance(raw("I01", invalid=True))

    def test_invalid_rank(self):
        with self.assertRaisesRegex(ValueError, "rank does not strictly decrease"):
            load_staged_instance(raw("I02", invalid=True))

    def test_invalid_analysis(self):
        with self.assertRaisesRegex(ValueError, "noninflationary"):
            load_staged_instance(raw("I03", invalid=True))


class StagedCertificates(unittest.TestCase):
    def setUp(self):
        self.instance = case("S01")
        cert = make_confluence_certificate(self.instance)
        assert cert is not None
        self.cert = cert

    def test_positive_certificates_replay(self):
        for name in ("S01", "S07", "S08", "S09", "S11"):
            instance = case(name)
            cert = make_confluence_certificate(instance)
            self.assertIsNotNone(cert)
            result = verify_confluence_certificate(instance, cert)
            self.assertTrue(result["valid"])

    def test_negative_instances_do_not_get_positive_certificates(self):
        for name in ("S02", "S03", "S04", "S10"):
            self.assertIsNone(make_confluence_certificate(case(name)))

    def test_nonconfluence_witnesses_replay(self):
        for name in ("S02", "S03", "S04", "S10"):
            instance = case(name)
            witness = make_nonconfluence_witness(instance)
            self.assertIsNotNone(witness)
            self.assertTrue(verify_nonconfluence_witness(instance, witness)["valid"])

    def test_confluent_instance_has_no_terminal_fork_witness(self):
        self.assertIsNone(make_nonconfluence_witness(case("S01")))

    def mutate_reject(self, change, pattern=None):
        cert = copy.deepcopy(self.cert)
        change(cert)
        context = self.assertRaisesRegex(ValueError, pattern) if pattern else self.assertRaises(ValueError)
        with context:
            verify_confluence_certificate(self.instance, cert)

    def test_mutate_remaining_height(self):
        self.mutate_reject(lambda c: c["remaining_heights"].__setitem__(0, 99), "height")

    def test_mutate_measure(self):
        self.mutate_reject(lambda c: c["states"][0].__setitem__("measure", 99), "measure")

    def test_mutate_edge_target(self):
        self.mutate_reject(lambda c: c["edges"][0].__setitem__("target", 0), "target")

    def test_mutate_edge_rule(self):
        self.mutate_reject(lambda c: c["edges"][0].__setitem__("rule", 99), "enabled")

    def test_mutate_outgoing_coverage(self):
        self.mutate_reject(lambda c: c["states"][0]["outgoing"].pop(), "transition set")

    def test_mutate_parent(self):
        self.mutate_reject(lambda c: c["states"][1].__setitem__("parent_edge", None), "parent")

    def test_mutate_closure_trace(self):
        def change(c):
            row = next(r for r in c["closures"] if r["program"] == 0 and r["fact"] == 0)
            row["trace"] = []
        self.mutate_reject(change, "fixed")

    def test_mutate_peak_join(self):
        self.mutate_reject(lambda c: c["peaks"][0].__setitem__("join", 0), "wrong state")

    def test_mutate_peak_path(self):
        def change(c):
            c["peaks"][0]["left_path"] = [0]
        self.mutate_reject(change, "disconnected|wrong state")

    def test_mutate_semantics(self):
        self.mutate_reject(lambda c: c["semantics"]["program_truth_tables"][0].__setitem__(0, 1), "semantic")

    def test_mutate_claim(self):
        self.mutate_reject(lambda c: c["claims"].__setitem__("globally_confluent", False), "claim")

    def test_mutate_instance(self):
        self.mutate_reject(lambda c: c.__setitem__("instance", "other"), "name")

    def test_mutate_witness_terminal(self):
        instance = case("S03")
        witness = make_nonconfluence_witness(instance)
        assert witness is not None
        witness["left_terminal"] = [0, 0]
        with self.assertRaisesRegex(ValueError, "terminal mismatch"):
            verify_nonconfluence_witness(instance, witness)

    def test_mutate_witness_event(self):
        instance = case("S03")
        witness = make_nonconfluence_witness(instance)
        assert witness is not None
        witness["right"][0]["rule"] = 99
        with self.assertRaisesRegex(ValueError, "enabled"):
            verify_nonconfluence_witness(instance, witness)


if __name__ == "__main__":
    unittest.main()
