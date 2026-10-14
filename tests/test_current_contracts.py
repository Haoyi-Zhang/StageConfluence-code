"""Owned fault controls for replay types, scientific gates and recovery."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import collect
import reproduce
import staged_campaign
from src.staged_model import load_staged_instance
from src.staged_certificate import make_confluence_certificate
from src.staged_verify import verify_confluence_certificate

ROOT = Path(__file__).resolve().parents[1]


class CurrentContracts(unittest.TestCase):
    def test_changed_parseable_output_is_not_completed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root/'value.json'
            path.write_text('{"value":1}', encoding='utf-8')
            markers = root/'markers'
            reproduce.mark_complete(root, 'owned', [path], markers)
            path.write_text('{"value":2}', encoding='utf-8')
            self.assertFalse(reproduce.step_complete(root, 'owned', [path], markers))

    def test_current_input_change_invalidates_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root/'source'
            (source/'cases').mkdir(parents=True)
            input_path = source/'cases'/'owned.json'
            input_path.write_text('{"inputs":1}', encoding='utf-8')
            path = root/'out'/'value.json'
            path.parent.mkdir()
            path.write_text('{"value":1}', encoding='utf-8')
            with patch.object(reproduce, 'ROOT', source):
                reproduce.mark_complete(path.parent, 'owned', [path], root/'markers')
                input_path.write_text('{"inputs":2}', encoding='utf-8')
                self.assertFalse(reproduce.step_complete(path.parent, 'owned', [path], root/'markers'))

    def test_nonsentinel_produced_output_is_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sentinel, detail = root/'summary.json', root/'proof.json'
            code = "import pathlib,sys; [pathlib.Path(p).write_text('{}') for p in sys.argv[1:]]"
            records = []
            reproduce.run(root, 'owned', [sys.executable,'-B','-c',code,str(sentinel),str(detail)],
                          [sentinel], root/'markers', records)
            self.assertTrue(reproduce.step_complete(root, 'owned', [sentinel], root/'markers'))
            detail.unlink()
            self.assertFalse(reproduce.step_complete(root, 'owned', [sentinel], root/'markers'))

    def test_changed_command_is_executed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root/'value.json'
            command = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
            records = []
            for value in ('1', '2'):
                reproduce.run(root, 'owned', [sys.executable, '-B', '-c', command, str(path), value],
                              [path], root/'markers', records)
            self.assertFalse(records[-1]['skipped_completed'])
            self.assertEqual(json.loads(path.read_text()), 2)

    def test_semantic_formula_gate_survives_optimization(self):
        # Corrupt only the syntax-safe guard, not the actual product-state oracle.
        original = collect.synthesize_guards
        def wrong_guard(*args):
            mu, reachable, safe, persistent, upward = original(*args)
            return mu, reachable, set(), persistent, upward
        with tempfile.TemporaryDirectory() as d, patch.object(collect, 'synthesize_guards', wrong_guard):
            with self.assertRaises((ValueError, AssertionError, RuntimeError)):
                collect.semantic(Path(d))

    def test_nonexistent_campaign_family_cannot_succeed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                staged_campaign.run_campaign(Path(d), {'misspelled-owned-family'})

    def test_certificate_does_not_coerce_numeric_types(self):
        instance = load_staged_instance(json.loads((ROOT/'staged_cases/S01.json').read_text()))
        certificate = make_confluence_certificate(instance)
        self.assertIsNotNone(certificate)
        for region, field, value in [('states','id',False), ('states','measure',8.0),
                                     ('closures','program',False), ('closures','final',3.0),
                                     ('peaks','state',False)]:
            with self.subTest(region=region, field=field):
                altered = copy.deepcopy(certificate)
                altered[region][0][field] = value
                with self.assertRaises(ValueError):
                    verify_confluence_certificate(instance, altered)


if __name__ == '__main__':
    unittest.main()
