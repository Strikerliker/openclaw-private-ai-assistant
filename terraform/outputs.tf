output "api_url" {
  description = "Base URL for the private assistant API."
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "api_token_secret_arn" {
  description = "Secrets Manager secret ARN whose value should be initialized out of band."
  value       = aws_secretsmanager_secret.api_token.arn
}

output "memory_table_name" {
  description = "DynamoDB table used for private conversation memory."
  value       = aws_dynamodb_table.memory.name
}

output "assistant_lambda_name" {
  description = "Assistant Lambda function name."
  value       = aws_lambda_function.assistant.function_name
}
