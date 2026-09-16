# Changelog

## 19.0.1.0.0 - 2026-09-15  First release.

- Models renamed under the `drkds.lite.*` namespace: `drkds.label.template`,
  `drkds.label.template.line` and `drkds.label.print` became
  `drkds.lite.label.template`, `drkds.lite.label.template.line` and
  `drkds.lite.label.print`. `drkds.label.template` was shared with the paid
  Label Designer app, so the two modules wrote to the same table with
  different schemas and could not be installed in the same database. Access
  rules, views, the report action, the shipped template data and the tests
  were updated with them.
