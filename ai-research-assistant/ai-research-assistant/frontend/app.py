"""
app.py — يخدم الواجهة الأمامية كـ static HTML عبر FastAPI نفسه
ضعه في جذر المشروع بجانب main.py
"""

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from main import app   # استيراد app من main.py


HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>مساعد البحث الذكي</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;--bg2:#1a1d27;--bg3:#23273a;
  --border:#2e3248;--text:#e8eaf0;--text2:#8b90a7;
  --accent:#5b6ef5;--accent2:#3d4fd4;
  --success:#22c55e;--error:#ef4444;
  --radius:12px;--radius-sm:8px;
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);height:100dvh;display:flex;flex-direction:column;overflow:hidden}

/* ── Header ── */
#hdr{padding:12px 18px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:10px}
#hdr-l{display:flex;align-items:center;gap:10px}
#logo{width:30px;height:30px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0}
#hdr h1{font-size:14px;font-weight:600;white-space:nowrap}
#hdr-r{display:flex;align-items:center;gap:8px;flex-shrink:0}
#mode{font-size:11px;padding:2px 9px;border-radius:20px;border:1px solid var(--border);color:var(--text2);transition:all .3s;white-space:nowrap}
#mode.rag{border-color:var(--success);color:var(--success);background:rgba(34,197,94,.08)}
#ndocs{font-size:11px;color:var(--text2);white-space:nowrap}
#clr{font-size:11px;padding:2px 9px;border:1px solid var(--border);border-radius:20px;background:transparent;color:var(--text2);cursor:pointer;transition:all .2s;white-space:nowrap}
#clr:hover{border-color:var(--error);color:var(--error)}

/* ── Messages ── */
#msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:14px}
#msgs::-webkit-scrollbar{width:3px}
#msgs::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
#empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--text2);height:100%}
#empty .ic{font-size:36px;opacity:.3}
#empty p{font-size:13px}
#empty small{font-size:11px;opacity:.6}

.row{display:flex;gap:8px;align-items:flex-start}
.row.user{flex-direction:row-reverse}
.av{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;margin-top:2px}
.row.user .av{background:var(--accent);color:#fff}
.row.assistant .av{background:var(--bg3);color:var(--text2);border:1px solid var(--border)}
.bbl{max-width:75%;padding:10px 14px;border-radius:var(--radius);font-size:13px;line-height:1.75;white-space:pre-wrap;word-break:break-word;border:1px solid var(--border)}
.row.user .bbl{background:var(--bg3);border-radius:var(--radius) 3px var(--radius) var(--radius)}
.row.assistant .bbl{background:#1e2238;border-radius:3px var(--radius) var(--radius) var(--radius)}
.bbl.err{border-color:var(--error);color:var(--error);background:rgba(239,68,68,.06)}
.bbl.ok{border-color:var(--success);color:var(--success);background:rgba(34,197,94,.06)}
.typing{display:flex;gap:4px;align-items:center;padding:12px 14px}
.dot{width:6px;height:6px;border-radius:50%;background:var(--text2);animation:b .9s infinite}
.dot:nth-child(2){animation-delay:.15s}.dot:nth-child(3){animation-delay:.3s}
@keyframes b{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}

/* ── Upload bar ── */
#upbar{padding:7px 14px;border-top:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;gap:8px;flex-shrink:0}
#flbl{cursor:pointer;font-size:12px;padding:4px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text2);transition:border-color .2s;white-space:nowrap}
#flbl:hover{border-color:var(--accent);color:var(--text)}
#finput{display:none}
#finfo{flex:1;font-size:12px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
#pwrap{width:50px;height:2px;background:var(--bg3);border-radius:1px;display:none;flex-shrink:0}
#pbar{height:100%;background:var(--accent);border-radius:1px;width:0;transition:width .3s}
#ubtn{font-size:12px;padding:4px 12px;border:1px solid var(--accent);border-radius:var(--radius-sm);background:transparent;color:var(--accent);cursor:pointer;transition:background .2s;white-space:nowrap;flex-shrink:0}
#ubtn:hover:not(:disabled){background:rgba(91,110,245,.15)}
#ubtn:disabled{opacity:.4;cursor:not-allowed}

/* ── Input area ── */
#inarea{padding:10px 14px 14px;border-top:1px solid var(--border);background:var(--bg2);display:flex;gap:8px;align-items:flex-end;flex-shrink:0}
#qin{flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:9px 13px;font-size:13px;font-family:inherit;color:var(--text);resize:none;min-height:40px;max-height:120px;line-height:1.5;direction:rtl;transition:border-color .2s}
#qin::placeholder{color:var(--text2)}
#qin:focus{outline:none;border-color:var(--accent)}
#sbtn{width:40px;height:40px;border-radius:var(--radius-sm);background:var(--accent);border:none;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:background .2s;flex-shrink:0}
#sbtn:hover:not(:disabled){background:var(--accent2)}
#sbtn:disabled{opacity:.4;cursor:not-allowed}
#sbtn svg{width:16px;height:16px;fill:#fff}
</style>
</head>
<body>

<div id="hdr">
  <div id="hdr-l">
    <div id="logo">AI</div>
    <h1>مساعد البحث الذكي</h1>
  </div>
  <div id="hdr-r">
    <span id="mode">chat</span>
    <span id="ndocs">0 وثيقة</span>
    <button id="clr">مسح</button>
  </div>
</div>

<div id="msgs">
  <div id="empty">
    <div class="ic">◎</div>
    <p>اسأل أي سؤال أو ارفع ملفاً للبدء</p>
    <small>يعمل بدون ملفات — ارفع PDF أو DOCX لتفعيل وضع RAG</small>
  </div>
</div>

<div id="upbar">
  <label id="flbl" for="finput">📎 ملف</label>
  <input id="finput" type="file" accept=".pdf,.docx"/>
  <span id="finfo">PDF أو DOCX</span>
  <div id="pwrap"><div id="pbar"></div></div>
  <button id="ubtn" disabled>رفع</button>
</div>

<div id="inarea">
  <textarea id="qin" placeholder="اكتب سؤالك... (Enter إرسال | Shift+Enter سطر جديد)" rows="1"></textarea>
  <button id="sbtn">
    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
  </button>
</div>

<script>
const API = '/api';   /* نفس الدومين — لا حاجة لـ localhost */
let history = [], docCount = 0, busy = false;

const msgs  = document.getElementById('msgs');
const empty = document.getElementById('empty');
const qin   = document.getElementById('qin');
const sbtn  = document.getElementById('sbtn');
const clr   = document.getElementById('clr');
const fin   = document.getElementById('finput');
const finfo = document.getElementById('finfo');
const ubtn  = document.getElementById('ubtn');
const modEl = document.getElementById('mode');
const ndEl  = document.getElementById('ndocs');
const pwrap = document.getElementById('pwrap');
const pbar  = document.getElementById('pbar');

function setMode(n){
  docCount = n ?? docCount;
  ndEl.textContent = docCount + ' وثيقة';
  if(docCount > 0){ modEl.textContent='RAG ✓'; modEl.classList.add('rag'); }
  else            { modEl.textContent='chat';  modEl.classList.remove('rag'); }
}

function rmEmpty(){ if(empty.parentNode) empty.remove(); }

function addMsg(role, text, cls=''){
  rmEmpty();
  const row = document.createElement('div'); row.className='row '+role;
  const av  = document.createElement('div'); av.className='av'; av.textContent=role==='user'?'أنت':'AI';
  const bbl = document.createElement('div'); bbl.className='bbl'+(cls?' '+cls:''); bbl.textContent=text;
  row.appendChild(av); row.appendChild(bbl);
  msgs.appendChild(row); msgs.scrollTop=msgs.scrollHeight;
  return bbl;
}

function showTyping(){
  rmEmpty();
  const row=document.createElement('div'); row.className='row assistant'; row.id='typ';
  const av=document.createElement('div'); av.className='av'; av.textContent='AI';
  const bbl=document.createElement('div'); bbl.className='bbl';
  bbl.innerHTML='<div class="typing"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';
  row.appendChild(av); row.appendChild(bbl); msgs.appendChild(row); msgs.scrollTop=msgs.scrollHeight;
}
function hideTyping(){ const t=document.getElementById('typ'); if(t)t.remove(); }

async function send(){
  const q=qin.value.trim(); if(!q||busy) return;
  busy=true; sbtn.disabled=true; qin.value=''; qin.style.height='40px';
  addMsg('user',q); showTyping();
  try{
    const r=await fetch(API+'/query',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question:q,history,stream:false})
    });
    if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.detail||'HTTP '+r.status); }
    const d=await r.json();
    hideTyping();
    const ans=d.answer||'لا توجد إجابة';
    addMsg('assistant',ans);
    history.push({role:'user',content:q},{role:'assistant',content:ans});
    if(history.length>20) history=history.slice(-20);
    if(typeof d.documents_count==='number') setMode(d.documents_count);
  } catch(e){
    hideTyping();
    addMsg('assistant','❌ فشل الاتصال بالخادم\n'+e.message,'err');
  }
  busy=false; sbtn.disabled=false; qin.focus();
}

fin.addEventListener('change',()=>{
  const f=fin.files[0];
  finfo.textContent = f ? f.name : 'PDF أو DOCX';
  ubtn.disabled = !f;
});

ubtn.addEventListener('click',async()=>{
  const f=fin.files[0]; if(!f) return;
  ubtn.disabled=true; ubtn.textContent='...';
  pwrap.style.display='block'; pbar.style.width='40%';
  const fd=new FormData(); fd.append('file',f);
  try{
    const r=await fetch(API+'/upload',{method:'POST',body:fd});
    const d=await r.json();
    pbar.style.width='100%';
    setTimeout(()=>{pwrap.style.display='none';pbar.style.width='0';},600);
    if(d.error||!r.ok){
      addMsg('assistant','❌ فشل الرفع: '+(d.error||d.detail||'خطأ'),'err');
    } else {
      addMsg('assistant','✅ تم رفع "'+f.name+'" — جارٍ المعالجة في الخلفية...','ok');
      finfo.textContent='PDF أو DOCX'; fin.value='';
      setTimeout(async()=>{
        try{ const x=await(await fetch(API+'/documents/count')).json(); setMode(x.count??0); }catch(_){}
      },4000);
    }
  } catch(e){
    pwrap.style.display='none';
    addMsg('assistant','❌ فشل الرفع: '+e.message,'err');
  }
  ubtn.textContent='رفع'; ubtn.disabled=false;
});

clr.addEventListener('click',()=>{
  history=[];
  msgs.innerHTML='';
  const es=document.createElement('div'); es.id='empty'; es.className=''; 
  es.style.cssText='display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--text2);height:100%';
  es.innerHTML='<div class="ic" style="font-size:36px;opacity:.3">◎</div><p style="font-size:13px">تم مسح المحادثة</p>';
  msgs.appendChild(es);
});

qin.addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();} });
qin.addEventListener('input',()=>{ qin.style.height='40px'; qin.style.height=Math.min(qin.scrollHeight,120)+'px'; });

(async()=>{
  try{ const d=await(await fetch('/health')).json(); setMode(d.documents_count??0); }catch(_){}
  qin.focus();
})();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTMLResponse(content=HTML)
