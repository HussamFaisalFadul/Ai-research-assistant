import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
