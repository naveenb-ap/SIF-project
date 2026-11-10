// Vercel serverless function: receives sign-ups from the SIF Partner Hub.
// Set LEAD_WEBHOOK_URL in Vercel (e.g. a Zoho Flow / Zoho CRM webform / Google Apps Script URL)
// to forward each lead as JSON. Without it, leads are written to the function logs.
const FIELDS = ["id", "update", "name", "mobile", "city", "arn", "noArn", "vd", "consent", "source", "want", "doc",
  "eventClicked", "utm_source", "utm_medium", "utm_campaign", "utm_content", "referrer", "landedAt", "visit", "at", "updatedAt", "page"];

module.exports = async (req, res) => {
  if (req.method !== "POST") { res.setHeader("Allow", "POST"); return res.status(405).json({ ok: false }); }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = null; } }
  if (!body || typeof body !== "object" || !body.id) return res.status(400).json({ ok: false, error: "Missing lead" });
  const lead = {};
  for (const k of FIELDS) if (body[k] !== undefined) lead[k] = typeof body[k] === "string" ? body[k].slice(0, 300) : body[k];
  if (!lead.update) {
    const okMobile = lead.name && /^[6-9]\d{9}$/.test(String(lead.mobile || ""));
    const okArn = /^ARN-?\d{3,7}$/i.test(String(lead.arn || ""));
    if (!okMobile && !okArn) return res.status(400).json({ ok: false, error: "Need name and mobile, or an ARN" });
  }
  lead.receivedAt = new Date().toISOString();
  const hook = process.env.LEAD_WEBHOOK_URL;
  try {
    if (hook) {
      const r = await fetch(hook, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(lead) });
      if (!r.ok) throw new Error("webhook " + r.status);
    } else {
      console.log("SIF_LEAD", JSON.stringify(lead));
    }
    return res.status(200).json({ ok: true, id: lead.id });
  } catch (e) {
    console.error("SIF_LEAD_FAILED", e.message, JSON.stringify(lead));
    return res.status(502).json({ ok: false });
  }
};
