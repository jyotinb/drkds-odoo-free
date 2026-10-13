from . import models
from . import wizard

# Every persistent model of this module; any of them can own attachments.
MODELS_OWNING_FILES = ("drkds.document", "drkds.document.folder", "drkds.document.tag")


def uninstall_hook(env):
    """Keep every file. A document only ever points at an ir.attachment; the
    attachment itself is never ours to delete.

    Runs before the module's data is removed.

    1. When a model is removed, mail deletes every attachment that still
       names it (``ir.model.unlink``). Files uploaded through the document
       form, files posted in a document's chatter, and anything attached to a
       folder or a tag through the API are stored against this module's
       models, so their link is cleared first and each file stays as a plain
       attachment, visible under Settings > Technical > Attachments.
       Mirrored attachments belong to their own record and are left
       untouched.
    2. The documents are then removed through the ORM. Because no attachment
       names the model any more, the ORM's own attachment clean-up finds
       nothing to delete.
    3. Sub-folders are detached from their parents so the folders seeded by
       the module can be deleted; a user-made child under Linked Records
       would otherwise block the seeded parent with a foreign key error.
    """
    env.cr.execute(
        "UPDATE ir_attachment SET res_model = NULL, res_id = NULL "
        "WHERE res_model IN %s AND res_field IS NULL",
        [MODELS_OWNING_FILES],
    )
    env["ir.attachment"].invalidate_model()
    env["drkds.document"].with_context(active_test=False).search([]).unlink()
    folders = env["drkds.document.folder"].with_context(active_test=False).search([])
    folders.write({"parent_id": False})
