# AssetPlus SIF Partner Hub (landing page)

Partner-facing SIF landing page: learn SIF, live AMFI NAV board, free NISM V-D certification push, gated partner kit (lead capture), WhatsApp.

- `index.src.html` — page source; `__SIFDATA__` is replaced with the NAV snapshot.
- `index.html` — built page (published as a Claude artifact).
- `pdfs/` — partner (01, 02, 04, 07a–f, 09, tracker, history) and client-shareable (06a–e) one-pagers.
- `../tools/fetch_sif_navs.py` — refreshes `sifdata.json` from AMFI's SIF APIs and rebuilds `index.html`.

Config at the top of the page script: WhatsApp number, event list (`EVENTS`), popup delay.
Leads are written to the artifact's `leads` collection: name, mobile, city, ARN, V-D status, source, document.

## Deploying to Vercel

The repo is Vercel-ready: `vercel.json` serves `landing/` as a static site and `api/lead.js` receives sign-ups.

1. Import `naveenb-ap/SIF-project` in Vercel (Framework: Other). No build command is needed.
2. In Project Settings → Environment Variables, set `LEAD_WEBHOOK_URL` to where leads should go
   (Zoho Flow / Zoho CRM webhook, or a Google Apps Script that appends to a Sheet).
   Without it, leads are written to the Vercel function logs as `SIF_LEAD {...}`.
3. Deploy. The nightly data refresh commits to the branch; Vercel redeploys on each push.

### SEO
- `tools/build_page.py` writes `landing/site.html`, a full HTML document (lang, title, description, Open Graph, Course/Event/FAQ structured data) that Vercel serves at `/`.
- Set the `SITE_URL` environment variable when building (e.g. `SITE_URL=https://sif.assetplus.in/ python3 tools/build_page.py`) to add the canonical URL, absolute share-image links and `sitemap.xml`.
- `og-image.jpg` is the 1200×630 share image; `robots.txt` keeps `/pdfs/` out of search.

### Batches and analytics
- Add new batches to `EVENTS` in `index.src.html`. Two days after the last listed batch starts, the page switches by itself to "Join the waitlist" copy and sign-ups are tagged `waitlist`.
- Paste IDs into `CONFIG.ga4`, `CONFIG.metaPixel` and `CONFIG.linkedinPartner` to switch on GA4, Meta Pixel and LinkedIn Insight. Every funnel step (pop-up, lead, register click, download, share, quiz, calculator, badge) is forwarded; leads fire GA4 `generate_lead` and Meta `Lead`.

### Sharing in comms (tracked links)
Replace `BASE` with the live URL. Every link carries UTM tags, so sign-ups show their source.
- WhatsApp broadcast: `BASE?utm_source=whatsapp&utm_medium=broadcast&utm_campaign=sif_ready`
- Email newsletter: `BASE?utm_source=email&utm_medium=newsletter&utm_campaign=sif_ready`
- AssetPlus app banner: `BASE?utm_source=app&utm_medium=banner&utm_campaign=sif_ready`
- RM / partner groups: `BASE?utm_source=rm&utm_medium=whatsapp&utm_campaign=sif_ready`
- LinkedIn post: `BASE?utm_source=linkedin&utm_medium=social&utm_campaign=sif_ready`
- Open the sign-up straight away: add `#register` to any link.
- Jump to live data: add `#pulse`.

### SEO
`tools/build_page.py` writes real SIF numbers (strategy table, counts, dates) into the HTML and generates FAQPage, Dataset and ItemList structured data from what is on the page, so search engines and link previews see them without running scripts. Rebuilt nightly with the data.

### Deploy without git (drag and drop)
1. `python3 tools/make_static_site.py` builds `dist/sif-site/` and `dist/sif-site.zip`.
2. Go to https://app.netlify.com/drop, log in, and drag the `sif-site` folder (or unzip the zip and drag the folder).
3. Leads arrive in Netlify → Site → Forms → `sif-lead` (enable form detection once in Site settings → Forms; set email notifications there).
4. To update data: rebuild and drag the folder onto the same site's Deploys page.
Same folder also works on Cloudflare Pages (Upload assets) or any static host; there, leads need the Vercel function or a webhook instead.
