# Presentation Runbook

## Before presentation day

1. Run `python deployment/local_test.py`.
2. Run `python deployment/deploy_endpoint.py --dry-run` and verify every resource name.
3. Complete one rehearsal of deploy → status → invoke → cleanup.
4. Record the successful rehearsal as a backup.

## 30–60 minutes before the presentation

```bash
cd olist-risk-sagemaker-deployment
source .venv/bin/activate
python deployment/deploy_endpoint.py
python deployment/endpoint_status.py
```

Do not continue until the endpoint status is `InService`.

## During the presentation

Show the endpoint page in the AWS Console, then run:

```bash
python deployment/invoke_endpoint.py
```

Optional business-facing demonstration:

```bash
python web_demo/app.py
```

Open `http://127.0.0.1:5056`, load the verified request and run live inference. Explain that the displayed customer-care queue is a routing recommendation, not a persisted RDS queue or an automatic customer action.

Explain:

> This project uses online real-time inference. After delivery confirmation, 47 structured order features are sent to the SageMaker endpoint. The endpoint returns a risk score, operating threshold, binary decision, priority-review flag and model version. Review text and review scores are not used as live inputs.

## After the presentation

```bash
python deployment/cleanup_endpoint.py
```

This removes the billable endpoint but retains the model and endpoint configuration for reproducibility.
