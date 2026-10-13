# Mass Update

Update one field on many selected records from the list view, as the current
user, with a clear report of what could not be changed. Odoo 19 Community,
depends on `base` only, LGPL-3.

## What it does

- **Settings > Technical > Mass Update.** The administrator lists the models
  on which mass update is allowed. Enabling a model adds a **Mass update**
  entry to the Actions menu of its list view (a server action bound to that
  model). Disabling or deleting the line removes it. Uninstalling the module
  removes every action it created.
- **The wizard, in two steps.** Shows how many records are selected and
  offers only the fields that can be written; **Next** then asks for a value
  of the matching kind, or a **Set Empty** tick; **Apply** writes.
- **Field list.** Stored, writable fields of a supported type: text, long
  text, formatted text, whole number, number, monetary, yes/no, date, date
  and time, selection, link to a record (many2one), tags (many2many).
  Excluded: `id`, `create_uid`, `create_date`, `write_uid`, `write_date`,
  binary fields, one2many fields, non-stored fields, readonly fields,
  computed fields without an inverse, and fields reserved to a group the
  current user is not in.
- **Tags are added, not replaced.** For a many2many field the chosen record is
  linked to every selected record; existing tags stay. Set Empty removes all
  tags.
- **As the current user, in batches of 500.** The write never uses superuser
  rights. When an access rule refuses a batch, every record of that batch is
  retried alone, so one locked record never blocks the others.
- **Result.** Updated count, not-updated count, and the list of records that
  could not be changed with the reason Odoo gave.

## Install

Copy the folder into your addons path, update the apps list and install
**Mass Update**. No configuration data is created on install.

## Configure

1. Settings > Technical > Mass Update (Settings administrator only).
2. Add a line, pick the model (for example *Contact*), leave **Enabled**
   ticked, save. The **Mass update** entry is now in the Actions menu of that
   model's list view.
3. Untick **Enabled** (or press **Disable** on the form) to take it away
   without losing the line.

## Use

1. Open the list view of an enabled model and select the records.
2. Actions > **Mass update**.
3. Pick the field and press **Next**.
4. Enter the value or tick **Set Empty**, press **Apply** and confirm.
5. Read the result: how many were updated and which records could not be
   changed. Close.

One field per run. Run the wizard again on the same selection for a second
field.

## Security

| Who | Can |
| --- | --- |
| Settings administrator (`base.group_system`) | Add, enable, disable and delete enabled models. |
| Any internal user (`base.group_user`) | See the Mass update action and open the wizard on an enabled model. |

Applying requires write access on the model; without it the wizard refuses
with the usual access error. Record rules apply record by record: a refused
record is reported, the rest are updated. The field list also hides fields
reserved to groups the user is not in.

## Notes

- There is no undo. The wizard asks for confirmation before writing.
- Writes are plain ORM writes: constraints, onchange-independent computes and
  tracking behave exactly as a manual edit of each record would.
- `drkds.mass.update.model` is a configuration table; it has no company
  field because a bound action is global to the model.
- The wizard reads field names, labels and choices from the registry, not
  from `ir.model.fields`, because a plain internal user has no read access
  on the technical models in Odoo 19. That is also why the field is chosen
  before the value.
- Uninstall is clean: the uninstall hook deletes the bound server actions,
  the models and views go with the module.

Part of the drkds Indian SME suite for Odoo 19 Community.
