#!/usr/bin/env python3
"""Deterministic scoring with explicit discovery and evidence guardrails."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_MAJOR_PLATFORMS = ["chatgpt", "claude", "gemini", "copilot"]
DEFAULT_BLEND = {"major_platform_average": 0.6, "current_platform": 0.4}
DEFAULT_RULES = {
    "select_min": 80.0,
    "select_margin": 7.0,
    "compose_min": 70.0,
    "compose_margin": 7.0,
    "improve_min": 55.0,
    "extend_gap": 10.0,
    "min_coverage": 0.8,
}
ALLOWED_CONFIRMATION_SOURCES = {
    "user-confirmed",
    "provided-input",
    "yolo-mode",
}
EFFORT_ORDER = {"s": 0, "m": 1, "l": 2}
RISK_ORDER = {"low": 0, "med": 1, "medium": 1, "high": 2}
SCORER_VERSION = "1.3.0"
RULES_VERSION = "2026-04-18"


def _to_float(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected numeric value for '{field}', got {value!r}") from exc
    if math.isnan(number) or math.isinf(number):
        raise ValueError(f"Invalid numeric value for '{field}': {value!r}")
    return number


def _normalize_score_scale(value: Any) -> str:
    raw = str(value or "0-100").strip().lower()
    if raw not in {"0-100", "1-5"}:
        raise ValueError("score_scale must be '0-100' or '1-5'")
    return raw


def _to_percent_score(value: Any, score_scale: str, field: str) -> float:
    score = _to_float(value, field)
    if score_scale == "1-5":
        score = score * 20.0
    return min(100.0, max(0.0, score))


def _normalize_blend(weights: dict[str, Any] | None) -> dict[str, float]:
    source = dict(DEFAULT_BLEND)
    if isinstance(weights, dict):
        source.update(weights)

    major = _to_float(source.get("major_platform_average"), "weights.major_platform_average")
    current = _to_float(source.get("current_platform"), "weights.current_platform")
    if major < 0 or current < 0:
        raise ValueError("Blend weights must be non-negative")
    if major + current <= 0:
        raise ValueError("Blend weights must sum to a positive value")

    total = major + current
    return {
        "major_platform_average": major / total,
        "current_platform": current / total,
    }


def _normalize_rules(rules: dict[str, Any] | None) -> dict[str, float]:
    source = dict(DEFAULT_RULES)
    if isinstance(rules, dict):
        source.update(rules)

    normalized: dict[str, float] = {}
    for key, value in source.items():
        normalized[key] = _to_float(value, f"recommendation_rules.{key}")

    min_coverage = normalized["min_coverage"]
    if min_coverage < 0 or min_coverage > 1:
        raise ValueError("recommendation_rules.min_coverage must be between 0 and 1")
    return normalized


def _normalize_confirmation_source(
    *,
    criteria_confirmed: Any,
    source: Any,
    allow_unconfirmed: bool,
) -> str:
    if criteria_confirmed is not True:
        if not allow_unconfirmed:
            raise ValueError("criteria_confirmed must be true before scoring")
        return "simulation-unconfirmed"

    normalized = str(source or "").strip().lower()
    if not normalized:
        raise ValueError(
            "criteria_confirmation_source is required when criteria_confirmed is true"
        )
    if normalized not in ALLOWED_CONFIRMATION_SOURCES:
        allowed = ", ".join(sorted(ALLOWED_CONFIRMATION_SOURCES))
        raise ValueError(
            "criteria_confirmation_source must be one of: "
            f"{allowed}"
        )
    return normalized


def _normalize_criteria(criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not criteria:
        raise ValueError("At least one criterion is required")

    normalized: list[dict[str, Any]] = []
    total_weight = 0.0
    seen_ids: set[str] = set()

    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            raise ValueError(f"criteria[{index}] must be an object")

        criterion_id = str(criterion.get("id", "")).strip()
        if not criterion_id:
            raise ValueError(f"criteria[{index}].id is required")
        if criterion_id in seen_ids:
            raise ValueError(f"Duplicate criterion id '{criterion_id}'")
        seen_ids.add(criterion_id)

        name = str(criterion.get("name", "")).strip()
        metric = str(criterion.get("metric", "")).strip()
        data_source = str(criterion.get("data_source", "")).strip()
        scoring_rule = str(criterion.get("scoring_rule", "")).strip()
        if not name:
            raise ValueError(f"criteria[{index}].name is required")
        if not metric:
            raise ValueError(f"criteria[{index}].metric is required")
        if not data_source:
            raise ValueError(f"criteria[{index}].data_source is required")
        if not scoring_rule:
            raise ValueError(f"criteria[{index}].scoring_rule is required")

        weight = _to_float(criterion.get("weight", 0.0), f"criteria[{index}].weight")
        if weight < 0:
            raise ValueError(f"criteria[{index}].weight must be non-negative")

        total_weight += weight
        normalized.append(
            {
                "id": criterion_id,
                "name": name,
                "weight": weight,
                "metric": metric,
                "data_source": data_source,
                "scoring_rule": scoring_rule,
            }
        )

    if total_weight <= 0:
        raise ValueError("Sum of criterion weights must be greater than zero")

    for criterion in normalized:
        criterion["weight"] = criterion["weight"] / total_weight

    return normalized


def _normalize_alternatives(
    alternatives: Any, *, allow_single_option: bool
) -> list[dict[str, Any]]:
    if not isinstance(alternatives, list) or not alternatives:
        raise ValueError("alternatives must be a non-empty array")
    if len(alternatives) < 2 and not allow_single_option:
        raise ValueError(
            "At least two alternatives are required for scoring; run discovery first "
            "or use --allow-single-option for simulation only."
        )

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, alt in enumerate(alternatives):
        if not isinstance(alt, dict):
            raise ValueError(f"alternatives[{index}] must be an object")

        alt_id = str(alt.get("id", "")).strip()
        if not alt_id:
            raise ValueError(f"alternatives[{index}].id is required")
        if alt_id in seen_ids:
            raise ValueError(f"Duplicate alternative id '{alt_id}'")
        seen_ids.add(alt_id)

        name = str(alt.get("name", alt_id)).strip() or alt_id
        alt_type = str(alt.get("type", "internal")).strip()
        if alt_type not in {"internal", "compose", "external", "build-new"}:
            raise ValueError(
                f"alternatives[{index}].type must be one of internal|compose|external|build-new"
            )
        effort = str(alt.get("effort", "")).strip()
        risk = str(alt.get("risk", "")).strip()
        justification = str(alt.get("justification", "")).strip()
        if not justification:
            raise ValueError(f"alternatives[{index}].justification is required")

        scores = alt.get("scores", {})
        if not isinstance(scores, dict):
            raise ValueError(f"alternatives[{index}].scores must be an object")

        evidence = alt.get("evidence", [])
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            raise ValueError(f"alternatives[{index}].evidence must be an array when provided")

        feasible = bool(alt.get("feasible", True))
        normalized.append(
            {
                "id": alt_id,
                "name": name,
                "type": alt_type,
                "effort": effort,
                "risk": risk,
                "feasible": feasible,
                "scores": scores,
                "evidence": evidence,
                "justification": justification,
                "notes": alt.get("notes", ""),
            }
        )

    return normalized


def _normalize_discovery(
    discovery: Any,
    alternatives: list[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(discovery, dict):
        raise ValueError("discovery object is required")

    external_done = bool(discovery.get("external_discovery_done", False))
    external_blocked = bool(discovery.get("external_discovery_blocked", False))
    block_reason = str(discovery.get("block_reason", "")).strip()
    checked_at = str(discovery.get("checked_at", "")).strip()

    if not external_done and not external_blocked:
        raise ValueError(
            "discovery must either complete external discovery or explicitly block it with reason"
        )
    if external_blocked and not block_reason:
        raise ValueError("discovery.block_reason is required when external discovery is blocked")

    has_external = any(alt["type"] == "external" for alt in alternatives)
    if external_done and not has_external:
        raise ValueError(
            "external discovery was marked complete but no alternative with type 'external' was provided"
        )

    return {
        "external_discovery_done": external_done,
        "external_discovery_blocked": external_blocked,
        "block_reason": block_reason,
        "checked_at": checked_at,
    }


def _normalize_independent_evaluations(
    records: Any,
    alternatives: list[dict[str, Any]],
    *,
    allow_nonisolated_evaluations: bool,
) -> list[dict[str, Any]]:
    alternative_ids = [alt["id"] for alt in alternatives]
    alternative_id_set = set(alternative_ids)

    if records is None and allow_nonisolated_evaluations:
        return []

    if not isinstance(records, list) or not records:
        raise ValueError(
            "independent_evaluations must be a non-empty array with one record per alternative"
        )

    by_alternative: dict[str, dict[str, Any]] = {}
    evaluator_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"independent_evaluations[{index}] must be an object")

        alternative_id = str(record.get("alternative_id", "")).strip()
        evaluator_id = str(record.get("evaluator_id", "")).strip()
        summary = str(record.get("summary", "")).strip()
        isolation_confirmed = record.get("isolation_confirmed")

        if not alternative_id:
            raise ValueError(f"independent_evaluations[{index}].alternative_id is required")
        if alternative_id not in alternative_id_set:
            raise ValueError(
                f"independent_evaluations[{index}] references unknown alternative '{alternative_id}'"
            )
        if alternative_id in by_alternative:
            raise ValueError(
                f"independent_evaluations has duplicate record for alternative '{alternative_id}'"
            )

        if not evaluator_id:
            raise ValueError(f"independent_evaluations[{index}].evaluator_id is required")
        if evaluator_id in evaluator_ids:
            raise ValueError(
                "independent_evaluations evaluator_id values must be unique; "
                f"duplicate '{evaluator_id}'"
            )
        evaluator_ids.add(evaluator_id)

        if isolation_confirmed is not True:
            raise ValueError(
                f"independent_evaluations[{index}].isolation_confirmed must be true"
            )
        if not summary:
            raise ValueError(f"independent_evaluations[{index}].summary is required")

        evidence_refs = record.get("evidence_refs", [])
        if evidence_refs is None:
            evidence_refs = []
        if not isinstance(evidence_refs, list):
            raise ValueError(
                f"independent_evaluations[{index}].evidence_refs must be an array when provided"
            )

        by_alternative[alternative_id] = {
            "alternative_id": alternative_id,
            "evaluator_id": evaluator_id,
            "isolation_confirmed": True,
            "summary": summary,
            "evidence_refs": [str(ref).strip() for ref in evidence_refs if str(ref).strip()],
        }

    missing = [alt_id for alt_id in alternative_ids if alt_id not in by_alternative]
    if missing:
        raise ValueError(
            "independent_evaluations must include every alternative; missing: "
            + ", ".join(missing)
        )

    return [by_alternative[alt_id] for alt_id in alternative_ids]


def _effort_rank(value: Any) -> int:
    key = str(value or "").strip().lower()
    return EFFORT_ORDER.get(key, 9)


def _risk_rank(value: Any) -> int:
    key = str(value or "").strip().lower()
    return RISK_ORDER.get(key, 9)


def _platform_score(
    alternative: dict[str, Any],
    platform: str,
    criteria: list[dict[str, Any]],
    score_scale: str,
) -> tuple[float, int, float]:
    scores_by_platform = alternative.get("scores", {})
    platform_scores = scores_by_platform.get(platform, {})
    if platform_scores is None:
        platform_scores = {}
    if not isinstance(platform_scores, dict):
        raise ValueError(
            f"Alternative '{alternative['id']}' has non-object scores for platform '{platform}'"
        )

    numerator = 0.0
    covered_weight = 0.0
    missing = 0
    for criterion in criteria:
        criterion_id = criterion["id"]
        raw = platform_scores.get(criterion_id)
        if raw is None:
            missing += 1
            continue
        score = _to_percent_score(
            raw,
            score_scale,
            f"alternatives[{alternative['id']}].scores.{platform}.{criterion_id}",
        )
        weight = criterion["weight"]
        numerator += weight * score
        covered_weight += weight

    coverage = covered_weight
    weighted_score = numerator / covered_weight if covered_weight > 0 else 0.0
    return weighted_score, missing, coverage


def _recommend(
    ranked: list[dict[str, Any]],
    rules: dict[str, float],
) -> dict[str, Any]:
    feasible = [item for item in ranked if item["feasible"]]
    if not feasible:
        top = ranked[0]
        return {
            "action": "build-new",
            "chosen_option_ids": [],
            "top_option_id": top["id"],
            "score_margin_vs_second": 0.0,
            "reason": "All discovered alternatives are infeasible; discover additional options or build new.",
            "rules": rules,
        }

    best = feasible[0]
    second = feasible[1] if len(feasible) > 1 else None
    margin = best["overall_success_score"] - second["overall_success_score"] if second else 0.0

    best_coverage_ok = best["coverage"] >= rules["min_coverage"]
    second_coverage_ok = bool(second and second["coverage"] >= rules["min_coverage"])

    if len(feasible) < 2:
        if best["overall_success_score"] >= rules["improve_min"]:
            return {
                "action": "improve",
                "chosen_option_ids": [best["id"]],
                "top_option_id": best["id"],
                "score_margin_vs_second": 0.0,
                "reason": (
                    "Only one feasible alternative remains; do not use margin-based select. "
                    "Run additional discovery."
                ),
                "rules": rules,
            }
        return {
            "action": "build-new",
            "chosen_option_ids": [],
            "top_option_id": best["id"],
            "score_margin_vs_second": 0.0,
            "reason": "Single feasible option is below viability threshold.",
            "rules": rules,
        }

    if (
        best["overall_success_score"] >= rules["select_min"]
        and margin >= rules["select_margin"]
        and best_coverage_ok
    ):
        return {
            "action": "select",
            "chosen_option_ids": [best["id"]],
            "top_option_id": best["id"],
            "score_margin_vs_second": round(margin, 2),
            "reason": (
                f"Top feasible option exceeds select threshold and margin ({margin:.2f}) "
                "with sufficient coverage."
            ),
            "rules": rules,
        }

    if (
        best["overall_success_score"] >= rules["compose_min"]
        and margin < rules["compose_margin"]
        and best_coverage_ok
        and second_coverage_ok
    ):
        return {
            "action": "compose",
            "chosen_option_ids": [best["id"], second["id"]],
            "top_option_id": best["id"],
            "score_margin_vs_second": round(margin, 2),
            "reason": (
                "Top two feasible options are strong, close, and both satisfy coverage gate."
            ),
            "rules": rules,
        }

    if best["overall_success_score"] >= rules["improve_min"]:
        if not best_coverage_ok:
            reason = "Top feasible option is viable but coverage is below gate; improve evidence first."
        elif (best["major_platform_average"] - best["current_platform_score"]) >= rules["extend_gap"]:
            reason = (
                "Top feasible option performs better across major platforms than current platform; "
                "extend current-platform support."
            )
            return {
                "action": "extend",
                "chosen_option_ids": [best["id"]],
                "top_option_id": best["id"],
                "score_margin_vs_second": round(margin, 2),
                "reason": reason,
                "rules": rules,
            }
        else:
            reason = "Top feasible option is viable but below direct-select threshold."
        return {
            "action": "improve",
            "chosen_option_ids": [best["id"]],
            "top_option_id": best["id"],
            "score_margin_vs_second": round(margin, 2),
            "reason": reason,
            "rules": rules,
        }

    return {
        "action": "build-new",
        "chosen_option_ids": [],
        "top_option_id": best["id"],
        "score_margin_vs_second": round(margin, 2),
        "reason": "No feasible option meets minimum viability threshold.",
        "rules": rules,
    }


def _decision_status(action: str) -> str:
    if action in {"select", "compose", "extend", "build-new"}:
        return "proceed"
    if action == "improve":
        return "defer"
    return "no-go"


def _evaluate(
    data: dict[str, Any],
    *,
    allow_unconfirmed: bool,
    allow_single_option: bool,
    allow_nonisolated_evaluations: bool,
) -> dict[str, Any]:
    decision = (
        str(data.get("decision", "Comparative decision analysis")).strip()
        or "Comparative decision analysis"
    )
    run_id = str(data.get("run_id", "")).strip()
    if not run_id:
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    criteria_confirmed = data.get("criteria_confirmed")
    criteria_confirmation_source = _normalize_confirmation_source(
        criteria_confirmed=criteria_confirmed,
        source=data.get("criteria_confirmation_source"),
        allow_unconfirmed=allow_unconfirmed,
    )

    current_platform = str(data.get("current_platform", "")).strip()
    if not current_platform:
        raise ValueError("current_platform is required")

    major_platforms = data.get("major_platforms") or list(DEFAULT_MAJOR_PLATFORMS)
    if not isinstance(major_platforms, list) or not major_platforms:
        raise ValueError("major_platforms must be a non-empty array")
    major_platforms = [str(p).strip() for p in major_platforms if str(p).strip()]
    if not major_platforms:
        raise ValueError("major_platforms must include at least one non-empty platform name")

    score_scale = _normalize_score_scale(data.get("score_scale"))
    criteria = _normalize_criteria(data.get("criteria") or [])
    alternatives = _normalize_alternatives(
        data.get("alternatives"),
        allow_single_option=allow_single_option,
    )
    discovery = _normalize_discovery(data.get("discovery"), alternatives)
    independent_evaluations = _normalize_independent_evaluations(
        data.get("independent_evaluations"),
        alternatives,
        allow_nonisolated_evaluations=allow_nonisolated_evaluations,
    )
    blend = _normalize_blend(data.get("weights"))
    rules = _normalize_rules(data.get("recommendation_rules"))

    required_platforms = sorted(set(major_platforms + [current_platform]))
    expected_values = len(criteria) * len(required_platforms)

    results = []
    for alternative in alternatives:
        per_platform: dict[str, tuple[float, int, float]] = {}
        for platform in required_platforms:
            per_platform[platform] = _platform_score(alternative, platform, criteria, score_scale)

        major_scores = [per_platform[p][0] for p in major_platforms]
        current_score = per_platform[current_platform][0]
        major_average = sum(major_scores) / len(major_scores)
        overall = (
            blend["major_platform_average"] * major_average
            + blend["current_platform"] * current_score
        )

        missing_values = sum(missing for _, missing, _ in per_platform.values())
        coverage = sum(cov for _, _, cov in per_platform.values()) / len(required_platforms)
        coverage = max(0.0, min(1.0, coverage))
        count_coverage = 1.0 - (missing_values / expected_values if expected_values else 0.0)
        count_coverage = max(0.0, min(1.0, count_coverage))

        platform_scores = {p: round(per_platform[p][0], 2) for p in required_platforms}

        results.append(
            {
                "id": alternative["id"],
                "name": alternative["name"],
                "type": alternative["type"],
                "effort": alternative["effort"],
                "risk": alternative["risk"],
                "effort_rank": _effort_rank(alternative["effort"]),
                "risk_rank": _risk_rank(alternative["risk"]),
                "feasible": alternative["feasible"],
                "justification": alternative["justification"],
                "platform_scores": platform_scores,
                "major_platform_average": round(major_average, 2),
                "current_platform_score": round(current_score, 2),
                "overall_success_score": round(overall, 2),
                "coverage": round(coverage, 3),
                "count_coverage": round(count_coverage, 3),
                "missing_values": missing_values,
                "notes": alternative.get("notes", ""),
            }
        )

    ranked = sorted(
        results,
        key=lambda item: (
            not item["feasible"],
            -item["overall_success_score"],
            -item["current_platform_score"],
            -item["major_platform_average"],
            item["effort_rank"],
            item["risk_rank"],
            item["name"].lower(),
        ),
    )
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank

    recommendation = _recommend(ranked, rules)
    action = recommendation["action"]
    return {
        "run_id": run_id,
        "scorer_version": SCORER_VERSION,
        "rules_version": RULES_VERSION,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "decision_status": _decision_status(action),
        "criteria_confirmed": bool(criteria_confirmed),
        "criteria_confirmation_source": criteria_confirmation_source,
        "score_scale": score_scale,
        "current_platform": current_platform,
        "major_platforms": major_platforms,
        "criteria": criteria,
        "discovery": discovery,
        "independent_evaluations": independent_evaluations,
        "weights": blend,
        "ranked_alternatives": ranked,
        "recommendation": recommendation,
    }


def _markdown_report(result: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Comparative Decision Analysis: {result['decision']}")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Run id: `{result['run_id']}`")
    lines.append(f"- Scorer version: `{result['scorer_version']}`")
    lines.append(f"- Rules version: `{result['rules_version']}`")
    lines.append(f"- Evaluated at: `{result['evaluated_at']}`")
    lines.append(f"- Criteria confirmed: `{result['criteria_confirmed']}`")
    lines.append(
        f"- Criteria confirmation source: `{result['criteria_confirmation_source']}`"
    )
    lines.append(f"- Score scale: `{result['score_scale']}`")
    lines.append(f"- Current platform: `{result['current_platform']}`")
    lines.append("- Major platforms: " + ", ".join(result["major_platforms"]))
    lines.append(
        "- Independent evaluations recorded: "
        f"`{len(result['independent_evaluations'])}`"
    )
    lines.append(
        "- External discovery: "
        f"done=`{result['discovery']['external_discovery_done']}` blocked=`{result['discovery']['external_discovery_blocked']}`"
    )
    if result["discovery"]["block_reason"]:
        lines.append(f"- Discovery block reason: {result['discovery']['block_reason']}")
    lines.append("")
    lines.append("## Criteria")
    lines.append("")
    lines.append("| Criterion | Weight | Metric | Data Source | Scoring Rule |")
    lines.append("|---|---:|---|---|---|")
    for criterion in result["criteria"]:
        lines.append(
            f"| {criterion['name']} (`{criterion['id']}`) | {criterion['weight']:.3f} | "
            f"{criterion['metric']} | {criterion['data_source']} | {criterion['scoring_rule']} |"
        )
    lines.append("")
    lines.append("## Ranked Alternatives")
    lines.append("")
    lines.append(
        "| Rank | Option | Type | Feasible | Effort | Risk | Major Avg | "
        f"Current ({result['current_platform']}) | Overall | Coverage | Missing | Justification |"
    )
    lines.append("|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---|")
    for item in result["ranked_alternatives"]:
        lines.append(
            f"| {item['rank']} | {item['name']} (`{item['id']}`) | {item['type']} | "
            f"{'yes' if item['feasible'] else 'no'} | {item['effort'] or '-'} | {item['risk'] or '-'} | "
            f"{item['major_platform_average']:.2f} | {item['current_platform_score']:.2f} | "
            f"{item['overall_success_score']:.2f} | {item['coverage']:.3f} | {item['missing_values']} | "
            f"{item['justification']} |"
        )
    lines.append("")
    lines.append("## Independent Evaluations")
    lines.append("")
    if result["independent_evaluations"]:
        lines.append("| Alternative | Evaluator | Isolation Confirmed | Summary |")
        lines.append("|---|---|---|---|")
        for record in result["independent_evaluations"]:
            lines.append(
                f"| `{record['alternative_id']}` | `{record['evaluator_id']}` | "
                f"{'yes' if record['isolation_confirmed'] else 'no'} | {record['summary']} |"
            )
    else:
        lines.append("- Not provided (simulation override).")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    rec = result["recommendation"]
    chosen = ", ".join(rec["chosen_option_ids"]) if rec["chosen_option_ids"] else "none"
    lines.append(f"- Decision status: `{result['decision_status']}`")
    lines.append(f"- Action: **{rec['action']}**")
    lines.append(f"- Chosen option(s): `{chosen}`")
    lines.append(f"- Top option: `{rec['top_option_id']}`")
    lines.append(f"- Margin vs second: {rec['score_margin_vs_second']:.2f}")
    lines.append(f"- Reason: {rec['reason']}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- Blend weights: major_platform_average="
        f"{result['weights']['major_platform_average']:.3f}, "
        f"current_platform={result['weights']['current_platform']:.3f}"
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score alternatives with comparative decision guardrails."
    )
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--output", help="Path to markdown report output")
    parser.add_argument("--json-output", help="Path to JSON report output")
    parser.add_argument(
        "--allow-unconfirmed",
        action="store_true",
        help="Allow scoring when criteria_confirmed is false (simulation only).",
    )
    parser.add_argument(
        "--allow-single-option",
        action="store_true",
        help="Allow scoring one alternative (simulation only).",
    )
    parser.add_argument(
        "--allow-nonisolated-evaluations",
        action="store_true",
        help=(
            "Allow scoring without independent evaluator records "
            "(simulation only)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    result = _evaluate(
        data,
        allow_unconfirmed=args.allow_unconfirmed,
        allow_single_option=args.allow_single_option,
        allow_nonisolated_evaluations=args.allow_nonisolated_evaluations,
    )
    report = _markdown_report(result)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    else:
        print(report)

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
