import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
import re
import time
from datetime import datetime

API_BASE = os.getenv("API_BASE_URL", "https://hussamfaisal-ai-research-backend.hf.space/api")

st.set_page_config(page_title="مساعد البحث الذكي", page_icon="🔬", layout="centered")

# ── session state ──
defaults = {
    "history": [],
    "doc_count": 0,
    "mode": "chat",
    "mm_raw_text": "",
    "mm_summary": "",
    "mm_data": None,
    "mm_step": 0,
    "theme": "light",
    "backend_warm": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

THEME = st.session_state.theme

# ── ألوان الثيم ──
if THEME == "light":
    BG = "#f8f9fc"
    BG2 = "#ffffff"
    BG3 = "#f0f2f8"
    BORDER = "#dde1f0"
    TEXT = "#1a1d2e"
    TEXT2 = "#6b7280"
    ACCENT = "#4f5ef0"
    ACCENT2 = "#3b4bd4"
    MSG_USER = "#eef0ff"
    MSG_AI = "#ffffff"
    CARD_BG = "#ffffff"
    SHADOW = "rgba(79,94,240,0.08)"
    SVG_BG = "#f8f9fc"
else:
    BG = "#0f1117"
    BG2 = "#1a1d27"
    BG3 = "#23273a"
    BORDER = "#2e3248"
    TEXT = "#e8eaf0"
    TEXT2 = "#8b90a7"
    ACCENT = "#5b6ef5"
    ACCENT2 = "#3d4fd4"
    MSG_USER = "#23273a"
    MSG_AI = "#1e2238"
    CARD_BG = "#1a1d27"
    SHADOW = "rgba(0,0,0,0.3)"
    SVG_BG = "#0f1117"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
html,body,[class*="css"]{{font-family:'Tajawal',sans-serif!important;direction:rtl}}
.stApp{{background:{BG};color:{TEXT}}}
#MainMenu,footer,header{{visibility:hidden}}
.stDeployButton{{display:none}}
div[data-testid="stToolbar"]{{display:none}}

.top-bar{{display:flex;align-items:center;justify-content:space-between;
  padding:12px 0 16px;border-bottom:2px solid {BORDER};margin-bottom:20px}}
.top-bar h2{{margin:0;font-size:19px;font-weight:700;color:{TEXT}}}
.badge{{font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid {BORDER};color:{TEXT2}}}
.badge.rag{{border-color:#22c55e;color:#22c55e;background:rgba(34,197,94,.1)}}

.msg-user{{background:{MSG_USER};border:1px solid {BORDER};border-radius:12px 3px 12px 12px;
  padding:11px 15px;margin:6px 0 6px 40px;font-size:14px;line-height:1.75;color:{TEXT}}}
.msg-ai{{background:{MSG_AI};border:1px solid {BORDER};box-shadow:0 2px 8px {SHADOW};
  border-radius:3px 12px 12px 12px;padding:11px 15px;margin:4px 40px 4px 0;
  font-size:14px;line-height:1.75;color:{TEXT}}}
.msg-label{{font-size:11px;color:{TEXT2};margin-bottom:3px;font-weight:500}}
.msg-time{{font-size:10px;color:{TEXT2};margin-top:4px;opacity:.7}}

.mm-box{{background:{BG3};border:1px solid {BORDER};border-radius:12px;padding:16px;margin-bottom:12px}}
.mm-box p{{font-size:13px;color:{TEXT2};margin-bottom:8px;line-height:1.6}}
.step-label{{font-size:12px;color:{ACCENT};font-weight:600;margin-bottom:6px;margin-top:14px}}
.summary-box{{background:{BG3};border:1px solid {BORDER};border-radius:10px;
  padding:12px 16px;font-size:13px;line-height:1.8;color:{TEXT};margin-bottom:12px}}

.success-box{{background:rgba(34,197,94,.08);border:1px solid #22c55e;border-radius:8px;padding:10px 14px;color:#16a34a;font-size:13px}}
.error-box{{background:rgba(239,68,68,.08);border:1px solid #ef4444;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px}}
.upload-info{{background:{BG3};border:1px solid {BORDER};border-radius:8px;padding:8px 12px;font-size:12px;color:{TEXT2};margin-bottom:8px}}

.stTextArea textarea{{background:{BG3}!important;color:{TEXT}!important;
  border:1px solid {BORDER}!important;border-radius:10px!important;
  font-family:'Tajawal',sans-serif!important;font-size:14px!important;direction:rtl!important}}
.stTextArea textarea:focus{{border-color:{ACCENT}!important;box-shadow:0 0 0 2px {ACCENT}22!important}}

.stButton>button{{background:{ACCENT}!important;color:#fff!important;border:none!important;
  border-radius:8px!important;font-family:'Tajawal',sans-serif!important;font-weight:600!important;
  width:100%;transition:all .2s!important}}
.stButton>button:hover{{background:{ACCENT2}!important;transform:translateY(-1px)!important}}
button[kind="secondary"]{{background:{BG3}!important;color:{TEXT2}!important;
  border:1px solid {BORDER}!important}}
button[kind="secondary"]:hover{{border-color:{ACCENT}!important;color:{TEXT}!important}}
</style>
""", unsafe_allow_html=True)

# ── API helpers ──
def warmup_once():
    if not st.session_state.backend_warm:
        try:
            requests.get(f"{API_BASE.replace('/api','')}/health", timeout=15)
            st.session_state.backend_warm = True
        except:
            pass

def fetch_count():
    try:
        return requests.get(f"{API_BASE}/documents/count", timeout=5).json().get("count", 0)
    except:
        return st.session_state.doc_count

def ask_llm(prompt):
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question": prompt, "history": [], "stream": False},
            timeout=300)
        return r.json().get("answer", "")
    except:
        return ""

def ask_chat(q):
    try:
        history = st.session_state.history if hasattr(st.session_state, 'history') and st.session_state.history else []
        r = requests.post(f"{API_BASE}/query",
            json={"question": q, "history": history, "stream": False},
            timeout=300)
        d = r.json()
        if "documents_count" in d:
            st.session_state.doc_count = d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ انتهت مهلة الاتصال — أعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال: {str(e)}"

def upload_file_to_backend(f):
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)}, timeout=30)
        d = r.json()
        if not r.ok or "error" in d:
            return False, d.get("error") or d.get("detail", "خطأ")
        return True, d.get("message", "تم الرفع")
    except Exception as e:
        return False, str(e)

def extract_text_from_file(f):
    """استخراج النص من ملف عبر API السيرفر"""
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)}, timeout=30)
        d = r.json()
        if not r.ok or "error" in d:
            return False, d.get("error") or d.get("detail", "خطأ")
        # السيرفر يعيد النص المستخرج
        return True, d.get("text", d.get("message", ""))
    except Exception as e:
        return False, str(e)

# ── Mindmap functions ──
def summarize_for_mindmap(text):
    prompt = f"""You must output ONLY a structured outline in Arabic. No explanations. No intro. Just the outline.

EXACT FORMAT:
Line 1: main title (max 5 Arabic words, NO ## prefix)
Then 3 to 5 branches, each starting with ##
Each ## branch: max 4 Arabic words
Each branch followed by 2-4 details starting with -
Each - detail: max 7 Arabic words

EXAMPLE:
التجارة الإلكترونية
## النمو والأرقام
- نمو 265٪ في المبيعات
- 4.88 تريليون بحلول 2021
## فوائد للشركات
- التميز عن المنافسين
- خفض التكاليف المباشرة

Now do the same for:
{text[:3000]}

OUTPUT:"""
    return ask_llm(prompt).strip()

def parse_mindmap_structure(structured_text):
    text = re.sub(r'(##[^#\n]+?)\s*-\s*', r'\1\n- ', structured_text)
    lines = []
    for raw in text.split('\n'):
        raw = raw.strip()
        if not raw:
            continue
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

    title = ' '.join(re.sub(r'^#+\s*','',lines[0]).strip().split()[:6])
    branches, current_branch, current_children = [], None, []
    
    for line in lines[1:]:
        if line.startswith('##') or (not line.startswith(('-','•','*')) and len(line)>3 and current_branch is None):
            if current_branch is not None:
                branches.append({
                    "topic": current_branch,
                    "children": [{"topic": c, "children": []} for c in current_children]
                })
            raw_b = re.sub(r'^#+\s*','',line).strip()
            current_branch = ' '.join(raw_b.split()[:5])
            current_children = []
        elif line.startswith(('-','•','*')):
            child = re.sub(r'^[-•*]\s*','',line).strip()
            child = ' '.join(child.split()[:8])
            if child and current_branch is not None:
                current_children.append(child)
    
    if current_branch is not None:
        branches.append({
            "topic": current_branch,
            "children": [{"topic": c, "children": []} for c in current_children]
        })

    if not branches:
        chunks = [re.sub(r'^[-•*##\s]+','',l).strip() for l in lines[1:] if len(l)>8][:7]
        branches = [{"topic": ' '.join(c.split()[:5]), "children": []} for c in chunks]

    return {"topic": title, "children": branches}

# ── دالة الخريطة الذهنية ──
def render_mindmap(data, theme="light"):
    json_str = json.dumps(data, ensure_ascii=False)
    
    svg_bg = "#f8f9fc" if theme == "light" else "#0f1117"
    node_bg0 = "#4f5ef0" if theme == "light" else "#5b6ef5"
    node_bg1 = "#ffffff" if theme == "light" else "#1e2238"
    node_bg2 = "#f0f2f8" if theme == "light" else "#13151f"
    txt_col = "#1a1d2e" if theme == "light" else "#e8eaf0"
    btn_bg = "#ffffff" if theme == "light" else "#1e2238"
    btn_brd = "#dde1f0" if theme == "light" else "#2e3248"
    btn_txt = "#6b7280" if theme == "light" else "#8b90a7"

    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{svg_bg};overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif;touch-action:pan-x pan-y;}}
#cv{{width:100%;height:580px;display:block;cursor:grab}}
#cv:active{{cursor:grabbing}}
.ctrl{{position:absolute;bottom:12px;left:12px;display:flex;gap:6px;z-index:99}}
.btn{{background:{btn_bg};border:1px solid {btn_brd};color:{btn_txt};padding:6px 13px;
      border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;
      transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.btn:hover{{border-color:#4f5ef0;color:#4f5ef0}}
#save-btn{{background:#4f5ef0;color:#fff;border-color:#4f5ef0}}
#save-btn:hover{{background:#3b4bd4;color:#fff}}
.wrap{{position:relative;width:100%;height:580px}}
@media (max-width: 500px) {{
  .btn{{padding:8px 14px;font-size:13px;}}
  #cv{{height:500px;}}
}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet"/>
</head><body>
<div class="wrap">
<svg id="cv"></svg>
<div class="ctrl">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳</button>
  <button class="btn" id="save-btn">💾 حفظ صورة</button>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA = {json_str};
const COLS = ['#4f5ef0','#16a34a','#d97706','#7c3aed','#0891b2','#db2777','#dc2626','#10b981','#6366f1','#f97316'];
const NODE0 = '{node_bg0}';
const NODE1 = '{node_bg1}';
const NODE2 = '{node_bg2}';
const TXTC = '{txt_col}';

function boxSize(text, depth) {{
  const isMobile = window.innerWidth < 500;
  const maxW = isMobile
    ? (depth===0 ? 85 : depth===1 ? 75 : 65)
    : (depth===0 ? 120 : depth===1 ? 105 : 95);
  const fs = isMobile
    ? (depth===0 ? 10 : depth===1 ? 9 : 8.5)
    : (depth===0 ? 13 : depth===1 ? 11.5 : 10.5);
  const lh = fs + 5;
  const words = text.split(' ');
  let line = '', lines = [];
  words.forEach(w => {{
    const t = line ? line + ' ' + w : w;
    if (t.length * fs * 0.52 > maxW && line) {{
      lines.push(line);
      line = w;
    }} else {{
      line = t;
    }}
  }});
  if (line) lines.push(line);
  if (lines.length === 0 && text) lines = [text];
  const W2 = Math.min(maxW, Math.max(50, lines.reduce((a, l) => Math.max(a, l.length * fs * 0.52), 0) + 16));
  const H2 = Math.max(lines.length * lh + 12, 32);
  return {{w: W2, h: H2, lines, fs, lh}};
}}

function drawText(g, box, x, y, depth) {{
  const {{lines, fs, lh, h}} = box;
  const startY = y - h/2 + (h - lines.length * lh)/2 + lh * 0.7;
  const fill = depth === 0 ? '#fff' : TXTC;
  lines.forEach((l, i) => {{
    g.append('text')
      .attr('x', x).attr('y', startY + i * lh)
      .attr('text-anchor', 'middle')
      .attr('font-size', fs + 'px')
      .attr('font-family', "'Tajawal','Segoe UI',sans-serif")
      .attr('font-weight', depth <= 1 ? '600' : '400')
      .attr('fill', fill)
      .attr('pointer-events', 'none')
      .text(l);
  }});
}}

function layoutTree(data, W, H) {{
  const isMobile = W < 500;
  const nodes = [];
  const links = [];

  const rootBox = boxSize(data.topic, 0);
  const root = {{
    id: 0, depth: 0, x: W / 2, y: H / 2,
    box: rootBox, color: NODE0, topic: data.topic
  }};
  nodes.push(root);

  const children = data.children || [];
  const n = children.length;
  if (n === 0) return {{nodes, links}};

  const base = Math.min(W, H);
  const R1 = isMobile
    ? base * (0.32 + Math.min(n * 0.035, 0.25))
    : base * (0.3 + Math.min(n * 0.02, 0.15));
  
  const angleStep = (2 * Math.PI) / n;
  const startAngle = -Math.PI / 2;
  
  children.forEach((child, ci) => {{
    const angle = startAngle + angleStep * ci;
    const cx = W / 2 + R1 * Math.cos(angle);
    const cy = H / 2 + R1 * Math.sin(angle);
    const col = COLS[ci % COLS.length];
    const cBox = boxSize(child.topic, 1);
    const cNode = {{
      id: nodes.length, depth: 1, x: cx, y: cy,
      box: cBox, color: col, stroke: col, topic: child.topic, parentId: 0
    }};
    nodes.push(cNode);
    links.push({{sx: W / 2, sy: H / 2, tx: cx, ty: cy, col: col + '88', w: 2}});

    const subs = child.children || [];
    const ns = subs.length;
    if (ns === 0) return;

    const R2 = isMobile
      ? base * (0.2 + Math.min(ns * 0.03, 0.12))
      : base * (0.18 + Math.min(ns * 0.02, 0.1));
    
    const subAngleStep = Math.min(Math.PI * 0.6, (Math.PI * 0.8) / Math.max(ns, 1));
    const subStartAngle = angle - subAngleStep / 2;
    
    subs.forEach((sub, si) => {{
      const subAngle = subStartAngle + (subAngleStep / Math.max(ns - 1, 1)) * si;
      const sx2 = cx + R2 * Math.cos(subAngle);
      const sy2 = cy + R2 * Math.sin(subAngle);
      const sBox = boxSize(sub.topic, 2);
      nodes.push({{
        id: nodes.length, depth: 2, x: sx2, y: sy2,
        box: sBox, color: NODE2, stroke: col + '99', topic: sub.topic
      }});
      links.push({{sx: cx, sy: cy, tx: sx2, ty: sy2, col: col + '55', w: 1.2}});
    }});
  }});

  return {{nodes, links}};
}}

let gAll;

function draw() {{
  const svgEl = document.getElementById('cv');
  const W = svgEl.clientWidth || 760;
  const H = svgEl.clientHeight || 580;
  const svg = d3.select('#cv').attr('viewBox', `0 0 ${{W}} ${{H}}`);
  svg.selectAll('*').remove();
  gAll = svg.append('g');

  const {{nodes, links}} = layoutTree(DATA, W, H);

  links.forEach(l => {{
    const mx = (l.sx + l.tx) / 2;
    gAll.append('path')
      .attr('d', `M${{l.sx}},${{l.sy}} Q${{mx}},${{l.sy}} ${{l.tx}},${{l.ty}}`)
      .attr('style', `fill:none;stroke:${{l.col}};stroke-width:${{l.w}};stroke-opacity:0.8`);
  }});

  nodes.forEach(n => {{
    const {{w, h}} = n.box;
    const rx = n.depth === 0 ? 14 : n.depth === 1 ? 10 : 8;

    if (n.depth <= 1) {{
      const shadowCol = n.depth === 0 ? COLS[0] : (n.stroke || COLS[0]);
      gAll.append('rect')
        .attr('x', n.x - w/2 + 2).attr('y', n.y - h/2 + 3)
        .attr('width', w).attr('height', h).attr('rx', rx)
        .attr('style', `fill:${{shadowCol}};opacity:0.12;stroke:none`);
    }}

    const fillCol = n.depth === 0 ? NODE0 : (n.depth === 1 ? NODE1 : NODE2);
    const strokeCol = n.stroke || n.color;
    const strokeW = n.depth === 0 ? 2.5 : (n.depth === 1 ? 1.8 : 1.2);
    const hoverFill = n.depth === 0 ? '#3b4bd4' : (n.depth === 1 ? '{BG3}' : '#1e2238');

    gAll.append('rect')
      .attr('x', n.x - w/2).attr('y', n.y - h/2)
      .attr('width', w).attr('height', h).attr('rx', rx)
      .attr('style', `fill:${{fillCol}};stroke:${{strokeCol}};stroke-width:${{strokeW}};cursor:pointer`)
      .on('mouseover', function() {{ this.style.fill = hoverFill; }})
      .on('mouseout', function() {{ this.style.fill = fillCol; }});

    drawText(gAll, n.box, n.x, n.y, n.depth);
  }});
}}

const svgSel = d3.select('#cv');
const zoomB = d3.zoom().scaleExtent([0.2, 4]).on('zoom', e => {{
  if (gAll) gAll.attr('transform', e.transform);
}});
svgSel.call(zoomB);

document.getElementById('zm').onclick = () => svgSel.transition().duration(220).call(zoomB.scaleBy, 0.7);
document.getElementById('zp').onclick = () => svgSel.transition().duration(220).call(zoomB.scaleBy, 1.4);
document.getElementById('zr').onclick = () => svgSel.transition().duration(300).call(zoomB.transform, d3.zoomIdentity);

document.getElementById('save-btn').onclick = function() {{
  const svgEl = document.getElementById('cv');
  let vx = 0, vy = 0, vw = svgEl.clientWidth || 760, vh = svgEl.clientHeight || 580;
  try {{
    const g = svgEl.querySelector('g');
    if (g) {{
      const bb = g.getBBox();
      const pad = 50;
      vx = bb.x - pad;
      vy = bb.y - pad;
      vw = bb.width + pad * 2;
      vh = bb.height + pad * 2;
    }}
  }} catch(e) {{}}

  const clone = svgEl.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
  clone.setAttribute('viewBox', `${{vx}} ${{vy}} ${{vw}} ${{vh}}`);
  clone.setAttribute('width', vw * 2);
  clone.setAttribute('height', vh * 2);
  clone.style.background = '{svg_bg}';

  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = "@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');";
  defs.appendChild(style);
  
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bg.setAttribute('x', vx);
  bg.setAttribute('y', vy);
  bg.setAttribute('width', vw);
  bg.setAttribute('height', vh);
  bg.setAttribute('fill', '{svg_bg}');
  clone.insertBefore(bg, clone.firstChild);
  clone.insertBefore(defs, clone.firstChild);

  clone.querySelectorAll('*').forEach(el => {{
    const sw = el.getAttribute('stroke-width');
    const so = el.getAttribute('stroke-opacity');
    if (sw || so) {{
      let s = el.getAttribute('style') || '';
      if (sw) {{ s += `;stroke-width:${{sw}}`; el.removeAttribute('stroke-width'); }}
      if (so) {{ s += `;stroke-opacity:${{so}}`; el.removeAttribute('stroke-opacity'); }}
      el.setAttribute('style', s.replace(/^;/, ''));
    }}
    el.removeAttribute('onclick');
    el.removeAttribute('onmouseover');
    el.removeAttribute('onmouseout');
  }});

  const serializer = new XMLSerializer();
  const src = serializer.serializeToString(clone);
  const blob = new Blob([src], {{type: 'image/svg+xml;charset=utf-8'}});
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.onload = function() {{
    const canvas = document.createElement('canvas');
    canvas.width = vw * 2;
    canvas.height = vh * 2;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '{svg_bg}';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    const a = document.createElement('a');
    a.download = 'mindmap_' + Date.now() + '.png';
    a.href = canvas.toDataURL('image/png', 1.0);
    a.click();
  }};
  img.onerror = function() {{
    URL.revokeObjectURL(url);
    const blob2 = new Blob([src], {{type: 'image/svg+xml'}});
    const url2 = URL.createObjectURL(blob2);
    const a = document.createElement('a');
    a.download = 'mindmap_' + Date.now() + '.svg';
    a.href = url2;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url2), 1000);
  }};
  img.src = url;
}};

let resizeTimeout;
window.addEventListener('resize', () => {{
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => draw(), 250);
}});

draw();
</script></body></html>"""
    components.html(html, height=600, scrolling=False)

# ══════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════
warmup_once()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"

col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.markdown(f'<div class="top-bar"><h2>🔬 مساعد البحث الذكي</h2><span class="badge {mc}">{mt}</span></div>', unsafe_allow_html=True)
with col_h2:
    theme_label = "🌙" if THEME == "light" else "☀️"
    if st.button(theme_label, key="theme_btn", help="تبديل الثيم"):
        st.session_state.theme = "dark" if THEME == "light" else "light"
        st.rerun()

# ── MODE TABS ──
tab1, tab2 = st.tabs(["💬 دردشة ذكية", "🗺️ خريطة ذهنية"])

# ══════════════════════════════════════════
# TAB 1: CHAT
# ══════════════════════════════════════════
with tab1:
    # رفع الملفات في الشريط الجانبي للدردشة
    with st.sidebar:
        st.markdown("### 📁 رفع للدردشة")
        uploaded_chat = st.file_uploader("PDF أو DOCX", type=["pdf", "docx"], key="chat_upload", label_visibility="collapsed")
        if uploaded_chat:
            st.markdown(f'<div class="upload-info">📄 {uploaded_chat.name}</div>', unsafe_allow_html=True)
            if st.button("⬆️ رفع للسيرفر", key="upload_chat_btn", use_container_width=True):
                with st.spinner("جارٍ الرفع..."):
                    ok, msg = upload_file_to_backend(uploaded_chat)
                if ok:
                    st.success(f"✅ {msg}")
                    time.sleep(1)
                    st.session_state.doc_count = fetch_count()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
    
    # عرض الدردشة
    if not st.session_state.history:
        st.markdown(f"""<div style="text-align:center;padding:50px 0;color:{TEXT2}">
        <div style="font-size:44px;opacity:.2;margin-bottom:14px">◎</div>
        <p style="font-size:15px;font-weight:500">اسأل أي سؤال للبدء</p>
        </div>""", unsafe_allow_html=True)
    else:
        for turn in st.session_state.history:
            if turn["role"] == "user":
                st.markdown(f'<div class="msg-label" style="text-align:right">أنت</div>'
                           f'<div class="msg-user">{turn["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-label">المساعد</div>'
                           f'<div class="msg-ai">{turn["content"]}</div>', unsafe_allow_html=True)
    
    with st.form("cf", clear_on_submit=True):
        q = st.text_area("س", placeholder="اكتب سؤالك هنا...", label_visibility="collapsed", height=85)
        sub = st.form_submit_button("إرسال ➤", use_container_width=True)
    
    if sub and q.strip():
        with st.spinner("🤔 جاري التفكير..."):
            ans = ask_chat(q.strip())
        now = datetime.now().strftime("%H:%M")
        st.session_state.history.append({"role": "user", "content": q.strip(), "time": now})
        st.session_state.history.append({"role": "assistant", "content": ans, "time": now})
        st.rerun()

# ══════════════════════════════════════════
# TAB 2: MINDMAP
# ══════════════════════════════════════════
with tab2:
    # رفع الملفات في الشريط الجانبي للخريطة
    with st.sidebar:
        st.markdown("### 📁 رفع للخريطة")
        uploaded_mm = st.file_uploader("PDF أو DOCX", type=["pdf", "docx"], key="mm_upload", label_visibility="collapsed")
        if uploaded_mm:
            st.markdown(f'<div class="upload-info">📄 {uploaded_mm.name}</div>', unsafe_allow_html=True)
            if st.button("📖 استخراج النص وتحويله لخريطة", key="extract_mm_btn", use_container_width=True):
                with st.spinner("جاري استخراج النص من الملف..."):
                    ok, result = extract_text_from_file(uploaded_mm)
                    if ok and result:
                        st.session_state.mm_raw_text = result[:5000]
                        st.success(f"✅ تم استخراج {len(result[:5000])} حرف")
                        time.sleep(1)
                        # نذهب مباشرة لتحليل النص
                        with st.spinner("🧠 جاري تحليل النص وبناء الخريطة..."):
                            summary = summarize_for_mindmap(result[:5000])
                            if summary:
                                st.session_state.mm_summary = summary
                                st.session_state.mm_data = parse_mindmap_structure(summary)
                                st.session_state.mm_step = 1
                            else:
                                st.session_state.mm_summary = result[:5000]
                                st.session_state.mm_data = parse_mindmap_structure(result[:5000])
                                st.session_state.mm_step = 1
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
    
    if st.session_state.mm_step == 0:
        st.markdown(f"""<div class="mm-box">
        <p>📝 <b style="color:{TEXT}">كيف يعمل:</b><br>
        ✍️ الصق نصاً في المربع أدناه، أو 📁 ارفع ملف PDF/DOCX من الشريط الجانبي</p>
        </div>""", unsafe_allow_html=True)
        
        with st.form("mmf", clear_on_submit=False):
            raw = st.text_area("📝 النص", 
                               placeholder="الصق نصك هنا...",
                               label_visibility="collapsed", 
                               height=200, 
                               value=st.session_state.mm_raw_text)
            go = st.form_submit_button("🧠 تحليل وبناء الخريطة", use_container_width=True)
        
        if go and raw.strip():
            st.session_state.mm_raw_text = raw.strip()
            with st.spinner("🧠 جاري تحليل النص وبناء الخريطة..."):
                summary = summarize_for_mindmap(raw.strip())
                if summary:
                    st.session_state.mm_summary = summary
                    st.session_state.mm_data = parse_mindmap_structure(summary)
                else:
                    st.session_state.mm_summary = raw.strip()
                    st.session_state.mm_data = parse_mindmap_structure(raw.strip())
                st.session_state.mm_step = 1
            st.rerun()
    
    elif st.session_state.mm_step == 1:
        # عرض الملخص
        with st.expander("📋 الملخص الهيكلي", expanded=False):
            st.markdown(f'<div class="summary-box">{st.session_state.mm_summary.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
        
        # عرض الخريطة
        st.markdown(f'<div class="step-label">🗺️ الخريطة الذهنية</div>', unsafe_allow_html=True)
        if st.session_state.mm_data:
            render_mindmap(st.session_state.mm_data, theme=THEME)
        
        # أزرار التحكم
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 نص جديد", use_container_width=True):
                st.session_state.mm_step = 0
                st.session_state.mm_raw_text = ""
                st.session_state.mm_summary = ""
                st.session_state.mm_data = None
                st.rerun()
        with col2:
            if st.button("✏️ تعديل النص", use_container_width=True):
                st.session_state.mm_step = 0
                st.rerun()
        with col3:
            if st.button("🔁 إعادة التلخيص", use_container_width=True):
                with st.spinner("🔄 جاري إعادة التحليل..."):
                    summary = summarize_for_mindmap(st.session_state.mm_raw_text)
                    if summary:
                        st.session_state.mm_summary = summary
                        st.session_state.mm_data = parse_mindmap_structure(summary)
                    st.rerun()
