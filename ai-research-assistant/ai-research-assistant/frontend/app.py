"""
app.py — الواجهة الرئيسية
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import time
import concurrent.futures
from datetime import datetime

from utils import (
    get_theme_colors, warmup_once, fetch_count,
    ask_chat, ask_llm, upload_file, extract_text_from_uploaded,
    load_history, save_history, load_sessions, save_sessions,
    summarize_for_mindmap, parse_mindmap_structure,
)

st.set_page_config(page_title="مساعد البحث الذكي", page_icon="🔬", layout="centered")

# ── session state ──
_defaults = {
    "history": load_history(),
    "doc_count": 0,
    "mode": "chat",
    "mm_raw_text": "",
    "mm_summary": "",
    "mm_data": None,
    "mm_step": 0,          # 0=input  1=result
    "theme": "light",
    "backend_warm": False,
    "mm_extracted": "",    # النص المستخرج من الملف
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

C = get_theme_colors(st.session_state.theme)   # اختصار للألوان


# ══════════════════════════════════════════
# CSS
# ══════════════════════════════════════════
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
.badge{{font-size:11px;padding:3px 10px;border-radius:20px;
  border:1px solid {C['BORDER']};color:{C['TEXT2']}}}
.badge.rag{{border-color:#22c55e;color:#22c55e;background:rgba(34,197,94,.1)}}

.msg-user{{background:{C['MSG_USER']};border:1px solid {C['BORDER']};
  border-radius:12px 3px 12px 12px;padding:11px 15px;
  margin:6px 0 6px 40px;font-size:14px;line-height:1.75;color:{C['TEXT']}}}
.msg-ai{{background:{C['MSG_AI']};border:1px solid {C['BORDER']};
  box-shadow:0 2px 8px {C['SHADOW']};border-radius:3px 12px 12px 12px;
  padding:11px 15px;margin:4px 40px 4px 0;font-size:14px;line-height:1.75;color:{C['TEXT']}}}
.msg-label{{font-size:11px;color:{C['TEXT2']};margin-bottom:3px;font-weight:500}}
.msg-time{{font-size:10px;color:{C['TEXT2']};margin-top:3px;opacity:.6}}

/* extracted text box */
.extracted-box{{background:{C['BG3']};border:2px dashed {C['ACCENT']};
  border-radius:12px;padding:14px 16px;font-size:13px;line-height:1.8;
  color:{C['TEXT']};margin:10px 0;max-height:180px;overflow-y:auto;
  white-space:pre-wrap;word-break:break-word}}
.extract-label{{font-size:12px;color:{C['ACCENT']};font-weight:600;
  margin-bottom:6px;display:flex;align-items:center;gap:6px}}

.mm-box{{background:{C['BG3']};border:1px solid {C['BORDER']};
  border-radius:12px;padding:14px;margin-bottom:10px}}
.mm-box p{{font-size:13px;color:{C['TEXT2']};margin:0;line-height:1.6}}
.step-label{{font-size:12px;color:{C['ACCENT']};font-weight:600;
  margin-bottom:6px;margin-top:12px}}
.summary-box{{background:{C['BG3']};border:1px solid {C['BORDER']};
  border-radius:10px;padding:12px 16px;font-size:13px;
  line-height:1.8;color:{C['TEXT']};margin-bottom:10px}}

.success-box{{background:rgba(34,197,94,.08);border:1px solid #22c55e;
  border-radius:8px;padding:9px 14px;color:#16a34a;font-size:13px}}
.error-box{{background:rgba(239,68,68,.08);border:1px solid #ef4444;
  border-radius:8px;padding:9px 14px;color:#dc2626;font-size:13px}}
.upload-info{{background:{C['BG3']};border:1px solid {C['BORDER']};
  border-radius:8px;padding:7px 12px;font-size:12px;color:{C['TEXT2']};margin-bottom:6px}}
.info-tip{{background:{C['BG3']};border-right:3px solid {C['ACCENT']};
  border-radius:0 8px 8px 0;padding:8px 12px;font-size:12px;
  color:{C['TEXT2']};margin:8px 0;line-height:1.6}}

.stTextArea textarea{{background:{C['BG3']}!important;color:{C['TEXT']}!important;
  border:1px solid {C['BORDER']}!important;border-radius:10px!important;
  font-family:'Tajawal',sans-serif!important;font-size:14px!important;direction:rtl!important}}
.stTextArea textarea:focus{{border-color:{C['ACCENT']}!important;
  box-shadow:0 0 0 2px {C['ACCENT']}22!important}}
.stButton>button{{background:{C['ACCENT']}!important;color:#fff!important;
  border:none!important;border-radius:8px!important;
  font-family:'Tajawal',sans-serif!important;font-weight:600!important;
  width:100%;transition:all .2s!important}}
.stButton>button:hover{{background:{C['ACCENT2']}!important;
  transform:translateY(-1px)!important}}
button[kind="secondary"]{{background:{C['BG3']}!important;
  color:{C['TEXT2']}!important;border:1px solid {C['BORDER']}!important}}
button[kind="secondary"]:hover{{border-color:{C['ACCENT']}!important;
  color:{C['TEXT']}!important}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# Mindmap HTML renderer
# ══════════════════════════════════════════
def render_mindmap(data: dict):
    C2 = get_theme_colors(st.session_state.theme)
    svg_bg   = C2["SVG_BG"]
    node_bg0 = C2["NODE0"]
    node_bg1 = C2["NODE1"]
    node_bg2 = C2["NODE2"]
    txt_col  = C2["TXT_COL"]
    btn_bg   = C2["BTN_BG"]
    btn_brd  = C2["BTN_BRD"]
    btn_txt  = C2["BTN_TXT"]
    json_str = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{svg_bg};overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif}}
#cv{{width:100%;height:560px;display:block;cursor:grab}}
#cv:active{{cursor:grabbing}}
.ctrl{{position:absolute;bottom:10px;left:10px;display:flex;gap:5px;z-index:99}}
.btn{{background:{btn_bg};border:1px solid {btn_brd};color:{btn_txt};
  padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px;
  font-family:inherit;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.btn:hover{{border-color:#4f5ef0;color:#4f5ef0}}
#save-btn{{background:#4f5ef0;color:#fff;border-color:#4f5ef0}}
#save-btn:hover{{background:#3b4bd4}}
.wrap{{position:relative;width:100%;height:560px}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet"/>
</head><body>
<div class="wrap">
  <svg id="cv"></svg>
  <div class="ctrl">
    <button class="btn" id="zm">−</button>
    <button class="btn" id="zp">+</button>
    <button class="btn" id="zr">⟳</button>
    <button class="btn" id="save-btn">💾 حفظ PNG</button>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA  = {json_str};
const COLS  = ['#4f5ef0','#16a34a','#d97706','#7c3aed','#0891b2','#db2777','#dc2626','#10b981'];
const NODE0 = '{node_bg0}';
const NODE1 = '{node_bg1}';
const NODE2 = '{node_bg2}';
const TXTC  = '{txt_col}';
const SVGBG = '{svg_bg}';

/* حجم المستطيل */
function boxSize(text, depth) {{
  const maxW = depth===0?125:depth===1?110:100;
  const fs   = depth===0?13:depth===1?11.5:10.5;
  const lh   = fs+5.5;
  const words= text.split(' ');
  let line='', lines=[];
  words.forEach(w=>{{
    const t=line?line+' '+w:w;
    if(t.length*fs*0.52>maxW&&line){{lines.push(line);line=w;}}
    else line=t;
  }});
  if(line)lines.push(line);
  if(!lines.length)lines=[text];
  const W2=Math.min(maxW,Math.max(55,lines.reduce((a,l)=>Math.max(a,l.length*fs*0.52),0)+18));
  return {{w:W2,h:Math.max(lines.length*lh+14,32),lines,fs,lh}};
}}

/* رسم النص */
function drawText(g,box,x,y,depth){{
  const {{lines,fs,lh,h}}=box;
  const startY=y-h/2+(h-lines.length*lh)/2+lh*0.72;
  lines.forEach((l,i)=>
    g.append('text')
      .attr('x',x).attr('y',startY+i*lh)
      .attr('text-anchor','middle')
      .attr('font-size',fs+'px')
      .attr('font-family',"'Tajawal','Segoe UI',sans-serif")
      .attr('font-weight',depth<=1?'600':'400')
      .attr('fill',depth===0?'#fff':TXTC)
      .attr('pointer-events','none')
      .text(l)
  );
}}

/* توزيع العقد */
function layoutTree(data,W,H){{
  const nodes=[],links=[];
  const rootBox=boxSize(data.topic,0);
  nodes.push({{id:0,depth:0,x:W/2,y:H/2,box:rootBox,color:NODE0,topic:data.topic}});
  const children=data.children||[];
  const n=children.length; if(!n)return{{nodes,links}};
  const R1=Math.min(W,H)*0.33;
  children.forEach((child,ci)=>{{
    const angle=(2*Math.PI*ci/n)-Math.PI/2;
    const cx=W/2+R1*Math.cos(angle), cy=H/2+R1*Math.sin(angle);
    const col=COLS[ci%COLS.length];
    const cBox=boxSize(child.topic,1);
    const cNode={{id:nodes.length,depth:1,x:cx,y:cy,box:cBox,color:col,stroke:col,topic:child.topic}};
    nodes.push(cNode);
    links.push({{sx:W/2,sy:H/2,tx:cx,ty:cy,col:col+'88',w:2}});
    const subs=child.children||[]; if(!subs.length)return;
    const R2=Math.min(W,H)*0.21;
    const spread=Math.min(Math.PI*0.65,subs.length*0.45);
    subs.forEach((sub,si)=>{{
      const sa=angle-spread/2+spread*(si/Math.max(subs.length-1,1));
      const sx2=cx+R2*Math.cos(sa), sy2=cy+R2*Math.sin(sa);
      nodes.push({{id:nodes.length,depth:2,x:sx2,y:sy2,
        box:boxSize(sub.topic,2),color:NODE2,stroke:col+'99',topic:sub.topic}});
      links.push({{sx:cx,sy:cy,tx:sx2,ty:sy2,col:col+'55',w:1.2}});
    }});
  }});
  return{{nodes,links}};
}}

let gAll;
function draw(){{
  const svgEl=document.getElementById('cv');
  const W=svgEl.clientWidth||760, H=svgEl.clientHeight||560;
  const svg=d3.select('#cv').attr('viewBox',`0 0 ${{W}} ${{H}}`);
  svg.selectAll('*').remove();
  gAll=svg.append('g');
  const {{nodes,links}}=layoutTree(DATA,W,H);

  /* روابط */
  links.forEach(l=>{{
    const mx=(l.sx+l.tx)/2;
    gAll.append('path')
      .attr('d',`M${{l.sx}},${{l.sy}} Q${{mx}},${{l.sy}} ${{l.tx}},${{l.ty}}`)
      .attr('style',`fill:none;stroke:${{l.col}};stroke-width:${{l.w}};stroke-opacity:0.8`);
  }});

  /* عقد */
  nodes.forEach(n=>{{
    const {{w,h}}=n.box;
    const rx=n.depth===0?14:n.depth===1?10:8;
    /* ظل */
    if(n.depth<=1){{
      const sc=n.depth===0?COLS[0]:n.stroke||COLS[0];
      gAll.append('rect')
        .attr('x',n.x-w/2+2).attr('y',n.y-h/2+3)
        .attr('width',w).attr('height',h).attr('rx',rx)
        .attr('style',`fill:${{sc}};opacity:0.12;stroke:none`);
    }}
    /* مستطيل */
    const fill=n.depth===0?NODE0:n.depth===1?NODE1:NODE2;
    const sc=n.stroke||n.color;
    const sw=n.depth===0?2.5:n.depth===1?1.8:1.2;
    const hov=n.depth===0?'#3b4bd4':n.depth===1?'${{NODE2}}':'#0f1117';
    gAll.append('rect')
      .attr('x',n.x-w/2).attr('y',n.y-h/2)
      .attr('width',w).attr('height',h).attr('rx',rx)
      .attr('style',`fill:${{fill}};stroke:${{sc}};stroke-width:${{sw}};cursor:pointer`)
      .on('mouseover',function(){{this.style.fill=hov;}})
      .on('mouseout', function(){{this.style.fill=fill;}});
    drawText(gAll,n.box,n.x,n.y,n.depth);
  }});
}}

/* zoom */
const sel=d3.select('#cv');
const zB=d3.zoom().scaleExtent([0.2,4]).on('zoom',e=>gAll&&gAll.attr('transform',e.transform));
sel.call(zB);
document.getElementById('zm').onclick=()=>sel.transition().duration(220).call(zB.scaleBy,.72);
document.getElementById('zp').onclick=()=>sel.transition().duration(220).call(zB.scaleBy,1.38);
document.getElementById('zr').onclick=()=>sel.transition().duration(300).call(zB.transform,d3.zoomIdentity);

/* ── حفظ PNG ── */
document.getElementById('save-btn').onclick=function(){{
  const svgEl=document.getElementById('cv');
  /* حجم حقيقي عبر getBBox */
  let vx=0,vy=0,vw=760,vh=560;
  try{{
    const g=svgEl.querySelector('g');
    if(g){{const bb=g.getBBox(),p=50;vx=bb.x-p;vy=bb.y-p;vw=bb.width+p*2;vh=bb.height+p*2;}}
  }}catch(e){{}}

  const clone=svgEl.cloneNode(true);
  clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
  clone.setAttribute('viewBox',`${{vx}} ${{vy}} ${{vw}} ${{vh}}`);
  clone.setAttribute('width',vw*2); clone.setAttribute('height',vh*2);

  /* خلفية + defs */
  const ns='http://www.w3.org/2000/svg';
  const defs=document.createElementNS(ns,'defs');
  const sty=document.createElementNS(ns,'style');
  sty.textContent="@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');";
  defs.appendChild(sty);
  const bg=document.createElementNS(ns,'rect');
  bg.setAttribute('x',vx);bg.setAttribute('y',vy);
  bg.setAttribute('width',vw);bg.setAttribute('height',vh);
  bg.setAttribute('fill',SVGBG);
  clone.insertBefore(bg,clone.firstChild);
  clone.insertBefore(defs,clone.firstChild);

  /* تنظيف attributes غير صالحة */
  clone.querySelectorAll('*').forEach(el=>{{
    ['stroke-width','stroke-opacity'].forEach(attr=>{{
      const val=el.getAttribute(attr);
      if(val){{
        let s=el.getAttribute('style')||'';
        s+=`;${{attr}}:${{val}}`;
        el.setAttribute('style',s.replace(/^;/,''));
        el.removeAttribute(attr);
      }}
    }});
    el.removeAttribute('onclick');
    el.removeAttribute('onmouseover');
    el.removeAttribute('onmouseout');
  }});

  const src=new XMLSerializer().serializeToString(clone);
  const url=URL.createObjectURL(new Blob([src],{{type:'image/svg+xml;charset=utf-8'}}));
  const img=new Image();
  img.onload=function(){{
    const cv=document.createElement('canvas');
    cv.width=vw*2; cv.height=vh*2;
    const ctx=cv.getContext('2d');
    ctx.fillStyle=SVGBG; ctx.fillRect(0,0,cv.width,cv.height);
    ctx.drawImage(img,0,0,cv.width,cv.height);
    URL.revokeObjectURL(url);
    const a=document.createElement('a');
    a.download='mindmap_'+Date.now()+'.png';
    a.href=cv.toDataURL('image/png',1.0); a.click();
  }};
  img.onerror=function(){{
    URL.revokeObjectURL(url);
    const a=document.createElement('a');
    a.download='mindmap_'+Date.now()+'.svg';
    a.href=URL.createObjectURL(new Blob([src],{{type:'image/svg+xml'}}));
    a.click();
  }};
  img.src=url;
}};

let rt;
window.addEventListener('resize',()=>{{clearTimeout(rt);rt=setTimeout(draw,250);}});
draw();
</script></body></html>"""
    components.html(html, height=575, scrolling=False)


# ══════════════════════════════════════════
# Live progress helper
# ══════════════════════════════════════════
WAIT_MSGS = [
    ("🧠","الذكاء يقرأ النص..."),("🔍","يحدد الأفكار الرئيسية..."),
    ("📌","يستخرج النقاط المهمة..."),("🌿","يرتب الفروع والتفاصيل..."),
    ("✍️","يصيغ الملخص الهيكلي..."),("🔗","يربط الأفكار ببعضها..."),
    ("🎯","يتحقق من الدقة والوضوح..."),("⚡","لحظات أخيرة قليلة..."),
    ("🗺️","الخريطة على وشك الظهور..."),("✨","تجهيز النتيجة النهائية..."),
]
TIPS = [
    "💡 الخريطة الذهنية تُحسّن الفهم بنسبة تصل لـ 40٪",
    "💡 اسحب الخريطة وكبّرها بعد الانتهاء",
    "💡 يمكن حفظ الخريطة كصورة PNG بضغط 💾",
    "💡 جرّب إعادة التلخيص للحصول على نتيجة مختلفة",
    "💡 ارفع ملف PDF/DOCX لتحليله مباشرة",
]
CHAT_MSGS = [
    ("🤔","يفكر في إجابتك..."),("📚","يراجع المعلومات..."),
    ("🔎","يبحث عن أفضل رد..."),("✍️","يصيغ الإجابة..."),
    ("🧩","يرتب الأفكار..."),("⚡","لحظات أخيرة..."),
]

def run_with_live_progress(fn, msgs, tips=None, tip_every=3):
    """
    يشغّل fn في thread، ويعرض progress bar حي أثناء الانتظار.
    يُعيد نتيجة fn.
    """
    result = {"val": None}
    def _run(): result["val"] = fn()
    prog = st.empty()
    tip  = st.empty()
    with concurrent.futures.ThreadPoolExecutor() as ex:
        fut = ex.submit(_run)
        step = 0
        while not fut.done():
            icon, msg = msgs[step % len(msgs)]
            prog.progress(min(10 + step * 9, 90), text=f"{icon} {msg}")
            if tips:
                tip.markdown(
                    f'<div style="text-align:center;font-size:12px;'
                    f'color:{C["TEXT2"]};margin-top:4px">{tips[step//tip_every % len(tips)]}</div>',
                    unsafe_allow_html=True
                )
            time.sleep(1.1)
            step += 1
    prog.progress(100, text="✅ جاهز!")
    tip.empty()
    time.sleep(0.3)
    prog.empty()
    return result["val"]


# ══════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════
warmup_once()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = (f"RAG ✓ — {st.session_state.doc_count} وثيقة"
      if st.session_state.doc_count > 0 else "chat")

h1, h2 = st.columns([5, 1])
with h1:
    st.markdown(
        f'<div class="top-bar">'
        f'<h2>🔬 مساعد البحث الذكي</h2>'
        f'<span class="badge {mc}">{mt}</span></div>',
        unsafe_allow_html=True
    )
with h2:
    label = "🌙" if st.session_state.theme == "light" else "☀️"
    if st.button(label, key="theme_btn", help="تبديل الثيم"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()


# ══════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════
with st.sidebar:
    st.markdown(f"### 📁 رفع الوثائق")
    uploaded = st.file_uploader(
        "PDF أو DOCX", type=["pdf","docx"], label_visibility="collapsed"
    )
    if uploaded:
        st.markdown(f'<div class="upload-info">📄 {uploaded.name}</div>',
                    unsafe_allow_html=True)
        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("⬆️ للدردشة", key="up_chat", use_container_width=True):
                with st.spinner("جارٍ الرفع..."):
                    ok, msg = upload_file(uploaded)
                if ok:
                    st.success(f"✅ {msg}")
                    time.sleep(1)
                    st.session_state.doc_count = fetch_count()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        with c_b:
            if st.button("🗺️ لخريطة", key="up_mm", use_container_width=True):
                # استخراج النص
                with st.spinner("📄 جارٍ قراءة الملف..."):
                    ok, text = extract_text_from_uploaded(uploaded)
                if ok and text.strip():
                    st.session_state.mm_raw_text  = text[:5000]
                    st.session_state.mm_extracted = ""   # لا نعرضه — نلخصه مباشرة
                    # تلخيص تلقائي فوري
                    summary = run_with_live_progress(
                        lambda t=text[:5000]: summarize_for_mindmap(t),
                        WAIT_MSGS, TIPS
                    )
                    st.session_state.mm_summary = summary or text[:5000]
                    st.session_state.mm_data = parse_mindmap_structure(
                        st.session_state.mm_summary
                    )
                    st.session_state.mm_step = 1
                    st.rerun()
                else:
                    st.error(f"❌ تعذر استخراج النص: {text}")

    st.divider()

    # ── محادثات محفوظة ──
    st.markdown("### 💾 المحادثات")
    sessions = load_sessions()

    if st.button("💾 حفظ الحالية", key="save_s",
                 type="secondary", use_container_width=True):
        if st.session_state.history:
            first_q = next(
                (t["content"][:40] for t in st.session_state.history if t["role"]=="user"),
                "محادثة"
            )
            sessions.insert(0, {
                "id": int(time.time()),
                "title": first_q,
                "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
                "history": st.session_state.history,
            })
            save_sessions(sessions[:10])
            st.success("تم الحفظ ✓")

    for i, sess in enumerate(sessions[:5]):
        sc1, sc2 = st.columns([5, 1])
        with sc1:
            if st.button(f"📝 {sess['title'][:22]}",
                         key=f"s_{i}", use_container_width=True, type="secondary"):
                st.session_state.history = sess["history"]
                st.session_state.mode = "chat"
                st.rerun()
        with sc2:
            if st.button("✕", key=f"d_{i}", type="secondary"):
                sessions.pop(i); save_sessions(sessions); st.rerun()

    st.divider()
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("🗑️ مسح", key="clr", type="secondary"):
            st.session_state.history = []
            save_history([])
            st.session_state.mm_step = 0
            st.session_state.mm_data = None
            st.rerun()
    with rc2:
        if st.button("🔄", key="ref", type="secondary"):
            st.session_state.doc_count = fetch_count()
            st.rerun()

    st.divider()
    # ── إيقاظ السيرفر ──
    srv = "🟢 متصل" if st.session_state.backend_warm else "🔴 قد يكون نائماً"
    st.markdown(f'<div style="font-size:12px;color:{C["TEXT2"]};margin-bottom:6px">'
                f'السيرفر: {srv}</div>', unsafe_allow_html=True)
    if st.button("🔔 إيقاظ السيرفر", key="wake", type="secondary", use_container_width=True):
        with st.spinner("جارٍ الإيقاظ... ⏳"):
            try:
                from utils import API_BASE
                import requests as req
                r = req.get(f"{API_BASE.replace('/api','')}/health", timeout=90)
                if r.ok:
                    st.session_state.backend_warm = True
                    st.success("✅ جاهز!")
                else:
                    st.warning("⚠️ يستجيب لكن بخطأ")
            except:
                st.error("❌ تعذر الوصول")
        st.rerun()

    st.markdown(f"""<div style="font-size:11px;color:{C['TEXT2']};line-height:1.9;margin-top:6px">
    <b style="color:{C['TEXT']}">الوضع:</b> {'🟢 RAG' if st.session_state.doc_count>0 else '🔵 Chat'}<br>
    <b style="color:{C['TEXT']}">وثائق:</b> {st.session_state.doc_count}
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# TABS
# ══════════════════════════════════════════
tab_chat, tab_mm = st.tabs(["💬 دردشة ذكية", "🗺️ خريطة ذهنية"])


# ─────────────────── TAB 1: CHAT ───────────────────
with tab_chat:
    if not st.session_state.backend_warm:
        st.markdown(
            f'<div class="info-tip">⚡ السيرفر قد يكون نائماً — '
            f'أول رد يأخذ 30-60 ثانية. '
            f'استخدم زر "إيقاظ السيرفر" في الشريط الجانبي لتسريع الأمر.</div>',
            unsafe_allow_html=True
        )

    if not st.session_state.history:
        st.markdown(
            f'<div style="text-align:center;padding:50px 0;color:{C["TEXT2"]}">'
            f'<div style="font-size:44px;opacity:.2;margin-bottom:14px">◎</div>'
            f'<p style="font-size:15px;font-weight:500">اسأل أي سؤال للبدء</p>'
            f'<p style="font-size:12px;opacity:.5;margin-top:8px">'
            f'ارفع ملفاً لتفعيل وضع RAG</p></div>',
            unsafe_allow_html=True
        )
    else:
        for i, turn in enumerate(st.session_state.history):
            if turn["role"] == "user":
                ts = turn.get("time","")
                st.markdown(
                    f'<div class="msg-label" style="text-align:right">أنت</div>'
                    f'<div class="msg-user">{turn["content"]}'
                    f'<div class="msg-time" style="text-align:right">{ts}</div></div>',
                    unsafe_allow_html=True
                )
            else:
                ts = turn.get("time","")
                st.markdown(
                    f'<div class="msg-label">المساعد</div>'
                    f'<div class="msg-ai">{turn["content"]}'
                    f'<div class="msg-time">{ts}</div></div>',
                    unsafe_allow_html=True
                )
                # زر إعادة المحاولة لآخر رد فقط
                if i == len(st.session_state.history) - 1:
                    if st.button("🔁 إعادة المحاولة", key=f"rt_{i}", type="secondary"):
                        last_q = next(
                            (t["content"] for t in reversed(st.session_state.history[:-1])
                             if t["role"]=="user"), None
                        )
                        if last_q:
                            st.session_state.history = st.session_state.history[:-1]
                            ans = run_with_live_progress(
                                lambda: ask_chat(last_q), CHAT_MSGS
                            )
                            st.session_state.history.append({
                                "role":"assistant","content":ans,
                                "time":datetime.now().strftime("%H:%M")
                            })
                            save_history(st.session_state.history)
                            st.rerun()

    with st.form("cf", clear_on_submit=True):
        q = st.text_area("س", placeholder="اكتب سؤالك هنا...",
                         label_visibility="collapsed", height=85)
        sub = st.form_submit_button("إرسال ➤", use_container_width=True)

    if sub and q.strip():
        q_text = q.strip()
        ans = run_with_live_progress(
            lambda: ask_chat(q_text), CHAT_MSGS
        )
        now = datetime.now().strftime("%H:%M")
        st.session_state.history.append({"role":"user","content":q_text,"time":now})
        st.session_state.history.append({"role":"assistant","content":ans,"time":now})
        if len(st.session_state.history) > 30:
            st.session_state.history = st.session_state.history[-30:]
        save_history(st.session_state.history)
        st.rerun()


# ─────────────────── TAB 2: MINDMAP ───────────────────
with tab_mm:
    # ── خطوة 0: إدخال النص ──
    if st.session_state.mm_step == 0:
        st.markdown(
            f'<div class="mm-box"><p>'
            f'✍️ الصق نصاً في المربع أدناه أو 📁 ارفع ملف PDF/DOCX من الشريط الجانبي<br>'
            f'← الذكاء يلخصه ويستخرج النقاط ← خريطة ذهنية تفاعلية'
            f'</p></div>',
            unsafe_allow_html=True
        )

        # مربع الإدخال اليدوي
        with st.form("mmf", clear_on_submit=False):
            raw = st.text_area(
                "النص",
                placeholder="الصق نصك هنا...",
                label_visibility="collapsed",
                height=200,
                value=st.session_state.mm_raw_text,
            )
            go = st.form_submit_button("🧠 تحليل وبناء الخريطة", use_container_width=True)

        if go and raw.strip():
            st.session_state.mm_raw_text  = raw.strip()
            st.session_state.mm_extracted = ""
            summary = run_with_live_progress(
                lambda: summarize_for_mindmap(raw.strip()),
                WAIT_MSGS, TIPS
            )
            st.session_state.mm_summary = summary or raw.strip()
            st.session_state.mm_data = parse_mindmap_structure(
                st.session_state.mm_summary
            )
            st.session_state.mm_step = 1
            st.rerun()

    # ── خطوة 1: عرض النتيجة ──
    elif st.session_state.mm_step == 1:
        with st.expander("📋 الملخص الهيكلي", expanded=False):
            st.markdown(
                f'<div class="summary-box">'
                f'{st.session_state.mm_summary.replace(chr(10),"<br>")}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div class="step-label">'
            f'🗺️ الخريطة الذهنية — اسحب للتنقل | +/− للتكبير | 💾 حفظ PNG'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.session_state.mm_data:
            render_mindmap(st.session_state.mm_data)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("🔄 نص جديد", key="mm_new",
                         use_container_width=True, type="secondary"):
                st.session_state.mm_step = 0
                st.session_state.mm_raw_text = ""
                st.session_state.mm_summary  = ""
                st.session_state.mm_data     = None
                st.session_state.mm_extracted= ""
                st.rerun()
        with bc2:
            if st.button("✏️ تعديل النص", key="mm_edit",
                         use_container_width=True, type="secondary"):
                st.session_state.mm_step = 0
                st.rerun()
        with bc3:
            if st.button("🔁 إعادة التلخيص", key="mm_retry",
                         use_container_width=True, type="secondary"):
                summary = run_with_live_progress(
                    lambda: summarize_for_mindmap(st.session_state.mm_raw_text),
                    WAIT_MSGS, TIPS
                )
                st.session_state.mm_summary = summary or st.session_state.mm_raw_text
                st.session_state.mm_data = parse_mindmap_structure(
                    st.session_state.mm_summary
                )
                st.rerun()
