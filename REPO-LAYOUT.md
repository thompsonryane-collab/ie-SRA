# Repo layout — exactly this, folders included

```
ie-SRA/                       (repo root = GitHub Pages root)
├── index.html                redirect → ie-SRS-ADMIN.html   ← replaces the mobile app that landed here
├── ie-SRS-ADMIN.html         admin hub (patched)
├── ie-SRA.html               core hub (if present; unchanged)
├── favicon.ico, favicon-16x16.png, CLAUDE.md, README.md   (unchanged)
├── CMDR-LINK.md
├── cmdr/
│   └── index.html            ← the mobile app lives HERE, not at the root
├── data/
│   └── bus.json              ← GitHub transport message file lives HERE
├── cmdr-src/                 build inputs (src.html, bus.js, admin_link.js, admin_comms.js, adm09_*.html)
├── build_cmdr_link.py
└── test_cmdr_link.py
```

## Fix the current deployment
1. **Delete** these from the repo root (they were unzipped flat):
   `src.html`, `bus.js`, `admin_link.js`, `admin_comms.js`, `adm09_card.html`, `adm09_overlay.html`, `bus.json`, and the root `index.html` (it's the mobile app).
2. **Upload** the contents of this zip. When using GitHub's "Add file → Upload files", drag the **folders** (`cmdr`, `data`, `cmdr-src`) in, not just the files inside them — GitHub keeps folder structure only when you drop a folder.
   Alternative that can't go wrong: `git clone`, copy the zip contents over the working tree, `git add -A`, commit, push.
3. Wait ~1 min, then check:
   - `https://thompsonryane-collab.github.io/ie-SRS/` → redirects to ADMIN
   - `https://thompsonryane-collab.github.io/ie-SRS/ie-SRS-ADMIN.html` → admin, CMDR LINK chip bottom-right
   - `https://thompsonryane-collab.github.io/ie-SRS/cmdr/` → mobile app
