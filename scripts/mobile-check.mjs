#!/usr/bin/env node
// HeatReady mobile-first gate. Run before every publish; exits 1 on any failure.
//
//   node scripts/mobile-check.mjs                       # serve this folder locally, check every page
//   node scripts/mobile-check.mjs --base https://heatready.goes.health/   # check the live site
//   node scripts/mobile-check.mjs --only guides/memphis-construction.html
//   node scripts/mobile-check.mjs --screenshots /workspace/mobile-review/heatready/after
//
// Browser: uses $CHROME_PATH, else /usr/bin/google-chrome, else playwright-core's bundled chromium.
import { chromium } from "playwright-core";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opt = (name, dflt = null) => {
  const i = args.indexOf(name);
  return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith("--") ? args[i + 1] : true) : dflt;
};
const SHOTS = opt("--screenshots");
const ONLY = opt("--only");
let BASE = opt("--base");

const VIEWPORTS = [
  { name: "iphone-375", width: 375, height: 812, mobile: true },
  { name: "iphone-390", width: 390, height: 844, mobile: true },
  { name: "tablet-768", width: 768, height: 1024, mobile: false },
  { name: "desktop-1280", width: 1280, height: 800, mobile: false },
];
const RULES = {
  maxHeaderMobile: 120,     // px, sticky header height at phone widths
  maxHeaderDesktop: 96,
  minBodyFont: 16,          // px, running text
  minSmallPrint: 13,        // px, labels / eyebrows / legal small print
  minTap: 44,               // px, both dimensions, phone widths
  maxLineEm: 46,            // paragraph width in em (≈ 75-85 characters)
};
// Elements allowed to use small print (labels, captions, legal lines).
const SMALL_PRINT = [
  ".eyebrow", ".meta", ".status", ".badge", "th", ".cite", ".cta-disclaimer",
  ".footer-disclaimer", ".site-footer", ".partner-line", ".soon", ".menu-label",
  ".chip-count", ".brand-lockup", "td[data-label]::before", ".nav-cta", ".count",
];

function pagesFromDisk() {
  const out = ["index.html", "guides/index.html"];
  for (const f of fs.readdirSync(path.join(ROOT, "guides")).sort())
    if (f.endsWith(".html") && f !== "index.html") out.push(`guides/${f}`);
  return out;
}

function serve() {
  const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
    ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json", ".txt": "text/plain" };
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "index.html";
    const f = path.join(ROOT, p);
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise((r) => srv.listen(0, "127.0.0.1", () => r(srv)));
}

function launchOpts() {
  const exe = process.env.CHROME_PATH || (fs.existsSync("/usr/bin/google-chrome") ? "/usr/bin/google-chrome" : undefined);
  return exe ? { executablePath: exe, headless: true } : { headless: true };
}

// Runs in the page. Returns a list of failure strings.
function audit({ rules, smallPrint, mobile }) {
  const fails = [];
  const vw = document.documentElement.clientWidth;
  const vh = window.innerHeight;
  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && !el.closest("[hidden],details:not([open]) > :not(summary)");
  };
  const label = (el) => {
    const t = (el.innerText || el.getAttribute("alt") || "").trim().replace(/\s+/g, " ").slice(0, 40);
    return `<${el.tagName.toLowerCase()}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : ""}>${t ? ` "${t}"` : ""}`;
  };
  const inScroller = (el) => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") return true;
    }
    return false;
  };

  // 1. viewport meta
  const vp = document.querySelector('meta[name="viewport"]');
  if (!vp || !/width=device-width/.test(vp.content) || !/initial-scale=1/.test(vp.content))
    fails.push("viewport meta missing or wrong (need width=device-width, initial-scale=1)");
  if (vp && /user-scalable=no|maximum-scale=1(\D|$)/.test(vp.content)) fails.push("viewport blocks pinch zoom");

  // 2. horizontal scroll
  const sw = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  if (sw > vw + 1) {
    const off = [...document.querySelectorAll("body *")]
      .filter((el) => visible(el) && !inScroller(el) && el.getBoundingClientRect().right > vw + 1)
      .slice(0, 5).map(label);
    fails.push(`horizontal scroll: scrollWidth ${sw} > ${vw}; overflowing: ${off.join(", ")}`);
  }

  // 3. header height
  const hdr = document.querySelector(".site-header");
  if (!hdr) fails.push("no .site-header");
  else {
    const h = hdr.getBoundingClientRect().height;
    const max = mobile ? rules.maxHeaderMobile : rules.maxHeaderDesktop;
    if (h > max) fails.push(`header is ${Math.round(h)}px tall (max ${max})`);
    // header items must not overlap or clip (e.g. site name hidden behind the CTA)
    const items = [...hdr.querySelectorAll(".inner > *")].filter(visible);
    for (let i = 0; i + 1 < items.length; i++) {
      const a = items[i].getBoundingClientRect(), b = items[i + 1].getBoundingClientRect();
      if (a.right > b.left + 0.5) fails.push(`header items overlap: ${label(items[i])} runs into ${label(items[i + 1])}`);
    }
    for (const el of hdr.querySelectorAll(".brand-lockup, .brand-lockup *, .nav-cta"))
      if (visible(el) && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).display !== "inline") fails.push(`header text clipped: ${label(el)}`);
    if (hdr.querySelector(".inner").getBoundingClientRect().right > vw + 0.5) fails.push("header row wider than viewport");
    const navLinks = hdr.querySelectorAll('a[href*="guides/"]:not([href$="guides/index.html"]):not([href$="guides/"])');
    const guideLinks = [...hdr.querySelectorAll("a")].filter((a) => /guides\/[^/]+\.html$|^[a-z0-9-]+\.html$/.test(a.getAttribute("href") || "") && !/index\.html$/.test(a.getAttribute("href")));
    if (guideLinks.length > 0) fails.push(`header links to ${guideLinks.length} individual guide page(s); guides belong in the directory`);
    void navLinks;
  }

  // 4. font sizes
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    if (!el || seen.has(el) || !visible(el) || el.closest("script,style,noscript,[aria-hidden=true],.visually-hidden")) continue;
    seen.add(el);
    const fs = parseFloat(getComputedStyle(el).fontSize);
    const small = smallPrint.some((sel) => !sel.includes("::") && el.closest(sel));
    const min = small ? rules.minSmallPrint : rules.minBodyFont;
    if (fs + 0.01 < min) fails.push(`font ${fs.toFixed(1)}px < ${min}px: ${label(el)}`);
  }

  // 5. tap targets (phone widths)
  if (mobile) {
    for (const el of document.querySelectorAll("a[href], button, summary, input, select, textarea")) {
      if (!visible(el)) continue;
      const s = getComputedStyle(el);
      if (s.display === "inline") {
        // WCAG 2.5.8 inline exception: links inside a sentence of running text
        const block = el.closest("p, li, td, dd, figcaption, .faq details");
        const own = (el.innerText || "").trim().length;
        if (block && (block.innerText || "").trim().length > own + 3) continue;
      }
      // stretched links (::after covering the card) use the card as the tap area
      const after = getComputedStyle(el, "::after");
      const r = after.content !== "none" && after.position === "absolute" && el.offsetParent
        ? el.offsetParent.getBoundingClientRect() : el.getBoundingClientRect();
      if (r.height + 0.5 < rules.minTap || r.width + 0.5 < rules.minTap)
        fails.push(`tap target ${Math.round(r.width)}x${Math.round(r.height)} < ${rules.minTap}: ${label(el)}`);
    }
  }

  // 6. CTA above the fold (phone widths): a visible GOES link styled as a button in the first screen
  if (mobile) {
    const cta = [...document.querySelectorAll('a[href^="https://goes.health"]')].find((a) => {
      if (!visible(a)) return false;
      const r = a.getBoundingClientRect();
      return r.top >= 0 && r.bottom <= vh && r.height >= rules.minTap && /btn|cta/.test(a.className);
    });
    if (!cta) fails.push("no GOES CTA button visible in the first screen");
  }

  // 7. line length
  for (const p of document.querySelectorAll("main p, main li")) {
    if (!visible(p)) continue;
    const em = p.getBoundingClientRect().width / parseFloat(getComputedStyle(p).fontSize);
    if (em > rules.maxLineEm) { fails.push(`line too long (${Math.round(em)}em): ${label(p)}`); break; }
  }

  // 8. images scale
  for (const img of document.querySelectorAll("img")) {
    if (!visible(img)) continue;
    const r = img.getBoundingClientRect();
    if (r.width > vw + 1) fails.push(`image wider than viewport: ${img.getAttribute("src")}`);
    if (img.complete && img.naturalWidth === 0) fails.push(`broken image: ${img.getAttribute("src")}`);
  }

  // 9. tables: must fit or sit in a horizontal scroller
  for (const t of document.querySelectorAll("table")) {
    if (!visible(t)) continue;
    if (t.getBoundingClientRect().right > vw + 1 && !inScroller(t)) fails.push("table overflows and is not in a scroll container");
  }
  return [...new Set(fails)];
}

async function main() {
  let srv = null;
  if (!BASE) { srv = await serve(); BASE = `http://127.0.0.1:${srv.address().port}/`; }
  if (!BASE.endsWith("/")) BASE += "/";
  const pages = ONLY ? String(ONLY).split(",") : pagesFromDisk();
  const browser = await chromium.launch(launchOpts());
  let failed = 0, checks = 0;
  for (const vpd of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vpd.width, height: vpd.height },
      reducedMotion: "reduce", deviceScaleFactor: vpd.mobile ? 3 : 1, isMobile: vpd.mobile, hasTouch: vpd.mobile,
      userAgent: vpd.mobile ? "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1" : undefined,
    });
    const page = await ctx.newPage();
    for (const p of pages) {
      checks++;
      const url = BASE + p.replace(/^\//, "") + (BASE.startsWith("http://127.0.0.1") ? "" : `?mc=${Date.now()}`);
      const resp = await page.goto(url, { waitUntil: "networkidle" }).catch((e) => ({ status: () => String(e.message).slice(0, 80) }));
      let fails = resp && resp.status() === 200 ? [] : [`HTTP ${resp && resp.status()}`];
      if (!fails.length) {
        await page.evaluate(() => document.fonts && document.fonts.ready);
        fails = await page.evaluate(audit, { rules: RULES, smallPrint: SMALL_PRINT, mobile: vpd.mobile });
        // mobile menu: must open, show 44px links, and not cause horizontal scroll
        const toggle = page.locator(".menu > summary");
        if (vpd.mobile && (await toggle.count()) && (await toggle.isVisible())) {
          await toggle.click();
          const menu = await page.evaluate((minTap) => {
            const panel = document.querySelector(".menu-panel");
            if (!panel || !panel.getBoundingClientRect().height) return ["menu does not open"];
            const f = [];
            for (const a of panel.querySelectorAll("a")) {
              const r = a.getBoundingClientRect();
              if (r.height + 0.5 < minTap) f.push(`menu link ${Math.round(r.height)}px tall: ${a.innerText.trim()}`);
            }
            const vw = document.documentElement.clientWidth;
            if (document.documentElement.scrollWidth > vw + 1) f.push("menu causes horizontal scroll");
            if (panel.getBoundingClientRect().bottom > window.innerHeight + 1 && getComputedStyle(panel).overflowY === "visible")
              f.push("open menu runs off screen without scrolling");
            return f;
          }, RULES.minTap);
          fails.push(...menu);
          if (SHOTS) {
            const dir = path.join(SHOTS, vpd.name);
            fs.mkdirSync(dir, { recursive: true });
            await page.screenshot({ path: path.join(dir, `${p.replace(/\//g, "__").replace(/\.html$/, "")}--menu-open.png`) });
          }
          await toggle.click();
        }
      }
      if (SHOTS) {
        const dir = path.join(SHOTS, vpd.name);
        fs.mkdirSync(dir, { recursive: true });
        const base = path.join(dir, p.replace(/\//g, "__").replace(/\.html$/, ""));
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${base}--first-screen.png` });
        await page.screenshot({ path: `${base}--full.png`, fullPage: true });
      }
      const tag = `${vpd.name.padEnd(13)} ${p}`;
      if (fails.length) {
        failed++;
        console.log(`FAIL ${tag}`);
        for (const f of fails.slice(0, 12)) console.log(`     - ${f}`);
        if (fails.length > 12) console.log(`     … ${fails.length - 12} more`);
      } else console.log(`ok   ${tag}`);
    }
    await ctx.close();
  }
  await browser.close();
  if (srv) srv.close();
  console.log(`\n${checks - failed}/${checks} page×viewport checks passed (${pages.length} pages × ${VIEWPORTS.length} viewports) against ${BASE}`);
  process.exit(failed ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
