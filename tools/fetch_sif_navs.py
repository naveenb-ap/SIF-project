"""Pull every SIF strategy's NAV from AMFI and compute the 1-day change.

Writes landing/sifdata.json (one row per strategy, direct growth where available)
and rebuilds landing/index.html (via tools/build_page.py).

Usage: python3 tools/fetch_sif_navs.py [YYYY-MM-DD previous date]
"""
import json, sys, urllib.request, datetime, pathlib

API = "https://www.amfiindia.com/api"
ROOT = pathlib.Path(__file__).resolve().parent.parent
AMC = {"Altiva SIF": "Edelweiss", "Apex SIF": "Aditya Birla Sun Life", "Arthaya SIF": "Union", "Arudha SIF": "Bandhan",
       "Diviniti SIF": "ITI", "DynaSIF SIF": "360 ONE", "iSIF SIF": "ICICI Prudential", "Magnum SIF": "SBI",
       "MSIF": "Mahindra Manulife", "qsif SIF": "Quant", "Sapphire SIF": "Franklin Templeton", "SUMMIT SIF": "Invesco",
       "Titanium SIF": "Tata", "WSIF": "The Wealth Company", "Infinity SIF": "Kotak Mahindra", "Platinum SIF": "Mirae Asset",
       "Prism SIF": "Jio BlackRock", "RedHex SIF": "HSBC"}

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)

def history(day):
    out = {}
    for h in get(f"{API}/sif-nav-history?query_type=all_for_date&from_date={day}").get("data", []):
        for sc in h["schemes"]:
            for n in sc["navs"]:
                out[n["SD_ID"]] = float(n["hNAV_Amt"])
    return out

latest = [s for t in get(f"{API}/sif-latest-nav?type=all")["data"] for c in t["categories"] for g in c["groups"] for s in g["schemes"]]
asof = datetime.datetime.strptime(latest[0]["Date"], "%d-%b-%Y").date()
prev_nav, prev_day = {}, asof
for _ in range(7):
    prev_day -= datetime.timedelta(days=1)
    if len(sys.argv) > 1:
        prev_day = datetime.date.fromisoformat(sys.argv[1])
    prev_nav = history(prev_day.isoformat())
    if prev_nav:
        break

best = {}
for s in latest:
    name = s.get("NavName") or ""
    if "regular" in name.lower() or "growth" not in name.lower() or s["Sd_Id"] not in prev_nav:
        continue
    cat = s["category"].split(" - ")[-1]
    key = (s["SIFName"], cat)
    if key in best and best[key]["nav"] >= s["NetAssetValue"]:
        continue
    brand = s["SIFName"] if s["SIFName"] in ("MSIF", "WSIF") else s["SIFName"].replace(" SIF", "")
    prev = prev_nav[s["Sd_Id"]]
    best[key] = {"b": brand, "amc": AMC.get(s["SIFName"], ""), "c": cat,
                 "t": "Interval" if "Interval" in s["type"] else "Open-ended",
                 "nav": s["NetAssetValue"], "prev": prev, "chg": round((s["NetAssetValue"] / prev - 1) * 100, 2)}

rows = sorted(best.values(), key=lambda r: (r["c"], r["b"]))
data = {"asof": asof.strftime("%d %b %Y"), "prev": prev_day.strftime("%d %b %Y"), "rows": rows}
(ROOT / "landing/sifdata.json").write_text(json.dumps(data, separators=(",", ":")))
src = (ROOT / "landing/index.src.html").read_text()
import importlib.util, sys
sys.path.insert(0, str(ROOT / "tools"))
import build_page
build_page.build()
print(f"{len(rows)} strategies, {data['prev']} -> {data['asof']}")
