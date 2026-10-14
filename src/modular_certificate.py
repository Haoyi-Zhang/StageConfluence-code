"""Replay GP/CC plus a closed saturated graph, without listing the mixed graph.

The graph kernel is the existing exact replay verifier, not a new independent
trusted implementation. Only the producer searches. The ordinary full-graph
format remains the exact fallback for confluent systems outside GP/CC.
"""
from dataclasses import replace

from .staged_model import AnalysisRule
from .staged_verify import _exact, _require, verify_confluence_certificate

SCHEMA = 'pvso-modular-certificate-1'


def replay_closures(instance, rows):
    """All P x L rows, including unreachable ones; no fixed-point search."""
    pairs = [(p, f) for p in range(len(instance.programs)) for f in range(instance.lattice.n)]
    _require(isinstance(rows, list) and len(rows) == len(pairs), 'closure coverage mismatch')
    closed = {}
    for row, (p, f) in zip(rows, pairs):
        _require(isinstance(row, dict) and _exact((row.get('program'), row.get('fact')), (p, f)),
                 'noncanonical closure row')
        trace = row.get('trace')
        _require(isinstance(trace, list), 'invalid closure trace')
        _require(len(trace) < instance.lattice.n, 'overlong closure trace')
        rules = instance.programs[p].analyses
        current = f
        for ai in trace:
            _require(type(ai) is int and 0 <= ai < len(rules), 'invalid closure rule')
            target = rules[ai].table[current]
            _require(target != current, 'closure trace contains a stutter')
            current = target
        _require(all(a.table[current] == current for a in rules), 'closure endpoint not fixed')
        _require(_exact(row.get('final'), current), 'closure final mismatch')
        closed[p, f] = current
    return closed


def obligations(instance, closed):
    """Global GP and enabled-fact CC; never restrict these to the sat graph."""
    for ri, r in enumerate(instance.rewrites):
        for f, enabled in enumerate(r.guard):
            if not enabled:
                continue
            for ai, a in enumerate(instance.programs[r.source].analyses):
                _require(r.guard[a.table[f]], f'GP fails at rewrite {ri}, fact {f}, analysis {ai}')
            early = closed[r.target, r.transfer[f]]
            late = closed[r.target, r.transfer[closed[r.source, f]]]
            _require(early == late, f'CC fails at rewrite {ri}, fact {f}')


def saturated_instance(instance, closed):
    """Identity-analysis presentation of exactly the closed rewrite relation.

    This is computed from replayed closures, not accepted from the producer.
    At closed x its edge is (p,x) -> (q,C_q(tau(x))). Nonclosed sources are
    disabled. C_q o tau remains monotone/inflationary on all declared facts.
    """
    identity = tuple(range(instance.lattice.n))
    programs = tuple(replace(p, analyses=(AnalysisRule('closed', 'auxiliary', identity),))
                     for p in instance.programs)
    rewrites = tuple(replace(r,
        guard=tuple(r.guard[f] and closed[r.source, f] == f for f in identity),
        transfer=tuple(closed[r.target, r.transfer[f]] for f in identity)) for r in instance.rewrites)
    return replace(instance, programs=programs, rewrites=rewrites,
                   initial_fact=closed[instance.initial_program, instance.initial_fact])


def make_modular_certificate(instance):
    # Imports confined to production. Verification below never imports search.
    from .staged_checker import analysis_closure_trace
    from .staged_certificate import make_confluence_certificate
    instance.validate()
    rows = []
    for p in range(len(instance.programs)):
        for f in range(instance.lattice.n):
            final, trace = analysis_closure_trace(instance, p, f)
            rows.append(dict(program=p, fact=f, final=final, trace=list(trace)))
    closed = replay_closures(instance, rows)
    try:
        obligations(instance, closed)
    except ValueError:
        return None  # Failure of a sufficient criterion is not nonconfluence.
    graph = make_confluence_certificate(saturated_instance(instance, closed))
    if graph is None:
        return None
    graph.pop('closures')  # Identity-analysis traces are reconstructed locally.
    result = dict(schema=SCHEMA, instance=instance.name, closures=rows, graph=graph)
    verify_modular_certificate(instance, result)
    return result


def verify_modular_certificate(instance, certificate):
    instance.validate()
    _require(isinstance(certificate, dict) and certificate.get('schema') == SCHEMA,
             'wrong modular certificate schema')
    _require(certificate.get('instance') == instance.name, 'instance name mismatch')
    closed = replay_closures(instance, certificate.get('closures'))
    obligations(instance, closed)
    derived = saturated_instance(instance, closed)
    graph = certificate.get('graph')
    _require(isinstance(graph, dict) and 'closures' not in graph, 'invalid saturated graph object')
    graph = dict(graph, closures=[dict(program=p, fact=f, final=f, trace=[])
        for p in range(len(instance.programs)) for f in range(instance.lattice.n)])
    checked = verify_confluence_certificate(derived, graph)
    # Under GP+CC, full and saturated terminal sets are identical (paper lemma).
    terminal = graph['states'][graph['terminals'][0]]
    return dict(valid=True, full_state_confluent=True,
        saturated_states=checked['states'], saturated_edges=checked['edges'],
        saturated_peaks=checked['peaks'], terminal_state=[terminal['program'], terminal['fact']],
        all_declared_rewrites_preserve_observation=checked['all_declared_rewrites_preserve_observation'],
        terminal_programs_source_equivalent=checked['terminal_programs_source_equivalent'])
