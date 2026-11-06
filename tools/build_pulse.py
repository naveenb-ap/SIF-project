"""Build the data for the SIF Pulse section of the landing page from AMFI's SIF APIs:

  * latest NAV for every strategy          /api/sif-latest-nav?type=all
  * NAV on past dates (1M, 3M, 6M)         /api/sif-nav-history?query_type=all_for_date
  * launch dates                           /api/investment-strategy-detail?sif_id=
  * average AUM per strategy (quarterly)   /api/sif-average-aum-schemewise
  * AUM by SIF brand (quarter-end)         /api/sif-average-aum-fundwise

Monthly industry AUM, net flows and folios have no AMFI API; those stay as
published in AMFI's monthly release and are labelled as such on the page.

Usage: python3 tools/build_pulse.py
Writes landing/pulse-data.json and rebuilds landing/index.html, whose SIF Pulse section uses it.
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
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import build_page
    build_page.build()
    print("%d strategies, NAV %s, AUM %s" % (len(funds), asof, per["period"]))


if __name__ == "__main__":
    main()
