# CMDR link — ADMIN ↔ mobile bus

## Layout (one repo)
```
ie-SRA-ADMIN.html      hub, patched: bus + CMDR LINK chip (bottom-right)
cmdr/index.html        commander mobile app → https://thompsonryane-collab.github.io/ie-SRA/cmdr/
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
python3 build_cmdr_link.py src/ie-SRA-ADMIN.html
python3 test_cmdr_link.py
```

## Next
Cloudflare Worker / Supabase Realtime adapter for push (same `start/stop/send` contract); Foundry API adapter later.

## ADM-09 Comms Log (hub card, teal)
Ledger of every envelope both directions: sent/received time, direction, type, site, peer, transport, delivery latency (IN), commander ack round-trip (WARNORD), status (sent / awaiting ack / acknowledged · by / received), payload preview. Stored in `adm_comms_log` (cap 3000). KPI strip: envelopes, in/out 24h, avg latency, avg ack RTT, unacked WARNORDs, devices. Filters: text, direction, type, site, window. Sortable columns. Export CSV/JSON; **Push to repo** writes `data/comms-log.json` via the GitHub token from the chip. ARIA's live context now includes comms stats and the list of unacknowledged orders (`window.admAriaContext`). Audit gets `COMMS_LOG_PUSH` / `COMMS_LOG_CLEAR`.

## Health tab (CMDR) ↔ ADM-04 Instance Health
The Map tab is replaced by **Health**. STATUS envelopes now carry the full ADM-04 site record: health state (HEALTHY / DEGRADED / OFFLINE / OUTAGE via `ADMIN_CORE.health`), primary + secondary instance (status, version, last sync, uptime, CPU), FM + Backup users (status, device enrollment, last seen), open WO count (seeded + live unacked), and the enterprise roll-up (online/degraded/offline of 140, open WOs across 70 sites). ADMIN pushes a snapshot on HELLO and every 60 s to every site that has linked in the last 24 h; the phone's Refresh button re-requests. The Health tab badge shows `!` whenever the site is not HEALTHY.
