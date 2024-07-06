from __future__ import annotations

import argparse
import sys
from datetime import datetime

import kfp
from components.models.logistic_regression import logistic_regression
from components.utils.custom_split import split_data
from kfp import compiler
from kfp.registry import RegistryClient


TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

BUCKET = "mlops-workshop"
ENVIRONMENT = "dev"
PIPELINE_REPO = "https://us-central1-kfp.pkg.dev/gsd-ai-mx-ferneutron/mlops"
PIPELINE_NAME = f"beans-{ENVIRONMENT}-{TIMESTAMP}"
PIPELINE_ROOT = f"{BUCKET}/{ENVIRONMENT}/{TIMESTAMP}/pipeline_root"


@kfp.dsl.pipeline(name=PIPELINE_NAME, pipeline_root=PIPELINE_ROOT)
def pipeline(
    bq_source: str,
    project_id: str,
    location: str,
):
    import google_cloud_pipeline_components.v1.dataset as DataSet

    TabularDatasetCreateOp = DataSet.create_tabular_dataset.component

    dataset_create_op = TabularDatasetCreateOp(
        project=project_id,
        location=location,
        display_name="dataset-name",
        bq_source=bq_source,
    )

    data = split_data(
        project_id=project_id,
        location=location,
        dataset=dataset_create_op.outputs["dataset"],
    )

    logistic_regression(
        project_id=project_id,
        location=location,
        train_dataset=data.outputs["train_dataset"],
    )


def init_parser():
    parser = argparse.ArgumentParser(
        description="Compile and run your Python code.",
    )

    parser.add_argument(
        "--compile",
        action="store_true",
        help="Compile pipeline.",
    )

    parser.add_argument(
        "--register",
        action="store_true",
        help="Register pipeline to Artifact Registry.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    sys.path.append("pipelines/")

    args = init_parser()

    if args.compile:
        compiler.Compiler().compile(
            pipeline_func=pipeline,
            package_path="/workspace/pipeline.yaml",
        )

    elif args.register:
        client = RegistryClient(host=PIPELINE_REPO)
        templateName, versionName = client.upload_pipeline(
            file_name="/workspace/pipeline.yaml",
            tags=["latest"],
            extra_headers={
                "description": "This is an exampleß",
            },
        )
