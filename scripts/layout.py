#!/usr/bin/env python3
"""HeatReady shared layout: one source of truth for the header, footer, directory and home guide list.

Run after adding or editing any page (the nightly routine runs it right after writing the new guide):

    python3 scripts/layout.py          # rewrite header/footer/lists in every page from data/guides.json
    python3 scripts/layout.py --check  # exit 1 if any page is out of date (CI / pre-publish)

What it owns (never hand-edit these regions):
  * <!-- layout:header:start --> … <!-- layout:header:end -->   compact header: logo, All guides,
    GOES platform, "Get live WBGT" CTA, and a <details> hamburger menu on phones. NO per-guide links.
  * <!-- layout:footer:start --> … <!-- layout:footer:end -->
  * <!-- layout:directory:start --> … <!-- layout:directory:end -->  (guides/index.html) all shipped
    guides grouped by industry, with jump chips.
  * <!-- layout:latest:start --> … <!-- layout:latest:end -->  (index.html) newest six guides.
  * data-label="…" on trigger-table cells so tables stack into cards on phones.
Card blurbs come from each guide's "summary" in data/guides.json (falls back to the page's meta
description). Pages written with the old long header are migrated automatically.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "guides.json")
GOES = "https://goes.health"
PLATFORM = "https://goes.health/platform"
LATEST_N = 6

esc = lambda s: html.escape(s, quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("&", " ")).strip("-")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def load():
    with open(DATA, encoding="utf-8") as f:
        D = json.load(f)
    shipped = [g for g in D["guides"] if g.get("status") == "shipped" and os.path.exists(os.path.join(ROOT, g["path"]))]
    return D, shipped


def harvest_summaries(D):
    """Fill missing guide summaries from existing directory/home cards, then meta descriptions."""
    found = {}
    for rel, prefix in (("guides/index.html", ""), ("index.html", "guides/")):
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        for m in re.finditer(r'<a class="title-link" href="([^"]+)">.*?</a></h[34]>\s*<p>(.*?)</p>', read(rel), re.S):
            gid = os.path.basename(m.group(1))[:-5]
            found.setdefault(gid, html.unescape(re.sub(r"\s+", " ", m.group(2)).strip()))
    changed = False
    for g in D["guides"]:
        if g.get("summary"):
            continue
        s = found.get(g["id"])
        if not s and os.path.exists(os.path.join(ROOT, g["path"])):
            m = re.search(r'<meta name="description" content="([^"]*)"', read(g["path"]))
            if m:
                d = html.unescape(m.group(1))
                d = re.sub(r"\s*Not legal advice\.?\s*$", "", d)
                s = d if len(d) <= 170 else d[:167].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        if s:
            g["summary"] = s
            changed = True
    return changed


def industries(shipped):
    groups = {}
    for g in shipped:
        groups.setdefault(g["industry"], []).append(g)
    order = sorted(groups, key=lambda k: (-len(groups[k]), k))
    return [(k, sorted(groups[k], key=lambda g: g.get("published", ""), reverse=True)) for k in order]


def chips(shipped, href_prefix, ind=None):
    ind = ind or industries(shipped)
    out = [f'<nav class="chips" aria-label="Browse guides by industry">']
    for name, gs in ind:
        out.append(f'<a class="chip" href="{href_prefix}#{slug(name)}">{esc(name)} <span class="chip-count">{len(gs)}</span></a>')
    out.append("</nav>")
    return "\n".join(out)


def header(root, page, shipped):
    cur = ' aria-current="page"' if page == "guides/index.html" else ""
    home_cur = ' aria-current="page"' if page == "index.html" else ""
    n = len(shipped)
    return f"""<!-- layout:header:start -->
  <header class="site-header">
    <div class="inner">
      <a class="brand-lockup" href="{root}index.html" aria-label="HeatReady Guides by GOES, home"{home_cur}>
        <img class="goes-logo" src="{root}assets/brand/logo/GOES_black.svg" alt="GOES" width="951" height="186">
        <span class="divider" aria-hidden="true"></span>
        <span class="site-name">HeatReady<span class="site-name-tail"> Guides</span></span>
      </a>
      <nav class="nav" aria-label="Primary">
        <a class="nav-link" href="{root}guides/index.html"{cur}>All guides</a>
        <a class="nav-link" href="{PLATFORM}">GOES platform</a>
        <a class="btn btn-primary nav-cta" href="{GOES}"><span class="nav-cta-long">Get live WBGT</span><span class="nav-cta-short" aria-hidden="true">Live WBGT</span></a>
      </nav>
      <details class="menu">
        <summary aria-label="Open menu"><span class="menu-icon" aria-hidden="true"></span></summary>
        <div class="menu-panel">
          <a href="{root}index.html">Home</a>
          <a href="{root}guides/index.html">All {n} guides</a>
          <p class="menu-label">By industry</p>
          {chips(shipped, root + "guides/index.html").replace(chr(10), chr(10) + "          ")}
          <a href="{PLATFORM}">GOES platform</a>
          <a class="btn btn-primary" href="{GOES}">Get live WBGT &amp; heat-risk scores</a>
        </div>
      </details>
    </div>
  </header>
  <script src="{root}assets/js/site.js" defer></script>
  <!-- layout:header:end -->"""


def footer(root):
    return f"""<!-- layout:footer:start -->
  <footer class="site-footer">
    <img class="footer-pattern" src="{root}assets/brand/pattern/Pattern_BotLeft.svg" alt="" aria-hidden="true">
    <div class="inner">
      <div class="footer-brand">
        <img class="goes-logo" src="{root}assets/brand/logo/GOES_offwhite.svg" alt="GOES" width="951" height="186">
        <div><strong>HeatReady Guides</strong> — practical outdoor worker heat safety. Not legal advice.</div>
        <p class="footer-disclaimer">GOES provides guidance. It is not a substitute for professional medical care.</p>
      </div>
      <nav class="footer-nav" aria-label="Footer">
        <a href="{root}index.html">Home</a>
        <a href="{root}guides/index.html">All guides</a>
        <a href="{GOES}">goes.health</a>
        <a href="{PLATFORM}">GOES platform</a>
      </nav>
    </div>
  </footer>
  <!-- layout:footer:end -->"""


def card(g, href, h="h4"):
    return f"""<article class="card card-link">
            <div class="meta">{esc(g['city'])} · {esc(g['industry'])}</div>
            <{h}><a class="title-link" href="{href}">{esc(g['title'])}</a></{h}>
            <p>{esc(g.get('summary', ''))}</p>
            <span class="status status-shipped">Live</span>
          </article>"""


def directory_block(shipped):
    ind = industries(shipped)
    parts = ["<!-- layout:directory:start -->",
             f'        <h2>All guides <span class="count">{len(shipped)} live</span></h2>',
             "        " + chips(shipped, "", ind).replace("\n", "\n        ")]
    for name, gs in ind:
        sid = slug(name)
        cards = "\n          ".join(card(g, os.path.basename(g["path"])) for g in gs)
        parts.append(f"""        <section class="industry-group" id="{sid}" aria-labelledby="h-{sid}">
          <h3 class="group-title" id="h-{sid}">{esc(name)} <span class="count">{len(gs)}</span></h3>
          <div class="grid grid-2">
          {cards}
          </div>
        </section>""")
    parts.append("        <!-- layout:directory:end -->")
    return "\n".join(parts)


def latest_block(shipped):
    newest = sorted(shipped, key=lambda g: g.get("published", ""), reverse=True)[:LATEST_N]
    cards = "\n          ".join(card(g, g["path"], "h3") for g in newest)
    return f"""<!-- layout:latest:start -->
        <p class="eyebrow">Directory</p>
        <h2>Latest guides <span class="count">{len(shipped)} live</span></h2>
        <div class="grid grid-2">
          {cards}
        </div>
        <p class="more-link"><a class="btn btn-secondary" href="guides/index.html">See all {len(shipped)} guides</a></p>
        <!-- layout:latest:end -->"""


def replace_region(src, name, new, legacy=None):
    pat = re.compile(rf"<!-- layout:{name}:start -->.*?<!-- layout:{name}:end -->", re.S)
    if pat.search(src):
        return pat.sub(lambda m: new, src, count=1)
    if legacy is not None:
        m = legacy.search(src)
        if m:
            return src[:m.start()] + new + src[m.end():]
    raise SystemExit(f"layout.py: could not find the {name} region")


LEGACY_HEADER = re.compile(r'<header class="site-header">.*?</header>', re.S)
LEGACY_FOOTER = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)
LEGACY_DIRECTORY = re.compile(r'<h2>All guides</h2>\s*<div class="grid grid-2">.*?</div>\s*(?=<div class="cta-band">)', re.S)
LEGACY_LATEST = re.compile(r'<p class="eyebrow">Directory</p>\s*<h2>[^<]*</h2>\s*<div class="grid grid-2">.*?See full directory[^<]*</a></p>', re.S)


def label_tables(src):
    def do_table(m):
        t = m.group(0)
        heads = [html.unescape(re.sub(r"<[^>]+>", "", h)).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)]
        if not heads:
            return t
        def do_row(r):
            i = [0]
            def do_td(c):
                k = i[0]; i[0] += 1
                if "data-label" in c.group(0) or k >= len(heads):
                    return c.group(0)
                return f'<td data-label="{esc(heads[k])}"' + (c.group(1) or "") + ">"
            return re.sub(r"<td(\s[^>]*)?>", do_td, r.group(0))
        return re.sub(r"<tr>.*?</tr>", do_row, t, flags=re.S)
    return re.sub(r"<table>.*?</table>", do_table, src, flags=re.S)


def render(rel, src, shipped):
    root = "" if rel == "index.html" else "../"
    out = replace_region(src, "header", header(root, rel, shipped), LEGACY_HEADER)
    out = replace_region(out, "footer", footer(root), LEGACY_FOOTER)
    if rel == "guides/index.html":
        out = replace_region(out, "directory", directory_block(shipped), LEGACY_DIRECTORY)
    if rel == "index.html":
        out = replace_region(out, "latest", latest_block(shipped), LEGACY_LATEST)
        out = re.sub(r"Browse all [\w-]+ guides", f"Browse all {len(shipped)} guides", out)
    out = label_tables(out)
    return out


def pages():
    out = ["index.html", "guides/index.html"]
    out += sorted(f"guides/{f}" for f in os.listdir(os.path.join(ROOT, "guides")) if f.endswith(".html") and f != "index.html")
    return out


def main():
    check = "--check" in sys.argv
    D, shipped = load()
    if harvest_summaries(D) and not check:
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(D, f, ensure_ascii=False, indent=2)
            f.write("\n")
    stale = []
    for rel in pages():
        src = read(rel)
        new = render(rel, src, shipped)
        if new != src:
            stale.append(rel)
            if not check:
                with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as f:
                    f.write(new)
    if check:
        if stale:
            print("layout.py --check: out of date:", ", ".join(stale))
            sys.exit(1)
        print("layout.py --check: all pages up to date")
    else:
        print(f"layout.py: updated {len(stale)} page(s)" + (": " + ", ".join(stale) if stale else ""))


if __name__ == "__main__":
    main()
