# Load environment variables from backend .env file for Terraform
# PowerShell version

$envFile = "..\app\backend\.env"

if (-not (Test-Path $envFile)) {
    Write-Error "❌ .env file not found at $envFile"
    exit 1
}

Write-Host "📦 Loading secrets from $envFile for Terraform..." -ForegroundColor Cyan

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim() -replace '^["'']|["'']$'
        
        switch ($name) {
            "MONGODB_URL" { 
                $env:TF_VAR_mongodb_url = $value 
                Write-Host "  ✓ TF_VAR_mongodb_url" -ForegroundColor Green
            }
            "QDRANT_URL" { 
                $env:TF_VAR_qdrant_url = $value 
                Write-Host "  ✓ TF_VAR_qdrant_url" -ForegroundColor Green
            }
            "QDRANT_API_KEY" { 
                $env:TF_VAR_qdrant_api_key = $value 
                Write-Host "  ✓ TF_VAR_qdrant_api_key" -ForegroundColor Green
            }
            "GROQ_API_KEY" { 
                $env:TF_VAR_groq_api_key = $value 
                Write-Host "  ✓ TF_VAR_groq_api_key" -ForegroundColor Green
            }
            "CLERK_SECRET_KEY" { 
                $env:TF_VAR_clerk_secret_key = $value 
                Write-Host "  ✓ TF_VAR_clerk_secret_key" -ForegroundColor Green
            }
            "CLERK_JWKS_URL" { 
                $env:TF_VAR_clerk_jwks_url = $value 
                Write-Host "  ✓ TF_VAR_clerk_jwks_url" -ForegroundColor Green
            }
        }
    }
}

Write-Host ""
Write-Host "✅ Secrets loaded successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Now run: terraform plan" -ForegroundColor Yellow
