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


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _pct(v):
    if v is None:
        return "–"
    return ("+" if v > 0 else "−" if v < 0 else "") + "%.2f%%" % abs(v)


def prerender(body, nav, pulse):
    """Write real numbers into the HTML so search engines and link previews see them without running scripts."""
    funds = pulse["funds"]
    day = dt.date.fromisoformat(pulse["asof"])
    day_txt = day.strftime("%-d %b %Y")
    rows = nav["rows"]
    up = sum(1 for r in rows if r["chg"] > 0)
    m1 = [f for f in funds if f.get("m1") is not None]
    cls = lambda v: "na" if v is None else "up" if v > 0 else "down" if v < 0 else ""
    trs = []
    for f in sorted(funds, key=lambda f: -(f.get("aum") or 0))[:10]:
        ld = dt.date.fromisoformat(f["launch"]).strftime("%-d %b %y") if f.get("launch") else "–"
        trs.append('<tr><td class="pz-name"><b>%s</b><small>%s</small></td><td><span class="pz-pill">%s</span></td><td class="num pz-ld">%s</td><td class="r num">%s</td><td class="r num">%s</td>'
                   '<td class="r num"><span class="pz-ret na">–</span></td>%s<td class="r num"><span class="pz-si %s">%s</span></td></tr>' % (
                       _esc(f["name"]), _esc(f["amc"]), _esc(f["cat"]), ld, "–" if f.get("aum") is None else format(f["aum"], ","), "%.2f" % f["nav"],
                       "".join('<td class="r num"><span class="pz-ret %s">%s</span></td>' % (cls(f.get(k)), _pct(f.get(k))) for k in ("m1", "m3", "m6", "m12")),
                       cls(f.get("si")), _pct(f.get("si"))))
    rep = {
        "__PZ_ROWS__": "".join(trs),
        "__PZ_ASOF__": "NAV as of %s. Average AUM for %s." % (day_txt, pulse["aumPeriod"]),
        "__PZ_N__": str(len(funds)),
        "__PZ_UP__": "%d of %d" % (up, len(rows)),
        "__PZ_B__": str(len({f["brand"] for f in funds})),
        "__PS_TXT__": "<b>%d strategies</b> · NAV %s · %d of %d up on the day · launch date, 1M to 12M returns" % (len(funds), day.strftime("%-d %b"), up, len(rows)),
    }
    for k, v in rep.items():
        body = body.replace(k, v)

    # structured data from what is visible on the page
    faqs = []
    for q, a in re.findall(r"<details><summary>(.*?)</summary><div class=\"ans\">(.*?)</div></details>", body, flags=re.S):
        a = re.sub(r'<span data-closed="[^"]*">(.*?)</span>', r"\1", a)
        faqs.append({"@type": "Question", "name": re.sub("<[^>]+>", "", q).strip(),
                     "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", a)).strip()}})
    dataset = {"@context": "https://schema.org", "@type": "Dataset", "name": "SIF Pulse: NAV, returns and AUM of every SIF strategy in India",
               "description": "Daily NAV and 1-month, 3-month, 6-month and since-launch returns, with quarterly average AUM, for every live Specialised Investment Fund strategy, built from AMFI data.",
               "creator": {"@type": "Organization", "name": "AssetPlus"}, "isBasedOn": "https://www.amfiindia.com/sif",
               "dateModified": pulse["asof"], "temporalCoverage": "2025-10/" + pulse["asof"], "variableMeasured": ["NAV", "Launch date", "1M return", "3M return", "6M return", "12M return", "Since-launch return", "Average AUM"],
               "keywords": ["SIF", "Specialised Investment Fund", "SIF NAV", "SIF returns", "AMFI"]}
    items = {"@context": "https://schema.org", "@type": "ItemList", "name": "Live SIF strategies in India", "numberOfItems": len(funds),
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": "%s (%s, %s)" % (f["name"], f["amc"], f["cat"])} for i, f in enumerate(sorted(funds, key=lambda f: f["name"]))]}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', body, flags=re.S)
    ld = [x for x in json.loads(m.group(1)) if x.get("@type") not in ("FAQPage", "Dataset", "ItemList")]
    ld += [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs}, dataset, items]
    body = body[:m.start()] + '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>" + body[m.end():]
    body = body.replace('<meta name="robots"', '<meta property="article:modified_time" content="%sT23:00:00+05:30">\n<meta name="robots"' % pulse["asof"], 1)
    return body


def build():
    src = (ROOT / "landing/index.src.html").read_text()
    nav = (ROOT / "landing/sifdata.json").read_text()
    pulse = json.loads((ROOT / "landing/pulse-data.json").read_text())
    pulse.pop("brandQuarterEnd", None)
    body = src.replace("__SIFDATA__", nav).replace("__PULSEDATA__", json.dumps(pulse, ensure_ascii=False, separators=(",", ":")))
    body = prerender(body, json.loads(nav), pulse)

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
