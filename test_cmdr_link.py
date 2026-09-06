#!/usr/bin/env python3
"""test_cmdr_link.py — end-to-end ADMIN <-> CMDR bus tests (Playwright, local http server)."""
import json, base64, threading, http.server, functools, pathlib, sys, time
from playwright.sync_api import sync_playwright

DIST = pathlib.Path(__file__).parent / 'dist'
PORT = 8765
BASE = f'http://127.0.0.1:{PORT}'
BASELINE_ERR = ('Leaflet', 'tile', 'favicon', 'net::ERR', 'Failed to load resource')

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

def errs_of(page):
    out = []
    page.on('console', lambda m: out.append(m.text) if m.type == 'error' and not any(b in m.text for b in BASELINE_ERR) else None)
    page.on('pageerror', lambda e: out.append('PAGEERROR ' + str(e)))
    return out

def wait_for(fn, timeout=8, msg='condition'):
    t = time.time()
    while time.time() - t < timeout:
        try:
            if fn(): return True
        except Exception: pass
        time.sleep(0.15)
    raise AssertionError('timeout: ' + msg)

def tier1(b):
    ctx = b.new_context(viewport={'width': 1400, 'height': 900})
    ctx.route('**/*.{png,jpg}', lambda r: r.abort())
    ctx.route('https://*.tile.*/**', lambda r: r.abort())
    ctx.route('**/unpkg.com/**', lambda r: r.abort())
    ctx.route('**/cdnjs.cloudflare.com/**', lambda r: r.abort())
    admin = ctx.new_page(); ae = errs_of(admin)
    admin.goto(BASE + '/ie-SRS-ADMIN.html', wait_until='domcontentloaded'); admin.wait_for_timeout(2500)
    assert admin.evaluate('!!window.ADMIN_CORE && !!window.SRABus && !!window.CMDR_LINK'), 'admin link not initialised'
    assert admin.evaluate("document.getElementById('cl-chip')!==null")
    cmdr = ctx.new_page(); cmdr.set_viewport_size({'width': 393, 'height': 852}); ce = errs_of(cmdr)
    cmdr.add_init_script("localStorage.setItem('sra_bus_cfg_cmdr',JSON.stringify({transport:'broadcast',node:'cmdr',site:'nb-sd'}));")
    cmdr.goto(BASE + '/cmdr/index.html', wait_until='domcontentloaded'); cmdr.wait_for_timeout(1200)
    assert cmdr.evaluate('!!window.CMDR && window.SRABus.status().connected'), 'cmdr not connected'

    # HELLO from CMDR -> ADMIN records peer, replies STATUS
    wait_for(lambda: admin.evaluate("Object.keys(window.CMDR_LINK.peers()).length>0"), msg='admin saw HELLO')
    wait_for(lambda: cmdr.evaluate("!!window.CMDR.state().status"), msg='cmdr got STATUS')
    assert cmdr.evaluate("window.CMDR.state().status.siteName")=='NB San Diego'
    audit = admin.evaluate("window.ADMIN_CORE.listAudit().map(a=>a.action)")
    assert 'CMDR_HELLO' in audit, audit[:5]

    # WARNORD: admin test dispatch -> cmdr card
    admin.evaluate("admCmdrTest('nb-sd')")
    wait_for(lambda: cmdr.evaluate("Object.keys(window.CMDR.state().warnords).length>0"), msg='cmdr got WARNORD')
    code = cmdr.evaluate("Object.keys(window.CMDR.state().warnords)[0]")
    assert code.startswith('TEST-'), code
    assert cmdr.evaluate(f"document.querySelector('.warn[data-code=\"{code}\"] .btn.pri')!==null"), 'ack button missing'
    cmdr.screenshot(path='qa_cmdr_warnord.png')

    # ACK: cmdr -> admin audit + WO record
    cmdr.evaluate(f"document.querySelector('.warn[data-code=\"{code}\"] .btn.pri').click()")
    wait_for(lambda: admin.evaluate("window.ADMIN_CORE.listAudit().some(a=>a.action==='CMDR_ACK')"), msg='admin audit CMDR_ACK')
    wo = admin.evaluate(f"window.ADMIN_CORE.listWO().find(w=>w.code==='{code}')")
    assert wo and wo.get('ack') and wo['ack']['by'], wo
    assert cmdr.evaluate(f"document.querySelector('.warn[data-code=\"{code}\"]').classList.contains('acked')")

    # MSG both ways
    cmdr.evaluate("go('msgs');document.getElementById('mtext').value='Convene EOC in 15 minutes.';sendMsg();")
    wait_for(lambda: admin.evaluate("window.ADMIN_CORE.listMsgs().some(m=>/Convene EOC/.test(m.text)&&/^CMDR/.test(m.from))"), msg='admin got MSG')
    admin.evaluate("window.ADMIN_CORE.sendMsg('site:nb-sd','Copy CO. Utility crew on site, ETR 30 min.','sysadmin')")
    wait_for(lambda: cmdr.evaluate("window.CMDR.state().msgs.some(m=>/ETR 30/.test(m.text)&&!m.mine)"), msg='cmdr got MSG')
    cmdr.screenshot(path='qa_cmdr_msgs.png')

    # all-hands round trip: admin broadcast → phone reply lands in #all-hands, not site channel
    admin.evaluate("window.ADMIN_CORE.sendMsg('all','ADMIN NOTICE: comms check, all commanders acknowledge.','sysadmin')")
    wait_for(lambda: cmdr.evaluate("window.CMDR.state().msgs.some(m=>/comms check/.test(m.text)&&m.ch==='all')"), msg='phone got all-hands')
    assert cmdr.evaluate("window.CMDR.state().replyCh")=='all'
    cmdr.evaluate("go('msgs');document.getElementById('mtext').value='NBSD acknowledges comms check.';sendMsg();")
    wait_for(lambda: admin.evaluate("window.ADMIN_CORE.listMsgs().some(m=>/NBSD acknowledges/.test(m.text)&&m.ch==='all')"), msg='reply in all-hands')
    assert not admin.evaluate("window.ADMIN_CORE.listMsgs().some(m=>/NBSD acknowledges/.test(m.text)&&m.ch!=='all')")
    # then a site message from admin flips the phone back to the site channel
    admin.evaluate("window.ADMIN_CORE.sendMsg('site:nb-sd','Site-only: crew ETA 20.','sysadmin')")
    wait_for(lambda: cmdr.evaluate("window.CMDR.state().replyCh==='site:nb-sd'"), msg='reply channel back to site')
    cmdr.evaluate("document.getElementById('mtext').value='Copy site.';sendMsg();")
    wait_for(lambda: admin.evaluate("window.ADMIN_CORE.listMsgs().some(m=>/Copy site/.test(m.text)&&m.ch==='site:nb-sd')"), msg='site reply routed')
    cmdr.screenshot(path='qa_cmdr_allhands.png')

    # ADM-08 / routing path: any C.logWO publishes
    admin.evaluate("window.ADMIN_CORE.logWO({ts:Date.now(),site:'nb-sd',siteName:'NB San Diego',code:'WO-LIVE-1',test:false,kind:'LIVE',msg:'Pier 8 feeder loss — shore power to DDG berth down.',channels:'Base Commander: mobile'})")
    wait_for(lambda: cmdr.evaluate("!!window.CMDR.state().warnords['WO-LIVE-1']"), msg='cmdr got live WARNORD')
    assert cmdr.evaluate("document.querySelectorAll('#outage-list .row').length")>=1
    # other-site WARNORD must be filtered
    admin.evaluate("window.ADMIN_CORE.logWO({ts:Date.now(),site:'nas-lemoore',siteName:'NAS Lemoore',code:'WO-OTHER',test:false,msg:'x',channels:''})")
    cmdr.wait_for_timeout(600)
    assert not cmdr.evaluate("!!window.CMDR.state().warnords['WO-OTHER']"), 'site filter failed'

    # Health tab mirrors ADM-04 snapshot
    st = cmdr.evaluate("window.CMDR.state().status")
    for k in ('health','primaryInst','secondaryInst','fm','backup','enterprise'): assert k in st, k
    adm_h = admin.evaluate("window.ADMIN_CORE.health(window.ADMIN_CORE.SITE['nb-sd'])")
    assert st['health']==adm_h and st['enterprise']['instances']==140, (st['health'], adm_h)
    cmdr.evaluate("go('health')"); cmdr.wait_for_timeout(200)
    assert cmdr.evaluate("document.querySelectorAll('#h-inst .irow').length")==2 and cmdr.evaluate("document.querySelectorAll('#h-users .irow').length")==2
    assert cmdr.evaluate("document.querySelector('#h-hero .st').textContent.trim()")==adm_h
    cmdr.screenshot(path='qa_cmdr_health.png')
    # ADM-10 CMDR Mobile overlay
    admin.evaluate("enterHub()"); admin.wait_for_timeout(1200)
    admin.evaluate("document.getElementById('cl-chip').click()"); admin.wait_for_timeout(800)
    assert admin.evaluate("document.getElementById('overlay-adm-cmdr').classList.contains('visible')"), 'chip did not open ADM-10'
    assert admin.evaluate("document.querySelectorAll('#cx-peers .cm-peer').length")>=1
    assert admin.evaluate("document.querySelectorAll('#cx-unacked .cm-peer').length")>=1
    assert admin.evaluate("document.getElementById('cx-url').textContent").endswith('/cmdr/')
    assert admin.evaluate("document.getElementById('cx-frame')")==None
    assert admin.evaluate("document.querySelectorAll('#cx-acked .cm-peer').length")>=1
    admin.evaluate("document.getElementById('card-cmdr-peers')"); assert admin.evaluate("document.getElementById('card-cmdr-unacked').textContent")!='0 unacked'
    admin.screenshot(path='qa_admin_cmdr.png')
    admin.evaluate("closeApp('overlay-adm-cmdr')")
    # ADM-02 live presence: only this admin + CMDR devices
    lp = admin.evaluate("window.admLivePresence()")
    assert lp['admins']==1 and lp['mobile']==1 and lp['total']==2, lp
    admin.evaluate("enterHub()"); admin.wait_for_timeout(600); admin.evaluate("openApp('overlay-adm-msg')"); admin.wait_for_timeout(500)
    assert admin.evaluate("document.querySelectorAll('#am-users .adm-usr').length")==2
    assert admin.evaluate("document.getElementById('am-online-badge').textContent")=='2 ONLINE · LIVE'
    assert 'CMDR MOBILE' in admin.evaluate("document.getElementById('am-users').textContent")
    admin.screenshot(path='qa_presence.png', clip={'x':0,'y':0,'width':520,'height':520})
    admin.evaluate("closeApp('overlay-adm-msg')")
    assert admin.evaluate("[...document.querySelectorAll('#adm-strip .adm-kpi')].some(k=>/users online/i.test(k.textContent)&&/1 admin/.test(k.textContent))")
    # ADM-09 comms ledger
    st = admin.evaluate("window.ADM_COMMS.stats()")
    assert st['wo'] >= 2 and st['acked'] >= 1 and st['rtt'] is not None and st['unacked'] >= 1, st
    led = admin.evaluate("window.ADM_COMMS.list()")
    kinds = {(r['dir'], r['type']) for r in led}
    for k in [('OUT','WARNORD'),('IN','ACK'),('IN','MSG'),('OUT','MSG'),('IN','HELLO'),('OUT','STATUS'),('OUT','HELLO')]: assert k in kinds, (k, kinds)
    acked = [r for r in led if r['type']=='WARNORD' and r['code']==code][0]
    assert acked['status']=='acknowledged' and acked['rtt']>=0 and acked['ackBy'], acked
    assert 'ADM-09 COMMS LOG' in admin.evaluate("window.admAriaContext()")
    assert admin.evaluate("document.getElementById('card-comms-n').textContent")!='0 Envelopes'
    admin.evaluate("enterHub()"); admin.wait_for_timeout(1200)
    admin.evaluate("openApp('overlay-adm-comms')"); admin.wait_for_timeout(600)
    assert admin.evaluate("document.querySelectorAll('#cm-body tr').length")>=7
    admin.screenshot(path='qa_admin_comms.png')
    admin.evaluate("document.getElementById('cm-type').value='WARNORD';admPaintComms()")
    assert admin.evaluate("[...document.querySelectorAll('#cm-body tr')].every(t=>/WARNORD/.test(t.textContent))")
    admin.evaluate("closeApp('overlay-adm-comms')")
    # ledger survives reload
    admin.reload(wait_until='domcontentloaded'); admin.wait_for_timeout(2500)
    assert admin.evaluate("window.ADM_COMMS.stats().total") >= len(led), 'ledger lost on reload'

    # reload CMDR: replay restores state
    cmdr.reload(wait_until='domcontentloaded'); cmdr.wait_for_timeout(900)
    assert cmdr.evaluate(f"window.CMDR.state().warnords['{code}'].ack.by"), 'ack lost on reload'
    cmdr.evaluate("go('dash')"); cmdr.screenshot(path='qa_cmdr_dash.png')
    admin.screenshot(path='qa_admin_chip.png', clip={'x': 1000, 'y': 700, 'width': 400, 'height': 200})
    admin.evaluate("document.getElementById('cl-chip').click()"); admin.wait_for_timeout(200)
    admin.screenshot(path='qa_admin_panel.png', clip={'x': 1000, 'y': 380, 'width': 400, 'height': 520})
    assert not ae, 'admin console errors: ' + '\n'.join(ae[:5])
    assert not ce, 'cmdr console errors: ' + '\n'.join(ce[:5])
    ctx.close(); print('tier1 broadcast: PASS')

def tier2(b):
    """Mock api.github.com contents endpoint; two isolated contexts (no shared storage) talk only via the mock."""
    store = {'sha': 'sha0', 'content': json.dumps({'v': 1, 'messages': []}), 'conflict_once': True, 'puts': 0, 'gets': 0}
    def handler(route, request):
        if request.method == 'GET':
            store['gets'] += 1
            body = {'sha': store['sha'], 'content': base64.b64encode(store['content'].encode()).decode()}
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        if request.method == 'PUT':
            store['puts'] += 1
            data = json.loads(request.post_data)
            if data.get('sha') != store['sha']:
                return route.fulfill(status=409, content_type='application/json', body='{"message":"conflict"}')
            if store['conflict_once']:
                store['conflict_once'] = False; store['sha'] = 'sha-bumped'   # simulate a race: sha changed under them
                return route.fulfill(status=409, content_type='application/json', body='{"message":"conflict"}')
            store['content'] = base64.b64decode(data['content']).decode(); store['sha'] = 'sha' + str(store['puts'])
            return route.fulfill(status=200, content_type='application/json', body=json.dumps({'content': {'sha': store['sha']}}))
        route.continue_()
    def mk(url, w, h):
        ctx = b.new_context(viewport={'width': w, 'height': h})
        ctx.route('https://api.github.com/**', handler)
        for pat in ('**/*.{png,jpg}', 'https://*.tile.*/**', '**/unpkg.com/**', '**/cdnjs.cloudflare.com/**'): ctx.route(pat, lambda r: r.abort())
        p = ctx.new_page(); e = errs_of(p)
        p.add_init_script("localStorage.setItem('sra_bus_cfg_admin',JSON.stringify({transport:'github',token:'t',poll:3,node:'admin',site:'*'}));localStorage.setItem('sra_bus_cfg_cmdr',JSON.stringify({transport:'github',token:'t',poll:3,node:'cmdr',site:'nb-sd'}));")
        p.goto(url, wait_until='domcontentloaded'); return ctx, p, e
    actx, admin, ae = mk(BASE + '/ie-SRS-ADMIN.html', 1400, 900); admin.wait_for_timeout(2500)
    cctx, cmdr, ce = mk(BASE + '/cmdr/index.html', 393, 852); cmdr.wait_for_timeout(1000)
    assert admin.evaluate("window.SRABus.status().transport")=='github'
    wait_for(lambda: cmdr.evaluate("!!window.CMDR.state().status"), timeout=15, msg='cmdr STATUS via github')
    admin.evaluate("admCmdrTest('nb-sd')")
    wait_for(lambda: cmdr.evaluate("Object.keys(window.CMDR.state().warnords).length>0"), timeout=15, msg='cmdr WARNORD via github')
    code = cmdr.evaluate("Object.keys(window.CMDR.state().warnords)[0]")
    cmdr.evaluate(f"ack('{code}')")
    wait_for(lambda: admin.evaluate("window.ADMIN_CORE.listAudit().some(a=>a.action==='CMDR_ACK')"), timeout=15, msg='admin ACK via github')
    doc = json.loads(store['content'])
    types = [m['type'] for m in doc['messages']]
    assert 'WARNORD' in types and 'ACK' in types and 'HELLO' in types, types
    assert store['puts'] >= 3 and not store['conflict_once'], store
    assert cmdr.evaluate("document.getElementById('linktxt').textContent")=='GitHub'
    assert not ae, 'admin console errors: ' + '\n'.join(ae[:5])
    assert not ce, 'cmdr console errors: ' + '\n'.join(ce[:5])
    actx.close(); cctx.close(); print(f'tier2 github (mocked, {store["puts"]} PUTs incl. 1 retried conflict, {store["gets"]} GETs): PASS')

def tier_norm(b):
    ctx = b.new_context(); p = ctx.new_page(); p.goto(BASE + '/cmdr/index.html', wait_until='domcontentloaded'); p.wait_for_timeout(800)
    d = p.evaluate("window.SRABus.cfg()")
    assert d['transport']=='github' and d['repo']=='thompsonryane-collab/ie-SRS' and d['branch']=='main' and d['path']=='data/bus.json' and d['token']=='' and d['site']=='nb-sd', d
    assert p.evaluate("document.getElementById('p-link').classList.contains('on')") and p.evaluate("document.getElementById('f-transport').value")=='github'
    print('fresh-install defaults: github / ie-SRS / main / data/bus.json, token empty, Link tab opened')
    c = p.evaluate("window.SRABus.configure({transport:'off',repo:' Thompsonryane-collab/ie-SRS ',branch:'main ',path:'data/bus. Json',token:' ghp_x '}).cfg()")
    assert c['repo']=='Thompsonryane-collab/ie-SRS' and c['branch']=='main' and c['path']=='data/bus.json' and c['token']=='ghp_x', c
    ctx.close(); print('config normalization: PASS')

def tier2b(b):
    """Write-forbidden token: reads OK, writes 403 → stable 'read only' state, no green/red flapping."""
    def handler(route, request):
        if request.method == 'GET':
            body = {'sha': 'sha0', 'content': base64.b64encode(json.dumps({'v':1,'messages':[]}).encode()).decode()}
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        return route.fulfill(status=403, content_type='application/json', body='{"message":"Resource not accessible by personal access token"}')
    ctx = b.new_context(viewport={'width': 393, 'height': 852}); ctx.route('https://api.github.com/**', handler)
    p = ctx.new_page(); e = errs_of(p)
    p.add_init_script("localStorage.setItem('sra_bus_cfg_cmdr',JSON.stringify({transport:'github',token:'t',poll:3,node:'cmdr',site:'nb-sd'}));")
    p.goto(BASE + '/cmdr/index.html', wait_until='domcontentloaded'); p.wait_for_timeout(1500)
    seen = set()
    for _ in range(12):
        seen.add(p.evaluate("document.getElementById('linkpill').className")); p.wait_for_timeout(500)
    assert 'link on' not in seen and 'link warn' in seen, seen
    st = p.evaluate("window.SRABus.status()")
    assert st['read']=='ok' and st['write']=='error' and '403' in st['error'] and 'Resource owner' in st['error'], st
    assert p.evaluate("document.getElementById('linktxt').textContent")=='Write 403'
    p.evaluate("go('link')"); p.wait_for_timeout(200); p.screenshot(path='qa_cmdr_403.png')
    assert not e, e[:3]
    ctx.close(); print('tier2b github write-403: PASS (stable amber, hint shown)')

if __name__ == '__main__':
    srv = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        tier1(b); tier2(b); tier2b(b); tier_norm(b)
        b.close()
    srv.shutdown(); print('ALL PASS')
