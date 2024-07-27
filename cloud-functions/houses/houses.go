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

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	aiplatform "cloud.google.com/go/aiplatform/apiv1beta1"
	"cloud.google.com/go/iam"
	"github.com/gin-gonic/gin"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
	"google.golang.org/genproto/googleapis/cloud/aiplatform/v1beta1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const (
	// Maximum attempts to wait for the pipeline to start
	maxAttemptsStatus = 6
	// Time interval between attempts in seconds
	waitIntervalSeconds = 20
)

// PipelineJob represents a pipeline job for running a KFP pipeline
type PipelineJob struct {
	Name          string
	DisplayName  string
	TemplatePath string
	Parameters   map[string]interface{}
	State         aiplatform.PipelineState
}

// GetPipelineJobState gets the state of the pipeline job
func (pj *PipelineJob) GetPipelineJobState(ctx context.Context, client *aiplatform.PipelineServiceClient) error {
	resp, err := client.GetPipelineJob(ctx, &aiplatform.GetPipelineJobRequest{
		Name: pj.Name,
	})
	if err != nil {
		return err
	}
	pj.State = resp.State
	return nil
}

func main() {
	router := gin.Default()

	// Define the endpoint to run the pipeline
	router.POST("/run-beans-pipeline", func(c *gin.Context) {
		var requestData map[string]interface{}
		if err := c.BindJSON(&requestData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       fmt.Sprintf("Invalid request body: %s", err),
				"jobName":       nil,
			})
			return
		}

		// Validate required parameters
		requiredParams := []string{"config_values", "parameter_values"}
		for _, param := range requiredParams {
			if _, ok := requestData[param]; !ok {
				c.JSON(http.StatusBadRequest, gin.H{
					"statusCode":    400,
					"pipelineStatus": "FAILED",
					"message":       fmt.Sprintf("Missing required parameter: %s", param),
					"jobName":       nil,
				})
				return
			}
		}

		// Access the configuration and parameter values
		configValues := requestData["config_values"].(map[string]interface{})
		parameterValues := requestData["parameter_values"].(map[string]interface{})

		// Extract values from configuration
		var projectID, location, stagingBucket, serviceAccount, pipelineDisplayName, pipelineRepo, pipelineName, pipelineTag string
		if v, ok := configValues["project_id"]; ok {
			projectID = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: project_id",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["location"]; ok {
			location = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: location",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["staging_bucket"]; ok {
			stagingBucket = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: staging_bucket",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["service_account"]; ok {
			serviceAccount = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: service_account",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["pipeline_display_name"]; ok {
			pipelineDisplayName = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: pipeline_display_name",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["pipeline_repo"]; ok {
			pipelineRepo = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: pipeline_repo",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["pipeline_name"]; ok {
			pipelineName = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: pipeline_name",
				"jobName":       nil,
			})
			return
		}

		if v, ok := configValues["pipeline_tag"]; ok {
			pipelineTag = v.(string)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{
				"statusCode":    400,
				"pipelineStatus": "FAILED",
				"message":       "Missing required parameter: pipeline_tag",
				"jobName":       nil,
			})
			return
		}

		// Construct the pipeline root URL
		pipelineRoot := fmt.Sprintf("https://%s-kfp.pkg.dev/%s/%s/%s", location, projectID, pipelineRepo, pipelineName)

		// Ensure email addresses are provided
		if _, ok := parameterValues["email_addresses"]; !ok {
			parameterValues["email_addresses"] = []string{"dummy@example.com"}
		}

		// Combine general values and parameter values
		for k, v := range configValues {
			parameterValues[k] = v
		}

		// Create a new context
		ctx := context.Background()

		// Initialize the AIPlatform client
		client, err := aiplatform.NewPipelineServiceClient(ctx, option.WithCredentialsFile(serviceAccount))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"statusCode":    500,
				"pipelineStatus": "FAILED",
				"message":       fmt.Sprintf("Error initializing AIPlatform client: %s", err),
				"jobName":       nil,
			})
			return
		}
		defer client.Close()

		// Submit the pipeline job
		pipelineJob := PipelineJob{
			DisplayName:  pipelineDisplayName,
			TemplatePath: fmt.Sprintf("%s/%s", pipelineRoot, pipelineTag),
			Parameters:   parameterValues,
		}

		jobName, err := submitPipelineJob(ctx, client, &pipelineJob, projectID, location, stagingBucket)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"statusCode":    500,
				"pipelineStatus": "FAILED",
				"message":       fmt.Sprintf("Error submitting pipeline job: %s", err),
				"jobName":       nil,
			})
			return
		}

		// Wait for the pipeline job to start or fail
		pipelineJob.Name = jobName
		err = waitForPipelineJobState(ctx, client, &pipelineJob)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"statusCode":    500,
				"pipelineStatus": "FAILED",
				"message":       fmt.Sprintf("Error waiting for pipeline job state: %s", err),
				"jobName":       jobName,
			})
			return
		}

		// Return the response based on the pipeline job state
		var statusCode int
		var pipelineStatus string
		var message string

		switch pipelineJob.State {
		case aiplatform.PipelineState_PIPELINE_STATE_RUNNING:
			statusCode = http.StatusOK
			pipelineStatus = "RUNNING"
			message = fmt.Sprintf("Pipeline job %s is running.", pipelineJob.DisplayName)
		case aiplatform.PipelineState_PIPELINE_STATE_FAILED:
			statusCode = http.StatusBadRequest
			pipelineStatus = "FAILED"
			message = fmt.Sprintf("Pipeline job %s failed.", pipelineJob.DisplayName)
		default:
			statusCode = http.StatusInternalServerError
			pipelineStatus = "FAILED"
			message = fmt.Sprintf("Pipeline job %s in unexpected state: %s.", pipelineJob.DisplayName, pipelineJob.State)
		}

		c.JSON(statusCode, gin.H{
			"statusCode":    statusCode,
			"pipelineStatus": pipelineStatus,
			"message":       message,
			"jobName":       jobName,
		})
	})

	router.Run(":8080")
}

// submitPipelineJob submits a pipeline job to AIPlatform
func submitPipelineJob(ctx context.Context, client *aiplatform.PipelineServiceClient, pipelineJob *PipelineJob, projectID, location, stagingBucket string) (string, error) {
	// Convert parameters to proto format
	var protoParams []*aiplatform.PipelineJob_Parameter
	for key, value := range pipelineJob.Parameters {
		switch v := value.(type) {
		case string:
			protoParams = append(protoParams, &aiplatform.PipelineJob_Parameter{
				Name:  key,
				Value: &aiplatform.PipelineJob_Parameter_StringValue{StringValue: v},
			})
		case int:
			protoParams = append(protoParams, &aiplatform.PipelineJob_Parameter{
				Name:  key,
				Value: &aiplatform.PipelineJob_Parameter_IntValue{IntValue: int64(v)},
			})
		case float64:
			protoParams = append(protoParams, &aiplatform.PipelineJob_Parameter{
				Name:  key,
				Value: &aiplatform.PipelineJob_Parameter_DoubleValue{DoubleValue: v},
			})
		case []interface{}:
			var stringValues []string
			for _, val := range v {
				stringValues = append(stringValues, val.(string))
			}
			protoParams = append(protoParams, &aiplatform.PipelineJob_Parameter{
				Name:  key,
				Value: &aiplatform.PipelineJob_Parameter_StringValue{StringValue: stringValues[0]},
			})
		default:
			return "", fmt.Errorf("unsupported parameter type: %T", v)
		}
	}

	// Create the pipeline job
	req := &aiplatform.CreatePipelineJobRequest{
		Parent: fmt.Sprintf("projects/%s/locations/%s", projectID, location),
		PipelineJob: &aiplatform.PipelineJob{
			DisplayName: pipelineJob.DisplayName,
			Template: &aiplatform.PipelineJob_Template{
				TemplatePath: pipelineJob.TemplatePath,
			},
			ParameterValues: protoParams,
			ServiceAccount: &aiplatform.PipelineJob_ServiceAccount{
				ServiceAccount: serviceAccount,
			},
		},
	}
	resp, err := client.CreatePipelineJob(ctx, req)
	if err != nil {
		return "", err
	}

	return resp.GetName(), nil
}

// waitForPipelineJobState waits for the pipeline job to reach a running or failed state
func waitForPipelineJobState(ctx context.Context, client *aiplatform.PipelineServiceClient, pipelineJob *PipelineJob) error {
	attempt := 0
	for attempt <= maxAttemptsStatus {
		err := pipelineJob.GetPipelineJobState(ctx, client)
		if err != nil {
			return err
		}

		switch pipelineJob.State {
		case aiplatform.PipelineState_PIPELINE_STATE_RUNNING, aiplatform.PipelineState_PIPELINE_STATE_FAILED:
			return nil
		}

		time.Sleep(waitIntervalSeconds * time.Second)
		attempt++
	}

	return fmt.Errorf("pipeline job %s did not reach a running or failed state within the timeout", pipelineJob.DisplayName)
}

// Convert an error to a gin.H response
func errorToGinH(err error) gin.H {
	var statusCode int
	var message string

	// Check for NotFound errors
	if status.Code(err) == codes.NotFound {
		statusCode = http.StatusNotFound
		message = "Resource not found."
	} else {
		statusCode = http.StatusInternalServerError
		message = err.Error()
	}

	return gin.H{
		"statusCode": statusCode,
		"message":     message,
	}
}

// Parse the service account key from the request body
func parseServiceAccountKey(request *http.Request) (string, error) {
	// Get the request body
	requestBody, err := ioutil.ReadAll(request.Body)
	if err != nil {
		return "", err
	}
	defer request.Body.Close()

	// Unmarshal the JSON data
	var jsonData map[string]interface{}
	if err := json.Unmarshal(requestBody, &jsonData); err != nil {
		return "", err
	}

	// Extract the service account key
	serviceAccountKey, ok := jsonData["service_account_key"].(string)
	if !ok {
		return "", fmt.Errorf("service_account_key not found in request body")
	}

	return serviceAccountKey, nil
}

// Get the email addresses from the request body
func getEmailAddresses(request *http.Request) ([]string, error) {
	// Get the request body
	requestBody, err := ioutil.ReadAll(request.Body)
	if err != nil {
		return nil, err
	}
	defer request.Body.Close()

	// Unmarshal the JSON data
	var jsonData map[string]interface{}
	if err := json.Unmarshal(requestBody, &jsonData); err != nil {
		return nil, err
	}

	// Extract the email addresses
	emailAddresses, ok := jsonData["email_addresses"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("email_addresses not found in request body")
	}

	// Convert the interface{} array to a string array
	var stringAddresses []string
	for _, email := range emailAddresses {
		stringAddresses = append(stringAddresses, email.(string))
	}

	return stringAddresses, nil
}
