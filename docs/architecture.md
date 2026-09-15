# Architecture

The implemented reference design separates ingress, authorization, assistant orchestration, model inference, memory, and tool execution.

```text
Client
  |
  v
API Gateway / Local HTTP Server
  |
  +--> Auth boundary
  |
  v
Assistant Orchestrator
  |        |             |
  |        |             +--> Allow-listed read-only tools
  |        +----------------> Private memory
  +-------------------------> Model provider
```

## AWS mode

- API Gateway exposes `GET /health` and protected `POST /v1/chat`.
- A Lambda REQUEST authorizer validates the bearer token stored in AWS Secrets Manager.
- The assistant Lambda stores session-scoped messages in DynamoDB.
- Amazon Bedrock provides model inference.
- CloudWatch captures operational logs without request bodies or authorization headers.
- Terraform creates the IAM roles, API, Lambda functions, memory table, secret container, and log groups.

## Local mode

- The included Python HTTP server requires a local bearer token for chat requests.
- SQLite stores private session history on a Docker volume.
- A deterministic model provider demonstrates grounding and policy behavior without sending prompts to an external model.
- The container runs as a non-root user, drops capabilities, uses `no-new-privileges`, and publishes port 8080 to loopback only.

## Authorization model

The model is not an authorization authority. The application decides which tools exist and which requests require approval. The reference tool registry contains only read-only guidance and escalation-template tools. Requests for destructive, privileged, credential, or production-changing actions are stopped before model inference and returned with `approval_required=true`.

## Memory model

Each conversation is partitioned by a validated `session_id`. AWS mode uses `session_id` as the DynamoDB partition key and an ordered unique message identifier as the sort key. Local mode uses the same logical model in SQLite.

## Model-provider boundary

`src/provider.py` defines a provider interface. The AWS deployment selects Amazon Bedrock, while local mode defaults to a deterministic provider. The Bedrock IAM policy is restricted to the configured foundation-model ARN.

For the expanded threat model and security controls, see `../architecture.md` and `security.md`.