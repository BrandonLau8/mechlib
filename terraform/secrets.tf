# AWS Secrets Manager for application environment variables
# Structure created by Terraform, actual values set manually via AWS CLI

resource "aws_secretsmanager_secret" "mechlib_env" {
  name        = "mechlib/${var.environment}/env"
  description = "Environment variables for mechlib application"

  recovery_window_in_days = 7  # 7 day recovery window if accidentally deleted

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Placeholder secret version (replace with actual values via AWS CLI)
resource "aws_secretsmanager_secret_version" "mechlib_env" {
  secret_id     = aws_secretsmanager_secret.mechlib_env.id

  # Placeholder - actual values should be set via AWS CLI
  secret_string = jsonencode({
    PLACEHOLDER = "Run command to update secret values"
  })

  lifecycle {
    # Prevents Terraform from overwriting manual updates after setting all the secret values
    ignore_changes = [secret_string]
  }
}

# Outputs
output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.mechlib_env.name
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.mechlib_env.arn
}

output "update_secrets_command" {
  description = "Command to update secret values"
  value       = <<-EOT
    aws secretsmanager update-secret \
      --secret-id ${aws_secretsmanager_secret.mechlib_env.name} \
      --secret-string file://secrets.json
      }'
  EOT
}
