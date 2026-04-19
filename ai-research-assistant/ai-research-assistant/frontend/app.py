import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
import re
import io
import time
from datetime import datetime

API_BASE = os.getenv("API_BASE_URL", "https://hussamfaisal-ai-research-backend.hf.space/api")

st.set_page_config(page_title="مساعد البحث الذكي", page_icon="🔬", layout="centered")

# ── تهيئة session state ──
if "history" not in st.session_state:
    st.session_state.history = []
if "doc_count" not in st.session_state:
    st.session_state.doc_count = 0
if "mm_raw_text" not in st.session_state:
    st.session_state.mm_raw_text = ""
if "mm_summary" not in st.session_state:
    st.session_state.mm_summary = ""
if "mm_data" not in st.session_state:
    st.session_state.mm_data = None
if "mm_step" not in st.session_state:
    st.session_state.mm_step = 0
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "backend_warm" not in st.session_state:
    st.session_state.backend_warm = False
if "processing" not in st.session_state:
    st.session_state.processing = False

T = st.session_state.theme
C = {
    "light": dict(BG="#f8f9fc", BG3="#f0f2f8", BORDER="#dde1f0", TEXT="#1a1d2e",
                  TEXT2="#6b7280", ACCENT="#4f5ef0", ACCENT2="#3b4bd4",
                  MSG_U="#eef0ff", MSG_A="#ffffff", SHADOW="rgba(79,94,240,0.08)",
                  SVG="#f8f9fc", N0="#4f5ef0", N1="#ffffff", N2="#f0f2f8",
                  TC="#1a1d2e", BB="#ffffff", BBD="#dde1f0", BBT="#6b7280"),
    "dark": dict(BG="#0f1117", BG3="#23273a", BORDER="#2e3248", TEXT="#e8eaf0",
                 TEXT2="#8b90a7", ACCENT="#5b6ef5", ACCENT2="#3d4fd4",
                 MSG_U="#23273a", MSG_A="#1e2238", SHADOW="rgba(0,0,0,0.3)",
                 SVG="#0f1117", N0="#5b6ef5", N1="#1e2238", N2="#13151f",
                 TC="#e8eaf0", BB="#1e2238", BBD="#2e3248", BBT="#8b90a7"),
}[T]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
html,body,[class*="css"]{{font-family:'Tajawal',sans-serif!important;direction:rtl}}
.stApp{{background:{C['BG']};color:{C['TEXT']}}}
#MainMenu,footer,header{{visibility:hidden}}
.stDeployButton,div[data-testid="stToolbar"]{{display:none}}
.top-bar{{display:flex;align-items:center;justify-content:space-between;
  padding:10px 0 14px;border-bottom:2px solid {C['BORDER']};margin-bottom:18px}}
.top-bar h2{{margin:0;font-size:18px;font-weight:700;color:{C['TEXT']}}}
.badge{{font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid {C['BORDER']};color:{C['TEXT2']}}}
.badge.rag{{border-color:#22c55e;color:#22c55e;background:rgba(34,197,94,.1)}}
.msg-user{{background:{C['MSG_U']};border:1px solid {C['BORDER']};border-radius:12px 3px 12px 12px;
  padding:11px 15px;margin:6px 0 6px 40px;font-size:14px;line-height:1.75;color:{C['TEXT']}}}
.msg-ai{{background:{C['MSG_A']};border:1px solid {C['BORDER']};box-shadow:0 2px 8px {C['SHADOW']};
  border-radius:3px 12px 12px 12px;padding:11px 15px;margin:4px 40px 4px 0;
  font-size:14px;line-height:1.75;color:{C['TEXT']}}}
.msg-label{{font-size:11px;color:{C['TEXT2']};margin-bottom:3px;font-weight:500}}
.mm-box{{background:{C['BG3']};border:1px solid {C['BORDER']};border-radius:12px;padding:14px;margin-bottom:10px}}
.mm-box p{{font-size:13px;color:{C['TEXT2']};margin:0;line-height:1.6}}
.step-label{{font-size:12px;color:{C['ACCENT']};font-weight:600;margin-bottom:6px;margin-top:12px}}
.summary-box{{background:{C['BG3']};border:1px solid {C['BORDER']};border-radius:10px;
  padding:12px 16px;font-size:13px;line-height:1.8;color:{C['TEXT']};margin-bottom:10px}}
.stTextArea textarea{{background:{C['BG3']}!important;color:{C['TEXT']}!important;
  border:1px solid {C['BORDER']}!important;border-radius:10px!important;
  font-family:'Tajawal',sans-serif!important;font-size:14px!important;direction:rtl!important}}
.stTextArea textarea:focus{{border-color:{C['ACCENT']}!important}}
.stButton>button{{background:{C['ACCENT']}!important;color:#fff!important;border:none!important;
  border-radius:8px!important;font-family:'Tajawal',sans-serif!important;font-weight:600!important;
  width:100%;transition:all .2s!important}}
.stButton>button:hover{{background:{C['ACCENT2']}!important}}
button[kind="secondary"]{{background:{C['BG3']}!important;color:{C['TEXT2']}!important;
  border:1px solid {C['BORDER']}!important}}
button[kind="secondary"]:hover{{border-color:{C['ACCENT']}!important;color:{C['TEXT']}!important}}
</style>
""", unsafe_allow_html=True)

# ── دوال API مبسطة ──
def warmup():
    if not st.session_state.backend_warm:
        try:
            requests.get(f"{API_BASE.replace('/api','')}/health", timeout=10)
            st.session_state.backend_warm = True
        except:
            pass

def fetch_count():
    try:
        return requests.get(f"{API_BASE}/documents/count", timeout=3).json().get("count", 0)
    except:
        return st.session_state.doc_count

def ask_llm(prompt):
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": prompt, "history": [], "stream": False}, timeout=120)
        return r.json().get("answer", "")
    except:
        return ""

def ask_chat(q):
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": q, "history": st.session_state.history, "stream": False}, timeout=120)
        d = r.json()
        if "documents_count" in d:
            st.session_state.doc_count = d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except:
        return "⚠️ عذراً، حدث خطأ في الاتصال. حاول مرة أخرى."

def upload_backend(f):
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)}, timeout=30)
        return True, "تم الرفع"
    except:
        return False, "فشل الرفع"

def extract_text_simple(f):
    """استخراج النص من الملف ببساطة"""
    try:
        import fitz
        data = f.getvalue()
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join([p.get_text() for p in doc])
        doc.close()
        if text.strip():
            return True, text[:4000]
    except:
        pass
    
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(f.getvalue()))
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        if text.strip():
            return True, text[:4000]
    except:
        pass
    
    try:
        from docx import Document
        doc = Document(io.BytesIO(f.getvalue()))
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        if text.strip():
            return True, text[:4000]
    except:
        pass
    
    return False, "تعذر قراءة الملف"

def summarize_for_mindmap(text):
    prompt = f"""استخرج من النص التالي هيكلاً عربياً فقط للخريطة الذهنية:

التنسيق المطلوب:
السطر الأول: العنوان الرئيسي (بدون ##)
ثم لكل فرع: ## ثم اسم الفرع
ثم تحته: - ثم نقطة فرعية

النص:
{text[:3000]}

الخرج المطلوب فقط (بدون شرح):"""
    
    return ask_llm(prompt).strip()

def parse_mindmap(text):
    """تحويل النص إلى JSON ببساطة"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return {"topic": "الموضوع", "children": []}
    
    title = lines[0][:50]
    branches = []
    current = None
    kids = []
    
    for line in lines[1:]:
        if line.startswith('##'):
            if current:
                branches.append({"topic": current, "children": [{"topic": k, "children": []} for k in kids]})
            current = line.replace('##', '').strip()[:40]
            kids = []
        elif line.startswith('-'):
            kid = line.replace('-', '').strip()[:40]
            if kid and current:
                kids.append(kid)
    
    if current:
        branches.append({"topic": current, "children": [{"topic": k, "children": []} for k in kids]})
    
    return {"topic": title, "children": branches}

# ── دالة الخريطة ──
def render_mindmap(data):
    js = json.dumps(data, ensure_ascii=False)
    sv = C['SVG']; n0 = C['N0']; n1 = C['N1']; n2 = C['N2']
    tc = C['TC']; bb = C['BB']; bbd = C['BBD']; bbt = C['BBT']
    
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{sv};overflow:hidden;font-family:'Tajawal',sans-serif}}
#cv{{width:100%;height:520px;display:block;cursor:grab}}
#cv:active{{cursor:grabbing}}
.ctrl{{position:absolute;bottom:10px;left:10px;display:flex;gap:5px;z-index:99}}
.btn{{background:{bb};border:1px solid {bbd};color:{bbt};padding:5px 11px;border-radius:6px;
  cursor:pointer;font-size:11px;font-family:inherit}}
.btn:hover{{border-color:#4f5ef0;color:#4f5ef0}}
#sb{{background:#4f5ef0;color:#fff}}
</style>
</head><body>
<div style="position:relative;width:100%;height:520px">
<svg id="cv"></svg>
<div class="ctrl">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳</button>
  <button class="btn" id="sb">💾</button>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA = {js};
const COLS = ['#4f5ef0','#16a34a','#d97706','#7c3aed','#0891b2','#db2777','#dc2626'];

function draw() {{
    const W = window.innerWidth - 20;
    const H = 520;
    const svg = d3.select('#cv').attr('viewBox', `0 0 ${{W}} ${{H}}`).html('');
    const g = svg.append('g');
    
    const nodes = [];
    const links = [];
    
    // الجذر
    nodes.push({{id:0, depth:0, x:W/2, y:H/2, text:DATA.topic, color:COLS[0]}});
    
    const children = DATA.children || [];
    const n = children.length;
    const R = Math.min(W, H) * 0.28;
    
    children.forEach((c, i) => {{
        const angle = (2 * Math.PI * i / n) - Math.PI/2;
        const x = W/2 + R * Math.cos(angle);
        const y = H/2 + R * Math.sin(angle);
        const id = nodes.length;
        nodes.push({{id, depth:1, x, y, text:c.topic, color:COLS[(i+1)%COLS.length]}});
        links.push({{sx:W/2, sy:H/2, tx:x, ty:y}});
        
        const subs = c.children || [];
        const r2 = R * 0.7;
        subs.forEach((s, j) => {{
            const a2 = angle + (j - (subs.length-1)/2) * 0.35;
            const x2 = x + r2 * Math.cos(a2);
            const y2 = y + r2 * Math.sin(a2);
            nodes.push({{id:nodes.length, depth:2, x:x2, y:y2, text:s.topic, color:COLS[(i+1)%COLS.length]}});
            links.push({{sx:x, sy:y, tx:x2, ty:y2}});
        }});
    }});
    
    // رسم الخطوط
    links.forEach(l => {{
        g.append('line')
            .attr('x1', l.sx).attr('y1', l.sy)
            .attr('x2', l.tx).attr('y2', l.ty)
            .attr('stroke', '#4f5ef0').attr('stroke-width', 1.5).attr('opacity', 0.5);
    }});
    
    // رسم العقد
    nodes.forEach(n => {{
        const fontSize = n.depth===0 ? 13 : (n.depth===1 ? 11 : 9);
        const w = Math.min(100, n.text.length * fontSize * 0.6 + 20);
        const h = 30;
        
        g.append('rect')
            .attr('x', n.x - w/2).attr('y', n.y - h/2)
            .attr('width', w).attr('height', h).attr('rx', 8)
            .attr('fill', n.depth===0 ? '#4f5ef0' : (n.depth===1 ? '{n1}' : '{n2}'))
            .attr('stroke', n.color).attr('stroke-width', 1.5);
        
        g.append('text')
            .attr('x', n.x).attr('y', n.y + 5)
            .attr('text-anchor', 'middle').attr('font-size', fontSize)
            .attr('fill', n.depth===0 ? '#fff' : '{tc}')
            .text(n.text.length > 25 ? n.text.slice(0,22)+'...' : n.text);
    }});
}}

const svg = d3.select('#cv');
const zoom = d3.zoom().scaleExtent([0.3, 2.5]).on('zoom', e => {{
    d3.select('#cv g').attr('transform', e.transform);
}});
svg.call(zoom);

document.getElementById('zm').onclick = () => svg.transition().call(zoom.scaleBy, 0.8);
document.getElementById('zp').onclick = () => svg.transition().call(zoom.scaleBy, 1.2);
document.getElementById('zr').onclick = () => svg.transition().call(zoom.transform, d3.zoomIdentity);

document.getElementById('sb').onclick = function() {{
    const svgEl = document.getElementById('cv');
    const clone = svgEl.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.style.background = '{sv}';
    const src = new XMLSerializer().serializeToString(clone);
    const blob = new Blob([src], {{type: 'image/svg+xml'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.download = 'mindmap.svg';
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
}};

draw();
window.addEventListener('resize', () => setTimeout(draw, 200));
</script>
</body></html>"""
    components.html(html, height=540, scrolling=False)

# ══ HEADER ══
warmup()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = f"RAG ✓ {st.session_state.doc_count}" if st.session_state.doc_count > 0 else "chat"

col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f'<div class="top-bar"><h2>🔬 مساعد البحث الذكي</h2><span class="badge {mc}">{mt}</span></div>', unsafe_allow_html=True)
with col2:
    if st.button("🌙" if T == "light" else "☀️"):
        st.session_state.theme = "dark" if T == "light" else "light"
        st.rerun()

# ── TABS ──
tab_chat, tab_mm = st.tabs(["💬 دردشة", "🗺️ خريطة ذهنية"])

# ══ SIDEBAR خفيف ══
with st.sidebar:
    st.markdown("### 📁 رفع ملف")
    uploaded = st.file_uploader("PDF أو DOCX", type=["pdf", "docx"], label_visibility="collapsed")
    
    if uploaded:
        st.caption(f"📄 {uploaded.name[:30]}")
        
        # زر واحد للخريطة
        if st.button("🗺️ تحويل لخريطة ذهنية", use_container_width=True):
            with st.spinner("📖 جاري قراءة الملف..."):
                ok, text = extract_text_simple(uploaded)
            
            if ok and text:
                st.session_state.mm_raw_text = text
                with st.spinner("🧠 جاري التحليل..."):
                    summary = summarize_for_mindmap(text)
                    if summary:
                        st.session_state.mm_summary = summary
                        st.session_state.mm_data = parse_mindmap(summary)
                    else:
                        st.session_state.mm_summary = text
                        st.session_state.mm_data = parse_mindmap(text)
                    st.session_state.mm_step = 1
                st.success("✅ تم!")
                st.rerun()
            else:
                st.error(f"❌ {text}")
        
        # زر رفع للدردشة
        if st.button("💬 رفع للدردشة", use_container_width=True):
            with st.spinner("رفع..."):
                ok, msg = upload_backend(uploaded)
            if ok:
                st.success("✅ تم الرفع")
                st.session_state.doc_count = fetch_count()
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ {msg}")
    
    st.divider()
    
    if st.button("🗑️ مسح المحادثة", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    
    st.caption(f"📊 وثائق: {st.session_state.doc_count}")
    st.caption("🟢 متصل" if st.session_state.backend_warm else "🔵 وضع غير متصل")

# ══ TAB 1: الدردشة ══
with tab_chat:
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f'<div class="msg-label" style="text-align:right">أنت</div>'
                        f'<div class="msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="msg-label">المساعد</div>'
                        f'<div class="msg-ai">{msg["content"]}</div>', unsafe_allow_html=True)
    
    with st.form("chat_form", clear_on_submit=True):
        q = st.text_area("", placeholder="اكتب سؤالك...", label_visibility="collapsed", height=80)
        submitted = st.form_submit_button("إرسال ➤", use_container_width=True)
    
    if submitted and q.strip():
        with st.spinner("🤔 جاري التفكير..."):
            ans = ask_chat(q.strip())
        st.session_state.history.append({"role": "user", "content": q.strip()})
        st.session_state.history.append({"role": "assistant", "content": ans})
        st.rerun()

# ══ TAB 2: الخريطة الذهنية ══
with tab_mm:
    if st.session_state.mm_step == 0:
        st.markdown(f'<div class="mm-box"><p>📝 الصق نصاً أو ارفع ملفاً من الشريط الجانبي</p></div>', unsafe_allow_html=True)
        
        with st.form("mm_form", clear_on_submit=False):
            text_input = st.text_area("النص", placeholder="الصق النص هنا...", 
                                       height=150, value=st.session_state.mm_raw_text)
            submitted = st.form_submit_button("🧠 إنشاء خريطة", use_container_width=True)
        
        if submitted and text_input.strip():
            st.session_state.mm_raw_text = text_input.strip()
            with st.spinner("🧠 جاري التحليل..."):
                summary = summarize_for_mindmap(text_input.strip())
                if summary:
                    st.session_state.mm_summary = summary
                    st.session_state.mm_data = parse_mindmap(summary)
                else:
                    st.session_state.mm_summary = text_input.strip()
                    st.session_state.mm_data = parse_mindmap(text_input.strip())
                st.session_state.mm_step = 1
            st.rerun()
    
    elif st.session_state.mm_step == 1:
        with st.expander("📋 الملخص", expanded=False):
            st.markdown(f'<div class="summary-box">{st.session_state.mm_summary.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        
        if st.session_state.mm_data:
            render_mindmap(st.session_state.mm_data)
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 نص جديد", use_container_width=True):
                st.session_state.mm_step = 0
                st.session_state.mm_raw_text = ""
                st.session_state.mm_summary = ""
                st.session_state.mm_data = None
                st.rerun()
        with col_b:
            if st.button("🔁 إعادة التلخيص", use_container_width=True):
                with st.spinner("🔄 جاري..."):
                    summary = summarize_for_mindmap(st.session_state.mm_raw_text)
                    if summary:
                        st.session_state.mm_summary = summary
                        st.session_state.mm_data = parse_mindmap(summary)
                    st.rerun()
