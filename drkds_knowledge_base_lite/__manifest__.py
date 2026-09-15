{
    "name": "Knowledge Base (Lite)",
    "summary": "Internal articles in a section tree, with rich text, tags and search, on Odoo 19 Community",
    "description": """
Knowledge Base (Lite)
=====================

A place to write down how your company actually does things, and a way to find
it again six months later.

Articles are rich text, filed in a tree of sections, tagged, searched and
bookmarked. Nothing here talks to the outside world and nothing is hidden
behind a paywall inside the app.

Sections
--------
* Sections nest as deeply as the subject deserves, and every section carries
  its full path - *Handbook / Onboarding / First Week* - so a title is never
  ambiguous on its own.
* The hierarchy is stored with a materialised path, so "everything under this
  branch" is one indexed query rather than a walk through the tree.
* A section cannot be moved inside one of its own sub-sections; the save is
  refused with a plain message.

Articles
--------
* Title, rich text body, section, tags, author, last editor and a draft or
  published status.
* The last editor is stamped automatically whenever the text, the filing or the
  status changes, so it is never wrong.
* Full chatter: comments, followers and activities on every article.

Finding things again
--------------------
* The search box searches **inside the article**, not only the title. A saved
  article keeps a flattened plain text copy of its body, so a word that appears
  only in the third paragraph is still findable.
* A section tree sits beside the article list, with live counts, and selecting a
  branch shows everything below it.
* Filters for section, tag, author, status and recency; group by section,
  author, last editor, status or month of last change.
* **Recently Updated** answers "what changed while I was away".

Bookmarks
---------
* One click bookmarks an article into **My Bookmarks**. Bookmarks are private to
  each user and are stored separately from the article, so a reader with no
  write access can still keep their own list.

Access
------
* Two groups. **Reader** sees published articles and keeps bookmarks. **Editor**
  writes articles, manages sections and tags, and is the only one who sees
  drafts.
* Enforced by record rules, not by hiding buttons.

The drkds Knowledge Base app adds article versioning with rollback, portal
sharing and approval workflows.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/drkds_kb_security.xml",
        "security/ir.model.access.csv",
        "views/drkds_kb_section_views.xml",
        "views/drkds_kb_tag_views.xml",
        "views/drkds_kb_article_views.xml",
        "views/drkds_kb_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "drkds_knowledge_base_lite/static/src/scss/drkds_kb.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
