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
        "pandas==1.3.5",
        "joblib==1.1.0",
    ],
)
def logistic_regression(
    train_dataset: Input[Dataset],
    metrics: Output[Metrics],
    output_model: Output[Model],
):
    import joblib
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    train = pd.read_csv(train_dataset.path)

    X_train, X_test, y_train, y_test = train_test_split(
        train.drop("Class", axis=1),
        train["Class"],
        test_size=0.2,
        random_state=42,
    )

    model = LogisticRegression()
    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    acc = accuracy_score(y_test, pred)
    aucRoc = roc_auc_score(
        y_test,
        model.predict_proba(X_test),
        multi_class="ovr",
    )

    metrics.log_metric("accuracy", (acc))
    metrics.log_metric("aucRoc", (aucRoc))

    joblib.dump(model, output_model.path)
