"""Agent-referral tagging for GOES agent files (llms.txt, JSON feeds, Markdown twins).

Shared logic, copied verbatim into each site's scripts/agent_utm.py. Only links that
agents follow out of machine-readable files are tagged; human HTML is never touched.

  goes.health (and www.)  -> ?utm_source=<src>&utm_medium=agent&utm_campaign=<site>&utm_content=<content>
  Google Play             -> &referrer=<url-encoded utm string>   (Play Console > Acquisition reports)
  Apple App Store         -> ?ct=<site>_<src>&mt=8                 (App Store Connect campaign token;
                                                                    attribution also needs pt=<provider id>,
                                                                    set APPSTORE_PROVIDER_TOKEN when known)
Subdomains (parks.goes.health, heatready.goes.health) and mailto: are left alone.
Idempotent: a URL that already carries utm_/ct=/referrer= is not re-tagged.
"""
import os, re
from urllib.parse import quote

APPSTORE_PROVIDER_TOKEN = os.environ.get("GOES_APPSTORE_PT", "")  # e.g. "123456789" from App Store Connect

_URL = re.compile(r"https://(?:www\.)?goes\.health(?:/[^\s)\]\"'<>`]*)?"
                  r"|https://apps\.apple\.com/[^\s)\]\"'<>`]*"
                  r"|https://play\.google\.com/store/apps/details\?[^\s)\]\"'<>`]*")
_TRAIL = ".,;:!?"


def tag_url(url, source, campaign, content=None):
    if re.search(r"[?&](utm_|ct=|referrer=)", url):
        return url
    if re.fullmatch(r"https://(www\.)?goes\.health", url):
        url += "/"
    sep = "&" if "?" in url else "?"
    if "apps.apple.com" in url:
        q = (f"pt={APPSTORE_PROVIDER_TOKEN}&" if APPSTORE_PROVIDER_TOKEN else "") + "ct=" + f"{campaign}_{source}"[:40] + "&mt=8"
        return url + sep + q
    utm = f"utm_source={source}&utm_medium=agent&utm_campaign={campaign}" + (f"&utm_content={content}" if content else "")
    if "play.google.com" in url:
        return url + sep + "referrer=" + quote(utm, safe="")
    return url + sep + utm


def tag_text(text, source, campaign, content=None):
    def rep(m):
        u = m.group(0)
        tail = ""
        while u and u[-1] in _TRAIL:
            tail, u = u[-1] + tail, u[:-1]
        return tag_url(u, source, campaign, content) + tail
    return _URL.sub(rep, text)
