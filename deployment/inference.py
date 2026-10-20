"""Minimal inference entry point for local testing and SageMaker adaptation."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


def model_fn(model_dir: str):
    model_path = Path(model_dir)
    model = joblib.load(model_path / "model.joblib")

    with (model_path / "metadata.json").open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    catalog = pd.read_csv(model_path / "model_feature_catalog.csv")
    features = catalog["feature_name"].tolist()

    if len(features) != metadata["feature_count"]:
        raise ValueError("Feature catalog does not match model metadata")

    return {
        "model": model,
        "metadata": metadata,
        "features": features,
    }


def input_fn(request_body: str, content_type: str):
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise ValueError("Only application/json is supported")

    payload = json.loads(request_body)
    instances = payload.get("instances")

    if not isinstance(instances, list) or not instances:
        raise ValueError("Request must contain a non-empty instances list")
    if not all(isinstance(instance, dict) for instance in instances):
        raise ValueError("Every instance must be a JSON object")

    if "order_ids" in payload:
        order_ids = payload["order_ids"]
    elif "order_id" in payload and len(instances) == 1:
        order_ids = [payload["order_id"]]
    else:
        order_ids = [None] * len(instances)

    if not isinstance(order_ids, list) or len(order_ids) != len(instances):
        raise ValueError("order_ids must match the number of instances")

    return {"instances": instances, "order_ids": order_ids}


def predict_fn(input_data, model_bundle):
    features = model_bundle["features"]
    allowed = set(features)
    records = []

    for row_number, instance in enumerate(input_data["instances"], start=1):
        missing = [feature for feature in features if feature not in instance]
        unknown = sorted(set(instance) - allowed)

        if missing:
            raise ValueError(
                f"Instance {row_number} is missing required fields: {missing}"
            )
        if unknown:
            raise ValueError(
                f"Instance {row_number} contains unknown fields: {unknown}"
            )

        records.append({feature: instance[feature] for feature in features})

    frame = pd.DataFrame(records, columns=features)
    scores = model_bundle["model"].predict_proba(frame)[:, 1]
    metadata = model_bundle["metadata"]
    threshold = float(metadata["risk_threshold"])

    predictions = []
    for order_id, score in zip(input_data["order_ids"], scores):
        risk_score = float(score)
        flagged = risk_score >= threshold
        predictions.append(
            {
                "order_id": order_id,
                "risk_score": risk_score,
                "risk_threshold": threshold,
                "predicted_class": int(flagged),
                "priority_review_flag": bool(flagged),
                "model_version": metadata["model_version"],
            }
        )

    return {"predictions": predictions}


def output_fn(prediction, accept: str):
    if accept.split(";", 1)[0].strip().lower() != "application/json":
        raise ValueError("Only application/json responses are supported")
    return json.dumps(prediction, ensure_ascii=False), "application/json"
