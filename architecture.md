# OpenClaw Private AI Assistant Architecture

## Design objective

Build a private assistant whose memory, authentication, tool permissions, and operational controls remain under the operator's control. The language model is treated as an untrusted reasoning component: it can generate text, but it does not decide what infrastructure permissions exist or whether a higher-risk action is authorized.

## Implemented flow

```text
Client
  |
  v
API Gateway (AWS) or local HTTP server
  |
  +--> authentication boundary
  |      AWS: Lambda authorizer + Secrets Manager
  |      Local: constant-time bearer-token validation
  |
  v
Assistant Orchestrator
  |        |             |
  |        |             +--> Allow-listed read-only tools
  |        +----------------> Private memory
  |                             AWS: DynamoDB
  |                             Local: SQLite
  |
  +--------------------------> Model provider
                                 AWS: Amazon Bedrock
                                 Local: deterministic demo provider

CloudWatch receives API and Lambda operational telemetry in AWS mode.
```

## Trust boundaries

### Client to ingress

Only `GET /health` is public in the AWS reference architecture. `POST /v1/chat` requires a bearer token validated by a Lambda authorizer. The local server also requires a bearer token for chat requests and fails closed when no local token is configured.

### Ingress to assistant runtime

API Gateway can invoke only the configured Lambda functions. The assistant Lambda does not have permission to read the API authentication secret.

### Assistant to memory

The AWS assistant role is scoped to `PutItem` and `Query` on a single DynamoDB table. The local implementation uses a SQLite database stored on a dedicated Docker volume.

### Assistant to model provider

The AWS assistant role can invoke only the configured Bedrock foundation-model ARN. Local demo mode does not require an external model and uses a deterministic provider so the control flow can be demonstrated without sending prompts outside the container.

### Assistant to tools

Tools are registered explicitly in `src/tools.py`. The reference implementation exposes only read-only guidance and escalation-template tools. Unknown tool names are rejected. Higher-risk requests are intercepted by the orchestrator and returned as `approval_required` instead of being executed.

## Memory model

Conversation history is keyed by a validated `session_id`. The assistant retrieves only the most recent session messages and does not search across unrelated session identifiers. The AWS table uses `session_id` as the partition key and a time-ordered message identifier as the sort key.

## Security controls

- No hardcoded AWS credentials or bearer tokens
- Secrets Manager secret value initialized outside Terraform state
- Separate IAM roles for authorization and assistant execution
- Least-privilege DynamoDB and Bedrock permissions
- Constant-time bearer-token comparison
- Session identifier validation
- Message-size validation
- Explicit tool allow-list
- Higher-risk approval gate
- No prompt or authorization-header content in API Gateway access logs
- CloudWatch retention is configurable
- DynamoDB encryption at rest and point-in-time recovery
- Local Docker process runs as a non-root user
- Local container drops Linux capabilities and enables `no-new-privileges`
- CI runs unit tests, Bandit, Docker build, and Terraform validation

## Threat considerations

### Prompt injection

The model never receives authority to add tools or permissions. Application code decides which tools can run and rejects unregistered names.

### Destructive or privileged actions

Requests matching high-risk operational actions return an approval-required response and an escalation template. The reference implementation does not include destructive tools.

### Secret exposure

The API token is not stored in source code or Terraform state. API access logs exclude authorization headers and request bodies.

### Memory leakage

Session identifiers are validated and memory access is partitioned by session. Operators should apply retention policies appropriate to their environment before production use.

### Model-provider outage or error

Provider failures return approved operational guidance and clearly state that no action was taken.

## Production expansion path

A production deployment could add enterprise OIDC/JWT authentication, AWS WAF, VPC-connected Lambda or ECS, customer-managed KMS keys, Bedrock Guardrails, automated secret rotation, fine-grained user/role memory partitions, structured audit events, alarms, traces, approval workflows, and a dedicated policy engine.