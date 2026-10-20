"""Delete only the billable endpoint while retaining fast-redeploy resources."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from settings import ENDPOINT_CONFIG_NAME, ENDPOINT_NAME, MODEL_NAME, REGION


def main() -> int:
    client = boto3.client("sagemaker", region_name=REGION)
    try:
        response = client.describe_endpoint(EndpointName=ENDPOINT_NAME)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ValidationException":
            print(f"Endpoint is already absent: {ENDPOINT_NAME}")
            return 0
        raise

    status = response["EndpointStatus"]
    if status == "Deleting":
        print(f"Endpoint is already deleting: {ENDPOINT_NAME}")
        return 0
    if status in {"Creating", "Updating", "SystemUpdating", "RollingBack"}:
        print(
            f"Endpoint is still {status} and AWS will not allow deletion yet: "
            f"{ENDPOINT_NAME}"
        )
        print("Wait for InService or Failed, then run this script again.")
        return 2

    client.delete_endpoint(EndpointName=ENDPOINT_NAME)
    print(f"Endpoint deletion started: {ENDPOINT_NAME}")
    print("Retained for quick presentation-day redeploy:")
    print(f"  SageMaker Model: {MODEL_NAME}")
    print(f"  Endpoint Configuration: {ENDPOINT_CONFIG_NAME}")
    print("Run deployment/endpoint_status.py later to confirm status NotCreated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
