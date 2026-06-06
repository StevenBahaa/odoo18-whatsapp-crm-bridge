import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppWebhookController(http.Controller):

    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET"] ,  csrf=False)
    def verify_webhook(self, **kwargs):
        """
        Verify Meta WhatsApp webhook URL.

        Meta sends:
        - hub.mode
        - hub.verify_token
        - hub.challenge

        If the verify token matches an active WhatsApp account in Odoo,
        Odoo must return hub.challenge.
        """

        mode = kwargs.get("hub.mode")
        verify_token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        if mode != "subscribe" or not verify_token or not challenge:
            _logger.warning("Invalid webhook verification request: %s", kwargs)
            return request.make_response("Invalid verification request", status=400)

        account = request.env["whatsapp.account"].sudo().search([("verify_token", "=", verify_token), ("active", "=", True)], limit=1)

        if not account:
            _logger.warning("No active WhatsApp account found for verify token: %s", verify_token)
            return request.make_response("Invalid verify token", status=403)
        
        _logger.info(
                    "WhatsApp webhook verified successfully for account ID %s.",
                    account.id,
                )
        
        return request.make_response(challenge, status=200 , headers=[("Content-Type", "text/plain")],)