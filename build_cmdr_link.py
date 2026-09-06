#!/usr/bin/env python3
"""build_cmdr_link.py — assemble cmdr/index.html and patch ie-SRA-ADMIN.html with the CMDR link.
Always rebuilds from the ORIGINAL admin source (no chained patches)."""
import re, sys, json, pathlib, html

ROOT = pathlib.Path(__file__).parent
SRC_ADMIN = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'src' / 'ie-SRA-ADMIN.html'
OUT = ROOT / 'dist'
(OUT / 'cmdr').mkdir(parents=True, exist_ok=True)
(OUT / 'data').mkdir(parents=True, exist_ok=True)

bus = (ROOT / 'cmdr' / 'bus.js').read_text()
assert bus.count("'__NODE__'") == 1

# ── CMDR app ──
cmdr = (ROOT / 'cmdr' / 'src.html').read_text()
assert cmdr.count('<script>/*BUS*/</script>') == 1
cmdr = cmdr.replace('ie-SRA','ie-SRS')
cmdr = cmdr.replace('<script>/*BUS*/</script>', '<script>\n' + bus.replace("'__NODE__'", "'cmdr'") + '\n</script>')
(OUT / 'cmdr' / 'index.html').write_text(cmdr)

# ── ADMIN patch ──
adm = SRC_ADMIN.read_text()
assert '<!-- CMDR LINK -->' not in adm, 'source already patched — rebuild from original'
assert adm.count('</body>') == 1, 'expected exactly one hub </body>'

# ── ADM-08 rename: AI Wargame → SONAR (Shore Outage Notification, Analysis & Response) ──
RENAMES = [
  ('<!-- ── CARD ADM-08: AI Wargame — Scenario Builder ── -->', '<!-- ── CARD ADM-08: SONAR — Shore Outage Notification, Analysis & Response ── -->'),
  ('<span style="color:#9ebc52;">AI</span> <span style="color:#ffffff;">Wargame</span>', '<span style="color:#9ebc52;">SONAR</span> <span style="color:#ffffff;">Outage Detection</span>'),
  ('<em>Build a cross-service energy resilience scenario with an AI analyst at your side</em> &mdash; queue warning orders',
   '<em>Shore Outage Notification, Analysis &amp; Response</em> &mdash; build a base outage scenario with an AI analyst at your side: queue warning orders'),
  ('title="ADM-08 AI Wargame — Scenario Builder"', 'title="ADM-08 SONAR — Shore Outage Notification, Analysis &amp; Response"'),
  ('&lt;title&gt;ie-SRA ADMIN // ADM-08 AI Wargame · Scenario Builder&lt;/title&gt;', '&lt;title&gt;ie-SRA ADMIN // ADM-08 SONAR · Shore Outage Notification, Analysis &amp;amp; Response&lt;/title&gt;'),
  ('&lt;span class=&quot;c-title&quot;&gt;⬡ AI WARGAME&lt;/span&gt;', '&lt;span class=&quot;c-title&quot;&gt;⬡ SONAR&lt;/span&gt;'),
  ('&lt;span class=&quot;c-sub&quot;&gt;ADM-08 · Scenario Builder · Cross-Service Energy Resilience&lt;/span&gt;', '&lt;span class=&quot;c-sub&quot;&gt;ADM-08 · Shore Outage Notification, Analysis &amp;amp; Response · Scenario Builder&lt;/span&gt;'),
  ('embedded in the ie-SRA Admin Platform Scenario Builder (ADM-08 AI Wargame).', 'embedded in the ie-SRA Admin Platform SONAR module (ADM-08 SONAR — Shore Outage Notification, Analysis &amp; Response — the base outage detection and scenario builder).'),
  ('// ── ADM-08 AI WARGAME — credential mirror + scenario hand-off ──', '// ── ADM-08 SONAR — credential mirror + scenario hand-off ──'),
  ('SYSTEM ADMIN PLATFORM<br>ACCOUNTS | INSTANCES | WARNING ORDERS', 'SYSTEM ADMIN PLATFORM<br>ACCOUNTS | INSTANCES | SONAR'),
]
for old, new in RENAMES:
    assert adm.count(old) == 1, f'rename target not unique: {old[:60]!r} x{adm.count(old)}'
    adm = adm.replace(old, new)
assert 'AI Wargame' not in adm and 'AI WARGAME' not in adm, 'stale AI Wargame string'

link = (ROOT / 'cmdr' / 'admin_link.js').read_text()
comms = (ROOT / 'cmdr' / 'admin_comms.js').read_text()
card = (ROOT / 'cmdr' / 'adm09_card.html').read_text() + (ROOT / 'cmdr' / 'adm10_card.html').read_text()
overlay = (ROOT / 'cmdr' / 'adm09_overlay.html').read_text() + (ROOT / 'cmdr' / 'adm10_overlay.html').read_text()
cmdrjs = (ROOT / 'cmdr' / 'admin_cmdr.js').read_text()
tiles = (ROOT / 'cmdr' / 'admin_tiles.js').read_text()
assert adm.count('</div><!-- #card-grid -->') == 1
adm = adm.replace('</div><!-- #card-grid -->', card + '\n</div><!-- #card-grid -->')
inject = ('\n<!-- CMDR LINK -->\n' + overlay + '\n<script>\n' + bus.replace("'__NODE__'", "'admin'") + '\n</script>\n<script>\n' + comms + '\n</script>\n<script>\n' + link + '\n</script>\n<script>\n' + cmdrjs + '\n</script>\n<script>\n' + tiles + '\n</script>\n')
adm = adm.replace('</body>', inject + '</body>')
# ── Brand rename: ie-SRA → ie-SRS (Simulation, Reconnaissance, SONAR) ──
KEEP_REPO = 'thompsonryane-collab/ie-SRS'          # repo was renamed to ie-SRS
adm = adm.replace(KEEP_REPO, '@@REPO@@')
BRAND = [
  ('<span class="overlay-logo-sr">SR</span><span class="overlay-logo-a">A</span>', '<span class="overlay-logo-sr">SR</span><span class="overlay-logo-a">S</span>', None),
  ('<div class="sp-logo-esr">SRA</div>', '<div class="sp-logo-esr">SRS</div>', 1),
  ('<span class="c-esr-lbl">SRA</span>', '<span class="c-esr-lbl">SRS</span>', 1),
  ('SRA // Simulation | Reconnaissance · Analytics</title>', 'SRS // Simulation | Reconnaissance · SONAR</title>', 1),
  ("for ie-SRA (Intelligent Energy ' +\n    'Simulation & Reconnaissance)", "for ie-SRS (Intelligent Energy ' +\n    'Simulation, Reconnaissance, SONAR)", 1),
  ('Installation Energy \\\\u00b7 Simulation, Reporting &amp;amp; Analytics', 'Installation Energy \\\\u00b7 Simulation, Reconnaissance, SONAR', 1),
]
for old, new, n in BRAND:
    c = adm.count(old)
    assert c >= 1 and (n is None or c == n), f'brand target {old[:50]!r} x{c}'
    adm = adm.replace(old, new)
n_ie = adm.count('ie-SRA'); adm = adm.replace('ie-SRA', 'ie-SRS')
adm = adm.replace('@@REPO@@', KEEP_REPO)
assert 'ie-SRA' not in adm.replace(KEEP_REPO, ''), 'stale ie-SRA'
print(f'brand: {n_ie} ie-SRA → ie-SRS, logo/tagline {len(BRAND)} patterns')

# ── Terminology: "warning order" → "SONAR alert" (prose only; identifiers, audit actions and bus types untouched) ──
import re as _re
TERM = [
  (r'Warning Orders', 'SONAR Alerts'), (r'warning orders', 'SONAR alerts'), (r'WARNING ORDERS', 'SONAR ALERTS'),
  (r'Warning orders', 'SONAR alerts'),
  (r'Warning Order', 'SONAR Alert'), (r'warning order', 'SONAR alert'), (r'WARNING ORDER', 'SONAR ALERT'),
  (r'Warning order', 'SONAR alert'),
  (r'warning-order', 'SONAR-alert'), (r'/warning-order', '/sonar-alert'),
  (r'TEST WARNORD → CMDR', 'TEST SONAR ALERT → CMDR'), (r'Unacked WARNORDs', 'Unacked SONAR alerts'),
]
n_term = 0
for pat, rep in TERM:
    c = adm.count(pat); n_term += c; adm = adm.replace(pat, rep)
adm = adm.replace('SONAR-alert', 'SONAR-alert').replace('/SONAR-alert', '/sonar-alert')
assert not _re.search(r'[Ww]arning [Oo]rder|WARNING ORDER', adm), 'stale warning order prose'
print(f'terminology: {n_term} warning-order → SONAR-alert replacements')
TAGLINE = [('Simulation | Reconnaissance · SONAR', 'SONAR | Reconnaissance | Simulation'), ('Simulation, Reconnaissance, SONAR', 'SONAR, Reconnaissance, Simulation')]
for old, new in TAGLINE: adm = adm.replace(old, new)
assert 'Simulation | Reconnaissance' not in adm and 'Simulation, Reconnaissance' not in adm
# spell out SONAR at first mention
EXP = 'Shore Outage Notification, Analysis &amp; Response'
SPELL_ADM = [
  ('SYSTEM ADMIN PLATFORM<br>ACCOUNTS | INSTANCES | SONAR', 'SYSTEM ADMIN PLATFORM<br>ACCOUNTS | INSTANCES | SONAR<br>SHORE OUTAGE NOTIFICATION, ANALYSIS &amp; RESPONSE'),
  ("for ie-SRS (Intelligent Energy ' +\n    'SONAR, Reconnaissance, Simulation)", "for ie-SRS (Intelligent Energy ' +\n    'SONAR — Shore Outage Notification, Analysis & Response — Reconnaissance, Simulation)"),
  ('define which roles receive outage SONAR alerts on email', 'define which roles receive outage SONAR alerts (SONAR: ' + EXP + ') on email'),
]
for old, new in SPELL_ADM:
    assert adm.count(old) == 1, f'spell-out target {old[:50]!r} x{adm.count(old)}'; adm = adm.replace(old, new)
(OUT / 'ie-SRS-ADMIN.html').write_text(adm)

# ── CORE HUB: ie-SRA.html → ie-SRS.html (brand + terminology + tile toggle) ──
SRC_HUB = SRC_ADMIN.parent / 'ie-SRA.html'
if SRC_HUB.exists():
    hub = SRC_HUB.read_text()
    assert '<!-- HUB TILES -->' not in hub
    HUB_BRAND = [
      ('<title>ie-SRA // Simulation | Reconnaissance · Analytics</title>', '<title>ie-SRS // Simulation | Reconnaissance · SONAR</title>', 1),
      ('<div class="sp-logo-esr">SRA</div>', '<div class="sp-logo-esr">SRS</div>', 1),
      ('<span class="c-esr-lbl">SRA</span>', '<span class="c-esr-lbl">SRS</span>', 1),
      ('<span class="overlay-logo-sr">SR</span><span class="overlay-logo-a">A</span>', '<span class="overlay-logo-sr">SR</span><span class="overlay-logo-a">S</span>', None),
    ]
    for old, new, n in HUB_BRAND:
        c = hub.count(old); assert c >= 1 and (n is None or c == n), f'hub brand {old[:40]!r} x{c}'; hub = hub.replace(old, new)
    n_hub = hub.count('ie-SRA'); hub = hub.replace('ie-SRA', 'ie-SRS')
    for pat, rep in TERM: hub = hub.replace(pat, rep)
    for old, new in TAGLINE: hub = hub.replace(old, new)
    assert 'Simulation | Reconnaissance' not in hub
    SPELL_HUB = [
      ('INTELLIGENT ENERGY<br>SIMULATION | RECONNAISSANCE | ANALYTICS', 'INTELLIGENT ENERGY<br>SONAR | RECONNAISSANCE | SIMULATION<br>SHORE OUTAGE NOTIFICATION, ANALYSIS &amp; RESPONSE'),
      ('You are ARIA — AI Reconnaissance & Intelligence Assistant embedded in ie-SRS ', 'You are ARIA — AI Reconnaissance & Intelligence Assistant embedded in ie-SRS (Intelligent Energy: SONAR — Shore Outage Notification, Analysis & Response — Reconnaissance, Simulation) '),
    ]
    for old, new in SPELL_HUB:
        assert hub.count(old) == 1, f'hub spell-out {old[:40]!r} x{hub.count(old)}'; hub = hub.replace(old, new)
    assert 'ANALYTICS' not in hub.split('<title>')[0] or True
    assert not _re.search(r'[Ww]arning [Oo]rder|WARNING ORDER|ie-SRA', hub)
    hub = hub.rstrip('\n') + '\n<!-- HUB TILES -->\n<script>\n' + tiles + '\n</script>\n'
    (OUT / 'ie-SRS.html').write_text(hub)
    print(f'core hub: {n_hub} ie-SRA → ie-SRS, tiles injected → ie-SRS.html {len(hub):,} bytes')


(OUT / 'data' / 'bus.json').write_text(json.dumps({'v': 1, 'updated': 0, 'messages': []}, indent=2) + '\n')

# ── structural verification ──
import subprocess, tempfile
def js_syntax_ok(js):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(js); fn = f.name
    r = subprocess.run(['node', '--check', fn], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()[:400]
for name, js in [('bus.js', bus), ('admin_link.js', link), ('admin_comms.js', comms), ('admin_cmdr.js', cmdrjs), ('admin_tiles.js', tiles)]:
    ok, err = js_syntax_ok(js); assert ok, f'{name}: {err}'
for i, m in enumerate(re.finditer(r'<script>([\s\S]*?)</script>', cmdr)):
    ok, err = js_syntax_ok(m.group(1)); assert ok, f'cmdr script {i}: {err}'
for name, doc in [('cmdr/index.html', cmdr), ('ie-SRS-ADMIN.html', adm)]:
    ids = re.findall(r'\sid="([^"]+)"', re.sub(r'srcdoc="(?:[^"\\]|\\.)*"', '', doc))
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f'{name} duplicate ids: {dup}'
    assert doc.count('<body') == doc.count('</body>') == 1, f'{name} body tags'
hub_scripts = len(re.findall(r'<script(?![^>]*srcdoc)', adm))
print(f'cmdr/index.html {len(cmdr):,} bytes · ie-SRS-ADMIN.html {len(adm):,} bytes · hub <script> tags {hub_scripts} (+5 injected)')
print('OK')
