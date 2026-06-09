# -*- coding: utf-8 -*-

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WhatsAppSendMessageWizard(models.TransientModel):
    _name = "whatsapp.send.message.wizard"
    _description = "Send WhatsApp Message Wizard"

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="CRM Lead",
        required=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )

    conversation_id = fields.Many2one(
        comodel_name="whatsapp.conversation",
        string="WhatsApp Conversation",
        readonly=True,
    )

    account_id = fields.Many2one(
        comodel_name="whatsapp.account",
        string="WhatsApp Account",
        required=True,
    )

    phone = fields.Char(
        string="Recipient Phone",
        required=True,
    )

    message_body = fields.Text(
        string="Message",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model == "whatsapp.conversation" and active_id:
            conversation = self.env["whatsapp.conversation"].browse(active_id).exists()
            if not conversation:
                return res

            lead = conversation.lead_id
            partner = conversation.partner_id or lead.partner_id
            phone = conversation.normalized_phone or conversation.phone

            res.update({
                "conversation_id": conversation.id,
                "lead_id": lead.id if lead else False,
                "partner_id": partner.id if partner else False,
                "phone": self.env["whatsapp.webhook.event"]._normalize_phone(phone) if phone else False,
                "account_id": conversation.account_id.id if conversation.account_id else False,
            })

            return res

        if active_model != "crm.lead" or not active_id:
            return res

        lead = self.env["crm.lead"].browse(active_id).exists()
        if not lead:
            return res

        partner = lead.partner_id

        phone = (
            lead.mobile
            or lead.phone
            or partner.mobile
            or partner.phone
        )

        account = self.env["whatsapp.account"].search(
            [
                ("active", "=", True),
                ("company_id", "=", lead.company_id.id or self.env.company.id),
            ],
            limit=1,
        )

        if not account:
            account = self.env["whatsapp.account"].search(
                [("active", "=", True)],
                limit=1,
            )

        res.update({
            "lead_id": lead.id,
            "partner_id": partner.id if partner else False,
            "phone": self.env["whatsapp.webhook.event"]._normalize_phone(phone) if phone else False,
            "account_id": account.id if account else False,
        })

        return res

    def action_send_message(self):
        self.ensure_one()

        if not self.account_id:
            raise UserError(_("Please select a WhatsApp account."))

        if not self.phone:
            raise UserError(_("Please enter a recipient phone number."))

        if not self.message_body:
            raise UserError(_("Please enter a message."))

        normalized_phone = self.env["whatsapp.webhook.event"]._normalize_phone(self.phone)

        if not normalized_phone:
            raise UserError(_("Invalid recipient phone number."))

        send_result = self.account_id._send_text_message(
            normalized_phone,
            self.message_body,
        )

        # UC-07: every outbound send attempt must have a durable message record.
        # This includes failures, because failures are operationally important and
        # must not disappear after the wizard closes.
        whatsapp_message = self.env["whatsapp.message"].sudo().create_outbound_from_send_result(
            account=self.account_id,
            lead=self.lead_id,
            partner=self.partner_id,
            recipient_phone=normalized_phone,
            body=self.message_body,
            send_result=send_result,
            conversation=self.conversation_id,
        )

        response_json = send_result.get("response_json") or {}
        external_message_id = False

        messages = response_json.get("messages") or []
        if messages:
            external_message_id = messages[0].get("id")

        if not send_result.get("success"):
            safe_phone = escape(normalized_phone)
            safe_message = escape(self.message_body)
            safe_error = escape(send_result.get("error_message") or "Unknown error")

            chatter_body = Markup("""
                <div>
                    <p><strong>Failed Outbound WhatsApp Message</strong></p>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>To</strong></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><strong>Error</strong></td>
                            <td>%s</td>
                        </tr>
                    </table>
                    <blockquote>%s</blockquote>
                </div>
            """) % (
                safe_phone,
                safe_error,
                safe_message,
            )

            self.lead_id.message_post(
                body=chatter_body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Message Failed"),
                    "message": send_result.get("error_message") or _("Meta WhatsApp API error."),
                    "type": "danger",
                    "sticky": True,
                },
            }

        safe_phone = escape(normalized_phone)
        safe_message = escape(self.message_body)
        safe_external_id = escape(external_message_id or "N/A")

        chatter_body = Markup("""
            <div>
                <p><strong>Outbound WhatsApp Message</strong></p>
                <table class="table table-sm">
                    <tr>
                        <td><strong>To</strong></td>
                        <td>%s</td>
                    </tr>
                    <tr>
                        <td><strong>Meta Message ID</strong></td>
                        <td>%s</td>
                    </tr>
                </table>
                <blockquote>%s</blockquote>
            </div>
        """) % (
            safe_phone,
            safe_external_id,
            safe_message,
        )

        self.lead_id.message_post(
            body=chatter_body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Message"),
                "message": _("Message sent successfully."),
                "type": "success",
                "sticky": False,
            },
        }