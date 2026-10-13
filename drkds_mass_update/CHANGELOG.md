# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Settings > Technical > Mass Update: list of models enabled for mass update.
  Enabling a model creates a server action bound to its list view (Actions
  menu, "Mass update"); disabling or deleting the line removes it; uninstall
  removes every action the module created.
- Wizard: selected record count, picker limited to stored writable fields of
  a supported type (char, text, html, integer, float, monetary, boolean,
  date, datetime, selection, many2one, many2many), typed value input, Set
  Empty option.
- Write as the current user in batches of 500; a batch refused by an access
  rule is retried record by record; result with updated count, failed count
  and the records that could not be changed.
- Administrator (Settings group) manages the enabled models; any internal
  user with write access on the model may run the wizard.

### Fixed during review, before release

- **Security:** an internal user could read and rewrite another user's open
  wizard (Odoo 19 puts no owner restriction on transient records), so an
  administrator's Apply could be turned into a write of the other user's
  choosing, such as adding them to the Settings group. Each wizard is now
  visible to the user who opened it only (record rule
  `rule_drkds_mass_update_wizard_own`).
- Called over RPC, the wizard ran on any model, enabled or not; it now
  refuses a model the administrator has not enabled.
- Set Empty on a required field reached the database and failed with a NOT
  NULL error; it is now refused with a clear message and the tick is hidden
  for required fields (numbers and yes/no excepted).
- A choice for a selection field whose options come from a method (such as
  Language) was not validated, so any text could be stored; it must now be
  one of the field's choices.
- A crafted id of a record the user cannot read (for example a contact of
  another company) was accepted as the value of a link or tag field; the
  record must now be readable.
- A record deleted after it was selected was silently left out, so updated
  plus not updated did not add up to the selection; it is now reported as
  no longer existing. A repeated id counts once.
- The result field stored raw HTML written over RPC; it is now sanitized.
- Abstract models and models read from a database view could be enabled,
  giving an Actions menu entry that could never write; they are refused.
- Uninstall left a duplicated bound action behind; the uninstall hook now
  also removes any server action whose code opens the wizard.
- The wizard form's always-invisible fields carried no reason, which base's
  `test_uncommented_invisible_field` reports as an error; each is commented.
