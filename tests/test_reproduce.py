"""Crash-completeness tests for the resumable reproduction driver."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from reproduce import (
    MARKER_DIRECTORY,
    mark_complete,
    run,
    step_complete,
    valid_output,
)


class ReproductionCompletion(unittest.TestCase):
    def test_structural_sentinel_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good_json = root / "good.json"
            good_json.write_text('{"ok": true}\n', encoding="utf-8")
            bad_json = root / "bad.json"
            bad_json.write_text('{"ok":', encoding="utf-8")
            good_csv = root / "good.csv"
            good_csv.write_text("a,b\n1,2\n", encoding="utf-8")
            ragged_csv = root / "ragged.csv"
            ragged_csv.write_text("a,b\n1\n", encoding="utf-8")
            self.assertTrue(valid_output(good_json))
            self.assertFalse(valid_output(bad_json))
            self.assertTrue(valid_output(good_csv))
            self.assertFalse(valid_output(ragged_csv))

    def test_nonempty_file_without_completion_record_is_not_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = output / "result.json"
            sentinel.write_text('{"partial_but_parseable": true}\n', encoding="utf-8")
            markers = output / MARKER_DIRECTORY
            markers.mkdir()
            self.assertFalse(step_complete(output, "step", [sentinel], markers))

    def test_completion_record_and_sentinel_must_both_remain_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = output / "result.json"
            sentinel.write_text('{"complete": true}\n', encoding="utf-8")
            markers = output / MARKER_DIRECTORY
            markers.mkdir()
            mark_complete(output, "step", [sentinel], markers)
            self.assertTrue(step_complete(output, "step", [sentinel], markers))
            sentinel.write_text('{"truncated":', encoding="utf-8")
            self.assertFalse(step_complete(output, "step", [sentinel], markers))

    def test_run_marks_success_and_then_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            markers = output / MARKER_DIRECTORY
            markers.mkdir()
            sentinel = output / "child.json"
            code = (
                "from pathlib import Path; import json, sys; "
                "Path(sys.argv[1]).write_text(json.dumps({'ok': True})+'\\n', encoding='utf-8')"
            )
            records: list[dict[str, object]] = []
            run(output, "child-step", [sys.executable, "-c", code, str(sentinel)],
                [sentinel], markers, records)
            self.assertTrue(step_complete(output, "child-step", [sentinel], markers))
            self.assertFalse(records[0]["skipped_completed"])
            second: list[dict[str, object]] = []
            run(output, "child-step", [sys.executable, "-c", "raise SystemExit(99)"],
                [sentinel], markers, second)
            self.assertTrue(second[0]["skipped_completed"])
            self.assertEqual(second[0]["returncode"], 0)

    def test_marker_metadata_is_bound_to_the_declared_sentinel_set(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            first = output / "first.json"
            second = output / "second.json"
            first.write_text(json.dumps({"first": True}) + "\n", encoding="utf-8")
            second.write_text(json.dumps({"second": True}) + "\n", encoding="utf-8")
            markers = output / MARKER_DIRECTORY
            markers.mkdir()
            mark_complete(output, "step", [first], markers)
            self.assertFalse(step_complete(output, "step", [second], markers))


if __name__ == "__main__":
    unittest.main()
