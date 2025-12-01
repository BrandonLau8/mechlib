# S3 Bucket Outputs
output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.mechlib_bucket.s3_bucket_id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = module.mechlib_bucket.s3_bucket_arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = module.mechlib_bucket.s3_bucket_bucket_regional_domain_name
}

output "bucket_region" {
  description = "Region of the S3 bucket"
  value       = module.mechlib_bucket.s3_bucket_region
}

# # KMS Key Outputs
# output "kms_key_id" {
#   description = "ID of the KMS key used for bucket encryption"
#   value       = aws_kms_key.mechlib.key_id
# }
#
# output "kms_key_arn" {
#   description = "ARN of the KMS key used for bucket encryption"
#   value       = aws_kms_key.mechlib.arn
# }
#
# # IAM Role Outputs (if created)
# output "app_role_arn" {
#   description = "ARN of the application IAM role"
#   value       = var.create_app_role ? aws_iam_role.mechlib_app[0].arn : null
# }
#
# output "app_role_name" {
#   description = "Name of the application IAM role"
#   value       = var.create_app_role ? aws_iam_role.mechlib_app[0].name : null
# }

# IAM User Outputs
output "iam_user_name" {
  description = "Name of the IAM user"
  value       = aws_iam_user.mechlib_user.name
}

output "iam_user_arn" {
  description = "ARN of the IAM user"
  value       = aws_iam_user.mechlib_user.arn
}

output "iam_access_key_id" {
  description = "Access key ID for the IAM user"
  value       = aws_iam_access_key.mechlib_user.id
  sensitive   = true
}

output "iam_secret_access_key" {
  description = "Secret access key for the IAM user"
  value       = aws_iam_access_key.mechlib_user.secret
  sensitive   = true
}

# Configuration Summary
output "configuration_summary" {
  description = "Summary of the S3 bucket configuration"
  value = {
    bucket_name        = module.mechlib_bucket.s3_bucket_id
    region             = var.aws_region
    environment        = var.environment
    versioning_enabled = var.enable_versioning
    lifecycle_enabled  = var.enable_lifecycle_rules
    cors_enabled       = var.enable_cors
    # encryption         = "KMS"
  }
}
