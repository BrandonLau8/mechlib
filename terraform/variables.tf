variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile"
  type = string
}


variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# S3
variable "data_bucket_name" {
  description = "Name of the Data S3 bucket (must be globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.data_bucket_name))
    error_message = "Bucket name must be lowercase, alphanumeric, and hyphens only (3-63 characters)."
  }
}

variable "backup_bucket_name" {
  description = "Name of the Backup S3 bucket (must be globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.backup_bucket_name))
    error_message = "Bucket name must be lowercase, alphanumeric, and hyphens only (3-63 characters)."
  }
}

variable "enable_versioning" {
  description = "Enable versioning for S3 bucket"
  type        = bool
  default     = false
}

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for cost optimization"
  type        = bool
  default     = true
}

variable "enable_cors" {
  description = "Enable CORS configuration for web access"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = []
}

# EC2
variable "instance_type" {
  description = "EC2 Instance Type"
  type        = string
  default     = "t3.small"
}

# Security Groups for EC2
variable "key_name" {
  description = "SSH key pair name (without .pem extension)"
  type        = string
  default     = "mechlib-key"
}

variable "admin_ip" {
  description = "Your IP address for SSH access (CIDR notation, e.g., 1.2.3.4/32)"
  type        = string
}

variable "app_server_ip" {
  description = "Application server IP for pgbouncer access (CIDR notation, or use 0.0.0.0/0 for anywhere)"
  type        = string
  default     = "0.0.0.0/0" # Allow from anywhere (change for production)
}

# EC2 CloudWatch
variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
}
