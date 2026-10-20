# Risk Prediction API Specification

## Purpose

The API scores bad-review risk immediately after an order is confirmed as delivered. It uses only structured information available by that point. Review text, review score, derived complaint topics and the final outcome label are prohibited inputs.

## Serving interface

- Service: Amazon SageMaker real-time inference endpoint
- Endpoint name: `olist-risk-final-v2-endpoint`
- Region: `ap-southeast-1`
- Request content type: `application/json`
- Response content type: `application/json`

## Request

The body must contain a non-empty `instances` list. A single request supplies `order_id`; a multi-row request supplies an `order_ids` list with the same length as `instances`.

The complete verified request is stored in `sample_request.json`.

```json
{
  "order_id": "ae3818a9067c10088e84a13bceaa9b68",
  "instances": [
    {
      "purchase_year": 2018,
      "purchase_month": 2,
      "delay_days": 13.994189814814815,
      "customer_state": "RJ",
      "main_category": "computers_accessories"
    }
  ]
}
```

The example above is abbreviated. A valid request contains all 47 fields listed in `final_model/model_feature_catalog.csv`.

## Successful response

```json
{
  "predictions": [
    {
      "order_id": "ae3818a9067c10088e84a13bceaa9b68",
      "risk_score": 0.9756467938423157,
      "risk_threshold": 0.5906863212585449,
      "predicted_class": 1,
      "priority_review_flag": true,
      "model_version": "v1.0-project-demo"
    }
  ]
}
```

`risk_score` is an uncalibrated model ranking score. It must not be described as a literal 97.56% probability of a bad review.

## Validation rules

- Reject a missing or empty `instances` list.
- Reject a non-object instance.
- Reject missing required features.
- Reject unknown features.
- Reject `order_ids` whose length differs from `instances`.
- Accept and return only JSON.

The current SageMaker container logs clear validation details, but some invalid requests may surface to the caller as a generic server error. This is a documented limitation and is not presented as a completed JSON 4xx implementation.

## Model traceability

Every successful response includes `model_version`. Training metrics, threshold, feature count and limitations are stored in `final_model/metadata.json`.

No RDS, OLAP or prediction-log persistence is part of this API contract.
