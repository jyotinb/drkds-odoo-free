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
2. Pick the model. Wizards, abstract models, reports and other database
   views are not accepted: nothing could be written there.
3. Leave **Enabled** ticked and save.

From now on the list view of that model carries a **Mass update** entry in its
Actions menu for every internal user. Untick **Enabled**, or open the line and
press **Disable**, to remove the entry while keeping the line for later.
Deleting the line removes the entry too.

The **Bound Action** column shows the technical server action that carries the
entry. It is created and removed for you; there is no need to touch it.

The wizard only runs on enabled models. Disabling a model also stops a
wizard a user already has open on it, and a wizard created directly over
RPC for a model that is not enabled is refused.

**Choose with care.** Everyone with write access on an enabled model can
change any field the model lets them write. Restrictions that exist only in
a form view are not applied: a field the form shows read-only in a given
state, or hides from a group, can still be written. For example, with
Journal Entries enabled a billing user could rename a posted invoice,
because only the form makes the number read-only. Enable a model only when
that is acceptable.

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
   | Formatted text | a rich-text editor (a plain box taking HTML on a database without Odoo's editor module, which any app installs) |
   | Whole number, number, monetary | a number |
   | Yes / No | a checkbox |
   | Date, date and time | a date picker |
   | Selection | the list of choices of that field |
   | Link to a record | a record picker on the target model |
   | Tags | a record picker; the chosen tag is **added** to each record |

   The record picker lists every record of the target model you can read; it
   does not apply a narrower choice the form may use (for example internal
   users only for a salesperson). A record you cannot read, such as one of a
   company you are not in, is refused. A choice is checked against the
   field's own choices when you apply.

6. Or tick **Set Empty** to clear the field instead. Numbers become zero, a
   tag field loses all its tags, everything else becomes empty. Set Empty is
   not offered on a required field, except a number (set to zero) or a
   yes/no (set to No).
7. Press **Apply** and confirm.

## 4. Reading the result

The wizard stays open and shows:

- **Updated**: the number of records written.
- **Not Updated**: the number of records that were refused.
- A list of the refused records, with their name, id and the reason Odoo
  gave (usually an access rule). A record you cannot even read is shown by
  its id only. A record deleted after you selected it is listed as no longer
  existing.

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
  tracking behave as if you had edited each record by hand. A constraint or
  business rule error (for example a duplicate reference, or archiving a
  contact linked to an active user) stops the run and is shown as usual;
  nothing is written.
- Notifications follow each record as for a hand edit: assigning a
  salesperson on 200 orders sends that person 200 assignment emails.
- A translatable field (a tag name, for instance) is written in your current
  language, as in the form. Other languages keep their translation.
- The wizard never uses superuser rights.
- Your wizard is visible to you only. No other user can read it or change
  what it is about to write.

## 7. Uninstalling

Uninstalling the module deletes every **Mass update** action it created,
including one an administrator renamed, edited or duplicated, so no Actions
menu keeps a dead entry. Data written through the wizard is
ordinary record data and stays as it is.

## 8. Troubleshooting

**Mass update is not in the Actions menu.** The model is not enabled, or
the line is disabled. Check Settings > Technical > Mass Update. Reload the
page after enabling. If someone deleted the action under Settings >
Technical > Server Actions, the line still reads Enabled: untick **Enabled**
and tick it again to recreate the action.

**"Mass update is not enabled for ..."** The administrator disabled the
model while your wizard was open. Ask for it to be enabled again.

**The field I need is not offered.** See section 5. Most often the field is
computed without an inverse, or reserved to a group you are not in.

**All records are reported as not updated.** A record rule refuses every
selected record for your user; ask your administrator.

**A value for a selection field does not appear.** The choices come from the
field's own definition; a choice removed from the field is not offered.
