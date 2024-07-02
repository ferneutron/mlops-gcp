from typing import List, NamedTuple, Tuple

import kfp
from kfp import compiler, dsl
from kfp.dsl import Artifact, Dataset, Input, Metrics, Model, Output, component


@component(
    base_image="gcr.io/deeplearning-platform-release/tf2-cpu.2-6:latest",
    packages_to_install=[
        "xgboost==1.6.2",
        "pandas==1.3.5",
        "joblib==1.1.0",
    ],
)
def dumb_eval(
    project_id: str,
    location: str,
    test_dataset: Input[Dataset],
    logistic_trained_model: Input[Model],
    output_model: Output[Model],
):
    import joblib
    import pandas as pd
    from sklearn.metrics import accuracy_score, roc_auc_score

    test = pd.read_csv(test_dataset.path)

    output_model.path = logistic_trained_model.path
