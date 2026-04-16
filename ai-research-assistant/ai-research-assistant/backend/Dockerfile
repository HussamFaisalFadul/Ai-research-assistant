# ======================================================
# AI Research Assistant - HuggingFace Spaces Dockerfile
# Runs: Ollama + FastAPI in a single container
# ======================================================
FROM python:3.11-slim

# Install system dependencies + Ollama
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ ./app/

# Create necessary directories
RUN mkdir -p ./data ./chroma_db

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# HuggingFace Spaces uses port 7860
EXPOSE 7860

ENV OLLAMA_BASE_URL=http://localhost:11434
ENV OLLAMA_MODEL=qwen2.5:3b
ENV CHROMA_DB_PATH=./chroma_db
ENV UPLOAD_FOLDER=./data

CMD ["./start.sh"]
