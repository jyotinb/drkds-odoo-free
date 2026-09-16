# Changelog

## 19.0.1.0.0 - 2026-09-15  First release.

- Models renamed under the `drkds.lite.*` namespace: `drkds.branch` is now
  `drkds.lite.branch`, and the allowed-branches relation table is now
  `drkds_lite_branch_res_users_rel`. The previous names were shared with the
  paid Branch Operations app, so the two modules wrote to the same tables with
  different schemas and could not be installed in the same database. Security
  rules, views, record rules and tests were updated with them.
