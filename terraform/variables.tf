variable "aws_region" {
  description = "AWS region for the private assistant stack."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "openclaw-private-ai-assistant"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "portfolio"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID available in the deployment region."
  type        = string
  default     = "amazon.nova-lite-v1:0"
}

variable "allowed_origins" {
  description = "Optional browser origins allowed by API Gateway CORS. Leave empty for non-browser clients."
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention period."
  type        = number
  default     = 30
}

variable "throttling_burst_limit" {
  description = "API Gateway burst limit."
  type        = number
  default     = 20
}

variable "throttling_rate_limit" {
  description = "API Gateway steady-state requests per second."
  type        = number
  default     = 10
}

variable "tags" {
  description = "Additional tags applied to supported resources."
  type        = map(string)
  default     = {}
}
