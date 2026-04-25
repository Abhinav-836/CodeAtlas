#!/bin/bash

echo "🚀 CodeAtlas Docker Setup with Ollama Cloud Model"
echo "=================================================="

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend
mkdir -p storage/{uploads,reports,exports,tmp,logs,task_results,repos}
mkdir -p ollama_data
mkdir -p postgres_data
mkdir -p redis_data

# Copy your backend files to backend/ directory
echo "📋 Copying backend files..."
# Assuming your files are in current directory
cp *.py backend/ 2>/dev/null || true
cp requirements.txt backend/ 2>/dev/null || true
cp .env backend/ 2>/dev/null || true

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating .env file..."
    cat > backend/.env << EOF
# CodeAtlas Configuration
API_TITLE="CodeAtlas API"
API_VERSION="1.0.0"
DEBUG=False
API_KEY="your-secure-api-key-here"
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
EOF
    echo "✅ .env file created"
fi

# Start the containers
echo "🐳 Starting Docker containers..."
docker-compose up -d

echo "⏳ Waiting for Ollama to start..."
sleep 10

# Sign in to Ollama (you'll need to do this interactively)
echo ""
echo "⚠️  You need to sign in to Ollama for cloud models:"
echo "   Run this command: docker exec -it codeatlas-ollama ollama signin"
echo ""
echo "📥 After signing in, pull the model:"
echo "   docker exec -it codeatlas-ollama ollama pull gpt-oss:20b-cloud"
echo ""

echo "✅ Setup complete! CodeAtlas is running at:"
echo "   http://localhost:8000"
echo "   http://localhost:8000/docs (API documentation)"
echo ""
echo "📊 Check status: docker-compose ps"
echo "📜 View logs: docker-compose logs -f"