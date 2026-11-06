"""Build the AssetPlus SIF Pulse page from live AMFI data.

Uses the design in landing/pulse.src.html and replaces its strategy list,
category totals and dated text with figures pulled from AMFI's own SIF APIs:

  * latest NAV for every strategy          /api/sif-latest-nav?type=all
  * NAV on past dates (1M, 3M, 6M)         /api/sif-nav-history?query_type=all_for_date
  * launch dates                           /api/investment-strategy-detail?sif_id=
  * average AUM per strategy (quarterly)   /api/sif-average-aum-schemewise
  * AUM by SIF brand (quarter-end)         /api/sif-average-aum-fundwise

Monthly industry AUM, net flows and folios have no AMFI API; those stay as
published in AMFI's monthly release and are labelled as such on the page.

Usage: python3 tools/build_pulse.py
Writes landing/pulse.html and landing/pulse-data.json.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.request

API = "https://www.amfiindia.com/api"
ROOT = pathlib.Path(__file__).resolve().parent.parent
AMC = {"Altiva": "Edelweiss", "Apex": "Aditya Birla Sun Life", "Arthaya": "Union", "Arudha": "Bandhan",
       "Diviniti": "ITI", "DynaSIF": "360 ONE", "iSIF": "ICICI Prudential", "Magnum": "SBI",
       "MSIF": "Mahindra Manulife", "qSIF": "Quant", "Sapphire": "Franklin Templeton", "Summit": "Invesco",
       "Titanium": "Tata", "WSIF": "The Wealth Company", "Infinity": "Kotak Mahindra", "Platinum": "Mirae Asset",
       "Prism": "Jio BlackRock", "RedHex": "HSBC", "Eminence": "AlphaGrep"}
CATS = {"Hybrid Long-Short Fund": "Hybrid Long-Short", "Equity Ex-Top 100 Long-Short Fund": "Equity Ex-Top 100",
        "Equity Long-Short Fund": "Equity Long-Short", "Active Asset Allocator Long-Short Fund": "Active Asset Allocator",
        "Sector Rotation Long-Short Fund": "Sector Rotation"}


def get(path):
    with urllib.request.urlopen(API + path, timeout=90) as r:
        return json.load(r)


def brand_of(sif_name):
    b = sif_name.replace(" SIF", "").strip()
    return {"qsif": "qSIF", "SUMMIT": "Summit"}.get(b, b)


def short_cat(desc):
    tail = desc.split(" - ")[-1].strip()
    return CATS.get(tail, tail)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("ex- top", "ex-top"))


def strategy_name(nav_name):
    n = re.split(r"\s*-\s*(Direct|Regular)|\s*(Direct|Regular)\s+(Plan|Growth)|-Direct|-Regular", nav_name, maxsplit=1)[0]
    return re.sub(r"\s+", " ", n.replace(" - ", "-")).strip(" -")


def navs_on(day):
    """All SIF NAVs on a date, stepping back up to 7 days for holidays."""
    for back in range(8):
        d = day - dt.timedelta(days=back)
        js = get("/sif-nav-history?query_type=all_for_date&from_date=" + d.isoformat())
        out = {}
        for h in js.get("data") or []:
            for sc in h["schemes"]:
                for n in sc["navs"]:
                    out[n["SD_ID"]] = float(n["hNAV_Amt"])
        if out:
            return d, out
    return day, {}


def main():
    latest = [s for t in get("/sif-latest-nav?type=all")["data"] for c in t["categories"] for g in c["groups"] for s in g["schemes"]]
    asof = dt.datetime.strptime(latest[0]["Date"], "%d-%b-%Y").date()

    # one row per strategy: Regular Growth, else Direct Growth
    picks = {}
    for s in latest:
        name = s.get("NavName") or ""
        low = name.lower()
        if "growth" not in low and (s.get("Option") or "").lower() != "growth":
            continue
        key = (s["SIFName"], s["category"])
        rank = 0 if "regular" in low else 1
        if key not in picks or rank < picks[key][0]:
            picks[key] = (rank, s)

    # launch dates by (brand, category)
    launch = {}
    for sif_id in sorted({s["sifId"] for s in latest}):
        try:
            for d in get("/investment-strategy-detail?sif_id=" + str(sif_id)).get("data") or []:
                if d.get("Launch_Date"):
                    ld = dt.datetime.fromisoformat(d["Launch_Date"].replace("Z", "+00:00")).date() + dt.timedelta(days=1)
                    launch[(brand_of(d["SIF_Name"]), short_cat(d["SchemeCat_Desc"]))] = ld
        except Exception:
            pass

    periods = {"m1": 30, "m3": 91, "m6": 182}
    hist = {k: navs_on(asof - dt.timedelta(days=v)) for k, v in periods.items()}

    # average AUM by strategy, latest quarter (₹ lakh -> ₹ crore)
    fy = get("/sif-average-aum-fundwise")["data"][0]["id"]
    per = get("/sif-average-aum-fundwise?fyId=%s" % fy)["data"]["periods"][0]
    aum_rows = get("/sif-average-aum-schemewise?strType=Categorywise&fyId=%s&periodId=%s&SIF_Id=0" % (fy, per["id"]))["data"]
    aum = {}
    for r in aum_rows:
        aum[(brand_of(r["sifname"]), short_cat(r["SchemeCat_Desc"]))] = round(float(r["totalAUM"]["AverageAum"]) / 100)
    brand_q = get("/sif-average-aum-fundwise?fyId=%s&periodId=%s" % (fy, per["id"]))

    funds = []
    for (sif, cat_desc), (_, s) in picks.items():
        brand, cat = brand_of(sif), short_cat(cat_desc)
        nav = float(s["NetAssetValue"])
        name = brand + " " + {"Equity Ex-Top 100": "Equity Ex-Top 100 Long-Short", "Active Asset Allocator": "Active Asset Allocator Long-Short", "Sector Rotation": "Sector Rotation Long-Short"}.get(cat, cat)
        ld = launch.get((brand, cat))
        row = {"name": name, "brand": brand, "amc": AMC.get(brand, ""), "cat": cat, "aum": aum.get((brand, cat)),
               "nav": round(nav, 4), "launch": ld.isoformat() if ld else None, "sd": s["Sd_Id"]}
        for k, (d, m) in hist.items():
            old = m.get(s["Sd_Id"])
            row[k] = round((nav / old - 1) * 100, 2) if old and (ld is None or ld <= d) else None
        face = 1000 if nav > 300 else 10
        row["si"] = round((nav / face - 1) * 100, 2)
        funds.append(row)
    funds.sort(key=lambda f: -(f["aum"] or 0))

    cats = {}
    for f in funds:
        c = cats.setdefault(f["cat"], {"name": f["cat"], "n": 0, "aum": 0})
        c["n"] += 1
        c["aum"] += f["aum"] or 0
    cats = sorted(cats.values(), key=lambda c: -c["aum"])

    data = {"asof": asof.isoformat(), "aumPeriod": per["period"], "funds": funds, "cats": cats,
            "brandQuarterEnd": brand_q.get("data"), "periodDates": {k: v[0].isoformat() for k, v in hist.items()}}
    (ROOT / "landing/pulse-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    build_html(data)
    print("%d strategies, NAV %s, AUM %s" % (len(funds), asof, per["period"]))


def build_html(data):
    src = (ROOT / "landing/pulse.src.html").read_text()
    asof = dt.date.fromisoformat(data["asof"])
    asof_txt = asof.strftime("%-d %b %Y")
    funds, cats = data["funds"], data["cats"]
    HL, EX, EL, AA, SR = "Hybrid Long-Short", "Equity Ex-Top 100", "Equity Long-Short", "Active Asset Allocator", "Sector Rotation"
    js_cat = {HL: "HL", EX: "EX", EL: "EL", AA: "AA", SR: "SR"}

    def lit(v):
        return "null" if v is None else json.dumps(v, ensure_ascii=False)

    fund_lines = ",\n".join("    [%s,%s,%s,%s,%s,%s,%s,%s,%s,%s]" % (
        lit(f["name"]), lit(f["brand"]), lit(f["amc"]), js_cat.get(f["cat"], lit(f["cat"])), lit(f["aum"]),
        lit(f["nav"]), lit(f["m1"]), lit(f["m3"]), lit(f["m6"]), lit(f["si"])) for f in funds)
    src, n_f = re.subn(r"const funds = \[.*?\n  \]\.map", lambda m: "const funds = [\n" + fund_lines + "\n  ].map", src, count=1, flags=re.S)
    assert n_f == 1, "fund list not found in template"
    cat_lines = ",\n".join('    { name: %s, n: %d, aum: %d }' % (json.dumps({"Equity Ex-Top 100": "Equity Ex-Top 100 Long-Short"}.get(c["name"], c["name"])), c["n"], c["aum"]) for c in cats)
    src, n_c = re.subn(r"const cats = \[.*?\n  \];", lambda m: "const cats = [\n" + cat_lines + "\n  ];", src, count=1, flags=re.S)
    assert n_c == 1, "category list not found in template"

    with_m1 = sorted([f for f in funds if f["m1"] is not None], key=lambda f: -f["m1"])
    ups = [f for f in with_m1 if f["m1"] > 0]
    median = with_m1[len(with_m1) // 2]["m1"] if with_m1 else 0
    if len(ups) <= 3:
        who = (" Up: " + ", ".join(f["name"] for f in ups) + ".") if ups else ""
    else:
        who = ""
    breadth_js = "`${up} of ${withM1.length} strategies with a one-month record were up.%s The median strategy %s %s%%.`" % (
        who.replace("`", ""), "rose" if median >= 0 else "fell", "%.2f" % abs(median))
    src = re.sub(r"document\.getElementById\(\"breadthText\"\)\.textContent = `.*?`;",
                 "document.getElementById(\"breadthText\").textContent = " + breadth_js + ";", src, count=1, flags=re.S)
    headline = "One month to %s: %d of %d strategies up" % (asof.strftime("%-d %b"), len(ups), len(with_m1))

    reps = [
        ("SIF Pulse · November 2026 edition", "SIF Pulse · Live AMFI data · NAV " + asof_txt),
        ('<div class="value num">36</div><div class="sub">34 in AMFI’s Sep count</div>', '<div class="value num">%d</div><div class="sub">with a live NAV on AMFI</div>' % len(funds)),
        ("NAV &amp; returns 26 Oct 2026 · Regular, Growth · AUM Sep 2026", "NAV &amp; returns %s · Regular, Growth · Average AUM %s" % (asof_txt, data["aumPeriod"])),
        ("A tough October for long-short equity", headline),
        ("<span class=\"asof\">To 26 Oct 2026</span>", "<span class=\"asof\">To %s</span>" % asof_txt),
    ]
    tot = sum(f["aum"] or 0 for f in funds) or 1
    top5 = sum(sorted([f["aum"] or 0 for f in funds], reverse=True)[:5]) / tot * 100
    brands = {}
    for f in funds:
        brands[f["brand"]] = brands.get(f["brand"], 0) + (f["aum"] or 0)
    bl = sorted(brands.items(), key=lambda x: -x[1])
    b1 = bl[0][1] / tot * 100
    b3 = sum(v for _, v in bl[:3]) / tot * 100
    hyb = next((c["aum"] for c in cats if c["name"] == "Hybrid Long-Short"), 0) / tot * 100
    frac = lambda x: "about a third" if 30 <= x < 37 else "about two-thirds" if 62 <= x < 70 else "about half" if 45 <= x < 55 else "%.0f%%" % x
    reps += [
        ("Hybrid long-short holds almost two-thirds", "Hybrid long-short holds %.0f%% of SIF money" % hyb),
        ('<span class="asof">30 Sep 2026 · AMFI</span>', '<span class="asof">Average AUM, %s · AMFI</span>' % data["aumPeriod"]),
        ("Five strategies hold 59% of all SIF money", "Five strategies hold %.0f%% of all SIF money" % top5),
        ("Share of strategy AUM, Sep 2026", "Share of average AUM, %s" % data["aumPeriod"]),
        ("Altiva (Edelweiss) alone is a third of the market; the top three brands (Altiva, iSIF and Magnum) hold about two-thirds.",
         "%s (%s) alone holds %.0f%% of the market; the top three brands (%s) hold %.0f%%." % (bl[0][0], AMC.get(bl[0][0], ""), b1, ", ".join(x for x, _ in bl[:3]), b3)),
    ]
    for a, b in reps:
        src = src.replace(a, b)
    src = re.sub(r"<p><b style=\"color:var\(--ink\)\">Sources\.</b>.*?</p>",
                 "<p><b style=\"color:var(--ink)\">Sources.</b> Strategy NAVs, 1M/3M/6M returns, launch dates and average AUM: AMFI SIF APIs (amfiindia.com), NAV as of %s, average AUM for %s. Monthly industry AUM, net inflows, folios and category flows: AMFI monthly SIF data as published; September flow and redemption detail: Matasec SIF Industry Pulse. Rules: SEBI.</p>" % (asof_txt, data["aumPeriod"]),
                 src, count=1, flags=re.S)
    src = re.sub(r"<p>Strategy AUMs total about .*?</p>",
                 "<p>Returns are absolute, not annualised, on the Regular plan, growth option. Since-launch returns are measured from the allotment price (₹10, or ₹1,000 where that is the face value). A period shows “–” when the strategy launched after the start of that period. Strategy AUM is AMFI’s average AUM for the quarter, so it differs from month-end industry figures. Brand shares are computed from strategy AUM. Updated automatically from AMFI.</p>",
                 src, count=1, flags=re.S)
    src = re.sub(r"Prepared by AssetPlus Research, [^.<]+\.", "Prepared by AssetPlus Research from AMFI data, %s." % asof_txt, src)
    (ROOT / "landing/pulse.html").write_text(src)


if __name__ == "__main__":
    main()
