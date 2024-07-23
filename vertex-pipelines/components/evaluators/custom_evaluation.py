# Copyright 2023 Google LLC
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

from kfp.dsl import component
from kfp.dsl import Dataset
from kfp.dsl import Input
from kfp.dsl import Metrics
from kfp.dsl import Model
from kfp.dsl import Output


@component(
    base_image="gcr.io/deeplearning-platform-release/tf2-cpu.2-6:latest",
    packages_to_install=[
        "xgboost==1.6.2",
        "pandas==1.3.5",
        "joblib==1.1.0",
    ],
)
def custom_evaluation(
    test_dataset: Input[Dataset],
    logistic_trained_model: Input[Model],
    xgboost_trained_model: Input[Model],
    random_forest_trained_model: Input[Model],
    decision_tree_trained_model: Input[Model],
    metrics: Output[Metrics],
    output_model: Output[Model],
):

    import joblib
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    test = pd.read_csv(test_dataset.path)

    models = {
        "logistic_regression": logistic_trained_model.path,
        "xgboost": xgboost_trained_model.path,
        "random_forest": random_forest_trained_model.path,
        "decision_tree": decision_tree_trained_model.path,
    }

    best_model_name, best_auc_roc = "", 0.0
    for model_name, model_path in models.items():
        model = joblib.load(model_path)
        y_pred = model.predict_proba(test.drop("Class", axis=1))
        auc_roc = roc_auc_score(test["Class"], y_pred, multi_class="ovr")

        metrics.log_metric(f"{model_name} (AUC ROC)", (auc_roc))

        if auc_roc > best_auc_roc:
            best_auc_roc = auc_roc
            best_model_name = model_name

    output_model.path = models[best_model_name]

    metrics.log_metric("best_model_name", (best_model_name))
    metrics.log_metric("best_auc_roc", (best_auc_roc))
