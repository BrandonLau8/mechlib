# KMS key for S3 bucket encryption
# resource "aws_kms_key" "mechlib" {
#   description             = "KMS key for mechlib image bucket encryption"
#   deletion_window_in_days = 7
#   enable_key_rotation     = true
#
#   tags = {
#     Project     = "mechlib"
#     Purpose     = "s3-encryption"
#     Environment = var.environment
#   }
# }
#
# resource "aws_kms_alias" "mechlib" {
#   name          = "alias/mechlib-${var.environment}"
#   target_key_id = aws_kms_key.mechlib.key_id
# }
