#!/bin/bash

# UnSearch Digital Ocean Deployment Script
# This script automates the deployment process on a fresh Ubuntu 22.04 droplet

set -e  # Exit on error

echo "========================================="
echo "UnSearch Digital Ocean Deployment"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

echo "Step 1: Update system..."
apt update && apt upgrade -y

echo ""
echo "Step 2: Installing Docker..."
apt install -y apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo ""
echo "Step 3: Verifying Docker installation..."
docker --version
docker compose version

echo ""
echo "Step 4: Installing Certbot for SSL..."
apt install -y certbot python3-certbot-nginx

echo ""
echo "Step 5: Creating unsearch user..."
if id "unsearch" &>/dev/null; then
    echo "User 'unsearch' already exists"
else
    adduser --disabled-password --gecos "" unsearch
    usermod -aG sudo unsearch
    usermod -aG docker unsearch
    echo "User 'unsearch' created"
fi

echo ""
echo "Step 6: Setting up UFW firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

echo ""
echo "========================================="
echo "Base installation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Switch to unsearch user: su - unsearch"
echo "2. Clone repository: git clone <repo-url>"
echo "3. Configure .env file"
echo "4. Obtain SSL certificates:"
echo "   sudo certbot certonly --standalone -d api.unsearch.dev"
echo "   sudo certbot certonly --standalone -d unsearch.dev -d www.unsearch.dev"
echo "5. Deploy: docker compose up -d"
echo ""
echo "See full guide: docs/deployment-digitalocean.md"
