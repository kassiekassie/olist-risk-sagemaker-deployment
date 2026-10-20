"""Create or restore the PAL SageMaker real-time endpoint.

The script is idempotent: retained SageMaker Model and Endpoint Configuration
resources are reused. After an endpoint-only cleanup, presentation-day startup
only needs to recreate the endpoint and wait for InService.
"""

from __future__ import annotations

import argparse
import json

import boto3
from botocore.exceptions import ClientError

from settings import (
    ENDPOINT_CONFIG_NAME,
    ENDPOINT_NAME,
    EXECUTION_ROLE_ARN,
    IMAGE_URI,
    INSTANCE_TYPE,
    MODEL_DATA_URL,
    MODEL_NAME,
    REGION,
)


def is_not_found(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") in {
        "ValidationException",
        "ResourceNotFound",
    }


def ensure_model(client) -> None:
    try:
        response = client.describe_model(ModelName=MODEL_NAME)
        container = response["PrimaryContainer"]
        print(f"Reusing SageMaker Model: {MODEL_NAME}")
        print(f"  image: {container.get('Image')}")
        print(f"  artifact: {container.get('ModelDataUrl')}")
        return
    except ClientError as error:
        if not is_not_found(error):
            raise

    client.create_model(
        ModelName=MODEL_NAME,
        ExecutionRoleArn=EXECUTION_ROLE_ARN,
        PrimaryContainer={
            "Image": IMAGE_URI,
            "ModelDataUrl": MODEL_DATA_URL,
            "Environment": {
                "SAGEMAKER_PROGRAM": "inference.py",
                "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
                "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
                "SAGEMAKER_REGION": REGION,
            },
        },
    )
    print(f"Created SageMaker Model: {MODEL_NAME}")


def ensure_endpoint_config(client) -> None:
    try:
        response = client.describe_endpoint_config(
            EndpointConfigName=ENDPOINT_CONFIG_NAME
        )
        variant = response["ProductionVariants"][0]
        print(f"Reusing Endpoint Configuration: {ENDPOINT_CONFIG_NAME}")
        print(f"  model: {variant['ModelName']}")
        print(f"  instance: {variant['InstanceType']}")
        return
    except ClientError as error:
        if not is_not_found(error):
            raise

    client.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": MODEL_NAME,
                "InitialInstanceCount": 1,
                "InstanceType": INSTANCE_TYPE,
                "InitialVariantWeight": 1.0,
            }
        ],
    )
    print(f"Created Endpoint Configuration: {ENDPOINT_CONFIG_NAME}")


def ensure_endpoint(client) -> None:
    try:
        response = client.describe_endpoint(EndpointName=ENDPOINT_NAME)
        status = response["EndpointStatus"]
        print(f"Endpoint already exists: {ENDPOINT_NAME} ({status})")
        if status == "Failed":
            raise RuntimeError(response.get("FailureReason", "Endpoint creation failed"))
        if status == "Deleting":
            raise RuntimeError("Endpoint is still deleting. Wait and rerun this script.")
    except ClientError as error:
        if not is_not_found(error):
            raise
        client.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG_NAME,
        )
        print(f"Endpoint creation started: {ENDPOINT_NAME}")

    if client.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"] != "InService":
        print("Waiting for endpoint to become InService...")
        client.get_waiter("endpoint_in_service").wait(
            EndpointName=ENDPOINT_NAME,
            WaiterConfig={"Delay": 30, "MaxAttempts": 40},
        )

    response = client.describe_endpoint(EndpointName=ENDPOINT_NAME)
    print(
        json.dumps(
            {
                "endpoint_name": response["EndpointName"],
                "endpoint_status": response["EndpointStatus"],
                "endpoint_config": response["EndpointConfigName"],
            },
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the configured resources without calling AWS.",
    )
    args = parser.parse_args()

    configuration = {
        "region": REGION,
        "model_name": MODEL_NAME,
        "model_artifact": MODEL_DATA_URL,
        "image": IMAGE_URI,
        "execution_role": EXECUTION_ROLE_ARN,
        "endpoint_config": ENDPOINT_CONFIG_NAME,
        "endpoint_name": ENDPOINT_NAME,
        "instance_type": INSTANCE_TYPE,
    }
    if args.dry_run:
        print(json.dumps(configuration, indent=2))
        return 0

    session = boto3.Session(region_name=REGION)
    identity = session.client("sts").get_caller_identity()
    print(f"AWS caller: {identity['Arn']}")
    session.client("s3").head_object(
        Bucket=MODEL_DATA_URL.removeprefix("s3://").split("/", 1)[0],
        Key=MODEL_DATA_URL.removeprefix("s3://").split("/", 1)[1],
    )
    print(f"Verified model artifact: {MODEL_DATA_URL}")

    client = session.client("sagemaker")
    ensure_model(client)
    ensure_endpoint_config(client)
    ensure_endpoint(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
