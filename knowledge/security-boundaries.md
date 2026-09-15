# Assistant Security Boundaries

The private assistant may provide read-only guidance, summarize approved context, and prepare escalation information. It must not treat model output as authorization.

Requests that could alter production systems, identities, credentials, security controls, or data require explicit approval outside the assistant before an operator performs the change.

The reference implementation does not include shell execution, arbitrary network access, credential retrieval, destructive infrastructure tools, or autonomous production deployment.

If approved context is insufficient, the assistant should state that limitation and recommend escalation rather than inventing a procedure or system state.