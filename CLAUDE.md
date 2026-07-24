# ie-SRA

**ie-SRA** (Installation Energy — Simulation, Reconnaissance & Analytics; formerly ie-SR / i-eSR) is a single-file HTML platform for Navy/NAVFAC installation energy management, built for Naval Energy Systems (NES) practitioners, Installation Energy Managers, and NAVFAC personnel. It's designed for both live demonstration (large-screen NAVFAC audiences) and operational use, running standalone in-browser with no server backend.

## Architecture

ie-SRA is a **hub-based launcher**: a single top-level HTML file (`ie-SRA.html`) containing a card-grid shell that opens sub-applications as `srcdoc` iframes. Each sub-app is fully self-contained HTML/CSS/JS embedded as an escaped string inside the hub file — there are no external app files.

**Sub-applications:**
- **ARIA** (`AI-01`) — AI assistant with direct Anthropic API connectivity (`claude-sonnet-4-6`)
- **SimRecon** (`SYS-01`) — scenario simulator/wargame with Web Speech API voiceover narration
- **Intelligent Analytics / DUERS AI** (`SYS-02`) — defense utility energy reporting dashboard, pre-loaded with a locked CFE asset dataset (`DUERS_LOCKED`: 14,968 assets, 11 CNR regions, 68 UICs, 3-year demo window)
- **Data Drop Zone** (`SYS-04`) — file ingest (XLSX/CSV/JSON) via SheetJS, with AI-assisted analysis
- **Intel Archive / Saved Scenarios / Recon** (`SYS-03`) — localStorage-backed record keeping

**Key files in this project:**
- `ie-SRA.html` — primary active file
- `ie-SR.html` — related/earlier deployment, kept for reference
- `launcher-v115.html` — hub launcher reference version

## Conventions & hard-won constraints

**srcdoc / iframe embedding**
- Sub-app HTML is stored `html.escape(quote=True)`-encoded inside the hub file's iframe `srcdoc` attribute; unescape to extract, re-escape to reinsert.
- The reliable boundary delimiter when parsing srcdoc blocks is `"\n  ></iframe>` — naive quote matching breaks when content contains unescaped quotes.
- `rfind()` for `</body>` is unsafe — srcdoc content can contain literal `</body>` strings from nested templates (e.g. embedded user-guide HTML).
- Inline `onclick` handlers with single-quoted dynamic values break JS string parsing; prefer data-attribute delegation.
- `window.onerror = function(){ return true; }` silently swallows all JS errors — strip it out when debugging.

**Layout/CSS**
- `position:fixed` fails inside sandboxed artifact contexts; use `position:absolute` within a positioned parent instead.
- CSP in some hosting contexts blocks certain CDNs (e.g. cdnjs Leaflet) — `unpkg` is a more reliable CDN fallback.

**Editing workflow**
- Always rebuild from the original source file rather than chaining edits on prior outputs — chaining causes position drift and orphaned closing tags.
- Use Python string replacement via `bash_tool` for multi-line srcdoc edits; regex is unreliable at this scale.
- Use a placeholder-then-resolve pattern (e.g. an `XSYS-` prefix) when renaming numbered identifiers, to avoid cascade collisions.
- Use brace-counting loops to find function boundaries in minified JS.

**AI / API integration**
- `anthropic-dangerous-direct-browser-access: true` must be sent unconditionally on both API call sites (direct fetch and the postMessage bridge) — required for CORS to work under GitHub Pages.
- Three-tier AI routing: (1) postMessage bridge to the hub parent when running in iframe context, (2) direct Claude API call via `window._inedApiKey`, (3) CAPRA/STARK fallback.
- Always check `response.ok` before parsing JSON; route non-2xx responses to `onError`; roll back `ariaHistory` on failure to avoid corrupting conversation state.
- ARIA's "online" status indicator (`updateAiStatus()`) should only go green on a fully verified connection — call it from every relevant success/failure path, not just on initial load.
- All user-visible AI provider branding is scrubbed/generic; underlying transport details stay in code comments only.

**Verification before delivering any file**
Run the full instrument check: div balance, duplicate IDs, required IDs present, JS function presence, CSS brace balance, `openApp`/`closeApp` target resolution. Hub-level `<script>` count should always be exactly 1 — extra top-level `<script>` tags outside the srcdoc ranges indicate leaked/duplicated content.

## Deployment

- GitHub Pages under the `thompsonryane-collab` organization.
- Uses `index.html` redirect files plus a `.nojekyll` file to bypass Jekyll processing.

## Data

CFE asset schema (`CFE_Data_LAT_LONG`): `CFE_ASSETNUM`, `CFE_TYPE`, `CFE_SUBTYPE`, `CONDITIONINDEX`, `MISSIONDEPENDENCYINDEX`, `UEM_IND`, plus geospatial coordinates.

## Working style for this project

- Instructions tend to be terse/directive: "run" = execute end-to-end and produce output; "instrument check" = run the full verification suite above; "repair" = diagnose and fix independently without re-explanation of the bug.
- Iterate by re-reading the current source fresh each round rather than assuming state from earlier conversation turns.
- Deliver finished files to `/mnt/user-data/outputs/` and present them via `present_files`.
