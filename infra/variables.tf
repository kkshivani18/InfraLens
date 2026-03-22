variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "infralens"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"

  validation {
    condition     = contains(["t3.micro", "t3.small", "t3.medium"], var.instance_type)
    error_message = "Instance type must be t3.micro"
  }
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (your IP address/32)"
  type        = string
}

# Environment Variables for Application
variable "mongodb_url" {
  description = "MongoDB Atlas connection string"
  type        = string
  sensitive   = true
}

variable "qdrant_url" {
  description = "Qdrant Cloud endpoint URL"
  type        = string
  sensitive   = true
}

variable "qdrant_api_key" {
  description = "Qdrant Cloud API key"
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key for LLM"
  type        = string
  sensitive   = true
}

variable "clerk_secret_key" {
  description = "Clerk secret key for authentication"
  type        = string
  sensitive   = true
}

variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT verification"
  type        = string
  sensitive   = true
}

variable "enable_swap" {
  description = "Enable swap space for t2.micro instances (helps with memory constraints)"
  type        = bool
  default     = true
}

variable "swap_size_gb" {
  description = "Swap file size in GB (only used if enable_swap is true)"
  type        = number
  default     = 2
}