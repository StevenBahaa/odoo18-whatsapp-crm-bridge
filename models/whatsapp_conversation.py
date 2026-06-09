from odoo import api, fields, models, _


class WhatsAppConversation(models.Model):
    _name = "whatsapp.conversation"
    _description = "WhatsApp Conversation"
    _order = "last_message_at desc, create_date desc"

    name = fields.Char(
        string="Conversation",
        required=True,
        copy=False,
        default=lambda self: _("New WhatsApp Conversation"),
    )

    account_id = fields.Many2one(
        comodel_name="whatsapp.account",
        string="WhatsApp Account",
        required=True,
        index=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="account_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        index=True,
        ondelete="set null",
    )

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="CRM Lead",
        index=True,
        ondelete="set null",
    )

    assigned_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Salesperson",
        index=True,
        ondelete="set null",
    )

    phone = fields.Char(
        string="Phone",
        index=True,
        help="Original or display phone number for the WhatsApp customer.",
    )

    normalized_phone = fields.Char(
        string="Normalized Phone",
        required=True,
        index=True,
        help="Normalized phone used to match the customer conversation.",
    )

    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("pending", "Pending"),
            ("closed", "Closed"),
        ],
        string="Status",
        required=True,
        default="open",
        index=True,
        copy=False,
    )

    message_ids = fields.One2many(
        comodel_name="whatsapp.message",
        inverse_name="conversation_id",
        string="Messages",
        readonly=True,
    )

    message_count = fields.Integer(
        string="Messages",
        compute="_compute_message_stats",
        store=True,
    )

    inbound_message_count = fields.Integer(
        string="Inbound Messages",
        compute="_compute_message_stats",
        store=True,
    )

    outbound_message_count = fields.Integer(
        string="Outbound Messages",
        compute="_compute_message_stats",
        store=True,
    )

    last_message_at = fields.Datetime(
        string="Last Message At",
        compute="_compute_message_stats",
        store=True,
        index=True,
    )

    last_inbound_at = fields.Datetime(
        string="Last Inbound At",
        compute="_compute_message_stats",
        store=True,
        index=True,
    )

    last_outbound_at = fields.Datetime(
        string="Last Outbound At",
        compute="_compute_message_stats",
        store=True,
        index=True,
    )

    needs_reply = fields.Boolean(
        string="Needs Reply",
        compute="_compute_needs_reply",
        store=True,
        index=True,
        help="True when the latest inbound message is newer than the latest outbound reply.",
    )

    @api.depends(
        "message_ids",
        "message_ids.direction",
        "message_ids.create_date",
        "message_ids.received_at",
        "message_ids.sent_at",
        "message_ids.failed_at",
        "message_ids.delivered_at",
        "message_ids.read_at",
    )
    def _compute_message_stats(self):
        for conversation in self:
            messages = conversation.message_ids

            inbound_messages = messages.filtered(lambda m: m.direction == "inbound")
            outbound_messages = messages.filtered(lambda m: m.direction == "outbound")

            conversation.message_count = len(messages)
            conversation.inbound_message_count = len(inbound_messages)
            conversation.outbound_message_count = len(outbound_messages)

            all_dates = [
                date for date in (
                    messages.mapped("received_at")
                    + messages.mapped("sent_at")
                    + messages.mapped("failed_at")
                    + messages.mapped("delivered_at")
                    + messages.mapped("read_at")
                    + messages.mapped("create_date")
                )
                if date
            ]

            inbound_dates = [
                date for date in (
                    inbound_messages.mapped("received_at")
                    + inbound_messages.mapped("create_date")
                )
                if date
            ]

            outbound_dates = [
                date for date in (
                    outbound_messages.mapped("sent_at")
                    + outbound_messages.mapped("failed_at")
                    + outbound_messages.mapped("delivered_at")
                    + outbound_messages.mapped("read_at")
                    + outbound_messages.mapped("create_date")
                )
                if date
            ]

            conversation.last_message_at = max(all_dates) if all_dates else False
            conversation.last_inbound_at = max(inbound_dates) if inbound_dates else False
            conversation.last_outbound_at = max(outbound_dates) if outbound_dates else False

    @api.depends("last_inbound_at", "last_outbound_at", "state")
    def _compute_needs_reply(self):
        for conversation in self:
            if conversation.state == "closed" or not conversation.last_inbound_at:
                conversation.needs_reply = False
            elif not conversation.last_outbound_at:
                conversation.needs_reply = True
            else:
                conversation.needs_reply = conversation.last_inbound_at > conversation.last_outbound_at

    @api.model
    def _prepare_name(self, partner=False, normalized_phone=False):
        if partner:
            return _("WhatsApp Conversation - %s") % partner.name
        return _("WhatsApp Conversation - %s") % (normalized_phone or _("Unknown"))

    @api.model
    def find_or_create_open_conversation(
        self,
        account,
        normalized_phone,
        partner=False,
        lead=False,
        assigned_user=False,
        original_phone=False,
    ):
        if not account or not normalized_phone:
            return False

        conversation = self.sudo().search(
            [
                ("account_id", "=", account.id),
                ("normalized_phone", "=", normalized_phone),
                ("state", "in", ["open", "pending"]),
            ],
            order="last_message_at desc, create_date desc",
            limit=1,
        )

        vals = {}

        if conversation:
            if partner and not conversation.partner_id:
                vals["partner_id"] = partner.id
            if lead and not conversation.lead_id:
                vals["lead_id"] = lead.id
            if assigned_user and not conversation.assigned_user_id:
                vals["assigned_user_id"] = assigned_user.id
            if original_phone and not conversation.phone:
                vals["phone"] = original_phone

            if vals:
                conversation.write(vals)

            return conversation

        return self.sudo().create({
            "name": self._prepare_name(partner=partner, normalized_phone=normalized_phone),
            "account_id": account.id,
            "partner_id": partner.id if partner else False,
            "lead_id": lead.id if lead else False,
            "assigned_user_id": assigned_user.id if assigned_user else False,
            "phone": original_phone or normalized_phone,
            "normalized_phone": normalized_phone,
            "state": "open",
        })

    def action_mark_open(self):
        self.write({"state": "open"})

    def action_mark_pending(self):
        self.write({"state": "pending"})

    def action_mark_closed(self):
        self.write({"state": "closed"})