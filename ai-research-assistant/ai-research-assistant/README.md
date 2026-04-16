# 📚 AI Research Assistant

مساعد بحث ذكي يعتمد على RAG (Retrieval Augmented Generation) باستخدام Ollama + ChromaDB.

## 🏗️ المعمارية

```
┌─────────────────────────────────────────┐
│    HuggingFace Space (Backend)          │
│                                         │
│  FastAPI  +  Ollama  +  ChromaDB        │
│      ↕           ↕          ↕           │
│  RAG Chain   qwen2.5:3b   Vectors       │
└─────────────────────────────────────────┘
         ↕ HTTP API
┌─────────────────────────────────────────┐
│   Streamlit Cloud (Frontend)            │
└─────────────────────────────────────────┘
```

## 🚀 خطوات الرفع

### الخطوة 1: رفع الـ Backend على HuggingFace Spaces

1. اذهب إلى [huggingface.co/new-space](https://huggingface.co/new-space)
2. الإعدادات:
   - **Space name**: `ai-research-backend`
   - **SDK**: `Docker`
   - **Hardware**: `CPU Basic` (مجاني - 16GB RAM)
3. ارفع محتويات مجلد `backend/` للـ Space
4. انتظر حتى يبني الـ Space (5-10 دقائق)
5. الـ URL هيكون: `https://YOUR-USERNAME-ai-research-backend.hf.space`

### الخطوة 2: رفع الـ Frontend على Streamlit Cloud

1. ارفع المشروع كله على GitHub
2. اذهب إلى [share.streamlit.io](https://share.streamlit.io)
3. اربطه بالـ GitHub repo
4. **Main file path**: `frontend/app.py`
5. في **Secrets** أضف:
   ```
   BACKEND_URL = "https://YOUR-USERNAME-ai-research-backend.hf.space"
   ```
6. انشر!

## 📁 هيكل المشروع

```
ai-research-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── routers/
│   │   │   ├── upload.py    # رفع الملفات
│   │   │   └── query.py     # الاستعلامات
│   │   └── core/
│   │       ├── rag.py       # RAG chain
│   │       ├── vector_store.py
│   │       └── config.py
│   ├── requirements.txt
│   ├── Dockerfile           # للـ HF Spaces
│   └── start.sh             # يشغل Ollama + FastAPI
└── frontend/
    ├── app.py               # Streamlit app
    └── requirements.txt
```

## 🔧 API Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/health` | حالة النظام |
| POST | `/api/upload` | رفع PDF |
| POST | `/api/query` | سؤال عن الوثائق |

## ⚙️ Environment Variables

### Backend (HF Space Secrets):
| المتغير | القيمة الافتراضية | الوصف |
|---------|-----------------|-------|
| `OLLAMA_MODEL` | `qwen2.5:3b` | النموذج المستخدم |
| `CHROMA_DB_PATH` | `./chroma_db` | مسار قاعدة البيانات |
| `UPLOAD_FOLDER` | `./data` | مجلد الملفات |

### Frontend (Streamlit Secrets):
| المتغير | الوصف |
|---------|-------|
| `BACKEND_URL` | URL الـ Backend Space |

## ⚠️ ملاحظات مهمة

- **Storage**: البيانات تُمسح عند restart الـ Space (HF Spaces مجاني)
- **Cold Start**: أول طلب ممكن يأخد وقت لتحميل النموذج
- **RAM**: النموذج `qwen2.5:3b` يحتاج ~3GB RAM
