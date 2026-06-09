# -*- coding: utf-8 -*-
r"""
Create demo screenshot data for whatsapp_crm_bridge.

Usage from Odoo shell:

python odoo-bin shell -c odoo.conf -d whatsapp_crm_bridge_demo --db-filter=^whatsapp_crm_bridge_demo$

Then inside shell:

exec(open(r"C:\odoo18\dev\whatsapp_crm_bridge\scripts\create_demo_screenshot_data.py", encoding="utf-8").read())

This script is intended for local demo/screenshot databases only.
It does not use real WhatsApp credentials.
"""

from datetime import timedelta
import json

from odoo import fields

TARGET_DB = "whatsapp_crm_bridge_demo"

current_db = getattr(env.cr, "dbname", None)
if current_db != TARGET_DB:
    raise RuntimeError(
        "Refusing to create demo screenshot data on database %r. "
        "Connect Odoo shell to %r only." % (current_db, TARGET_DB)
    )

now = fields.Datetime.now()

Company = env["res.company"]
Partner = env["res.partner"]
User = env["res.users"]
Lead = env["crm.lead"]
Account = env["whatsapp.account"]
Message = env["whatsapp.message"]
Conversation = env["whatsapp.conversation"]
WebhookEvent = env["whatsapp.webhook.event"]

company = env.company
admin_user = env.ref("base.user_admin")


def has_field(model, field_name):
    return field_name in env[model]._fields


def first_existing_user():
    user = User.search([("share", "=", False)], limit=1)
    return user or admin_user


sales_user = first_existing_user()


def upsert_record(model, domain, values):
    allowed_values = {
        field_name: value
        for field_name, value in values.items()
        if has_field(model, field_name)
    }
    record = env[model].search(domain, limit=1)
    if record:
        record.write(allowed_values)
        return record
    return env[model].create(allowed_values)


print("Creating WhatsApp CRM Bridge demo screenshot data...")
print("Database:", current_db)


# -------------------------------------------------------------------------
# WhatsApp Account
# -------------------------------------------------------------------------

account_values = {
    "name": "Demo WhatsApp Account - Egypt Sales",
    "company_id": company.id,
    "active": True,
}

for field_name, value in {
    "mode": "sandbox",
    "api_version": "v20.0",
    "phone_number_id": "123456789000000",
    "waba_id": "987654321000000",
    "business_phone_number": "+201000000000",
    "access_token": "<META_ACCESS_TOKEN>",
    "webhook_verify_token": "<WEBHOOK_VERIFY_TOKEN>",
    "webhook_secret": "<WEBHOOK_SECRET>",
    "connection_state": "not_tested",
}.items():
    if has_field("whatsapp.account", field_name):
        account_values[field_name] = value

account = upsert_record(
    "whatsapp.account",
    [("name", "=", "Demo WhatsApp Account - Egypt Sales")],
    account_values,
)


# -------------------------------------------------------------------------
# Partners
# -------------------------------------------------------------------------

partners_data = [
    {
        "name": "Ahmed Hassan - Restaurant Owner",
        "mobile": "201012345678",
        "phone": "01012345678",
        "email": "ahmed.restaurant@example.com",
    },
    {
        "name": "Mona Ali - Retail Manager",
        "mobile": "201055501010",
        "phone": "01055501010",
        "email": "mona.retail@example.com",
    },
    {
        "name": "Karim Samir - Hotel Purchasing",
        "mobile": "201099998888",
        "phone": "01099998888",
        "email": "karim.hotel@example.com",
    },
]

partners = {}
for vals in partners_data:
    partner = upsert_record(
        "res.partner",
        [("mobile", "=", vals["mobile"])],
        vals,
    )
    partners[vals["name"]] = partner


# -------------------------------------------------------------------------
# CRM Leads
# -------------------------------------------------------------------------

lead_specs = [
    {
        "key": "restaurant",
        "name": "WhatsApp Inquiry - Restaurant Equipment",
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "description": "Customer asked via WhatsApp about kitchen equipment pricing and delivery.",
        "probability": 35,
    },
    {
        "key": "retail",
        "name": "WhatsApp Inquiry - Retail POS Setup",
        "partner": partners["Mona Ali - Retail Manager"],
        "description": "Customer requested a quotation for POS and inventory workflow consultation.",
        "probability": 55,
    },
    {
        "key": "hotel",
        "name": "WhatsApp Inquiry - Hotel Supply Order",
        "partner": partners["Karim Samir - Hotel Purchasing"],
        "description": "Customer asked about bulk order availability and payment terms.",
        "probability": 70,
    },
]

leads = {}
for spec in lead_specs:
    lead_values = {
        "name": spec["name"],
        "partner_id": spec["partner"].id,
        "contact_name": spec["partner"].name,
        "email_from": spec["partner"].email,
        "phone": spec["partner"].phone,
        "mobile": spec["partner"].mobile,
        "user_id": sales_user.id,
        "company_id": company.id,
        "description": spec["description"],
        "probability": spec["probability"],
        "type": "lead",
    }

    lead = upsert_record(
        "crm.lead",
        [("name", "=", spec["name"])],
        lead_values,
    )
    leads[spec["key"]] = lead


# -------------------------------------------------------------------------
# Conversations
# -------------------------------------------------------------------------

conversation_specs = [
    {
        "key": "restaurant",
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "lead": leads["restaurant"],
        "phone": "+201012345678",
        "normalized_phone": "201012345678",
        "state": "open",
        "needs_reply": True,
    },
    {
        "key": "retail",
        "partner": partners["Mona Ali - Retail Manager"],
        "lead": leads["retail"],
        "phone": "+201055501010",
        "normalized_phone": "201055501010",
        "state": "pending",
        "needs_reply": False,
    },
    {
        "key": "hotel",
        "partner": partners["Karim Samir - Hotel Purchasing"],
        "lead": leads["hotel"],
        "phone": "+201099998888",
        "normalized_phone": "201099998888",
        "state": "closed",
        "needs_reply": False,
    },
]

conversations = {}
for spec in conversation_specs:
    vals = {
        "name": "WhatsApp Conversation - %s" % spec["partner"].name,
        "account_id": account.id,
        "partner_id": spec["partner"].id,
        "lead_id": spec["lead"].id,
        "assigned_user_id": sales_user.id,
        "phone": spec["phone"],
        "normalized_phone": spec["normalized_phone"],
        "state": spec["state"],
    }

    for field_name, value in {
        "closed_at": now - timedelta(days=1),
        "closed_by_id": sales_user.id,
        "close_reason": "Demo conversation closed after quotation follow-up.",
        "lifecycle_note": "Demo lifecycle note for screenshots.",
        "last_state_change_at": now - timedelta(hours=6),
        "last_state_change_by_id": sales_user.id,
    }.items():
        if spec["state"] == "closed" and has_field("whatsapp.conversation", field_name):
            vals[field_name] = value

    conversation = upsert_record(
        "whatsapp.conversation",
        [
            ("account_id", "=", account.id),
            ("normalized_phone", "=", spec["normalized_phone"]),
            ("lead_id", "=", spec["lead"].id),
        ],
        vals,
    )
    conversations[spec["key"]] = conversation


# -------------------------------------------------------------------------
# Messages
# -------------------------------------------------------------------------

def message_values(
    *,
    conversation,
    lead,
    partner,
    direction,
    body,
    external_message_id,
    status,
    offset_hours,
    message_type="text",
    recipient_phone=False,
    sender_id=False,
    error_code=False,
    error_message=False,
):
    vals = {
        "account_id": account.id,
        "partner_id": partner.id,
        "lead_id": lead.id,
        "conversation_id": conversation.id,
        "assigned_user_id": sales_user.id,
        "direction": direction,
        "message_type": message_type,
        "body": body,
        "external_message_id": external_message_id,
        "status": status,
        "raw_payload": json.dumps(
            {
                "demo": True,
                "source": "create_demo_screenshot_data.py",
                "external_message_id": external_message_id,
                "status": status,
            },
            ensure_ascii=False,
        ),
    }

    if recipient_phone and has_field("whatsapp.message", "recipient_phone"):
        vals["recipient_phone"] = recipient_phone

    if sender_id and has_field("whatsapp.message", "external_sender_id"):
        vals["external_sender_id"] = sender_id

    msg_time = now - timedelta(hours=offset_hours)

    if direction == "inbound" and has_field("whatsapp.message", "received_at"):
        vals["received_at"] = msg_time

    if status == "sent" and has_field("whatsapp.message", "sent_at"):
        vals["sent_at"] = msg_time
    elif status == "delivered" and has_field("whatsapp.message", "delivered_at"):
        vals["sent_at"] = msg_time - timedelta(minutes=10) if has_field("whatsapp.message", "sent_at") else False
        vals["delivered_at"] = msg_time
    elif status == "read" and has_field("whatsapp.message", "read_at"):
        vals["sent_at"] = msg_time - timedelta(minutes=20) if has_field("whatsapp.message", "sent_at") else False
        vals["delivered_at"] = msg_time - timedelta(minutes=10) if has_field("whatsapp.message", "delivered_at") else False
        vals["read_at"] = msg_time
    elif status == "failed" and has_field("whatsapp.message", "failed_at"):
        vals["failed_at"] = msg_time
        if error_code and has_field("whatsapp.message", "error_code"):
            vals["error_code"] = error_code
        if error_message and has_field("whatsapp.message", "error_message"):
            vals["error_message"] = error_message

    return vals


message_specs = [
    {
        "conversation": conversations["restaurant"],
        "lead": leads["restaurant"],
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "direction": "inbound",
        "body": "Hello, I need pricing for a commercial oven and delivery to Nasr City.",
        "external_message_id": "wamid.demo.restaurant.in.001",
        "status": "received",
        "offset_hours": 5,
        "sender_id": "201012345678",
    },
    {
        "conversation": conversations["restaurant"],
        "lead": leads["restaurant"],
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "direction": "outbound",
        "body": "Thanks Ahmed. I will send you the available models and quotation shortly.",
        "external_message_id": "wamid.demo.restaurant.out.001",
        "status": "delivered",
        "offset_hours": 4,
        "recipient_phone": "201012345678",
    },
    {
        "conversation": conversations["restaurant"],
        "lead": leads["restaurant"],
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "direction": "inbound",
        "body": "Great. Please include warranty and installation cost.",
        "external_message_id": "wamid.demo.restaurant.in.002",
        "status": "received",
        "offset_hours": 1,
        "sender_id": "201012345678",
    },
    {
        "conversation": conversations["retail"],
        "lead": leads["retail"],
        "partner": partners["Mona Ali - Retail Manager"],
        "direction": "inbound",
        "body": "Can you help us connect WhatsApp inquiries to CRM follow-up?",
        "external_message_id": "wamid.demo.retail.in.001",
        "status": "received",
        "offset_hours": 30,
        "sender_id": "201055501010",
    },
    {
        "conversation": conversations["retail"],
        "lead": leads["retail"],
        "partner": partners["Mona Ali - Retail Manager"],
        "direction": "outbound",
        "body": "Yes, we can map WhatsApp messages into CRM leads and conversation follow-up queues.",
        "external_message_id": "wamid.demo.retail.out.001",
        "status": "read",
        "offset_hours": 28,
        "recipient_phone": "201055501010",
    },
    {
        "conversation": conversations["hotel"],
        "lead": leads["hotel"],
        "partner": partners["Karim Samir - Hotel Purchasing"],
        "direction": "inbound",
        "body": "We need a quotation for a bulk hotel supply order.",
        "external_message_id": "wamid.demo.hotel.in.001",
        "status": "received",
        "offset_hours": 60,
        "sender_id": "201099998888",
    },
    {
        "conversation": conversations["hotel"],
        "lead": leads["hotel"],
        "partner": partners["Karim Samir - Hotel Purchasing"],
        "direction": "outbound",
        "body": "Quotation has been prepared. Please review the attached commercial offer.",
        "external_message_id": "wamid.demo.hotel.out.001",
        "status": "failed",
        "offset_hours": 48,
        "recipient_phone": "201099998888",
        "error_code": "DEMO_FAILED",
        "error_message": "Demo failed status for screenshot/reporting purposes.",
    },
]

for spec in message_specs:
    vals = message_values(**spec)
    upsert_record(
        "whatsapp.message",
        [
            ("account_id", "=", account.id),
            ("external_message_id", "=", spec["external_message_id"]),
        ],
        vals,
    )


# -------------------------------------------------------------------------
# Webhook Events
# -------------------------------------------------------------------------

webhook_event_specs = [
    {
        "event_type": "message",
        "processing_status": "processed",
        "external_event_id": "wamid.demo.restaurant.in.001",
        "sender_phone": "201012345678",
        "normalized_sender_phone": "201012345678",
        "message_type": "text",
        "message_body": "Hello, I need pricing for a commercial oven and delivery to Nasr City.",
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "lead": leads["restaurant"],
    },
    {
        "event_type": "status",
        "processing_status": "processed",
        "external_event_id": "wamid.demo.restaurant.out.001",
        "sender_phone": "201012345678",
        "normalized_sender_phone": "201012345678",
        "message_type": "unknown",
        "message_body": False,
        "partner": partners["Ahmed Hassan - Restaurant Owner"],
        "lead": leads["restaurant"],
    },
    {
        "event_type": "status",
        "processing_status": "processed",
        "external_event_id": "wamid.demo.hotel.out.001",
        "sender_phone": "201099998888",
        "normalized_sender_phone": "201099998888",
        "message_type": "unknown",
        "message_body": False,
        "error_message": "Demo failed status event for screenshot/reporting purposes.",
        "partner": partners["Karim Samir - Hotel Purchasing"],
        "lead": leads["hotel"],
    },
]

for item in webhook_event_specs:
    vals = {
        "account_id": account.id,
        "partner_id": item["partner"].id,
        "lead_id": item["lead"].id,
        "assigned_user_id": sales_user.id,
        "raw_payload": json.dumps(
            {
                "demo": True,
                "event_type": item["event_type"],
                "external_event_id": item["external_event_id"],
            },
            ensure_ascii=False,
        ),
    }

    for field_name, value in {
        "event_type": item["event_type"],
        "processing_status": item["processing_status"],
        "external_event_id": item["external_event_id"],
        "sender_phone": item["sender_phone"],
        "normalized_sender_phone": item["normalized_sender_phone"],
        "message_type": item["message_type"],
        "message_body": item["message_body"],
        "error_message": item.get("error_message"),
        "processed_at": now - timedelta(minutes=15),
    }.items():
        if has_field("whatsapp.webhook.event", field_name):
            vals[field_name] = value

    upsert_record(
        "whatsapp.webhook.event",
        [
            ("account_id", "=", account.id),
            ("external_event_id", "=", item["external_event_id"]),
        ],
        vals,
    )


# -------------------------------------------------------------------------
# Recompute conversation stats if needed
# -------------------------------------------------------------------------

for conversation in conversations.values():
    if hasattr(conversation, "_compute_message_stats"):
        conversation._compute_message_stats()

env.cr.commit()

print("Demo data created successfully.")
print("WhatsApp Account:", account.display_name)
print("Partners:", len(partners))
print("Leads:", len(leads))
print("Conversations:", len(conversations))
print("Messages:", len(message_specs))
print("Webhook events:", len(webhook_event_specs))
