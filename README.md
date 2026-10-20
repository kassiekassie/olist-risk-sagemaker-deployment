# Olist Bad-Review Risk — DSD SageMaker Deployment

This repository contains the clean Member 5 deployment workflow for the PAL project.

The scope is deliberately limited to what the Data Science Deployment course and PAL deployment rubric require:

1. verify the final model locally;
2. package the versioned model artifact;
3. deploy the model to an Amazon SageMaker real-time endpoint;
4. invoke the endpoint with a held-out order;
5. show the live result during the presentation;
6. delete the billable endpoint after the demonstration.

RDS, OLAP, prediction-log tables and data-warehouse implementation are not part of this repository. The team handles dimensional modelling and MySQL implementation separately under the Data Engineering for Analytics scope.

## Architecture

```text
Held-out delivered order JSON
        ↓
SageMaker real-time endpoint
        ↓
Model pipeline: preprocessing + XGBoost
        ↓
risk_score + threshold + class + priority flag + model version
```

The selected inference mode is **online / real-time inference** because a newly delivered order is scored immediately and receives a synchronous response.

## Repository structure

```text
olist-risk-sagemaker-deployment/
├── deployment/
│   ├── settings.py
│   ├── inference.py
│   ├── local_test.py
│   ├── package_and_upload.py
│   ├── deploy_endpoint.py
│   ├── endpoint_status.py
│   ├── invoke_endpoint.py
│   └── cleanup_endpoint.py
├── final_model/
│   ├── model.joblib
│   ├── metadata.json
│   ├── model_feature_catalog.csv
│   └── code/
│       ├── inference.py
│       └── requirements.txt
├── evidence/
├── sample_request.json
├── expected_response.json
├── invalid_request_missing_feature.json
├── final_model.tar.gz
├── Dockerfile
├── requirements.txt
└── API_SPECIFICATION.md
```

## 1. Prepare the local environment

```bash
cd olist-risk-sagemaker-deployment
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The `.venv` directory is ignored by Git and must not be pushed to GitHub.

## 2. Verify local inference

```bash
python deployment/local_test.py
```

Success ends with `Local inference verification passed`. This proves that the model artifact, feature catalog, request and expected response agree. It is not a cloud deployment by itself.

## 3. Rebuild and verify the model archive

```bash
python deployment/package_and_upload.py
```

This rebuilds `final_model.tar.gz` and verifies that it contains exactly:

```text
model.joblib
metadata.json
model_feature_catalog.csv
code/inference.py
code/requirements.txt
```

Upload only when the S3 artifact must be refreshed:

```bash
python deployment/package_and_upload.py --upload
```

## 4. Inspect the deployment configuration

```bash
python deployment/deploy_endpoint.py --dry-run
```

Defaults are stored in `deployment/settings.py`. No passwords or AWS access keys are stored in this repository. AWS credentials remain in the normal local AWS configuration.

## 5. Create or restore the SageMaker endpoint

```bash
python deployment/deploy_endpoint.py
```

The script verifies the S3 artifact, reuses or creates the SageMaker Model and Endpoint Configuration, creates the endpoint if absent, and waits until it becomes `InService`.

After an endpoint-only cleanup, this does **not** retrain the model, rebuild the Docker image or repeat the entire project. It reuses the retained S3 artifact, ECR image, SageMaker Model and Endpoint Configuration.

Check status with:

```bash
python deployment/endpoint_status.py
```

## 6. Run the live cloud inference

```bash
python deployment/invoke_endpoint.py
```

The script submits `sample_request.json` and verifies that the cloud prediction matches `expected_response.json`.

For the presentation, show:

1. the AWS Console endpoint status `InService`;
2. the request containing only delivery-time structured features;
3. the command above in the VS Code terminal;
4. the returned risk score, threshold, class, priority flag and model version.

The `risk_score` is an uncalibrated ranking score and must not be presented as a literal probability of a bad review.

## 7. Delete the billable endpoint

```bash
python deployment/cleanup_endpoint.py
```

This deletes only the real-time endpoint. It intentionally retains the SageMaker Model and Endpoint Configuration so the endpoint can be recreated quickly on presentation day.

Later, confirm that it is absent:

```bash
python deployment/endpoint_status.py
```

## Presentation-day sequence

Run these commands 30–60 minutes before the presentation:

```bash
cd olist-risk-sagemaker-deployment
source .venv/bin/activate
python deployment/deploy_endpoint.py
python deployment/endpoint_status.py
```

During the presentation:

```bash
python deployment/invoke_endpoint.py
```

After the presentation:

```bash
python deployment/cleanup_endpoint.py
```

Keep the existing successful invocation screenshot and a rehearsal recording as backup, but use a live cloud invocation when AWS is available.

## Optional customer-care dashboard

The local Flask dashboard turns the live model response into a proposed customer-care routing decision. It does not use RDS, persist cases, contact customers or create a real queue.

Start it only after the endpoint is `InService`:

```bash
python web_demo/app.py
```

Open `http://127.0.0.1:5056`, load the verified sample and choose **Run live inference**. The browser sends JSON to the local Flask server; AWS credentials remain on the server side and are never exposed in the HTML.

## GitHub safety check

Before committing:

```bash
git status --short
git grep -n -I -E 'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}' --cached
```

The credential scan should return no matches.
