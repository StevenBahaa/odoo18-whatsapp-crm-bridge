# -*- coding: utf-8 -*-

{
    "name": "WhatsApp CRM Bridge",
    "summary": "Connect WhatsApp Business Cloud API with Odoo CRM",
    "description": """
WhatsApp CRM Bridge
===================

A portfolio-grade Odoo 18 Community integration module that connects
Meta WhatsApp Business Cloud API with Odoo CRM.

MVP v1 focuses on:
- WhatsApp account configuration
- Webhook verification
- Inbound webhook logging
- CRM lead creation from WhatsApp messages
- Manual WhatsApp replies from CRM leads
    """,
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Steven Bahaa",
    "license": "LGPL-3",
    "depends": [
        "base",
        "crm",
        "mail",
    ],
    "data": [
        "security/whatsapp_security.xml",
        "security/ir.model.access.csv",
        "data/whatsapp_data.xml",
        "views/whatsapp_account_views.xml",
        "views/whatsapp_webhook_event_views.xml",
        "views/whatsapp_send_message_wizard_views.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}