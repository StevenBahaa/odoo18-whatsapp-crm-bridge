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

    UC-07:
    - Status webhook processing for sent/delivered/read/failed updates.
    """

    @http.route(
        "/whatsapp/webhook",
        type="http",
        auth="none",
        methods=["GET", "POST"],
        csrf=False,
    )
    def whatsapp_webhook(self, **kwargs):
        _logger.info(
            "WhatsApp webhook hit. method=%s",
            request.httprequest.method,
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
                    # External webhook requests do not use the normal browser
                    # transaction flow. Commit only after a controlled 200 response
                    # where records were safely written.
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
        except Exception:
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

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data),
            status=status,
            headers=[("Content-Type", "application/json")],
        )

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
        Receive Meta WhatsApp webhook POST payload.

        This method keeps raw webhook logging as the audit layer, then delegates
        business processing based on the detected event type:
        - message: partner/lead/chatter flow + inbound whatsapp.message record.
        - status: update existing whatsapp.message by external_message_id.
        - unknown: log safely as ignored.
        """
        WebhookEvent = env["whatsapp.webhook.event"].sudo()
        Account = env["whatsapp.account"].sudo()
        WhatsAppMessage = env["whatsapp.message"].sudo()

        try:
            raw_body = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            _logger.exception("Invalid JSON received from WhatsApp webhook.")
            return self._json_response({
                "status": "failed",
                "reason": "invalid_json",
            }, status=400)

        if not payload:
            _logger.warning("Received empty WhatsApp webhook payload.")
            return self._json_response({
                "status": "ignored",
                "reason": "empty_payload",
            })

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

            return self._json_response({
                "status": "ignored",
                "reason": "account_not_found",
            })

        if event_type == "status":
            return self._process_status_webhook(
                WebhookEvent,
                WhatsAppMessage,
                account,
                payload,
                raw_payload,
                external_event_id,
            )

        if event_type == "message":
            return self._process_message_webhook(
                WebhookEvent,
                WhatsAppMessage,
                account,
                payload,
                raw_payload,
                external_event_id,
            )

        event = WebhookEvent.create({
            "account_id": account.id,
            "event_type": event_type,
            "external_event_id": external_event_id,
            "raw_payload": raw_payload,
            "processing_status": "ignored",
            "error_message": "Unsupported or unknown WhatsApp webhook event type.",
            "processed_at": fields.Datetime.now(),
        })

        account.write({
            "last_webhook_received_at": fields.Datetime.now(),
        })

        _logger.info(
            "Ignored unknown WhatsApp webhook event. account_id=%s event_id=%s external_event_id=%s",
            account.id,
            event.id,
            external_event_id,
        )

        return self._json_response({
            "status": "ignored",
            "reason": "unknown_event_type",
        })

    def _process_status_webhook(self, WebhookEvent, WhatsAppMessage, account, payload, raw_payload, external_event_id):
        """
        Process Meta message status webhook.

        Status webhooks do not represent a new customer message. Therefore we do
        not create partners/leads here. We only update an existing whatsapp.message.
        """
        event = WebhookEvent.create({
            "account_id": account.id,
            "event_type": "status",
            "external_event_id": external_event_id,
            "raw_payload": raw_payload,
            "processing_status": "pending",
        })

        result = WhatsAppMessage._apply_status_webhook(account, payload)
        matched_message = result.get("message")

        if result.get("success"):
            event.write({
                "partner_id": matched_message.partner_id.id if matched_message and matched_message.partner_id else False,
                "lead_id": matched_message.lead_id.id if matched_message and matched_message.lead_id else False,
                "assigned_user_id": matched_message.assigned_user_id.id if matched_message and matched_message.assigned_user_id else False,
                "processing_status": "processed",
                "error_message": False,
                "processed_at": fields.Datetime.now(),
            })

            _logger.info(
                "Processed WhatsApp status webhook. account_id=%s event_id=%s external_message_id=%s message_id=%s",
                account.id,
                event.id,
                result.get("external_message_id"),
                matched_message.id if matched_message else None,
            )
        else:
            reason = result.get("reason") or "unknown_status_processing_error"
            external_message_id = result.get("external_message_id") or external_event_id or "N/A"
            event.write({
                "partner_id": matched_message.partner_id.id if matched_message and matched_message.partner_id else False,
                "lead_id": matched_message.lead_id.id if matched_message and matched_message.lead_id else False,
                "processing_status": "ignored",
                "error_message": "Status webhook ignored: %s. External message ID: %s" % (
                    reason,
                    external_message_id,
                ),
                "processed_at": fields.Datetime.now(),
            })

            _logger.warning(
                "Ignored WhatsApp status webhook. account_id=%s event_id=%s reason=%s external_message_id=%s",
                account.id,
                event.id,
                reason,
                external_message_id,
            )

        account.write({
            "last_webhook_received_at": fields.Datetime.now(),
        })

        return self._json_response({
            "status": "received",
            "event_type": "status",
        })

    def _process_message_webhook(self, WebhookEvent, WhatsAppMessage, account, payload, raw_payload, external_event_id):
        """
        Process inbound WhatsApp message webhook.

        This preserves the existing UC-04/UC-05 behavior and adds the new
        durable whatsapp.message record required by UC-07.
        """
        partner_data = WebhookEvent._find_or_create_partner_from_payload(account, payload)
        partner = partner_data["partner"]

        lead = False
        if partner:
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
            "event_type": "message",
            "external_event_id": external_event_id,
            "raw_payload": raw_payload,
            "processing_status": "pending",
            "assigned_user_id": lead.user_id.id if lead and lead.user_id else False,
        })

        whatsapp_message = WhatsAppMessage.create_inbound_from_payload(
            account,
            partner,
            lead,
            payload,
        )

        if lead:
            WebhookEvent._post_whatsapp_message_to_lead_chatter(
                lead,
                partner,
                payload,
            )

        event.write({
            "processing_status": "processed",
            "processed_at": fields.Datetime.now(),
        })

        account.write({
            "last_webhook_received_at": fields.Datetime.now(),
        })

        _logger.info(
            "Processed WhatsApp message webhook. account_id=%s event_id=%s whatsapp_message_id=%s external_event_id=%s partner_id=%s lead_id=%s",
            account.id,
            event.id,
            whatsapp_message.id if whatsapp_message else None,
            external_event_id,
            event.partner_id.id if event.partner_id else None,
            event.lead_id.id if event.lead_id else None,
        )

        return self._json_response({
            "status": "received",
            "event_type": "message",
        })
