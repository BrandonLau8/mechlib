# Creates S3 Bucket for Mechlib Images
module "mechlib_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = var.bucket_name

  # Force destroy allows bucket deletion even with objects (use carefully)
  force_destroy = var.environment == "dev" ? true : false

  # # Server-side encryption with KMS
  # server_side_encryption_configuration = {
  #   rule = {
  #     apply_server_side_encryption_by_default = {
  #       kms_master_key_id = aws_kms_key.mechlib.arn
  #       sse_algorithm     = "aws:kms"
  #     }
  #     bucket_key_enabled = true
  #   }
  # }

  # Encryption enforcement policies
  # attach_deny_incorrect_encryption_headers  = true
  # attach_deny_incorrect_kms_key_sse         = true
  # attach_deny_unencrypted_object_uploads    = true
  # attach_deny_ssec_encrypted_object_uploads = true
  # allowed_kms_key_arn                       = aws_kms_key.mechlib.arn

  # Security policies
  attach_deny_insecure_transport_policy = true
  attach_require_latest_tls_policy      = true

  # # Block all public access (use signed URLs for access)
  # block_public_acls       = true
  # block_public_policy     = true
  # ignore_public_acls      = true
  # restrict_public_buckets = true

  # Versioning for data protection
  versioning = {
    enabled = var.enable_versioning
  }

  # Object ownership
  control_object_ownership = true
  object_ownership         = "BucketOwnerEnforced"

  # Lifecycle rules for cost optimization
  lifecycle_rule = [
    {
      id      = "transition-old-images"
      enabled = var.enable_lifecycle_rules

      filter = {
        prefix = ""
      }

      # Move to cheaper storage classes over time
      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
        },
        {
          days          = 365
          storage_class = "GLACIER_IR"
        }
      ]

      # # Clean up old versions
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
    {
      id      = "cleanup-incomplete-uploads"
      enabled = true

      abort_incomplete_multipart_upload_days = 7

      filter = {
        prefix = ""
      }
    }
  ]

  # CORS configuration (optional, enable if accessing from web app)
  cors_rule = var.enable_cors ? [
    {
      allowed_methods = ["GET", "HEAD"]
      allowed_origins = var.cors_allowed_origins
      allowed_headers = ["*"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3600
    }
  ] : []

  tags = {
    Project     = "mechlib"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
