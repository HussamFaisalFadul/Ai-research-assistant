import streamlit as st
import requests
import os

# ====================== الإعدادات ======================
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://YOUR-USERNAME-ai-research-backend.hf.space"
)

# ====================== إعداد الصفحة ======================
st.set_page_config(
    page_title="مساعد البحث الذكي",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 مساعد البحث الذكي")
st.markdown("### منصة ذكاء اصطناعي للبحث والتلخيص في الوثائق")

# ====================== Sidebar ======================
with st.sidebar:
    st.header("⚙️ الإعدادات")

    backend_display = BACKEND_URL.replace("https://", "").split(".")[0]
    st.caption(f"🔗 Backend: `{backend_display}`")

    if st.button("🔄 تحديث حالة النظام"):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                st.success(
                    f"✅ النظام يعمل\n"
                    f"النموذج: **{data.get('model', 'غير معروف')}**\n"
                    f"الوثائق: **{data.get('documents_count', 0)}**"
                )
            else:
                st.error("❌ فشل الاتصال")
        except Exception as e:
            st.error(f"❌ لا يمكن الاتصال بالـ Backend\n{str(e)}")

    st.divider()
    st.caption("AI Research Assistant")

# ====================== رفع الملفات ======================
st.header("1️⃣ رفع وثيقة جديدة")

col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "اختر ملف (PDF أو Word)",
        type=["pdf", "docx"],
        help="يدعم PDF و Word"
    )

with col2:
    if uploaded_file and st.button("📤 رفع وفهرسة", type="primary"):
        with st.spinner("جاري الرفع والفهرسة..."):
            try:
                filename = uploaded_file.name.lower()

                if filename.endswith(".pdf"):
                    mime_type = "application/pdf"
                elif filename.endswith(".docx"):
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                else:
                    mime_type = "application/octet-stream"

                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        mime_type
                    )
                }

                response = requests.post(
                    f"{BACKEND_URL}/api/upload",
                    files=files,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()

                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        st.success(
                            f"✅ تم الرفع بنجاح!\n"
                            f"📄 {result['filename']}\n"
                            f"⏳ جاري الفهرسة بالخلفية..."
                        )
                else:
                    st.error(f"❌ خطأ في السيرفر: {response.status_code}")

            except Exception as e:
                st.error(f"❌ خطأ في الاتصال: {str(e)}")

# ====================== الدردشة ======================
st.header("2️⃣ اسأل عن الوثائق")

question = st.text_area(
    "اكتب سؤالك هنا",
    placeholder="مثال: لخص المحتوى، ما أهم النقاط، ما النتائج...",
    height=100
)

if st.button("🚀 إرسال السؤال", type="primary") and question.strip():
    with st.spinner("جاري التفكير..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/query",
                json={"question": question},
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()

                if "error" in result and not result.get("answer"):
                    st.error(f"❌ {result['error']}")
                else:
                    st.markdown("### 📝 الإجابة:")
                    st.markdown(result["answer"])
            else:
                st.error("❌ فشل في الحصول على إجابة")

        except requests.exceptions.Timeout:
            st.error("⏰ الطلب أخذ وقت طويل، حاول مرة أخرى")
        except Exception as e:
            st.error(f"❌ خطأ في الاتصال: {str(e)}")

# ====================== Footer ======================
st.divider()
st.caption("© 2026 AI Research Assistant | FastAPI + Ollama + ChromaDB + Streamlit")
