# EC2 Instance for mechlib (PostgreSQL + pgvector + pgbouncer)

# Use battle tested Ubuntu 22.04 LTS (long term support) AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical (Ubuntu)

  # Searches through AWS AMI catalog
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }


  #  - Modern technology (2010s+)
  #  - Full hardware virtualization
  #  - Better performance
  #  - Supports all EC2 instance types (t3, m5, c5, etc.)
  #  - Can use special CPU features (encryption, vector processing)
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# SSH Key Pair (upload public key to AWS)
resource "aws_key_pair" "mechlib" {
  key_name   = var.key_name
  public_key = file("~/.ssh/${var.key_name}.pub")

  tags = {
    Name = "mechlib-key-${var.environment}"
  }
}

# EC2 Instance
resource "aws_instance" "mechlib" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type # t3.small or t3.medium

  # SSH Key Pair (references the key pair resource above)
  key_name = aws_key_pair.mechlib.key_name

  # IAM Role for S3 and CloudWatch access
  iam_instance_profile = aws_iam_instance_profile.mechlib_ec2.name

  # Security Groups (allow SSH and pgbouncer)
  vpc_security_group_ids = [aws_security_group.mechlib.id]

  # EBS Root Volume Configuration
  root_block_device {
    volume_type           = "gp3"  # Uses GP3 (General Purpose SSD v3), AWS's latest generation SSD
    volume_size           = 30 # Allocates 30 GB of disk space for the OS, PostgreSQL, and application data
    iops                  = 3000 # Guarantees 3,000 Input/Output Operations Per Second. This is the baseline for GP3 volumes (you can go up to 16,000 for additional cost).
    throughput            = 125 # Guarantees 125 MB/s throughput. This is the baseline for GP3 (you can go up to 1,000 MB/s for additional cost).

    encrypted             = true # Enables encryption at rest using AWS default key. This encrypts all data stored on the volume.

    # Dev environment: Volume is deleted when the EC2 instance terminates (saves costs, data isn't critical)
    # Prod environment: Volume is preserved when instance terminates (prevents accidental data loss)
    delete_on_termination = var.environment == "dev" ? true : false

    tags = {
      Name = "mechlib-root-volume-${var.environment}"
    }
  }

  # User data script to install Docker on first boot
  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name    = "mechlib-${var.environment}"
    Purpose = "PostgreSQL + pgvector database server"
  }
}

# Outputs
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.mechlib.id
}

output "ec2_public_ip" {
  description = "EC2 public IP address"
  value       = aws_instance.mechlib.public_ip
}

output "ec2_private_ip" {
  description = "EC2 private IP address"
  value       = aws_instance.mechlib.private_ip
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.mechlib.public_ip}"
}
