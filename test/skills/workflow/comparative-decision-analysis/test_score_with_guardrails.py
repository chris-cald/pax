#!/usr/bin/env python3
"""Regression tests for comparative-decision-analysis guardrail scoring."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    REPO_ROOT
    / "skills/workflow/comparative-decision-analysis/scripts/score_with_guardrails.py"
)
VALIDATOR = (
    REPO_ROOT
    / "skills/workflow/comparative-decision-analysis/scripts/validate_json_contract.mjs"
)
INPUT_SCHEMA = (
    REPO_ROOT
    / "skills/workflow/comparative-decision-analysis/references/input-schema.json"
)
OUTPUT_SCHEMA = (
    REPO_ROOT
    / "skills/workflow/comparative-decision-analysis/references/output-schema.json"
)


def _run(input_data: dict[str, Any], extra_args: list[str] | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    if extra_args is None:
        extra_args = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        cmd = [
            "python3",
            str(SCRIPT),
            "--input",
            str(input_path),
            "--json-output",
            str(output_path),
            *extra_args,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return proc, None

        result = json.loads(output_path.read_text(encoding="utf-8"))
        return proc, result


def _base_input() -> dict[str, Any]:
    return {
        "decision": "test",
        "run_id": "run-test",
        "criteria_confirmed": True,
        "criteria_confirmation_source": "user-confirmed",
        "current_platform": "chatgpt",
        "major_platforms": ["chatgpt"],
        "score_scale": "0-100",
        "discovery": {
            "external_discovery_done": False,
            "external_discovery_blocked": True,
            "block_reason": "unit test local simulation",
            "checked_at": "2026-04-18T00:00:00Z",
        },
        "criteria": [
            {
                "id": "fit",
                "name": "Fit",
                "weight": 1,
                "metric": "fit metric",
                "data_source": "source",
                "scoring_rule": "0-100",
            },
            {
                "id": "risk",
                "name": "Risk",
                "weight": 1,
                "metric": "risk metric",
                "data_source": "source",
                "scoring_rule": "0-100",
            },
        ],
        "alternatives": [],
        "independent_evaluations": [],
    }


def _independent_records(*alternative_ids: str) -> list[dict[str, Any]]:
    records = []
    for alt_id in alternative_ids:
        records.append(
            {
                "alternative_id": alt_id,
                "evaluator_id": f"eval-{alt_id}",
                "isolation_confirmed": True,
                "summary": f"Independent evaluation for {alt_id}",
            }
        )
    return records


class GuardrailScoreTests(unittest.TestCase):
    def test_missing_scores_are_excluded_not_zeroed(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "A has missing evidence on risk",
                "scores": {"chatgpt": {"fit": 100, "risk": None}},
            },
            {
                "id": "b",
                "name": "B",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "B has complete evidence",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
        ]
        data["independent_evaluations"] = _independent_records("a", "b")

        proc, result = _run(data)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None

        ranked = result["ranked_alternatives"]
        self.assertEqual(ranked[0]["id"], "a")
        self.assertAlmostEqual(ranked[0]["current_platform_score"], 100.0, places=2)
        self.assertAlmostEqual(ranked[0]["coverage"], 0.5, places=3)

    def test_single_option_requires_discovery_by_default(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "single option",
                "scores": {"chatgpt": {"fit": 99, "risk": 99}},
            }
        ]
        data["independent_evaluations"] = _independent_records("a")

        proc, result = _run(data)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(result)

        proc, result = _run(data, ["--allow-single-option"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None
        self.assertNotEqual(result["recommendation"]["action"], "select")

    def test_tie_break_uses_effort_then_risk(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "slow",
                "name": "Slow",
                "effort": "L",
                "risk": "High",
                "feasible": True,
                "justification": "same scores but higher effort and risk",
                "scores": {"chatgpt": {"fit": 90, "risk": 90}},
            },
            {
                "id": "fast",
                "name": "Fast",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "same scores but lower effort and risk",
                "scores": {"chatgpt": {"fit": 90, "risk": 90}},
            },
        ]
        data["independent_evaluations"] = _independent_records("slow", "fast")

        proc, result = _run(data)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None
        self.assertEqual(result["ranked_alternatives"][0]["id"], "fast")

    def test_select_is_blocked_when_coverage_below_gate(self) -> None:
        data = _base_input()
        data["recommendation_rules"] = {"select_margin": 1.0, "min_coverage": 0.9}
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "high score but low coverage",
                "scores": {"chatgpt": {"fit": 100, "risk": None}},
            },
            {
                "id": "b",
                "name": "B",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "lower score but complete coverage",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
        ]
        data["independent_evaluations"] = _independent_records("a", "b")

        proc, result = _run(data)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None
        self.assertNotEqual(result["recommendation"]["action"], "select")

    def test_confirmation_source_is_required_when_confirmed(self) -> None:
        data = _base_input()
        data.pop("criteria_confirmation_source")
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
            {
                "id": "b",
                "name": "B",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 79, "risk": 79}},
            },
        ]
        data["independent_evaluations"] = _independent_records("a", "b")

        proc, result = _run(data)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(result)

    def test_independent_evaluations_require_unique_evaluators(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
            {
                "id": "b",
                "name": "B",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 79, "risk": 79}},
            },
        ]
        data["independent_evaluations"] = [
            {
                "alternative_id": "a",
                "evaluator_id": "eval-shared",
                "isolation_confirmed": True,
                "summary": "Independent evaluation for a",
            },
            {
                "alternative_id": "b",
                "evaluator_id": "eval-shared",
                "isolation_confirmed": True,
                "summary": "Independent evaluation for b",
            },
        ]

        proc, result = _run(data)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(result)

    def test_nonisolated_override_allows_missing_records(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 81, "risk": 81}},
            },
            {
                "id": "b",
                "name": "B",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
        ]
        data["independent_evaluations"] = None

        proc, result = _run(data)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(result)

        proc, result = _run(data, ["--allow-nonisolated-evaluations"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None
        self.assertEqual(result["independent_evaluations"], [])

    def test_output_includes_audit_metadata_and_decision_status(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "a",
                "name": "A",
                "type": "internal",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 90, "risk": 90}},
            },
            {
                "id": "b",
                "name": "B",
                "type": "external",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "baseline",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
        ]
        data["discovery"] = {
            "external_discovery_done": True,
            "external_discovery_blocked": False,
            "checked_at": "2026-04-18T00:00:00Z",
        }
        data["independent_evaluations"] = _independent_records("a", "b")

        proc, result = _run(data)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        assert result is not None
        self.assertEqual(result["run_id"], "run-test")
        self.assertIn("scorer_version", result)
        self.assertIn("rules_version", result)
        self.assertIn("evaluated_at", result)
        self.assertEqual(result["decision_status"], "proceed")

    def test_json_schema_validation_on_input_and_output(self) -> None:
        data = _base_input()
        data["alternatives"] = [
            {
                "id": "external",
                "name": "External",
                "type": "external",
                "effort": "M",
                "risk": "Med",
                "feasible": True,
                "justification": "external option",
                "scores": {"chatgpt": {"fit": 85, "risk": 85}},
            },
            {
                "id": "internal",
                "name": "Internal",
                "type": "internal",
                "effort": "S",
                "risk": "Low",
                "feasible": True,
                "justification": "internal option",
                "scores": {"chatgpt": {"fit": 80, "risk": 80}},
            },
        ]
        data["discovery"] = {
            "external_discovery_done": True,
            "external_discovery_blocked": False,
            "checked_at": "2026-04-18T00:00:00Z",
        }
        data["independent_evaluations"] = _independent_records("external", "internal")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            output_path = tmp_path / "output.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            score_proc = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--input",
                    str(input_path),
                    "--json-output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(score_proc.returncode, 0, score_proc.stderr)

            in_proc = subprocess.run(
                [
                    "node",
                    str(VALIDATOR),
                    "--schema",
                    str(INPUT_SCHEMA),
                    "--data",
                    str(input_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(in_proc.returncode, 0, in_proc.stderr)

            out_proc = subprocess.run(
                [
                    "node",
                    str(VALIDATOR),
                    "--schema",
                    str(OUTPUT_SCHEMA),
                    "--data",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(out_proc.returncode, 0, out_proc.stderr)


if __name__ == "__main__":
    unittest.main()
