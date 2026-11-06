"""Build landing/index.html from landing/index.src.html.

Fills in the two data blocks the page needs:
  __SIFDATA__    daily NAV snapshot (landing/sifdata.json, from fetch_sif_navs.py)
  __PULSEDATA__  SIF Pulse data      (landing/pulse-data.json, from build_pulse.py)
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def build():
    src = (ROOT / "landing/index.src.html").read_text()
    nav = (ROOT / "landing/sifdata.json").read_text()
    pulse = json.loads((ROOT / "landing/pulse-data.json").read_text())
    pulse.pop("brandQuarterEnd", None)
    out = src.replace("__SIFDATA__", nav).replace("__PULSEDATA__", json.dumps(pulse, ensure_ascii=False, separators=(",", ":")))
    (ROOT / "landing/index.html").write_text(out)


if __name__ == "__main__":
    build()
