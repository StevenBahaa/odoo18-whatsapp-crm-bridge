# -*- coding: utf-8 -*-

import json
import logging

from odoo import api, fields, http, registry, SUPERUSER_ID
from odoo.http import request
from odoo.service import db as db_service

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):
    """
    Public webhook controller for Meta WhatsApp Cloud API.

    UC-02:
    - GET webhook verification.

    UC-03:
    - POST webhook payload logging.
    """

    @http.route(
        "/whatsapp/webhook",
        type="http",
        auth="none",
        methods=["GET", "POST"],
        csrf=False,
    )
    def whatsapp_webhook(self, **kwargs):
        _logger.warning(
            "WHATSAPP WEBHOOK HIT method=%s args=%s params=%s",
            request.httprequest.method,
            kwargs,
            dict(request.params),
        )
        try:
            db_name = self._get_db_name(**kwargs)
            if not db_name:
                return request.make_response(
                    "Database not found",
                    status=404,
                )

            reg = registry(db_name)
            with reg.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                if request.httprequest.method == "GET":
                    return self._verify_webhook(env, **kwargs)

                if request.httprequest.method == "POST":
                    response = self._receive_webhook(env, **kwargs)
                    # Commit the cursor only after successful POST handling where records are written.
                    if response.status_code == 200:
                        try:
                            resp_data = json.loads(response.data.decode("utf-8"))
                            if (
                                resp_data.get("status") in ("received", "ignored")
                                and resp_data.get("reason") != "empty_payload"
                            ):
                                cr.commit()
                        except Exception:
                            pass
                    return response

                return request.make_response(
                    "Method Not Allowed",
                    status=405,
                )
        except Exception as e:
            _logger.exception("Error processing WhatsApp webhook:")
            # Do not expose internal tracebacks or sensitive information in HTTP responses.
            return request.make_response(
                "Internal Server Error",
                status=500,
            )

    def _get_db_name(self, **kwargs):
        """
        Resolve database for external webhook requests.

        Browser requests may have a session database, but external callers
        like Meta or PowerShell do not. Therefore local testing can pass:

        ?db=whatsapp_crm_bridge
        """
        db_name = kwargs.get("db") or request.params.get("db")
        if not db_name and request.session and getattr(request.session, "db", None):
            db_name = request.session.db

        if not db_name:
            return False

        try:
            dbs = db_service.list_dbs()
        except Exception:
            dbs = []

        if db_name not in dbs:
            return False

        return db_name

    def _verify_webhook(self, env, **kwargs):
        """
        Verify Meta WhatsApp webhook URL.

        Meta sends:
        - hub.mode
        - hub.verify_token
        - hub.challenge
        """
        mode = kwargs.get("hub.mode")
        verify_token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        if mode != "subscribe" or not verify_token or not challenge:
            _logger.warning("Invalid WhatsApp webhook verification request.")
            return request.make_response(
                "Invalid verification request",
                status=400,
            )

        account = env["whatsapp.account"].sudo().search(
            [
                ("active", "=", True),
                ("webhook_verify_token", "=", verify_token),
            ],
            limit=1,
        )

        if not account:
            _logger.warning("Failed WhatsApp webhook verification: invalid verify token.")
            return request.make_response(
                "Forbidden",
                status=403,
            )

        _logger.info(
            "WhatsApp webhook verified successfully for account ID %s.",
            account.id,
        )

        return request.make_response(
            challenge,
            status=200,
            headers=[("Content-Type", "text/plain")],
        )

    def _receive_webhook(self, env, **kwargs):
        """
        Receive Meta WhatsApp webhook POST payload and store it.

        UC-03 only logs the event. Message parsing, partner matching,
        and CRM lead creation will be implemented in later UCs.
        """
        WebhookEvent = env["whatsapp.webhook.event"].sudo()
        Account = env["whatsapp.account"].sudo()

        try:
            raw_body = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            _logger.exception("Invalid JSON received from WhatsApp webhook.")
            response_body = json.dumps({
                "status": "failed",
                "reason": "invalid_json",
            })
            return request.make_response(
                response_body,
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        if not payload:
            _logger.warning("Received empty WhatsApp webhook payload.")
            response_body = json.dumps({
                "status": "ignored",
                "reason": "empty_payload",
            })
            return request.make_response(
                response_body,
                status=200,
                headers=[("Content-Type", "application/json")],
            )

        raw_payload = WebhookEvent._json_dumps_payload(payload)
        phone_number_id = WebhookEvent._extract_phone_number_id(payload)
        event_type = WebhookEvent._detect_event_type(payload)
        external_event_id = WebhookEvent._extract_external_event_id(payload)

        account = False
        if phone_number_id:
            account = Account.search(
                [
                    ("active", "=", True),
                    ("phone_number_id", "=", phone_number_id),
                ],
                limit=1,
            )

        if not account:
            WebhookEvent.create({
                "account_id": False,
                "event_type": event_type,
                "external_event_id": external_event_id,
                "raw_payload": raw_payload,
                "processing_status": "ignored",
                "error_message": (
                    "No active WhatsApp account matched phone_number_id: %s"
                    % (phone_number_id or "N/A")
                ),
                "processed_at": fields.Datetime.now(),
            })

            _logger.warning(
                "Ignored WhatsApp webhook payload. No account matched phone_number_id=%s.",
                phone_number_id,
            )

            response_body = json.dumps({
                "status": "ignored",
                "reason": "account_not_found",
            })
            return request.make_response(
                response_body,
                status=200,
                headers=[("Content-Type", "application/json")],
            )

        partner_data = WebhookEvent._find_or_create_partner_from_payload(account, payload)
        partner = partner_data["partner"]

        lead = False
        if event_type == "message" and partner:
            lead = WebhookEvent._find_or_create_crm_lead_from_payload(
                account,
                partner,
                payload,
            )

        message_type = WebhookEvent._extract_message_type(payload)
        message_body = WebhookEvent._extract_message_body(payload)

        event = WebhookEvent.create({
            "account_id": account.id,
            "partner_id": partner.id if partner else False,
            "lead_id": lead.id if lead else False,
            "sender_phone": partner_data["sender_phone"],
            "normalized_sender_phone": partner_data["normalized_phone"],
            "sender_name": partner_data["sender_name"],
            "message_type": message_type,
            "message_body": message_body,
            "event_type": event_type,
            "external_event_id": external_event_id,
            "raw_payload": raw_payload,
            "processing_status": "pending",
        })

        if lead:
            WebhookEvent._post_whatsapp_message_to_lead_chatter(
                lead,
                partner,
                payload,
            )

        account.write({
            "last_webhook_received_at": fields.Datetime.now(),
        })

        _logger.info(
            "Stored WhatsApp webhook event. account_id=%s event_id=%s event_type=%s external_event_id=%s partner_id=%s lead_id=%s",
            account.id,
            event.id,
            event_type,
            external_event_id,
            event.partner_id.id if event.partner_id else None,
            event.lead_id.id if event.lead_id else None,
        )

        response_body = json.dumps({
            "status": "received",
        })
        return request.make_response(
            response_body,
            status=200,
            headers=[("Content-Type", "application/json")],
        )