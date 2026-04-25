# setup.ps1 - Minimal Working Version
Write-Host "======================================"
Write-Host "CodeAtlas Docker Setup"
Write-Host "======================================"
Write-Host ""

# Create directories
Write-Host "Creating directories..."
$folders = @("storage\uploads", "storage\reports", "storage\exports", "storage\tmp", "storage\logs", "storage\task_results", "storage\repos", "ollama_data")
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    Write-Host "  Created: $folder"
}

# Create .env file
if (-not (Test-Path "backend\.env")) {
    Write-Host "`nCreating backend\.env file..."
    @"
# CodeAtlas Configuration
API_TITLE="CodeAtlas API"
API_VERSION="1.0.0"
DEBUG=false
API_KEY="your-api-key-here"
DATABASE_URL="sqlite+aiosqlite:///./codeatlas.db"
UPLOAD_DIR="storage/uploads"
REPORT_DIR="storage/reports"
EXPORT_DIR="storage/exports"
LLM_PROVIDER="ollama"
OLLAMA_BASE_URL="http://ollama:11434"
LLM_MODEL="gpt-oss:20b-cloud"
ENABLE_AI_SUMMARIES="true"
ENABLE_AI_README="true"
ENABLE_AI_INSIGHTS="true"
"@ | Out-File -FilePath "backend\.env" -Encoding ASCII
    Write-Host "  Created backend\.env"
}

# Check Docker
Write-Host "`nChecking Docker..."
$dockerCheck = docker info 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Docker is running"
} else {
    Write-Host "  ERROR: Docker is not running"
    Write-Host "  Please start Docker Desktop first"
    exit 1
}

# Start containers
Write-Host "`nStarting containers..."
docker-compose up -d

Write-Host "`nWaiting 20 seconds for containers to start..."
Start-Sleep -Seconds 20

Write-Host "`nContainer Status:"
docker-compose ps

Write-Host "`n======================================"
Write-Host "Next Steps:"
Write-Host "1. Sign in to Ollama:"
Write-Host "   docker exec -it codeatlas-ollama ollama signin"
Write-Host ""
Write-Host "2. Pull the model:"
Write-Host "   docker exec -it codeatlas-ollama ollama pull gpt-oss:20b-cloud"
Write-Host ""
Write-Host "3. Access CodeAtlas:"
Write-Host "   http://localhost:8000"
Write-Host "   http://localhost:8000/docs"
Write-Host "======================================"
