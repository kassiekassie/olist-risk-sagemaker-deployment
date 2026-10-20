"""Run one verified end-to-end inference without AWS credentials."""

from __future__ import annotations

import json
from pathlib import Path

from inference import input_fn, model_fn, output_fn, predict_fn


HANDOFF_ROOT = Path(__file__).resolve().parents[1]


def main():
    model_bundle = model_fn(str(HANDOFF_ROOT / "final_model"))
    request_body = (HANDOFF_ROOT / "sample_request.json").read_text(
        encoding="utf-8"
    )
    expected = json.loads(
        (HANDOFF_ROOT / "expected_response.json").read_text(encoding="utf-8")
    )

    parsed_request = input_fn(request_body, "application/json")
    prediction = predict_fn(parsed_request, model_bundle)
    response_body, _ = output_fn(prediction, "application/json")
    actual = json.loads(response_body)

    expected_row = expected["predictions"][0]
    actual_row = actual["predictions"][0]

    assert actual_row["order_id"] == expected_row["order_id"]
    assert abs(actual_row["risk_score"] - expected_row["risk_score"]) < 1e-9
    assert actual_row["risk_threshold"] == expected_row["risk_threshold"]
    assert actual_row["predicted_class"] == expected_row["predicted_class"]
    assert actual_row["priority_review_flag"] is True
    assert actual_row["model_version"] == expected_row["model_version"]

    print(json.dumps(actual, indent=2, ensure_ascii=False))
    print("Local inference verification passed")


if __name__ == "__main__":
    main()
