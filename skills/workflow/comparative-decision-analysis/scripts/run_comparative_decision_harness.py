#!/usr/bin/env python3
"""Deterministic harness wrapper for comparative decision scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run comparative decision scoring with reproducible artifacts."
    )
    parser.add_argument("--input", required=True, help="Path to analysis input JSON.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for generated report/result/manifest artifacts.",
    )
    parser.add_argument(
        "--run-id",
        help="Stable run id to use for output file names. Defaults to input hash prefix.",
    )
    parser.add_argument(
        "--schema",
        default=str(
            Path(__file__).resolve().parent.parent / "references" / "input-schema.json"
        ),
        help="Path to machine-readable input schema (recorded for traceability).",
    )
    parser.add_argument(
        "--output-schema",
        default=str(
            Path(__file__).resolve().parent.parent / "references" / "output-schema.json"
        ),
        help="Path to machine-readable output schema (recorded for traceability).",
    )
    parser.add_argument(
        "--allow-unconfirmed",
        action="store_true",
        help="Pass through simulation override to scorer.",
    )
    parser.add_argument(
        "--allow-single-option",
        action="store_true",
        help="Pass through simulation override to scorer.",
    )
    parser.add_argument(
        "--allow-nonisolated-evaluations",
        action="store_true",
        help="Pass through simulation override to scorer.",
    )
    return parser.parse_args()


def _build_score_cmd(
    *,
    score_script: Path,
    input_path: Path,
    report_path: Path,
    result_path: Path,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        sys.executable,
        str(score_script),
        "--input",
        str(input_path),
        "--output",
        str(report_path),
        "--json-output",
        str(result_path),
    ]
    if args.allow_unconfirmed:
        cmd.append("--allow-unconfirmed")
    if args.allow_single_option:
        cmd.append("--allow-single-option")
    if args.allow_nonisolated_evaluations:
        cmd.append("--allow-nonisolated-evaluations")
    return cmd


def _build_validate_cmd(
    *,
    validator_script: Path,
    schema_path: Path,
    data_path: Path,
) -> list[str]:
    return [
        "node",
        str(validator_script),
        "--schema",
        str(schema_path),
        "--data",
        str(data_path),
    ]


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    schema_path = Path(args.schema).resolve()
    if not schema_path.exists():
        raise SystemExit(f"Schema file not found: {schema_path}")
    output_schema_path = Path(args.output_schema).resolve()
    if not output_schema_path.exists():
        raise SystemExit(f"Output schema file not found: {output_schema_path}")

    input_sha = _sha256(input_path)
    schema_sha = _sha256(schema_path)
    output_schema_sha = _sha256(output_schema_path)
    run_id = args.run_id or f"run-{input_sha[:12]}"
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / f"{run_id}.analysis-report.md"
    result_path = output_dir / f"{run_id}.analysis-result.json"
    manifest_path = output_dir / f"{run_id}.manifest.json"

    score_script = Path(__file__).with_name("score_with_guardrails.py").resolve()
    validator_script = Path(__file__).with_name("validate_json_contract.mjs").resolve()
    cmd = _build_score_cmd(
        score_script=score_script,
        input_path=input_path,
        report_path=report_path,
        result_path=result_path,
        args=args,
    )

    input_validate_cmd = _build_validate_cmd(
        validator_script=validator_script,
        schema_path=schema_path,
        data_path=input_path,
    )
    input_validation = subprocess.run(
        input_validate_cmd,
        text=True,
        capture_output=True,
        check=False,
    )

    if input_validation.returncode != 0:
        manifest: dict[str, Any] = {
            "run_id": run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input": {
                "path": str(input_path),
                "sha256": input_sha,
            },
            "schema": {
                "path": str(schema_path),
                "sha256": schema_sha,
            },
            "output_schema": {
                "path": str(output_schema_path),
                "sha256": output_schema_sha,
            },
            "validator_script": str(validator_script),
            "validation": {
                "input": {
                    "command": input_validate_cmd,
                    "exit_code": input_validation.returncode,
                    "stderr": input_validation.stderr.strip(),
                }
            },
            "exit_code": input_validation.returncode,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if input_validation.stderr:
            print(input_validation.stderr, file=sys.stderr)
        print(f"Manifest: {manifest_path}")
        return input_validation.returncode

    completed = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )

    output_validate_cmd = _build_validate_cmd(
        validator_script=validator_script,
        schema_path=output_schema_path,
        data_path=result_path,
    )
    output_validation = subprocess.run(
        output_validate_cmd,
        text=True,
        capture_output=True,
        check=False,
    ) if completed.returncode == 0 else None

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": str(input_path),
            "sha256": input_sha,
        },
        "schema": {
            "path": str(schema_path),
            "sha256": schema_sha,
        },
        "output_schema": {
            "path": str(output_schema_path),
            "sha256": output_schema_sha,
        },
        "score_script": str(score_script),
        "validator_script": str(validator_script),
        "command": cmd,
        "validation": {
            "input": {
                "command": input_validate_cmd,
                "exit_code": input_validation.returncode,
                "stderr": input_validation.stderr.strip(),
            },
            "output": {
                "command": output_validate_cmd if output_validation else [],
                "exit_code": output_validation.returncode if output_validation else None,
                "stderr": output_validation.stderr.strip() if output_validation else "",
            },
        },
        "artifacts": {
            "report": str(report_path),
            "result_json": str(result_path),
        },
        "exit_code": (
            output_validation.returncode
            if output_validation is not None and output_validation.returncode != 0
            else completed.returncode
        ),
        "stderr": (
            output_validation.stderr.strip()
            if output_validation is not None and output_validation.returncode != 0
            else completed.stderr.strip()
        ),
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        print(f"Manifest: {manifest_path}")
        return completed.returncode

    if output_validation is not None and output_validation.returncode != 0:
        if output_validation.stderr:
            print(output_validation.stderr, file=sys.stderr)
        print(f"Manifest: {manifest_path}")
        return output_validation.returncode

    print(f"Report: {report_path}")
    print(f"Result JSON: {result_path}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
