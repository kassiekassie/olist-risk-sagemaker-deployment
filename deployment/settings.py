"""Single source of truth for the PAL SageMaker demonstration resources.

None of the values in this file are passwords or access keys. Environment
variables can override them when the repository is used in another account.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REGION = os.getenv("AWS_REGION", "ap-southeast-1")
ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "471443766652")

BUCKET = os.getenv("PAL_MODEL_BUCKET", "olist-risk-model-kassie-2026")
MODEL_S3_KEY = os.getenv("PAL_MODEL_S3_KEY", "final/model.tar.gz")
MODEL_DATA_URL = f"s3://{BUCKET}/{MODEL_S3_KEY}"

IMAGE_URI = os.getenv(
    "PAL_SAGEMAKER_IMAGE_URI",
    f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/"
    "olist-risk-sagemaker:sagemaker-v2",
)

EXECUTION_ROLE_ARN = os.getenv(
    "PAL_SAGEMAKER_ROLE_ARN",
    f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/"
    "AmazonSageMaker-ExecutionRole-20261019T171796",
)

MODEL_NAME = os.getenv("PAL_SAGEMAKER_MODEL_NAME", "olist-risk-final-v2-model")
ENDPOINT_CONFIG_NAME = os.getenv(
    "PAL_ENDPOINT_CONFIG_NAME", "olist-risk-final-v2-config"
)
ENDPOINT_NAME = os.getenv("PAL_ENDPOINT_NAME", "olist-risk-final-v2-endpoint")
INSTANCE_TYPE = os.getenv("PAL_INSTANCE_TYPE", "ml.m5.large")

MODEL_DIRECTORY = PROJECT_ROOT / "final_model"
MODEL_ARCHIVE = PROJECT_ROOT / "final_model.tar.gz"
SAMPLE_REQUEST = PROJECT_ROOT / "sample_request.json"
EXPECTED_RESPONSE = PROJECT_ROOT / "expected_response.json"
