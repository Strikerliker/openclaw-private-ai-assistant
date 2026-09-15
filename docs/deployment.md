# Deployment Guide

## Local Docker demo

1. Copy the example configuration:

```bash
cp .env.example .env
```

2. Set a long random value for `LOCAL_API_TOKEN` in `.env`.
3. Keep `PROVIDER_MODE=deterministic` for the offline demo.
4. Start the service:

```bash
docker compose up --build
```

5. Verify health:

```bash
curl http://localhost:8080/health
```

6. Send a protected chat request:

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_LOCAL_TOKEN' \
  -d '{"session_id":"demo-session","message":"What is the approved process for production access?"}'
```

The Compose file publishes the service only to host loopback and stores SQLite memory in a Docker volume.

## AWS reference deployment

### Prerequisites

- Terraform 1.6 or newer
- AWS credentials obtained outside this repository
- Permission to create API Gateway, Lambda, DynamoDB, Secrets Manager, IAM, and CloudWatch resources
- Access to the configured Amazon Bedrock model in the selected region

### Validate before deployment

```bash
cd terraform
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
```

### Plan and apply

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Initialize the API token out of band

Terraform creates only the Secrets Manager secret container. It intentionally does not place the bearer-token value in Terraform configuration or state.

```bash
SECRET_ARN="$(terraform output -raw api_token_secret_arn)"
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ARN" \
  --secret-string 'REPLACE_WITH_A_LONG_RANDOM_TOKEN'
```

### Verify the API

```bash
API_URL="$(terraform output -raw api_url)"

curl "$API_URL/health"

curl -X POST "$API_URL/v1/chat" \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer REPLACE_WITH_A_LONG_RANDOM_TOKEN' \
  -d '{"session_id":"portfolio-demo","message":"How should a privileged access request be handled?"}'
```

A higher-risk request such as a destructive production change should return HTTP 202 with `approval_required=true` instead of executing an action.

## Operations

- Rotate the API token through Secrets Manager without changing application code.
- Review CloudWatch logs without adding prompt bodies or authorization headers to access logging.
- Review DynamoDB retention requirements before using real organizational conversations.
- Change the configured Bedrock model only after validating regional availability and IAM scope.
- Use enterprise OIDC/JWT authentication rather than a shared bearer token for a real multi-user production environment.

## Cleanup

```bash
cd terraform
terraform destroy
```

AWS resources can incur charges while deployed. This repository is validated as infrastructure as code; deployment into a real account is an explicit operator action.