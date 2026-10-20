"""Build the SageMaker model archive and optionally upload it to Amazon S3."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

import boto3

from settings import (
    BUCKET,
    MODEL_ARCHIVE,
    MODEL_DIRECTORY,
    MODEL_S3_KEY,
    REGION,
)


REQUIRED_FILES = (
    "model.joblib",
    "metadata.json",
    "model_feature_catalog.csv",
    "code/inference.py",
    "code/requirements.txt",
)


def validate_source(model_directory: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (model_directory / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Model package is missing required files: {missing}")


def build_archive(model_directory: Path, archive_path: Path) -> None:
    validate_source(model_directory)
    with tarfile.open(archive_path, "w:gz") as archive:
        for relative_name in REQUIRED_FILES:
            archive.add(model_directory / relative_name, arcname=relative_name)

    with tarfile.open(archive_path, "r:gz") as archive:
        archived_names = sorted(member.name for member in archive.getmembers() if member.isfile())
    expected_names = sorted(REQUIRED_FILES)
    if archived_names != expected_names:
        raise RuntimeError(
            f"Archive verification failed. Expected {expected_names}, got {archived_names}"
        )


def upload_archive(archive_path: Path) -> None:
    session = boto3.Session(region_name=REGION)
    identity = session.client("sts").get_caller_identity()
    print(f"AWS caller: {identity['Arn']}")
    session.client("s3").upload_file(str(archive_path), BUCKET, MODEL_S3_KEY)
    print(f"Uploaded: s3://{BUCKET}/{MODEL_S3_KEY}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the verified archive to the configured S3 location.",
    )
    args = parser.parse_args()

    build_archive(MODEL_DIRECTORY, MODEL_ARCHIVE)
    print(f"Verified model archive: {MODEL_ARCHIVE}")
    if args.upload:
        upload_archive(MODEL_ARCHIVE)
    else:
        print("Upload skipped. Add --upload when an S3 refresh is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
