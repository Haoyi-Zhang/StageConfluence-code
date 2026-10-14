"""Retain existing named inputs, modular proofs, exact fallback and complete cost.

No new generated systems. Timings include parsing/validation, production,
serialization, reparsing and replay for proof routes. The ordinary direct
decision baseline has the same instance and outcome questions, but trusts its
search rather than transporting a search-free proof.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
import time

from src.staged_model import load_staged_instance
from src.staged_certificate import make_confluence_certificate, make_nonconfluence_witness
from src.staged_verify import verify_confluence_certificate, verify_nonconfluence_witness
from src.modular_certificate import make_modular_certificate, verify_modular_certificate
from independent_audit import independent_classify, reachable_graph, terminal_sets
from src.runtime_support import scope, peak_rss_kib

ROOT = Path(__file__).resolve().parent
CASES = ('S01','S02','S03','S04','S07','S08','S09','S10','S11')
ROUTES = ('full-proof', 'modular-with-exact-fallback', 'ordinary-direct')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n', encoding='utf-8')


def run_route(payload, route):
    begin = time.perf_counter_ns()
    instance = load_staged_instance(json.loads(payload))
    parsed = time.perf_counter_ns()
    if route == 'ordinary-direct':
        result = independent_classify(instance)
        initial, states, edges = reachable_graph(instance)
        terminals = terminal_sets(states, edges)[initial]
        tables, source = instance.program_truth_tables(), instance.source_truth_table()
        outcome = dict(confluent=result['direct'],
            terminal_programs_source_equivalent=all(tables[p] == source for p, _ in terminals))
        done = time.perf_counter_ns()
        return outcome, dict(kind='direct-decision', input_parse_ns=parsed-begin,
            production_ns=done-parsed, transport_ns=0, consumer_ns=0,
            total_ns=done-begin, proof_bytes=0), None
    proof = make_modular_certificate(instance) if route == 'modular-with-exact-fallback' else None
    kind = 'modular' if proof is not None else 'full'
    if proof is None:
        proof = make_confluence_certificate(instance)
    if proof is None:
        proof = make_nonconfluence_witness(instance)
        kind = 'witness'
    if proof is None:
        raise RuntimeError('no evidence for admitted finite named instance')
    produced = time.perf_counter_ns()
    serialized = json.dumps(proof, sort_keys=True, separators=(',', ':')).encode('utf-8')
    received = json.loads(serialized)
    consumer_instance = load_staged_instance(json.loads(payload))
    transported = time.perf_counter_ns()
    if kind == 'modular':
        checked = verify_modular_certificate(consumer_instance, received)
    elif kind == 'full':
        checked = verify_confluence_certificate(consumer_instance, received)
    else:
        checked = verify_nonconfluence_witness(consumer_instance, received)
    if not checked['valid']:
        raise RuntimeError('consumer rejected producer evidence')
    done = time.perf_counter_ns()
    # A terminal fork proves nonconfluence, but need not enumerate all terminal
    # semantics. Do not turn two preserving endpoints into an all-terminal claim.
    outcome = dict(confluent=kind != 'witness', terminal_programs_source_equivalent=
        checked.get('terminal_programs_source_equivalent'))
    return outcome, dict(kind=kind, input_parse_ns=parsed-begin,
        production_ns=produced-parsed, transport_ns=transported-produced,
        consumer_ns=done-transported, total_ns=done-begin, proof_bytes=len(serialized)), proof


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    rows, cases = [], []
    started_cpu, started_wall = time.process_time(), time.perf_counter()
    for name in CASES:
        payload = (ROOT/'staged_cases'/f'{name}.json').read_text(encoding='utf-8')
        expected, _, _ = run_route(payload, 'ordinary-direct')
        case = dict(case=name, input=json.loads(payload), expected=expected, routes={})
        for repeat in range(5):
            order = ROUTES if repeat % 2 == 0 else tuple(reversed(ROUTES))
            for route in order:
                result, metrics, proof = run_route(payload, route)
                if result['confluent'] != expected['confluent']:
                    raise RuntimeError(f'{name}: decision mismatch for {route}')
                if result['confluent'] and result != expected:
                    raise RuntimeError(f'{name}: positive semantic mismatch for {route}')
                rows.append(dict(case=name, repeat=repeat, route=route, **metrics))
                if repeat == 0:
                    case['routes'][route] = dict(outcome=result, kind=metrics['kind'])
                    if proof is not None:
                        dump(out/name/f'{route}.json', proof)
        dump(out/name/'input.json', case['input'])
        dump(out/name/'comparison.json', case)
        cases.append(case)
    with (out/'cost.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    ratios = []
    for name in CASES:
        medians = {r: statistics.median(x['total_ns'] for x in rows if x['case']==name and x['route']==r)
                   for r in ROUTES}
        sizes = {r: next(x['proof_bytes'] for x in rows if x['case']==name and x['route']==r) for r in ROUTES}
        ratios.append(dict(case=name, median_total_ns=medians, serialized_proof_bytes=sizes,
            modular_full_time_ratio=medians[ROUTES[1]]/medians[ROUTES[0]],
            modular_full_byte_ratio=sizes[ROUTES[1]]/sizes[ROUTES[0]]))
    summary = dict(schema='pvso-modular-evidence-1', cases=list(CASES), repetitions=5,
        timing_rows=len(rows), optimize=sys.flags.optimize, host=scope(),
        modular_positive_cases=[x['case'] for x in cases if x['routes'][ROUTES[1]]['kind']=='modular'],
        exact_fallback_positive_cases=[x['case'] for x in cases if x['routes'][ROUTES[1]]['kind']=='full'],
        witness_cases=[x['case'] for x in cases if x['routes'][ROUTES[1]]['kind']=='witness'],
        comparisons=ratios,
        cost_scope='proof routes: input parse/validate + production incl self-check + serialize + parse proof and instance + replay; direct: parse/validate + independent classification and all-terminal semantic decision',
        exclusions=['interpreter startup', 'disk I/O', 'paper compilation'],
        scientific_scope='nine existing owned finite Boolean cases, not native BuildIt/Nexis or production compiler deployment; repeats are timing observations not extra systems',
        direct_baseline_assurance='same input/decision; search is trusted, not a search-free proof consumer',
        negative_semantic_boundary='two terminal witness endpoints do not decide universal terminal source equivalence')
    dump(out/'summary.json', summary)
    dump(out/'resources.json', dict(cpu_seconds=time.process_time()-started_cpu,
        wall_seconds=time.perf_counter()-started_wall, peak_rss_kib=peak_rss_kib()))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
