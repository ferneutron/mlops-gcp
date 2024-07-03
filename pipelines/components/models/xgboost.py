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
def xgboost(
    project_id: str,
    location: str,
    train_dataset: Input[Dataset],
    metrics: Output[Metrics],
    output_model: Output[Model],
):
    import joblib
    import pandas as pd
    import xgboost as xgb
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    train = pd.read_csv(train_dataset.path)

    X_train, X_test, y_train, y_test = train_test_split(
        train.drop("Class", axis=1), train["Class"], test_size=0.2, random_state=42
    )

    model = xgb.XGBClassifier()
    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    acc = accuracy_score(y_test, pred)
    aucRoc = roc_auc_score(y_test, model.predict_proba(X_test), multi_class="ovr")

    metrics.log_metric("accuracy", (acc))
    metrics.log_metric("aucRoc", (aucRoc))

    joblib.dump(model, output_model.path)
