from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx
import os

from app.routers import upload, query
from app.core.vector_store import init_vector_store, get_documents_count
from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL

async def pull_model_if_needed():
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            model_base = OLLAMA_MODEL.split(":")[0]
            if not any(model_base in m for m in models):
                print(f"📥 Pulling model {OLLAMA_MODEL}...")
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": OLLAMA_MODEL},
                ) as stream:
                    async for line in stream.aiter_lines():
                        if line:
                            print(line[:100])
                print("✅ Model ready")
            else:
                print(f"✅ Model {OLLAMA_MODEL} already present")
        except Exception as e:
            print(f"⚠️ Ollama check failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting AI Research Assistant...")
    os.makedirs("./data", exist_ok=True)
    init_vector_store()
    await pull_model_if_needed()
    print("✅ Ready!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI Research Assistant API",
    description="RAG-powered research assistant using Ollama + ChromaDB",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": OLLAMA_MODEL,
        "documents_count": get_documents_count()
    }

@app.get("/")
async def root():
    return {"message": "AI Research Assistant API is running 🚀"}
