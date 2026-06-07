# -*- coding: utf-8 -*-

import json
import logging

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