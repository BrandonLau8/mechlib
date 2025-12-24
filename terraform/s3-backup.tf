# Creates S3 Bucket for Mechlib Backups
module "mechlib_backup_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = var.backup_bucket_name

  # Force destroy allows bucket deletion even with objects (use carefully)
  force_destroy = var.environment == "dev" ? true : false

  # Security policies (uses AWS default SSE-S3 encryption) at rest
  # SSE-S3 (Server-Side Encryption with S3-managed keys) means AWS automatically encrypts your data at rest when it's stored in S3
  server_side_encryption_configuration = {
  rule = {
    apply_server_side_encryption_by_default = {
      sse_algorithm = "AES256" # SSE-S3: AWS manages everything
    }
    # Creates a bucket-level encryption key that's used to encrypt individual object keys
    # Reduces the number of requests to AWS KMS (if you switch to KMS later)
    bucket_key_enabled = true
  }
}

  # In transit
  # This prevents any unencrypted HTTP requests to the bucket. All access must use HTTPS/TLS encryption in transit.
  attach_deny_insecure_transport_policy = true
  # This enforces the use of modern TLS versions (TLS 1.2+), blocking older, less secure protocols.
  attach_require_latest_tls_policy      = true

  # Block all public access (use signed URLs for access)
  block_public_acls       = true # Creating new public ACLs
  block_public_policy     = true # Creating new public bucket policies
  ignore_public_acls      = true # Using existing public ACLs
  restrict_public_buckets = true # Accessing buckets with public policies

  # Versioning for data protection
  versioning = {
    enabled = var.enable_versioning
  }

  # Object ownership
  # Disables ACLs entirely - all objects are owned by the bucket owner (you)
  control_object_ownership = true
  object_ownership         = "BucketOwnerEnforced"


  # Lifecycle rules for cost optimization
  # Manages monthly backups: moves to cheaper storage after 90 days, deletes after 1 year
  lifecycle_rule = [
    {
      id      = "manage-monthly-backups"
      enabled = var.enable_lifecycle_rules

      filter = {
        prefix = ""
      }

      # Move backups to cheaper storage after 90 days (rarely accessed)
      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA" # 46% cheaper than STANDARD
        },
        {
          days          = 180
          storage_class = "GLACIER_IR" # 83% cheaper, instant retrieval if needed
        }
      ]

      # Delete backups after 1 year
      expiration = {
        days = 365
      }

      # # Clean up old versions (if you ever re-upload with same name)
      # noncurrent_version_transition = [
      #   {
      #     days          = 30
      #     storage_class = "STANDARD_IA"
      #   }
      # ]
      #
      # noncurrent_version_expiration = {
      #   days = 90
      # }
    },

    # Cleans up incomplete multipart uploads after 7 days
    # Prevents paying for orphaned partial uploads
    {
      id      = "cleanup-incomplete-uploads"
      enabled = true

      abort_incomplete_multipart_upload_days = 7

      filter = {
        prefix = ""
      }
    }
  ]

}

# S3 Bucket Outputs
output "backup_bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.mechlib_backup_bucket.s3_bucket_id
}

output "backup_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = module.mechlib_backup_bucket.s3_bucket_arn
}

output "backup_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = module.mechlib_backup_bucket.s3_bucket_bucket_regional_domain_name
}

output "backup_bucket_region" {
  description = "Region of the S3 bucket"
  value       = module.mechlib_backup_bucket.s3_bucket_region
}

# Configuration Summary
output "backup_bucket_configuration_summary" {
  description = "Summary of the S3 bucket configuration"
  value = {
    bucket_name        = module.mechlib_backup_bucket.s3_bucket_id
    region             = var.aws_region
    environment        = var.environment
    versioning_enabled = var.enable_versioning
    lifecycle_enabled  = var.enable_lifecycle_rules
  }
}

