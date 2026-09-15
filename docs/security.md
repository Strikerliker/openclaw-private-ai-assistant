# Security Model

## Core rule

The language model is not trusted to authorize actions. Identity, permissions, tool availability, memory access, and approval requirements are enforced outside the model.

## Implemented controls

- Protected chat route with bearer-token authentication
- Secrets Manager-backed token in AWS mode
- Constant-time token comparison
- Separate IAM roles for the authorizer and assistant runtime
- Bedrock access restricted to the configured model ARN
- DynamoDB permissions restricted to the project memory table
- Session identifiers validated before memory access
- Request length validation
- Read-only tool registry with unknown tools rejected
- Approval gate for destructive, privileged, credential, and production-changing requests
- API Gateway access logs exclude prompt bodies and authorization headers
- DynamoDB point-in-time recovery and encryption at rest
- Non-root local container with dropped Linux capabilities
- CI unit tests, Bandit scan, Docker build, and Terraform validation

## Approval-gated request examples

The reference orchestrator will not automatically execute requests that include actions such as:

- granting administrator access
- deleting or destroying resources
- resetting passwords
- rotating secrets
- shutting down or restarting production systems
- changing security groups or firewall rules
- executing arbitrary commands
- deploying directly to production

The response returns `approval_required=true` together with approved guidance and an escalation template.

## Prompt injection boundary

A prompt cannot add a new tool to the registry, broaden an IAM policy, read the API secret, or bypass the application approval gate. The model receives text context but not authorization authority.

## Logging

API Gateway logs request metadata only. The project does not configure prompt bodies or bearer tokens in gateway access logs. Operators should apply the same principle to any additional application telemetry.

## Memory and privacy

The reference design stores session history because memory is a project requirement. Real deployments should define retention, deletion, access, backup, and legal/compliance policies before storing organizational conversations. Sensitive secrets should never be placed in prompts or memory.

## Production hardening roadmap

For a production multi-user deployment, replace the shared token with enterprise OIDC/JWT identity, add role-aware authorization, AWS WAF, customer-managed KMS keys, Bedrock Guardrails, automated secret rotation, audit event export, alarms, tracing, policy-as-code, and a separate human approval workflow for privileged tools.