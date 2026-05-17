"""Live progress view for the seeded `background_agent` Tool.

Two token-authed endpoints (no session — the chat embeds these in a
sandboxed, null-origin iframe, so the signed job token is the credential):

  GET /api/v1/agent/jobs/{job_id}/view?token=    -> self-contained HTML page
  GET /api/v1/agent/jobs/{job_id}/stream?token=  -> text/event-stream

See open_webui.utils.agent_jobs for the registry + token.
"""

import asyncio
import json
import logging
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from open_webui.utils import agent_jobs
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()


def _authorize(job_id: str, token: str):
    tok_job = agent_jobs.verify_job_token(token or "")
    if tok_job is None or tok_job != job_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    rec = agent_jobs.get(job_id)
    if rec is None:
        # Pruned after completion (discardable) or never existed.
        raise HTTPException(status_code=410, detail="Job no longer available")
    return rec


@router.get("/jobs/{job_id}/stop")
async def stop_job(job_id: str, token: str = Query("")):
    """Token-authed cancel (called by the Stop button in the iframe; the
    run loop checks the flag between steps and finalizes a partial)."""
    if agent_jobs.verify_job_token(token or "") != job_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    ok = agent_jobs.request_cancel(job_id)
    return JSONResponse(
        {"stopping": ok},
        headers={"Access-Control-Allow-Origin": "*",
                 "Cache-Control": "no-store"},
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, request: Request, token: str = Query("")):
    rec = _authorize(job_id, token)

    async def gen():
        # 1) Replay everything buffered so far (late iframe still sees history).
        for ev in list(rec.events):
            yield f"data: {json.dumps(ev)}\n\n"
        if agent_jobs.is_terminal(rec.state):
            yield "event: done\ndata: {}\n\n"
            return
        # 2) Live tail.
        q = agent_jobs.subscribe(job_id)
        if q is None:
            yield "event: done\ndata: {}\n\n"
            return
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # keep proxies/cloudflared from idling out
                    continue
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("kind") == "state" and str(
                    ev.get("text", "")
                ).startswith("__done__:"):
                    yield "event: done\ndata: {}\n\n"
                    break
        finally:
            agent_jobs.unsubscribe(job_id, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            # Sandboxed iframe = null origin; token is the only credential.
            "Access-Control-Allow-Origin": "*",
        },
    )


_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Agent</title><style>
:root{color-scheme:dark}
html,body{margin:0;height:100%;background:#0d1117;color:#c9d1d9;
font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
#hd{padding:6px 10px;background:#161b22;border-bottom:1px solid #30363d;
display:flex;gap:8px;align-items:center;position:sticky;top:0;z-index:2}
#bdg{padding:1px 7px;border-radius:9px;font-weight:600;font-size:11px}
.run,.running{background:#1f6feb33;color:#58a6ff}
.success,.done{background:#23863633;color:#3fb950}
.partial,.noop{background:#9e6a0333;color:#d29922}
.error,.cancelled,.failed{background:#da363333;color:#f85149}
.pending{background:#30363d55;color:#8b949e}
#sm{color:#8b949e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#wrap{padding:6px 8px}
.step{border:1px solid #30363d;border-radius:6px;margin:6px 0;overflow:hidden}
.sh{display:flex;gap:8px;align-items:center;padding:5px 8px;cursor:pointer;
background:#161b22;user-select:none}
.sh .n{color:#6e7681}.sh .ti{flex:1;overflow:hidden;text-overflow:ellipsis;
white-space:nowrap}
.sb{padding:4px 10px;white-space:pre-wrap;word-break:break-word;
border-top:1px solid #21262d}
.sb.collapsed{display:none}
.l{padding:1px 0}.t{color:#6e7681;margin-right:6px}
.k-tool_call{color:#58a6ff}.k-tool_result{color:#3fb950}
.k-error{color:#f85149}.k-llm{color:#bc8cff}.k-state{color:#d29922}
.k-log{color:#8b949e}
.bmini{font-size:10px;padding:0 6px;border-radius:8px}
#el{color:#8b949e;font-variant-numeric:tabular-nums}
#stop{margin-left:auto;font:inherit;font-size:11px;cursor:pointer;
background:#da363322;color:#f85149;border:1px solid #da363355;
border-radius:6px;padding:1px 9px}
#stop:disabled{opacity:.5;cursor:default}
</style></head><body>
<div id="hd"><span id="bdg" class="run">běží</span>
<span id="el">0:00</span><span id="sm"></span>
<button id="stop" title="Zastavit běžící úlohu">Stop</button></div>
<div id="wrap"></div>
<script>
var JOB=%JOB%,TOK=%TOK%;
var bdg=document.getElementById('bdg'),sm=document.getElementById('sm'),
wrap=document.getElementById('wrap'),el=document.getElementById('el'),
stopBtn=document.getElementById('stop');
sm.textContent=%SUMMARY%;
var T0=Date.now(),lastTs=0,clk=setInterval(tick,1000);
function fmt(s){s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+
('0'+(s%60)).slice(-2);}
function tick(){el.textContent=fmt(lastTs||((Date.now()-T0)/1000));}
function freeze(){if(clk){clearInterval(clk);clk=null;}
stopBtn.disabled=true;}
stopBtn.onclick=function(){stopBtn.disabled=true;stopBtn.textContent='…';
fetch('%BASE%/api/v1/agent/jobs/'+JOB+'/stop?token='+
encodeURIComponent(TOK)).catch(function(){});};
var L={pending:'čeká',running:'běží',done:'hotovo',noop:'bez akcí',
failed:'SELHAL',success:'hotovo',partial:'částečně',error:'chyba',
cancelled:'zrušeno'};
var steps={},cur=null;
function mkStep(n,title){
 var box=document.createElement('div');box.className='step';
 var h=document.createElement('div');h.className='sh';
 var nn=document.createElement('span');nn.className='n';nn.textContent='#'+n;
 var ti=document.createElement('span');ti.className='ti';ti.textContent=title||('Krok '+n);
 var bg=document.createElement('span');bg.className='bmini running';bg.textContent='běží';
 h.appendChild(nn);h.appendChild(ti);h.appendChild(bg);
 var b=document.createElement('div');b.className='sb collapsed';
 h.onclick=function(){b.classList.toggle('collapsed');};
 box.appendChild(h);box.appendChild(b);wrap.appendChild(box);
 steps[n]={box:box,body:b,badge:bg,head:h,ti:ti};
 // collapse the previously running step to keep the list scannable
 if(cur!=null&&steps[cur])steps[cur].body.classList.add('collapsed');
 cur=n;return steps[n];}
function prep(){if(!steps.__prep__){
 var b=document.createElement('div');b.className='sb';b.style.borderTop='0';
 var box=document.createElement('div');box.className='step';
 var h=document.createElement('div');h.className='sh';
 h.innerHTML='<span class="ti">Příprava</span>';
 h.onclick=function(){b.classList.toggle('collapsed');};
 box.appendChild(h);box.appendChild(b);wrap.appendChild(box);
 steps.__prep__={body:b};}
 return steps.__prep__;}
function line(body,ev){var d=document.createElement('div');d.className='l';
 var t=document.createElement('span');t.className='t';
 t.textContent=(ev.ts!=null?ev.ts+'s':'');
 var m=document.createElement('span');m.className='k-'+(ev.kind||'log');
 m.textContent=' '+(ev.text||'');d.appendChild(t);d.appendChild(m);
 body.appendChild(d);
 try{d.scrollIntoView({block:'nearest'});}catch(x){
  window.scrollTo(0,document.body.scrollHeight);}}
var TERM={success:1,partial:1,error:1,cancelled:1,failed:1,done:1};
function setState(s){bdg.className=s;bdg.textContent=L[s]||s;
 if(TERM[s]){tick();freeze();}}
function handle(ev){
 if(ev&&typeof ev.ts==='number'){lastTs=ev.ts;tick();}
 if(ev.kind==='step'){
  var n=(ev.data&&ev.data.n)||0,st=(ev.data&&ev.data.status)||'running',
  tt=(ev.data&&ev.data.title)||ev.text;
  var s=steps[n]||mkStep(n,tt);
  if(tt)s.ti.textContent='Krok '+n+' — '+tt;
  s.badge.className='bmini '+st;s.badge.textContent=L[st]||st;
  if(st==='running'){cur=n;
   for(var kk in steps){if(steps[kk].body)
    steps[kk].body.classList.add('collapsed');}
   try{s.box.scrollIntoView({block:'start'});}catch(x){}}
  else s.body.classList.add('collapsed');
  return;}
 if(ev.kind==='state'&&(''+ev.text).indexOf('__done__:')===0){
  setState((''+ev.text).split(':')[1]);return;}
 var tgt=(cur!=null&&steps[cur])?steps[cur].body:prep().body;
 line(tgt,ev);}
var EV=%EVENTS%;
if(EV){for(var i=0;i<EV.length;i++)handle(EV[i]);
 if(bdg.className==='run'||bdg.className==='running')setState('done');}
else{var es=new EventSource('%BASE%/api/v1/agent/jobs/'+JOB
 +'/stream?token='+encodeURIComponent(TOK));
 es.onmessage=function(e){try{var ev=JSON.parse(e.data);}catch(x){return;}
  handle(ev);};
 es.addEventListener('done',function(){es.close();
  if(bdg.className==='run'||bdg.className==='running')setState('success');});
 es.onerror=function(){/* keep retrying; backend may be mid-restart */};}
</script></body></html>"""


def _render(job_id, summary, token="", events=None):
    return (
        _PAGE.replace("%JOB%", json.dumps(job_id))
        .replace("%TOK%", json.dumps(token))
        .replace("%SUMMARY%", json.dumps(summary or "Agent"))
        .replace("%BASE%", "")
        .replace("%EVENTS%", json.dumps(events) if events is not None else "null")
    )


@router.get("/jobs/{job_id}/view", response_class=HTMLResponse)
async def view_job(job_id: str, request: Request, token: str = Query("")):
    # Token must be valid for this job (the in-chat iframe credential).
    if agent_jobs.verify_job_token(token or "") != job_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    rec = agent_jobs.get(job_id)
    if rec is not None:
        # Live: stream via EventSource.
        page = _render(job_id, rec.summary, token=token, events=None)
    else:
        # Fallen out of memory — serve the persisted log statically so the
        # in-chat link still works within the token TTL.
        pj = agent_jobs.read_persisted(job_id)
        if pj is None:
            raise HTTPException(status_code=410, detail="Job no longer available")
        page = _render(
            job_id, pj.get("summary"), token=token,
            events=pj.get("events") or [],
        )
    return HTMLResponse(
        content=page,
        headers={"Cache-Control": "no-store", "X-Frame-Options": "SAMEORIGIN"},
    )


@router.get("/jobs")
async def list_jobs(user=Depends(get_admin_user)):
    """Admin: recent agent runs (active in-memory + persisted), newest first.
    For later debugging via GET /api/v1/agent/jobs/{id}/log."""
    seen = set()
    out = []
    for jid, rec in list(agent_jobs.JOBS.items()):
        seen.add(jid)
        out.append(
            {
                "job_id": jid,
                "summary": rec.summary,
                "state": rec.state,
                "created_at": rec.created_at,
                "finished_at": rec.finished_at,
                "events": len(rec.events),
                "live": True,
            }
        )
    for m in agent_jobs.list_persisted():
        if m.get("job_id") in seen:
            continue
        m["live"] = False
        out.append(m)
    out.sort(
        key=lambda x: (x.get("finished_at") or x.get("created_at") or 0),
        reverse=True,
    )
    return {"jobs": out}


@router.get("/jobs/{job_id}/log")
async def job_log(
    job_id: str,
    format: str = Query("html"),
    user=Depends(get_admin_user),
):
    """Admin: retrieve a (possibly old) run log for debugging. Live job uses
    its in-memory events; otherwise the persisted file. `?format=json` for
    the raw record."""
    rec = agent_jobs.get(job_id)
    if rec is not None:
        data = {
            "job_id": job_id,
            "summary": rec.summary,
            "state": rec.state,
            "created_at": rec.created_at,
            "finished_at": rec.finished_at,
            "events": list(rec.events),
        }
    else:
        data = agent_jobs.read_persisted(job_id)
        if data is None:
            raise HTTPException(status_code=404, detail="No log for this job")
    if format == "json":
        return JSONResponse(data)
    return HTMLResponse(
        content=_render(
            job_id, data.get("summary"), token="",
            events=data.get("events") or [],
        ),
        headers={"Cache-Control": "no-store", "X-Frame-Options": "SAMEORIGIN"},
    )
