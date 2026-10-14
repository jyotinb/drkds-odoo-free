# Document Folders (Lite)

A folder tree for company files, with tags, owners, linked records, expiry
reminders and chatter mirroring, on Odoo 19 Community.

Contracts, licences, certificates, scanned invoices, policies: every company
has files that belong to nobody's inbox. This module gives them a home. A file
goes into a folder, carries tags, an owner, a contact and a link to the record
it concerns, and can be given an expiry date that raises a to-do a week
ahead. Files already posted in a chatter can be filed with one action or
mirrored automatically.

## What you get

| Piece | What it does |
|---|---|
| Folder | Name, parent, sequence, company, read groups, write groups, optional mirrored model; full path such as `Legal / Contracts / 2026` |
| Document | Name, folder, file (a normal `ir.attachment`), tags, owner, contact, linked record, description, expiry date; size and type read from the file; chatter and activities |
| Add to Documents | An action on any attachment list that files the selected attachments into a folder, without copying them |
| Chatter mirroring | Models chosen in Settings; every file posted in their chatter is filed in a folder named after the model under *Linked Records* |
| Expiry reminders | A daily job schedules a to-do for the owner seven days before expiry, once per expiry date |
| Views | Kanban with image thumbnails and file-type icons, list, form with inline PDF or image preview, activity view, search with filters and group-bys, an *Expiring* menu |
| Security | Document user and manager groups; record rules from the folder's groups and multi-company rules |

Two folders are installed: **Company Documents** and **Linked Records**. The
second is the parent of the per-model mirror folders.

## Installation

Copy the module into your addons path, update the apps list and install
**Document Folders (Lite)**. Depends on `base` and `mail` only. The user who
installs it is made a document manager.

## Configuration

1. **Settings > Users**: give each person the *Document Folders* level:
   *User* to file and read documents, *Manager* to see everything and
   maintain folders, tags and settings.
2. **Document Folders > Configuration > Folders**: build the tree. On each folder,
   **Read Groups** says who may see it (empty: every document user) and
   **Write Groups** says who may file in it (empty: anyone who can see it).
   A new sub-folder starts with its parent's groups and follows later
   changes to them, until it is given groups of its own.
3. **Document Folders > Configuration > Tags**: a few labels that cut across
   folders, such as *Signed*, *Draft*, *Renewal due*. A new tag gets a
   colour of its own; change it in the list.
4. **Document Folders > Configuration > Settings**, or **Settings > Document
   Folders**: pick the models whose chatter files should be mirrored. A
   folder named after each model is created under *Linked Records*.

## Use

1. **Document Folders > Documents > New**: name, file, folder, tags, owner, contact,
   expiry date. The size and type are read from the file. PDFs and images
   show a preview on the form.
2. **Add to Documents**: on any attachment list (for example *Settings >
   Technical > Attachments*), select files, open the *Actions* menu and
   choose *Add to Documents*. Pick the folder and tags. The attachment is
   linked, not copied, and the document carries the record and the contact
   it came from. A folder kept for one company gives the document that
   company; a contact of another company is then left off.
3. **Mirroring**: once a model is in the settings, posting a file in the
   chatter of one of its records files it as a document in that model's
   folder, linked to the record, owned by the person who posted it. The
   poster follows the document only if they can open it. A record of a
   company the folder is not kept for is not mirrored, and the post itself
   always goes through.
4. **Expiring**: lists everything expiring within seven days or already
   expired. The nightly job schedules a to-do for the owner, with the
   expiry date as deadline, counting the seven days on the owner's own date
   (their timezone). Changing the expiry date makes it fire again for the
   new date. A document whose owner cannot act on it (no owner, an archived
   owner, or an owner outside the folder's groups) gets no to-do until it
   has an owner who can open it; it is still listed under *Expiring*.
5. **Open Record** on a linked document jumps to the record it concerns.

## Behaviour worth knowing

- A restricted folder is invisible, documents included, to anyone outside
  its read groups. The rules are record rules, so this holds in exports and
  the API, not only in the interface.
- Moving a document into another folder, or another company, needs the
  right to file there.
- A file keeps the access of the record it belongs to. A document whose
  file belongs to a record you cannot open shows its name, type and size,
  but not the file. A document can only be pointed at a file its author
  can open.
- A document's owner, and the poster of a mirrored file, follow the
  document and get its expiry reminders only when they can open it.
- A file uploaded through the form belongs to its document and is deleted
  with it. A file taken from another record (by *Add to Documents* or by
  mirroring) stays with that record whatever happens to the document.
- The same attachment is never filed twice.
- A folder that still holds documents, or sub-folders, cannot be deleted;
  archive it instead.
- Uninstalling the module keeps every file. Files uploaded through the form
  or posted in a document's chatter become plain attachments under
  *Settings > Technical > Attachments*; mirrored files are left on their
  records.
- The lite edition has no file versions, no share links, no request-a-file
  and no workflow actions on folders.

Part of the drkds Indian SME suite for Odoo 19 Community.

The paid drkds Document Management app adds workflow buttons on folders, document requests with portal upload, share links, versions with restore, check-out locking and full-text search that also reads PDF text.
