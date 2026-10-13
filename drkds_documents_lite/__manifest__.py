{
    "name": "Document Folders (Lite)",
    "summary": "A folder tree for company files, with tags, owners, linked records, expiry reminders and chatter mirroring, on Odoo 19 Community",
    "description": """
Document Folders (Lite)
=======================

A central place for the files a company keeps: contracts, licences,
certificates, scanned invoices, policies. Files sit in a folder tree, carry
tags, an owner, a contact and a link to the record they concern, and can be
given an expiry date that raises a reminder a week ahead.

What it gives you
-----------------
* **Folders** - a tree of folders, each with its own read and write groups.
  A folder with no read group is open to every document user; a folder with
  read groups is invisible to anyone outside them, and so are its documents.
  Sub-folders follow their parent's groups until given groups of their own.
* **Documents** - a file stored as a normal Odoo attachment, with name,
  folder, tags, owner, contact, a link to any record, description, expiry
  date, and the size and type read from the file. Kanban with image
  thumbnails and file-type icons, list, form with an inline PDF or image
  preview, search by folder, tag, owner, contact and expiry.
* **Add to Documents** - an action on any attachment list that files the
  selected attachments into a folder of your choice, without copying the
  file.
* **Chatter mirroring** - pick models in Settings; from then on every file
  posted in the chatter of those records is also filed as a document in a
  folder of its own, linked back to the record.
* **Expiry reminders** - a daily job schedules a to-do for the owner seven
  days before a document expires, counted on the owner's own date.

Security
--------
Document users see the folders and documents their groups allow. Document
managers see everything and maintain folders, tags and the mirroring list.
Record rules enforce it, so it holds in exports and the API too. A file
keeps the access of the record it belongs to, and a document's owner
follows it and is reminded about it only when they can open it.

The drkds Documents app adds workflow actions on folders, request-a-file,
sharing links, versioning and OCR-based indexing.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/drkds_documents_groups.xml",
        "security/ir.model.access.csv",
        "security/drkds_documents_rules.xml",
        "data/drkds_document_folder_data.xml",
        "data/drkds_documents_cron.xml",
        "data/drkds_documents_server_action.xml",
        "wizard/drkds_document_add_wizard_views.xml",
        "views/drkds_document_tag_views.xml",
        "views/drkds_document_folder_views.xml",
        "views/drkds_document_views.xml",
        "views/res_config_settings_views.xml",
        "views/drkds_documents_menus.xml",
    ],
    "images": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "uninstall_hook": "uninstall_hook",
}
