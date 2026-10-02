#!/usr/bin/env python3
"""Compare every retained deterministic scientific file; timings are excluded."""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path


def selected(root: Path) -> dict[Path, Path]:
    paths: list[Path] = []
    legacy_patterns = (
        'inputs/*.json', 'cases/*.json', 'enumeration/*.csv',
        'enumeration-summary.csv', 'enumeration-total.json',
        'semantic-pairs.csv', 'semantic-summary.json', 'test-summary.json',
    )
    staged_patterns = (
        'staged/staged-enumeration-families.csv',
        'staged/staged-enumeration-summary.json',
        'staged/staged-enumeration-examples.json',
        'staged/independent-audit-summary.json',
        'staged/independent-audit-families.csv',
        'staged/independent-audit-parts/*/independent-audit-summary.json',
        'staged/independent-audit-parts/*/independent-audit-families.csv',
        'staged/case-summary.csv', 'staged/case-summary.json',
        'staged/mutation-results.csv', 'staged/mutation-summary.json',
        'staged/cases/*.json', 'staged/certificates/*.json',
        'staged/witnesses/*.json',
    )
    for pattern in (*legacy_patterns, *staged_patterns):
        paths.extend(root.glob(pattern))
    return {p.relative_to(root): p for p in paths}


def compare(left: Path, right: Path) -> dict[str, object]:
    a, b = selected(left), selected(right)
    if set(a) != set(b):
        missing_left = sorted(str(x) for x in set(b) - set(a))
        missing_right = sorted(str(x) for x in set(a) - set(b))
        raise ValueError(f'evidence file-set mismatch; missing-left={missing_left}; missing-right={missing_right}')
    if not a:
        raise ValueError('no deterministic evidence')
    for key in sorted(a):
        if key.suffix == '.json':
            aa, bb = json.loads(a[key].read_text()), json.loads(b[key].read_text())
            # Campaign summary timings are nondeterministic but all scientific fields are deterministic.
            if key.name == 'staged-enumeration-summary.json':
                for value in (aa, bb):
                    value.pop('cpu_seconds', None); value.pop('wall_seconds', None)
                    for row in value.get('families', []):
                        row.pop('cpu_seconds', None); row.pop('wall_seconds', None)
        else:
            aa, bb = a[key].read_text(), b[key].read_text()
            if key.name == 'staged-enumeration-families.csv':
                # Strip timing columns with a real CSV parser so quoted commas
                # cannot change the comparison boundary.
                def strip_timing(text: str) -> list[dict[str, str]]:
                    rows = []
                    for row in csv.DictReader(io.StringIO(text)):
                        row.pop('cpu_seconds', None)
                        row.pop('wall_seconds', None)
                        rows.append(row)
                    return rows
                aa, bb = strip_timing(aa), strip_timing(bb)
        if aa != bb:
            raise ValueError(f'deterministic evidence mismatch: {key}')
    result = {'deterministic_files_compared': len(a), 'equal': True, 'resources_compared': False}
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('retained', type=Path)
    parser.add_argument('fresh', type=Path)
    args = parser.parse_args()
    compare(args.retained, args.fresh)
