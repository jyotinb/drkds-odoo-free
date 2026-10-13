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
