from fastapi import APIRouter
from pydantic import BaseModel
from ..core.rag import get_rag_chain

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/query")
async def query_documents(request: QueryRequest):
    try:
        chain = get_rag_chain()
        answer = chain.invoke(request.question)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e), "answer": f"حدث خطأ: {str(e)}"}
