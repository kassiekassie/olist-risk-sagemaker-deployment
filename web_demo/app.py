"""Local customer-care dashboard backed by SageMaker real-time inference.

The browser never receives AWS credentials. This server accepts one delivered-
order JSON request, invokes the private SageMaker endpoint, and converts the
model output into a proposed service-routing decision. It does not persist
cases, write to a queue or contact customers.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from flask import Flask, jsonify, render_template, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from deployment.settings import ENDPOINT_NAME, REGION, SAMPLE_REQUEST  # noqa: E402


FEATURE_CATALOG = PROJECT_ROOT / "final_model" / "model_feature_catalog.csv"
REQUIRED_RESPONSE_FIELDS = {
    "order_id",
    "risk_score",
    "risk_threshold",
    "predicted_class",
    "priority_review_flag",
    "model_version",
}


def _load_required_features() -> list[str]:
    with FEATURE_CATALOG.open(encoding="utf-8", newline="") as file:
        return [row["feature_name"] for row in csv.DictReader(file)]


REQUIRED_FEATURES = _load_required_features()
app = Flask(__name__)


def _client_error_message(error: ClientError) -> str:
    details = error.response.get("Error", {})
    code = details.get("Code", "AWS error")
    message = details.get("Message", "The AWS service rejected the request.")
    return f"{code}: {message}"


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    instances = payload.get("instances")
    if not isinstance(instances, list) or len(instances) != 1:
        raise ValueError("The dashboard accepts exactly one item in 'instances'.")
    if not isinstance(instances[0], dict):
        raise ValueError("The item in 'instances' must be a JSON object.")

    order_id = payload.get("order_id")
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("A non-empty 'order_id' is required for service routing.")

    row = instances[0]
    required = set(REQUIRED_FEATURES)
    missing = [feature for feature in REQUIRED_FEATURES if feature not in row]
    unknown = sorted(set(row) - required)
    if missing:
        raise ValueError(f"Missing required feature(s): {', '.join(missing)}")
    if unknown:
        raise ValueError(f"Unknown feature(s): {', '.join(unknown)}")
    return payload


def validate_prediction(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("SageMaker returned an invalid response object.")
    predictions = result.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != 1:
        raise ValueError("SageMaker must return exactly one prediction.")

    prediction = predictions[0]
    if not isinstance(prediction, dict):
        raise ValueError("The prediction must be a JSON object.")
    missing = sorted(REQUIRED_RESPONSE_FIELDS - set(prediction))
    if missing:
        raise ValueError(f"Prediction is missing field(s): {', '.join(missing)}")

    prediction["risk_score"] = float(prediction["risk_score"])
    prediction["risk_threshold"] = float(prediction["risk_threshold"])
    prediction["predicted_class"] = int(prediction["predicted_class"])
    prediction["priority_review_flag"] = bool(prediction["priority_review_flag"])
    expected_flag = prediction["risk_score"] >= prediction["risk_threshold"]
    if prediction["priority_review_flag"] != expected_flag:
        raise ValueError("Priority flag is inconsistent with the model threshold.")
    return prediction


def build_request_summary(payload: dict[str, Any]) -> dict[str, Any]:
    row = payload["instances"][0]
    return {
        "order_id": payload["order_id"],
        "delay_days": float(row["delay_days"]),
        "late_delivery": bool(row["late_delivery_flag"]),
        "order_value": float(row["total_payment_value"]),
        "category": str(row["main_category"]),
        "customer_state": str(row["customer_state"]),
        "seller_state": str(row["main_seller_state"]),
        "cross_state": bool(row["customer_seller_cross_state_flag"]),
    }


def build_business_decision(prediction: dict[str, Any]) -> dict[str, Any]:
    if prediction["priority_review_flag"]:
        return {
            "risk_band": "HIGH",
            "queue": "Customer Care — Priority Review",
            "headline": "Prioritise this order for human review",
            "summary": (
                "The score crossed the operating threshold. A customer-care "
                "specialist should review the delivery context before deciding "
                "whether proactive outreach is appropriate."
            ),
            "actions": [
                {
                    "step": "01",
                    "title": "Review delivery context",
                    "detail": "Check delay, route and order-value signals supplied at delivery confirmation.",
                },
                {
                    "step": "02",
                    "title": "Assess customer-care response",
                    "detail": "A human agent decides whether proactive contact or a service-recovery option is appropriate.",
                },
                {
                    "step": "03",
                    "title": "Record the operational outcome",
                    "detail": "Use the team's existing process; this demo does not create or persist a case.",
                },
            ],
        }

    return {
        "risk_band": "STANDARD",
        "queue": "Standard Monitoring",
        "headline": "Continue through the standard service flow",
        "summary": (
            "The score is below the operating threshold. No priority-review "
            "routing is recommended by the model."
        ),
        "actions": [
            {
                "step": "01",
                "title": "Retain standard monitoring",
                "detail": "Keep the order in the normal post-delivery service workflow.",
            },
            {
                "step": "02",
                "title": "Respond to customer signals",
                "detail": "Escalate only if new operational or customer feedback requires attention.",
            },
            {
                "step": "03",
                "title": "Review aggregate performance",
                "detail": "Use model monitoring outside this demo to review routing quality over time.",
            },
        ],
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        endpoint_name=ENDPOINT_NAME,
        region=REGION,
        feature_count=len(REQUIRED_FEATURES),
    )


@app.get("/api/sample")
def sample_request():
    return jsonify(json.loads(SAMPLE_REQUEST.read_text(encoding="utf-8")))


@app.get("/api/endpoint-status")
def endpoint_status():
    try:
        response = boto3.client("sagemaker", region_name=REGION).describe_endpoint(
            EndpointName=ENDPOINT_NAME
        )
        return jsonify(
            {
                "endpoint_name": ENDPOINT_NAME,
                "region": REGION,
                "status": response["EndpointStatus"],
            }
        )
    except NoCredentialsError:
        return jsonify(
            {
                "endpoint_name": ENDPOINT_NAME,
                "region": REGION,
                "status": "CredentialsMissing",
                "detail": "Local AWS credentials are not available.",
            }
        )
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        return jsonify(
            {
                "endpoint_name": ENDPOINT_NAME,
                "region": REGION,
                "status": "NotCreated" if code == "ValidationException" else "Unavailable",
                "detail": _client_error_message(error),
            }
        )
    except BotoCoreError as error:
        return jsonify(
            {
                "endpoint_name": ENDPOINT_NAME,
                "region": REGION,
                "status": "Unavailable",
                "detail": str(error),
            }
        )


@app.post("/api/predict")
def predict():
    started = time.perf_counter()
    try:
        payload = validate_payload(request.get_json(silent=True))
        response = boto3.client(
            "sagemaker-runtime", region_name=REGION
        ).invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Accept="application/json",
            Body=json.dumps(payload).encode("utf-8"),
        )
        result = json.loads(response["Body"].read().decode("utf-8"))
        prediction = validate_prediction(result)
    except ValueError as error:
        return jsonify({"error": "Invalid request", "detail": str(error)}), 400
    except NoCredentialsError:
        return (
            jsonify(
                {
                    "error": "AWS credentials unavailable",
                    "detail": "Sign in to AWS locally before running live inference.",
                }
            ),
            503,
        )
    except ClientError as error:
        return (
            jsonify(
                {
                    "error": "SageMaker invocation failed",
                    "detail": _client_error_message(error),
                }
            ),
            502,
        )
    except (BotoCoreError, json.JSONDecodeError) as error:
        return (
            jsonify(
                {
                    "error": "SageMaker response unavailable",
                    "detail": str(error),
                }
            ),
            502,
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return jsonify(
        {
            "prediction": prediction,
            "business_decision": build_business_decision(prediction),
            "request_summary": build_request_summary(payload),
            "runtime": {
                "endpoint_name": ENDPOINT_NAME,
                "region": REGION,
                "latency_ms": elapsed_ms,
                "source": "Amazon SageMaker real-time endpoint",
            },
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PAL_DASHBOARD_PORT", "5056"))
    app.run(host="127.0.0.1", port=port, debug=False)
