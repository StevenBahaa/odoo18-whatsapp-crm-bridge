# WhatsApp CRM Bridge for Odoo 18 Community

A portfolio-grade Odoo 18 Community integration module that connects Meta WhatsApp Business Cloud API with Odoo CRM.

The module is designed for Middle East / Egypt business workflows where WhatsApp is often the primary customer communication channel, while Odoo CRM is the system where sales leads should be managed.

## Current Status

### Completed

- UC-01: WhatsApp Account Configuration

### Planned

- UC-02: Webhook Verification
- UC-03: Inbound Webhook Logging
- UC-04: Partner Matching
- UC-05: CRM Lead Creation
- UC-06: Manual Reply from CRM
- UC-07: Message Status Updates
- UC-08: Salesperson Assignment
- UC-09: Basic Dashboard and Reporting

## UC-01 Scope

UC-01 adds the configuration foundation:

- `whatsapp.account` model
- sandbox/production mode
- Meta API configuration fields
- restricted access token field
- webhook verify token field
- security groups
- backend menu and views
- connection test placeholder

## Security Notes

For this portfolio MVP, the access token is stored as a restricted Odoo Char field and masked in the form view.

Important:

- Masking hides the token in the UI.
- Masking does not encrypt the token in the database.
- Production deployments should use encrypted storage, environment variables, or an external secret manager.
- Tokens must never be printed in logs, chatter, webhook logs, or exported debug payloads.

## MVP Exclusions

The MVP does not include:

- bulk campaigns
- chatbot
- AI auto-replies
- media support
- WhatsApp template management
- cron-based retries
- full live chat UI