#!/bin/bash
# Deployment script for mechlib application
# Deploys code and restarts services on EC2

set -e  # Exit on any error

echo "Starting deployment..."

# Change to terraform directory to get outputs
cd "$(dirname "$0")/terraform"

# Get EC2 IP from Terraform output
echo "Getting EC2 IP address..."
EC2_IP=$(terraform output -raw ec2_public_ip 2>/dev/null || echo "")

if [ -z "$EC2_IP" ]; then
  echo "Error: Could not get EC2 IP. Make sure Terraform is applied."
  exit 1
fi

# SSH key path
KEY_PATH="$HOME/.ssh/mechlib-key.pem"

if [ ! -f "$KEY_PATH" ]; then
  echo "Error: SSH key not found at $KEY_PATH"
  exit 1
fi

echo "Deploying to EC2: $EC2_IP"

# Go back to project root
cd ..

# Get git repository URL (customize this)
GIT_REPO="${GIT_REPO:-git@github.com:yourusername/mechlib.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"

echo "Pulling latest code from git..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@$EC2_IP << ENDSSH
  set -e

  # Clone repo if it doesn't exist, otherwise pull latest
  if [ ! -d "/opt/mechlib/.git" ]; then
    echo "Cloning repository..."
    git clone -b $GIT_BRANCH $GIT_REPO /opt/mechlib
  else
    echo "Pulling latest changes..."
    cd /opt/mechlib
    git fetch origin
    git reset --hard origin/$GIT_BRANCH
  fi

  cd /opt/mechlib

  # Fetch secrets from AWS Secrets Manager and create .env
  echo "Fetching secrets from AWS Secrets Manager..."
  aws secretsmanager get-secret-value \
    --secret-id mechlib/dev/env \
    --query SecretString \
    --output text > .env

  # If using Docker Compose
  if [ -f "docker-compose.yml" ]; then
    echo "Restarting Docker containers..."
    docker compose down
    docker compose pull  # Pull latest images if needed
    docker compose up -d --build
  fi

  # If using systemd service
  # sudo systemctl restart mechlib

  echo "Deployment successful!"
ENDSSH

echo "Deployment complete!"
echo "Check logs with: ssh -i $KEY_PATH ubuntu@$EC2_IP 'docker compose logs -f'"
