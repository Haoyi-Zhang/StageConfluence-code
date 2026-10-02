#!/usr/bin/env python3
"""Generate exact consumed map tables, concrete results, and finite summaries."""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path
import resource
import time
import unittest
from collections import defaultdict
from src.model import (named_lattice, monotone_inflationary_maps, load_instance,
                       syntax_key, truth_table)
from src.checker import analyze, make_witness, verify_witness, terminal_oracle, synthesize_guards

ROOT=Path(__file__).resolve().parent
LATTICES=('C1','C2','C3','C4','C5','B2','M3','N5')

def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def write_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def maps(out):
    for name in LATTICES:
        lat=named_lattice(name);lat.validate()
        write_json(out/'inputs'/f'{name}.json',dict(lattice=lat.as_dict(),maps=monotone_inflationary_maps(lat)))

def examples(out):
    for path in sorted((ROOT/'cases').glob('C*.json')):
        raw=json.loads(path.read_text())
        try:
            inst=load_instance(raw)
        except ValueError as e:
            if path.stem!='C08':raise
            write_json(out/'cases'/f'{path.stem}-analysis.json',dict(name=path.stem,expected_rejection=True,error=str(e)))
            continue
        write_json(out/'cases'/f'{path.stem}-analysis.json',analyze(inst))
        cert=make_witness(inst)
        if cert is not None:
            write_json(out/'cases'/f'{path.stem}-witness.json',cert)
            write_json(out/'cases'/f'{path.stem}-replay.json',verify_witness(inst,cert))

def semantic(out):
    leaves=(('var',0),('var',1),('const',0),('const',1))
    exprs=leaves+tuple(('not',e) for e in leaves)+tuple((op,a,b) for op in ('and','or','xor') for a in leaves for b in leaves)
    assert len(exprs)==len(set(exprs))==56
    tables=[truth_table(e,2) for e in exprs]
    keys=[syntax_key(e) for e in exprs]
    rows=[];lat=named_lattice('C2');fs=((1,1),)
    for i,a in enumerate(exprs):
        for j,b in enumerate(exprs):
            e=(keys[i],keys[j]);sem=(tables[i],tables[j])
            ts,_,_=terminal_oracle(0,fs,(True,True),e)
            _,_,sg,_,_=synthesize_guards(lat,fs,e)
            _,_,qg,_,_=synthesize_guards(lat,fs,sem)
            st,_,_=terminal_oracle(0,fs,tuple(x in sg for x in range(2)),e)
            qt,_,_=terminal_oracle(0,fs,tuple(x in qg for x in range(2)),sem)
            final,_,_=terminal_oracle(0,fs,(False,True),e)
            assert st==final=={(1,e[1])}
            assert qt=={(1,sem[1])}
            rows.append(dict(early=i,final=j,eager_terminal_count=len(ts),same_syntax=i==j,
                             same_truth_table=tables[i]==tables[j],syntax_guard_early=0 in sg,
                             semantic_guard_early=0 in qg,final_only_terminal_count=len(final)))
    write_csv(out/'semantic-pairs.csv',rows)
    write_json(out/'inputs'/'expressions.json',dict(inputs=2,expressions=exprs,truth_tables=tables))
    summary=dict(expressions=len(exprs),ordered_pairs=len(rows),runtime_inputs=4,
                 unique_eager_syntax=sum(r['same_syntax'] for r in rows),
                 semantically_preserving_eager_pairs=sum(r['same_truth_table'] for r in rows),
                 distinct_syntax_equivalent_pairs=sum(r['same_truth_table'] and not r['same_syntax'] for r in rows),
                 semantically_wrong_eager_pairs=sum(not r['same_truth_table'] for r in rows),
                 final_only_unique_and_preserving_pairs=len(rows),syntax_guard_unique_and_preserving_pairs=len(rows),
                 semantic_guard_preserving_pairs=len(rows))
    write_json(out/'semantic-summary.json',summary)

def tests(out):
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    names=[line.split(' ... ')[0] for line in stream.getvalue().splitlines() if ' ... ' in line]
    write_json(out/'test-summary.json',dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                                         skipped=len(result.skipped),successful=result.wasSuccessful(),tests=names))
    if not result.wasSuccessful():raise AssertionError(stream.getvalue())

def summarize(out):
    groups=defaultdict(list)
    keys_seen=set()
    for path in sorted((out/'enumeration').glob('*.csv')):
        with path.open() as s:
            for row in csv.DictReader(s):
                key=(row['lattice'],int(row['first_map']),int(row['second_map']))
                if key in keys_seen:raise ValueError('overlapping or duplicate chunk')
                keys_seen.add(key);groups[key[0]].append(row)
    rows=[]
    numeric=('cases','incomplete_cases','complete_unique_cases','complete_multiple_cases','formula_mismatches',
             'maximal_guard_checks','persistent_guard_checks','strict_transition_guard_advantage_emitters')
    for name in LATTICES:
        lat=named_lattice(name);m=len(monotone_inflationary_maps(lat));rs=groups[name]
        expected={(name,i,j) for i in range(m) for j in range(m)}
        if {k for k in keys_seen if k[0]==name} != expected:raise ValueError(f'incomplete chunk coverage: {name}')
        d=dict(lattice=name,states=lat.n,maps=m,ordered_map_pairs=len(rs))
        for k in numeric:d[k]=sum(int(r[k]) for r in rs)
        assert d['cases']==m*m*4**lat.n
        assert d['cases']==d['incomplete_cases']+d['complete_unique_cases']+d['complete_multiple_cases']
        rows.append(d)
    write_csv(out/'enumeration-summary.csv',rows)
    total={k:sum(r[k] for r in rows) for k in numeric}
    total['ordered_map_pairs']=sum(r['ordered_map_pairs'] for r in rows)
    total['named_lattices']=len(rows)
    write_json(out/'enumeration-total.json',total)
    metrics=[json.loads(p.read_text()) for p in (out/'enumeration').glob('*.json')]
    write_json(out/'enumeration-resources.json',dict(chunks=len(metrics),
        cumulative_measured_cpu_seconds=sum(x['cpu_seconds'] for x in metrics),
        cumulative_measured_wall_seconds=sum(x['wall_seconds'] for x in metrics),
        maximum_process_peak_rss_kib=max(x['peak_rss_kib'] for x in metrics),timeouts=sum(x['timeouts'] for x in metrics),
        note='Process CPU and wall values measure chunk bodies, not shell, interpreter startup, pre-campaign work, or document compilation. Very short calls may report zero CPU at timer resolution.'))
    print(json.dumps(total,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['evidence','summarize'])
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();cpu=time.process_time();wall=time.perf_counter()
    if a.action=='evidence':maps(a.out);examples(a.out);semantic(a.out);tests(a.out)
    else:summarize(a.out)
    write_json(a.out/f'{a.action}-resources.json',dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,workers=1,children=0))
