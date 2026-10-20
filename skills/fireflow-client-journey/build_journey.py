#!/usr/bin/env python3
"""Build a client-specific FireFlow commercial journey deck from a client JSON file.

Two modes, set by "fictional" in the client file:
  false  a proposal for a real prospect, shown with its real name (the normal case)
  true   a fictional, publicly shareable example such as Falaj Community Bank

Usage (from the repository root):
    python3 skills/fireflow-client-journey/build_journey.py CLIENT.json OUTPUT.html [--forbid NAMES.txt]

Python 3.9+, standard library only. The output is one self-contained HTML file.
--forbid lists names (one per line) that must not appear in the visible text:
for a fictional example, the real entity it is based on; for a real proposal,
other clients' names, to catch copy-paste mistakes.
"""
from pathlib import Path
from html import escape
import argparse
import base64
import json
import re
import sys

SKILL = Path(__file__).resolve().parent
ASSETS = SKILL / "assets"


# ---------- helpers ----------
def money(value):
    return "$" + format(round(value), ",")


def h(text):
    return escape(str(text), quote=False)


def icon(name):
    return f'<svg class="icon" aria-hidden="true"><use href="#{name}"/></svg>'


def heading(slide_id, title):
    first, emphasis = title
    return f'<h1 id="title-{slide_id}" tabindex="-1">{h(first)}<br><em>{h(emphasis)}</em></h1>'


def gate(label, text):
    return (f'<div class="gate-line"><span class="gate-icon">{icon("check")}</span>'
            f'<div><span class="mini-label">{h(label)}</span><p>{h(text)}</p></div></div>')


def slide(slide_id, tone, copy, visual, gate_html, extra_class=""):
    eyebrow, title, lead = copy["eyebrow"], copy["title"], copy["lead"]
    return (f'<section class="slide {tone} {extra_class}" id="{slide_id}" aria-labelledby="title-{slide_id}">'
            f'<div class="slide-content"><div class="copy"><p class="eyebrow">{h(eyebrow)}</p>'
            f'{heading(slide_id, title)}<p class="lead">{h(lead)}</p></div>'
            f'<div class="visual">{visual}</div>{gate_html}</div></section>')


def route(steps, tones=("sky", "orange", "mint")):
    parts = []
    for i, (title, text) in enumerate(steps):
        if i:
            parts.append(f'<span class="flow-arrow" aria-hidden="true">{icon("arrow")}</span>')
        parts.append(f'<div class="flow-step {tones[i % len(tones)]}"><span class="step-number">{i + 1:02d}.</span>'
                     f'<b>{h(title)}</b><span>{h(text)}</span></div>')
    return '<div class="system-flow"><div class="route">' + "".join(parts) + "</div></div>"


def control_list(items):
    rows = "".join(f'<div>{icon(i.get("icon", "check"))}<span><b>{h(i["title"])}</b><small>{h(i["text"])}</small></span></div>'
                   for i in items)
    return f'<div class="control-list">{rows}</div>'


def service_list(items):
    rows = "".join(f'<div><span class="service-number">{n + 1:02d}.</span><p><b>{h(t)}</b><span>{h(d)}</span></p></div>'
                   for n, (t, d) in enumerate(items))
    return f'<div class="service-list">{rows}</div>'


def fee_note(title, text):
    return f'<div class="fee-note"><b>{h(title)}</b><span>{h(text)}</span></div>'


# ---------- validation and calculation ----------
def validate(client, terms):
    problems = []
    fictional = client.get("fictional")
    if fictional not in (True, False):
        problems.append('Set "fictional" to false (real client proposal) or true (fictional example).')
    if fictional is True and not client.get("client", {}).get("fictional_note"):
        problems.append("A fictional example needs client.fictional_note.")
    if fictional is False and not client.get("sources"):
        problems.append("A real-client proposal needs a non-empty \"sources\" list (internal; not shown in the deck).")
    if not client.get("client", {}).get("name"):
        problems.append("client.name is required.")
    todo = []
    def scan(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                scan(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                scan(v, f"{path}[{i}]")
        elif isinstance(value, str) and "TODO" in value:
            todo.append(path)
    scan(client, "")
    if todo:
        problems.append("Fill in the TODO fields: " + ", ".join(todo[:8]) + (" …" if len(todo) > 8 else ""))
    for a in client.get("agents", []):
        if a.get("initial") and not (a.get("units_per_month") and a.get("tokens_in")):
            problems.append(f'{a.get("id")}: set units_per_month and tokens_in/tokens_out.')
    initial = [a for a in client["agents"] if a.get("initial")]
    if len(initial) != 3:
        problems.append("Exactly three initial agents are required (Stage 1 scopes the first three agents).")
    for a in client["agents"]:
        if a["workload"] not in ("UIO", "BPO"):
            problems.append(f'{a["id"]}: workload must be UIO or BPO.')
        if a["model"] not in ("private", "frontier"):
            problems.append(f'{a["id"]}: model must be private or frontier.')
        if a["workload"] == "UIO" and a["model"] != "private":
            problems.append(f'{a["id"]}: UIO agents must use private models only.')
    if problems:
        sys.exit("Client file problems:\n- " + "\n- ".join(problems))


def calculate(client, terms):
    rates, t = client["rates"], client["timeline"]
    pct = {"private": terms["surcharge_private"], "frontier": terms["surcharge_frontier"]}
    for a in client["agents"]:
        r = rates[a["model"]]
        tin = a["units_per_month"] * a["tokens_in"] / 1e6
        tout = a["units_per_month"] * a["tokens_out"] / 1e6
        a["cost"] = tin * r["in"] + tout * r["out"]
        a["rate"] = pct[a["model"]]
        a["surcharge"] = a["cost"] * a["rate"]
    initial = [a for a in client["agents"] if a.get("initial")]
    run_cost = sum(a["cost"] for a in initial)
    run_surcharge = sum(a["surcharge"] for a in initial)

    def ramp(month):
        if month < t["limited_month"]:
            return 0.0
        return float(t["ramp"].get(str(month), 1.0))

    months = range(1, t["year_months"] + 1)
    share = sum(ramp(m) for m in months)
    prepay_end = t["prepay_month"] + terms["maintenance_prepay_months"] - 1
    monthly_start = max(t["go_live_month"], prepay_end + 1)
    monthly_count = max(0, t["year_months"] - monthly_start + 1)
    maintenance = terms["maintenance_prepay"] + monthly_count * terms["maintenance_monthly"]
    inference = run_cost * share
    surcharge = run_surcharge * share
    return {
        "run_cost": run_cost, "run_surcharge": run_surcharge,
        "first_surcharge": run_surcharge * ramp(t["limited_month"]),
        "first_share": ramp(t["limited_month"]),
        "prepay_end": prepay_end, "monthly_start": monthly_start, "monthly_count": monthly_count,
        "maintenance": maintenance, "inference": inference, "surcharge": surcharge,
        "fees_total": terms["setup_fee"] + maintenance + surcharge,
        "total_with_inference": terms["setup_fee"] + maintenance + surcharge + inference,
    }


# ---------- client logo (real clients only) ----------
LOGO_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
LOGO_MAX_BYTES = 500_000


def load_logos(client, base):
    """Embed client.logo (and optional client.logo_dark) as data URIs. Paths are relative to the client file."""
    cl = client["client"]
    if not cl.get("logo"):
        if cl.get("logo_dark"):
            sys.exit("client.logo_dark needs client.logo as well.")
        return
    if client["fictional"]:
        sys.exit("Fictional examples must not use a logo. Remove client.logo.")
    for key in ("logo", "logo_dark"):
        if not cl.get(key):
            continue
        path = (base / cl[key]).resolve()
        if not path.is_file():
            sys.exit(f"client.{key}: file not found: {path}")
        kind = LOGO_TYPES.get(path.suffix.lower())
        if not kind:
            sys.exit(f"client.{key}: use an SVG, PNG, JPG or WebP file.")
        data = path.read_bytes()
        if len(data) > LOGO_MAX_BYTES:
            sys.exit(f"client.{key}: file is larger than {LOGO_MAX_BYTES // 1000} KB; use an optimised version.")
        if kind == "image/svg+xml" and re.search(rb"<script|\son[a-z]+\s*=|javascript:", data, re.I):
            sys.exit(f"client.{key}: SVG contains scripts or event handlers; use a clean file.")
        cl["_" + key] = f"data:{kind};base64," + base64.b64encode(data).decode("ascii")


def logo_html(cl):
    alt = escape(cl["name"] + " logo")
    if cl.get("_logo_dark"):
        return (f'<span class="client-logo"><img class="logo-on-light" src="{cl["_logo"]}" alt="{alt}">'
                f'<img class="logo-on-dark" src="{cl["_logo_dark"]}" alt="{alt}"></span>')
    # One version only: show it on a light plate so it stays legible in the dark theme.
    return f'<span class="client-logo plate"><img src="{cl["_logo"]}" alt="{alt}"></span>'


# ---------- mode-dependent wording ----------
def mode(client):
    cl = client["client"]
    name, short = cl["name"], cl.get("short", cl["name"])
    if client["fictional"]:
        return {
            "header": "ILLUSTRATIVE EXAMPLE · FICTIONAL BANK",
            "card_label": "FICTIONAL CLIENT",
            "flag": "Fictional bank · illustrative figures only",
            "intro_gate": ("ILLUSTRATIVE ONLY", cl["fictional_note"]),
            "end_gate": ("ILLUSTRATIVE ONLY", "Fictional bank. Volumes, rates and timings are assumptions, not quotes. "
                                              "Final fees and scope are agreed in the contract."),
            "title": f"FireFlow | Illustrative example: {name} (fictional)",
            "description": f"An illustrative FireFlow commercial journey for {name}, a fictional bank.",
            "mark": waves_mark(),
        }
    return {
        "header": f"PROPOSAL FOR {short.upper()}",
        "card_label": "PREPARED FOR",
        "flag": "Proposal for discussion · estimated figures",
        "intro_gate": ("PROPOSAL FOR DISCUSSION", cl.get("proposal_note") or
                       f"Based on public information about {name}. Volumes and timings are estimates to refine together; "
                       "final fees and scope are agreed in the contract."),
        "end_gate": ("PROPOSED TERMS", f"Volumes, rates and timings are estimates to confirm with {short}. "
                                       "US dollars; taxes excluded. Final fees and scope are agreed in the contract."),
        "title": f"FireFlow | Proposed commercial journey for {name}",
        "description": f"Proposed FireFlow commercial journey for {name}.",
        "mark": logo_html(cl) if cl.get("_logo") else initials_mark(short),
    }


# ---------- slides ----------
def build_slides(client, terms, c):
    s, cl, t = client["slides"], client["client"], client["timeline"]
    m = mode(client)
    links = client.get("links", {})
    initial = [a for a in client["agents"] if a.get("initial")]
    addons = [a for a in client["agents"] if not a.get("initial")]
    out = []

    facts = "".join(f"<li>{h(f)}</li>" for f in cl["facts"])
    tagline = cl.get("brand", {}).get("tagline")
    tagline_html = f'<span class="client-tagline">{h(tagline)}</span>' if tagline else ""
    card = (f'<div class="client-card"><div class="client-head">{m["mark"]}<div><p class="mini-label">{h(m["card_label"])}</p>'
            f'<b>{h(cl["name"])}</b>{tagline_html}</div></div><ul>{facts}</ul>'
            f'<p class="client-flag">{h(m["flag"])}</p></div>')
    out.append(slide("intro", "orange", s["intro"], card, gate(*m["intro_gate"]), "intro-slide"))

    out.append(slide("bank", "gold", s["bank"], control_list(s["bank"]["items"]), gate(*s["bank"]["gate"])))

    uc = service_list([(f'{a["name"]} · {a["workload"]}', a["desc"]) for a in initial])
    def soft(name):  # lower-case the first word unless it is an acronym such as SME
        first = name.split()[0]
        return name if first.isupper() else name[0].lower() + name[1:]
    later = ", ".join([addons[0]["name"]] + [soft(a["name"]) for a in addons[1:]]) if addons else "None planned"
    out.append(slide("use-cases", "violet", s["use_cases"], uc, gate("LATER: ADD-ON SERVICES", later + ".")))

    out.append(slide("systems", "sky", s["systems"], control_list(s["systems"]["items"]), gate(*s["systems"]["gate"])))

    panel = (f'<div class="price-panel orange"><p class="mini-label">STAGE 1 · ONE-TIME</p>'
             f'<p class="amount">{money(terms["setup_fee"])}<span></span></p>'
             f'<p class="price-detail">{h(terms["setup_label"])}. Invoiced at signature (month {t["setup_month"]}).</p></div>')
    out.append(slide("staging", "orange", s["staging"], panel + fee_note(*s["staging"]["note"]), gate(*s["staging"]["gate"])))

    prepay = fee_note(f'Maintenance prepayment: {money(terms["maintenance_prepay"])}',
                      f'Invoiced at Stage 2 (month {t["prepay_month"]}). Covers Stages 2–4 and months {t["prepay_month"]}–{c["prepay_end"]}.')
    out.append(slide("build", "orange", s["build"], route(s["build"]["steps"]) + prepay, gate(*s["build"]["gate"])))

    controls = control_list([{"icon": "shield", "title": a["name"], "text": a["control"]} for a in initial])
    out.append(slide("prepare", "sky", s["prepare"], controls, gate(*s["prepare"]["gate"])))

    first = fee_note("Compute surcharge starts",
                     f'From month {t["limited_month"]}, a {round(terms["surcharge_private"] * 100)}% surcharge applies to the inference '
                     f'cost of live agents. With about {round(c["first_share"] * 100)}% of customers using them, that is roughly '
                     f'{money(c["first_surcharge"])} for the month.')
    out.append(slide("rollout", "sky", s["rollout"], route(s["rollout"]["steps"]) + first, gate(*s["rollout"]["gate"])))

    maint = (f'<div class="price-panel mint"><p class="mini-label">PLATFORM MAINTENANCE</p>'
             f'<p class="amount">{money(terms["maintenance_monthly"])}<span>/month</span></p>'
             f'<p class="price-detail">Prepayment covers months {t["prepay_month"]}–{c["prepay_end"]}. Monthly billing starts in month '
             f'{c["monthly_start"]}, the later of go-live and the end of the prepaid months.</p></div>')
    split = "".join(f"<p><b>{h(a)}</b>{h(b)}</p>" for a, b in s["operate"]["split"])
    out.append(slide("operate", "mint", s["operate"], maint + f'<div class="ownership-split">{split}</div>',
                     gate("YEAR ONE", f'{c["monthly_count"]} monthly invoices (months {c["monthly_start"]}–{t["year_months"]}): '
                                      f'{money(c["monthly_count"] * terms["maintenance_monthly"])}.')))

    rows = "".join(f'<tr><th scope="row">{h(a["name"])}</th><td>{a["units_per_month"]:,} {h(a["unit"])}</td>'
                   f'<td>{money(a["cost"])}</td><td>{money(a["surcharge"])}</td></tr>' for a in initial)
    r = client["rates"]["private"]
    table = (f'<table class="cost-table"><thead><tr><th scope="col">Agent</th><th scope="col">Volume / month</th>'
             f'<th scope="col">Inference</th><th scope="col">Surcharge {round(terms["surcharge_private"] * 100)}%</th></tr></thead>'
             f'<tbody>{rows}</tbody><tfoot><tr><th scope="row">Total</th><td></td><td>{money(c["run_cost"])}</td>'
             f'<td>{money(c["run_surcharge"])}</td></tr></tfoot></table>'
            )
    assumptions = (f'${r["in"]:.2f} per million input and ${r["out"]:.2f} per million output tokens ({r["label"]}). '
                   + s["usage"]["gate"][1])
    out.append(slide("usage", "mint", s["usage"], table, gate("ASSUMED RATES", assumptions)))

    rows = []
    for n, a in enumerate(addons):
        rate = f'{a["model"].capitalize()} model · {round(a["rate"] * 100)}% compute surcharge'
        rows.append(f'<div><span class="service-number">{n + 1:02d}.</span><p><span class="addon-head"><b>{h(a["name"])} · {h(a["workload"])}</b>'
                    f'<span class="addon-rate">{h(rate)}</span></span><span>{h(a["desc"])}</span></p></div>')
    addon_list = f'<div class="service-list">{"".join(rows)}</div>'
    out.append(slide("addons", "violet", s["addons"], addon_list,
                     gate("ALSO POSSIBLE", client.get("addons_extra", "") + " Add-on fees are quoted separately.")))

    grid = (f'<div class="summary-grid">'
            f'<div class="orange"><span>01. {h(terms["setup_label"])}</span><b>{money(terms["setup_fee"])}</b><small>Stage 1 · month {t["setup_month"]}</small></div>'
            f'<div class="mint"><span>02. Maintenance</span><b>{money(c["maintenance"])}</b><small>{money(terms["maintenance_prepay"])} prepaid + '
            f'{c["monthly_count"]} × {money(terms["maintenance_monthly"])}</small></div>'
            f'<div class="sky"><span>03. Compute surcharge</span><b>{money(c["surcharge"])}</b><small>25% of {money(c["inference"])} inference</small></div>'
            f'<div class="violet"><span>Year-one FireFlow fees</span><b>{money(c["fees_total"])}</b><small>Plus ~{money(c["inference"])} inference at cost, '
            f'paid to the provider or passed through; add-ons excluded</small></div></div>')
    link_html = ""
    if links.get("standard_model"):
        link_html += f'<a class="primary-link" href="{escape(links["standard_model"])}">Standard commercial model {icon("arrow")}</a>'
    if links.get("overview"):
        link_html += f'<a href="{escape(links["overview"])}">Full overview {icon("launch")}</a>'
    if link_html:
        grid += f'<div class="overview-links">{link_html}</div>'
    out.append(slide("year-one", "orange summary-slide", s["year_one"], grid, gate(*m["end_gate"])))
    return out


def initials_mark(short):
    # Neutral monogram for real clients. Never draw or copy a client's own logo.
    letters = "".join(w[0] for w in re.findall(r"[A-Za-z0-9]+", short)[:2]).upper() or "•"
    return (f'<svg class="client-mark" viewBox="0 0 48 48" role="img" aria-label="{h(short)}">'
            '<rect x="2" y="2" width="44" height="44" rx="12" fill="none" stroke="currentColor" stroke-width="3"/>'
            f'<text x="24" y="30" text-anchor="middle" font-family="Red Hat Display" font-weight="700" font-size="16" fill="currentColor">{h(letters)}</text></svg>')


def waves_mark():
    # Fictional mark for the Falaj example: three water channels. Not a real institution's logo.
    return ('<svg class="client-mark" viewBox="0 0 48 48" role="img" aria-label="Fictional bank mark">'
            '<rect x="2" y="2" width="44" height="44" rx="12" fill="none" stroke="currentColor" stroke-width="3"/>'
            '<path d="M10 17c5-4 9 4 14 0s9 4 14 0M10 25c5-4 9 4 14 0s9 4 14 0M10 33c5-4 9 4 14 0s9 4 14 0" '
            'fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>')


EXAMPLE_CSS = """
.client-card{border:1px solid var(--border);border-top:4px solid var(--client);border-radius:12px;background:var(--panel);padding:24px;display:flex;flex-direction:column;gap:16px}
.client-head{display:flex;gap:16px;align-items:center}
.client-mark{width:48px;height:48px;color:var(--client);flex:none}
.client-logo{display:flex;align-items:center;flex:0 0 auto}
.client-logo img{display:block;height:44px;width:auto;max-width:220px;object-fit:contain}
.client-logo.plate{background:#fff;border-radius:8px;padding:6px 10px}
.client-head:has(.client-logo){flex-wrap:wrap}
[data-theme="dark"] .logo-on-light,[data-theme="light"] .logo-on-dark{display:none}
.client-head b{display:block;font:700 24px/1.15 'Red Hat Display';color:var(--text)}
.client-tagline{font-size:14px;color:var(--secondary)}
.client-card ul{margin:0;padding-left:18px;display:grid;gap:6px;font-size:15px;color:var(--secondary)}
.client-flag{font:500 11px/1.3 'Red Hat Mono';letter-spacing:.04em;text-transform:uppercase;color:var(--client)}
.service-list p{flex:1;min-width:0}.service-list p>span.addon-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px;color:inherit}
.addon-rate{font:500 11px/1.3 'Red Hat Mono';color:var(--tone);white-space:nowrap}
#addons .service-list{gap:10px}#addons .service-list>div{padding:13px 18px}#addons .service-list p{gap:4px}
@media(max-width:1000px) and (orientation:portrait){#addons .service-list>div{padding:10px 12px}#addons .service-list{gap:8px}}
@media(min-width:1001px) and (max-height:800px){#addons .service-list>div{padding:10px 16px}#addons .service-list p>span:not(.addon-head){font-size:13px}}
.cost-table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden;font-size:15px}
.cost-table th,.cost-table td{padding:12px 14px;text-align:right;border-bottom:1px solid var(--border);color:var(--text)}
.cost-table th:first-child{text-align:left}
.cost-table thead th{font:500 11px/1.3 'Red Hat Mono';text-transform:uppercase;color:var(--secondary)}
.cost-table tbody th{font-weight:500}
.cost-table tfoot th,.cost-table tfoot td{font-weight:700;border-bottom:0}
.example-flag{color:var(--client)}
@media(max-width:1000px) and (orientation:portrait){
 .client-card{padding:16px;gap:10px}.client-head b{font-size:19px}.client-card ul{font-size:13px}
 .cost-table{font-size:12px}.cost-table th,.cost-table td{padding:8px 6px}
}
@media(max-width:350px) and (orientation:portrait){.cost-table{font-size:11px}.cost-table th,.cost-table td{padding:6px 4px}}
@media(max-width:1000px) and (orientation:portrait) and (max-height:700px){
 .client-logo img{height:34px;max-width:170px}
 .client-card{padding:12px;gap:8px}.client-mark{width:36px;height:36px}.client-head b{font-size:17px}.client-card ul{font-size:11px;gap:3px}
 #addons .service-list p>span:not(.addon-head){display:none}#addons .service-list>div{padding:9px 12px}#addons .addon-rate{font-size:10px}
 .cost-table th,.cost-table td{padding:6px 5px}
}
@media(max-width:1000px) and (orientation:portrait) and (max-height:600px){
 .client-card ul,.client-tagline{display:none}#intro .lead{font-size:13px}
 .lead{font-size:13px;margin-top:8px}h1{font-size:29px}
 .control-list>div{padding:9px 12px;gap:14px}.control-list .icon{width:24px;height:24px}.control-list b{font-size:15px}.control-list small{font-size:10px}
 #operate .ownership-split{display:none}
 .cost-table th:nth-child(2),.cost-table td:nth-child(2){display:none}
 #use-cases .service-list p>span{font-size:10px}
}
@media(orientation:landscape) and (max-height:540px){
 .client-logo img{height:28px;max-width:150px}
 .client-card{padding:10px;gap:6px}.client-card ul,.client-tagline{display:none}.client-mark{width:32px;height:32px}.client-head b{font-size:16px}
 .cost-table{font-size:11px}.cost-table th,.cost-table td{padding:4px 8px}.cost-table th:nth-child(2),.cost-table td:nth-child(2){display:none}
 .service-list p>span:not(.addon-head),.control-list small{display:none}.service-list>div,.control-list>div{padding:8px 12px}#addons .addon-rate{font-size:10px}#addons .service-list{gap:5px}#addons .service-list>div{padding:5px 12px}#addons .service-list b{font-size:14px}
 #operate .ownership-split{display:none}
}
@media(orientation:landscape) and (max-height:360px){
 .lead,.fee-note span,.price-detail,.client-flag{display:none}h1{font-size:24px}.eyebrow{margin-bottom:4px}
 .amount{font-size:30px;margin:4px 0}.price-panel{padding:10px 14px}.fee-note{padding-top:4px}
 .flow-step{padding:6px 8px}.flow-step>span:last-child:not(.step-number){display:none}
 .summary-grid>div{padding:7px;gap:3px}.summary-grid b{font-size:18px}.summary-grid small{display:none}
 .overview-links a{min-height:36px}.cost-table th,.cost-table td{padding:3px 8px}
 .service-list{gap:6px}.service-list>div{padding:6px 10px}.service-list b{font-size:14px}
 .cost-table thead{display:none}#addons .service-list{gap:3px}#addons .service-list>div{padding:3px 10px}#addons .service-list b{font-size:12px}#addons .addon-rate{font-size:9px}
 #year-one .overview-links{display:none}.summary-grid b{font-size:16px}
}
"""


def asset(name):
    return (ASSETS / name).read_text(encoding="utf-8")


def embed_fonts(css):
    def repl(m):
        data = base64.b64encode((ASSETS / "fonts" / m.group(1)).read_bytes()).decode("ascii")
        return f"url(data:font/woff2;base64,{data})"
    return re.sub(r"url\(assets/fonts/([^)]+\.woff2)\)", repl, css)


def page(client, slides_html, metadata):
    cl, m, links = client["client"], mode(client), client.get("links", {})
    brand = cl.get("brand", {})
    accent = (f':root,[data-theme="light"]{{--client:{brand.get("color_light", "var(--accent)")}}}'
              f'[data-theme="dark"]{{--client:{brand.get("color_dark", "var(--accent)")}}}')
    css = embed_fonts("".join(asset(n) for n in ("red-hat-text-latin-variable.css", "red-hat-display-latin-variable.css",
                                                 "red-hat-mono-latin-variable.css", "viewport.css", "slides.css"))) + accent + EXAMPLE_CSS
    skip = (f'<a class="skip-overview" href="{escape(links["standard_model"])}">Standard commercial model {icon("arrow")}</a>'
            if links.get("standard_model") else "")
    n = len(metadata)
    data = json.dumps(metadata).replace("</", "<\\/")
    return (
        '<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">'
        f'<title>{h(m["title"])}</title>'
        f'<meta name="description" content="{escape(m["description"])}">'
        "<script>try{document.documentElement.dataset.theme=localStorage.getItem('fireflow-theme')||"
        "(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light')}catch(e){document.documentElement.dataset.theme='dark'}</script>"
        f"<style>{css}</style></head><body>{asset('icons.svg')}<div class=\"deck-viewport\">"
        '<header class="deck-header"><a class="brand" href="#intro" aria-label="FireFlow: return to the first screen"><b>FireFlow</b><span>by Persistent Labs</span></a>'
        f'<div class="header-centre"><span class="draft-dot"></span>{h(m["header"])}</div>'
        f'<button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch to light mode">{icon("sun")}<span>Light mode</span></button></header>'
        f'<main class="deck-stage" id="deck-stage" aria-label="{escape(m["title"])}">{"".join(slides_html)}</main>'
        f'<footer class="deck-footer"><div class="progress-track" role="progressbar" aria-label="Journey progress" aria-valuemin="1" aria-valuemax="{n}" aria-valuenow="1"><span id="progress-fill"></span></div>'
        f'<div class="navigation">{skip}'
        f'<button class="previous" id="previous" type="button" aria-label="Previous screen">{icon("arrow")}<span>Back</span></button>'
        f'<div class="position"><span id="position-number">01 / {n:02d}</span><span id="chapter-name">Start</span></div>'
        '<p id="next-topic" class="next-topic"></p>'
        f'<button class="next" id="next" type="button"><span id="next-label">Next</span>{icon("arrow")}</button></div></footer></div>'
        '<p id="announcement" class="sr-only" role="status" aria-live="polite"></p>'
        '<noscript><div class="no-script"><p>This guided view needs JavaScript.</p></div></noscript>'
        f'<script id="slide-data" type="application/json">{data}</script>'
        f"<script>{asset('slides.js')}</script></body></html>"
    )


CHAPTERS = {"intro": "Start", "bank": "Start", "use-cases": "Scope", "systems": "Scope", "staging": "Deploy", "build": "Deploy",
            "prepare": "Deploy", "rollout": "Deploy", "operate": "Operate", "usage": "Usage", "addons": "Extend", "year-one": "Summary"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("output")
    ap.add_argument("--forbid", help="Text file (outside the repo) with real-entity names that must not appear")
    args = ap.parse_args()
    terms = json.loads((SKILL / "commercial-terms.json").read_text(encoding="utf-8"))
    client_path = Path(args.client).resolve()
    client = json.loads(client_path.read_text(encoding="utf-8"))
    validate(client, terms)
    load_logos(client, client_path.parent)
    c = calculate(client, terms)
    slides_html = build_slides(client, terms, c)
    metadata = []
    for html in slides_html:
        sid = re.search(r'id="([^"]+)" aria-labelledby', html).group(1)
        title = re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", html).group(1).replace("<br>", " "))
        metadata.append({"id": sid, "chapter": CHAPTERS.get(sid, ""), "title": title})
    result = page(client, slides_html, metadata)
    if args.forbid:
        text = re.sub(r"<(style|script|svg)\b.*?</\1>", " ", result, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        for name in [l.strip() for l in Path(args.forbid).read_text(encoding="utf-8").splitlines() if l.strip()]:
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", text, re.I):
                sys.exit(f"Leak check failed: the deck mentions a forbidden name: {name!r}")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    summary = {k: round(v, 2) if isinstance(v, float) else v for k, v in c.items()}
    print(f"Built {out} ({len(slides_html)} slides).")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
