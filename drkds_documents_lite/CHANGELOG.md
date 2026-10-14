# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Folder tree with full path, sequence, company, read groups, write groups
  and an optional mirrored model; sub-folders inherit the parent's groups.
  Two folders seeded: Company Documents and Linked Records.
- Documents with name, folder, file stored as an ir.attachment, tags, owner,
  contact, linked record, description, expiry date; type and size read from
  the file; chatter, activities and field tracking.
- Kanban with image thumbnails and file-type icons, list, form with inline
  PDF or image preview and Download and Open Record buttons, activity view,
  search with filters and group-bys, Documents and Expiring menus.
- Add to Documents server action on attachment lists, with a folder and tag
  wizard; files are linked, never copied or filed twice.
- Chatter mirroring for the models picked in Settings, into a folder per
  model under Linked Records.
- Daily expiry job scheduling a to-do for the owner seven days ahead, once
  per expiry date.
- Document user and manager groups, record rules from folder groups and
  multi-company rules.
- Uninstall keeps every file: uploaded files become plain attachments,
  mirrored files stay on their records.

### Fixed during review, before release

- The app menu was named *Documents*, the name of an Odoo Enterprise app.
  It is now *Document Folders*, the module's own title; the menu paths in
  the README and manual follow it.
- The closing sentence about the paid app said it offers OCR-based
  indexing. It does not; the sentence now lists only what the paid
  Document Management app does.
- A document whose file belongs to a record the reader cannot open (a
  mirrored chatter file, a filed attachment) made the whole Kanban, and the
  form, fail with an access error for that reader. The document now shows
  without its file (type and size only, no Download), and the file keeps
  the access of its record.
- A document could be pointed, through the API, at any attachment, showing
  the name, type and size of files its author could not read. The author
  must now be able to read the file.
- A user could move a document into a folder they may not file in, or into
  another company, because record rules are checked before a write only.
  The destination is now checked too.
- Restricting a folder left its existing sub-folders, and their documents,
  open. A sub-folder now follows its parent's read and write groups until
  it is given groups of its own.
- Posting a file in a chatter failed with a company error when the mirror
  folder was kept for another company than the record, or the record's
  contact belonged to another company. Such records are no longer mirrored
  into a company folder, and a contact of another company is left off
  (Add to Documents likewise).
- The poster of a mirrored file, and an owner set by a manager, were made
  followers even when they could not open the document, and so received
  every message posted on it. An owner or poster now follows a document
  only when they can open it.
- Expiry reminders went to OdooBot for documents without an owner or with
  an archived owner, and were marked as sent, so nobody was ever told; an
  owner outside the folder's groups was assigned, subscribed and notified.
  Such documents now wait, unreminded, for an owner who can open them.
- The expiry job counted the seven days on the UTC date; it now uses the
  owner's date in their timezone.
- New tags had colour 0, which the Kanban cards do not show. A new tag gets
  a random colour.
- Add to Documents looked up the model's mirror folder with superuser
  rights, offering (and naming) a folder the user could not see; it now
  searches with the user's rights.
- The uninstall hook freed only document attachments; anything attached to
  a folder or a tag would have been deleted with the models. It now frees
  the attachments of every model of the module.
