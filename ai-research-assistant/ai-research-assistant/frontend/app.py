import streamlit as st
import requests
import os

# ─── Config ───────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "https://hussamfaisal-ai-research-backend.hf.space/api")

st.set_page_config(
    page_title="مساعد البحث الذكي",
    page_icon="🔬",
    layout="centered",
)

# ─── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Tajawal', sans-serif !important; direction: rtl; }

.stApp { background: #0f1117; color: #e8eaf0; }

/* header */
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0 16px; border-bottom: 1px solid #2e3248; margin-bottom: 16px;
}
.top-bar h2 { margin: 0; font-size: 18px; font-weight: 700; color: #e8eaf0; }
.badge {
    font-size: 11px; padding: 3px 10px; border-radius: 20px;
    border: 1px solid #2e3248; color: #8b90a7;
}
.badge.rag { border-color: #22c55e; color: #22c55e; background: rgba(34,197,94,.1); }

/* chat bubbles */
.msg-user {
    background: #23273a; border: 1px solid #2e3248;
    border-radius: 12px 3px 12px 12px;
    padding: 10px 14px; margin: 6px 0 6px 40px;
    font-size: 14px; line-height: 1.7; color: #e8eaf0;
}
.msg-ai {
    background: #1e2238; border: 1px solid #2e3248;
    border-radius: 3px 12px 12px 12px;
    padding: 10px 14px; margin: 6px 40px 6px 0;
    font-size: 14px; line-height: 1.7; color: #e8eaf0;
}
.msg-label { font-size: 11px; color: #8b90a7; margin-bottom: 2px; }

/* upload area */
.upload-info {
    background: #1a1d27; border: 1px solid #2e3248; border-radius: 8px;
    padding: 8px 12px; font-size: 12px; color: #8b90a7; margin-bottom: 8px;
}
.success-box {
    background: rgba(34,197,94,.08); border: 1px solid #22c55e;
    border-radius: 8px; padding: 10px 14px; color: #22c55e; font-size: 13px;
}
.error-box {
    background: rgba(239,68,68,.08); border: 1px solid #ef4444;
    border-radius: 8px; padding: 10px 14px; color: #ef4444; font-size: 13px;
}

/* hide streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
div[data-testid="stToolbar"] { display: none; }

/* input styling */
.stTextArea textarea {
    background: #23273a !important; color: #e8eaf0 !important;
    border: 1px solid #2e3248 !important; border-radius: 10px !important;
    font-family: 'Tajawal', sans-serif !important; font-size: 14px !important;
    direction: rtl !important;
}
.stTextArea textarea:focus { border-color: #5b6ef5 !important; }

.stButton > button {
    background: #5b6ef5 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-family: 'Tajawal', sans-serif !important; font-weight: 500 !important;
    width: 100%;
}
.stButton > button:hover { background: #3d4fd4 !important; }

button[kind="secondary"] {
    background: transparent !important; color: #8b90a7 !important;
    border: 1px solid #2e3248 !important;
}
button[kind="secondary"]:hover { border-color: #ef4444 !important; color: #ef4444 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "doc_count" not in st.session_state:
    st.session_state.doc_count = 0


# ─── Helpers ──────────────────────────────────────────────────
def fetch_doc_count() -> int:
    try:
        r = requests.get(f"{API_BASE}/documents/count", timeout=5)
        return r.json().get("count", 0)
    except Exception:
        return st.session_state.doc_count


def ask(question: str) -> str:
    try:
        r = requests.post(
            f"{API_BASE}/query",
            json={
                "question": question,
                "history": st.session_state.history,
                "stream": False,
            },
            timeout=300,
        )
        data = r.json()
        if "documents_count" in data:
            st.session_state.doc_count = data["documents_count"]
        return data.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ الموديل يعمل على CPU وقد يأخذ وقتاً أطول — انتظر 30 ثانية وأعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال بالخادم: {str(e)}"


def upload_file(file) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_BASE}/upload",
            files={"file": (file.name, file.getvalue(), file.type)},
            timeout=30,
        )
        data = r.json()
        if not r.ok or "error" in data:
            return False, data.get("error") or data.get("detail") or "خطأ غير معروف"
        return True, data.get("message", "تم الرفع بنجاح")
    except Exception as e:
        return False, str(e)


# ─── Header ───────────────────────────────────────────────────
st.session_state.doc_count = fetch_doc_count()
mode_class = "rag" if st.session_state.doc_count > 0 else ""
mode_text  = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"

st.markdown(f"""
<div class="top-bar">
  <h2>🔬 مساعد البحث الذكي</h2>
  <span class="badge {mode_class}">{mode_text}</span>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar: Upload + Controls ───────────────────────────────
with st.sidebar:
    st.markdown("### 📁 رفع الوثائق")
    uploaded = st.file_uploader(
        "اختر ملف PDF أو DOCX",
        type=["pdf", "docx"],
        label_visibility="collapsed",
    )

    if uploaded:
        st.markdown(f'<div class="upload-info">📄 {uploaded.name}</div>', unsafe_allow_html=True)
        if st.button("⬆️ رفع الملف", key="upload_btn"):
            with st.spinner("جارٍ الرفع..."):
                ok, msg = upload_file(uploaded)
            if ok:
                st.markdown(f'<div class="success-box">✅ {msg}</div>', unsafe_allow_html=True)
                import time; time.sleep(3)
                st.session_state.doc_count = fetch_doc_count()
                st.rerun()
            else:
                st.markdown(f'<div class="error-box">❌ {msg}</div>', unsafe_allow_html=True)

    st.divider()

    st.markdown("### ⚙️ الإعدادات")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ مسح المحادثة", key="clear_chat", type="secondary"):
            st.session_state.history = []
            st.rerun()
    with col2:
        if st.button("🔄 تحديث", key="refresh_count", type="secondary"):
            st.session_state.doc_count = fetch_doc_count()
            st.rerun()

    st.divider()
    st.markdown(f"""
    <div style="font-size:12px;color:#8b90a7;line-height:1.8">
    <b style="color:#e8eaf0">الوضع الحالي:</b><br>
    {'🟢 RAG — يقرأ الوثائق' if st.session_state.doc_count > 0 else '🔵 Chat — بدون وثائق'}<br><br>
    <b style="color:#e8eaf0">الوثائق المفهرسة:</b><br>
    {st.session_state.doc_count} وثيقة
    </div>
    """, unsafe_allow_html=True)


# ─── Chat history display ─────────────────────────────────────
if not st.session_state.history:
    st.markdown("""
    <div style="text-align:center;padding:40px 0;color:#8b90a7">
        <div style="font-size:40px;opacity:.3;margin-bottom:12px">◎</div>
        <p style="font-size:14px">اسأل أي سؤال للبدء</p>
        <p style="font-size:12px;opacity:.6;margin-top:6px">ارفع ملف من الشريط الجانبي لتفعيل وضع RAG</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for turn in st.session_state.history:
        if turn["role"] == "user":
            st.markdown(f"""
            <div class="msg-label" style="text-align:right">أنت</div>
            <div class="msg-user">{turn["content"]}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="msg-label">المساعد</div>
            <div class="msg-ai">{turn["content"]}</div>
            """, unsafe_allow_html=True)


# ─── Input ────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    question = st.text_area(
        "السؤال",
        placeholder="اكتب سؤالك هنا...",
        label_visibility="collapsed",
        height=80,
    )
    submitted = st.form_submit_button("إرسال ➤", use_container_width=True)

if submitted and question.strip():
    with st.spinner("جارٍ التفكير... (الموديل على CPU قد يأخذ 20-40 ثانية) ⏳"):
        answer = ask(question.strip())
    st.session_state.history.append({"role": "user",      "content": question.strip()})
    st.session_state.history.append({"role": "assistant", "content": answer})
    if len(st.session_state.history) > 20:
        st.session_state.history = st.session_state.history[-20:]
    st.rerun()
