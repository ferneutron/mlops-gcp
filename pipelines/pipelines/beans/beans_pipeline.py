from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import kfp
from components.evaluators.dumb_eval import dumb_eval
from components.models.logistic_regression import logistic_regression
from components.utils.custom_split import split_data
from components.utils.dumb_deploy_model import dumb_deploy_model
from google.cloud import aiplatform
from kfp import compiler

sys.path.append("src/")

# Define environment variables to be used for pipeline
# compilation.
BUCKET = os.getenv("BUCKET")
LOCATION = os.getenv("LOCATION")
PROJECT_ID = os.getenv("PROJECT_ID")
ENVIRONMENT = os.getenv("ENVIRONMENT")
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

# Define pipeline name and path where the pipeline
# artifcats will be stored
PIPELINE_ROOT = f"{BUCKET}/{ENVIRONMENT}/{TIMESTAMP}/pipeline_root"
PIPELINE_STAGING = f"{BUCKET}/{ENVIRONMENT}/{TIMESTAMP}/staging"
PIPELINE_DESCRIPTION = "A base pipeline for testing purposes"

# Artifacts settings

MACHINE_TYPE = "n1-standard-4"
BQ_DATASET = "beans"
BQ_TABLE = "beans1"
BQ_SOURCE = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"


@kfp.dsl.pipeline(name="test nae", pipeline_root=PIPELINE_ROOT)
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

    logistic_training_op = logistic_regression(
        project_id=project_id,
        location=location,
        train_dataset=data.outputs["train_dataset"],
    )

    dumb_eval_op = dumb_eval(
        project_id=project_id,
        location=location,
        test_dataset=data.outputs["test_dataset"],
        logistic_trained_model=logistic_training_op.outputs["output_model"],
    )

    dumb_deploy_model(
        project_id=project_id,
        location=location,
        model=dumb_eval_op.outputs["output_model"],
    )


def init_parser():
    parser = argparse.ArgumentParser(
        description="Compile and run your Python code.",
    )

    parser.add_argument(
        "--compile",
        action="store_true",
        help="Compile the Python code (e.g., to bytecode).",
    )

    parser.add_argument(
        "--out",
        required=True,
        metavar="OUTPUT_FILE",
        help="Name of the file to store the output.",
    )

    parser.add_argument(
        "--run", action="store_true",
        help="Run the Python code.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = init_parser()

    OUTPUT_FILE = args.out
    PIPELINE_NAME = OUTPUT_FILE.split(".")[0]

    if args.compile:
        compiler.Compiler().compile(
            pipeline_func=pipeline, package_path=f"/workspace/{OUTPUT_FILE}",
        )

    elif args.run:
        job = aiplatform.PipelineJob(
            display_name={PIPELINE_NAME},
            template_path=f"/workspace/{OUTPUT_FILE}",
            pipeline_root=PIPELINE_ROOT,
            parameter_values={
                "project_id": PROJECT_ID,
                "location": LOCATION,
                "bq_source": f"bq://{BQ_SOURCE}",
                "auc_threshold": 0.90,
                "DATASET_DISPLAY_NAME": "dataset-name",
                "TRAINING_DISPLAY_NAME": "training-job-nae",
                "MODEL_DISPLAY_NAME": "model-display-nae",
                "ENDPOINT_DISPLAY_NAME": "endpoint-display-name",
                "MACHINE_TYPE": MACHINE_TYPE,
            },
            enable_caching=True,
        )

        job.run()
