import sys
import os
import argparse
from datetime import datetime

import kfp
from kfp import compiler
from kfp.registry import RegistryClient

TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

BUCKET = "mlops-workshop"
ENVIRONMENT = "devi"
PIPELINE_REPO = "https://us-central1-kfp.pkg.dev/gsd-ai-mx-ferneutron/mlops"
PIPELINE_NAME = f"beans-{ENVIRONMENT}-{TIMESTAMP}"
PIPELINE_ROOT = f"{BUCKET}/{ENVIRONMENT}/{TIMESTAMP}/pipeline_root"

MYENV = os.getenv("MYENV")
print(f"Content of MYENV: {MYENV}")

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
        help="Register pipeline to Artifact.",
    )

    args = parser.parse_args()

    if args.compile:
        try:
            compiler.Compiler().compile(
                pipeline_func=pipeline,
                package_path="/workspace/pipeline.yaml",
            )
        except Exception as e:
            print(e)
            compiler.Compiler().compile(
                pipeline_func=pipeline,
                package_path="pipeline.yaml",
            )

    elif args.register:
        client = RegistryClient(host=PIPELINE_REPO)
        templateName, versionName = client.upload_pipeline(
            file_name="/workspace/pipeline.yaml",
            tags=["latest"],
            extra_headers={
                "description": "Description",
            },
        )
