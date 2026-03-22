output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.backend.public_ip
}

output "backend_url" {
  description = "Backend API URL"
  value       = "http://${aws_eip.backend.public_ip}:8000"
}

output "health_check_url" {
  description = "Health check endpoint"
  value       = "http://${aws_eip.backend.public_ip}:8000/health"
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.backend.repository_url
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/your-key.pem ubuntu@${aws_eip.backend.public_ip}"
}

output "docker_push_commands" {
  description = "Commands to push Docker image to ECR"
  value = <<-EOT
    # Authenticate Docker to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}
    
    # Build and tag Docker image
    cd app/backend
    docker build -t ${var.project_name}-backend .
    docker tag ${var.project_name}-backend:latest ${aws_ecr_repository.backend.repository_url}:latest
    
    # Push to ECR
    docker push ${aws_ecr_repository.backend.repository_url}:latest
  EOT
}

output "cors_update_required" {
  description = "Add this IP to your backend CORS configuration"
  value       = "Add 'http://${aws_eip.backend.public_ip}:8000' to CORS allowed origins"
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront domain for HTTPS API access"
  value       = aws_cloudfront_distribution.backend_api.domain_name
}

output "cloudfront_api_url" {
  description = "HTTPS API base URL to use in Vercel"
  value       = "https://${aws_cloudfront_distribution.backend_api.domain_name}"
}

output "cloudfront_health_check_url" {
  description = "CloudFront health check endpoint"
  value       = "https://${aws_cloudfront_distribution.backend_api.domain_name}/health"
}