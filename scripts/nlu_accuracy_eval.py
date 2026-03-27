"""
Run 10 NLU samples against the parse API and write a tracking CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SAMPLES = Path("scripts/nlu_eval_samples.json")
DEFAULT_OUTPUT = Path("docs/nlu_accuracy_tracking.csv")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value)).lower()


def normalize_list(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    return [normalize_text(item) for item in values if normalize_text(item)]


def score_exact(expected: Any, actual: Any) -> float:
    if expected in (None, "", []):
        return 1.0
    return 1.0 if normalize_text(expected) == normalize_text(actual) else 0.0


def score_list_coverage(expected: list[Any] | None, actual: list[Any] | None) -> float:
    expected_items = normalize_list(expected)
    if not expected_items:
        return 1.0

    actual_items = set(normalize_list(actual))
    matched = sum(1 for item in expected_items if item in actual_items)
    return matched / len(expected_items)


def score_years(expected: dict[str, Any], actual: dict[str, Any]) -> float:
    scores: list[float] = []

    if expected.get("years_exp_min") is not None:
        scores.append(score_exact(expected.get("years_exp_min"), actual.get("years_exp_min")))
    if expected.get("years_exp_max") is not None:
        scores.append(score_exact(expected.get("years_exp_max"), actual.get("years_exp_max")))

    return sum(scores) / len(scores) if scores else 1.0


def score_salary(expected: dict[str, Any], actual: dict[str, Any]) -> float:
    scores: list[float] = []

    if expected.get("salary_min") is not None:
        scores.append(score_exact(expected.get("salary_min"), actual.get("salary_min")))
    if expected.get("salary_max") is not None:
        scores.append(score_exact(expected.get("salary_max"), actual.get("salary_max")))

    return sum(scores) / len(scores) if scores else 1.0


def call_nlu_api(base_url: str, token: str, text: str) -> tuple[int, dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/nlu/parse"
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw_error": body}
        return exc.code, payload


def evaluate_sample(sample: dict[str, Any], actual_payload: dict[str, Any]) -> dict[str, Any]:
    expected = sample["expected"]
    draft = actual_payload.get("data", {}).get("job_requirement_draft", {})

    title_score = score_exact(expected.get("job_title"), draft.get("job_title"))
    skills_score = score_list_coverage(expected.get("skills"), draft.get("skills"))
    years_score = score_years(expected, draft)
    location_score = score_list_coverage(expected.get("location"), draft.get("location"))
    salary_score = score_salary(expected, draft)

    sample_accuracy = round(
        (title_score + skills_score + years_score + location_score + salary_score) / 5,
        4,
    )

    return {
        "sample_id": sample["id"],
        "text": sample["text"],
        "expected_job_title": expected.get("job_title"),
        "actual_job_title": draft.get("job_title"),
        "title_score": round(title_score, 4),
        "expected_skills": json.dumps(expected.get("skills", []), ensure_ascii=False),
        "actual_skills": json.dumps(draft.get("skills", []), ensure_ascii=False),
        "skills_score": round(skills_score, 4),
        "expected_years": f"{expected.get('years_exp_min')}|{expected.get('years_exp_max')}",
        "actual_years": f"{draft.get('years_exp_min')}|{draft.get('years_exp_max')}",
        "years_score": round(years_score, 4),
        "expected_locations": json.dumps(expected.get("location", []), ensure_ascii=False),
        "actual_locations": json.dumps(draft.get("location", []), ensure_ascii=False),
        "location_score": round(location_score, 4),
        "expected_salary": f"{expected.get('salary_min')}|{expected.get('salary_max')}",
        "actual_salary": f"{draft.get('salary_min')}|{draft.get('salary_max')}",
        "salary_score": round(salary_score, 4),
        "sample_accuracy": sample_accuracy,
        "http_status": 200,
        "error": "",
    }


def write_csv(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "text",
        "expected_job_title",
        "actual_job_title",
        "title_score",
        "expected_skills",
        "actual_skills",
        "skills_score",
        "expected_years",
        "actual_years",
        "years_score",
        "expected_locations",
        "actual_locations",
        "location_score",
        "expected_salary",
        "actual_salary",
        "salary_score",
        "sample_accuracy",
        "http_status",
        "error",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the NLU parse API against 10 canned samples.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost",
        help="Gateway or service root URL, for example http://localhost or http://localhost:8004",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Bearer access token returned by /api/v1/auth/login",
    )
    parser.add_argument(
        "--samples",
        default=str(DEFAULT_SAMPLES),
        help="Path to the JSON sample file",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to the generated CSV tracking file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    samples_path = Path(args.samples)
    output_path = Path(args.output)

    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    for sample in samples:
        status_code, payload = call_nlu_api(args.base_url, args.token, sample["text"])

        if status_code != 200:
            rows.append(
                {
                    "sample_id": sample["id"],
                    "text": sample["text"],
                    "expected_job_title": sample["expected"].get("job_title"),
                    "actual_job_title": "",
                    "title_score": 0,
                    "expected_skills": json.dumps(sample["expected"].get("skills", []), ensure_ascii=False),
                    "actual_skills": "[]",
                    "skills_score": 0,
                    "expected_years": f"{sample['expected'].get('years_exp_min')}|{sample['expected'].get('years_exp_max')}",
                    "actual_years": "",
                    "years_score": 0,
                    "expected_locations": json.dumps(sample["expected"].get("location", []), ensure_ascii=False),
                    "actual_locations": "[]",
                    "location_score": 0,
                    "expected_salary": f"{sample['expected'].get('salary_min')}|{sample['expected'].get('salary_max')}",
                    "actual_salary": "",
                    "salary_score": 0,
                    "sample_accuracy": 0,
                    "http_status": status_code,
                    "error": json.dumps(payload, ensure_ascii=False),
                }
            )
            continue

        rows.append(evaluate_sample(sample, payload))

    write_csv(output_path, rows)

    successful_rows = [row for row in rows if row["http_status"] == 200]
    average_accuracy = (
        sum(float(row["sample_accuracy"]) for row in successful_rows) / len(successful_rows)
        if successful_rows
        else 0.0
    )

    print(f"Output: {output_path}")
    print(f"Successful samples: {len(successful_rows)}/{len(rows)}")
    print(f"Average accuracy: {average_accuracy:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
