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
  region  = var.aws_region
  profile = var.aws_profile

  # Default tags applied to all AWS resources
  # Reduces tag duplication across individual resources
  default_tags {
    tags = {
      Project     = "mechlib"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}
