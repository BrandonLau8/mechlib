# IAM User for mechlib application
resource "aws_iam_user" "mechlib_user" {
  name = "mechlib-${var.environment}"

  tags = {
    Project     = "mechlib"
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "Application access to S3 bucket"
  }
}

# Access keys for programmatic access
resource "aws_iam_access_key" "mechlib_user" {
  user = aws_iam_user.mechlib_user.name
}


# IAM Policy for S3 and KMS access
resource "aws_iam_user_policy" "mechlib_s3_kms_access" {
  name = "mechlib-s3-kms-access"
  user = aws_iam_user.mechlib_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBucket"
        Effect = "Allow"
        Action = [
          # "s3:ListBucket",
          # "s3:GetBucketLocation",
          "s3:*"

        ]
        Resource = module.mechlib_bucket.s3_bucket_arn
      },
      {
        Sid    = "ObjectAccess"
        Effect = "Allow"
        Action = [
          # "s3:GetObject",
          # "s3:PutObject",
          # "s3:DeleteObject",
          # "s3:GetObjectVersion"
          "s3:*"
        ]
        Resource = "${module.mechlib_bucket.s3_bucket_arn}/*"
      },
      # {
      #   Sid    = "KMSAccess"
      #   Effect = "Allow"
      #   Action = [
      #     "kms:Decrypt",
      #     "kms:Encrypt",
      #     "kms:GenerateDataKey",
      #     "kms:DescribeKey"
      #   ]
      #   Resource = aws_kms_key.mechlib.arn
      # }
    ]
  })
}

# # IAM role for application access (optional - for EC2/Lambda)
# resource "aws_iam_role" "mechlib_app" {
#   count = var.create_app_role ? 1 : 0
#
#   name = "mechlib-app-${var.environment}"
#
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "ec2.amazonaws.com"
#         }
#       }
#     ]
#   })
#
#   tags = {
#     Project     = "mechlib"
#     Environment = var.environment
#   }
# }
#
# # IAM policy for S3 and KMS access for application access
# resource "aws_iam_role_policy" "mechlib_s3_access" {
#   count = var.create_app_role ? 1 : 0
#
#   name = "mechlib-s3-access"
#   role = aws_iam_role.mechlib_app[0].id
#
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Sid    = "S3BucketAccess"
#         Effect = "Allow"
#         Action = [
#           "s3:ListBucket",
#           "s3:GetBucketLocation"
#         ]
#         Resource = module.mechlib_bucket.s3_bucket_arn
#       },
#       {
#         Sid    = "S3ObjectAccess"
#         Effect = "Allow"
#         Action = [
#           "s3:GetObject",
#           "s3:PutObject",
#           "s3:DeleteObject"
#         ]
#         Resource = "${module.mechlib_bucket.s3_bucket_arn}/*"
#       },
#       {
#         Sid    = "KMSAccess"
#         Effect = "Allow"
#         Action = [
#           "kms:Decrypt",
#           "kms:Encrypt",
#           "kms:GenerateDataKey"
#         ]
#         Resource = aws_kms_key.mechlib.arn
#       }
#     ]
#   })
# }
