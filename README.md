# WhatsApp Business API to Odoo CRM Connector

A portfolio-grade MVP for connecting a Meta WhatsApp Cloud API integration concept with Odoo 18 Community CRM.

This module is designed for demonstration, GitHub, CV, LinkedIn, and technical portfolio review. It shows how WhatsApp conversations can become structured CRM records, message history, operational follow-up queues, and reporting data inside Odoo. It is safe for demonstration after replacing credentials with local placeholder or sandbox values, but it is not presented as production-ready software.

## Business Problem

Many sales teams receive new customer inquiries through WhatsApp, while their formal pipeline lives in Odoo CRM. Without an integration layer, customer messages stay outside the CRM process, salesperson ownership is unclear, follow-up history is fragmented, and managers cannot report on WhatsApp activity.

## Solution Overview

`whatsapp_crm_bridge` connects WhatsApp webhook events to Odoo CRM concepts:

- Meta webhook verification and inbound webhook receipt are handled through `/whatsapp/webhook`.
- Raw webhook payloads are stored in an audit model for traceability.
- Incoming customer phone numbers are normalized for the Egypt-focused MVP.
- Partners and open CRM leads are matched or created from inbound messages.
- Inbound and outbound WhatsApp messages are stored in a durable message model.
- Conversations group messages into an operational follow-up layer with lifecycle states.
- CRM users can send manual text replies from CRM leads or conversations.
- Odoo-native list, search, pivot, and graph views support reporting.

## Key Features

### Configuration and Integration

- WhatsApp account configuration per company.
- Sandbox/production mode flag.
- Meta API version, phone number ID, WABA ID, business phone, access token, webhook verify token, and optional webhook secret fields.
- Webhook verification endpoint for Meta callback setup.
- Explicit database resolution for external webhook calls using `?db=whatsapp_crm_bridge`.

### CRM Intake

- Inbound WhatsApp message webhook handling.
- Raw webhook event logging.
- Egypt-focused phone normalization.
- Partner matching by normalized phone/mobile, with partner creation when needed.
- Open CRM lead reuse for WhatsApp inquiries.
- New CRM lead creation only when no suitable open WhatsApp lead exists.
- Safe chatter notes on CRM leads for inbound WhatsApp messages.

### Messaging Operations

- Manual outbound text reply from a CRM lead.
- Manual outbound text reply from a WhatsApp conversation.
- Outbound Meta Cloud API send attempt tracking.
- Durable `whatsapp.message` records for both successful and failed send attempts.
- Message status updates for `sent`, `delivered`, `read`, and `failed`.

### Conversation Management

- `whatsapp.conversation` groups inbound and outbound messages by account and normalized phone.
- Conversation ownership through assigned salesperson.
- Needs-reply indicator when the latest inbound message is newer than the latest outbound reply.
- Lifecycle states: open, pending, closed, reopened.
- Close reason, closed by, closed at, latest lifecycle note, and last state change tracking.
- CRM lead smart button for related WhatsApp conversations.

### Reporting

- List, search, pivot, and graph views for WhatsApp messages.
- List, search, pivot, and graph views for webhook events.
- List, search, pivot, and graph views for conversations.
- Filters and group-bys for status, direction, salesperson, lead, partner, event type, processing status, conversation state, and creation date.

## Architecture Overview

The module separates the integration into four business layers:

| Layer | Model | Purpose |
| --- | --- | --- |
| Raw audit/debug layer | `whatsapp.webhook.event` | Stores received webhook payloads, processing status, extracted fields, and related partner/lead/salesperson context. |
| Durable message layer | `whatsapp.message` | Stores inbound/outbound messages, external Meta message IDs, delivery/read/failure status, timestamps, and payload traces. |
| Operational conversation layer | `whatsapp.conversation` | Groups messages by customer/account, tracks ownership, reply need, and lifecycle state. |
| Sales pipeline layer | `crm.lead` | Holds the sales opportunity or lead created/reused from WhatsApp inquiries. |

## Main Odoo Models

- `whatsapp.account`: Meta WhatsApp account configuration and credential holder.
- `whatsapp.webhook.event`: raw webhook event log and processing audit record.
- `whatsapp.message`: durable WhatsApp message and status tracking record.
- `whatsapp.conversation`: operational conversation ownership and lifecycle record.
- `whatsapp.send.message.wizard`: transient wizard for manual text replies.
- `crm.lead`: extended with a Send WhatsApp action and WhatsApp Conversations smart button.

## User Flow

1. An integration manager configures a WhatsApp account in Odoo.
2. Meta verifies `/whatsapp/webhook` using the configured verify token.
3. Meta sends an inbound WhatsApp message webhook to Odoo.
4. Odoo logs the raw webhook event.
5. Odoo normalizes the sender phone for the Egypt-focused MVP.
6. Odoo matches or creates a customer partner.
7. Odoo reuses an open WhatsApp CRM lead or creates a new one.
8. Odoo posts a safe chatter note on the CRM lead.
9. Odoo creates or reuses an open WhatsApp conversation.
10. A salesperson reviews the lead or conversation and sends a manual WhatsApp text reply.
11. Odoo stores the outbound message attempt.
12. Later Meta status webhooks update message state to sent, delivered, read, or failed.
13. Managers review messages, webhook events, conversations, and reporting views.

## Setup Instructions

1. Clone the repository into the Odoo addons path.
2. Install Odoo 18 Community dependencies and ensure `crm` and `mail` are available.
3. Create or select a local database, for example `whatsapp_crm_bridge`.
4. Add this repository path to the Odoo addons path in `odoo.conf`.
5. Install or upgrade the module `whatsapp_crm_bridge`.
6. In Odoo, assign users to the needed groups:
   - WhatsApp CRM User
   - WhatsApp CRM Manager
   - WhatsApp Integration Manager
7. Configure a WhatsApp Account with placeholder or sandbox values:
   - Access Token: `<META_ACCESS_TOKEN>`
   - Webhook Verify Token: `<WEBHOOK_VERIFY_TOKEN>`
   - Webhook Secret: `<WEBHOOK_SECRET>`
   - Phone Number ID: a sandbox or test phone number ID

## Local Testing Commands

Upgrade the module:

```bash
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge -u whatsapp_crm_bridge --stop-after-init --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge$
```

Run the server on port 8070:

```bash
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge$ --http-port=8070
```

Compile Python files:

```bash
python -m compileall .
```

## Meta Webhook Local Testing Notes

The webhook route is:

```text
/whatsapp/webhook
```

For local testing with a tunnel such as ngrok, configure Meta with a callback URL like:

```text
https://<your-tunnel-host>/whatsapp/webhook?db=whatsapp_crm_bridge
```

Webhook verification expects Meta query parameters:

- `hub.mode=subscribe`
- `hub.verify_token=<WEBHOOK_VERIFY_TOKEN>`
- `hub.challenge=<CHALLENGE_VALUE>`

POST payloads must include a Meta WhatsApp `phone_number_id` matching an active `whatsapp.account` record. Status webhooks update existing messages by matching the external Meta message ID.

## Screenshot Placeholders

Real screenshots should be captured from a clean demo database. Do not add fake screenshots.

- `docs/screenshots/whatsapp-account-configuration.png`: WhatsApp Account Configuration
- `docs/screenshots/crm-lead-whatsapp-reply.png`: CRM Lead WhatsApp Reply
- `docs/screenshots/whatsapp-messages.png`: WhatsApp Messages
- `docs/screenshots/whatsapp-conversations.png`: WhatsApp Conversations
- `docs/screenshots/reporting-pivot-graph.png`: Reporting Pivot/Graph

## Security Notes

- This is a portfolio-grade MVP, not a hardened production integration.
- Access tokens and webhook tokens must use placeholders in documentation and demo data.
- The access token field is masked in the Odoo form and restricted to the WhatsApp Integration Manager group.
- Form masking does not encrypt the value in the database.
- Production deployments should use encrypted secret storage, environment variables, or a deployment secret manager.
- Webhook responses do not expose tracebacks or token values.
- Do not log access tokens, webhook verify tokens, webhook secrets, or raw authorization headers.
- Raw webhook payloads may contain customer data and should be treated as operational audit data with restricted access.
- The optional webhook secret field exists for future hardening; payload signature validation is not implemented in the current MVP.

## Known Limitations

- Designed for Odoo 18 Community.
- Egypt-focused phone normalization only.
- Manual text replies only.
- No WhatsApp template management.
- No media message handling beyond unsupported-message labeling.
- No live chat UI or real-time bus notifications.
- No chatbot or AI suggested replies.
- No campaign or bulk messaging features.
- No cron retry queue.
- No SLA automation.
- No advanced assignment rules.
- Connection test is still a local configuration placeholder, not a real Meta API validation flow.
- Production secret management and webhook signature validation are intentionally outside the current MVP.

## Roadmap and Out-of-Scope Items

Completed portfolio milestones:

- `v0.1.0-whatsapp-crm-core`: account configuration, webhook verification/logging, partner matching, CRM lead creation, manual reply foundation.
- `v0.2.0-message-status-assignment`: durable messages, status updates, salesperson assignment.
- `v0.3.0-whatsapp-conversations-reporting`: conversations, reporting, CRM/conversation actions.

Planned milestone:

- `v0.4.0-whatsapp-crm-operations`: portfolio polish, demo readiness, lifecycle documentation, and release review.

Future ideas are intentionally outside the current MVP: templates, media messages, live chat UI, bus notifications, chatbot, AI suggested replies, bulk campaigns, SLA automation, advanced assignment rules, and multi-country phone normalization.

## Portfolio Positioning

This repository demonstrates how to design a scoped integration between an external messaging platform and Odoo CRM without overclaiming production readiness. It is useful as a portfolio case study for:

- Odoo 18 Community module development.
- CRM workflow design.
- Webhook-based integration architecture.
- Meta WhatsApp Cloud API integration concept.
- Secure documentation and demo preparation.
- Business-friendly reporting using Odoo-native views.
