"""Package the SIF Partner Hub as a static folder + zip for drag-and-drop hosting
(Netlify Drop, Cloudflare Pages direct upload, any web host).

Output: dist/sif-site/ and dist/sif-site.zip
Leads: posted to Netlify Forms ("sif-lead"); on Vercel the /api/lead function is used instead.
"""
import os, pathlib, re, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "sif-site"
subprocess.run([sys.executable, str(ROOT / "tools/build_page.py")], check=True, env=os.environ.copy())
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
html = (ROOT / "landing/site.html").read_text()
fields = ["id","update","name","mobile","city","arn","noArn","vd","consent","source","want","doc","waitlist","eventClicked","utm_source","utm_medium","utm_campaign","utm_content","ref","referrer","landedAt","visit","at","updatedAt","page"]
form = '<form name="sif-lead" data-netlify="true" netlify-honeypot="bot-field" hidden>' + '<input name="bot-field">' + "".join('<input name="%s">' % f for f in fields) + "</form>"
html = html.replace("<body>\n", "<body>\n" + form + "\n", 1)
(OUT / "index.html").write_text(html)
for name in ["decoder-cover.webp", "logo-light.png", "og-image.jpg", "robots.txt"] + (["sitemap.xml"] if (ROOT / "landing/sitemap.xml").exists() else []):
    shutil.copy2(ROOT / "landing" / name, OUT / name)
for d in ["img", "thumbs", "pdfs"]:
    shutil.copytree(ROOT / "landing" / d, OUT / d)
(OUT / "_headers").write_text("/img/*\n  Cache-Control: public, max-age=604800\n/thumbs/*\n  Cache-Control: public, max-age=604800\n/pdfs/*\n  X-Robots-Tag: noindex\n")
zp = shutil.make_archive(str(ROOT / "dist" / "sif-site"), "zip", OUT)
print("built", OUT, "and", zp)
