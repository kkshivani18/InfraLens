#!/bin/bash
# Load env vars from .env file for tf

ENV_FILE="../app/backend/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Loading secrets from $ENV_FILE for Terraform..."

# Export each variable with TF_VAR_ prefix
export TF_VAR_mongodb_url=$(grep MONGODB_URL $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")
export TF_VAR_qdrant_url=$(grep QDRANT_URL $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")
export TF_VAR_qdrant_api_key=$(grep QDRANT_API_KEY $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")
export TF_VAR_groq_api_key=$(grep GROQ_API_KEY $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")
export TF_VAR_clerk_secret_key=$(grep CLERK_SECRET_KEY $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")
export TF_VAR_clerk_jwks_url=$(grep CLERK_JWKS_URL $ENV_FILE | cut -d '=' -f2- | tr -d '"' | tr -d "'")

echo "Secrets loaded as environment variables"
echo ""
echo "You can now run:"
echo "  terraform plan"
echo "  terraform apply"