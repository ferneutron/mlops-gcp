import functions_framework
from google.cloud import aiplatform
from google.api_core.exceptions import NotFound


@functions_framework.http
def run_beans_pipeline(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    # Get the input parameters from the request
    request_json = request.get_json(silent=True)
    if request_json is None:
        request_json = request.form.to_dict()

    # Validate required parameters
    required_params = ["config_values", "parameter_values"]
    for param in required_params:
        if param not in request_json:
            return f"Missing required parameter: {param}", 400

    config_values = request_json["config_values"]
    parameter_values = request_json["parameter_values"]

    try:
        project_id = config_values["project_id"]
        location = config_values["location"]
        staging_bucket = config_values["staging_bucket"]
        service_account = config_values["service_account"]
        pipeline_display_name = config_values["pipeline_display_name"]
        pipeline_repo = config_values["pipeline_repo"]
        pipeline_name = config_values["pipeline_name"]
        pipeline_tag = config_values["pipeline_tag"]
    except KeyError as e:
        # Handle the missing parameter error
        return f"Missing required parameter in config_params: {e}", 400

    pipeline_root = (
        f"https://{location}-kfp.pkg.***/{project_id}/{pipeline_repo}/{pipeline_name}"
    )

    # Get pipeline definition from Registry
    general_values = {key: config_values[key] for key in ["project_id", "location"]}
    parameter_values = parameter_values | general_values

    try:
        aiplatform.init(
            project=project_id,
            location=location,
            staging_bucket=staging_bucket,
        )
        job = aiplatform.PipelineJob(
            display_name=pipeline_display_name,
            template_path=f"{pipeline_root}/{pipeline_tag}",
            parameter_values=parameter_values,
        )
        # If the pipeline job is created successfully, you can start it here
        print(
            job.submit(
                service_account=service_account,
            ),
        )
        print(f"Pipeline job {job.display_name} submitted successfully.")

    except NotFound as e:
        if "template path not found" in str(e).lower():  # Case-insensitive check
            print(
                f"Error: Pipeline template '{pipeline_root}/{pipeline_tag}' not found. Please double-check the path.",
            )
        else:
            print(f"An unexpected NotFound error occurred: {e}")
    except Exception as e:  # Catch any other potential errors
        print(f"An error occurred while creating the pipeline job: {e}")

    return f"{job.display_name} submitted successfully. Job State {job.state}", 200
