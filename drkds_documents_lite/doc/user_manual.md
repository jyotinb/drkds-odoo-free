# Document Folders (Lite) — user manual

## 1. Give people access

In **Settings > Users**, open a user and set the **Document Folders** level:

- **User** — sees the folders their groups allow and files documents in
  them.
- **Manager** — sees every folder and document, maintains folders, tags
  and the mirroring settings.

The user who installed the module is a manager already.

## 2. Build the folder tree

**Documents > Configuration > Folders**. Two folders come installed:
**Company Documents** and **Linked Records**.

For each folder:

| Field | Meaning |
|---|---|
| Folder | Its name. The **Full Path** shows every ancestor, e.g. `Legal / Contracts`. |
| Parent Folder | Where it sits in the tree. |
| Read Groups | Who may see the folder and its documents. Empty: every document user. |
| Write Groups | Who may add, change or delete documents in it. Empty: anyone who can see it. |
| Company | Leave empty for a folder shared by every company. |
| Mirrored Model | Set from Settings; files posted in this model's chatter land here. |

A new sub-folder starts with its parent's read and write groups and company,
so a restricted branch stays restricted. A manager may change them
afterwards.

The **Documents** button on the form opens everything filed in the folder
and its sub-folders.

## 3. Tags

**Documents > Configuration > Tags**: name and colour. A document can carry
any number of tags, and the search filters by them.

## 4. File a document

**Documents > Documents > New**.

- **Name** — what the file is.
- **File** — upload it. The **Type** and **Size** are read from the file.
- **Folder**, **Tags**.
- **Owner** — defaults to you. The expiry reminder goes to the owner.
- **Contact** — the customer, supplier or authority the file concerns.
- **Expiry Date** — when the file lapses, if it does.
- **Description** — free notes.

A PDF or image shows in the **Preview** tab. **Download** fetches the file.
The chatter below keeps comments and activities on the document.

## 5. File an existing attachment

Any list of attachments, for example **Settings > Technical > Attachments**,
has **Add to Documents** in its **Actions** menu. Select the files, run it,
choose the folder and tags, click **Add**. The documents open in a list.

The file is linked, not copied. The document records the record the
attachment came from, and the contact when the record has one. An
attachment already filed is skipped; if every selected file is already
filed, the wizard says so.

## 6. Mirror chatter files automatically

**Documents > Configuration > Settings** (also under **Settings > Document
Folders**). In **Mirror chatter files of**, pick the models — Contact,
Sales Order, Vendor Bill, whatever your database has — and save.

A folder named after each model appears under **Linked Records**. From then
on, every file posted in the chatter of such a record is also filed there,
linked to the record, with the poster as owner and the record's contact and
company. Removing a model from the list stops the mirroring; the folder and
its documents stay.

## 7. Expiry reminders

**Documents > Expiring** lists documents expiring within the next seven
days or already past their date; the Kanban and list mark them in orange
and red.

A daily scheduled job, *Documents: expiry reminders*, schedules a **To Do**
activity for the owner of each such document, with the expiry date as the
deadline. Each expiry date is reminded once; set a new date after a renewal
and the job fires again when that date comes within seven days.

## 8. Find things again

The search box looks in the name, the description and the file name.
Filters: My Documents, Linked to a Record, Expiring Soon, Expired, Has
Expiry Date, Images, PDF, activity filters, Archived. Group by folder,
owner, contact, linked model or expiry month. Searching on **Folder** also
matches its sub-folders.

## 9. Open the record a document concerns

A document taken from a record shows **Linked Record** and an **Open
Record** button.

## 10. Deleting and uninstalling

- Deleting a document deletes the file only when the document owned it
  (uploaded through the form). A file taken from another record stays with
  that record.
- A folder with documents or sub-folders cannot be deleted; archive it.
- Uninstalling keeps every file. Files uploaded through the form remain as
  plain attachments under **Settings > Technical > Attachments**.
