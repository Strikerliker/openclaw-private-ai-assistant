# OpenClaw Private AI Assistant

A security-focused private AI assistant reference implementation for AWS and local container deployment. The project demonstrates private conversation memory, pluggable model providers, allow-listed tools, approval gates for higher-risk actions, API authentication, audit-friendly behavior, and infrastructure as code.

This repository is a portfolio implementation. It does not claim that the AWS stack is currently deployed, and it does not bundle or represent an upstream OpenClaw distribution.

## What this project demonstrates

- Private assistant orchestration with session-scoped memory
- Local SQLite memory for self-hosted demos
- DynamoDB-backed memory for AWS deployment
- Amazon Bedrock model integration with a deterministic local demo mode
- Allow-listed read-only tools and explicit higher-risk approval gates
- Secrets Manager-backed bearer-token authorization
- API Gateway + Lambda deployment pattern
- Least-privilege IAM separation between authorization and assistant runtime
- CloudWatch operational logging with configurable retention
- Docker deployment that runs the included implementation instead of a placeholder image
- Python unit tests, Bandit scanning, and Terraform validation in GitHub Actions
- A project dashboard that reports implementation and live CI status

## Request flow

```text
Client
  |
  v
API Gateway / Local HTTP Server
  |
  +--> authentication boundary
  |
  v
Assistant Orchestrator
  |        |           |
  |        |           +--> Approved Tool Registry
  |        +--------------> Private Memory Store
  +-----------------------> Model Provider
                               |
                               +--> Amazon Bedrock (AWS mode)
                               +--> Deterministic demo provider (local mode)
```

The model is treated as an untrusted reasoning component. Authorization and tool permissions are enforced in application and infrastructure layers rather than delegated to the model.

## Repository contents

- `src/app.py` — Lambda/API entry point
- `src/assistant.py` — orchestration, grounding, memory, and approval logic
- `src/provider.py` — Bedrock and deterministic local model providers
- `src/memory.py` — SQLite, DynamoDB, and in-memory session stores
- `src/tools.py` — allow-listed tool registry
- `src/authorizer.py` — Secrets Manager-backed API authorizer
- `src/server.py` — local HTTP server
- `knowledge/` — example approved operational guidance
- `tests/` — unit tests for orchestration, tools, memory, API, and authorization
- `terraform/` — AWS infrastructure as code
- `docs/` — architecture, deployment, and security documentation
- `dashboard.html` — project dashboard with live GitHub Actions status
- `.github/workflows/validate.yml` — CI validation

## Local quick start

```bash
cp .env.example .env
docker compose up --build
```

The local service listens on `127.0.0.1:8080` by default when run directly, while the container binds the service inside the container and publishes port 8080 through Docker Compose.

Health check:

```bash
curl http://localhost:8080/health
```

Chat example:

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer change-this-local-token' \
  -d '{"session_id":"demo-session","message":"How should I handle a production access request?"}'
```

By default, local mode uses the deterministic provider so the project can be demonstrated without sending prompts to an external model. Set `PROVIDER_MODE=bedrock` and configure AWS credentials only when you intentionally want Bedrock inference.

## AWS deployment

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform creates the API, Lambda functions, DynamoDB memory table, Secrets Manager secret container, IAM roles, and CloudWatch log groups. The secret value is intentionally initialized out of band so it is not written into Terraform state.

See `docs/deployment.md` for the deployment sequence.

## Security model

- No hardcoded cloud credentials or API tokens
- API token value stays out of Git history and Terraform state
- Separate IAM roles for API authorization and assistant inference
- DynamoDB access is limited to the assistant memory table
- Bedrock permission is limited to the configured model
- Tools are explicitly allow-listed and read-only in the reference implementation
- Higher-risk requests return an approval-required response rather than executing an action
- Prompt content is not written to API Gateway access logs
- Session identifiers are validated before memory access
- Local server authentication uses constant-time token comparison

## Portfolio status

The repository is complete as a reproducible portfolio project: source code, tests, CI, Docker, Terraform, documentation, and dashboard are included. Running `terraform apply` creates billable AWS resources and is intentionally left to the operator.