data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Portfolio   = "John-D"
    },
    var.tags
  )
  bedrock_model_arn = "arn:${data.aws_partition.current.partition}:bedrock:${data.aws_region.current.name}::foundation-model/${var.bedrock_model_id}"
}

resource "aws_dynamodb_table" "memory" {
  name         = "${local.name_prefix}-memory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "message_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "message_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "api_token" {
  name                    = "${local.name_prefix}-api-token"
  description             = "Bearer token for the OpenClaw private assistant API authorizer."
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/openclaw-private-assistant.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "authorizer" {
  name               = "${local.name_prefix}-authorizer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role" "assistant" {
  name               = "${local.name_prefix}-assistant-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "authorizer_logs" {
  role       = aws_iam_role.authorizer.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "assistant_logs" {
  role       = aws_iam_role.assistant.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "authorizer" {
  statement {
    sid       = "ReadApiToken"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.api_token.arn]
  }
}

resource "aws_iam_role_policy" "authorizer" {
  name   = "${local.name_prefix}-authorizer-policy"
  role   = aws_iam_role.authorizer.id
  policy = data.aws_iam_policy_document.authorizer.json
}

data "aws_iam_policy_document" "assistant" {
  statement {
    sid    = "PrivateMemoryAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query"
    ]
    resources = [aws_dynamodb_table.memory.arn]
  }

  statement {
    sid       = "InvokeConfiguredBedrockModel"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.bedrock_model_arn]
  }
}

resource "aws_iam_role_policy" "assistant" {
  name   = "${local.name_prefix}-assistant-policy"
  role   = aws_iam_role.assistant.id
  policy = data.aws_iam_policy_document.assistant.json
}

resource "aws_cloudwatch_log_group" "authorizer" {
  name              = "/aws/lambda/${local.name_prefix}-authorizer"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "assistant" {
  name              = "/aws/lambda/${local.name_prefix}-assistant"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_lambda_function" "authorizer" {
  function_name = "${local.name_prefix}-authorizer"
  description   = "Validates private-assistant bearer tokens against AWS Secrets Manager."
  role          = aws_iam_role.authorizer.arn
  runtime       = "python3.12"
  handler       = "authorizer.lambda_handler"
  timeout       = 10
  memory_size   = 256

  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  environment {
    variables = {
      API_TOKEN_SECRET_ARN = aws_secretsmanager_secret.api_token.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.authorizer,
    aws_iam_role_policy.authorizer,
    aws_iam_role_policy_attachment.authorizer_logs
  ]

  tags = local.common_tags
}

resource "aws_lambda_function" "assistant" {
  function_name = "${local.name_prefix}-assistant"
  description   = "Private AI assistant with controlled memory, tools, and Amazon Bedrock inference."
  role          = aws_iam_role.assistant.arn
  runtime       = "python3.12"
  handler       = "app.lambda_handler"
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  environment {
    variables = {
      MEMORY_BACKEND = "dynamodb"
      MEMORY_TABLE   = aws_dynamodb_table.memory.name
      PROVIDER_MODE  = "bedrock"
      MODEL_ID       = var.bedrock_model_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.assistant,
    aws_iam_role_policy.assistant,
    aws_iam_role_policy_attachment.assistant_logs
  ]

  tags = local.common_tags
}

resource "aws_apigatewayv2_api" "api" {
  name          = local.name_prefix
  protocol_type = "HTTP"

  dynamic "cors_configuration" {
    for_each = length(var.allowed_origins) > 0 ? [1] : []
    content {
      allow_origins = var.allowed_origins
      allow_methods = ["GET", "POST", "OPTIONS"]
      allow_headers = ["authorization", "content-type"]
      max_age       = 300
    }
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_integration" "assistant" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.assistant.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_authorizer" "token" {
  api_id                            = aws_apigatewayv2_api.api.id
  name                              = "${local.name_prefix}-token-authorizer"
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.authorizer.invoke_arn
  identity_sources                  = ["$request.header.Authorization"]
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  authorizer_result_ttl_in_seconds  = 0
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.assistant.id}"
}

resource "aws_apigatewayv2_route" "chat" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /v1/chat"
  target             = "integrations/${aws_apigatewayv2_integration.assistant.id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.token.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit  = var.throttling_rate_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
      sourceIp         = "$context.identity.sourceIp"
    })
  }

  tags = local.common_tags
}

resource "aws_lambda_permission" "api_assistant" {
  statement_id  = "AllowApiGatewayInvokeAssistant"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.assistant.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_authorizer" {
  statement_id  = "AllowApiGatewayInvokeAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/authorizers/${aws_apigatewayv2_authorizer.token.id}"
}
