#!/usr/bin/env python3
"""CLI for finite code-changing staged-system analysis and certificate replay."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from src.staged_model import load_staged_instance
from src.staged_checker import analyze_staged
from src.staged_certificate import (
    make_confluence_certificate,
    make_nonconfluence_witness,
    verify_confluence_certificate,
    verify_nonconfluence_witness,
)

MAX_JSON_BYTES = 8 * 1024 * 1024


def read_json(path: Path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("JSON file exceeds eight MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(value, path: Path | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(text)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("analyze", "certify", "witness"):
        p = sub.add_parser(name)
        p.add_argument("instance", type=Path)
        p.add_argument("--out", type=Path)
    p = sub.add_parser("verify-certificate")
    p.add_argument("instance", type=Path)
    p.add_argument("certificate", type=Path)
    p = sub.add_parser("verify-witness")
    p.add_argument("instance", type=Path)
    p.add_argument("witness", type=Path)
    args = parser.parse_args()
    try:
        instance = load_staged_instance(read_json(args.instance))
        if args.command == "analyze":
            write_json(analyze_staged(instance, include_peak_paths=True), args.out)
        elif args.command == "certify":
            cert = make_confluence_certificate(instance)
            if cert is None:
                raise ValueError("instance is not locally confluent; no positive certificate exists")
            write_json(cert, args.out)
        elif args.command == "witness":
            witness = make_nonconfluence_witness(instance)
            if witness is None:
                raise ValueError("instance has no two distinct reachable terminal states")
            write_json(witness, args.out)
        elif args.command == "verify-certificate":
            write_json(verify_confluence_certificate(instance, read_json(args.certificate)), None)
        elif args.command == "verify-witness":
            write_json(verify_nonconfluence_witness(instance, read_json(args.witness)), None)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
