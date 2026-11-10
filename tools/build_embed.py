"""Build landing/pulse-embed.html: a self-contained SIF Pulse page for the
AssetPlus partner dashboard (open directly or embed in an iframe).

Same AMFI data as the landing page (pulse-data.json + sifdata.json), rebuilt
with the nightly refresh. No external scripts; works offline once loaded.
"""
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def build():
    pulse = json.loads((ROOT / "landing/pulse-data.json").read_text())
    nav = json.loads((ROOT / "landing/sifdata.json").read_text())
    norm = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
    catkey = lambda c: norm(c).replace("longshort", "").replace("fund", "")
    d1 = {norm("qsif" if r["b"] == "qsif" else r["b"]) + "|" + catkey(r["c"].replace("Equity Ex-Top 100 Long-Short Fund", "Equity Ex-Top 100")): r["chg"] for r in nav["rows"]}
    funds = []
    for f in pulse["funds"]:
        g = dict(f)
        g["d1"] = d1.get(norm(f["brand"]) + "|" + catkey(f["cat"]))
        funds.append(g)
    asof = dt.date.fromisoformat(pulse["asof"]).strftime("%-d %b %Y")
    data = json.dumps({"asof": asof, "aum": pulse["aumPeriod"], "funds": funds, "cats": pulse["cats"]}, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.replace("__DATA__", data).replace("__ASOF__", asof)
    (ROOT / "landing/pulse-embed.html").write_text(html)


TEMPLATE = r'''<!doctype html>
<html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIF Pulse | AssetPlus Partner</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@600;700&family=Inter:wght@400;500;600&display=swap">
<style>
:root{--ink:#1B1F28;--body:#33415C;--muted:#5B6B86;--line:#E3E9F4;--bg:#F7F9FD;--brand:#2B4FA8;--soft:#EEF4FF;--pos:#15803D;--posbg:#E7F6EC;--neg:#B3261E;--negbg:#FCE9E7;--red:#D63B3B}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--body);font:14px/1.5 Inter,"Segoe UI",Arial,sans-serif}
.w{max-width:1180px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px))}
h1{font:700 24px Geist,Inter,sans-serif;color:var(--brand);margin:0}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.live{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--red);border:1.5px solid var(--red);border-radius:999px;padding:2px 10px}
.live i{width:7px;height:7px;border-radius:50%;background:var(--red)}
.sub{color:var(--muted);font-size:13px}
.k{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:#fff;border:1px solid var(--line);border-radius:14px;margin-bottom:14px}
.k div{padding:12px 16px;border-left:1px solid var(--line)}.k div:first-child{border-left:0}
.k b{display:block;font:700 22px Geist,Inter,sans-serif;color:var(--ink)}.k span{font-size:12px;color:var(--muted)}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-bottom:10px}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{all:unset;cursor:pointer;font-size:13px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:#fff}
.chip[aria-pressed=true]{background:var(--brand);color:#fff;border-color:var(--brand)}
input{font:inherit;padding:8px 12px;border:1px solid var(--line);border-radius:10px;width:240px;max-width:100%}
.tb{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%;min-width:980px}th,td{padding:10px 9px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}td.n{white-space:normal;min-width:180px}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);background:#F1F4FA;position:sticky;top:0}
th button{all:unset;cursor:pointer}td.r,th.r{text-align:right}tr:last-child td{border-bottom:0}
.n b{display:block;color:var(--ink);font-weight:600}.n small{color:var(--muted);font-size:12px}
.p{font-size:11.5px;color:var(--brand);background:var(--soft);padding:2px 8px;border-radius:999px}
.up{color:var(--pos)}.dn{color:var(--neg)}.na{color:var(--muted)}
.si{font-weight:700;padding:2px 7px;border-radius:6px}.si.up{background:var(--posbg)}.si.dn{background:var(--negbg)}
.note{font-size:11.5px;color:var(--muted);margin-top:12px}
@media(max-width:700px){.k{grid-template-columns:1fr 1fr}.k div:nth-child(3){border-left:0}.k div:nth-child(n+3){border-top:1px solid var(--line)}}
</style></head><body><div class="w">
<div class="top"><div><h1>SIF Pulse</h1><div class="sub">Every live SIF strategy, from AMFI. NAV as of __ASOF__.</div></div><span class="live"><i></i>Updated every evening</span></div>
<div class="k" id="k"></div>
<div class="bar"><div class="chips" id="chips"></div><input id="q" type="search" placeholder="Search strategy, brand or AMC" aria-label="Search strategies"></div>
<div class="tb"><table id="t"><thead><tr>
<th data-k="name"><button>Strategy</button></th><th data-k="cat"><button>Category</button></th><th data-k="launch"><button>Launched</button></th>
<th data-k="aum" class="r"><button>Avg AUM ₹ cr</button></th><th data-k="nav" class="r"><button>NAV ₹</button></th><th data-k="d1" class="r"><button>1D</button></th>
<th data-k="m1" class="r"><button>1M</button></th><th data-k="m3" class="r"><button>3M</button></th><th data-k="m6" class="r"><button>6M</button></th>
<th data-k="m12" class="r"><button>12M</button></th><th data-k="si" class="r"><button>Since launch</button></th></tr></thead><tbody></tbody></table></div>
<p class="note">Source: AMFI SIF NAV and average AUM data (amfiindia.com). NAV and returns on the Regular plan, growth option; 1D on the Direct plan. Returns are absolute, not annualised. “–” means the strategy launched after the start of that period. Since-launch returns cover different periods; read them with the launch date. Average AUM for <span id="aum"></span>. For AssetPlus partners (mutual fund distributors) only; not for circulation to investors. Mutual Fund investments are subject to market risks, read all scheme related documents carefully. Investments in Specialised Investment Funds involve relatively higher risk, including potential loss of capital, liquidity risk and market volatility. Past performance may or may not be sustained in future. Not a recommendation. Valueplus Technologies Pvt. Ltd. (AssetPlus), ARN-114376.</p>
</div>
<script>
const D=__DATA__;const $=s=>document.querySelector(s);const esc=t=>String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pct=v=>v==null?"–":(v>0?"+":v<0?"−":"")+Math.abs(v).toFixed(2)+"%";const cl=v=>v==null?"na":v>0?"up":v<0?"dn":"";
const F=D.funds;const tot=F.reduce((s,f)=>s+(f.aum||0),0);
$("#aum").textContent=D.aum;
$("#k").innerHTML=[[F.length,"live strategies"],[new Set(F.map(f=>f.brand)).size,"SIF brands with a live NAV"],["₹"+tot.toLocaleString("en-IN")+" cr","strategy average AUM"],[F.filter(f=>f.d1>0).length+" of "+F.filter(f=>f.d1!=null).length,"up on the day"]].map(([v,l])=>"<div><b>"+v+"</b><span>"+l+"</span></div>").join("");
let cur="All",sk="aum",sd=-1;const cats=["All",...D.cats.map(c=>c.name)];
$("#chips").innerHTML=cats.map(c=>'<button class="chip" aria-pressed="'+(c==="All")+'" data-c="'+esc(c)+'">'+esc(c)+"</button>").join("");
$("#chips").onclick=e=>{const b=e.target.closest(".chip");if(!b)return;cur=b.dataset.c;document.querySelectorAll(".chip").forEach(x=>x.setAttribute("aria-pressed",x===b));draw();};
$("#q").oninput=draw;document.querySelectorAll("th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sk===k)sd=-sd;else{sk=k;sd=(k==="name"||k==="cat"||k==="launch")?1:-1;}draw();});
const ld=d=>d?new Date(d+"T00:00:00").toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"2-digit"}):"–";
function draw(){const q=$("#q").value.trim().toLowerCase();let r=F.filter(f=>(cur==="All"||f.cat===cur)&&(!q||(f.name+" "+f.brand+" "+f.amc).toLowerCase().includes(q)));
r.sort((a,b)=>{const x=a[sk],y=b[sk];if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return typeof x==="string"?x.localeCompare(y)*sd:(x-y)*sd;});
$("#t tbody").innerHTML=r.map(f=>'<tr><td class="n"><b>'+esc(f.name)+"</b><small>"+esc(f.amc)+'</small></td><td><span class="p">'+esc(f.cat)+"</span></td><td>"+ld(f.launch)+'</td><td class="r">'+(f.aum==null?"–":f.aum.toLocaleString("en-IN"))+'</td><td class="r">'+f.nav.toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2})+"</td>"+["d1","m1","m3","m6","m12"].map(k=>'<td class="r '+cl(f[k])+'">'+pct(f[k])+"</td>").join("")+'<td class="r"><span class="si '+cl(f.si)+'">'+pct(f.si)+"</span></td></tr>").join("")||'<tr><td colspan="11">No strategy matches.</td></tr>';}
draw();
</script></body></html>
'''

if __name__ == "__main__":
    build()
