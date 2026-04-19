import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
import re

API_BASE = os.getenv("API_BASE_URL", "https://hussamfaisal-ai-research-backend.hf.space/api")

st.set_page_config(page_title="مساعد البحث الذكي", page_icon="🔬", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'Tajawal',sans-serif!important;direction:rtl}
.stApp{background:#0f1117;color:#e8eaf0}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton{display:none}
div[data-testid="stToolbar"]{display:none}

/* top bar */
.top-bar{display:flex;align-items:center;justify-content:space-between;
  padding:12px 0 16px;border-bottom:1px solid #2e3248;margin-bottom:20px}
.top-bar h2{margin:0;font-size:18px;font-weight:700;color:#e8eaf0}
.badge{font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid #2e3248;color:#8b90a7}
.badge.rag{border-color:#22c55e;color:#22c55e;background:rgba(34,197,94,.1)}

/* mode tabs */
.mode-tabs{display:flex;gap:8px;margin-bottom:20px}
.tab{flex:1;text-align:center;padding:10px;border-radius:10px;cursor:pointer;
  font-size:14px;font-weight:500;border:1px solid #2e3248;color:#8b90a7;
  background:#1a1d27;transition:all .2s}
.tab.active{background:#5b6ef5;border-color:#5b6ef5;color:#fff}
.tab:hover:not(.active){border-color:#5b6ef5;color:#e8eaf0}

/* chat bubbles */
.msg-user{background:#23273a;border:1px solid #2e3248;border-radius:12px 3px 12px 12px;
  padding:10px 14px;margin:6px 0 6px 40px;font-size:14px;line-height:1.7;color:#e8eaf0}
.msg-ai{background:#1e2238;border:1px solid #2e3248;border-radius:3px 12px 12px 12px;
  padding:10px 14px;margin:4px 40px 4px 0;font-size:14px;line-height:1.7;color:#e8eaf0}
.msg-label{font-size:11px;color:#8b90a7;margin-bottom:2px}

/* mindmap input area */
.mm-box{background:#1a1d27;border:1px solid #2e3248;border-radius:12px;
  padding:16px;margin-bottom:12px}
.mm-box p{font-size:12px;color:#8b90a7;margin-bottom:8px;line-height:1.6}

/* misc */
.success-box{background:rgba(34,197,94,.08);border:1px solid #22c55e;border-radius:8px;padding:10px 14px;color:#22c55e;font-size:13px}
.error-box{background:rgba(239,68,68,.08);border:1px solid #ef4444;border-radius:8px;padding:10px 14px;color:#ef4444;font-size:13px}
.upload-info{background:#1a1d27;border:1px solid #2e3248;border-radius:8px;padding:8px 12px;font-size:12px;color:#8b90a7;margin-bottom:8px}
.step-label{font-size:12px;color:#5b6ef5;font-weight:600;margin-bottom:6px;margin-top:14px}
.summary-box{background:#1e2238;border:1px solid #3d4fd4;border-radius:10px;
  padding:12px 16px;font-size:13px;line-height:1.8;color:#c8cadc;margin-bottom:12px}

/* inputs */
.stTextArea textarea{background:#23273a!important;color:#e8eaf0!important;
  border:1px solid #2e3248!important;border-radius:10px!important;
  font-family:'Tajawal',sans-serif!important;font-size:14px!important;direction:rtl!important}
.stTextArea textarea:focus{border-color:#5b6ef5!important}
.stButton>button{background:#5b6ef5!important;color:#fff!important;border:none!important;
  border-radius:8px!important;font-family:'Tajawal',sans-serif!important;font-weight:500!important;width:100%}
.stButton>button:hover{background:#3d4fd4!important}
button[kind="secondary"]{background:transparent!important;color:#8b90a7!important;
  border:1px solid #2e3248!important}
button[kind="secondary"]:hover{border-color:#5b6ef5!important;color:#e8eaf0!important}
</style>
""", unsafe_allow_html=True)

# ── session state ──
defaults = {
    "history": [], "doc_count": 0,
    "mode": "chat",           # "chat" | "mindmap"
    "mm_raw_text": "",        # النص الخام
    "mm_summary": "",         # الملخص من الذكاء
    "mm_data": None,          # JSON الخريطة
    "mm_step": 0,             # 0=input, 1=summary_ready, 2=map_shown
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── API helpers ──
def warmup():
    try: requests.get(f"{API_BASE.replace('/api','')}/health", timeout=8)
    except: pass

def fetch_count():
    try: return requests.get(f"{API_BASE}/documents/count", timeout=5).json().get("count", 0)
    except: return st.session_state.doc_count

def ask_llm(prompt: str, system: str = "") -> str:
    """استدعاء الموديل مباشرة."""
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": prompt, "history": [], "stream": False},
            timeout=300)
        return r.json().get("answer", "")
    except requests.exceptions.Timeout:
        return ""
    except Exception:
        return ""

def ask_chat(q: str) -> str:
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": q, "history": st.session_state.history, "stream": False},
            timeout=300)
        d = r.json()
        if "documents_count" in d: st.session_state.doc_count = d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ الموديل يعمل على CPU — انتظر قليلاً وأعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال: {str(e)}"

def upload_file(f):
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)}, timeout=30)
        d = r.json()
        if not r.ok or "error" in d: return False, d.get("error") or d.get("detail", "خطأ")
        return True, d.get("message", "تم الرفع")
    except Exception as e: return False, str(e)


# ── mindmap: LLM summary → structured points ──
def summarize_for_mindmap(text: str) -> str:
    """يطلب من الذكاء تلخيص النص كنقاط هيكلية جاهزة للخريطة."""
    prompt = f"""لخّص النص التالي على شكل نقاط هيكلية واضحة مناسبة لخريطة ذهنية.

التعليمات:
- أول سطر: عنوان رئيسي قصير (أقل من 6 كلمات)
- ثم 4 إلى 6 فروع رئيسية، كل فرع يبدأ بـ ##
- تحت كل فرع 2 إلى 3 نقاط تفصيلية، كل نقطة تبدأ بـ -
- لا تكتب أي شيء آخر

النص:
{text[:2500]}

الملخص الهيكلي:"""

    result = ask_llm(prompt)
    return result.strip() if result else ""


def parse_mindmap_structure(structured_text: str) -> dict:
    """
    يحوّل النص الهيكلي إلى JSON للخريطة.
    يفهم صيغة:
      العنوان
      ## فرع رئيسي
      - تفصيل
    """
    lines = [l.strip() for l in structured_text.split('\n') if l.strip()]
    if not lines:
        return {"topic": "الموضوع", "children": []}

    title = re.sub(r'^#+\s*', '', lines[0])[:60]
    branches = []
    current_branch = None
    current_children = []

    for line in lines[1:]:
        if line.startswith('##'):
            if current_branch:
                branches.append({
                    "topic": current_branch,
                    "children": [{"topic": c, "children": []} for c in current_children]
                })
            current_branch = re.sub(r'^#+\s*', '', line).strip()[:55]
            current_children = []
        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            child = re.sub(r'^[-•*]\s*', '', line).strip()[:60]
            if child and current_branch:
                current_children.append(child)
        else:
            # سطر عادي بدون علامة
            if current_branch:
                current_children.append(line[:60])

    if current_branch:
        branches.append({
            "topic": current_branch,
            "children": [{"topic": c, "children": []} for c in current_children]
        })

    # fallback إذا ما في فروع
    if not branches:
        chunks = [l for l in lines[1:] if len(l) > 8][:8]
        branches = [{"topic": c[:55], "children": []} for c in chunks]

    return {"topic": title, "children": branches[:7]}


# ── D3 radial mindmap renderer ──
def render_mindmap(data: dict):
    json_str = json.dumps(data, ensure_ascii=False)
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f1117;overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif}}
svg{{width:100%;height:600px;display:block;cursor:grab}}
svg:active{{cursor:grabbing}}
.link{{fill:none;stroke-opacity:.7}}
.link-0{{stroke:#5b6ef5;stroke-width:2.5px}}
.link-1{{stroke:#3d4fd4;stroke-width:1.8px}}
.link-2{{stroke:#2e3248;stroke-width:1.2px}}
.node-text{{pointer-events:none;font-family:'Tajawal','Segoe UI',sans-serif}}
.controls{{position:fixed;bottom:12px;left:12px;display:flex;gap:6px;z-index:99}}
.btn{{background:#1e2238;border:1px solid #2e3248;color:#8b90a7;padding:6px 14px;
      border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;transition:all .2s}}
.btn:hover{{border-color:#5b6ef5;color:#e8eaf0;background:#23273a}}
.legend{{position:fixed;top:10px;right:10px;background:#1a1d27cc;border:1px solid #2e3248;
  border-radius:8px;padding:8px 12px;font-size:11px;color:#8b90a7;line-height:2}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet"/>
</head><body>
<svg id="svg"></svg>
<div class="controls">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳ إعادة</button>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA = {json_str};
const W = window.innerWidth || 720;
const H = 600;

const svg  = d3.select('#svg').attr('viewBox',`0 0 ${{W}} ${{H}}`);
const gAll = svg.append('g');

const zoom = d3.zoom().scaleExtent([0.2,3]).on('zoom', e => gAll.attr('transform', e.transform));
svg.call(zoom).call(zoom.transform, d3.zoomIdentity.translate(W/2, H/2));

document.getElementById('zm').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 0.7);
document.getElementById('zp').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1.4);
document.getElementById('zr').onclick = () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity.translate(W/2,H/2));

const COLORS = ['#5b6ef5','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899'];

function wrapText(sel, text, maxChars) {{
  const words = text.split(' ');
  let line='', lines=[];
  words.forEach(w => {{
    const t = line ? line+' '+w : w;
    if(t.length > maxChars && line) {{ lines.push(line); line=w; }}
    else line=t;
  }});
  if(line) lines.push(line);
  const lh = 14, start = -(lines.length-1)*lh/2;
  lines.forEach((l,i) => sel.append('tspan').attr('x',0).attr('dy', i===0 ? start : lh).text(l));
}}

function draw() {{
  gAll.selectAll('*').remove();
  const root = d3.hierarchy(DATA);
  const R = Math.min(W,H) * 0.40;
  d3.tree().size([2*Math.PI, R]).separation((a,b) => (a.parent===b.parent?1:2.2)/a.depth)(root);

  // روابط
  gAll.selectAll('.link')
    .data(root.links()).enter().append('path')
    .attr('class', d => `link link-${{d.source.depth}}`)
    .attr('d', d3.linkRadial().angle(d=>d.x).radius(d=>d.y));

  // عقد
  const node = gAll.selectAll('g.n')
    .data(root.descendants()).enter()
    .append('g').attr('class','n')
    .attr('transform', d=>`rotate(${{d.x*180/Math.PI-90}}) translate(${{d.y}},0)`);

  // دوائر
  node.append('circle')
    .attr('r', d => d.depth===0 ? 32 : d.depth===1 ? 20 : 13)
    .attr('fill', d => {{
      if(d.depth===0) return '#5b6ef5';
      if(d.depth===1) {{
        const idx = root.children ? root.children.indexOf(d) : 0;
        return COLORS[idx % COLORS.length] + '33';
      }}
      return '#1a1d27';
    }})
    .attr('stroke', d => {{
      if(d.depth===0) return '#7b8ef5';
      if(d.depth===1) {{
        const idx = root.children ? root.children.indexOf(d) : 0;
        return COLORS[idx % COLORS.length];
      }}
      return '#3d4fd4';
    }})
    .attr('stroke-width', d => d.depth===0 ? 2.5 : 1.8)
    .style('cursor', 'pointer')
    .on('mouseover', function(e,d) {{
      d3.select(this).transition().duration(150).attr('r',
        d.depth===0?36:d.depth===1?24:16);
    }})
    .on('mouseout', function(e,d) {{
      d3.select(this).transition().duration(150).attr('r',
        d.depth===0?32:d.depth===1?20:13);
    }});

  // نصوص
  node.append('text')
    .attr('class','node-text')
    .attr('transform', d => `rotate(${{-(d.x*180/Math.PI-90)}})`)
    .attr('text-anchor','middle')
    .attr('dy','0.1em')
    .attr('fill', d => d.depth===0 ? '#fff' : d.depth===1 ? '#e8eaf0' : '#9093ab')
    .attr('font-size', d => d.depth===0 ? '13px' : d.depth===1 ? '11px' : '10px')
    .attr('font-weight', d => d.depth<=1 ? '600' : '400')
    .each(function(d) {{
      wrapText(d3.select(this), d.data.topic, d.depth===0 ? 7 : d.depth===1 ? 9 : 11);
    }});
}}

draw();
window.addEventListener('resize', draw);
</script></body></html>"""
    components.html(html, height=610, scrolling=False)


# ── HEADER ──
warmup()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"
st.markdown(f'<div class="top-bar"><h2>🔬 مساعد البحث الذكي</h2><span class="badge {mc}">{mt}</span></div>', unsafe_allow_html=True)

# ── MODE TABS ──
st.markdown('<div class="mode-tabs">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    chat_active = "active" if st.session_state.mode == "chat" else ""
    if st.button("💬  دردشة ذكية", key="tab_chat", use_container_width=True,
                 type="primary" if st.session_state.mode == "chat" else "secondary"):
        st.session_state.mode = "chat"
        st.rerun()
with c2:
    mm_active = "active" if st.session_state.mode == "mindmap" else ""
    if st.button("🗺️  خريطة ذهنية", key="tab_mm", use_container_width=True,
                 type="primary" if st.session_state.mode == "mindmap" else "secondary"):
        st.session_state.mode = "mindmap"
        st.session_state.mm_step = 0
        st.session_state.mm_summary = ""
        st.session_state.mm_data = None
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("### 📁 رفع الوثائق")
    uploaded = st.file_uploader("PDF أو DOCX", type=["pdf","docx"], label_visibility="collapsed")
    if uploaded:
        st.markdown(f'<div class="upload-info">📄 {uploaded.name}</div>', unsafe_allow_html=True)
        if st.button("⬆️ رفع", key="ubtn"):
            with st.spinner("جارٍ الرفع..."):
                ok, msg = upload_file(uploaded)
            if ok:
                st.markdown(f'<div class="success-box">✅ {msg}</div>', unsafe_allow_html=True)
                import time; time.sleep(3)
                st.session_state.doc_count = fetch_count()
                st.rerun()
            else:
                st.markdown(f'<div class="error-box">❌ {msg}</div>', unsafe_allow_html=True)
    st.divider()
    c1s, c2s = st.columns(2)
    with c1s:
        if st.button("🗑️ مسح", key="clr", type="secondary"):
            st.session_state.history = []
            st.session_state.mm_step = 0
            st.session_state.mm_summary = ""
            st.session_state.mm_data = None
            st.rerun()
    with c2s:
        if st.button("🔄", key="ref", type="secondary"):
            st.session_state.doc_count = fetch_count()
            st.rerun()
    st.divider()
    st.markdown(f"""<div style="font-size:12px;color:#8b90a7;line-height:1.9">
    <b style="color:#e8eaf0">الوضع:</b> {'🟢 RAG' if st.session_state.doc_count>0 else '🔵 Chat'}<br>
    <b style="color:#e8eaf0">وثائق:</b> {st.session_state.doc_count}
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════
# MODE 1: CHAT
# ════════════════════════════════════════
if st.session_state.mode == "chat":
    if not st.session_state.history:
        st.markdown("""<div style="text-align:center;padding:50px 0;color:#8b90a7">
        <div style="font-size:42px;opacity:.2;margin-bottom:14px">◎</div>
        <p style="font-size:14px">اسأل أي سؤال</p>
        <p style="font-size:12px;opacity:.5;margin-top:6px">ارفع ملفاً لتفعيل وضع RAG</p>
        </div>""", unsafe_allow_html=True)
    else:
        for turn in st.session_state.history:
            if turn["role"] == "user":
                st.markdown(f'<div class="msg-label" style="text-align:right">أنت</div><div class="msg-user">{turn["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-label">المساعد</div><div class="msg-ai">{turn["content"]}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.form("cf", clear_on_submit=True):
        q = st.text_area("س", placeholder="اكتب سؤالك هنا...", label_visibility="collapsed", height=85)
        sub = st.form_submit_button("إرسال ➤", use_container_width=True)

    if sub and q.strip():
        with st.spinner("جارٍ التفكير... ⏳"):
            ans = ask_chat(q.strip())
        st.session_state.history.append({"role": "user",      "content": q.strip()})
        st.session_state.history.append({"role": "assistant", "content": ans})
        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]
        st.rerun()


# ════════════════════════════════════════
# MODE 2: MINDMAP
# ════════════════════════════════════════
else:
    # ── خطوة 0: إدخال النص ──
    if st.session_state.mm_step == 0:
        st.markdown("""<div class="mm-box">
        <p>📝 <b style="color:#e8eaf0">كيف يعمل:</b><br>
        أدخل أي نص (مقال، ملاحظات، ملف) ← الذكاء يلخصه ويستخرج النقاط الرئيسية ← تظهر الخريطة الذهنية فوراً</p>
        </div>""", unsafe_allow_html=True)

        with st.form("mmf", clear_on_submit=False):
            raw = st.text_area(
                "النص",
                placeholder="الصق نصك هنا — مقال، ملاحظات، وثيقة...",
                label_visibility="collapsed",
                height=200,
                value=st.session_state.mm_raw_text,
            )
            go = st.form_submit_button("🧠  تحليل وبناء الخريطة", use_container_width=True)

        if go and raw.strip():
            st.session_state.mm_raw_text = raw.strip()

            with st.spinner("الذكاء يلخص النص ويستخرج النقاط... ⏳"):
                summary = summarize_for_mindmap(raw.strip())

            if summary:
                st.session_state.mm_summary = summary
                st.session_state.mm_data = parse_mindmap_structure(summary)
                st.session_state.mm_step = 1
            else:
                # fallback: استخدم النص مباشرة بدون LLM
                st.session_state.mm_summary = raw.strip()
                st.session_state.mm_data = parse_mindmap_structure(raw.strip())
                st.session_state.mm_step = 1

            st.rerun()

    # ── خطوة 1: عرض الملخص + الخريطة ──
    elif st.session_state.mm_step == 1:

        # الملخص الهيكلي
        st.markdown('<div class="step-label">📋 الملخص الهيكلي (الذي بنت عليه الخريطة)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-box">{st.session_state.mm_summary.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)

        # الخريطة
        st.markdown('<div class="step-label">🗺️ الخريطة الذهنية — اسحب للتنقل، استخدم +/− للتكبير</div>', unsafe_allow_html=True)
        if st.session_state.mm_data:
            render_mindmap(st.session_state.mm_data)

        # أزرار
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            if st.button("🔄 نص جديد", key="mm_reset", use_container_width=True, type="secondary"):
                st.session_state.mm_step = 0
                st.session_state.mm_raw_text = ""
                st.session_state.mm_summary = ""
                st.session_state.mm_data = None
                st.rerun()
        with cb:
            if st.button("✏️ تعديل النص", key="mm_edit", use_container_width=True, type="secondary"):
                st.session_state.mm_step = 0
                st.rerun()
