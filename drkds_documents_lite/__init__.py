from . import models
from . import wizard


def uninstall_hook(env):
    """Keep every file. A document only ever points at an ir.attachment; the
    attachment itself is never ours to delete.

    Runs before the module's data is removed.

    1. Files uploaded through the document form were stored against the
       document model. Once the model is gone, an attachment that still
       names it would be unreadable to everyone (base refuses access to
       attachments of a removed model), so the link is cleared first and the
       file stays as a plain attachment, visible under Settings > Technical >
       Attachments. Mirrored attachments belong to their own record and are
       left untouched.
    2. The documents are then removed through the ORM. Because no attachment
       names the model any more, the ORM's own attachment clean-up finds
       nothing to delete.
    3. Sub-folders are detached from their parents so the folders seeded by
       the module can be deleted; a user-made child under Linked Records
       would otherwise block the seeded parent with a foreign key error.
    """
    env.cr.execute(
        "UPDATE ir_attachment SET res_model = NULL, res_id = NULL "
        "WHERE res_model = 'drkds.document' AND res_field IS NULL"
    )
    env["ir.attachment"].invalidate_model()
    env["drkds.document"].with_context(active_test=False).search([]).unlink()
    folders = env["drkds.document.folder"].with_context(active_test=False).search([])
    folders.write({"parent_id": False})
