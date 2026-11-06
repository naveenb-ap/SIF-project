# AssetPlus SIF Partner Hub (landing page)

Partner-facing SIF landing page: learn SIF, live AMFI NAV board, free NISM V-D certification push, gated partner kit (lead capture), WhatsApp.

- `index.src.html` — page source; `__SIFDATA__` is replaced with the NAV snapshot.
- `index.html` — built page (published as a Claude artifact).
- `pdfs/` — partner (01, 02, 04, 07a–f, 09, tracker, history) and client-shareable (06a–e) one-pagers.
- `../tools/fetch_sif_navs.py` — refreshes `sifdata.json` from AMFI's SIF APIs and rebuilds `index.html`.

Config at the top of the page script: WhatsApp number, event list (`EVENTS`), popup delay.
Leads are written to the artifact's `leads` collection: name, mobile, city, ARN, V-D status, source, document.
