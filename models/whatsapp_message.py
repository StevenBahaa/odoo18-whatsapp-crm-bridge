# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime

from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)


class WhatsAppMessage(models.Model):
    _name = "whatsapp.message"
    _description = "WhatsApp Message"
    _order = "create_date desc"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account",
        string="WhatsApp Account",
        required=True,
        index=True,
        ondelete="cascade",
        help="WhatsApp account used to receive or send this message.",
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
        help="Customer linked to this WhatsApp message when available.",
    )

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="CRM Lead",
        index=True,
        ondelete="set null",
        help="CRM lead linked to this WhatsApp message when available.",
    )

    direction = fields.Selection(
        selection=[
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        string="Direction",
        required=True,
        index=True,
        default="inbound",
    )

    message_type = fields.Selection(
        selection=[
            ("text", "Text"),
            ("image", "Image"),
            ("document", "Document"),
            ("audio", "Audio"),
            ("unknown", "Unknown"),
        ],
        string="Message Type",
        required=True,
        default="unknown",
        index=True,
    )

    body = fields.Text(
        string="Message Body",
        help="Text body or a short unsupported-message description.",
    )

    external_message_id = fields.Char(
        string="External Message ID",
        index=True,
        copy=False,
        help="Meta WhatsApp message ID. Used to match status webhooks.",
    )

    external_sender_id = fields.Char(
        string="External Sender ID",
        index=True,
        copy=False,
        help="WhatsApp sender ID for inbound messages when available.",
    )

    recipient_phone = fields.Char(
        string="Recipient Phone",
        index=True,
        help="Normalized recipient phone for outbound messages or status updates.",
    )

    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("received", "Received"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
            ("failed", "Failed"),
        ],
        string="Status",
        required=True,
        default="draft",
        index=True,
        copy=False,
    )

    error_code = fields.Char(
        string="Error Code",
        copy=False,
    )

    error_message = fields.Text(
        string="Error Message",
        copy=False,
    )

    raw_payload = fields.Text(
        string="Raw Payload",
        help="Latest relevant Meta payload or response connected to this message.",
    )

    payload_preview = fields.Char(
        string="Payload Preview",
        compute="_compute_payload_preview",
        store=False,
    )

    sent_at = fields.Datetime(
        string="Sent At",
        copy=False,
    )

    received_at = fields.Datetime(
        string="Received At",
        copy=False,
    )

    delivered_at = fields.Datetime(
        string="Delivered At",
        copy=False,
    )

    read_at = fields.Datetime(
        string="Read At",
        copy=False,
    )

    failed_at = fields.Datetime(
        string="Failed At",
        copy=False,
    )

    assigned_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Salesperson",
        index=True,
        ondelete="set null",
        help="Salesperson responsible for this WhatsApp message, usually taken from the linked CRM lead.",
    )
    conversation_id = fields.Many2one(
        comodel_name="whatsapp.conversation",
        string="WhatsApp Conversation",
        index=True,
        ondelete="set null",
        help="Conversation that groups this WhatsApp message with related inbound/outbound messages.",
    )

    _sql_constraints = [
        (
            "external_message_account_unique",
            "unique(account_id, external_message_id)",
            "The external WhatsApp message ID must be unique per WhatsApp account.",
        ),
    ]

    @api.depends("raw_payload")
    def _compute_payload_preview(self):
        for message in self:
            if not message.raw_payload:
                message.payload_preview = False
                continue

            preview = message.raw_payload.replace("\n", " ").strip()
            message.payload_preview = preview[:160]

    @api.model
    def _json_dumps_payload(self, payload):
        """Return a formatted JSON string for traceability."""
        return json.dumps(payload or {}, ensure_ascii=False, indent=2, sort_keys=True)

    @api.model
    def _datetime_from_whatsapp_timestamp(self, timestamp):
        """
        Convert Meta WhatsApp unix timestamp into an Odoo UTC datetime.

        Meta sends timestamps as strings in many webhook examples.
        Odoo stores naive UTC datetimes, so utcfromtimestamp is appropriate here.
        """
        if not timestamp:
            return fields.Datetime.now()

        try:
            return datetime.utcfromtimestamp(int(timestamp))
        except Exception:
            _logger.warning("Invalid WhatsApp status timestamp received: %s", timestamp)
            return fields.Datetime.now()

    @api.model
    def _extract_status_payload(self, payload):
        """
        Extract the first status object from a Meta WhatsApp webhook payload.

        Expected path:
        entry[0].changes[0].value.statuses[0]
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            statuses = value.get("statuses") or []
            status = statuses[0] if statuses else {}

            errors = status.get("errors") or []
            first_error = errors[0] if errors else {}

            return {
                "external_message_id": status.get("id"),
                "status": status.get("status"),
                "timestamp": status.get("timestamp"),
                "recipient_id": status.get("recipient_id"),
                "error_code": first_error.get("code"),
                "error_message": (
                    first_error.get("message")
                    or first_error.get("title")
                    or first_error.get("details")
                ),
            }
        except Exception:
            _logger.exception("Failed to extract WhatsApp status payload.")
            return {
                "external_message_id": False,
                "status": False,
                "timestamp": False,
                "recipient_id": False,
                "error_code": False,
                "error_message": False,
            }

    @api.model
    def _apply_status_webhook(self, account, payload):
        """
        Apply a WhatsApp status webhook to an existing whatsapp.message record.

        Matching rule:
        - Same WhatsApp account.
        - Same Meta external message ID.

        If no matching message exists, the webhook event remains logged but ignored.
        This is not an HTTP failure because Meta should not keep retrying a payload
        that Odoo safely received and classified.
        """
        status_data = self._extract_status_payload(payload)
        external_message_id = status_data.get("external_message_id")

        if not external_message_id:
            return {
                "success": False,
                "reason": "missing_external_message_id",
                "external_message_id": False,
                "message": False,
            }

        message = self.search(
            [
                ("account_id", "=", account.id),
                ("external_message_id", "=", external_message_id),
            ],
            limit=1,
        )

        if not message:
            return {
                "success": False,
                "reason": "message_not_found",
                "external_message_id": external_message_id,
                "message": False,
            }

        incoming_status = status_data.get("status") or ""
        status_time = self._datetime_from_whatsapp_timestamp(status_data.get("timestamp"))

        vals = {
            "raw_payload": self._json_dumps_payload(payload),
        }

        if status_data.get("recipient_id"):
            vals["recipient_phone"] = status_data["recipient_id"]

        if incoming_status == "sent":
            vals.update({
                "status": "sent",
                "sent_at": message.sent_at or status_time,
                "error_code": False,
                "error_message": False,
            })
        elif incoming_status == "delivered":
            vals.update({
                "status": "delivered",
                "delivered_at": status_time,
                "error_code": False,
                "error_message": False,
            })
        elif incoming_status == "read":
            vals.update({
                "status": "read",
                "read_at": status_time,
                "error_code": False,
                "error_message": False,
            })
        elif incoming_status == "failed":
            vals.update({
                "status": "failed",
                "failed_at": status_time,
                "error_code": status_data.get("error_code"),
                "error_message": status_data.get("error_message") or _("WhatsApp message failed."),
            })
        else:
            return {
                "success": False,
                "reason": "unsupported_status_%s" % (incoming_status or "unknown"),
                "external_message_id": external_message_id,
                "message": message,
            }

        message.write(vals)

        return {
            "success": True,
            "reason": "updated",
            "external_message_id": external_message_id,
            "message": message,
        }

    @api.model
    def create_outbound_from_send_result(self, account, lead, partner, recipient_phone, body, send_result):
        """
        Create a durable outbound whatsapp.message from the UC-06 send attempt.

        We create a record for both success and failure because failed attempts are
        also operationally important and must be auditable from Odoo.
        """
        response_json = send_result.get("response_json") or {}
        response_text = send_result.get("response_text") or ""
        messages = response_json.get("messages") or []
        external_message_id = messages[0].get("id") if messages else False

        error_data = response_json.get("error") or {}
        error_code = error_data.get("code")
        error_message = send_result.get("error_message") or error_data.get("message")

        raw_payload = response_json if response_json else {
            "response_text": response_text,
            "status_code": send_result.get("status_code"),
            "success": bool(send_result.get("success")),
        }

        now = fields.Datetime.now()
        success = bool(send_result.get("success"))

        Conversation = self.env["whatsapp.conversation"].sudo()

        conversation = Conversation.find_or_create_open_conversation(
            account=account,
            normalized_phone=recipient_phone,
            partner=partner,
            lead=lead,
            assigned_user=lead.user_id if lead and lead.user_id else False,
            original_phone=recipient_phone,
        )

        vals = {
            "account_id": account.id,
            "partner_id": partner.id if partner else False,
            "lead_id": lead.id if lead else False,
            "conversation_id": conversation.id if conversation else False,
            "assigned_user_id": lead.user_id.id if lead and lead.user_id else False,
            "direction": "outbound",
            "message_type": "text",
            "body": body,
            "external_message_id": external_message_id,
            "recipient_phone": recipient_phone,
            "status": "sent" if success else "failed",
            "sent_at": now if success else False,
            "failed_at": now if not success else False,
            "error_code": error_code if not success else False,
            "error_message": error_message if not success else False,
            "raw_payload": self._json_dumps_payload(raw_payload),
        }

        return self.sudo().create(vals)

    @api.model
    def create_inbound_from_payload(self, account, partner, lead, payload):
        """
        Create or return an inbound whatsapp.message from a message webhook.

        Meta may retry webhooks. Therefore, if the external message ID already
        exists for the same account, we return the existing message instead of
        creating duplicate CRM history.
        """
        WebhookEvent = self.env["whatsapp.webhook.event"].sudo()

        external_message_id = WebhookEvent._extract_external_event_id(payload)
        sender_phone = WebhookEvent._extract_sender_phone(payload)
        normalized_sender = WebhookEvent._normalize_phone(sender_phone)
        message_type = WebhookEvent._extract_message_type(payload)
        message_body = WebhookEvent._extract_message_body(payload)

        conversation = False
        if normalized_sender:
            Conversation = self.env["whatsapp.conversation"].sudo()
            conversation = Conversation.find_or_create_open_conversation(
                account=account,
                normalized_phone=normalized_sender,
                partner=partner,
                lead=lead,
                assigned_user=lead.user_id if lead and lead.user_id else False,
                original_phone=sender_phone,
            )

        if external_message_id:
            existing_message = self.sudo().search(
                [
                    ("account_id", "=", account.id),
                    ("external_message_id", "=", external_message_id),
                ],
                limit=1,
            )
            if existing_message:
                vals = {}

                if conversation and not existing_message.conversation_id:
                    vals["conversation_id"] = conversation.id

                if lead and not existing_message.lead_id:
                    vals["lead_id"] = lead.id

                if partner and not existing_message.partner_id:
                    vals["partner_id"] = partner.id

                if lead and lead.user_id and not existing_message.assigned_user_id:
                    vals["assigned_user_id"] = lead.user_id.id

                if vals:
                    existing_message.write(vals)

                return existing_message

        return self.sudo().create({
            "account_id": account.id,
            "partner_id": partner.id if partner else False,
            "lead_id": lead.id if lead else False,
            "conversation_id": conversation.id if conversation else False,
            "assigned_user_id": lead.user_id.id if lead and lead.user_id else False,
            "direction": "inbound",
            "message_type": message_type if message_type in dict(self._fields["message_type"].selection) else "unknown",
            "body": message_body,
            "external_message_id": external_message_id,
            "external_sender_id": normalized_sender or sender_phone,
            "status": "received",
            "received_at": fields.Datetime.now(),
            "raw_payload": self._json_dumps_payload(payload),
        })