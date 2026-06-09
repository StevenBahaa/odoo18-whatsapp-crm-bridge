# Roadmap and Release Notes

## Completed Milestones

### v0.1.0-whatsapp-crm-core

Core CRM integration foundation:

- WhatsApp account configuration.
- Meta webhook verification concept.
- Inbound webhook logging.
- Egypt-focused phone normalization.
- Partner matching and creation.
- CRM lead creation and reuse.
- Manual text reply from CRM lead.

### v0.2.0-message-status-assignment

Operational message tracking:

- Durable `whatsapp.message` records.
- Outbound send attempt recording.
- Status updates for sent, delivered, read, and failed messages.
- Salesperson assignment visibility on messages and webhook events.

### v0.3.0-whatsapp-conversations-reporting

Conversation and reporting layer:

- `whatsapp.conversation` operational model.
- Conversation grouping for inbound and outbound messages.
- CRM lead smart button for conversations.
- Send WhatsApp action from conversations.
- List, search, pivot, and graph reporting for messages, webhook events, and conversations.

## Planned Milestone

### v0.4.0-whatsapp-crm-operations

Portfolio polish and demo readiness:

- Professional README.
- Demo script.
- Portfolio summary.
- Testing checklist.
- Roadmap/release notes.
- UC-13 handoff.
- Security wording and demo-safe documentation review.

## Use Case List

- UC-01: WhatsApp Account Configuration.
- UC-02: Webhook Verification.
- UC-03: Inbound Webhook Logging.
- UC-04: Partner Matching.
- UC-05: CRM Lead Creation.
- UC-06: Manual Reply from CRM.
- UC-07: Message Status Updates.
- UC-08: Salesperson Assignment.
- UC-09: Reporting Views.
- UC-10: WhatsApp Conversations.
- UC-11: Conversation Follow-up Actions.
- UC-12: Conversation Lifecycle Management.
- UC-13: Portfolio Polish and Demo Readiness.

## Future Ideas Outside Current MVP

The following are intentionally out of scope for the current portfolio-grade MVP:

- WhatsApp templates.
- Media messages.
- Live chat UI.
- Odoo bus notifications.
- Chatbot.
- AI suggested replies.
- Bulk campaigns.
- SLA automation.
- Advanced assignment rules.
- Multi-country phone normalization.
- Retry queues and cron-based delivery recovery.
- Webhook signature validation.
- Production-grade secret management.
