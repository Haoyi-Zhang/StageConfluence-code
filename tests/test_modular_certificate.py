"""Small literal oracle, global-obligation negatives and real CLI round trips."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from state_admission_reference import literal_reference
from src.staged_model import load_staged_instance
from src.staged_certificate import make_confluence_certificate
from src.staged_verify import verify_confluence_certificate
from src.modular_certificate import (make_modular_certificate, verify_modular_certificate,
                                     replay_closures, obligations, saturated_instance)

ROOT = Path(__file__).resolve().parents[1]
CASES = ('S01','S02','S03','S04','S07','S08','S09','S10','S11')


def raw(name):
    return json.loads((ROOT/'staged_cases'/f'{name}.json').read_text(encoding='utf-8'))


class ModularCertificate(unittest.TestCase):
    def test_named_domains_match_literal_oracle_and_exact_baseline(self):
        accepted = []
        for name in CASES:
            data = raw(name)
            instance = load_staged_instance(data)
            oracle = literal_reference(data)  # Floyd closure / least-fixed-element selection.
            cert = make_modular_certificate(instance)
            if cert is None:
                continue
            accepted.append(name)
            self.assertTrue(oracle['confluent'])
            result = verify_modular_certificate(instance, cert)
            self.assertEqual(set(map(tuple, [result['terminal_state']])), oracle['terminal'])
            ordinary = verify_confluence_certificate(instance, make_confluence_certificate(instance))
            for field in ('all_declared_rewrites_preserve_observation','terminal_programs_source_equivalent'):
                self.assertEqual(result[field], ordinary[field])
            closed = replay_closures(instance, cert['closures'])
            self.assertEqual(closed, oracle['closures'])
            for row in cert['graph']['states']:
                self.assertEqual(closed[row['program'], row['fact']], row['fact'])
        self.assertEqual(accepted, ['S01','S07','S09','S11'])

    def test_s08_remains_exact_positive_not_modular_negative(self):
        instance = load_staged_instance(raw('S08'))
        self.assertIsNone(make_modular_certificate(instance))
        self.assertTrue(verify_confluence_certificate(instance, make_confluence_certificate(instance))['valid'])

    def test_missing_premises_cannot_pass_via_saturated_graph(self):
        for name, reason in [('S03','CC'), ('S04','GP'), ('S08','GP'), ('S10','CC')]:
            instance = load_staged_instance(raw(name))
            # Borrow only the original producer's closure traces; do not fake a
            # full confluence certificate for these generally negative cases.
            from src.staged_checker import analysis_closure_trace
            rows = []
            for p in range(len(instance.programs)):
                for f in range(instance.lattice.n):
                    endpoint, trace = analysis_closure_trace(instance, p, f)
                    rows.append(dict(program=p, fact=f, final=endpoint, trace=list(trace)))
            with self.assertRaisesRegex(ValueError, reason):
                verify_modular_certificate(instance, dict(schema='pvso-modular-certificate-1',
                    instance=instance.name, closures=rows, graph={}))

    def test_unreachable_obligation_is_not_silently_dropped(self):
        data = raw('S01')
        dead = copy.deepcopy(data['programs'][0])
        dead['name'] = 'owned-dead'
        dead['rank'] = 3
        data['programs'].append(dead)
        data['rewrites'].append(dict(name='dead-ephemeral', source='owned-dead', target='p3',
            guard=[True,False,False,False], transfer=[0,1,2,3]))
        # Use the actual names in the input, which need not be p3.
        data['rewrites'][-1]['target'] = data['programs'][3]['name']
        instance = load_staged_instance(data)
        self.assertTrue(literal_reference(data)['confluent'])
        self.assertIsNone(make_modular_certificate(instance))

    def test_noncommuting_analysis_and_nonbottom_root(self):
        data = raw('S01')
        data['programs'][0]['analyses'][1]['table'] = [0,3,2,3]
        data['initial_fact'] = 1
        instance = load_staged_instance(data)
        cert = make_modular_certificate(instance)
        self.assertIsNotNone(cert)
        self.assertEqual({tuple(verify_modular_certificate(instance, cert)['terminal_state'])},
                         literal_reference(data)['terminal'])

    def test_selected_coverage_trace_path_and_semantic_corruptions_reject(self):
        instance = load_staged_instance(raw('S01'))
        certificate = make_modular_certificate(instance)
        self.assertIsNotNone(certificate)
        changes = [lambda c: c['closures'].pop(),
                   lambda c: c['closures'][0].update(trace=[]),
                   lambda c: c['closures'][0].update(final=True),
                   lambda c: c['graph']['states'][0]['outgoing'].pop(),
                   lambda c: c['graph']['states'][1].update(parent_edge=None),
                   lambda c: c['graph']['peaks'][0].update(left_path=[]),
                   lambda c: c['graph']['semantics'].update(all_rewrites_preserve_observation=False),
                   lambda c: c['graph']['claims'].update(globally_confluent=1)]
        for i, change in enumerate(changes):
            altered = copy.deepcopy(certificate)
            change(altered)
            with self.subTest(corruption=i), self.assertRaises(ValueError):
                verify_modular_certificate(instance, altered)

    def test_replay_does_not_search(self):
        instance = load_staged_instance(raw('S01'))
        certificate = make_modular_certificate(instance)
        forbidden = RuntimeError('replay called a search helper')
        with patch('src.staged_checker.explore', side_effect=forbidden), \
             patch('src.staged_checker.analysis_closure_trace', side_effect=forbidden), \
             patch('src.staged_checker.join_paths', side_effect=forbidden), \
             patch('src.staged_certificate.make_confluence_certificate', side_effect=forbidden):
            self.assertTrue(verify_modular_certificate(instance, certificate)['valid'])

    def test_actual_cli_positive_and_sufficient_only_rejection(self):
        flags = ['-B'] + (['-O'] if sys.flags.optimize else [])
        with tempfile.TemporaryDirectory() as d:
            proof = Path(d)/'modular.json'
            for command in (['certify-modular','staged_cases/S01.json','--out',str(proof)],
                            ['verify-modular','staged_cases/S01.json',str(proof)]):
                result = subprocess.run([sys.executable,*flags,'staged_check.py',*command],
                    cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable,*flags,'staged_check.py','certify-modular',
                'staged_cases/S08.json','--out',str(Path(d)/'absent.json')],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(d)/'absent.json').exists())


if __name__ == '__main__':
    unittest.main()
