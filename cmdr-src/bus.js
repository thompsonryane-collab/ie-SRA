/* ie-SRA bus — one envelope, three transports.
   Envelope: {id, type, ts, from, to, site, payload}
   type: WARNORD | ACK | MSG | STATUS | HELLO
   Transports: 'broadcast' (BroadcastChannel + localStorage, same origin)
               'github'    (GitHub Contents API, cross-device demo)
               'off'
   Adapter contract: start(), stop(), send(env). Incoming goes to _recv(env). */
window.SRABus=(function(){
  var NODE='__NODE__';
  var CFG_KEY='sra_bus_cfg_'+NODE, LOG_KEY='sra_bus_log', SEEN_KEY='sra_bus_seen_'+NODE;
  var CH_NAME='ie-sra-bus';
  var DEF={transport:'broadcast', node:NODE, site:'nb-sd', repo:'thompsonryane-collab/ie-SRA', branch:'main', path:'data/bus.json', token:'', poll:5};
  function ls(k,d){try{var v=localStorage.getItem(k);return v?JSON.parse(v):d;}catch(e){return d;}}
  function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  var cfg=Object.assign({},DEF,ls(CFG_KEY,{}));
  var subs=[], statusSubs=[], seen=ls(SEEN_KEY,{}), adapter=null;
  var st={transport:cfg.transport, connected:false, lastSync:0, error:'', pending:0};
  function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,8);}
  function setStatus(p){Object.assign(st,p);statusSubs.forEach(function(f){try{f(st);}catch(e){}});}
  function remember(id){seen[id]=Date.now();var ks=Object.keys(seen);if(ks.length>600){ks.sort(function(a,b){return seen[a]-seen[b];}).slice(0,200).forEach(function(k){delete seen[k];});}lsSet(SEEN_KEY,seen);}
  function appendLog(env){var l=ls(LOG_KEY,[]);if(l.some(function(x){return x.id===env.id;}))return;l.push(env);if(l.length>300)l.splice(0,l.length-300);lsSet(LOG_KEY,l);}
  function _recv(env,replay){
    if(!env||!env.id||!env.type)return;
    if(env.from===cfg.node)return;
    if(seen[env.id])return;
    remember(env.id); appendLog(env);
    subs.forEach(function(f){try{f(env,!!replay);}catch(e){console.error('bus sub',e);}});
  }

  /* ── broadcast adapter ── */
  function Broadcast(){
    var bc=null, onStorage;
    return {
      start:function(){
        try{bc=new BroadcastChannel(CH_NAME);bc.onmessage=function(e){_recv(e.data);};}catch(e){bc=null;}
        onStorage=function(e){if(e.key==='sra_bus_ping'&&e.newValue){try{_recv(JSON.parse(e.newValue));}catch(x){}}};
        window.addEventListener('storage',onStorage);
        setStatus({connected:true,error:'',lastSync:Date.now()});
      },
      stop:function(){if(bc){bc.close();bc=null;}window.removeEventListener('storage',onStorage);},
      send:function(env){
        appendLog(env);
        if(bc)bc.postMessage(env);
        try{localStorage.setItem('sra_bus_ping',JSON.stringify(env));}catch(e){}
        setStatus({lastSync:Date.now()});
        return Promise.resolve(true);
      }
    };
  }

  /* ── github contents adapter ── */
  function GitHub(){
    var timer=null, sha=null, busy=false, queue=[];
    function url(){return 'https://api.github.com/repos/'+cfg.repo+'/contents/'+cfg.path+'?ref='+encodeURIComponent(cfg.branch)+'&t='+Date.now();}
    function hdr(){var h={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};if(cfg.token)h['Authorization']='Bearer '+cfg.token;return h;}
    function b64dec(s){try{return new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\n/g,'')),function(c){return c.charCodeAt(0);}));}catch(e){return atob(s.replace(/\n/g,''));}}
    function b64enc(s){var b=new TextEncoder().encode(s),o='';for(var i=0;i<b.length;i++)o+=String.fromCharCode(b[i]);return btoa(o);}
    function read(){
      return fetch(url(),{headers:hdr(),cache:'no-store'}).then(function(r){
        if(r.status===404)return {sha:null,doc:{v:1,messages:[]}};
        if(!r.ok)throw new Error('GitHub read '+r.status);
        return r.json().then(function(j){var doc;try{doc=JSON.parse(b64dec(j.content));}catch(e){doc={v:1,messages:[]};}return {sha:j.sha,doc:doc};});
      });
    }
    function write(doc,curSha){
      var body={message:'bus: '+cfg.node+' '+new Date().toISOString(),content:b64enc(JSON.stringify(doc)),branch:cfg.branch};
      if(curSha)body.sha=curSha;
      return fetch('https://api.github.com/repos/'+cfg.repo+'/contents/'+cfg.path,{method:'PUT',headers:Object.assign({'Content-Type':'application/json'},hdr()),body:JSON.stringify(body)})
        .then(function(r){if(r.status===409||r.status===422)return {conflict:true};if(!r.ok)throw new Error('GitHub write '+r.status);return r.json().then(function(j){return {sha:j.content&&j.content.sha};});});
    }
    function poll(){
      if(busy)return;busy=true;
      read().then(function(res){sha=res.sha;(res.doc.messages||[]).forEach(function(m){_recv(m);});setStatus({connected:true,error:'',lastSync:Date.now()});})
        .catch(function(e){setStatus({connected:false,error:String(e.message||e)});})
        .then(function(){busy=false;flush();});
    }
    function flush(){
      if(busy||!queue.length)return;busy=true;
      var batch=queue.splice(0,queue.length);setStatus({pending:queue.length});
      var attempt=0;
      (function tryWrite(){
        read().then(function(res){
          var doc=res.doc;doc.messages=(doc.messages||[]).concat(batch);if(doc.messages.length>200)doc.messages=doc.messages.slice(-200);doc.updated=Date.now();doc.v=1;
          (doc.messages||[]).forEach(function(m){_recv(m);});
          return write(doc,res.sha);
        }).then(function(w){
          if(w.conflict){if(++attempt<4)return setTimeout(tryWrite,300*attempt);throw new Error('GitHub write conflict');}
          sha=w.sha;setStatus({connected:true,error:'',lastSync:Date.now(),pending:queue.length});busy=false;if(queue.length)flush();
        }).catch(function(e){setStatus({connected:false,error:String(e.message||e),pending:queue.length});busy=false;queue=batch.concat(queue);});
      })();
    }
    return {
      start:function(){if(!cfg.token)setStatus({connected:false,error:'No GitHub token'});poll();timer=setInterval(poll,Math.max(3,cfg.poll|0)*1000);},
      stop:function(){clearInterval(timer);timer=null;},
      send:function(env){appendLog(env);queue.push(env);setStatus({pending:queue.length});flush();return Promise.resolve(true);}
    };
  }

  function Off(){return {start:function(){setStatus({connected:false,error:'Transport off'});},stop:function(){},send:function(){return Promise.resolve(false);}};}

  function build(){return cfg.transport==='github'?GitHub():cfg.transport==='off'?Off():Broadcast();}
  var api={
    cfg:function(){return Object.assign({},cfg);},
    configure:function(o){Object.assign(cfg,o||{});lsSet(CFG_KEY,cfg);if(adapter){adapter.stop();adapter=build();setStatus({transport:cfg.transport,connected:false,error:'',pending:0});adapter.start();}return api;},
    start:function(){if(!adapter){adapter=build();setStatus({transport:cfg.transport});adapter.start();}return api;},
    stop:function(){if(adapter){adapter.stop();adapter=null;}setStatus({connected:false});},
    publish:function(type,payload,extra){
      var env=Object.assign({id:uid(),type:type,ts:Date.now(),from:cfg.node,to:'*',site:cfg.site,payload:payload||{}},extra||{});
      remember(env.id);
      return (adapter||build()).send(env).then(function(){return env;});
    },
    subscribe:function(f){subs.push(f);return function(){subs=subs.filter(function(x){return x!==f;});};},
    onStatus:function(f){statusSubs.push(f);f(st);return function(){statusSubs=statusSubs.filter(function(x){return x!==f;});};},
    status:function(){return Object.assign({},st);},
    replay:function(f){ls(LOG_KEY,[]).forEach(function(env){try{f(env,true);}catch(e){}});},
    log:function(){return ls(LOG_KEY,[]);},
    reset:function(){seen={};lsSet(SEEN_KEY,seen);lsSet(LOG_KEY,[]);},
    ghPut:function(path,text,message){
      var h={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'};if(cfg.token)h['Authorization']='Bearer '+cfg.token;
      var base='https://api.github.com/repos/'+cfg.repo+'/contents/'+path;
      function enc(s){var b=new TextEncoder().encode(s),o='';for(var i=0;i<b.length;i++)o+=String.fromCharCode(b[i]);return btoa(o);}
      function once(){return fetch(base+'?ref='+encodeURIComponent(cfg.branch)+'&t='+Date.now(),{headers:h,cache:'no-store'}).then(function(r){return r.status===404?null:r.ok?r.json():Promise.reject(new Error('GitHub read '+r.status));})
        .then(function(j){var body={message:message||('update '+path),content:enc(text),branch:cfg.branch};if(j&&j.sha)body.sha=j.sha;return fetch(base,{method:'PUT',headers:h,body:JSON.stringify(body)});});}
      return once().then(function(r){if(r.status===409||r.status===422)return once();return r;}).then(function(r){if(!r.ok)throw new Error('GitHub write '+r.status);return r.json();});
    },
    _recv:_recv
  };
  return api;
})();
