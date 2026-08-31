import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

# Google Gmail OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://hussamfaisal-ai-research-backend.hf.space/api/gmail/callback"
)
