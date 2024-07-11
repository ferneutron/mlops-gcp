# Trigger Pipeline Run through Cloud Functions

This Cloud Function triggers a Kubeflow Pipeline run using a pipeline template stored in Artifact Registry.

## Steps to Use the Pipeline Template
1. **Create a Pipeline Template:**
   - With the template already uploaded in the Artifact Registry.

2. **Deploy the Cloud Function:**
   - Use the provided `gcloud` command to deploy the Cloud Function.
   - Ensure the function is configured with HTTP trigger.

3. **Trigger the Pipeline Run:**
   - Send an HTTP request to the deployed Cloud Function.
   - The request body should contain the following JSON payload:
     - `parameter_values`: A dictionary containing the pipeline parameters and their values.
     - `config_values`: A dictionary containing configuration values for the pipeline run, such as project ID, location, service account, and storage bucket.


4. **Monitor the Pipeline Run:**
   - The Cloud Function will trigger the pipeline run using the specified template from Artifact Registry.
   - You can monitor the pipeline run in the Kubeflow Pipelines UI.

## gcloud command to deploy the Cloud Function
```bash
    gcloud functions deploy test-cf-pipeline \
    --gen2 \
    --runtime=python312 \
    --region=us-central1 \
    --source=. \
    --entry-point=run_beans_pipeline \
    --trigger-http \
    --memory=512
```

## Example Request Body

```json
request_body={
    "config_values": {
        "project_id": "gsd-ai-mx-ferneutron",
        "location": "us-central1",
        "service_account": "workshop@gsd-ai-mx-ferneutron.iam.gserviceaccount.com",
        "staging_bucket": "mlops-pipeline-staging",
        "pipeline_repo": "mlops",
        "pipeline_name": "beans-pipeline",
        "pipeline_tag": "latest",
        "pipeline_display_name" : "beans-pipeline-CF"
    } ,
    "parameter_values" : {
        "bq_source": "bq://gsd-ai-mx-ferneutron.beans.beans1",
        "DATASET_DISPLAY_NAME": "MyDatasetName",
        "MACHINE_TYPE": "n1-standard-4",
        "TRAINING_DISPLAY_NAME": "MyTrainingName",
        "auc_threshold": 0.9,
        "thresholds_dict_str": "{'auRoc': 0.95}",
        "MODEL_DISPLAY_NAME": "MyModelName",
        "ENDPOINT_DISPLAY_NAME": "MyEndpointName"
    }
}
```
## References

[Use](https://cloud.google.com/vertex-ai/docs/pipelines/create-pipeline-template#use-the-template-in-kfp-client) Pipeline template.
[Deploy](https://cloud.google.com/functions/docs/create-deploy-gcloud#deploying_the_function) Cloud Function.
