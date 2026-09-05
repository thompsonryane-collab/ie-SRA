/* ══ CMDR LINK — ADMIN side of the ie-SRA bus ══ */
(function(){
  var C=window.ADMIN_CORE, bus=window.SRABus; if(!C||!bus)return;
  var $=function(id){return document.getElementById(id);};
  function esc(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function toast(m,t){if(typeof hubToast==='function')hubToast(m,t||'ok',3600);}
  function hhmm(ts){var d=new Date(ts);return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');}
  var cfg=bus.cfg(); if(cfg.node!=='admin'){bus.configure({node:'admin',site:'*'});cfg=bus.cfg();}
  var EV=[]; function ev(s){EV.unshift(hhmm(Date.now())+' '+s);if(EV.length>30)EV.length=30;paintPanel();}
  var peers={};

  /* ── outbound: wrap core ── */
  var _logWO=C.logWO;
  C.logWO=function(rec){
    var r=_logWO.apply(this,arguments);
    try{
      var p={code:rec.code,site:rec.site,siteName:rec.siteName,msg:rec.msg,test:!!rec.test,channels:rec.channels,kind:rec.kind||(rec.test?'TEST':'LIVE'),ts:rec.ts,title:rec.title||null};
      bus.publish('WARNORD',p,{site:rec.site||'*'});ev('WARNORD '+rec.code+' → '+(rec.siteName||'*'));
    }catch(e){console.error('cmdr link publish',e);}
    return r;
  };
  var _sendMsg=C.sendMsg;
  C.sendMsg=function(ch,text,from){
    var r=_sendMsg.apply(this,arguments);
    try{
      var f=from||''; if(/^CMDR\b/.test(f))return r;              // came from the bus — don't echo
      if(ch==='all'||(ch&&ch.indexOf('site:')===0)){bus.publish('MSG',{text:text,ch:ch,from:f||'ADMIN sysadmin'},{site:ch==='all'?'*':ch.slice(5)});ev('MSG → '+ch);}
    }catch(e){}
    return r;
  };
  function snapshot(siteId){
    var s=C.SITE[siteId]; if(!s)return null;
    var wos=C.listWO().filter(function(w){return w.site===siteId;}).slice(0,20);
    var sum=C.summary(), h=C.health(s);
    function inst(i){return {status:i.status,version:i.version,lastSyncMin:i.lastSyncMin,uptime:i.uptime,cpu:i.cpu};}
    function usr(u){return {name:u.name,role:u.role,status:u.status,device:u.device,lastSeenMin:u.lastSeenMin};}
    return {site:s.id,siteName:s.name,region:s.region,regionName:s.regionName,uic:s.uic,health:h,healthColor:C.healthColor(h),
      primary:s.primary.status,secondary:s.secondary.status,primaryInst:inst(s.primary),secondaryInst:inst(s.secondary),
      fm:usr(s.fm),backup:usr(s.backup),openWO:(s.openWO||0)+wos.filter(function(w){return !w.ack&&!w.test;}).length,outage:!!s.outage||wos.some(function(w){return !w.ack&&!w.test;}),
      usersOnline:[s.fm,s.backup].filter(function(u){return u.status==='online';}).length,
      enterprise:{sites:sum.sites,instances:sum.instances,online:sum.online,degraded:sum.degraded,offline:sum.offline,usersOnline:sum.usersOnline,openWO:sum.openWO,outages:sum.outages,devicesPending:sum.devicesPending},
      wos:wos,sub:null};
  }
  function sendStatus(siteId){var p=snapshot(siteId);if(!p)return;bus.publish('STATUS',p,{site:siteId});ev('STATUS → '+p.siteName);}

  /* ── inbound ── */
  bus.subscribe(function(env,replay){
    var p=env.payload||{};
    if(env.type==='ACK'){
      var log=C.listWO(); var hit=log.filter(function(w){return w.code===p.code;})[0];
      if(hit&&!hit.ack){hit.ack={by:p.by,ts:env.ts,via:p.via||'mobile'};try{localStorage.setItem('adm_wo_log',JSON.stringify(log));}catch(e){}}
      if(!replay){C.audit('CMDR_ACK',p.siteName||p.site||'',p.code+' acknowledged by '+p.by+' ('+(p.role||'Base Commander')+') via '+(p.via||'mobile'));
        toast('CMDR acknowledged '+p.code+' — '+p.by,'ok');ev('ACK '+p.code+' ← '+p.by);
        if(typeof admPaintRouting==='function'&&$('overlay-adm-routing')&&$('overlay-adm-routing').classList.contains('visible'))try{admPaintRouting();}catch(e){}
        if(typeof admPaintAudit==='function'&&$('overlay-adm-audit')&&$('overlay-adm-audit').classList.contains('visible'))try{admPaintAudit();}catch(e){}
        if(typeof admPaintStrip==='function')try{admPaintStrip();}catch(e){}}
    }else if(env.type==='MSG'){
      if(replay)return;
      var ch=p.ch||('site:'+(env.site||'nb-sd'));
      C.sendMsg(ch,p.text,'CMDR '+(p.by||'Base Commander')+' (mobile)');
      C.audit('CMDR_MSG',ch,String(p.text||'').slice(0,80));
      toast('CMDR message: '+String(p.text||'').slice(0,60),'ok');ev('MSG ← '+(p.by||'CMDR'));
      if(typeof admPaintMsgs==='function'&&$('overlay-adm-msg')&&$('overlay-adm-msg').classList.contains('visible'))try{admPaintMsgs();}catch(e){}
    }else if(env.type==='HELLO'){
      peers[env.site||'?']={name:p.commander,ts:env.ts,app:p.app};
      if(replay)return;
      C.audit('CMDR_HELLO',p.siteName||env.site||'',(p.commander||'')+' · '+(p.app||''));
      toast('CMDR linked: '+(p.commander||'commander')+' @ '+(p.siteName||env.site),'ok');ev('HELLO ← '+(p.commander||'')+' @ '+env.site);
      bus.publish('HELLO',{node:'admin',app:'ie-SRA ADMIN'},{site:env.site||'*'});
      sendStatus(env.site||'nb-sd');
    }
  });

  /* ── chip + panel UI ── */
  var css=document.createElement('style');
  css.textContent='#cl-chip{position:fixed;right:16px;bottom:16px;z-index:9000;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:20px;background:rgba(8,16,28,.92);border:1px solid rgba(110,144,176,.35);color:#cce0f2;font-family:"Share Tech Mono",monospace;font-size:10px;letter-spacing:1.4px;cursor:pointer;backdrop-filter:blur(10px);box-shadow:0 8px 24px rgba(0,0,0,.45)}'+
  '#cl-chip i{width:8px;height:8px;border-radius:50%;background:#e05555;box-shadow:0 0 0 3px rgba(224,85,85,.2)}#cl-chip.on i{background:#4db88a;box-shadow:0 0 0 3px rgba(77,184,138,.2)}#cl-chip.warn i{background:#d4a05a}'+
  '#cl-panel{position:fixed;right:16px;bottom:56px;z-index:9001;width:340px;max-width:calc(100vw - 32px);background:#0a1524;border:1px solid rgba(110,144,176,.35);border-radius:12px;padding:12px 14px;color:#cce0f2;font-family:-apple-system,"Segoe UI",sans-serif;font-size:12px;display:none;box-shadow:0 16px 40px rgba(0,0,0,.6)}#cl-panel.on{display:block}'+
  '#cl-panel h4{font-family:"Share Tech Mono",monospace;font-size:10px;letter-spacing:1.6px;color:#6e90b0;margin:0 0 8px}#cl-panel .r{display:grid;grid-template-columns:86px 1fr;gap:6px;align-items:center;margin-bottom:6px}#cl-panel label{color:#6e90b0;font-size:11px}'+
  '#cl-panel input,#cl-panel select{width:100%;background:#0f1d30;border:1px solid rgba(110,144,176,.3);border-radius:6px;color:#fff;font:inherit;padding:5px 7px}#cl-panel .btns{display:flex;gap:6px;margin-top:8px}#cl-panel button{flex:1;background:#132640;border:1px solid rgba(110,144,176,.4);color:#cce0f2;border-radius:6px;padding:6px;font:inherit;cursor:pointer}#cl-panel button.pri{background:#18d4f8;color:#04202c;border-color:#18d4f8;font-weight:600}'+
  '#cl-log{margin-top:8px;max-height:120px;overflow:auto;font-family:"Share Tech Mono",monospace;font-size:9.5px;color:#9ab4cc;line-height:1.5;border-top:1px solid rgba(110,144,176,.2);padding-top:6px}#cl-peers{font-size:11px;color:#4db88a;margin-bottom:6px}';
  document.head.appendChild(css);
  var chip=document.createElement('button');chip.id='cl-chip';chip.innerHTML='<i></i><span id="cl-txt">CMDR LINK</span>';chip.onclick=function(){panel.classList.toggle('on');paintPanel();};document.body.appendChild(chip);
  var panel=document.createElement('div');panel.id='cl-panel';
  panel.innerHTML='<h4>CMDR LINK — ADM-03 MOBILE BRIDGE</h4><div id="cl-peers"></div>'+
    '<div class="r"><label>Transport</label><select id="cl-transport"><option value="broadcast">Same browser (BroadcastChannel)</option><option value="github">GitHub repo (cross-device)</option><option value="off">Off</option></select></div>'+
    '<div class="r cl-gh"><label>Repo</label><input id="cl-repo"></div><div class="r cl-gh"><label>Branch</label><input id="cl-branch"></div><div class="r cl-gh"><label>File</label><input id="cl-path"></div><div class="r cl-gh"><label>Token</label><input id="cl-token" type="password" autocomplete="off"></div><div class="r cl-gh"><label>Poll (s)</label><input id="cl-poll" type="number" min="3"></div>'+
    '<div class="r"><label>Test site</label><select id="cl-site"></select></div>'+
    '<div class="btns"><button class="pri" id="cl-save">Save &amp; reconnect</button><button id="cl-test">Test WARNORD → CMDR</button></div>'+
    '<div class="btns"><button id="cl-status">Push STATUS</button><button id="cl-open">Open CMDR app</button></div>'+
    '<div id="cl-log"></div>';
  document.body.appendChild(panel);
  var sel=$('cl-site');C.SITES.forEach(function(s){var o=document.createElement('option');o.value=s.id;o.textContent=s.name;sel.appendChild(o);});sel.value='nb-sd';
  function fill(){var c=bus.cfg();$('cl-transport').value=c.transport;$('cl-repo').value=c.repo;$('cl-branch').value=c.branch;$('cl-path').value=c.path;$('cl-token').value=c.token;$('cl-poll').value=c.poll;ghVis();}
  function ghVis(){var gh=$('cl-transport').value==='github';document.querySelectorAll('#cl-panel .cl-gh').forEach(function(e){e.style.display=gh?'':'none';});}
  $('cl-transport').onchange=ghVis;
  $('cl-save').onclick=function(){bus.configure({transport:$('cl-transport').value,repo:$('cl-repo').value.trim(),branch:$('cl-branch').value.trim()||'main',path:$('cl-path').value.trim()||'data/bus.json',token:$('cl-token').value.trim(),poll:parseInt($('cl-poll').value,10)||5,node:'admin',site:'*'});C.audit('SETTINGS_CMDR_LINK','transport',$('cl-transport').value);toast('CMDR link: '+$('cl-transport').value,'ok');bus.publish('HELLO',{node:'admin',app:'ie-SRA ADMIN'});};
  $('cl-test').onclick=function(){
    var s=C.SITE[sel.value]; if(!s)return;
    var rec={ts:Date.now(),site:s.id,siteName:s.name,code:'TEST-'+String(Date.now()).slice(-4),test:true,kind:'TEST',msg:'Test warning order released by System Admin to CMDR mobile — no operational outage. Acknowledge on the phone to close the loop.',channels:'Base Commander: mobile+dash'};
    C.logWO(rec);C.audit('TEST_WARNING_ORDER',s.name,'CMDR link test');toast('Test warning order → CMDR ('+s.name+')','ok');
    if(typeof admPaintRouting==='function'&&$('overlay-adm-routing')&&$('overlay-adm-routing').classList.contains('visible'))try{admPaintRouting();}catch(e){}
    if(typeof admPaintStrip==='function')try{admPaintStrip();}catch(e){}
  };
  $('cl-status').onclick=function(){sendStatus(sel.value);toast('STATUS → CMDR','ok');};
  $('cl-open').onclick=function(){window.open('cmdr/index.html','ie-sra-cmdr','width=430,height=900');};
  function paintPanel(){
    if(!panel.classList.contains('on'))return;
    var ks=Object.keys(peers);$('cl-peers').textContent=ks.length?ks.map(function(k){return '● '+(peers[k].name||'CMDR')+' @ '+k+' ('+hhmm(peers[k].ts)+')';}).join('  '):'No CMDR device has said hello yet.';
    $('cl-log').innerHTML=EV.map(esc).join('<br>')||'—';
  }
  bus.onStatus(function(st){chip.className=st.connected?(st.pending?'warn':'on'):'';$('cl-txt').textContent='CMDR LINK · '+(st.transport==='off'?'OFF':st.connected?(st.transport==='github'?'GITHUB':'LIVE'):(st.error?'ERR':'—'));if(st.error)chip.title=st.error;});
  fill();bus.start();
  bus.replay(function(env){if(env.type==='HELLO'&&env.from==='cmdr')peers[env.site||'?']={name:env.payload&&env.payload.commander,ts:env.ts};});
  setTimeout(function(){bus.publish('HELLO',{node:'admin',app:'ie-SRA ADMIN'});},600);
  /* periodic health push to every site that has said hello (ADM-04 sync) */
  setInterval(function(){Object.keys(peers).forEach(function(site){if(C.SITE[site]&&peers[site].ts>Date.now()-864e5)sendStatus(site);});},60000);
  window.CMDR_LINK={bus:bus,sendStatus:sendStatus,snapshot:snapshot,events:function(){return EV.slice();},peers:function(){return peers;}};
})();
