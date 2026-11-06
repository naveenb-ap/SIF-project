"""Build the SIF Partner Hub page from landing/index.src.html.

Fills in the two data blocks the page needs:
  __SIFDATA__    daily NAV snapshot (landing/sifdata.json, from fetch_sif_navs.py)
  __PULSEDATA__  SIF Pulse data      (landing/pulse-data.json, from build_pulse.py)

Writes two files:
  landing/index.html  page body for the Claude artifact (the artifact adds its own <head>)
  landing/site.html   a complete HTML document for public hosting (Vercel), with
                      lang, canonical URL and absolute share-image URLs

Set SITE_URL (e.g. https://sif.assetplus.in/) to emit a canonical URL, absolute
og:image links and landing/sitemap.xml.
"""
import datetime as dt
import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_URL = os.environ.get("SITE_URL", "").strip()
if SITE_URL and not SITE_URL.endswith("/"):
    SITE_URL += "/"


def build():
    src = (ROOT / "landing/index.src.html").read_text()
    nav = (ROOT / "landing/sifdata.json").read_text()
    pulse = json.loads((ROOT / "landing/pulse-data.json").read_text())
    pulse.pop("brandQuarterEnd", None)
    body = src.replace("__SIFDATA__", nav).replace("__PULSEDATA__", json.dumps(pulse, ensure_ascii=False, separators=(",", ":")))

    (ROOT / "landing/index.html").write_text(body.replace("__SITEURL__", ""))

    # full document for public hosting: move <title>, <meta>, <link> and JSON-LD into <head>
    site = body.replace("__SITEURL__", SITE_URL)
    head_bits = []
    for pat in (r"<title>.*?</title>", r"<meta [^>]*>", r"<link [^>]*>", r'<script type="application/ld\+json">.*?</script>'):
        for m in re.findall(pat, site, flags=re.S):
            if "claude:" in m:
                site = site.replace(m, "", 1)
                continue
            head_bits.append(m)
            site = site.replace(m, "", 1)
    if SITE_URL:
        head_bits.append('<link rel="canonical" href="%s">' % SITE_URL)
        head_bits.append('<meta property="og:url" content="%s">' % SITE_URL)
    head_bits.append('<link rel="icon" href="logo-light.png">')
    doc = ('<!doctype html>\n<html lang="en-IN">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           + "\n".join(head_bits) + "\n</head>\n<body>\n" + site.strip() + "\n</body>\n</html>\n")
    (ROOT / "landing/site.html").write_text(doc)

    robots = "User-agent: *\nAllow: /\nDisallow: /pdfs/\n"
    if SITE_URL:
        robots += "Sitemap: %ssitemap.xml\n" % SITE_URL
        (ROOT / "landing/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>\n</urlset>\n"
            % (SITE_URL, dt.date.today().isoformat()))
    (ROOT / "landing/robots.txt").write_text(robots)


if __name__ == "__main__":
    build()
