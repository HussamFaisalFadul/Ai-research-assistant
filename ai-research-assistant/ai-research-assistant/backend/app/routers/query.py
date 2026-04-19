from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import re

from ..core.rag import answer, answer_stream
from ..core.vector_store import get_documents_count
from ..core.config import OLLAMA_MODEL, OLLAMA_BASE_URL

router = APIRouter()


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class ChatMessage(BaseModel):
    role:    str
    content: str

class QueryRequest(BaseModel):
    question: str
    history:  list[ChatMessage] = Field(default_factory=list)
    use_rag:  bool | None = None
    stream:   bool = False

class MindmapRequest(BaseModel):
    text: str   # نص الإجابة المراد تحويله


# ─────────────────────────────────────────────
# /query
# ─────────────────────────────────────────────
@router.post("/query")
async def query(request: QueryRequest):
    history_dicts = [m.model_dump() for m in request.history]

    if request.stream:
        async def event_stream():
            async for chunk in answer_stream(
                request.question,
                history=history_dicts,
                use_rag=request.use_rag,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        result = answer(request.question, history=history_dicts, use_rag=request.use_rag)
    except Exception as e:
        result = f"عذراً، حدث خطأ غير متوقع: {str(e)}"

    count = get_documents_count()
    return {
        "answer":          result,
        "mode":            "rag" if count > 0 else "chat",
        "documents_count": count,
    }


# ─────────────────────────────────────────────
# /chat
# ─────────────────────────────────────────────
@router.post("/chat")
async def chat(request: QueryRequest):
    request.use_rag = False
    return await query(request)


# ─────────────────────────────────────────────
# /mindmap  — تحويل نص إلى هيكل خريطة ذهنية
# ─────────────────────────────────────────────
@router.post("/mindmap")
async def generate_mindmap(request: MindmapRequest):
    """
    يأخذ نص الإجابة ويطلب من الموديل تحويله إلى JSON هيكلي
    للخريطة الذهنية.
    """
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = f"""حوّل النص التالي إلى خريطة ذهنية بصيغة JSON فقط.
القواعد الصارمة:
- أجب بـ JSON فقط بدون أي نص إضافي أو markdown
- البنية المطلوبة بالضبط:
{{
  "topic": "العنوان الرئيسي",
  "children": [
    {{
      "topic": "فرع رئيسي",
      "children": [
        {{"topic": "تفصيل", "children": []}},
        {{"topic": "تفصيل", "children": []}}
      ]
    }}
  ]
}}
- topic يجب أن يكون قصيراً (أقل من 8 كلمات)
- 3 إلى 6 فروع رئيسية
- كل فرع يحتوي 2 إلى 4 تفاصيل
- استخرج أهم النقاط من النص

النص:
{request.text[:2000]}

JSON:"""

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0.1,
        num_predict=1500,
        base_url=OLLAMA_BASE_URL,
        timeout=120,
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are a JSON generator. Output only valid JSON, no markdown, no explanation."),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()

        # تنظيف أي markdown محتمل
        raw = re.sub(r"```json|```", "", raw).strip()

        # استخراج أول {} صالح
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError("No JSON found")

        return {"success": True, "mindmap": data}

    except Exception as e:
        print(f"❌ Mindmap error: {e}")
        # fallback: بنية بسيطة من النص مباشرة
        lines = [l.strip() for l in request.text.split('\n') if len(l.strip()) > 10][:12]
        fallback = {
            "topic": "ملخص",
            "children": [{"topic": line[:60], "children": []} for line in lines]
        }
        return {"success": True, "mindmap": fallback, "fallback": True}
