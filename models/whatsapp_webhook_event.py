# -*- coding: utf-8 -*-

import json
import logging

from markupsafe import Markup, escape

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class WhatsAppWebhookEvent(models.Model):
    _name = "whatsapp.webhook.event"
    _description = "WhatsApp Webhook Event"
    _order = "create_date desc"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account",
        string="WhatsApp Account",
        index=True,
        ondelete="set null",
        help="The configured WhatsApp account matched from the webhook payload.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="account_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    event_type = fields.Selection(
        selection=[
            ("message", "Message"),
            ("status", "Status"),
            ("unknown", "Unknown"),
        ],
        string="Event Type",
        required=True,
        default="unknown",
        index=True,
        help="High-level type detected from the WhatsApp webhook payload.",
    )

    external_event_id = fields.Char(
        string="External Event ID",
        index=True,
        help="External message/status ID when available. Used later for duplicate protection and tracing.",
    )

    raw_payload = fields.Text(
        string="Raw Payload",
        required=True,
        help="Raw JSON payload received from Meta WhatsApp webhook.",
    )

    processing_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("processed", "Processed"),
            ("failed", "Failed"),
            ("ignored", "Ignored"),
        ],
        string="Processing Status",
        required=True,
        default="pending",
        index=True,
        copy=False,
    )

    error_message = fields.Text(
        string="Error Message",
        readonly=True,
        copy=False,
    )

    processed_at = fields.Datetime(
        string="Processed At",
        readonly=True,
        copy=False,
    )

    payload_preview = fields.Char(
        string="Payload Preview",
        compute="_compute_payload_preview",
        store=False,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Matched Partner",
        index=True,
        ondelete="set null",
        help="Customer partner matched or created from the WhatsApp sender phone.",
    )

    sender_phone = fields.Char(
        string="Sender Phone",
        index=True,
        help="Original WhatsApp sender phone extracted from the webhook payload.",
    )

    normalized_sender_phone = fields.Char(
        string="Normalized Sender Phone",
        index=True,
        help="Normalized sender phone used for partner matching.",
    )

    sender_name = fields.Char(
        string="Sender Name",
        help="Customer profile name extracted from WhatsApp contacts payload when available.",
    )

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="CRM Lead",
        index=True,
        ondelete="set null",
        help="CRM lead matched or created from this WhatsApp webhook event.",
    )

    message_body = fields.Text(
        string="Message Body",
        help="Inbound WhatsApp text message body extracted from the webhook payload.",
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
        default="unknown",
        index=True,
    )
    assigned_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Salesperson",
        index=True,
        ondelete="set null",
        help="Salesperson responsible for the CRM lead linked to this webhook event.",
    )

    @api.depends("raw_payload")
    def _compute_payload_preview(self):
        for event in self:
            if not event.raw_payload:
                event.payload_preview = False
                continue

            preview = event.raw_payload.replace("\n", " ").strip()
            event.payload_preview = preview[:160]

    @api.model
    def _json_dumps_payload(self, payload):
        """
        Convert incoming Python dict/list payload into formatted JSON text.

        We keep this helper centralized so controllers do not duplicate
        JSON formatting logic.
        """
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    @api.model
    def _detect_event_type(self, payload):
        """
        Detect a high-level webhook event type.

        UC-03 only classifies the payload for logging.
        Real message/status processing will be implemented later.
        """
        try:
            changes = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])
            )

            if not changes:
                return "unknown"

            value = changes[0].get("value", {})

            if value.get("messages"):
                return "message"

            if value.get("statuses"):
                return "status"

            return "unknown"

        except Exception:
            _logger.exception("Failed to detect WhatsApp webhook event type.")
            return "unknown"

    @api.model
    def _extract_phone_number_id(self, payload):
        """
        Extract phone_number_id from Meta WhatsApp webhook payload.

        Meta usually sends it under:
        entry[0].changes[0].value.metadata.phone_number_id
        """
        try:
            return (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
                .get("metadata", {})
                .get("phone_number_id")
            )
        except Exception:
            _logger.exception("Failed to extract phone_number_id from WhatsApp webhook payload.")
            return False

    @api.model
    def _extract_external_event_id(self, payload):
        """
        Extract a useful external ID when available.

        For inbound messages:
        value.messages[0].id

        For status updates:
        value.statuses[0].id
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )

            messages = value.get("messages") or []
            if messages:
                return messages[0].get("id")

            statuses = value.get("statuses") or []
            if statuses:
                return statuses[0].get("id")

            return False

        except Exception:
            _logger.exception("Failed to extract external event ID from WhatsApp webhook payload.")
            return False
    
    @api.model
    def _normalize_phone(self, phone, country_code="20"):
        """
        Normalize phone numbers for Egypt-focused MVP.

        Examples:
        - 01012345678     -> 201012345678
        - +201012345678   -> 201012345678
        - 00201012345678  -> 201012345678
        - 201012345678    -> 201012345678

        MVP limitation:
        This is Egypt-focused. Later it can become configurable per account/company.
        """
        if not phone:
            return False

        digits = "".join(ch for ch in str(phone).strip() if ch.isdigit())

        if not digits:
            return False

        if digits.startswith("00"):
            digits = digits[2:]

        if digits.startswith("0"):
            digits = country_code + digits[1:]

        return digits


    @api.model
    def _extract_sender_phone(self, payload):
        """
        Extract sender phone from inbound WhatsApp message payload.

        Expected Meta path:
        entry[0].changes[0].value.messages[0].from
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            messages = value.get("messages") or []
            if messages:
                return messages[0].get("from")
            return False
        except Exception:
            _logger.exception("Failed to extract sender phone from WhatsApp webhook payload.")
            return False


    @api.model
    def _extract_sender_name(self, payload):
        """
        Extract WhatsApp profile name when available.

        Expected Meta path:
        entry[0].changes[0].value.contacts[0].profile.name
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            contacts = value.get("contacts") or []
            if contacts:
                return (
                    contacts[0]
                    .get("profile", {})
                    .get("name")
                )
            return False
        except Exception:
            _logger.exception("Failed to extract sender name from WhatsApp webhook payload.")
            return False

    @api.model
    def _find_or_create_partner_from_payload(self, account, payload):
        """
        Find or create res.partner using WhatsApp sender phone.

        UC-04 only handles partner matching/creation.
        CRM lead creation is intentionally left for UC-05.
        """
        sender_phone = self._extract_sender_phone(payload)
        normalized_phone = self._normalize_phone(sender_phone)
        sender_name = self._extract_sender_name(payload)

        if not normalized_phone:
            return {
                "partner": False,
                "sender_phone": sender_phone,
                "normalized_phone": False,
                "sender_name": sender_name,
            }

        Partner = self.env["res.partner"].sudo()

        partner = Partner.search(
            [
                "|",
                ("phone", "=", normalized_phone),
                ("mobile", "=", normalized_phone),
            ],
            limit=1,
        )

        if not partner:
            # Extra fallback: check common display formats lightly.
            partner = Partner.search(
                [
                    "|",
                    ("phone", "ilike", normalized_phone[-10:]),
                    ("mobile", "ilike", normalized_phone[-10:]),
                ],
                limit=1,
            )

        if not partner:
            partner_name = sender_name or "WhatsApp Customer %s" % normalized_phone

            partner_vals = {
                "name": partner_name,
                "mobile": normalized_phone,
                "phone": normalized_phone,
                "company_id": account.company_id.id if account and account.company_id else False,
            }

            partner = Partner.create(partner_vals)

        return {
            "partner": partner,
            "sender_phone": sender_phone,
            "normalized_phone": normalized_phone,
            "sender_name": sender_name,
        }

    @api.model
    def _extract_message_type(self, payload):
        """
        Extract inbound WhatsApp message type.

        Expected Meta path:
        entry[0].changes[0].value.messages[0].type
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            messages = value.get("messages") or []
            if messages:
                return messages[0].get("type") or "unknown"
            return "unknown"
        except Exception:
            _logger.exception("Failed to extract WhatsApp message type.")
            return "unknown"


    @api.model
    def _extract_message_body(self, payload):
        """
        Extract inbound WhatsApp text body.

        MVP limitation:
        UC-05 supports text messages only for CRM chatter posting.
        Non-text messages are logged as unsupported/unknown.
        """
        try:
            value = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            messages = value.get("messages") or []
            if not messages:
                return False

            message = messages[0]
            message_type = message.get("type")

            if message_type == "text":
                return (
                    message.get("text", {})
                    .get("body")
                )

            return "[Unsupported WhatsApp message type: %s]" % (message_type or "unknown")

        except Exception:
            _logger.exception("Failed to extract WhatsApp message body.")
            return False
    
    @api.model
    def _find_or_create_crm_lead_from_payload(self, account, partner, payload):
        """
        Find or create an open CRM lead for the WhatsApp inbound message.

        UC-05 rule:
        - Do not create a new lead for every WhatsApp message.
        - Reuse an existing open lead for the same partner and WhatsApp source.
        - If no open lead exists, create a new lead.
        """
        if not partner:
            return False

        message_body = self._extract_message_body(payload)
        sender_phone = self._extract_sender_phone(payload)
        normalized_phone = self._normalize_phone(sender_phone)

        Source = self.env["utm.source"].sudo()
        Lead = self.env["crm.lead"].sudo()

        whatsapp_source = self.env.ref(
            "whatsapp_crm_bridge.crm_source_whatsapp",
            raise_if_not_found=False,
        )

        domain = [
            ("partner_id", "=", partner.id),
            ("type", "=", "lead"),
            ("active", "=", True),
            ("probability", "<", 100),
        ]

        if whatsapp_source:
            domain.append(("source_id", "=", whatsapp_source.id))

        existing_lead = Lead.search(
            domain,
            order="create_date desc",
            limit=1,
        )

        if existing_lead:
            return existing_lead

        lead_name = "WhatsApp Inquiry - %s" % (
            partner.name or normalized_phone or sender_phone or "Unknown Customer"
        )

        lead_vals = {
            "name": lead_name,
            "type": "lead",
            "partner_id": partner.id,
            "contact_name": partner.name,
            "phone": normalized_phone or sender_phone,
            "mobile": normalized_phone or sender_phone,
            "description": message_body or "",
            "company_id": account.company_id.id if account and account.company_id else False,
        }

        if whatsapp_source:
            lead_vals["source_id"] = whatsapp_source.id

        return Lead.create(lead_vals)

    @api.model
    def _post_whatsapp_message_to_lead_chatter(self, lead, partner, payload):
        """
        Post inbound WhatsApp message into CRM lead chatter.

        This gives the salesperson and manager a visible history
        inside Odoo CRM without building a live chat UI in MVP.
        """
        if not lead:
            return False

        message_body = self._extract_message_body(payload)
        message_type = self._extract_message_type(payload)
        sender_phone = self._extract_sender_phone(payload)
        sender_name = self._extract_sender_name(payload)

        if not message_body:
            message_body = "[Empty WhatsApp message]"

        safe_sender_name = escape(sender_name or (partner.name if partner else "Unknown"))
        safe_sender_phone = escape(sender_phone or "")
        safe_message_type = escape(message_type or "unknown")
        safe_message_body = escape(message_body)

        chatter_body = Markup("""
            <div>
                <p><strong>Inbound WhatsApp Message</strong></p>
                <table class="table table-sm">
                    <tr>
                        <td><strong>From</strong></td>
                        <td>%s</td>
                    </tr>
                    <tr>
                        <td><strong>Phone</strong></td>
                        <td>%s</td>
                    </tr>
                    <tr>
                        <td><strong>Type</strong></td>
                        <td>%s</td>
                    </tr>
                </table>
                <blockquote>%s</blockquote>
            </div>
        """) % (
            safe_sender_name,
            safe_sender_phone,
            safe_message_type,
            safe_message_body,
        )

        return lead.message_post(
            body=chatter_body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )