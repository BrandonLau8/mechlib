# IAM User for mechlib application
resource "aws_iam_user" "mechlib_user" {
  name = "mechlib-${var.environment}"

  tags = {
    Purpose = "Application access to S3 bucket"
  }
}

# Creates AWS access keys (Access Key ID + Secret Access Key) for the IAM user when you run terraform apply.
# Long Lived
resource "aws_iam_access_key" "mechlib_user" {
  user = aws_iam_user.mechlib_user.name
}


# IAM Policy for S3 access
# Grants least-privilege permissions for application to work with S3 objects
resource "aws_iam_user_policy" "mechlib_s3_access" {
  name = "mechlib-s3-access"
  user = aws_iam_user.mechlib_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BucketLevelOperations"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",        # List objects in bucket
          "s3:GetBucketLocation"  # Get bucket region (for presigned URLs)
        ]
        Resource = module.mechlib_bucket.s3_bucket_arn # Bucket
      },
      {
        Sid    = "ObjectLevelOperations"
        Effect = "Allow"
        Action = [
          "s3:GetObject",    # Download/read objects (for presigned URLs)
          "s3:PutObject",    # Upload objects
          "s3:DeleteObject"  # Delete objects
        ]
        Resource = "${module.mechlib_bucket.s3_bucket_arn}/*" # Object
      }
    ]
  })
}

# IAM User Outputs
output "iam_user_name" {
  description = "Name of the IAM user"
  value       = aws_iam_user.mechlib_user.name
}

output "iam_user_arn" {
  description = "ARN of the IAM user"
  value       = aws_iam_user.mechlib_user.arn
}

# output "iam_access_key_id" {
#   description = "Access key ID for the IAM user"
#   value       = aws_iam_access_key.mechlib_user.id
#   sensitive   = true
# }
#
# output "iam_secret_access_key" {
#   description = "Secret access key for the IAM user"
#   value       = aws_iam_access_key.mechlib_user.secret
#   sensitive   = true
# }

# Just copy/paste directly into ~/.aws/credentials
output "aws_credentials_example" {
  description = "Example ~/.aws/credentials entry"
  value = <<-EOT
    [mechlib-dev]
    aws_access_key_id = ${aws_iam_access_key.mechlib_user.id}
    aws_secret_access_key = ${aws_iam_access_key.mechlib_user.secret}
  EOT
  sensitive = true
  }

