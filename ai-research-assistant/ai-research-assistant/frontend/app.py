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
    prompt = f"""You must output ONLY a structured outline in Arabic. No explanations. No intro. Just the outline.

EXACT FORMAT — follow it precisely:
Line 1: the main title (max 5 Arabic words, no ## prefix)
Then 3 to 5 main branches, each on its own line starting with ##
Each ## branch must be followed by 2 to 4 detail lines starting with -
Each ## branch title: max 4 Arabic words
Each - detail: max 6 Arabic words

EXAMPLE:
التجارة الإلكترونية
## النمو والأرقام
- نمو 265٪ في المبيعات
- 4.88 تريليون دولار بحلول 2021
## فوائد للشركات
- التميز عن المنافسين
- خفض التكاليف

Now do the same for this text:
{text[:2500]}

OUTPUT:"""

    result = ask_llm(prompt)
    return result.strip() if result else ""


def parse_mindmap_structure(structured_text: str) -> dict:
    """
    يحوّل النص الهيكلي إلى JSON للخريطة.
    يفهم الصيغ:
      العنوان
      ## فرع رئيسي
      - تفصيل
    وأيضاً حالة ##- مدمجة التي يولدها الموديل أحياناً.
    """
    # أولاً: فصل ##- إلى سطرين
    text = re.sub(r'(##[^#\n]+?)\s*-\s*', r'\1\n- ', structured_text)
    # فصل نقاط متعددة على سطر واحد مفصولة بـ -
    lines = []
    for raw in text.split('\n'):
        raw = raw.strip()
        if not raw:
            continue
        # سطر يبدأ بـ ## ويحتوي - بعده → فصل
        if raw.startswith('##') and '-' in raw:
            parts = raw.split('-')
            lines.append(parts[0].strip())
            for p in parts[1:]:
                if p.strip():
                    lines.append('- ' + p.strip())
        else:
            lines.append(raw)

    if not lines:
        return {"topic": "الموضوع", "children": []}

    # السطر الأول = العنوان (أزل أي ## في البداية)
    title = re.sub(r'^#+\s*', '', lines[0]).strip()
    # اختصر العنوان لـ 5 كلمات إذا كان طويلاً
    title_words = title.split()
    title = ' '.join(title_words[:6]) if len(title_words) > 6 else title

    branches = []
    current_branch = None
    current_children = []

    for line in lines[1:]:
        if line.startswith('##') or (not line.startswith('-') and not line.startswith('•')
                                      and not line.startswith('*') and len(line) > 3
                                      and current_branch is None):
            # فرع رئيسي جديد
            if current_branch is not None:
                branches.append({
                    "topic": current_branch,
                    "children": [{"topic": c, "children": []} for c in current_children]
                })
            raw_branch = re.sub(r'^#+\s*', '', line).strip()
            # اختصر لـ 4 كلمات
            words = raw_branch.split()
            current_branch = ' '.join(words[:5]) if len(words) > 5 else raw_branch
            current_children = []

        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            child = re.sub(r'^[-•*]\s*', '', line).strip()
            # اختصر لـ 6 كلمات
            words = child.split()
            child = ' '.join(words[:7]) if len(words) > 7 else child
            if child and current_branch is not None:
                current_children.append(child)

    # أضف الفرع الأخير
    if current_branch is not None:
        branches.append({
            "topic": current_branch,
            "children": [{"topic": c, "children": []} for c in current_children]
        })

    # fallback
    if not branches:
        chunks = [re.sub(r'^[-•*##\s]+','',l).strip() for l in lines[1:] if len(l) > 8][:7]
        branches = [{"topic": ' '.join(c.split()[:5]), "children": []} for c in chunks]

    return {"topic": title, "children": branches[:6]}


# ── دالة الخريطة الذهنية المحسّنة للجوال ──
def render_mindmap(data: dict):
    json_str = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f1117;overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif;touch-action:pan-x pan-y;}}
#cv{{width:100%;height:620px;display:block;cursor:grab}}
#cv:active{{cursor:grabbing}}
.ctrl{{position:fixed;bottom:12px;left:12px;display:flex;gap:6px;z-index:99}}
.btn{{background:#1e2238;border:1px solid #2e3248;color:#8b90a7;padding:6px 14px;
      border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;transition:all .2s}}
.btn:hover{{border-color:#5b6ef5;color:#e8eaf0;background:#23273a}}
@media (max-width: 500px) {{
  .btn{{padding:8px 16px;font-size:14px;}}
  #cv{{height:550px;}}
}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet"/>
</head><body>
<svg id="cv"></svg>
<div class="ctrl">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳</button>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA  = {json_str};
const COLS  = ['#5b6ef5','#22c55e','#f59e0b','#8b5cf6','#06b6d4','#ec4899','#ef4444'];

/* ── تقليل عدد الفروع في الجوال ── */
function optimizeForMobile(data, isMobile) {{
  if(!isMobile) return data;
  // في الجوال: نخفّض عدد الفروع الرئيسية إلى 4 كحد أقصى
  const optimized = {{
    topic: data.topic,
    children: (data.children || []).slice(0, 4).map(child => ({{
      topic: child.topic,
      children: (child.children || []).slice(0, 3)  // كل فرع له 3 تفاصيل كحد أقصى
    }}))
  }};
  return optimized;
}}

/* ── حساب حجم المستطيل بناءً على النص (مع دعم الجوال) ── */
function boxSize(text, depth) {{
  const words = text.split(' ');
  const isMobile = window.innerWidth < 500;
  
  // تصغير الخط في الجوال
  const fs = isMobile
    ? (depth===0 ? 11 : depth===1 ? 10 : 9)
    : (depth===0 ? 13 : depth===1 ? 11 : 10);
    
  const maxW = isMobile
    ? (depth===0 ? 85 : depth===1 ? 75 : 65)
    : (depth===0 ? 110 : depth===1 ? 100 : 90);
    
  const lh = fs + 5;
  
  // تقسيم النص لأسطر
  let line='', lines=[];
  words.forEach(w=>{{
    const t=line?line+' '+w:w;
    if(t.length*fs*0.55>maxW && line){{lines.push(line);line=w;}}
    else line=t;
  }});
  if(line) lines.push(line);
  
  // تأكد من وجود سطر واحد على الأقل
  if(lines.length === 0 && text) lines = [text];
  
  const W2 = Math.min(maxW, Math.max(50, lines.reduce((a,l)=>Math.max(a,l.length*fs*0.55),0)+16));
  const H2 = Math.max(lines.length*lh + 12, 32);
  return {{w:W2, h:H2, lines, fs, lh}};
}}

/* ── رسم النص داخل المستطيل ── */
function drawText(g, box, x, y) {{
  const {{lines,fs,lh,w,h}} = box;
  const startY = y - h/2 + (h - lines.length*lh)/2 + lh*0.7;
  lines.forEach((l,i)=>{{
    g.append('text')
      .attr('x', x).attr('y', startY + i*lh)
      .attr('text-anchor','middle')
      .attr('font-size', fs+'px')
      .attr('font-family',"'Tajawal','Segoe UI',sans-serif")
      .attr('fill', '#e8eaf0')
      .attr('pointer-events','none')
      .text(l);
  }});
}}

/* ── حساب مواضع الفروع متكيفة مع الشاشة ── */
function layoutTree(data, W, H) {{
  const isMobile = W < 500;
  const optimizedData = optimizeForMobile(data, isMobile);
  const nodes = [];
  const links = [];

  // الجذر في المنتصف
  const rootBox = boxSize(optimizedData.topic, 0);
  const root = {{id:0, depth:0, x:W/2, y:H/2, box:rootBox, color:'#5b6ef5', topic:optimizedData.topic}};
  nodes.push(root);

  const children = optimizedData.children || [];
  const n = children.length;
  if(n===0) return {{nodes, links}};

  // 🔥 المسافات المتكيفة مع حجم الشاشة وعدد العناصر
  const base = Math.min(W, H);
  
  // R1 للمستوى الأول
  const R1 = isMobile
    ? base * (0.38 + Math.min(children.length * 0.035, 0.15))
    : base * 0.32;
  
  // توزيع الفروع الرئيسية على دائرة (مع زاوية ممددة للجوال)
  children.forEach((child, ci) => {{
    const spreadFactor = isMobile ? 1.4 : 1;
    const angle = (2 * Math.PI * ci / (n * spreadFactor)) - Math.PI/2;
    const cx = W/2 + R1 * Math.cos(angle);
    const cy = H/2 + R1 * Math.sin(angle);
    const col = COLS[ci % COLS.length];
    const cBox = boxSize(child.topic, 1);
    const cNode = {{id:nodes.length, depth:1, x:cx, y:cy, box:cBox, color:col, topic:child.topic, parentId:0}};
    nodes.push(cNode);
    links.push({{sx:W/2, sy:H/2, tx:cx, ty:cy, col}});

    // الفروع الثانوية
    const subs = child.children || [];
    const ns = subs.length;
    if(ns===0) return;

    // 🔥 R2 متكيف للجوال
    const R2 = isMobile
      ? base * 0.28
      : base * 0.22;
    
    // زاوية انتشار أقل في الجوال
    const spread = Math.min(Math.PI * (isMobile ? 0.45 : 0.55), ns * (isMobile ? 0.28 : 0.38));
    
    subs.forEach((sub, si) => {{
      const subAngle = angle - spread/2 + spread * (si / (Math.max(ns-1, 1)));
      const sx2 = cx + R2 * Math.cos(subAngle);
      const sy2 = cy + R2 * Math.sin(subAngle);
      const sBox = boxSize(sub.topic, 2);
      nodes.push({{id:nodes.length, depth:2, x:sx2, y:sy2, box:sBox, color:col+'99', topic:sub.topic, parentId:cNode.id}});
      links.push({{sx:cx, sy:cy, tx:sx2, ty:sy2, col:col+'88'}});
    }});
  }});

  return {{nodes, links}};
}}

/* ── الرسم الرئيسي مع التكيف على حجم النافذة ── */
function draw() {{
  const W = document.getElementById('cv').clientWidth;
  const H = document.getElementById('cv').clientHeight;

  const svg = d3.select('#cv').attr('viewBox', `0 0 ${{W}} ${{H}}`);
  svg.selectAll('*').remove(); // مسح المحتوى القديم
  const gAll = svg.append('g');

  const {{nodes, links}} = layoutTree(DATA, W, H);

  /* خطوط الوصل — منحنية */
  links.forEach(l=>{{
    const mx = (l.sx+l.tx)/2, my = (l.sy+l.ty)/2;
    gAll.append('path')
      .attr('d',`M${{l.sx}},${{l.sy}} Q${{mx}},${{l.sy}} ${{l.tx}},${{l.ty}}`)
      .attr('fill','none').attr('stroke',l.col)
      .attr('stroke-width', l.col.length>7 ? 1.2 : 2)
      .attr('stroke-opacity',0.7);
  }});

  /* عقد */
  nodes.forEach(n=>{{
    const {{w,h}} = n.box;
    const rx = n.depth===0 ? 14 : n.depth===1 ? 10 : 7;

    /* ظل/توهج */
    if(n.depth<=1) {{
      gAll.append('rect')
        .attr('x',n.x-w/2+2).attr('y',n.y-h/2+2)
        .attr('width',w).attr('height',h).attr('rx',rx)
        .attr('fill',n.color).attr('opacity',0.15);
    }}

    /* المستطيل */
    gAll.append('rect')
      .attr('x',n.x-w/2).attr('y',n.y-h/2)
      .attr('width',w).attr('height',h).attr('rx',rx)
      .attr('fill', n.depth===0?'#5b6ef5': n.depth===1?'#1e2238':'#13151f')
      .attr('stroke', n.color)
      .attr('stroke-width', n.depth===0?2.5: n.depth===1?1.8:1.2)
      .style('cursor','pointer')
      .on('mouseover', function(){{d3.select(this).attr('fill', n.depth===0?'#6b7ef9':'#23273a');}})
      .on('mouseout',  function(){{d3.select(this).attr('fill', n.depth===0?'#5b6ef5': n.depth===1?'#1e2238':'#13151f');}});

    /* النص */
    drawText(gAll, n.box, n.x, n.y);
  }});
}}

// تهيئة Zoom والرسم
let currentTransform = d3.zoomIdentity;
const svgElem = document.getElementById('cv');
const svg = d3.select(svgElem);
const zoom = d3.zoom().scaleExtent([0.25, 3.5]).on('zoom', (e) => {{
  currentTransform = e.transform;
  d3.select('#cv g').attr('transform', e.transform);
}});
svg.call(zoom).call(zoom.transform, currentTransform);

// وظيفة الرسم مع إعادة تعيين الـ Zoom
function initializeAndDraw() {{
  draw();
  // إعادة تعيين الـ Zoom إلى الوضع الافتراضي بعد الرسم
  svg.call(zoom.transform, d3.zoomIdentity);
  currentTransform = d3.zoomIdentity;
}}

// مستمعي الأزرار
document.getElementById('zm').onclick = ()=>svg.transition().duration(250).call(zoom.scaleBy, 0.72);
document.getElementById('zp').onclick = ()=>svg.transition().duration(250).call(zoom.scaleBy, 1.38);
document.getElementById('zr').onclick = ()=>svg.transition().duration(350).call(zoom.transform, d3.zoomIdentity);

// مراقبة تغيير حجم النافذة وإعادة الرسم تلقائياً
let resizeTimeout;
window.addEventListener('resize', () => {{
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {{
    initializeAndDraw();
  }}, 250);
}});

// التشغيل الأولي
initializeAndDraw();

</script></body></html>"""
    components.html(html, height=630, scrolling=False)


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
