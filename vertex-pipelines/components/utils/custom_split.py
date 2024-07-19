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

from kfp.dsl import Artifact
from kfp.dsl import component
from kfp.dsl import Dataset
from kfp.dsl import Input
from kfp.dsl import Output


@component(
    base_image="gcr.io/deeplearning-platform-release/tf2-cpu.2-6:latest",
    packages_to_install=[
        "xgboost==1.6.2",
        "pandas==1.3.5",
        "joblib==1.1.0",
        "google-cloud-aiplatform",
        "google-cloud-bigquery",
    ],
)
def split_data(
    project_id: str,
    location: str,
    dataset: Input[Artifact],
    train_dataset: Output[Dataset],
    test_dataset: Output[Dataset],
):
    import pandas as pd
    from google.cloud import aiplatform, bigquery
    from sklearn.model_selection import train_test_split

    aiplatform.init(project=project_id, location=location)

    data = aiplatform.TabularDataset(
        dataset_name=dataset.metadata["resourceName"],
    )
    data = data.to_dict()

    uri = data["metadata"]["inputConfig"]["bigquerySource"]["uri"]
    dataset_id = uri.split(f"bq://{project_id}.")[-1].split(".")[0]
    table_id = uri.split(f"bq://{project_id}.")[-1].split(".")[1]

    client = bigquery.Client()

    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    table_ref = dataset_ref.table(table_id)
    table = bigquery.Table(table_ref)
    iterable_table = client.list_rows(table).to_dataframe_iterable()

    dfs = []
    for row in iterable_table:
        dfs.append(row)

    df = pd.concat(dfs, ignore_index=True)
    del dfs

    df["Class"].replace(
        {
            "DERMASON": 0,
            "SIRA": 1,
            "SEKER": 2,
            "HOROZ": 3,
            "CALI": 4,
            "BARBUNYA": 5,
            "BOMBAY": 6,
        },
        inplace=True,
    )

    X_train, X_test, y_train, y_test = train_test_split(
        df.drop("Class", axis=1),
        df["Class"],
        test_size=0.2,
        random_state=42,
    )

    X_train["Class"] = y_train
    X_test["Class"] = y_test

    X_train.to_csv(f"{train_dataset.path}", index=False)
    X_test.to_csv(f"{test_dataset.path}", index=False)

    print(f"Path: {train_dataset}")
