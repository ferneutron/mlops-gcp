# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Simple comment for testing

import os
import sys
import argparse
from datetime import datetime

import kfp
from kfp import compiler, dsl
from kfp.registry import RegistryClient
from google_cloud_pipeline_components.v1.vertex_notification_email import (
    VertexNotificationEmailOp,
)

BUCKET = os.getenv("_BUCKET")
ENVIRONMENT = os.getenv("_ENVIRONMENT")
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

PIPELINE_REPO = os.getenv("_PIPELINE_REPO")
PIPELINE_NAME = f"beans-{ENVIRONMENT}-{TIMESTAMP}"
PIPELINE_ROOT = f"{BUCKET}/{ENVIRONMENT}/{TIMESTAMP}/pipeline_root"
PACKAGE_PATH = "." if ENVIRONMENT == "dev" else "/workspace"

sys.path.append("vertex-pipelines/")


@kfp.dsl.pipeline(name=PIPELINE_NAME, pipeline_root=PIPELINE_ROOT)
def pipeline(
    project_id: str,
    location: str,
    bq_source: str,
    dataset_name: str,
    email_addresses: list,
):
    import google_cloud_pipeline_components.v1.dataset as GData
    from components.utils.custom_split import split_data
    from components.models.logistic_regression import logistic_regression

    notify_email_task = VertexNotificationEmailOp(recipients=email_addresses)
    with dsl.ExitHandler(notify_email_task):
        TabularDatasetCreateOp = (
            GData.create_tabular_dataset.component.tabular_dataset_create
        )

        dataset_create_op = TabularDatasetCreateOp(
            project=project_id,
            location=location,
            display_name=dataset_name,
            bq_source=bq_source,
        )

        data = split_data(
            project_id=project_id,
            location=location,
            dataset=dataset_create_op.outputs["dataset"],
        )

        logistic_regression(
            train_dataset=data.outputs["train_dataset"],
        )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Compile and run your",
    )

    parser.add_argument(
        "--compile",
        action="store_true",
        help="Compile",
    )

    parser.add_argument(
        "--register",
        action="store_true",
        help="Register pipeline",
    )

    args = parser.parse_args()

    if args.compile:
        compiler.Compiler().compile(
            pipeline_func=pipeline,
            package_path=f"{PACKAGE_PATH}/pipeline.yaml",
        )

    elif args.register:
        client = RegistryClient(host=PIPELINE_REPO)
        templateName, versionName = client.upload_pipeline(
            file_name=f"{PACKAGE_PATH}/pipeline.yaml",
            tags=["latest"],
            extra_headers={
                "description": "Must set by definition. Comment to test changes. TEST16.",
            },
        )
