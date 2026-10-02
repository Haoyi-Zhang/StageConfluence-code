"""Positive, semantic, boundary, and benign mutation tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from src.model import (chain, powerset, named_lattice, load_instance, expression,
                       monotone_inflationary_maps, validate_maps, truth_table)
from src.checker import (analyze, make_witness, verify_witness, terminal_oracle,
                         synthesize_guards, round_robin)
ROOT = Path(__file__).resolve().parents[1]

def raw(n):
    return json.loads((ROOT/'cases'/f'C{n:02d}.json').read_text())

def case(n):
    return load_instance(raw(n))

class Lattices(unittest.TestCase):
    def test_named_lattices(self):
        for s in ('C1','C2','C3','C4','C5','B2','B3','M3','N5'):
            named_lattice(s).validate()
    def test_exact_map_counts(self):
        for s,c in [('C1',1),('C2',2),('C3',5),('C4',14),('C5',42),('B2',9),('M3',15),('N5',21)]:
            self.assertEqual(len(monotone_inflationary_maps(named_lattice(s))),c)
    def test_global_not_local(self):
        r=raw(8)
        with self.assertRaisesRegex(ValueError,'monotone'):
            load_instance(r)
        fs=tuple(tuple(m['table']) for m in r['maps'])
        ts,_,_=terminal_oracle(0,fs,(True,)*4,('x',)*4)
        self.assertEqual(ts,{(1,'x'),(2,'x')})
    def test_noninflationary_rejected(self):
        with self.assertRaisesRegex(ValueError,'inflationary'):
            validate_maps(chain(2),((0,0),))
    def test_boolean_map_index_rejected(self):
        r=raw(1);r['maps'][0]['table'][0]=True
        with self.assertRaises(ValueError):load_instance(r)
    def test_invalid_order(self):
        r=raw(1);r['lattice']={'kind':'explicit','upper':[3,3],'bottom':0,'top':1}
        with self.assertRaisesRegex(ValueError,'antisymmetric'):load_instance(r)
    def test_non_lattice_poset(self):
        # Bottom, a,b, u,v, top; a,b have two incomparable minimal upper bounds.
        r=raw(1);r['lattice']={'kind':'explicit','upper':[63,58,60,40,48,32],'bottom':0,'top':5}
        with self.assertRaisesRegex(ValueError,'least upper'):load_instance(r)

class Statements(unittest.TestCase):
    def test_early_emission(self):
        a=analyze(case(1))
        self.assertEqual(a['least_fixed_point'],1)
        self.assertEqual(a['terminal_count'],2)
        self.assertTrue(a['completed_runs_preserve_source'])
        self.assertFalse(a['unique_syntactic_output_for_all_runs'])
    def test_semantic_guard_does_not_promise_syntax(self):
        a=analyze(case(1))
        self.assertEqual(a['maximal_safe_guard_reachable'],[1])
        self.assertEqual(a['maximal_final_semantics_guard_reachable'],[0,1])
    def test_guards_cannot_repair_wrong_final_code(self):
        a=analyze(case(4))
        self.assertFalse(a['complete_source_preserving_guard_exists'])
        self.assertEqual(a['maximal_final_semantics_guard_reachable'],[0,1])
    def test_final_guard(self):
        a=analyze(case(2));self.assertTrue(a['unique_syntactic_output_for_all_runs'])
        self.assertTrue(a['completed_runs_preserve_source'])
    def test_stable_early_guard(self):
        a=analyze(case(3));self.assertTrue(a['unique_syntactic_output_for_all_runs'])
    def test_unique_wrong(self):
        a=analyze(case(4));self.assertTrue(a['unique_syntactic_output_for_all_runs'])
        self.assertFalse(a['completed_runs_preserve_source'])
    def test_incomplete_guard(self):
        a=analyze(case(5));self.assertFalse(a['all_maximal_progress_runs_complete'])
        self.assertEqual(a['terminal_count'],2)
    def test_no_vacuous_success(self):
        a=analyze(case(6));self.assertIsNone(a['completed_runs_preserve_source'])
        self.assertFalse(a['unique_syntactic_output_for_all_runs'])
    def test_transition_guard_strictly_larger(self):
        a=analyze(case(7))
        self.assertEqual(a['reachable_fact_states'],[0,1,2,3,7])
        self.assertEqual(a['maximal_persistent_safe_guard_reachable'],[1,7])
        self.assertEqual(a['order_upward_safe_guard_reachable'],[7])
    def test_singleton_minimality(self):
        self.assertTrue(analyze(case(9))['unique_syntactic_output_for_all_runs'])
    def test_unreachable_bad_state_ignored(self):
        a=analyze(case(10));self.assertEqual(a['reachable_fact_states'],[0,2])
        self.assertTrue(a['unique_syntactic_output_for_all_runs'])
    def test_final_baseline(self):
        for n in (1,2,3,4,5,6,7,9,10):
            i=case(n); a=analyze(i)
            final,_=round_robin(i.lattice.bottom,i.maps,i.lattice.n)
            self.assertEqual(final,a['least_fixed_point'])
    def test_synthetic_feedback_cycle(self):
        x=('var',0);es=(('and',x,('const',0)),('const',0))
        def reads(e):return e[0]=='var' or any(reads(t) for t in e[1:] if isinstance(t,tuple))
        self.assertEqual(tuple(int(reads(e)) for e in es),(1,0))
        self.assertEqual(truth_table(es[0],1),truth_table(es[1],1))
    def test_monotone_without_inflation_cycle(self):
        lat=powerset(2);f=(0,2,1,3)
        self.assertTrue(all(not lat.le(x,y) or lat.le(f[x],f[y]) for x in range(4) for y in range(4)))
        self.assertEqual(f[f[1]],1);self.assertNotEqual(f[1],1)

class Witnesses(unittest.TestCase):
    def test_generated_witnesses_replay(self):
        for n in (1,4,5,6,7):
            i=case(n);self.assertTrue(verify_witness(i,make_witness(i))['valid'])
    def test_no_spurious_witness(self):
        for n in (2,3,9,10):self.assertIsNone(make_witness(case(n)))
    def test_mutate_rule(self):
        i=case(1);w=make_witness(i);w['runs'][0][-1]['map']=5
        with self.assertRaises(ValueError):verify_witness(i,w)
    def test_mutate_guard(self):
        w=make_witness(case(1));r=raw(2);r['name']='C01'
        with self.assertRaisesRegex(ValueError,'emission'):verify_witness(load_instance(r),w)
    def test_mutate_duplicate_emit(self):
        i=case(1);w=make_witness(i);w['runs'][0]=[{'op':'emit'},{'op':'emit'}]
        with self.assertRaises(ValueError):verify_witness(i,w)
    def test_mutate_nonterminal(self):
        i=case(1);w=make_witness(i);w['runs'][0]=[{'op':'emit'}]
        with self.assertRaisesRegex(ValueError,'terminal'):verify_witness(i,w)
    def test_mutate_kind(self):
        i=case(1);w=make_witness(i);w['kind']='wrong_semantics';w['runs']=w['runs'][:1]
        with self.assertRaisesRegex(ValueError,'equivalent'):verify_witness(i,w)
    def test_mutate_same_run(self):
        i=case(1);w=make_witness(i);w['runs'][1]=copy.deepcopy(w['runs'][0])
        with self.assertRaisesRegex(ValueError,'distinct'):verify_witness(i,w)
    def test_mutate_nonprogress(self):
        i=case(1);w=make_witness(i);w['runs'][0]=[{'op':'apply','map':0},{'op':'apply','map':0}]
        with self.assertRaisesRegex(ValueError,'nonprogress'):verify_witness(i,w)
    def test_mutate_case(self):
        i=case(1);w=make_witness(i);w['case']='other'
        with self.assertRaisesRegex(ValueError,'mismatch'):verify_witness(i,w)
    def test_mutate_claim_incomplete(self):
        i=case(1);w=make_witness(i);w['kind']='incomplete';w['runs']=w['runs'][:1]
        with self.assertRaisesRegex(ValueError,'has an artifact'):verify_witness(i,w)

class ResidualLanguage(unittest.TestCase):
    def test_truth_tables(self):
        self.assertEqual(truth_table(expression(['xor',['var',0],['var',1]],2),2),(0,1,1,0))
    def test_bad_arity(self):
        with self.assertRaises(ValueError):expression(['not'],1)
    def test_unknown_construct(self):
        with self.assertRaises(ValueError):expression(['call','anything'],1)
    def test_depth_bound(self):
        e=['const',0]
        for _ in range(40):e=['not',e]
        with self.assertRaisesRegex(ValueError,'bound'):expression(e,0)
    def test_input_bound(self):
        r=raw(1);r['inputs']=9
        with self.assertRaises(ValueError):load_instance(r)

if __name__=='__main__':unittest.main()
