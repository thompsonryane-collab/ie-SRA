/* ══ ADM-09 COMMS LOG — ledger of every ADMIN ↔ CMDR envelope ══ */
(function(){
  var C=window.ADMIN_CORE, bus=window.SRABus; if(!C||!bus)return;
  var $=function(id){return document.getElementById(id);};
  var KEY='adm_comms_log', CAP=3000;
  function ls(k,d){try{var v=localStorage.getItem(k);return v?JSON.parse(v):d;}catch(e){return d;}}
  function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  function esc(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function tsZ(ts){var d=new Date(ts);return d.toISOString().slice(0,10)+' '+d.toISOString().slice(11,19)+'Z';}
  function mini(l,v,c,s){return '<div class="adm-mini"><div class="l">'+l+'</div><div class="v" style="color:'+(c||'#cce0f2')+'">'+v+'</div>'+(s?'<div class="l" style="margin-top:2px;text-transform:none;letter-spacing:0">'+s+'</div>':'')+'</div>';}
  function download(name,text,mime){try{var b=new Blob([text],{type:mime||'text/plain'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},800);}catch(e){}}
  function toast(m,t){if(typeof hubToast==='function')hubToast(m,t||'ok',3200);}
  var TYPE_COLOR={WARNORD:'#e05555',ACK:'#4db88a',MSG:'#18d4f8',STATUS:'#d4a05a',HELLO:'#c3aaf8'};
  var list=ls(KEY,[]); var idx={}; list.forEach(function(r){idx[r.id]=r;});
  function save(){if(list.length>CAP)list.splice(0,list.length-CAP);lsSet(KEY,list);}
  function paintCard(){var e=$('card-comms-n');if(e)e.textContent=list.length+' Envelope'+(list.length===1?'':'s');}
  function preview(env){var p=env.payload||{};return p.code?p.code+(p.msg?' · '+p.msg:''):p.text||p.commander||p.siteName||p.app||'';}
  function peerOf(env){var p=env.payload||{};return p.by||p.commander||(env.from==='admin'?'ADMIN':'CMDR');}
  function record(env,dir,transport){
    if(!env||!env.id||idx[env.id])return idx[env.id];
    var now=Date.now();
    var r={id:env.id,ts:env.ts,rx:now,dir:dir,type:env.type,site:env.site||(env.payload&&env.payload.site)||'*',peer:peerOf(env),transport:transport||bus.cfg().transport,
           bytes:JSON.stringify(env).length,latency:dir==='IN'?Math.max(0,now-env.ts):null,rtt:null,code:(env.payload&&env.payload.code)||'',preview:String(preview(env)).slice(0,160),status:dir==='OUT'?(env.type==='WARNORD'?'awaiting ack':'sent'):'received'};
    if(env.type==='ACK'&&r.code){var wo=list.filter(function(x){return x.type==='WARNORD'&&x.code===r.code;})[0];if(wo){wo.status='acknowledged';wo.rtt=env.ts-wo.ts;wo.ackBy=r.peer;r.rtt=wo.rtt;}}
    list.push(r);idx[r.id]=r;save();paintCard();
    if($('overlay-adm-comms')&&$('overlay-adm-comms').classList.contains('visible'))try{admPaintComms();}catch(e){}
    try{if(typeof admPaintStrip==='function')admPaintStrip();}catch(e){}
    return r;
  }
  /* tap the bus: outbound via publish wrapper, inbound via subscribe */
  var _publish=bus.publish;
  bus.publish=function(type,payload,extra){return _publish.call(bus,type,payload,extra).then(function(env){record(env,'OUT');return env;});};
  bus.subscribe(function(env,replay){record(env,'IN');});
  bus.replay(function(env){record(env,env.from==='admin'?'OUT':'IN');});

  /* ── overlay paint ── */
  var ST={sort:{k:'ts',d:-1}};
  function filtered(){
    var q=($('cm-q').value||'').toLowerCase(), dir=$('cm-dir').value, type=$('cm-type').value, site=$('cm-site').value, win=$('cm-win').value;
    var since=win==='1h'?Date.now()-36e5:win==='24h'?Date.now()-864e5:win==='7d'?Date.now()-6048e5:0;
    return list.filter(function(r){
      if(r.ts<since)return false; if(dir&&r.dir!==dir)return false; if(type&&r.type!==type)return false; if(site&&r.site!==site)return false;
      if(q&&(r.type+' '+r.site+' '+r.peer+' '+r.code+' '+r.preview+' '+r.status).toLowerCase().indexOf(q)<0)return false; return true;
    }).sort(function(a,b){var k=ST.sort.k,d=ST.sort.d;var x=a[k],y=b[k];if(x==null)x=-1;if(y==null)y=-1;return (x>y?1:x<y?-1:0)*d;});
  }
  window.cmSort=function(k){if(ST.sort.k===k)ST.sort.d*=-1;else ST.sort={k:k,d:k==='ts'||k==='rx'?-1:1};admPaintComms();};
  function fmtMs(ms){return ms==null?'—':ms<1000?ms+' ms':ms<60000?(ms/1000).toFixed(1)+' s':Math.round(ms/60000)+' min';}
  function avg(a){return a.length?Math.round(a.reduce(function(s,x){return s+x;},0)/a.length):null;}
  window.admCommsStats=function(){
    var day=list.filter(function(r){return r.ts>Date.now()-864e5;});
    var wo=list.filter(function(r){return r.type==='WARNORD'&&r.dir==='OUT';});
    var acked=wo.filter(function(r){return r.status==='acknowledged';});
    var peers={};list.forEach(function(r){if(r.dir==='IN')peers[r.peer+'@'+r.site]=r.ts;});
    return {total:list.length,day:day.length,inn:day.filter(function(r){return r.dir==='IN';}).length,out:day.filter(function(r){return r.dir==='OUT';}).length,
      latency:avg(list.filter(function(r){return r.latency!=null&&r.type!=='STATUS';}).map(function(r){return r.latency;})),
      rtt:avg(acked.map(function(r){return r.rtt;})),wo:wo.length,acked:acked.length,unacked:wo.length-acked.length,
      devices:Object.keys(peers).filter(function(k){return peers[k]>Date.now()-864e5;}).length,
      unackedList:wo.filter(function(r){return r.status!=='acknowledged';}).map(function(r){return r.code+' ('+r.site+', '+Math.round((Date.now()-r.ts)/60000)+' min)';}).slice(0,8)};
  };
  window.admPaintComms=function(){
    var sel=$('cm-site'); if(sel&&sel.options.length<=1){var seen={};list.forEach(function(r){if(r.site&&r.site!=='*'&&!seen[r.site]){seen[r.site]=1;var o=document.createElement('option');o.value=r.site;var s=C.SITE[r.site];o.textContent=s?s.name:r.site;sel.appendChild(o);}});}
    var rows=filtered(), s=admCommsStats();
    $('cm-strip').innerHTML=mini('Envelopes',s.total,'#ffffff',s.day+' in 24h')+mini('In / Out (24h)',s.inn+' / '+s.out,'#18d4f8')+mini('Avg delivery latency',fmtMs(s.latency),'#29d3c8',bus.cfg().transport)+mini('Avg ack RTT',fmtMs(s.rtt),'#4db88a',s.acked+' of '+s.wo+' WOs acked')+mini('Unacked WARNORDs',s.unacked,s.unacked?'#e05555':'#4db88a')+mini('Devices (24h)',s.devices,'#c3aaf8');
    var cols=[['ts','Sent (Z)'],['dir','Dir'],['type','Type'],['site','Site'],['peer','Peer'],['transport','Transport'],['latency','Latency'],['rtt','Ack RTT'],['status','Status'],['preview','Payload']];
    $('cm-head').innerHTML='<tr>'+cols.map(function(c){var on=ST.sort.k===c[0];return '<th style="cursor:pointer" onclick="cmSort(\''+c[0]+'\')">'+c[1]+(on?(ST.sort.d>0?' ▲':' ▼'):'')+'</th>';}).join('')+'</tr>';
    $('cm-body').innerHTML=rows.length?rows.slice(0,400).map(function(r){var c=TYPE_COLOR[r.type]||'#cce0f2';var sc=r.status==='acknowledged'?'#4db88a':r.status==='awaiting ack'?'#e8a33d':'#8fb0d0';
      return '<tr><td style="font-family:\'Share Tech Mono\',monospace;font-size:9.5px;color:#6e90b0">'+tsZ(r.ts)+'</td><td style="color:'+(r.dir==='IN'?'#18d4f8':'#d4a05a')+';font-family:\'Share Tech Mono\',monospace;font-size:9.5px">'+(r.dir==='IN'?'◀ IN':'OUT ▶')+'</td><td><span class="adm-pill" style="color:'+c+';border-color:'+c+'">'+r.type+'</span></td><td>'+esc(r.site)+'</td><td>'+esc(r.peer)+'</td><td style="color:#6e90b0">'+esc(r.transport)+'</td><td>'+fmtMs(r.latency)+'</td><td>'+fmtMs(r.rtt)+'</td><td style="color:'+sc+'">'+esc(r.status)+(r.ackBy?' · '+esc(r.ackBy):'')+'</td><td style="color:#8fb0d0;white-space:normal;max-width:420px">'+esc(r.preview)+'</td></tr>';}).join('')+(rows.length>400?'<tr><td colspan="10" class="adm-empty">showing 400 of '+rows.length+'</td></tr>':''):'<tr><td colspan="10" class="adm-empty">No envelopes'+(list.length?' match the filter.':' yet — open the CMDR app or send a test warning order from the CMDR LINK chip.')+'</td></tr>';
  };
  window.admExportComms=function(fmt){
    var rows=filtered();
    if(fmt==='json')return download('ie-sra-comms-log.json',JSON.stringify({exported:new Date().toISOString(),stats:admCommsStats(),rows:rows},null,1),'application/json');
    var h=['sent_z','received_z','dir','type','site','peer','transport','latency_ms','ack_rtt_ms','status','ack_by','code','bytes','payload'];
    download('ie-sra-comms-log.csv',h.join(',')+'\n'+rows.map(function(r){return [tsZ(r.ts),tsZ(r.rx),r.dir,r.type,r.site,r.peer,r.transport,r.latency==null?'':r.latency,r.rtt==null?'':r.rtt,r.status,r.ackBy||'',r.code,r.bytes,r.preview].map(function(v){return '"'+String(v).replace(/"/g,'""')+'"';}).join(',');}).join('\n'),'text/csv');
  };
  window.admPushComms=function(){
    var c=bus.cfg(); if(!c.token||!c.repo){toast('Set a GitHub repo + token in the CMDR LINK chip first','warn');return;}
    toast('Pushing comms log to '+c.repo+'/data/comms-log.json …','ok');
    bus.ghPut('data/comms-log.json',JSON.stringify({exported:new Date().toISOString(),stats:admCommsStats(),rows:list},null,1),'comms log '+new Date().toISOString())
      .then(function(){toast('Comms log pushed to repo','ok');C.audit('COMMS_LOG_PUSH','data/comms-log.json',list.length+' rows');})
      .catch(function(e){toast('Push failed: '+(e.message||e),'warn');});
  };
  window.admClearComms=function(){if(!confirm('Clear the comms ledger ('+list.length+' envelopes)? Audit entries are kept.'))return;list=[];idx={};save();C.audit('COMMS_LOG_CLEAR','ledger','');admPaintComms();};

  /* open/close routing + strip repaint */
  var _open=window.openApp;
  window.openApp=function(id){_open(id);if(id==='overlay-adm-comms')try{admPaintComms();}catch(e){console.warn('comms paint',e);}};
  /* ARIA: append comms state to the live context */
  if(typeof window.admAriaContext==='function'){var _ctx=window.admAriaContext;window.admAriaContext=function(){var s=admCommsStats();return _ctx()+'- ADM-09 COMMS LOG (ADMIN↔CMDR mobile bus, transport '+bus.cfg().transport+'): '+s.total+' envelopes logged, '+s.day+' in last 24h ('+s.inn+' in / '+s.out+' out). Avg delivery latency '+fmtMs(s.latency)+', avg commander ack round-trip '+fmtMs(s.rtt)+'. Warning orders sent to mobile: '+s.wo+', acknowledged '+s.acked+', unacknowledged '+s.unacked+(s.unackedList.length?' ('+s.unackedList.join('; ')+')':'')+'. Mobile devices heard from in 24h: '+s.devices+'.\n';};}
  paintCard();
  window.ADM_COMMS={list:function(){return list.slice();},stats:admCommsStats,record:record};
})();
