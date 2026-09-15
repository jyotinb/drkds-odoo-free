"""Threshold reminder: posted customer documents with no e-way bill.

A reminder, never a block. Posting is not prevented and nothing is raised:
exempt goods, short local movements and services legitimately carry no e-way
bill, so this is a list to work through, not a rule to enforce.
"""
from odoo import api, fields, models
from odoo.fields import Domain

#: Document types that move goods out and may therefore need an e-way bill.
EWAY_MOVE_TYPES = ("out_invoice", "out_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

    drkds_eway_missing = fields.Boolean(
        string="E-Way Bill Missing",
        compute="_compute_drkds_eway_missing",
        search="_search_drkds_eway_missing",
        help="Posted customer document at or above the company e-way bill "
        "threshold with no generated e-way bill. A reminder, not a rule.",
    )

    @api.depends(
        "amount_total", "state", "move_type", "company_id",
        "l10n_in_ewaybill_ids.state",
    )
    def _compute_drkds_eway_missing(self):
        for move in self:
            threshold = move.company_id.drkds_eway_threshold or 0.0
            has_bill = any(bill.state == "generated" for bill in move.l10n_in_ewaybill_ids)
            move.drkds_eway_missing = bool(
                move.move_type in EWAY_MOVE_TYPES
                and move.state == "posted"
                and not has_bill
                and threshold
                and move.amount_total >= threshold
            )

    def _search_drkds_eway_missing(self, operator, value):
        """Search the flag without storing it, so a changed threshold is live.

        The threshold is a company field, so the value comparison is built once
        per company across the companies the user is allowed to see.

        Odoo passes ``in`` and ``not in`` for boolean domains as well as ``=``
        and ``!=``, so all four are handled; anything else is refused rather
        than guessed at.
        """
        if operator in ("in", "not in"):
            values = value if isinstance(value, (list, tuple, set)) else [value]
            truthy = any(bool(item) for item in values)
            falsy = any(not bool(item) for item in values)
            if truthy and falsy:
                return Domain.TRUE
            wanted = truthy if operator == "in" else not truthy
        elif operator in ("=", "!="):
            wanted = bool(value) if operator == "=" else not bool(value)
        else:
            raise NotImplementedError("Unsupported operator %s" % operator)
        companies = self.env["res.company"].search([
            ("id", "in", self.env.companies.ids),
            ("drkds_eway_threshold", ">", 0.0),
        ])
        above_threshold = Domain.OR([
            Domain("company_id", "=", company.id)
            & Domain("amount_total", ">=", company.drkds_eway_threshold)
            for company in companies
        ] or [Domain.FALSE])
        domain = (
            Domain("move_type", "in", list(EWAY_MOVE_TYPES))
            & Domain("state", "=", "posted")
            & ~Domain("l10n_in_ewaybill_ids.state", "=", "generated")
            & above_threshold
        )
        return domain if wanted else ~domain
