# HeatReady Guides

Static HTML directory of **outdoor worker heat safety guides by city × industry**. Product hook: **GOES digital WBGT** (wet-bulb globe temperature) + live heat-risk scores. Built for people who search for practical jobsite heat checklists — and as a content funnel to [GOES Health](https://goes.health).

**Not legal advice.** Guides summarize common OSHA / NIOSH-style practices and public climate context. Employers must follow applicable federal, state, and local rules.

## Preview locally

From this folder:

```bash
cd /workspace/goes-directory
python3 -m http.server 8080
```

Then open:

- Home: http://127.0.0.1:8080/
- Directory: http://127.0.0.1:8080/guides/
- Page one: http://127.0.0.1:8080/guides/phoenix-construction.html
- Page two: http://127.0.0.1:8080/guides/houston-roofing.html
- Page three: http://127.0.0.1:8080/guides/las-vegas-landscaping.html

## Layout

```
goes-directory/
  index.html
  guides/index.html
  guides/phoenix-construction.html   # shipped
  guides/houston-roofing.html         # shipped
  guides/las-vegas-landscaping.html  # shipped
  assets/css/site.css
  data/guides.json                   # source of truth for planned pages
  robots.txt
  sitemap.xml
  README.md
```

## Nightly page plan

Publish one new city × industry guide per night (or batch) using the same template as Phoenix Construction:

1. Phoenix Construction — **shipped**
2. Houston Roofing — **shipped**
3. Las Vegas Landscaping — **shipped**
4. California Construction (Cal/OSHA 3395)
5. Dallas Utilities
6. Miami Delivery
7. Tucson Agriculture

Then expand the matrix (hot cities × construction / roofing / landscaping / utilities / agriculture / delivery / oil & gas). Keep `data/guides.json` updated (`status: shipped | planned`) and add each new URL to `sitemap.xml`.

Each page should include: risk snapshot, printable checklist, heat-index / WBGT-aware trigger table, local/regulatory note, gear block (partner links TBD), GOES CTA pitching digital WBGT → https://goes.health + https://goes.health/platform, FAQ, related guides.

## Brand

**HeatReady Guides** — practical, supervisor-friendly, mobile-first.


## Branding

Uses official **GOES Design System (Sept 2026)** tokens in `assets/css/site.css` (`--goes-charcoal`, `--goes-navy`, `--goes-sand`, `--goes-yellow`, `--goes-coral`, `--goes-teal`, etc.). Logos and patterns live under `assets/brand/`. HeatReady is the directory name; GOES appears in partner CTA strips with the disclaimer: *GOES provides guidance. It is not a substitute for professional medical care.*

## Agent discovery layer (llms.txt, Markdown twins, JSON feed)

AI assistants helping supervisors and crews find HeatReady through generated, machine-readable files. **Never hand-edit them.** After every new or changed guide (including the nightly "ship one guide" run):

```bash
python3 scripts/agents.py          # regenerate everything from the HTML + data/guides.json
python3 scripts/agents.py --check  # optional: exit 1 if anything is stale
# commit + push, wait for GitHub Pages to deploy, then:
python3 scripts/indexnow.py        # ping Bing/IndexNow with every live URL (no login)
```

Nightly order: write the new `guides/<id>.html` → set its `data/guides.json` entry to `"status": "shipped"` with `published` → `python3 scripts/agents.py` → commit/push → `python3 scripts/indexnow.py`. Only `shipped` guides whose HTML exists are published to agents.

It writes: `llms.txt`, `guides.json` (public feed; `data/guides.json` stays internal), `index.md` / `guides/**/*.md` (+ `*.html.md` aliases), `robots.txt`, `sitemap.xml`, the IndexNow key file, and an `<!-- agents:start -->…<!-- agents:end -->` block in each page `<head>` (Markdown alternate link, `describedby` llms.txt, and home-page JSON-LD). Visible page copy is never touched. Requires `pip install -r scripts/requirements.txt` (beautifulsoup4, markdownify). Do not remove `CNAME`.
