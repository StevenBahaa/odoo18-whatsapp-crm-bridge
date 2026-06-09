# Testing Checklist

Use this checklist before presenting, tagging, or merging UC-13.

## Commands

Compile Python files:

```bash
python -m compileall .
```

Upgrade the module:

```bash
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge -u whatsapp_crm_bridge --stop-after-init --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge$
```

Run the server:

```bash
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge$ --http-port=8070
```

## UI Checks

- Module installs or upgrades without errors.
- WhatsApp CRM menu appears for the correct groups.
- WhatsApp Account form opens and masks credential fields.
- Test Connection button still behaves as a placeholder and does not claim a real Meta API validation.
- CRM lead form shows Send WhatsApp for allowed users.
- CRM lead smart button appears when related conversations exist.

## Webhook Testing Checks

- GET `/whatsapp/webhook?db=whatsapp_crm_bridge` verifies with the configured `<WEBHOOK_VERIFY_TOKEN>`.
- Invalid verify token returns forbidden.
- POST message webhook with matching `phone_number_id` returns received.
- POST webhook with unknown `phone_number_id` is safely ignored and logged.
- Invalid JSON returns a controlled failed response.
- Empty payload is ignored.

## CRM Lead Checks

- Sender phone is extracted from inbound message payload.
- Phone is normalized for Egypt-focused formats.
- Existing partner is matched by phone or mobile when possible.
- New partner is created when no match exists.
- Existing open WhatsApp CRM lead is reused for the same partner when possible.
- New CRM lead is created only when no suitable open lead exists.
- Inbound WhatsApp message is posted to lead chatter as a safe note.

## Message Status Checks

- Inbound webhook creates a durable `whatsapp.message`.
- Outbound send success creates a sent `whatsapp.message`.
- Outbound send failure creates a failed `whatsapp.message`.
- Status webhook `sent` updates the matching message.
- Status webhook `delivered` updates the matching message.
- Status webhook `read` updates the matching message.
- Status webhook `failed` updates the matching message and stores error details when provided.
- Unknown status or unknown external message ID is logged as ignored, not treated as a webhook delivery failure.

## Conversation Lifecycle Checks

- Inbound message creates or reuses an open conversation by account and normalized phone.
- Outbound message from CRM links to the relevant conversation.
- Outbound message from conversation stays linked to that conversation.
- Needs Reply becomes true when latest inbound is newer than latest outbound.
- Mark Pending changes state and lifecycle note.
- Close Conversation sets state, closed at, closed by, and lifecycle note.
- Reopen Conversation clears closed metadata and returns to open.

## Reporting Checks

- Messages list opens.
- Messages pivot and graph views open.
- Webhook Events list opens.
- Webhook Events pivot and graph views open.
- Conversations list opens.
- Conversations pivot and graph views open.
- Filters and group-bys work for status, direction, salesperson, lead, partner, event type, processing status, conversation state, and date.

## Security Checks

- Documentation uses `<META_ACCESS_TOKEN>`, `<WEBHOOK_VERIFY_TOKEN>`, and `<WEBHOOK_SECRET>` placeholders only.
- No real access tokens are committed.
- No webhook secrets are committed.
- No demo data contains real tokens.
- Access token field is restricted to WhatsApp Integration Manager.
- Raw webhook events are visible only to intended groups.
- HTTP error responses do not expose tracebacks.
- Webhook verification and receipt do not log access tokens, verify tokens, webhook secrets, or authorization headers.

## No Token Logging Check

Review logs during:

- Account configuration.
- Webhook verification.
- Inbound message webhook.
- Status webhook.
- Outbound send failure.

Expected result:
Logs may include record IDs, event IDs, message IDs, and processing reasons, but must not include `<META_ACCESS_TOKEN>`, `<WEBHOOK_VERIFY_TOKEN>`, `<WEBHOOK_SECRET>`, bearer authorization headers, or full request parameter dictionaries containing secrets.
