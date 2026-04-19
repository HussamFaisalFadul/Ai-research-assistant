"""
utils.py — دوال مشتركة: API، Mindmap، Theme
"""
import requests
import re
import json
import os
import streamlit as st
from datetime import datetime

API_BASE = os.getenv("API_BASE_URL", "https://hussamfaisal-ai-research-backend.hf.space/api")
HISTORY_FILE = "chat_history.json"
SESSIONS_FILE = "sessions.json"


# ══════════════════════════════════════════
# Theme colors
# ══════════════════════════════════════════
def get_theme_colors(theme: str) -> dict:
    if theme == "light":
        return dict(
            BG="#f8f9fc", BG2="#ffffff", BG3="#f0f2f8",
            BORDER="#dde1f0", TEXT="#1a1d2e", TEXT2="#6b7280",
            ACCENT="#4f5ef0", ACCENT2="#3b4bd4",
            MSG_USER="#eef0ff", MSG_AI="#ffffff",
            SHADOW="rgba(79,94,240,0.08)", SVG_BG="#f8f9fc",
            NODE0="#4f5ef0", NODE1="#ffffff", NODE2="#f0f2f8",
            TXT_COL="#1a1d2e", BTN_BG="#ffffff",
            BTN_BRD="#dde1f0", BTN_TXT="#6b7280",
        )
    return dict(
        BG="#0f1117", BG2="#1a1d27", BG3="#23273a",
        BORDER="#2e3248", TEXT="#e8eaf0", TEXT2="#8b90a7",
        ACCENT="#5b6ef5", ACCENT2="#3d4fd4",
        MSG_USER="#23273a", MSG_AI="#1e2238",
        SHADOW="rgba(0,0,0,0.3)", SVG_BG="#0f1117",
        NODE0="#5b6ef5", NODE1="#1e2238", NODE2="#13151f",
        TXT_COL="#e8eaf0", BTN_BG="#1e2238",
        BTN_BRD="#2e3248", BTN_TXT="#8b90a7",
    )


# ══════════════════════════════════════════
# API calls
# ══════════════════════════════════════════
def warmup_once():
    if not st.session_state.get("backend_warm", False):
        try:
            requests.get(f"{API_BASE.replace('/api','')}/health", timeout=15)
            st.session_state.backend_warm = True
        except:
            pass

def fetch_count() -> int:
    try:
        return requests.get(f"{API_BASE}/documents/count", timeout=5).json().get("count", 0)
    except:
        return st.session_state.get("doc_count", 0)

def ask_llm(prompt: str) -> str:
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": prompt, "history": [], "stream": False},
            timeout=300)
        return r.json().get("answer", "")
    except:
        return ""

def ask_chat(q: str) -> str:
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": q,
                  "history": st.session_state.get("history", []),
                  "stream": False},
            timeout=300)
        d = r.json()
        if "documents_count" in d:
            st.session_state.doc_count = d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ انتهت مهلة الاتصال — أعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال: {str(e)}"

def upload_file(f) -> tuple[bool, str]:
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)},
            timeout=30)
        d = r.json()
        if not r.ok or "error" in d:
            return False, d.get("error") or d.get("detail", "خطأ")
        return True, d.get("message", "تم الرفع")
    except Exception as e:
        return False, str(e)


def extract_text_locally(f) -> tuple[bool, str]:
    """
    يستخرج النص مباشرة في Python بدون الباك اند.
    يدعم PDF و DOCX.
    """
    import io
    filename = f.name.lower()
    file_bytes = f.getvalue()

    # ── PDF ──
    if filename.endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text", flags=48) + "\n\n"
            doc.close()
            text = text.strip()
            if text:
                return True, text
        except ImportError:
            pass  # PyMuPDF غير مثبت — جرب pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
            if text:
                return True, text
        except Exception as e:
            return False, f"تعذر قراءة PDF: {e}"

    # ── DOCX ──
    elif filename.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text:
                return True, text.strip()
            return False, "الملف فارغ أو لا يحتوي على نص"
        except Exception as e:
            return False, f"تعذر قراءة DOCX: {e}"

    return False, "نوع الملف غير مدعوم"


def extract_text_from_uploaded(f) -> tuple[bool, str]:
    """
    يحاول الاستخراج محلياً أولاً.
    إذا فشل يرفع للسيرفر (كـ fallback).
    """
    # أولاً: محلياً — أسرع وأضمن
    ok, text = extract_text_locally(f)
    if ok and text.strip():
        # أيضاً ارفع للسيرفر في الخلفية لأجل RAG
        try:
            requests.post(f"{API_BASE}/upload",
                files={"file": (f.name, f.getvalue(), f.type)},
                timeout=30)
        except:
            pass
        return True, text.strip()

    # ثانياً: fallback للسيرفر
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)},
            timeout=60)
        d = r.json()
        if not r.ok or "error" in d:
            return False, d.get("error") or d.get("detail", "خطأ")
        extracted = d.get("text") or d.get("extracted_text") or ""
        if extracted:
            return True, extracted
        return False, text or "تعذر استخراج النص"
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════
# Local persistence
# ══════════════════════════════════════════
def load_history() -> list:
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def save_history(history: list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_sessions() -> list:
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def save_sessions(sessions: list):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except:
        pass


# ══════════════════════════════════════════
# Mindmap: summarize
# ══════════════════════════════════════════
def summarize_for_mindmap(text: str) -> str:
    prompt = f"""You must output ONLY a structured outline in Arabic. No intro. No explanation. Just the outline.

EXACT FORMAT (follow precisely):
Line 1: main title — max 5 Arabic words, NO ## prefix
Then 3 to 5 branches, each on its own line starting with ##
Each ## branch title: max 4 Arabic words
Each branch followed by 2-4 detail lines starting with -
Each - detail: max 7 Arabic words

GOOD EXAMPLE:
التجارة الإلكترونية
## النمو والأرقام
- نمو 265٪ في المبيعات
- 4.88 تريليون بحلول 2021
## فوائد للشركات
- التميز عن المنافسين
- خفض التكاليف

BAD (do NOT do this):
- No preamble like "Here is the outline:"
- No English text
- No merging ## and - on same line like "## فرع - تفصيل"

Now summarize:
{text[:3000]}

OUTPUT:"""
    return ask_llm(prompt).strip()


# ══════════════════════════════════════════
# Mindmap: parse
# ══════════════════════════════════════════
def parse_mindmap_structure(structured_text: str) -> dict:
    # فصل ##- المدمجة
    text = re.sub(r'(##[^#\n]+?)\s*-\s*', r'\1\n- ', structured_text)
    lines = []
    for raw in text.split('\n'):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith('##') and ' - ' in raw:
            head, *rest = raw.split(' - ')
            lines.append(head.strip())
            for r in rest:
                if r.strip():
                    lines.append('- ' + r.strip())
        else:
            lines.append(raw)

    if not lines:
        return {"topic": "الموضوع", "children": []}

    title = ' '.join(re.sub(r'^#+\s*', '', lines[0]).strip().split()[:6])
    branches, cur_branch, cur_children = [], None, []

    for line in lines[1:]:
        is_branch = line.startswith('##') or (
            not line.startswith(('-', '•', '*')) and len(line) > 3
            and cur_branch is None
        )
        if is_branch:
            if cur_branch is not None:
                branches.append({
                    "topic": cur_branch,
                    "children": [{"topic": c, "children": []} for c in cur_children]
                })
            cur_branch = ' '.join(re.sub(r'^#+\s*', '', line).strip().split()[:5])
            cur_children = []
        elif line.startswith(('-', '•', '*')):
            child = ' '.join(re.sub(r'^[-•*]\s*', '', line).strip().split()[:8])
            if child and cur_branch is not None:
                cur_children.append(child)

    if cur_branch is not None:
        branches.append({
            "topic": cur_branch,
            "children": [{"topic": c, "children": []} for c in cur_children]
        })

    if not branches:
        chunks = [re.sub(r'^[-•*##\s]+', '', l).strip() for l in lines[1:] if len(l) > 8][:7]
        branches = [{"topic": ' '.join(c.split()[:5]), "children": []} for c in chunks]

    return {"topic": title, "children": branches[:6]}
