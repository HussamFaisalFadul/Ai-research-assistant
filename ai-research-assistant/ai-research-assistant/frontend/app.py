import streamlit as st
import streamlit.components.v1 as components
import requests
import json
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
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0 16px; border-bottom: 1px solid #2e3248; margin-bottom: 16px;
}
.top-bar h2 { margin: 0; font-size: 18px; font-weight: 700; color: #e8eaf0; }
.badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; border: 1px solid #2e3248; color: #8b90a7; }
.badge.rag { border-color: #22c55e; color: #22c55e; background: rgba(34,197,94,.1); }
.msg-user {
    background: #23273a; border: 1px solid #2e3248;
    border-radius: 12px 3px 12px 12px;
    padding: 10px 14px; margin: 6px 0 6px 40px;
    font-size: 14px; line-height: 1.7; color: #e8eaf0;
}
.msg-ai {
    background: #1e2238; border: 1px solid #2e3248;
    border-radius: 3px 12px 12px 12px;
    padding: 10px 14px; margin: 4px 40px 2px 0;
    font-size: 14px; line-height: 1.7; color: #e8eaf0;
}
.msg-label { font-size: 11px; color: #8b90a7; margin-bottom: 2px; }
.upload-info { background: #1a1d27; border: 1px solid #2e3248; border-radius: 8px; padding: 8px 12px; font-size: 12px; color: #8b90a7; margin-bottom: 8px; }
.success-box { background: rgba(34,197,94,.08); border: 1px solid #22c55e; border-radius: 8px; padding: 10px 14px; color: #22c55e; font-size: 13px; }
.error-box { background: rgba(239,68,68,.08); border: 1px solid #ef4444; border-radius: 8px; padding: 10px 14px; color: #ef4444; font-size: 13px; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
div[data-testid="stToolbar"] { display: none; }
.stTextArea textarea {
    background: #23273a !important; color: #e8eaf0 !important;
    border: 1px solid #2e3248 !important; border-radius: 10px !important;
    font-family: 'Tajawal', sans-serif !important; font-size: 14px !important; direction: rtl !important;
}
.stTextArea textarea:focus { border-color: #5b6ef5 !important; }
.stButton > button {
    background: #5b6ef5 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-family: 'Tajawal', sans-serif !important; font-weight: 500 !important; width: 100%;
}
.stButton > button:hover { background: #3d4fd4 !important; }
button[kind="secondary"] { background: transparent !important; color: #8b90a7 !important; border: 1px solid #2e3248 !important; }
button[kind="secondary"]:hover { border-color: #ef4444 !important; color: #ef4444 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────
for key, val in {
    "history": [],
    "doc_count": 0,
    "mindmap_data": None,
    "show_mindmap_idx": -1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─── Helpers ──────────────────────────────────────────────────
def warmup_backend():
    try:
        requests.get(f"{API_BASE.replace('/api','')}/health", timeout=10)
    except Exception:
        pass

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
            json={"question": question, "history": st.session_state.history, "stream": False},
            timeout=300,
        )
        data = r.json()
        if "documents_count" in data:
            st.session_state.doc_count = data["documents_count"]
        return data.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ الموديل يعمل على CPU — انتظر قليلاً وأعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال بالخادم: {str(e)}"

def get_mindmap(text: str) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/mindmap",
            json={"text": text},
            timeout=120,
        )
        data = r.json()
        if data.get("success"):
            return data["mindmap"]
    except Exception as e:
        st.error(f"خطأ في الخريطة: {e}")
    return None

def upload_file(file) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_BASE}/upload",
            files={"file": (file.name, file.getvalue(), file.type)},
            timeout=30,
        )
        data = r.json()
        if not r.ok or "error" in data:
            return False, data.get("error") or data.get("detail") or "خطأ"
        return True, data.get("message", "تم الرفع بنجاح")
    except Exception as e:
        return False, str(e)


# ─── Mindmap renderer (HTML/JS with D3) ───────────────────────
def render_mindmap(data: dict):
    json_str = json.dumps(data, ensure_ascii=False)
    html = f"""
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f1117; font-family: 'Tajawal', 'Segoe UI', sans-serif; overflow: hidden; }}
  svg {{ width: 100%; height: 560px; display: block; }}
  .node circle {{ fill: #1e2238; stroke: #5b6ef5; stroke-width: 2px; cursor: pointer; transition: all .2s; }}
  .node circle:hover {{ fill: #5b6ef5; }}
  .node.root circle {{ fill: #5b6ef5; stroke: #7b8ef5; r: 28px; }}
  .node.level1 circle {{ fill: #23273a; stroke: #5b6ef5; }}
  .node.level2 circle {{ fill: #1a1d27; stroke: #3d4fd4; }}
  .node text {{ font-family: 'Tajawal', sans-serif; fill: #e8eaf0; font-size: 12px; pointer-events: none; }}
  .node.root text {{ font-size: 13px; font-weight: 700; fill: #fff; }}
  .link {{ fill: none; stroke: #2e3248; stroke-width: 1.5px; }}
  .controls {{ position: absolute; bottom: 10px; left: 10px; display: flex; gap: 6px; }}
  .btn {{ background: #23273a; border: 1px solid #2e3248; color: #8b90a7; padding: 5px 10px;
           border-radius: 6px; cursor: pointer; font-size: 12px; font-family: inherit; }}
  .btn:hover {{ border-color: #5b6ef5; color: #e8eaf0; }}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet"/>
</head>
<body>
<svg id="svg"></svg>
<div class="controls">
  <button class="btn" onclick="zoom(-0.2)">−</button>
  <button class="btn" onclick="zoom(0.2)">+</button>
  <button class="btn" onclick="reset()">⟳</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const data = {json_str};

const width = document.getElementById('svg').clientWidth || 700;
const height = 560;
let currentZoom = 1;
let currentX = 0, currentY = 0;

const svg = d3.select('#svg')
  .attr('viewBox', `0 0 ${{width}} ${{height}}`);

const g = svg.append('g');

// زر السحب
svg.call(d3.drag()
  .on('drag', (event) => {{
    currentX += event.dx;
    currentY += event.dy;
    g.attr('transform', `translate(${{currentX}},${{currentY}}) scale(${{currentZoom}})`);
  }})
);

function zoom(delta) {{
  currentZoom = Math.max(0.3, Math.min(2.5, currentZoom + delta));
  g.attr('transform', `translate(${{currentX}},${{currentY}}) scale(${{currentZoom}})`);
}}
function reset() {{
  currentZoom = 1; currentX = 0; currentY = 0;
  g.attr('transform', `translate(0,0) scale(1)`);
  render();
}}

function render() {{
  g.selectAll('*').remove();

  const root = d3.hierarchy(data);
  const treeLayout = d3.tree().size([height - 80, width - 200]);
  treeLayout(root);

  // تحويل المحاور لـ RTL
  root.descendants().forEach(d => {{
    const temp = d.x; d.x = d.y; d.y = d.x;
  }});

  // رسم الروابط
  g.selectAll('.link')
    .data(root.links())
    .enter().append('path')
    .attr('class', 'link')
    .attr('d', d => {{
      return `M${{d.source.x + 100}},${{d.source.y + 40}}
              C${{(d.source.x + d.target.x)/2 + 100}},${{d.source.y + 40}}
               ${{(d.source.x + d.target.x)/2 + 100}},${{d.target.y + 40}}
               ${{d.target.x + 100}},${{d.target.y + 40}}`;
    }});

  // رسم العقد
  const node = g.selectAll('.node')
    .data(root.descendants())
    .enter().append('g')
    .attr('class', d => {{
      const depth = d.depth;
      return `node ${{depth === 0 ? 'root' : depth === 1 ? 'level1' : 'level2'}}`;
    }})
    .attr('transform', d => `translate(${{d.x + 100}},${{d.y + 40}})`);

  // دائرة كل عقدة — حجم بناءً على المستوى
  node.append('circle')
    .attr('r', d => d.depth === 0 ? 28 : d.depth === 1 ? 20 : 14);

  // نص العقدة — تقسيم إذا طويل
  node.each(function(d) {{
    const el = d3.select(this);
    const words = d.data.topic.split(' ');
    const maxPerLine = 4;
    const lines = [];
    for (let i = 0; i < words.length; i += maxPerLine) {{
      lines.push(words.slice(i, i + maxPerLine).join(' '));
    }}
    const lineH = 14;
    const startY = -(lines.length - 1) * lineH / 2;
    lines.forEach((line, i) => {{
      el.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', startY + i * lineH)
        .attr('font-size', d.depth === 0 ? '12px' : d.depth === 1 ? '11px' : '10px')
        .text(line);
    }});
  }});
}}

render();
</script>
</body>
</html>
"""
    components.html(html, height=580, scrolling=False)


# ─── Header ───────────────────────────────────────────────────
warmup_backend()
st.session_state.doc_count = fetch_doc_count()
mode_class = "rag" if st.session_state.doc_count > 0 else ""
mode_text  = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"

st.markdown(f"""
<div class="top-bar">
  <h2>🔬 مساعد البحث الذكي</h2>
  <span class="badge {mode_class}">{mode_text}</span>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📁 رفع الوثائق")
    uploaded = st.file_uploader("اختر ملف PDF أو DOCX", type=["pdf", "docx"], label_visibility="collapsed")
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
        if st.button("🗑️ مسح", key="clear_chat", type="secondary"):
            st.session_state.history = []
            st.session_state.show_mindmap_idx = -1
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


# ─── Chat display ─────────────────────────────────────────────
if not st.session_state.history:
    st.markdown("""
    <div style="text-align:center;padding:40px 0;color:#8b90a7">
        <div style="font-size:40px;opacity:.3;margin-bottom:12px">◎</div>
        <p style="font-size:14px">اسأل أي سؤال للبدء</p>
        <p style="font-size:12px;opacity:.6;margin-top:6px">ارفع ملف من الشريط الجانبي لتفعيل وضع RAG</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # عرض المحادثة — كل رد مساعد عنده زر خريطة
    assistant_idx = 0  # عداد لردود المساعد فقط
    for i, turn in enumerate(st.session_state.history):
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

            # زر الخريطة الذهنية بجانب كل رد
            btn_key = f"mm_{i}_{assistant_idx}"
            col_a, col_b = st.columns([1, 6])
            with col_a:
                if st.button("🗺️ خريطة", key=btn_key, type="secondary"):
                    if st.session_state.show_mindmap_idx == i:
                        # أغلق إذا مفتوحة
                        st.session_state.show_mindmap_idx = -1
                        st.session_state.mindmap_data = None
                    else:
                        with st.spinner("جارٍ بناء الخريطة الذهنية... ⏳"):
                            mm = get_mindmap(turn["content"])
                        if mm:
                            st.session_state.mindmap_data = mm
                            st.session_state.show_mindmap_idx = i
                        else:
                            st.error("تعذر بناء الخريطة")
                    st.rerun()

            # عرض الخريطة تحت الرد مباشرة
            if st.session_state.show_mindmap_idx == i and st.session_state.mindmap_data:
                st.markdown("---")
                render_mindmap(st.session_state.mindmap_data)
                st.markdown("---")

            assistant_idx += 1


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
    with st.spinner("جارٍ التفكير... (قد يأخذ 20-40 ثانية على CPU) ⏳"):
        ans = ask(question.strip())
    st.session_state.history.append({"role": "user",      "content": question.strip()})
    st.session_state.history.append({"role": "assistant", "content": ans})
    if len(st.session_state.history) > 20:
        st.session_state.history = st.session_state.history[-20:]
    st.rerun()
