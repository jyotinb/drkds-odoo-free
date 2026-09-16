"""Render the shared drkds store description page (static/description/index.html).

Usage: import and call render(...), or run with a JSON spec file.
Keeps every module's listing visually identical, which is the point.

The suite strip every page carries is generated from SUITE below, so the
cross-links stay in step across all listings. Never hand-write it into a page:
hand-porting a shared block between copies is what let the sibling repo drift.
"""
import html
import json
import re
import sys

TEMPLATE = """<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <h2 class="oe_slogan" style="color:#183a5c; margin-bottom:6px;">{title}</h2>
      <h3 class="oe_slogan" style="color:#5d6d7e; font-weight:400; margin-top:0;">{summary}</h3>
    </div>
  </div>
</section>

<section class="oe_container oe_dark">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <p class="oe_mt32" style="font-size:16px; line-height:1.6; color:#2c3e50;">
        {intro}
      </p>
    </div>
  </div>
</section>
{shots}
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <h3 class="oe_slogan" style="color:#183a5c;">What it does</h3>
    </div>
  </div>
  <div class="oe_row oe_spaced">
{features}
  </div>
</section>
{extra}
<section class="oe_container oe_dark">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <h3 class="oe_slogan" style="color:#183a5c;">Good to know</h3>
      <ul style="font-size:15px; line-height:1.8; color:#2c3e50;">
{notes}
      </ul>
    </div>
  </div>
</section>
{disclaimer}
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12" style="text-align:center;">
      <p style="font-size:15px; color:#5d6d7e;">
        Odoo 19 Community · Licence LGPL-3 · Free and open source
      </p>
      <p style="font-size:15px; color:#5d6d7e;">
        Part of the drkds Indian SME suite for Odoo 19 Community.
      </p>
      <p style="font-size:15px; color:#5d6d7e;">
        Support: <a href="mailto:jyotinboghani@gmail.com" style="color:#183a5c;">jyotinboghani@gmail.com</a>
         · 
        <a href="https://drkdsinfo.com" style="color:#183a5c;">drkdsinfo.com</a>
      </p>
    </div>
  </div>
</section>
"""

FEATURE = """    <div class="oe_span6">
      <div style="padding:14px 18px; border-left:3px solid #e8922a; margin-bottom:14px;">
        <h4 style="color:#183a5c; margin:0 0 6px 0;">{name}</h4>
        <p style="color:#5d6d7e; margin:0; line-height:1.6;">{text}</p>
      </div>
    </div>"""

SHOTS = """
<section class="oe_container">
  <div class="oe_row oe_spaced">
{rows}
  </div>
</section>
"""

#: The headed variant: one section per screenshot, with its own sub-heading.
#: Both layouts exist in the repo; a page keeps the one it was written with.
SHOT_HEADED = """
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <h3 class="oe_slogan" style="color:#183a5c;">{heading}</h3>
      <img src="{src}" alt="{alt}" style="display:block; width:100%; max-width:1100px; margin:0 auto; border:1px solid #d5dbdb; border-radius:4px;"/>
      <p style="font-size:15px; line-height:1.6; color:#5d6d7e; max-width:1100px; margin:14px auto 0 auto; text-align:center;">{caption}</p>
    </div>
  </div>
</section>
"""

SHOT = """    <div class="oe_span12" style="text-align:center;">
      <img src="{src}" alt="{alt}" style="max-width:100%; height:auto; border:1px solid #d5dbdb; border-radius:4px;"/>
      <p style="font-size:14px; color:#5d6d7e; line-height:1.6; margin-top:10px;">{caption}</p>
    </div>"""

DISCLAIMER = """
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12">
      <p style="font-size:14px; color:#7f8c8d; font-style:italic; border-top:1px solid #e0e0e0; padding-top:14px;">
        This module is a tool to assist with compliance workflows. Responsibility
        for statutory compliance rests with the user and their tax professional.
      </p>
    </div>
  </div>
</section>
"""

#: The free suite, in listing order. Every page links to all of these except
#: its own module, so a reader who liked one finds the rest. One list, one
#: place to update: adding a module here updates all nineteen pages.
#: Kept only so a page can be regenerated exactly as it stood before the suite
#: strip existed, which is how the strip was proved to be the sole change.
LEGACY_PAID_LINK = """
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12" style="text-align:center; padding:18px;">
      <p style="font-size:15px; color:#5d6d7e;">
        Need the full version? {paid_sentence}
      </p>
    </div>
  </div>
</section>
"""

SUITE = [
    ("drkds_in_eway_watch", "E-Way Bill Expiry Watch (India)"),
    ("drkds_in_fy_sequence", "Indian Financial Year Numbering"),
    ("drkds_in_gst_summary", "GST Outward and Inward Summary (India)"),
    ("drkds_in_inr_words", "Rupee Amounts in Words (Lakh and Crore)"),
    ("drkds_in_invoice_print_extras", "Indian Invoice Print Extras"),
    ("drkds_in_msme_vendor", "MSME Vendor Payment Tracking (India)"),
    ("drkds_in_partner_validate", "India Partner Identifier Validation"),
    ("drkds_in_payroll_components", "Indian Payroll Components (PF, ESI, PT)"),
    ("drkds_in_tds_rate_register", "India TDS Rate and Deduction Register"),
    ("drkds_in_upi_qr_invoice", "UPI Payment QR on Invoices (India)"),
    ("drkds_asset_register_lite", "Fixed Asset Register (Lite)"),
    ("drkds_branch_lite", "Branches (Lite)"),
    ("drkds_budget_lite", "Account Budgets (Lite)"),
    ("drkds_knowledge_base_lite", "Knowledge Base (Lite)"),
    ("drkds_label_designer_lite", "Label Designer (Lite)"),
    ("drkds_material_request_lite", "Material Request (Lite)"),
    ("drkds_password_vault_lite", "Password Vault (Lite)"),
    ("drkds_proforma_invoice", "Proforma Invoice"),
    ("drkds_ticketing_lite", "Support Tickets (Lite)"),
]

SUITE_URL = "https://github.com/jyotinb/drkds-odoo-free/tree/19.0/{module}"

#: The suite strip. It sits where the paid sentence already sat, and carries
#: that same sentence unchanged, so a module still mentions the paid app once
#: and only on its store page. Nothing here goes inside the running app.
SUITE_STRIP = """
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <div class="oe_span12" style="text-align:center; padding:18px;">
      <h3 class="oe_slogan" style="color:#183a5c;">The drkds free suite for Odoo 19 Community</h3>
      <p style="font-size:15px; line-height:2; color:#5d6d7e;">
{links}
      </p>{paid}
    </div>
  </div>
</section>
"""

SUITE_PAID = """
      <p style="font-size:15px; color:#5d6d7e;">
        Need the full version? {paid_sentence}
      </p>"""

SUITE_LINK = '        <a href="{url}" style="color:#183a5c;">{name}</a>'


def suite_strip(module, paid_sentence=None):
    """Render the shared strip for ``module``, which never links to itself."""
    links = [
        SUITE_LINK.format(url=SUITE_URL.format(module=tech),
                          name=html.escape(name))
        for tech, name in SUITE if tech != module
    ]
    if not links:
        raise ValueError("no sibling modules to link for %r" % module)
    paid = (SUITE_PAID.format(paid_sentence=html.escape(paid_sentence))
            if paid_sentence else "")
    return SUITE_STRIP.format(links="\n         \u00b7 \n".join(links), paid=paid)


#: Separator that turns a blank line in ``intro`` into a second paragraph.
#: A single-paragraph intro renders exactly as it did before.
INTRO_BREAK = (
    '</p>\n'
    '      <p style="font-size:16px; line-height:1.6; color:#2c3e50;">\n'
    '        '
)


def render_shots(shots):
    """Render the screenshot block for a page, in whichever layout it uses.

    A shot is ``(src, alt, caption)`` for the plain layout, or
    ``(src, alt, caption, heading)`` for the headed one.
    """
    e = html.escape
    if not shots:
        return ""
    if any(len(shot) > 3 for shot in shots):
        if not all(len(shot) > 3 for shot in shots):
            raise ValueError("mixed headed and plain screenshots on one page")
        return "".join(
            SHOT_HEADED.format(src=e(src), alt=e(alt), caption=e(caption),
                               heading=e(heading))
            for src, alt, caption, heading in shots
        ) + "\n"
    return SHOTS.format(rows="\n".join(
        SHOT.format(src=e(src), alt=e(alt), caption=e(caption))
        for src, alt, caption in shots
    ))


def render(title, summary, intro, features, notes, module=None, shots=(),
           disclaimer=False, paid_sentence=None, suite=True):
    e = html.escape
    feats = "\n".join(
        FEATURE.format(name=e(n), text=e(t)) for n, t in features
    )
    note_items = "\n".join(f"        <li>{e(n)}</li>" for n in notes)
    if suite:
        extra = suite_strip(module, paid_sentence)
    elif paid_sentence:
        extra = LEGACY_PAID_LINK.format(paid_sentence=e(paid_sentence))
    else:
        extra = ""
    shot_html = render_shots(shots)
    return TEMPLATE.format(
        title=e(title), summary=e(summary),
        intro=INTRO_BREAK.join(
            e(para.strip()) for para in re.split(r"\n\s*\n", intro.strip())
        ),
        features=feats, notes=note_items,
        shots=shot_html,
        disclaimer=DISCLAIMER if disclaimer else "", extra=extra,
    )


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    open(out, "w").write(render(**spec))
    print("wrote", out)
