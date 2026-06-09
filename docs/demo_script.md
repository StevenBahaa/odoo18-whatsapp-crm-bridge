# UC-13 Demo Script

Use this script to present the module as a portfolio-grade MVP. Keep all tokens as placeholders and use a demo database.

## 1. Configure WhatsApp Account

Presenter says:
"The integration starts with a WhatsApp account record. This is where the Odoo administrator maps a Meta WhatsApp Cloud API account to a company in Odoo."

Presenter does:
Open WhatsApp CRM > Configuration > WhatsApp Accounts. Create or open an account with sandbox values and placeholders such as `<META_ACCESS_TOKEN>` and `<WEBHOOK_VERIFY_TOKEN>`.

Expected result:
The account shows company, mode, API version, phone number ID, masked credentials, and technical status fields.

## 2. Verify Webhook Endpoint Concept

Presenter says:
"Meta verifies the callback URL with a GET request. Odoo checks the verify token against the configured active WhatsApp account."

Presenter does:
Explain the endpoint `/whatsapp/webhook?db=whatsapp_crm_bridge` and the Meta query parameters `hub.mode`, `hub.verify_token`, and `hub.challenge`.

Expected result:
When the verify token matches an active account, Odoo returns the challenge value. Invalid tokens return a forbidden response.

## 3. Receive Inbound WhatsApp Webhook

Presenter says:
"Inbound messages arrive as POST webhooks. The route is public because Meta is external, but processing resolves the database explicitly and then matches the payload to an active account."

Presenter does:
Send or describe a sample Meta message webhook payload with `metadata.phone_number_id` matching the configured account.

Expected result:
Odoo returns a received response and processes the message in the selected database.

## 4. Raw Webhook Event Logging

Presenter says:
"The first business layer is an audit layer. Every meaningful webhook payload becomes a traceable event record."

Presenter does:
Open WhatsApp CRM > Configuration > Webhook Events.

Expected result:
A `whatsapp.webhook.event` record shows event type, processing status, extracted sender details, related partner, related lead, assigned salesperson, and raw payload.

## 5. Phone Normalization

Presenter says:
"The MVP includes Egypt-focused normalization so common local phone formats can be matched consistently."

Presenter does:
Show the normalized sender phone on the webhook event or related message.

Expected result:
Examples such as `01012345678`, `+201012345678`, and `00201012345678` normalize to `201012345678`.

## 6. Partner Matching or Creation

Presenter says:
"Once Odoo extracts the sender phone, it looks for an existing customer by phone or mobile. If none exists, it creates a new contact."

Presenter does:
Open the matched partner from the webhook event or CRM lead.

Expected result:
The partner is linked to the normalized phone and can be reused for future WhatsApp messages.

## 7. CRM Lead Creation or Reuse

Presenter says:
"The module avoids creating a new lead for every message. It reuses an open WhatsApp lead for the same partner when possible."

Presenter does:
Open the CRM lead linked from the webhook event.

Expected result:
The lead has WhatsApp as the source when available, includes customer phone data, and contains an inbound WhatsApp chatter note.

## 8. Salesperson Assignment

Presenter says:
"Salesperson ownership is carried through the lead, message, webhook event, and conversation so managers can filter and group operational work."

Presenter does:
Assign a salesperson to the CRM lead, then review related messages and events.

Expected result:
Related WhatsApp records show the assigned salesperson and can be filtered or grouped by that user.

## 9. Open WhatsApp Conversation

Presenter says:
"The conversation model is the operational layer. It groups related inbound and outbound messages by account and normalized customer phone."

Presenter does:
Open the WhatsApp Conversations smart button from the CRM lead or open WhatsApp CRM > Configuration > Conversations.

Expected result:
The conversation shows customer, lead, assigned salesperson, lifecycle state, message counters, needs-reply status, and message timeline.

## 10. Send Manual WhatsApp Reply from CRM

Presenter says:
"A salesperson can send a manual text reply directly from the CRM lead. This MVP intentionally avoids templates, campaigns, AI replies, and live chat."

Presenter does:
Click Send WhatsApp on the CRM lead, review the selected account and normalized phone, enter a short text message, and send.

Expected result:
Odoo calls the Meta Cloud API send endpoint, posts a chatter note, and creates a durable outbound `whatsapp.message` record. Failed sends are also stored with error details.

## 11. Send Manual WhatsApp Reply from Conversation

Presenter says:
"The same send wizard is reused from the conversation screen, keeping the operational conversation linked to the outgoing message."

Presenter does:
Open a conversation and click Send WhatsApp.

Expected result:
The outbound message is linked to the same conversation, lead, partner, account, and assigned salesperson context.

## 12. Message Status Updates

Presenter says:
"Meta later sends status webhooks. The module updates existing message records by matching the external Meta message ID."

Presenter does:
Send or describe status webhook payloads for `sent`, `delivered`, `read`, and `failed`.

Expected result:
The matching `whatsapp.message` updates status timestamps. Failed messages store error code and error message when provided.

## 13. Conversation Lifecycle

Presenter says:
"Sales teams need an operational state separate from the CRM stage. Conversations can be open, pending, closed, or reopened."

Presenter does:
Open a conversation, mark it pending, close it with a reason, then reopen it.

Expected result:
The state changes, lifecycle note updates, and closed metadata is set or cleared appropriately.

## 14. Reporting

Presenter says:
"The reporting is intentionally Odoo-native. Managers can inspect message activity, webhook processing, and conversation workload without a custom dashboard."

Presenter does:
Open Messages, Webhook Events, and Conversations. Switch between list, pivot, and graph views. Use filters and group-bys for status, direction, salesperson, event type, processing status, and conversation state.

Expected result:
The presenter can show operational workload, message status distribution, processing audit records, and salesperson ownership using built-in Odoo reporting views.
