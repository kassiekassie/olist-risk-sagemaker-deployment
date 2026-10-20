"""Invoke the final PAL endpoint and validate the live prediction contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3

from settings import ENDPOINT_NAME, EXPECTED_RESPONSE, REGION, SAMPLE_REQUEST


REQUIRED_RESPONSE_FIELDS = {
    "order_id",
    "risk_score",
    "risk_threshold",
    "predicted_class",
    "priority_review_flag",
    "model_version",
}


def validate_response(actual: dict, expected: dict) -> None:
    predictions = actual.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != 1:
        raise ValueError("Expected exactly one prediction")

    row = predictions[0]
    missing = sorted(REQUIRED_RESPONSE_FIELDS - set(row))
    if missing:
        raise ValueError(f"Response is missing fields: {missing}")

    expected_row = expected["predictions"][0]
    if row["order_id"] != expected_row["order_id"]:
        raise ValueError("Returned order_id does not match the test request")
    if abs(float(row["risk_score"]) - float(expected_row["risk_score"])) > 1e-9:
        raise ValueError("Cloud prediction does not match verified local inference")
    if row["model_version"] != expected_row["model_version"]:
        raise ValueError("Cloud model version does not match the expected version")
    if bool(row["priority_review_flag"]) != (
        float(row["risk_score"]) >= float(row["risk_threshold"])
    ):
        raise ValueError("priority_review_flag is inconsistent with the threshold")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, default=SAMPLE_REQUEST)
    parser.add_argument("--save-response", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.request.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_RESPONSE.read_text(encoding="utf-8"))

    print(f"Endpoint: {ENDPOINT_NAME}")
    print(f"Request: {args.request.name}")
    print(f"Instances: {len(payload.get('instances', []))}")
    print("Invoking SageMaker real-time endpoint...")

    response = boto3.client("sagemaker-runtime", region_name=REGION).invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(payload).encode("utf-8"),
    )
    result = json.loads(response["Body"].read().decode("utf-8"))
    validate_response(result, expected)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("Live cloud inference passed and matches local inference.")

    if args.save_response:
        args.save_response.parent.mkdir(parents=True, exist_ok=True)
        args.save_response.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Saved response: {args.save_response}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
