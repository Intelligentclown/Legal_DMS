from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import current_context_manifest as manifest


class TestCurrentContextManifest(unittest.TestCase):
    def _root(self) -> Path:
        root = Path(__file__).parents[2]
        return root

    def test_real_repository_is_deterministic_and_has_no_clock_field(self) -> None:
        first = manifest.canonical_json(self._root())
        second = manifest.canonical_json(self._root())
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertNotIn("generatedAt", first)
        self.assertEqual(payload["projection"]["authority"], "non_authoritative")

    def test_frontier_and_required_adrs_use_governance_derivation(self) -> None:
        payload = manifest.build(self._root())
        self.assertEqual(payload["governance_frontier"]["latest_done"], "T128")
        self.assertEqual(payload["governance_frontier"]["latest_authorized"], "T129")
        self.assertEqual(payload["required_adrs"]["unresolved"], [10, 11, 12, 15, 16, 17, 20])

    def test_ledger_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ADR").mkdir()
            (root / "IMPLEMENTATION_QUEUE.md").write_text(
                "| T1 | Authorized by the project owner. T1 is now Done -- merged. QA Decision: Approved. |\n",
                encoding="utf-8",
            )
            (root / "PROJECT_STATE.json").write_text(
                json.dumps({"governanceLedger": {"latestTaskDone": "T2"}}), encoding="utf-8"
            )
            with patch.object(manifest.governance, "find_repo_root", return_value=root), patch.object(
                manifest, "_git_commit", return_value="a" * 40
            ):
                with self.assertRaises(manifest.ManifestError):
                    manifest.build(root)

    def test_generation_does_not_use_network(self) -> None:
        with patch("subprocess.run", wraps=subprocess.run) as run:
            manifest.canonical_json(self._root())
        self.assertTrue(all("fetch" not in call.args[0] for call in run.call_args_list))


if __name__ == "__main__":
    unittest.main()
