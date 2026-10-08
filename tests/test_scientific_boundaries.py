"""Narrow regressions for the scientific contracts used in the manuscript."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import reproduce
import staged_campaign
from src.model import load_instance
from src.checker import factor_terminals, verify_witness
from src.staged_model import load_staged_instance
from src.staged_checker import analysis_closure, analyze_staged
from src.staged_certificate import make_confluence_certificate
from src.staged_verify import verify_confluence_certificate

ROOT = Path(__file__).resolve().parents[1]


class ScientificBoundaries(unittest.TestCase):
    def test_temporarily_enabled_emission_can_be_postponed(self):
        raw = json.loads((ROOT / "cases/C01.json").read_text(encoding="utf-8"))
        raw["guard"] = [True, False]
        instance = load_instance(raw)
        self.assertIn((1, None), factor_terminals(instance))
        witness = {"case": instance.name, "kind": "incomplete",
                   "runs": [[{"op": "apply", "map": 0}]]}
        self.assertTrue(verify_witness(instance, witness)["valid"])

    def test_noncommuting_analyses_share_closure_in_both_orders(self):
        raw = json.loads((ROOT / "staged_cases/S01.json").read_text(encoding="utf-8"))
        first, second = [1, 1, 3, 3], [0, 3, 2, 3]
        self.assertNotEqual(second[first[0]], first[second[0]])
        raw["rewrites"] = []
        raw["programs"] = [raw["programs"][0]]
        for rules in ((first, second), (second, first)):
            raw["programs"][0]["analyses"] = [
                {"name": f"a{i}", "direction": "auxiliary", "table": table}
                for i, table in enumerate(rules)
            ]
            instance = load_staged_instance(raw)
            for fact in range(4):
                self.assertEqual(analysis_closure(instance, 0, fact), 3)
            self.assertTrue(analyze_staged(instance)["global_confluence"])

    def test_rule_preservation_does_not_relate_a_different_reference_source(self):
        raw = json.loads((ROOT / "staged_cases/S07.json").read_text(encoding="utf-8"))
        raw["source_expression"] = ["not", ["var", 0]]
        raw["rewrites"] = []
        raw["programs"] = [raw["programs"][0]]
        instance = load_staged_instance(raw)
        report = analyze_staged(instance)
        self.assertTrue(report["semantic_preservation"]["reachable_rewrites_preserve_observation"])
        self.assertTrue(report["global_confluence"])
        self.assertFalse(report["schedule_independent_source_equivalent_program"])
        verified=verify_confluence_certificate(instance,make_confluence_certificate(instance))
        self.assertTrue(verified["all_declared_rewrites_preserve_observation"])
        self.assertFalse(verified["terminal_programs_source_equivalent"])

    def test_global_program_audit_is_not_a_terminal_audit(self):
        raw = json.loads((ROOT / "staged_cases/S11.json").read_text(encoding="utf-8"))
        instance = load_staged_instance(raw)
        report = analyze_staged(instance)
        self.assertFalse(report["semantic_preservation"]["all_programs_source_equivalent"])
        self.assertTrue(report["semantic_preservation"]["unique_terminal_program_source_equivalent"])
        verified=verify_confluence_certificate(instance,make_confluence_certificate(instance))
        self.assertFalse(verified["all_declared_rewrites_preserve_observation"])
        self.assertTrue(verified["terminal_programs_source_equivalent"])

    def test_certificate_metadata_and_record_order_are_required(self):
        raw = json.loads((ROOT / "staged_cases/S01.json").read_text(encoding="utf-8"))
        instance = load_staged_instance(raw)
        certificate = make_confluence_certificate(instance)
        self.assertIsNotNone(certificate)
        for field in ("name", "direction"):
            altered = copy.deepcopy(certificate)
            altered["edges"][0].pop(field)
            with self.assertRaises(ValueError):
                verify_confluence_certificate(instance, altered)
        altered = copy.deepcopy(certificate)
        altered["closures"][0], altered["closures"][1] = altered["closures"][1], altered["closures"][0]
        with self.assertRaisesRegex(ValueError, "noncanonical closure"):
            verify_confluence_certificate(instance, altered)

    def test_full_driver_requires_posix_limits_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-created"
            with patch.object(reproduce, "resource", None), patch("sys.argv", ["reproduce.py", str(output)]):
                with self.assertRaisesRegex(RuntimeError, "requires POSIX"):
                    reproduce.main()
            self.assertFalse(output.exists())

    def test_primary_campaign_fails_but_keeps_raw_theorem_disagreement(self):
        for gate in ("newman_mismatches", "modular_false_positives"):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as directory:
                row = {"family": "synthetic-gate", "declared_instances": 1,
                       **staged_campaign.empty_counts(), "cpu_seconds": 0, "wall_seconds": 0}
                row["instances"], row[gate] = 1, 1
                with patch.object(staged_campaign, "families", return_value=[("synthetic-gate", lambda: (), 1)]), \
                     patch.object(staged_campaign, "run_family", return_value=(row, {})):
                    with self.assertRaisesRegex(RuntimeError, "disagreement|false positive"):
                        staged_campaign.run_campaign(Path(directory))
                saved = json.loads((Path(directory) / "staged-enumeration-summary.json").read_text())
                self.assertEqual(saved["totals"][gate], 1)


if __name__ == "__main__":
    unittest.main()
