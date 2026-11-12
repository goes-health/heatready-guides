#!/usr/bin/env python3
"""Ping IndexNow (Bing, Yandex, Seznam, Naver, ...) after a publish. No account or login needed.
Usage: python3 scripts/indexnow.py            # submit home, llms.txt, feed, sitemap and every HTML + .md page
       python3 scripts/indexnow.py --dry-run
Key lives in data/indexnow.json; scripts/agents.py publishes it as <key>.txt at the site root.
Run only after GitHub Pages has finished deploying (the key file must be live)."""
import json, os, sys, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import BASE, ROOT, load_data, url_of, md_url

key = json.load(open(os.path.join(ROOT, "data", "indexnow.json")))["key"]
_, shipped = load_data()
urls = [BASE, BASE + "index.md", BASE + "llms.txt", BASE + "guides.json", BASE + "sitemap.xml",
        BASE + "robots.txt", BASE + "guides/", BASE + "guides/index.md"]
for g in shipped:
    urls += [url_of(g["path"]), md_url(g["path"])]
body = {"host": urllib.parse.urlparse(BASE).netloc, "key": key, "keyLocation": f"{BASE}{key}.txt", "urlList": urls}
if "--dry-run" in sys.argv:
    print(json.dumps(body, indent=1)); sys.exit()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow:", r.status, len(urls), "URLs")
except urllib.error.HTTPError as e:
    print("IndexNow:", e.code, e.read()[:300].decode(errors="replace")); sys.exit(1)
