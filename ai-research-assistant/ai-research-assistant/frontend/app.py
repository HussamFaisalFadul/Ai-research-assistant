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
.top-bar{display:flex;align-items:center;justify-content:space-between;padding:12px 0 16px;border-bottom:1px solid #2e3248;margin-bottom:16px}
.top-bar h2{margin:0;font-size:18px;font-weight:700;color:#e8eaf0}
.badge{font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid #2e3248;color:#8b90a7}
.badge.rag{border-color:#22c55e;color:#22c55e;background:rgba(34,197,94,.1)}
.msg-user{background:#23273a;border:1px solid #2e3248;border-radius:12px 3px 12px 12px;padding:10px 14px;margin:6px 0 6px 40px;font-size:14px;line-height:1.7;color:#e8eaf0}
.msg-ai{background:#1e2238;border:1px solid #2e3248;border-radius:3px 12px 12px 12px;padding:10px 14px;margin:4px 40px 2px 0;font-size:14px;line-height:1.7;color:#e8eaf0}
.msg-label{font-size:11px;color:#8b90a7;margin-bottom:2px}
.success-box{background:rgba(34,197,94,.08);border:1px solid #22c55e;border-radius:8px;padding:10px 14px;color:#22c55e;font-size:13px}
.error-box{background:rgba(239,68,68,.08);border:1px solid #ef4444;border-radius:8px;padding:10px 14px;color:#ef4444;font-size:13px}
.upload-info{background:#1a1d27;border:1px solid #2e3248;border-radius:8px;padding:8px 12px;font-size:12px;color:#8b90a7;margin-bottom:8px}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton{display:none}
div[data-testid="stToolbar"]{display:none}
.stTextArea textarea{background:#23273a!important;color:#e8eaf0!important;border:1px solid #2e3248!important;border-radius:10px!important;font-family:'Tajawal',sans-serif!important;font-size:14px!important;direction:rtl!important}
.stTextArea textarea:focus{border-color:#5b6ef5!important}
.stButton>button{background:#5b6ef5!important;color:#fff!important;border:none!important;border-radius:8px!important;font-family:'Tajawal',sans-serif!important;font-weight:500!important;width:100%}
.stButton>button:hover{background:#3d4fd4!important}
button[kind="secondary"]{background:transparent!important;color:#8b90a7!important;border:1px solid #2e3248!important}
button[kind="secondary"]:hover{border-color:#5b6ef5!important;color:#e8eaf0!important}
</style>
""", unsafe_allow_html=True)

# ── session state ──
for k,v in {"history":[],"doc_count":0,"show_mindmap_idx":-1}.items():
    if k not in st.session_state: st.session_state[k]=v


# ── helpers ──
def warmup():
    try: requests.get(f"{API_BASE.replace('/api','')}/health", timeout=8)
    except: pass

def fetch_count():
    try: return requests.get(f"{API_BASE}/documents/count",timeout=5).json().get("count",0)
    except: return st.session_state.doc_count

def ask(q):
    try:
        r = requests.post(f"{API_BASE}/query",
            json={"question":q,"history":st.session_state.history,"stream":False},
            timeout=300)
        d = r.json()
        if "documents_count" in d: st.session_state.doc_count=d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ الموديل يعمل على CPU — انتظر قليلاً وأعد المحاولة."
    except Exception as e:
        return f"❌ فشل الاتصال: {str(e)}"

def upload_file(f):
    try:
        r = requests.post(f"{API_BASE}/upload",
            files={"file":(f.name,f.getvalue(),f.type)}, timeout=30)
        d = r.json()
        if not r.ok or "error" in d: return False, d.get("error") or d.get("detail","خطأ")
        return True, d.get("message","تم الرفع")
    except Exception as e: return False, str(e)


# ── text → mindmap JSON (Python side, no LLM needed) ──
def text_to_mindmap(text: str) -> dict:
    """
    يستخرج النقاط من النص ويبني هيكل الخريطة الذهنية.
    يعمل بالكامل في Python بدون استدعاء الموديل.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # العنوان الرئيسي = أول جملة مختصرة
    title = lines[0][:50] if lines else "الموضوع"

    branches = []
    current_branch = None
    current_children = []

    for line in lines[1:]:
        # أزل علامات القوائم
        clean = re.sub(r'^[\*\-\•\d\.\)\:]+\s*', '', line).strip()
        if not clean or len(clean) < 4:
            continue

        # هل هو عنوان فرعي؟ (قصير نسبياً أو ينتهي بـ : أو يبدأ بأرقام)
        is_header = (
            len(clean) < 45 and
            (line.startswith('*') or line.startswith('-') or
             re.match(r'^\d', line) or clean.endswith(':') or
             len(current_children) >= 4)
        )

        if is_header and current_branch is None:
            current_branch = clean.rstrip(':')
            current_children = []
        elif is_header and current_branch:
            # احفظ الفرع الحالي وابدأ جديداً
            if current_children:
                branches.append({
                    "topic": current_branch[:50],
                    "children": [{"topic": c[:55], "children": []} for c in current_children[:5]]
                })
            else:
                branches.append({"topic": current_branch[:50], "children": []})
            current_branch = clean.rstrip(':')
            current_children = []
        else:
            if current_branch:
                current_children.append(clean[:55])
            else:
                # بدون فرع محدد — أضفه كفرع مباشر
                branches.append({"topic": clean[:50], "children": []})

    # الفرع الأخير
    if current_branch:
        branches.append({
            "topic": current_branch[:50],
            "children": [{"topic": c[:55], "children": []} for c in current_children[:5]]
        })

    # إذا ما في فروع كافية، قسّم النص تلقائياً
    if len(branches) < 2:
        chunks = [l.strip() for l in text.replace('،','\n').replace('.','\n').split('\n')
                  if len(l.strip()) > 15][:10]
        branches = [{"topic": c[:55], "children": []} for c in chunks]

    return {"topic": title, "children": branches[:8]}


# ── render mindmap (D3 radial tree) ──
def render_mindmap(data: dict):
    json_str = json.dumps(data, ensure_ascii=False)
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f1117;overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif}}
svg{{width:100%;height:580px;display:block;cursor:grab}}
svg:active{{cursor:grabbing}}
.link{{fill:none;stroke:#2e3248;stroke-width:1.8px;stroke-opacity:.8}}
.link.l1{{stroke:#3d4fd4;stroke-width:2.5px}}
.node-circle{{cursor:pointer;transition:all .25s}}
.root-c{{fill:#5b6ef5;stroke:#7b8ef5;stroke-width:2}}
.l1-c{{fill:#23273a;stroke:#5b6ef5;stroke-width:1.5}}
.l2-c{{fill:#1a1d27;stroke:#3d4fd4;stroke-width:1}}
.node-text{{font-family:'Tajawal','Segoe UI',sans-serif;pointer-events:none;fill:#e8eaf0}}
.root-t{{font-size:13px;font-weight:700;fill:#fff}}
.l1-t{{font-size:11.5px;font-weight:500;fill:#c8cadc}}
.l2-t{{font-size:10.5px;fill:#9093ab}}
.controls{{position:fixed;bottom:12px;left:12px;display:flex;gap:6px;z-index:10}}
.btn{{background:#1e2238;border:1px solid #2e3248;color:#8b90a7;padding:6px 12px;
      border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;transition:all .2s}}
.btn:hover{{border-color:#5b6ef5;color:#e8eaf0}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet"/>
</head><body>
<svg id="svg"><g id="root-g"></g></svg>
<div class="controls">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳ إعادة</button>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA = {json_str};
const W = window.innerWidth || 700;
const H = 580;
let tx=W/2, ty=H/2, sc=1;

const svg = d3.select('#svg').attr('viewBox',`0 0 ${{W}} ${{H}}`);
const gMain = d3.select('#root-g');

// zoom + drag
const zoomed = (e) => {{ tx=e.transform.x; ty=e.transform.y; sc=e.transform.k; gMain.attr('transform',`translate(${{tx}},${{ty}}) scale(${{sc}})`); }};
const zoomBeh = d3.zoom().scaleExtent([0.2,3]).on('zoom', zoomed);
svg.call(zoomBeh);
svg.call(zoomBeh.transform, d3.zoomIdentity.translate(W/2, H/2));

document.getElementById('zm').onclick = () => svg.transition().call(zoomBeh.scaleBy, 0.75);
document.getElementById('zp').onclick = () => svg.transition().call(zoomBeh.scaleBy, 1.33);
document.getElementById('zr').onclick = () => svg.transition().duration(400).call(zoomBeh.transform, d3.zoomIdentity.translate(W/2,H/2));

function wrapText(el, text, maxW) {{
  const words = text.split(' ');
  let line = '', lines = [];
  words.forEach(w => {{
    const test = line ? line+' '+w : w;
    if (test.length > maxW && line) {{ lines.push(line); line=w; }}
    else line = test;
  }});
  if(line) lines.push(line);
  lines.forEach((l,i) => {{
    el.append('tspan').attr('x',0).attr('dy', i===0 ? 0 : '1.2em').text(l);
  }});
  return lines.length;
}}

function draw() {{
  gMain.selectAll('*').remove();
  const root = d3.hierarchy(DATA);
  const n = root.children ? root.children.length : 1;

  // شجرة شعاعية
  const radius = Math.min(W, H) * 0.42;
  d3.tree().size([2*Math.PI, radius]).separation((a,b)=>((a.parent===b.parent?1:2)/a.depth))(root);

  // روابط
  gMain.selectAll('.link')
    .data(root.links()).enter().append('path').attr('class', d=>`link ${{d.source.depth===0?'l1':''}}`)
    .attr('d', d3.linkRadial().angle(d=>d.x).radius(d=>d.y));

  // عقد
  const node = gMain.selectAll('.node')
    .data(root.descendants()).enter().append('g')
    .attr('transform', d=>`rotate(${{d.x*180/Math.PI-90}}) translate(${{d.y}},0)`);

  // دوائر
  node.append('circle').attr('class', d=>d.depth===0?'node-circle root-c':d.depth===1?'node-circle l1-c':'node-circle l2-c')
    .attr('r', d=>d.depth===0?30:d.depth===1?18:12)
    .on('mouseover', function(e,d){{ if(d.depth>0) d3.select(this).attr('fill','#5b6ef5'); }})
    .on('mouseout',  function(e,d){{ if(d.depth===1) d3.select(this).attr('fill','#23273a'); else if(d.depth===2) d3.select(this).attr('fill','#1a1d27'); }});

  // نصوص
  node.append('text')
    .attr('class', d=>d.depth===0?'node-text root-t':d.depth===1?'node-text l1-t':'node-text l2-t')
    .attr('transform', d=>{{
      const angle = d.x*180/Math.PI - 90;
      const flip  = angle > 0 && angle < 180;
      return `rotate(${{-(angle)}})`
    }})
    .attr('text-anchor','middle')
    .attr('dy', d=>d.depth===0?'0.35em':'-0.1em')
    .each(function(d) {{ wrapText(d3.select(this), d.data.topic, d.depth===0?8:d.depth===1?10:12); }});
}}

draw();
window.addEventListener('resize', draw);
</script></body></html>"""
    components.html(html, height=590, scrolling=False)


# ── header ──
warmup()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"
st.markdown(f'<div class="top-bar"><h2>🔬 مساعد البحث الذكي</h2><span class="badge {mc}">{mt}</span></div>', unsafe_allow_html=True)

# ── sidebar ──
with st.sidebar:
    st.markdown("### 📁 رفع الوثائق")
    uploaded = st.file_uploader("PDF أو DOCX", type=["pdf","docx"], label_visibility="collapsed")
    if uploaded:
        st.markdown(f'<div class="upload-info">📄 {uploaded.name}</div>', unsafe_allow_html=True)
        if st.button("⬆️ رفع الملف", key="ubtn"):
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
    st.markdown("### ⚙️ الإعدادات")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🗑️ مسح",key="clr",type="secondary"):
            st.session_state.history=[]; st.session_state.show_mindmap_idx=-1; st.rerun()
    with c2:
        if st.button("🔄 تحديث",key="ref",type="secondary"):
            st.session_state.doc_count=fetch_count(); st.rerun()
    st.divider()
    st.markdown(f"""<div style="font-size:12px;color:#8b90a7;line-height:1.8">
    <b style="color:#e8eaf0">الوضع:</b><br>
    {'🟢 RAG' if st.session_state.doc_count>0 else '🔵 Chat'}<br><br>
    <b style="color:#e8eaf0">وثائق:</b> {st.session_state.doc_count}
    </div>""", unsafe_allow_html=True)

# ── chat ──
if not st.session_state.history:
    st.markdown("""<div style="text-align:center;padding:50px 0;color:#8b90a7">
    <div style="font-size:42px;opacity:.25;margin-bottom:14px">◎</div>
    <p style="font-size:14px">اسأل أي سؤال للبدء</p>
    <p style="font-size:12px;opacity:.5;margin-top:6px">ارفع ملفاً لتفعيل وضع RAG</p>
    </div>""", unsafe_allow_html=True)
else:
    ai_idx = 0
    for i, turn in enumerate(st.session_state.history):
        if turn["role"] == "user":
            st.markdown(f'<div class="msg-label" style="text-align:right">أنت</div><div class="msg-user">{turn["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="msg-label">المساعد</div><div class="msg-ai">{turn["content"]}</div>', unsafe_allow_html=True)

            # زر الخريطة
            if st.button("🗺️ خريطة ذهنية", key=f"mm_{i}", type="secondary"):
                if st.session_state.show_mindmap_idx == i:
                    st.session_state.show_mindmap_idx = -1
                else:
                    st.session_state.show_mindmap_idx = i
                st.rerun()

            # عرض الخريطة
            if st.session_state.show_mindmap_idx == i:
                mm_data = text_to_mindmap(turn["content"])
                render_mindmap(mm_data)

            ai_idx += 1

# ── input ──
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
with st.form("cf", clear_on_submit=True):
    q = st.text_area("س", placeholder="اكتب سؤالك هنا...", label_visibility="collapsed", height=80)
    sub = st.form_submit_button("إرسال ➤", use_container_width=True)

if sub and q.strip():
    with st.spinner("جارٍ التفكير... ⏳"):
        ans = ask(q.strip())
    st.session_state.history.append({"role":"user","content":q.strip()})
    st.session_state.history.append({"role":"assistant","content":ans})
    if len(st.session_state.history) > 20:
        st.session_state.history = st.session_state.history[-20:]
    st.rerun()
