# -*- coding: utf-8 -*-
r"""
Create EXTRA demo screenshot data for whatsapp_crm_bridge.

This script complements scripts/create_demo_screenshot_data.py with additional
safe demo records for richer screenshots and reporting.

Usage from Odoo shell:

python odoo-bin shell -c odoo.conf -d whatsapp_crm_bridge_demo --db-filter=^whatsapp_crm_bridge_demo$

Then inside shell:

exec(open(r"C:\odoo18\dev\whatsapp_crm_bridge\scripts\create_extra_demo_screenshot_data.py", encoding="utf-8").read())

This script is intended for local demo/screenshot databases only.
It does not use real WhatsApp credentials.
It refuses to run on any database except whatsapp_crm_bridge_demo.
"""

from datetime import timedelta
import json

from odoo import fields

TARGET_DB = "whatsapp_crm_bridge_demo"

current_db = getattr(env.cr, "dbname", None)
if current_db != TARGET_DB:
    raise RuntimeError(
        "Refusing to create extra demo screenshot data on database %r. "
        "Connect Odoo shell to %r only." % (current_db, TARGET_DB)
    )

now = fields.Datetime.now()

User = env["res.users"]

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


print("Creating EXTRA WhatsApp CRM Bridge demo screenshot data...")
print("Database:", current_db)


# -------------------------------------------------------------------------
# WhatsApp Account
# -------------------------------------------------------------------------

account_values = {
    "name": "Demo WhatsApp Account - Extra Portfolio Data",
    "company_id": company.id,
    "active": True,
}

for field_name, value in {
    "mode": "sandbox",
    "api_version": "v20.0",
    "phone_number_id": "223456789000000",
    "waba_id": "887654321000000",
    "business_phone_number": "+201111111111",
    "access_token": "<META_ACCESS_TOKEN>",
    "webhook_verify_token": "<WEBHOOK_VERIFY_TOKEN>",
    "webhook_secret": "<WEBHOOK_SECRET>",
    "connection_state": "not_tested",
}.items():
    if has_field("whatsapp.account", field_name):
        account_values[field_name] = value

account = upsert_record(
    "whatsapp.account",
    [("name", "=", "Demo WhatsApp Account - Extra Portfolio Data")],
    account_values,
)


# -------------------------------------------------------------------------
# Partners
# -------------------------------------------------------------------------

partners_data = [
    {
        "key": "clinic",
        "name": "Dr. Sara Nabil - Dental Clinic",
        "mobile": "201066667777",
        "phone": "01066667777",
        "email": "sara.clinic@example.com",
    },
    {
        "key": "travel",
        "name": "Youssef Maher - Travel Agency",
        "mobile": "201022223333",
        "phone": "01022223333",
        "email": "youssef.travel@example.com",
    },
    {
        "key": "real_estate",
        "name": "Nadine Fathy - Real Estate Sales",
        "mobile": "201088887777",
        "phone": "01088887777",
        "email": "nadine.realestate@example.com",
    },
    {
        "key": "ecommerce",
        "name": "Omar Adel - E-commerce Store",
        "mobile": "201077778888",
        "phone": "01077778888",
        "email": "omar.store@example.com",
    },
]

partners = {}
for item in partners_data:
    vals = {
        "name": item["name"],
        "mobile": item["mobile"],
        "phone": item["phone"],
        "email": item["email"],
    }
    partner = upsert_record("res.partner", [("mobile", "=", item["mobile"])], vals)
    partners[item["key"]] = partner


# -------------------------------------------------------------------------
# CRM Leads
# -------------------------------------------------------------------------

lead_specs = [
    {
        "key": "clinic",
        "name": "WhatsApp Inquiry - Clinic Appointment Workflow",
        "description": "Dental clinic asked about organizing patient WhatsApp inquiries inside CRM.",
        "probability": 25,
    },
    {
        "key": "travel",
        "name": "WhatsApp Inquiry - Visa Consultation Follow-up",
        "description": "Travel agency requested a way to track visa inquiries coming from WhatsApp.",
        "probability": 45,
    },
    {
        "key": "real_estate",
        "name": "WhatsApp Inquiry - Property Leads Tracking",
        "description": "Real estate team asked for WhatsApp lead tracking and salesperson ownership.",
        "probability": 65,
    },
    {
        "key": "ecommerce",
        "name": "WhatsApp Inquiry - Online Order Support",
        "description": "E-commerce store asked how WhatsApp conversations can be linked to customer follow-up.",
        "probability": 80,
    },
]

leads = {}
for spec in lead_specs:
    partner = partners[spec["key"]]
    lead_values = {
        "name": spec["name"],
        "partner_id": partner.id,
        "contact_name": partner.name,
        "email_from": partner.email,
        "phone": partner.phone,
        "mobile": partner.mobile,
        "user_id": sales_user.id,
        "company_id": company.id,
        "description": spec["description"],
        "probability": spec["probability"],
        "type": "lead",
    }
    lead = upsert_record("crm.lead", [("name", "=", spec["name"])], lead_values)
    leads[spec["key"]] = lead


# -------------------------------------------------------------------------
# Conversations
# -------------------------------------------------------------------------

conversation_specs = [
    {
        "key": "clinic",
        "phone": "+201066667777",
        "normalized_phone": "201066667777",
        "state": "open",
    },
    {
        "key": "travel",
        "phone": "+201022223333",
        "normalized_phone": "201022223333",
        "state": "pending",
    },
    {
        "key": "real_estate",
        "phone": "+201088887777",
        "normalized_phone": "201088887777",
        "state": "open",
    },
    {
        "key": "ecommerce",
        "phone": "+201077778888",
        "normalized_phone": "201077778888",
        "state": "closed",
    },
]

conversations = {}
for spec in conversation_specs:
    partner = partners[spec["key"]]
    lead = leads[spec["key"]]
    vals = {
        "name": "WhatsApp Conversation - %s" % partner.name,
        "account_id": account.id,
        "partner_id": partner.id,
        "lead_id": lead.id,
        "assigned_user_id": sales_user.id,
        "phone": spec["phone"],
        "normalized_phone": spec["normalized_phone"],
        "state": spec["state"],
    }

    if spec["state"] == "closed":
        for field_name, value in {
            "closed_at": now - timedelta(days=2),
            "closed_by_id": sales_user.id,
            "close_reason": "Demo closed after customer confirmed the next action.",
            "lifecycle_note": "Extra demo lifecycle note for portfolio screenshots.",
            "last_state_change_at": now - timedelta(days=2),
            "last_state_change_by_id": sales_user.id,
        }.items():
            if has_field("whatsapp.conversation", field_name):
                vals[field_name] = value

    conversation = upsert_record(
        "whatsapp.conversation",
        [
            ("account_id", "=", account.id),
            ("normalized_phone", "=", spec["normalized_phone"]),
            ("lead_id", "=", lead.id),
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
                "source": "create_extra_demo_screenshot_data.py",
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
        if has_field("whatsapp.message", "sent_at"):
            vals["sent_at"] = msg_time - timedelta(minutes=8)
        vals["delivered_at"] = msg_time
    elif status == "read" and has_field("whatsapp.message", "read_at"):
        if has_field("whatsapp.message", "sent_at"):
            vals["sent_at"] = msg_time - timedelta(minutes=20)
        if has_field("whatsapp.message", "delivered_at"):
            vals["delivered_at"] = msg_time - timedelta(minutes=10)
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
        "key": "clinic",
        "direction": "inbound",
        "body": "Hi, can your CRM track patient inquiries coming from WhatsApp?",
        "external_message_id": "wamid.extra.clinic.in.001",
        "status": "received",
        "offset_hours": 18,
        "sender_id": "201066667777",
    },
    {
        "key": "clinic",
        "direction": "outbound",
        "body": "Yes, the module can create CRM leads and keep the conversation history linked.",
        "external_message_id": "wamid.extra.clinic.out.001",
        "status": "sent",
        "offset_hours": 17,
        "recipient_phone": "201066667777",
    },
    {
        "key": "clinic",
        "direction": "inbound",
        "body": "Great, please send me a demo flow for reception follow-up.",
        "external_message_id": "wamid.extra.clinic.in.002",
        "status": "received",
        "offset_hours": 2,
        "sender_id": "201066667777",
    },
    {
        "key": "travel",
        "direction": "inbound",
        "body": "We receive many visa inquiries on WhatsApp. Can we assign them to consultants?",
        "external_message_id": "wamid.extra.travel.in.001",
        "status": "received",
        "offset_hours": 36,
        "sender_id": "201022223333",
    },
    {
        "key": "travel",
        "direction": "outbound",
        "body": "Yes, every conversation can be assigned to a salesperson or consultant.",
        "external_message_id": "wamid.extra.travel.out.001",
        "status": "read",
        "offset_hours": 34,
        "recipient_phone": "201022223333",
    },
    {
        "key": "real_estate",
        "direction": "inbound",
        "body": "I want to connect WhatsApp property inquiries to Odoo CRM opportunities.",
        "external_message_id": "wamid.extra.realestate.in.001",
        "status": "received",
        "offset_hours": 12,
        "sender_id": "201088887777",
    },
    {
        "key": "real_estate",
        "direction": "outbound",
        "body": "I will prepare a CRM workflow demo for property sales tracking.",
        "external_message_id": "wamid.extra.realestate.out.001",
        "status": "failed",
        "offset_hours": 11,
        "recipient_phone": "201088887777",
        "error_code": "EXTRA_DEMO_FAILED",
        "error_message": "Extra demo failed outbound message for reporting screenshots.",
    },
    {
        "key": "ecommerce",
        "direction": "inbound",
        "body": "Can WhatsApp customer support messages be visible to the sales team?",
        "external_message_id": "wamid.extra.ecommerce.in.001",
        "status": "received",
        "offset_hours": 72,
        "sender_id": "201077778888",
    },
    {
        "key": "ecommerce",
        "direction": "outbound",
        "body": "Yes, messages are linked to customer, CRM lead, conversation, and salesperson.",
        "external_message_id": "wamid.extra.ecommerce.out.001",
        "status": "delivered",
        "offset_hours": 70,
        "recipient_phone": "201077778888",
    },
    {
        "key": "ecommerce",
        "direction": "outbound",
        "body": "The demo conversation has been closed after confirming the workflow.",
        "external_message_id": "wamid.extra.ecommerce.out.002",
        "status": "read",
        "offset_hours": 66,
        "recipient_phone": "201077778888",
    },
]

for spec in message_specs:
    spec_data = dict(spec)
    key = spec_data.pop("key")
    partner = partners[key]
    lead = leads[key]
    conversation = conversations[key]
    vals = message_values(
        conversation=conversation,
        lead=lead,
        partner=partner,
        **spec_data
    )
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
        "key": "clinic",
        "event_type": "message",
        "processing_status": "processed",
        "external_event_id": "wamid.extra.clinic.in.001",
        "sender_phone": "201066667777",
        "normalized_sender_phone": "201066667777",
        "message_type": "text",
        "message_body": "Hi, can your CRM track patient inquiries coming from WhatsApp?",
    },
    {
        "key": "travel",
        "event_type": "status",
        "processing_status": "processed",
        "external_event_id": "wamid.extra.travel.out.001",
        "sender_phone": "201022223333",
        "normalized_sender_phone": "201022223333",
        "message_type": "unknown",
        "message_body": False,
    },
    {
        "key": "real_estate",
        "event_type": "status",
        "processing_status": "processed",
        "external_event_id": "wamid.extra.realestate.out.001",
        "sender_phone": "201088887777",
        "normalized_sender_phone": "201088887777",
        "message_type": "unknown",
        "message_body": False,
        "error_message": "Extra demo failed status event for reporting screenshots.",
    },
    {
        "key": "ecommerce",
        "event_type": "message",
        "processing_status": "processed",
        "external_event_id": "wamid.extra.ecommerce.in.001",
        "sender_phone": "201077778888",
        "normalized_sender_phone": "201077778888",
        "message_type": "text",
        "message_body": "Can WhatsApp customer support messages be visible to the sales team?",
    },
]

for item in webhook_event_specs:
    partner = partners[item["key"]]
    lead = leads[item["key"]]
    vals = {
        "account_id": account.id,
        "partner_id": partner.id,
        "lead_id": lead.id,
        "assigned_user_id": sales_user.id,
        "raw_payload": json.dumps(
            {
                "demo": True,
                "source": "create_extra_demo_screenshot_data.py",
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
        "processed_at": now - timedelta(minutes=10),
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

print("Extra demo data created successfully.")
print("WhatsApp Account:", account.display_name)
print("Partners:", len(partners))
print("Leads:", len(leads))
print("Conversations:", len(conversations))
print("Messages:", len(message_specs))
print("Webhook events:", len(webhook_event_specs))
