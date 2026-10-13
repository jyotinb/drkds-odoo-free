# User manual - Mass Update

## 1. What it is for

You have many records that need the same change: a tag on every contact of
a mailing, a new salesperson on a page of customers, a category on a set of
products. Instead of opening each record, select them in the list, run
**Mass update**, choose the field and the value, apply.

The change is made as you. Whatever you could not edit by hand you cannot
mass update either: such records are listed in the result and left alone,
while every other record is updated.

## 2. Enabling a model (administrator)

Settings > Technical > Mass Update. Only Settings administrators see this
menu.

1. Press **New** (the list is editable in place).
2. Pick the model. Wizards and other transient models are not accepted.
3. Leave **Enabled** ticked and save.

From now on the list view of that model carries a **Mass update** entry in its
Actions menu for every internal user. Untick **Enabled**, or open the line and
press **Disable**, to remove the entry while keeping the line for later.
Deleting the line removes the entry too.

The **Bound Action** column shows the technical server action that carries the
entry. It is created and removed for you; there is no need to touch it.

## 3. Running a mass update

1. Open the list view of an enabled model and tick the records to change.
   Use the "select all" option at the top of the list to take every record of
   the current filter.
2. Actions > **Mass update**.
3. The wizard shows the model and the number of selected records.
4. **Field to Update**: pick the field. Only fields that can actually be
   written are offered (see section 5). Press **Next**. (**Back** returns to
   this step.)
5. Enter the value. The input matches the field:

   | Field type | Input |
   | --- | --- |
   | Text | a single line |
   | Long text | a multi-line box |
   | Formatted text | a rich-text editor |
   | Whole number, number, monetary | a number |
   | Yes / No | a checkbox |
   | Date, date and time | a date picker |
   | Selection | the list of choices of that field |
   | Link to a record | a record picker on the target model |
   | Tags | a record picker; the chosen tag is **added** to each record |

6. Or tick **Set Empty** to clear the field instead. Numbers become zero, a
   tag field loses all its tags, everything else becomes empty.
7. Press **Apply** and confirm.

## 4. Reading the result

The wizard stays open and shows:

- **Updated**: the number of records written.
- **Not Updated**: the number of records that were refused.
- A list of the refused records, with their name, id and the reason Odoo
  gave (usually an access rule).

Updated and Not Updated always add up to the number of selected records.
Press **Close** when done. There is no undo: to reverse a change, run the
wizard again with the previous value.

## 5. Which fields are offered

Offered: fields that are stored in the database, writable, and of a type the
wizard has an input for (text, long text, formatted text, whole number,
number, monetary, yes/no, date, date and time, selection, link, tags).

Not offered, on purpose:

- the record id and the creation / modification user and date;
- binary fields (files, images) and one-to-many lists;
- fields that are not stored;
- readonly fields, including computed fields that have no way to be written
  back (a value set there would be refused or overwritten by the ORM);
- fields reserved to a security group you are not a member of.

A computed field that Odoo itself lets you edit (for example a contact's
Salesperson, which is only proposed from the parent company) is offered.

## 6. How access is applied

- You need write access on the model to apply; otherwise the wizard refuses
  with the usual access error before writing anything.
- Record rules are applied record by record. The wizard writes in batches of
  500; when a batch is refused, each record of that batch is tried alone, so
  only the refused records are left out and reported.
- The write is a normal write by your user. Constraints, required fields and
  tracking behave as if you had edited each record by hand. A constraint
  error (for example a duplicate reference) stops the run and is shown as
  usual; nothing is half-written.
- The wizard never uses superuser rights.

## 7. Uninstalling

Uninstalling the module deletes every **Mass update** action it created, so
no Actions menu keeps a dead entry. Data written through the wizard is
ordinary record data and stays as it is.

## 8. Troubleshooting

**Mass update is not in the Actions menu.** The model is not enabled, or
the line is disabled. Check Settings > Technical > Mass Update. Reload the
page after enabling.

**The field I need is not offered.** See section 5. Most often the field is
computed without an inverse, or reserved to a group you are not in.

**All records are reported as not updated.** A record rule refuses every
selected record for your user; ask your administrator.

**A value for a selection field does not appear.** The choices come from the
field's own definition; a choice removed from the field is not offered.
