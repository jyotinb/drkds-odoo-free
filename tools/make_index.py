"""Render the shared drkds store description page (static/description/index.html).

Usage: import and call render(...), or run with a JSON spec file.
Keeps every module's listing visually identical, which is the point.
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

PAID_LINK = """
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


#: Separator that turns a blank line in ``intro`` into a second paragraph.
#: A single-paragraph intro renders exactly as it did before.
INTRO_BREAK = (
    '</p>\n'
    '      <p style="font-size:16px; line-height:1.6; color:#2c3e50;">\n'
    '        '
)


def render(title, summary, intro, features, notes,
           disclaimer=False, paid_sentence=None):
    e = html.escape
    feats = "\n".join(
        FEATURE.format(name=e(n), text=e(t)) for n, t in features
    )
    note_items = "\n".join(f"        <li>{e(n)}</li>" for n in notes)
    extra = PAID_LINK.format(paid_sentence=e(paid_sentence)) if paid_sentence else ""
    return TEMPLATE.format(
        title=e(title), summary=e(summary),
        intro=INTRO_BREAK.join(
            e(para.strip()) for para in re.split(r"\n\s*\n", intro.strip())
        ),
        features=feats, notes=note_items,
        disclaimer=DISCLAIMER if disclaimer else "", extra=extra,
    )


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    open(out, "w").write(render(**spec))
    print("wrote", out)
