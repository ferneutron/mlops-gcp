import argparse
import os
import sys
from datetime import datetime

import kfp
from google.cloud import aiplatform
from kfp import compiler, dsl

sys.path.append("src/")

from components.evaluators.automl_evaluation import automl_evaluation
from components.evaluators.custom_evaluation import custom_evaluation

# Evaluation
from components.evaluators.dumb_eval import dumb_eval
from components.models.decision_tree import decision_tree
from components.models.logistic_regression import logistic_regression
from components.models.random_forest import random_forest

# Training
from components.models.xgboost import xgboost

# Utils
from components.utils.custom_split import split_data
from components.utils.deploy_model import deploy_model
from components.utils.dumb_deploy_model import dumb_deploy_model

global PIPELINE_NAME
global MODEL_NAME
global DATASET_NAME
global TRAINING_JOB_NAME
global ENDPOINT_NAME

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


@kfp.dsl.pipeline(name=PIPELINE_NAME, pipeline_root=PIPELINE_ROOT)
def pipeline(
    bq_source: str,
    DATASET_DISPLAY_NAME: str,
    TRAINING_DISPLAY_NAME: str,
    MODEL_DISPLAY_NAME: str,
    ENDPOINT_DISPLAY_NAME: str,
    MACHINE_TYPE: str,
    project_id: str,
    location: str,
    thresholds_dict_str: str,
    auc_threshold: float,
):
    from google_cloud_pipeline_components.v1.automl.training_job import (
        AutoMLTabularTrainingJobRunOp,
    )
    from google_cloud_pipeline_components.v1.dataset.create_tabular_dataset.component import (
        tabular_dataset_create as TabularDatasetCreateOp,
    )
    from google_cloud_pipeline_components.v1.endpoint.create_endpoint.component import (
        endpoint_create as EndpointCreateOp,
    )
    from google_cloud_pipeline_components.v1.endpoint.deploy_model.component import (
        model_deploy as ModelDeployOp,
    )

    dataset_create_op = TabularDatasetCreateOp(
        project=project_id,
        location=location,
        display_name=DATASET_NAME,
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

    dumb_deploy_model_op = dumb_deploy_model(
        project_id=project_id,
        location=location,
        model=dumb_eval_op.outputs["output_model"],
    )


def init_parser():
    parser = argparse.ArgumentParser(description="Compile and run your Python code.")

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

    parser.add_argument("--run", action="store_true", help="Run the Python code.")

    return parser.parse_args()


if __name__ == "__main__":
    args = init_parser()

    OUTPUT_FILE = args.out
    PIPELINE_NAME = OUTPUT_FILE.split(".")[0]

    if args.compile:
        compiler.Compiler().compile(
            pipeline_func=pipeline, package_path=f"/workspace/{OUTPUT_FILE}"
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
                "thresholds_dict_str": '{"auRoc": 0.95}',
                "auc_threshold": 0.90,
                "DATASET_DISPLAY_NAME": DATASET_NAME,
                "TRAINING_DISPLAY_NAME": TRAINING_JOB_NAME,
                "MODEL_DISPLAY_NAME": MODEL_NAME,
                "ENDPOINT_DISPLAY_NAME": ENDPOINT_NAME,
                "MACHINE_TYPE": MACHINE_TYPE,
            },
            enable_caching=True,
        )

        job.run()
