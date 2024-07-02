from typing import List, NamedTuple, Tuple

import kfp
from kfp import compiler, dsl
from kfp.dsl import Artifact, Dataset, Input, Metrics, Model, Output, component


@component(
    base_image="gcr.io/deeplearning-platform-release/tf2-cpu.2-6:latest",
    packages_to_install=["google-cloud-aiplatform"],
)
def deploy_model(
    project_id: str,
    location: str,
    model: Input[Model],
):
    from pathlib import Path

    import joblib
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=location)

    uploaded_model = aiplatform.Model.upload_scikit_learn_model_file(
        model_file_path=str(Path(model.path)),
        display_name="BeansModelv1",
        project=project_id,
        location=location,
    )

    endpoint = aiplatform.Endpoint.create(
        display_name="BeansEndpointv1", project=project_id, location=location
    )

    model_deploy = uploaded_model.deploy(
        machine_type="n1-standard-4",
        endpoint=endpoint,
        traffic_split={"0": 100},
        deployed_model_display_name="BeansDeploymentv1",
    )
