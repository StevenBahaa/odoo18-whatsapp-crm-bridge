# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class WhatsAppAccount(models.Model):
    _name = "whatsapp.account"
    _description = "WhatsApp Business Account"
    _order = "company_id, name"

    name = fields.Char(
        string="Account Name",
        required=True,
        help="Internal name for this WhatsApp Business API account.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Company that owns this WhatsApp account configuration.",
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Disable this account without deleting its configuration.",
    )

    mode = fields.Selection(
        selection=[
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        string="Mode",
        required=True,
        default="sandbox",
        help="Sandbox is used for portfolio/testing. Production is used for real Meta WhatsApp Business accounts.",
    )

    api_version = fields.Char(
        string="API Version",
        required=True,
        default="v20.0",
        help="Meta Graph API version, for example v20.0.",
    )

    phone_number_id = fields.Char(
        string="Phone Number ID",
        required=True,
        help="Meta WhatsApp Business phone number ID used when sending messages.",
    )

    waba_id = fields.Char(
        string="WhatsApp Business Account ID",
        help="Meta WhatsApp Business Account ID.",
    )

    business_phone_number = fields.Char(
        string="Business Phone Number",
        help="The visible WhatsApp business phone number.",
    )

    # Token storage approach:
    # Portfolio/MVP: stored as a Char field and masked in the XML form view.
    # This masks the value in the UI only; it does NOT encrypt the token in the database.
    # Production recommendation: replace this with encrypted storage or load the token
    # from an environment variable / secret manager / protected deployment-level secret.
    access_token = fields.Char(
        string="Access Token",
        groups="whatsapp_crm_bridge.group_whatsapp_integration_manager",
        help="Meta WhatsApp Cloud API access token. Restricted to Integration Managers.",
    )

    webhook_verify_token = fields.Char(
        string="Webhook Verify Token",
        required=True,
        groups="whatsapp_crm_bridge.group_whatsapp_integration_manager",
        help="Token used by Meta to verify the webhook callback URL.",
    )

    webhook_secret = fields.Char(
        string="Webhook Secret",
        groups="whatsapp_crm_bridge.group_whatsapp_integration_manager",
        help="Optional webhook secret for future payload signature validation.",
    )

    token_expiry_date = fields.Datetime(
        string="Token Expiry Date",
        groups="whatsapp_crm_bridge.group_whatsapp_integration_manager",
        help="Optional expiry date for temporary/sandbox tokens.",
    )

    last_webhook_received_at = fields.Datetime(
        string="Last Webhook Received At",
        readonly=True,
    )

    last_connection_test_at = fields.Datetime(
        string="Last Connection Test At",
        readonly=True,
    )

    connection_state = fields.Selection(
        selection=[
            ("not_tested", "Not Tested"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Connection State",
        default="not_tested",
        readonly=True,
        copy=False,
    )

    connection_error_message = fields.Text(
        string="Connection Error Message",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "phone_number_id_company_unique",
            "unique(phone_number_id, company_id)",
            "The Phone Number ID must be unique per company.",
        ),
    ]

    def action_test_connection(self):
        """
        UC-01 placeholder.

        The real Meta API connection test will be implemented later.
        For now, this button confirms that the configuration record exists
        and that required fields are available.
        """
        for account in self:
            missing_fields = []

            if not account.phone_number_id:
                missing_fields.append(_("Phone Number ID"))

            if not account.access_token:
                missing_fields.append(_("Access Token"))

            if missing_fields:
                raise UserError(
                    _("Cannot test connection. Missing required fields: %s")
                    % ", ".join(missing_fields)
                )

            account.write({
                "last_connection_test_at": fields.Datetime.now(),
                "connection_state": "not_tested",
                "connection_error_message": _(
                    "Connection test placeholder only. Real Meta API call is not implemented in UC-01."
                ),
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Account"),
                "message": _("Configuration looks ready. Real API test will be implemented later."),
                "type": "info",
                "sticky": False,
            },
        }