terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# KMS key for S3 bucket encryption
resource "aws_kms_key" "mechlib_images" {
  description             = "KMS key for mechlib image bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Project     = "mechlib"
    Purpose     = "s3-encryption"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "mechlib_images" {
  name          = "alias/mechlib-images-${var.environment}"
  target_key_id = aws_kms_key.mechlib_images.key_id
}

# Creates S3 Bucket for Mechlib Images
module "mechlib_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = var.bucket_name

  # Force destroy allows bucket deletion even with objects (use carefully)
  force_destroy = var.environment == "dev" ? true : false

  # Server-side encryption with KMS
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.mechlib_images.arn
        sse_algorithm     = "aws:kms"
      }
      bucket_key_enabled = true
    }
  }

  # Encryption enforcement policies
  attach_deny_incorrect_encryption_headers  = true
  attach_deny_incorrect_kms_key_sse         = true
  attach_deny_unencrypted_object_uploads    = true
  attach_deny_ssec_encrypted_object_uploads = true
  allowed_kms_key_arn                       = aws_kms_key.mechlib_images.arn

  # Security policies
  attach_deny_insecure_transport_policy = true
  attach_require_latest_tls_policy      = true

  # Block all public access (use signed URLs for access)
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

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
    Purpose     = "keyboard-images"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM role for application access (optional - for EC2/Lambda)
resource "aws_iam_role" "mechlib_app" {
  count = var.create_app_role ? 1 : 0

  name = "mechlib-app-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "mechlib"
    Environment = var.environment
  }
}

# IAM policy for S3 and KMS access
resource "aws_iam_role_policy" "mechlib_s3_access" {
  count = var.create_app_role ? 1 : 0

  name = "mechlib-s3-access"
  role = aws_iam_role.mechlib_app[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = module.mechlib_bucket.s3_bucket_arn
      },
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${module.mechlib_bucket.s3_bucket_arn}/*"
      },
      {
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.mechlib_images.arn
      }
    ]
  })
}