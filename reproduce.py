#!/usr/bin/env python3
"""Reproduce all deterministic finite evidence with resumable process isolation.

The legacy one-slot enumerator and the code-changing staged enumerator share a
small lattice module but allocate very different short-lived object graphs.
This driver launches a fixed sequence of bounded child processes, never more
than one at a time.  Every step has durable completion sentinels, so rerunning
the same command after an external interruption resumes without changing the
scientific selection.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Sequence

try:
    import resource
except ModuleNotFoundError:
    resource = None  # Portable completion helpers do not require POSIX limits.

ROOT = Path(__file__).resolve().parent
CHUNKS = (
    ("C1", 0, 1), ("C2", 0, 2), ("C3", 0, 5), ("C4", 0, 14),
    ("B2", 0, 9), ("C5", 0, 14), ("C5", 14, 28), ("C5", 28, 42),
    ("M3", 0, 15), ("N5", 0, 21),
)
INDEPENDENT_FAMILIES = (
    "A-C2-one-rewrite",
    "A-C3-one-rewrite",
    "A-B2-one-rewrite",
    "B-C2-fork",
    "B-B2-fork",
    "C-B2-diamond",
    "D-B2-two-analysis",
)

MARKER_SCHEMA = "pvso-reproduction-step-1"
MARKER_DIRECTORY = ".reproduction-complete"


def atomic_write_text(path: Path, text: str) -> None:
    """Replace *path* atomically after flushing a same-directory temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def child_limits() -> None:
    """Apply the documented Linux limits before exec in each child."""
    if resource is None:
        raise RuntimeError("POSIX resource limits are unavailable")
    # Each program is single-threaded.  Do not pin the orchestrated child: the
    # kernel may migrate it away from a contended logical CPU.  The legacy
    # chunk executable applies its own one-CPU affinity.
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (180, 185))


def valid_output(path: Path) -> bool:
    """Check that a sentinel is present and structurally parseable.

    This is deliberately a crash-completeness check, not an integrity hash.  A
    clean forced reproduction plus ``compare_results.py`` remains the semantic
    comparison path.
    """
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
                return False
        return True
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error):
        return False


def valid_outputs(paths: Sequence[Path]) -> bool:
    return bool(paths) and all(valid_output(path) for path in paths)


def marker_path(marker_directory: Path, label: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in label)
    return marker_directory / f"{safe}.json"


def relative_sentinels(output: Path, sentinels: Sequence[Path]) -> list[str]:
    return [str(path.resolve().relative_to(output.resolve())) for path in sentinels]


def step_complete(
    output: Path,
    label: str,
    sentinels: Sequence[Path],
    marker_directory: Path,
) -> bool:
    marker = marker_path(marker_directory, label)
    if not marker.is_file() or not valid_outputs(sentinels):
        return False
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return value == {
        "schema": MARKER_SCHEMA,
        "label": label,
        "sentinels": relative_sentinels(output, sentinels),
    }


def mark_complete(
    output: Path,
    label: str,
    sentinels: Sequence[Path],
    marker_directory: Path,
) -> None:
    if not valid_outputs(sentinels):
        raise RuntimeError(f"cannot mark invalid reproduction outputs complete: {label}")
    write_json(marker_path(marker_directory, label), {
        "schema": MARKER_SCHEMA,
        "label": label,
        "sentinels": relative_sentinels(output, sentinels),
    })


def run(
    output: Path,
    label: str,
    argv: Sequence[str],
    sentinels: Sequence[Path],
    marker_directory: Path,
    records: list[dict[str, object]],
) -> None:
    marker = marker_path(marker_directory, label)
    if step_complete(output, label, sentinels, marker_directory):
        records.append({"label": label, "skipped_completed": True, "returncode": 0})
        return
    marker.unlink(missing_ok=True)
    started_wall = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN) if resource is not None else None
    env = os.environ.copy()
    env.update({"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"})
    completed = subprocess.run(
        list(argv), cwd=ROOT, env=env, check=False,
        preexec_fn=child_limits if os.name == "posix" and resource is not None else None,
        timeout=240,
    )
    after = resource.getrusage(resource.RUSAGE_CHILDREN) if resource is not None else None
    record = {
        "label": label,
        "skipped_completed": False,
        "returncode": completed.returncode,
        "wall_seconds": time.perf_counter() - started_wall,
        "child_user_cpu_seconds": after.ru_utime - before.ru_utime if before is not None else None,
        "child_system_cpu_seconds": after.ru_stime - before.ru_stime if before is not None else None,
    }
    records.append(record)
    if completed.returncode != 0:
        raise RuntimeError(f"reproduction step failed ({label}): return code {completed.returncode}")
    if not valid_outputs(sentinels):
        raise RuntimeError(f"reproduction step did not create valid completion sentinels: {label}")
    mark_complete(output, label, sentinels, marker_directory)


def component_cpu(output: Path) -> float:
    total = 0.0
    for path in (output / "enumeration").glob("*.json"):
        total += float(json.loads(path.read_text())["cpu_seconds"])
    for name in ("evidence-resources.json", "summarize-resources.json"):
        path = output / name
        if path.is_file():
            total += float(json.loads(path.read_text()).get("cpu_seconds", 0.0))
    path = output / "staged" / "staged-enumeration-summary.json"
    if path.is_file():
        total += float(json.loads(path.read_text()).get("cpu_seconds", 0.0))
    path = output / "staged" / "staged-evidence-resources.json"
    if path.is_file():
        total += float(json.loads(path.read_text()).get("cpu_seconds", 0.0))
    path = output / "staged" / "independent-audit-resources.json"
    if path.is_file():
        value = json.loads(path.read_text())
        total += float(value.get("cumulative_cpu_seconds", value.get("cpu_seconds", 0.0)))
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--force", action="store_true",
        help="ignore prior step-completion records and rerun every component",
    )
    args = parser.parse_args()
    if os.name != "posix" or resource is None:
        raise RuntimeError("full reproduction requires POSIX resource limits; portable checks remain available")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    marker_directory = output / MARKER_DIRECTORY
    if args.force:
        shutil.rmtree(marker_directory, ignore_errors=True)
    marker_directory.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    records: list[dict[str, object]] = []
    wall_started = time.perf_counter()
    parent_cpu_started = time.process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)

    # Legacy inputs, named controls, semantic catalog, and complete test suite.
    run(
        output,
        "legacy-evidence-and-tests",
        [python, "collect.py", "evidence", "--out", str(output)],
        [output / "evidence-resources.json", output / "test-summary.json",
         output / "semantic-summary.json", output / "inputs" / "expressions.json"],
        marker_directory,
        records,
    )
    for lattice, first, stop in CHUNKS:
        stem = f"{lattice}-{first:03d}-{stop:03d}"
        run(
            output,
            f"legacy-enumeration-{lattice}-{first}-{stop}",
            [python, "exhaustive.py", "--lattice", lattice, "--start", str(first),
             "--stop", str(stop), "--out", str(output / "enumeration")],
            [output / "enumeration" / f"{stem}.csv", output / "enumeration" / f"{stem}.json"],
            marker_directory,
            records,
        )
    run(
        output,
        "legacy-summarize",
        [python, "collect.py", "summarize", "--out", str(output)],
        [output / "summarize-resources.json", output / "enumeration-total.json",
         output / "enumeration-summary.csv"],
        marker_directory,
        records,
    )

    # Main code-changing staged-system campaign and independently replayed evidence.
    staged = output / "staged"
    run(
        output,
        "staged-enumeration",
        [python, "staged_campaign.py", "--out", str(staged)],
        [staged / "staged-enumeration-summary.json", staged / "staged-enumeration-families.csv",
         staged / "staged-enumeration-examples.json"],
        marker_directory,
        records,
    )
    audit_parts = staged / "independent-audit-parts"
    for family in INDEPENDENT_FAMILIES:
        part = audit_parts / family
        run(
            output,
            f"staged-independent-audit-{family}",
            [python, "independent_audit.py", "--out", str(part), "--family", family],
            [part / "independent-audit-summary.json",
             part / "independent-audit-families.csv",
             part / "independent-audit-resources.json"],
            marker_directory,
            records,
        )
    run(
        output,
        "staged-independent-audit-aggregate",
        [python, "aggregate_independent_audit.py", "--parts", str(audit_parts),
         "--out", str(staged)],
        [staged / "independent-audit-summary.json",
         staged / "independent-audit-families.csv",
         staged / "independent-audit-resources.json"],
        marker_directory,
        records,
    )
    run(
        output,
        "staged-case-evidence",
        [python, "staged_evidence.py", "--cases", str(ROOT / "staged_cases"), "--out", str(staged)],
        [staged / "case-summary.json", staged / "mutation-summary.json",
         staged / "staged-evidence-resources.json"],
        marker_directory,
        records,
    )

    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    write_json(output / "driver-resources.json", {
        "completed": True,
        "resumable": True,
        "wall_seconds_this_invocation": time.perf_counter() - wall_started,
        "parent_cpu_seconds_this_invocation": time.process_time() - parent_cpu_started,
        "child_user_cpu_seconds_this_invocation": child_after.ru_utime - child_before.ru_utime,
        "child_system_cpu_seconds_this_invocation": child_after.ru_stime - child_before.ru_stime,
        "scientific_component_cpu_seconds": component_cpu(output),
        "maximum_child_peak_rss_kib_this_invocation": child_after.ru_maxrss,
        "workers": 1,
        "maximum_concurrent_children": 1,
        "steps_in_plan": len(records),
        "steps_skipped_from_prior_completed_output": sum(bool(r.get("skipped_completed")) for r in records),
        "legacy_chunks": len(CHUNKS),
        "staged_families": 7,
        "child_cpu_limit_seconds": 180,
        "child_address_space_limit_bytes": 3 * 1024**3,
        "steps": records,
        "note": (
            "Sequential process isolation prevents cross-campaign allocator/GC interference. "
            "A step is skipped only when its parseable sentinels and atomically written completion "
            "record agree; a partial nonempty file is never a completion signal. Timings are informative; "
            "deterministic scientific files are compared separately."
        ),
    })


if __name__ == "__main__":
    main()
