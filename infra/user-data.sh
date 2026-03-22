#!/bin/bash
set -e

# Log all output
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "--------------------------------"
echo "InfraLens Backend Setup Starting"
echo "--------------------------------"

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
systemctl start docker
systemctl enable docker

# Install AWS CLI
echo "Installing AWS CLI..."
apt-get install -y unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Configure swap (if enabled)
%{ if enable_swap }
echo "Configuring ${swap_size_gb}GB swap space..."
fallocate -l ${swap_size_gb}G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
sysctl vm.swappiness=10
echo 'vm.swappiness=10' | tee -a /etc/sysctl.conf
%{ endif }

# Create app directory
mkdir -p /opt/infralens
cd /opt/infralens

# Wait for IAM instance profile to be available
echo "Waiting for IAM instance profile..."
sleep 30

# Get AWS region and account ID
AWS_REGION="${aws_region}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Authenticate Docker to ECR
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${ecr_repository}

# Fetch secrets from Secrets Manager
echo "Fetching application secrets..."
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id ${secret_arn} --region $AWS_REGION --query SecretString --output text)

# Extract individual secrets
export MONGODB_URL=$(echo $SECRET_JSON | jq -r '.MONGODB_URL')
export QDRANT_URL=$(echo $SECRET_JSON | jq -r '.QDRANT_URL')
export QDRANT_API_KEY=$(echo $SECRET_JSON | jq -r '.QDRANT_API_KEY')
export GROQ_API_KEY=$(echo $SECRET_JSON | jq -r '.GROQ_API_KEY')
export CLERK_SECRET_KEY=$(echo $SECRET_JSON | jq -r '.CLERK_SECRET_KEY')
export CLERK_JWKS_URL=$(echo $SECRET_JSON | jq -r '.CLERK_JWKS_URL')

# Create docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  backend:
    image: ${ecr_repository}:latest
    container_name: infralens-backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=$MONGODB_URL
      - QDRANT_URL=$QDRANT_URL
      - QDRANT_API_KEY=$QDRANT_API_KEY
      - GROQ_API_KEY=$GROQ_API_KEY
      - CLERK_SECRET_KEY=$CLERK_SECRET_KEY
      - CLERK_JWKS_URL=$CLERK_JWKS_URL
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# Pull and start the container
echo "Pulling Docker image..."
docker compose pull

echo "Starting InfraLens backend..."
docker compose up -d

# Create systemd service for auto-restart
cat > /etc/systemd/system/infralens.service <<EOF
[Unit]
Description=InfraLens Backend
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/infralens
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable infralens.service

echo "--------------------------------"
echo "InfraLens Backend Setup Complete"
echo ""--------------------------------"
echo "Backend should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo "Health check: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/health"