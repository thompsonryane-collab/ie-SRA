# ie-SRS — Intelligent Energy: SONAR, Reconnaissance, Simulation

# CMDR link — ADMIN ↔ mobile bus

## Layout (one repo)
```
ie-SRS-ADMIN.html      hub, patched: bus + CMDR LINK chip (bottom-right)
cmdr/index.html        commander mobile app → https://thompsonryane-collab.github.io/ie-SRS/cmdr/
data/bus.json          message file for the GitHub transport (seeded empty)
build_cmdr_link.py     rebuilds both from cmdr/src.html + cmdr/bus.js + cmdr/admin_link.js + ORIGINAL admin
test_cmdr_link.py      Playwright: tier 1 (BroadcastChannel) + tier 2 (mocked GitHub Contents API)
```

## Envelope (identical on every transport)
`{id, type, ts, from:'admin'|'cmdr', to:'*', site:'nb-sd'|'*', payload}`
`type` ∈ WARNORD · ACK · MSG · STATUS · HELLO

## Transports (Link tab in CMDR, chip panel in ADMIN)
| mode | how | use |
|---|---|---|
| Same browser | BroadcastChannel + localStorage ping/replay | ADMIN tab + CMDR tab, or "Open CMDR app" from the chip |
| GitHub repo | `api.github.com/repos/{repo}/contents/data/bus.json` — read-modify-write with sha, 409 retry ×3, poll N s | real phone on cell/Wi-Fi; needs fine-grained PAT (Contents: read/write) on both ends — demo only, token lives in the browser |
| Off | — | — |

## Wiring in ADMIN
- `ADMIN_CORE.logWO` wrapped → every dispatch (ADM-03 test, ADM-08 wargame, SYS-03 map, workflow sim) publishes WARNORD.
- `ADMIN_CORE.sendMsg` wrapped → `all` and `site:*` channels publish MSG (bus-originated messages are not echoed).
- Inbound ACK → WO record gets `ack{by,ts,via}`, `CMDR_ACK` written to ADM-05 audit, routing/audit overlays repainted if open.
- Inbound MSG → ADM-02 message center on `site:<id>` from `CMDR <name> (mobile)`, `CMDR_MSG` audited.
- Inbound HELLO → `CMDR_HELLO` audited, ADMIN replies HELLO + STATUS snapshot (site health, open WOs) so a phone joining late still gets pending WARNORDs.

## Test
```
python3 build_cmdr_link.py src/ie-SRS-ADMIN.html
python3 test_cmdr_link.py
```

## Next
Cloudflare Worker / Supabase Realtime adapter for push (same `start/stop/send` contract); Foundry API adapter later.

## ADM-09 Comms Log (hub card, teal)
Ledger of every envelope both directions: sent/received time, direction, type, site, peer, transport, delivery latency (IN), commander ack round-trip (WARNORD), status (sent / awaiting ack / acknowledged · by / received), payload preview. Stored in `adm_comms_log` (cap 3000). KPI strip: envelopes, in/out 24h, avg latency, avg ack RTT, unacked WARNORDs, devices. Filters: text, direction, type, site, window. Sortable columns. Export CSV/JSON; **Push to repo** writes `data/comms-log.json` via the GitHub token from the chip. ARIA's live context now includes comms stats and the list of unacknowledged orders (`window.admAriaContext`). Audit gets `COMMS_LOG_PUSH` / `COMMS_LOG_CLEAR`.

## Health tab (CMDR) ↔ ADM-04 Instance Health
The Map tab is replaced by **Health**. STATUS envelopes now carry the full ADM-04 site record: health state (HEALTHY / DEGRADED / OFFLINE / OUTAGE via `ADMIN_CORE.health`), primary + secondary instance (status, version, last sync, uptime, CPU), FM + Backup users (status, device enrollment, last seen), open WO count (seeded + live unacked), and the enterprise roll-up (online/degraded/offline of 140, open WOs across 70 sites). ADMIN pushes a snapshot on HELLO and every 60 s to every site that has linked in the last 24 h; the phone's Refresh button re-requests. The Health tab badge shows `!` whenever the site is not HEALTHY.

## ADM-10 CMDR Mobile (hub card, green)
The front door for the phone app. Toolbar: site picker, **Test WARNORD → CMDR**, **Push health snapshot**, open in new window, jump to Comms Log. KPI strip: link state, linked commanders, awaiting ack, envelopes logged, avg ack RTT. Panels: phone URL with copy (add-to-home-screen hint), linked commanders (from HELLO), warning orders awaiting acknowledgment, transport settings (moved here from the chip), link events, and a recently-acknowledged list with round-trip times. Each linked commander row has TEST ALERT and PUSH HEALTH buttons. (The in-page phone preview was removed; use Open in new window.) The bottom-right chip now just shows link state and opens ADM-10.

## Hub tile layout
The ADMIN card grid defaults to **5-column icon tiles** (square, icon only; no hover tooltip; aria-label carries the name). Live count badges: ADM-01 pending accounts, ADM-02 commander messages, ADM-03 open WOs, ADM-04 degraded+offline instances, ADM-10 unacked mobile WOs. A **TILES / CARDS** toggle sits next to FULL in the top bar and is remembered (`adm_tiles`). Responsive: 4 columns under 1000 px, 3 under 720 px.

## ADM-08 renamed: SONAR
**SONAR — Shore Outage Notification, Analysis & Response** replaces "AI Wargame" on the ADM-08 card, the builder overlay chrome and page title, and in the embedded AI analyst's system prompt. Element ids (`card-adm-wargame`, `frame-builder`, `overlay-builder`), audit action `WARGAME_SCENARIO`, and the hub↔builder message types are unchanged, so nothing else needed re-wiring. The rename is applied by `build_cmdr_link.py` (see `RENAMES`), so it survives rebuilds from a fresh ADMIN source.

## Brand rename: ie-SRA → ie-SRS
The product is now **ie-SRS — SONAR, Reconnaissance, Simulation**. Renamed in the ADMIN splash logo, top bar, page title, ARIA system prompt, every overlay logo, the CMDR app, and the docs. The admin file is now `ie-SRS-ADMIN.html` and the root `index.html` redirects there. The GitHub repo has since been renamed to `ie-SRS`; the transport default repo is `thompsonryane-collab/ie-SRS`.

## Terminology: "warning order" → "SONAR alert"
All user-facing prose now says **SONAR alert(s)** (KPI strip, ADM-03 "SONAR Alert Routing", ADM-07 strategy deck, ADM-08 builder, ARIA prompts, CMDR app). Applied in `build_cmdr_link.py` (`TERM`), 153 replacements in ADMIN. Unchanged on purpose: audit action names (`WARNING_ORDER_*`, `TEST_WARNING_ORDER`), the bus envelope type `WARNORD`, the ADM-09 type filter/pills (protocol names), JS identifiers (`warningOrders`, `addWarningOrder`), and `WO-`/`WARN-` code prefixes.

## Core hub: ie-SRS.html
`ie-SRA.html` is now built to `ie-SRS.html` by the same script (place the source at `src/ie-SRA.html`): brand → ie-SRS / SONAR | Reconnaissance | Simulation, "warning order" → "SONAR alert", and the same **TILES / CARDS** toggle (default TILES, remembered under the shared `adm_tiles` key so both hubs follow one setting). Five tiles, one row.

## Link status: read vs write
The GitHub transport now tracks read and write separately. A token that can read the public repo but not write shows a steady **amber** "Write 403" pill (phone) / `CMDR LINK · READ ONLY · WRITE 403` chip (ADMIN) instead of flapping red/green each poll, and the Link tab explains the likely cause (401 token invalid/expired · 403 resource owner / Contents permission · 404 repo/branch/path). Queued messages are kept and flush automatically once a good token is saved. Test `tier2b` covers it.

## ADM-02 live presence
"Users online" now means real sessions only: the System Admin on web (this session) plus every CMDR mobile device heard from in the last 15 min (HELLO, ACK, MSG or heartbeat — phones send a HELLO heartbeat every 10 min while open and on resume). Stale devices show greyed with "last seen". Clicking a commander opens that site's channel. The KPI strip's Users online reads "1 admin (web) · N CMDR mobile". Synthetic FM/Backup presence is no longer shown in ADM-02 (site records are untouched elsewhere).

## Channel-aware replies (ADM-02 #all-hands)
Every message now carries its channel end to end. An ADMIN #all-hands broadcast arrives on the phone tagged **#all-hands**, the compose bar's channel pill flips to #all-hands, and the commander's reply is published on `ch:'all'` so ADMIN files it in **#all-hands** — not the site channel. A site message from ADMIN flips the pill back to `@<SITE>`; the pill can also be tapped to switch manually. Bubbles show their channel tag.

## Phone defaults
A fresh install of `cmdr/` starts on **GitHub repo · thompsonryane-collab/ie-SRS · main · data/bus.json · site nb-sd** with an empty token; it opens the Link tab and focuses the token field, so the commander only pastes the token and taps Save. ADMIN still defaults to same-browser.
