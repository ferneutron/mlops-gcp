import os
import sys
import argparse
from datetime import datetime

import kfp
from kfp import compiler
from kfp.registry import RegistryClient

BUCKET = os.getenv("BUCKET")
ENVIRONMENT = os.getenv("ENVIRONMENT")
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

PIPELINE_REPO = os.getenv("PIPELINE_REPO")
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
):
    import google_cloud_pipeline_components.v1.dataset as GData
    from components.utils.custom_split import split_data
    from components.models.logistic_regression import logistic_regression

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
                "description": "Must set by definition. Comment to test changes. TEST7.",
            },
        )
