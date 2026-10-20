"""Print the current SageMaker endpoint status without changing resources."""

from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError

from settings import ENDPOINT_NAME, REGION


def main() -> int:
    client = boto3.client("sagemaker", region_name=REGION)
    try:
        response = client.describe_endpoint(EndpointName=ENDPOINT_NAME)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ValidationException":
            print(json.dumps({"endpoint_name": ENDPOINT_NAME, "status": "NotCreated"}, indent=2))
            return 0
        raise

    print(
        json.dumps(
            {
                "endpoint_name": response["EndpointName"],
                "status": response["EndpointStatus"],
                "endpoint_config": response["EndpointConfigName"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
