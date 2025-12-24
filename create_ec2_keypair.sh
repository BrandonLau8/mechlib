#!/bin/bash

# Create ED25519 key pair
# --query extracts only the raw ssh key from the json object
aws ec2 create-key-pair \
    --key-name mechlib-key \
    --key-type ed25519 \
    --query 'KeyMaterial' \
    --output text > ~/.ssh/mechlib-key.pem

# Set permissions
chmod 400 ~/.ssh/mechlib-key.pem

# Verify it was created
aws ec2 describe-key-pairs --key-names mechlib-key