import streamlit as st
import requests
import os

# ====================== الإعدادات ======================
# في HF Spaces: اتغير من localhost لـ URL الـ Backend Space
BACKEND_URL = os.getenv("BACKEND_URL", "https://YOUR-USERNAME-ai-research-backend.hf.space")

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="مساعد البحث الذكي",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 مساعد البحث الذكي")
st.markdown("### منصة ذكاء اصطناعي للبحث والتلخيص في الوثائق العلمية والتقنية")

# ====================== Sidebar ======================
with st.sidebar:
    st.header("⚙️ الإعدادات")

    # إظهار URL الـ backend
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
    st.caption("AI Research Assistant\nFastAPI + Ollama + ChromaDB")

# ====================== رفع الملف ======================
st.header("1️⃣ رفع وثيقة جديدة")

col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader(
        "اختر ملف PDF",
        type=["pdf"],
        help="يدعم ملفات PDF فقط"
    )

with col2:
    if uploaded_file and st.button("📤 رفع وفهرسة", type="primary"):
        with st.spinner("جاري الرفع والفهرسة..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
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
                            f"✅ تم الرفع!\n"
                            f"**{result['filename']}**\n"
                            f"جاري الفهرسة في الخلفية..."
                        )
                else:
                    st.error(f"❌ خطأ {response.status_code}")
            except Exception as e:
                st.error(f"❌ خطأ في الاتصال: {str(e)}")

# ====================== الدردشة ======================
st.header("2️⃣ اسأل عن الوثائق")

question = st.text_area(
    "اكتب سؤالك هنا",
    placeholder="مثال: لخص الورقة البحثية، ما هي أهم النتائج، ما هي المنهجية المستخدمة...",
    height=100
)

if st.button("🚀 إرسال السؤال", type="primary") and question.strip():
    with st.spinner("جاري التفكير..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/query",
                json={"question": question},
                timeout=120  # Ollama ممكن يأخد وقت
            )
            if response.status_code == 200:
                result = response.json()
                if "error" in result and not result.get("answer"):
                    st.error(f"❌ {result['error']}")
                else:
                    st.markdown("### 📝 الإجابة:")
                    st.markdown(result["answer"])
            else:
                st.error("❌ حدث خطأ أثناء الحصول على الإجابة")
        except requests.exceptions.Timeout:
            st.error("⏰ انتهى وقت الانتظار - النموذج قد يكون بطيء، حاول مرة أخرى")
        except Exception as e:
            st.error(f"❌ خطأ في الاتصال: {str(e)}")

# ====================== Footer ======================
st.divider()
st.caption("© 2026 AI Research Assistant | FastAPI + Ollama + ChromaDB + Streamlit")
