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
cmdr = cmdr.replace('<script>/*BUS*/</script>', '<script>\n' + bus.replace("'__NODE__'", "'cmdr'") + '\n</script>')
(OUT / 'cmdr' / 'index.html').write_text(cmdr)

# ── ADMIN patch ──
adm = SRC_ADMIN.read_text()
assert '<!-- CMDR LINK -->' not in adm, 'source already patched — rebuild from original'
assert adm.count('</body>') == 1, 'expected exactly one hub </body>'
link = (ROOT / 'cmdr' / 'admin_link.js').read_text()
comms = (ROOT / 'cmdr' / 'admin_comms.js').read_text()
card = (ROOT / 'cmdr' / 'adm09_card.html').read_text()
overlay = (ROOT / 'cmdr' / 'adm09_overlay.html').read_text()
assert adm.count('</div><!-- #card-grid -->') == 1
adm = adm.replace('</div><!-- #card-grid -->', card + '\n</div><!-- #card-grid -->')
inject = ('\n<!-- CMDR LINK -->\n' + overlay + '\n<script>\n' + bus.replace("'__NODE__'", "'admin'") + '\n</script>\n<script>\n' + comms + '\n</script>\n<script>\n' + link + '\n</script>\n')
adm = adm.replace('</body>', inject + '</body>')
(OUT / 'ie-SRA-ADMIN.html').write_text(adm)

# ── seed bus file for GitHub transport ──
(OUT / 'data' / 'bus.json').write_text(json.dumps({'v': 1, 'updated': 0, 'messages': []}, indent=2) + '\n')

# ── structural verification ──
import subprocess, tempfile
def js_syntax_ok(js):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(js); fn = f.name
    r = subprocess.run(['node', '--check', fn], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()[:400]
for name, js in [('bus.js', bus), ('admin_link.js', link), ('admin_comms.js', comms)]:
    ok, err = js_syntax_ok(js); assert ok, f'{name}: {err}'
for i, m in enumerate(re.finditer(r'<script>([\s\S]*?)</script>', cmdr)):
    ok, err = js_syntax_ok(m.group(1)); assert ok, f'cmdr script {i}: {err}'
for name, doc in [('cmdr/index.html', cmdr), ('ie-SRA-ADMIN.html', adm)]:
    ids = re.findall(r'\sid="([^"]+)"', re.sub(r'srcdoc="(?:[^"\\]|\\.)*"', '', doc))
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f'{name} duplicate ids: {dup}'
    assert doc.count('<body') == doc.count('</body>') == 1, f'{name} body tags'
hub_scripts = len(re.findall(r'<script(?![^>]*srcdoc)', adm))
print(f'cmdr/index.html {len(cmdr):,} bytes · ie-SRA-ADMIN.html {len(adm):,} bytes · hub <script> tags {hub_scripts} (+3 injected)')
print('OK')
