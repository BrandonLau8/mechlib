#!/bin/bash
# EC2 Initial Setup Script
# Runs once when instance first launches
# Installs Docker, Docker Compose, and sets up application directory

set -e  # Exit on any error

# Log all output to file for debugging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting mechlib EC2 setup..."

# Update system packages
echo "Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Add ubuntu user to docker group (allows running docker without sudo)
usermod -aG docker ubuntu

# Install Docker Compose
echo "Installing Docker Compose..."
apt-get install -y docker-compose-plugin

# Install useful utilities
echo "Installing utilities..."
apt-get install -y \
  htop \
  curl \
  wget \
  git \
  unzip \
  jq

# Install AWS CLI (for Secrets Manager access)
echo "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Enable Docker service
echo "Enabling Docker service..."
systemctl enable docker
systemctl start docker

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/mechlib
chown ubuntu:ubuntu /opt/mechlib

# Note: Application code should be deployed separately via deploy.sh
# which will clone from git and fetch secrets from AWS Secrets Manager

echo "EC2 setup complete!"
echo "Setup completed at: $(date)" >> /var/log/user-data.log
