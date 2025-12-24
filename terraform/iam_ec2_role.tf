# IAM Role for EC2 Instance
# This role allows the EC2 instance to access S3, CloudWatch, and Systems Manager
# without needing hardcoded AWS credentials

# Create the IAM Role
resource "aws_iam_role" "mechlib_ec2" {
  name = "mechlib-ec2-role-${var.environment}"

  # Trust policy: allows EC2 service to assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Purpose = "EC2 instance role for S3 and CloudWatch access"
  }
}

# Custom S3 Policy (least-privilege)
# Allows EC2 to work with S3 objects (same permissions as IAM user)
resource "aws_iam_role_policy" "s3_access" {
  name = "mechlib-s3-access"
  role = aws_iam_role.mechlib_ec2.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BucketLevelOperations"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = module.mechlib_bucket.s3_bucket_arn # Bucket
      },
      {
        Sid    = "ObjectLevelOperations"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${module.mechlib_bucket.s3_bucket_arn}/*" # Object
      }
    ]
  })
}

# Attach CloudWatch Logs Policy
# Allows EC2 to write application logs and metrics to CloudWatch
resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = aws_iam_role.mechlib_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# Attach Systems Manager Policy (Optional but Recommended)
# Allows remote access via Session Manager without SSH keys
# If I lose SSH key I can connect through console
# Also enables patch management and run commands
resource "aws_iam_role_policy_attachment" "ssm_access" {
  role       = aws_iam_role.mechlib_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Create Instance Profile
# EC2 instances use instance profiles (not roles directly)
# Instance Profile = A wrapper that holds an IAM role so EC2 can use it. Like a wallet for an ID
resource "aws_iam_instance_profile" "mechlib_ec2" {
  name = "mechlib-ec2-profile-${var.environment}"
  role = aws_iam_role.mechlib_ec2.name
}

# Allow AWS Secrets Manager
resource "aws_iam_role_policy_attachment" "secrets_manager" {
  role       = aws_iam_role.mechlib_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}



output "ec2_instance_profile_name" {
  description = "Instance profile name to attach to EC2 instance"
  value       = aws_iam_instance_profile.mechlib_ec2.name
}

output "ec2_instance_profile_arn" {
  description = "Instance profile ARN"
  value       = aws_iam_instance_profile.mechlib_ec2.arn
}

output "ec2_role_name" {
  description = "IAM role name"
  value       = aws_iam_role.mechlib_ec2.name
}

output "ec2_role_arn" {
  description = "IAM role ARN"
  value       = aws_iam_role.mechlib_ec2.arn
}
