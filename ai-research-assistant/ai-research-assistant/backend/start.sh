#!/bin/bash
# ======================================================
# Startup script for HuggingFace Spaces
# Starts Ollama in background, then FastAPI on port 7860
# ======================================================

echo "🚀 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    sleep 2
    echo "  Attempt $i/30..."
done

# Pull the model
echo "📥 Pulling model: $OLLAMA_MODEL"
ollama pull $OLLAMA_MODEL
echo "✅ Model ready!"

# Start FastAPI on port 7860 (required by HF Spaces)
echo "🌐 Starting FastAPI on port 7860..."
uvicorn app.main:app --host 0.0.0.0 --port 7860 --workers 1

# If FastAPI exits, kill Ollama
kill $OLLAMA_PID
