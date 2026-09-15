from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestTicketing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["drkds.ticket"]
        cls.Stage = cls.env["drkds.ticket.stage"]
        cls.Team = cls.env["drkds.ticket.team"]

        cls.stage_new = cls.env.ref("drkds_ticketing_lite.stage_new")
        cls.stage_progress = cls.env.ref("drkds_ticketing_lite.stage_in_progress")
        cls.stage_solved = cls.env.ref("drkds_ticketing_lite.stage_solved")

        cls.agent_a = new_test_user(
            cls.env, login="drkds_agent_a",
            groups="base.group_user,drkds_ticketing_lite.group_ticket_user",
        )
        cls.agent_b = new_test_user(
            cls.env, login="drkds_agent_b",
            groups="base.group_user,drkds_ticketing_lite.group_ticket_user",
        )
        cls.manager = new_test_user(
            cls.env, login="drkds_manager",
            groups="base.group_user,drkds_ticketing_lite.group_ticket_manager",
        )
        cls.team_a = cls.Team.create({
            "name": "Team A",
            "member_ids": [(6, 0, cls.agent_a.ids)],
            "default_user_id": cls.agent_a.id,
        })
        cls.team_b = cls.Team.create({
            "name": "Team B",
            "member_ids": [(6, 0, cls.agent_b.ids)],
        })
        cls.customer = cls.env["res.partner"].create({
            "name": "Acme Ltd", "email": "support@acme.example",
        })

    # -- numbering -----------------------------------------------------
    def test_number_is_unique_and_sequential(self):
        """Each ticket takes the next number from the sequence, never a duplicate."""
        tickets = self.Ticket.create([
            {"name": "First"}, {"name": "Second"}, {"name": "Third"},
        ])
        numbers = tickets.mapped("number")
        self.assertEqual(len(set(numbers)), 3, "numbers must be unique")
        for number in numbers:
            self.assertTrue(number.startswith("TKT/"))
        tails = [int(number.split("/")[1]) for number in numbers]
        self.assertEqual(tails, sorted(tails))
        self.assertEqual(tails[2] - tails[0], 2, "numbering must not skip")

    def test_copy_takes_a_fresh_number(self):
        ticket = self.Ticket.create({"name": "Original"})
        copy = ticket.copy()
        self.assertNotEqual(copy.number, ticket.number)
        self.assertNotEqual(copy.number, "/")

    # -- closing date --------------------------------------------------
    def test_closing_stage_stamps_date(self):
        ticket = self.Ticket.create({"name": "Broken", "stage_id": self.stage_new.id})
        self.assertFalse(ticket.date_closed)
        self.assertFalse(ticket.is_closed)
        ticket.stage_id = self.stage_solved
        self.assertTrue(ticket.date_closed, "a closing stage must stamp the closing date")
        self.assertTrue(ticket.is_closed)

    def test_reopening_clears_the_closing_date(self):
        ticket = self.Ticket.create({"name": "Broken", "stage_id": self.stage_solved.id})
        self.assertTrue(ticket.date_closed)
        ticket.stage_id = self.stage_progress
        self.assertFalse(ticket.date_closed, "a reopened ticket keeps no stale closing date")

    def test_action_close_picks_a_closing_stage(self):
        ticket = self.Ticket.create({"name": "Close me", "stage_id": self.stage_new.id})
        ticket.action_close()
        self.assertTrue(ticket.stage_id.is_closed)
        self.assertTrue(ticket.date_closed)

    # -- defaults ------------------------------------------------------
    def test_team_default_assignee_applies_on_create(self):
        ticket = self.Ticket.create({"name": "Unowned", "team_id": self.team_a.id})
        self.assertEqual(ticket.user_id, self.agent_a)

    def test_explicit_assignee_beats_the_team_default(self):
        ticket = self.Ticket.create({
            "name": "Owned", "team_id": self.team_a.id, "user_id": self.manager.id,
        })
        self.assertEqual(ticket.user_id, self.manager)

    def test_team_without_default_leaves_ticket_unassigned(self):
        ticket = self.Ticket.create({"name": "Nobody", "team_id": self.team_b.id})
        self.assertFalse(ticket.user_id)

    def test_first_stage_and_customer_email_are_filled(self):
        ticket = self.Ticket.create({"name": "Fresh", "partner_id": self.customer.id})
        self.assertEqual(ticket.stage_id, self.stage_new)
        self.assertEqual(ticket.partner_email, "support@acme.example")

    # -- security ------------------------------------------------------
    def test_user_cannot_read_another_teams_ticket(self):
        other = self.Ticket.create({"name": "Team B only", "team_id": self.team_b.id})
        with self.assertRaises(AccessError):
            other.with_user(self.agent_a).read(["name"])

    def test_user_reads_own_team_ticket(self):
        mine = self.Ticket.create({"name": "Team A", "team_id": self.team_a.id})
        self.assertEqual(mine.with_user(self.agent_a).name, "Team A")

    def test_user_reads_ticket_assigned_to_them(self):
        assigned = self.Ticket.create({
            "name": "Personal", "team_id": self.team_b.id, "user_id": self.agent_a.id,
        })
        self.assertEqual(assigned.with_user(self.agent_a).name, "Personal")

    def test_manager_reads_every_ticket(self):
        self.Ticket.create({"name": "A", "team_id": self.team_a.id})
        self.Ticket.create({"name": "B", "team_id": self.team_b.id})
        visible = self.Ticket.with_user(self.manager).search([])
        self.assertEqual(len(visible.filtered(lambda t: t.name in ("A", "B"))), 2)

    def test_user_cannot_maintain_stages(self):
        with self.assertRaises(AccessError):
            self.Stage.with_user(self.agent_a).create({"name": "Sneaky"})

    # -- search filters ------------------------------------------------
    def _filter_domain(self, name):
        view = self.env.ref("drkds_ticketing_lite.view_drkds_ticket_search")
        from lxml import etree
        node = etree.fromstring(view.arch).find(f".//filter[@name='{name}']")
        self.assertIsNotNone(node, f"filter {name} is missing from the search view")
        return node.get("domain")

    def test_search_filters_return_what_they_claim(self):
        """Each advertised filter's own domain selects the right tickets."""
        mine = self.Ticket.create({
            "name": "Mine", "user_id": self.agent_a.id, "team_id": self.team_a.id,
        })
        free = self.Ticket.create({"name": "Free", "team_id": self.team_b.id})
        urgent = self.Ticket.create({
            "name": "Urgent", "priority": "3", "user_id": self.manager.id,
        })
        closed = self.Ticket.create({"name": "Done", "stage_id": self.stage_solved.id})
        pool = mine + free + urgent + closed

        def matched(filter_name, user=None):
            domain = self._filter_domain(filter_name).replace("uid", str(
                (user or self.env.user).id
            ))
            records = self.Ticket.search(eval(domain) + [("id", "in", pool.ids)])
            return records

        self.assertEqual(matched("my_tickets", self.agent_a), mine)
        self.assertEqual(matched("unassigned"), free + closed)
        self.assertEqual(matched("my_teams", self.agent_a), mine)
        self.assertEqual(matched("urgent"), urgent)
        self.assertEqual(matched("closed"), closed)
        self.assertEqual(matched("open"), mine + free + urgent)

    # -- constraints ---------------------------------------------------
    def test_stage_of_another_team_is_refused(self):
        from odoo.exceptions import ValidationError
        stage_b = self.Stage.create({"name": "B only", "team_id": self.team_b.id})
        with self.assertRaises(ValidationError):
            self.Ticket.create({
                "name": "Wrong stage", "team_id": self.team_a.id, "stage_id": stage_b.id,
            })

    def test_team_ticket_counts(self):
        self.Ticket.create({"name": "Open one", "team_id": self.team_a.id})
        self.Ticket.create({
            "name": "Closed one", "team_id": self.team_a.id,
            "stage_id": self.stage_solved.id,
        })
        self.team_a.invalidate_recordset()
        self.assertEqual(self.team_a.ticket_count, 2)
        self.assertEqual(self.team_a.open_ticket_count, 1)

    def _flush_tracking(self):
        """Tracking messages are posted from the cursor pre-commit queue."""
        self.env.flush_all()
        self.cr.precommit.run()

    # -- chatter -------------------------------------------------------
    def test_stage_change_is_recorded_as_a_tracking_value(self):
        """The stage is a tracked field, so a move leaves a trace in the chatter."""
        ticket = self.Ticket.create({"name": "Tracked", "stage_id": self.stage_new.id})
        self._flush_tracking()
        ticket.stage_id = self.stage_progress
        self._flush_tracking()
        tracked = ticket.message_ids.tracking_value_ids.filtered(
            lambda value: value.field_id.name == "stage_id"
        )
        self.assertTrue(tracked, "the stage change must be tracked in the chatter")
        self.assertEqual(tracked[0].new_value_char, self.stage_progress.name)

    def test_ticket_is_a_mail_thread_with_activities(self):
        ticket = self.Ticket.create({"name": "Followed"})
        ticket.message_subscribe(partner_ids=self.customer.ids)
        self.assertIn(self.customer, ticket.message_partner_ids)
        ticket.message_post(body="Called the customer back.")
        self.assertTrue(ticket.message_ids)
        self.assertIn("activity_ids", ticket._fields)
