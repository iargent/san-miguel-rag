variable "aws_region" {
  description = "AWS region to deploy to"
  type = string
  default = "eu-west-1"
}

variable "bucket_name" {
  description = "S3 bucket name - must be globally unique"
  type = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type = string
  sensitive = true
}

