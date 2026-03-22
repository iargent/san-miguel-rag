resource "aws_lambda_function" "cv_optimiser" {
  filename         = "../deployment.zip"
  function_name    = "cv-optimiser"
  role             = aws_iam_role.lambda.arn
  handler          = "main.handler"
  runtime          = "python3.14"
  timeout          = 30
  memory_size      = 256
  source_code_hash = filebase64sha256("../deployment.zip")

  environment {
    variables = {
      ANTHROPIC_API_KEY = var.anthropic_api_key
    }
  }
}