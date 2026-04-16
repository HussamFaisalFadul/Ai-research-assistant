from fastapi import APIRouter, UploadFile, File, BackgroundTasks
import os
import shutil
from ..core.vector_store import add_documents_to_vectorstore
from ..core.config import UPLOAD_FOLDER

router = APIRouter()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_file(file_path: str):
    try:
        print("🚀 Processing file...")
        add_documents_to_vectorstore(file_path)
        print("✅ Done processing")
    except Exception as e:
        print("❌ Background error:", str(e))


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "PDF only"}

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        background_tasks.add_task(process_file, file_path)

        return {
            "message": "uploaded successfully, processing in background",
            "filename": file.filename,
            "chunks_added": 0
        }
    except Exception as e:
        return {"error": str(e)}
