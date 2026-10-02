#!/usr/bin/env python3
"""Analyze a bounded explicit instance, or replay a witness independently.

Examples:
  python check.py analyze cases/C01.json
  python check.py witness cases/C01.json --out /tmp/certificate.json
  python check.py verify cases/C01.json /tmp/certificate.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from src.model import load_instance
from src.checker import analyze, make_witness, verify_witness

MAX_FILE_BYTES = 8 * 1024 * 1024


def read_json(path: Path):
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('input exceeds the 8 MiB file bound')
    return json.loads(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for cmd in ('analyze', 'witness', 'verify'):
        p = sub.add_parser(cmd)
        p.add_argument('instance', type=Path)
        if cmd == 'verify':
            p.add_argument('certificate', type=Path)
        p.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        inst = load_instance(read_json(args.instance))
        if args.command == 'analyze':
            result = analyze(inst)
        elif args.command == 'witness':
            result = make_witness(inst)
        else:
            result = verify_witness(inst, read_json(args.certificate))
        text = json.dumps(result, indent=2, sort_keys=True) + '\n'
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text)
        else:
            print(text, end='')
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as exc:
        print(f'validation error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
