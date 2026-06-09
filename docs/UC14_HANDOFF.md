# UC-14 Handoff — Odoo View UX Polish for Portfolio Screenshots

## Branch

`feature/uc-14-view-ux-polish`

## Objective

Improve the visual presentation and usability of all Odoo XML views in the
`whatsapp_crm_bridge` module so that portfolio screenshots, GitHub README,
CV, and LinkedIn demonstrations look professional and readable.

This UC is **UI/view polish only**. No Python business logic was changed.

---

## Views Changed

| File | Changes |
|---|---|
| `views/whatsapp_account_views.xml` | List decorations, badge widgets, notebook tabs for credentials/status, menu hierarchy |
| `views/whatsapp_conversation_views.xml` | List decorations, cleaner form with tabbed sections, enriched search, reporting action |
| `views/whatsapp_message_views.xml` | List decorations, form restructured with Body/Timeline/Errors/Technical tabs, enriched search, reporting action |
| `views/whatsapp_webhook_event_views.xml` | List decorations, form with clear sections, raw payload in manager-only tab, reporting action |
| `views/whatsapp_send_message_wizard_views.xml` | Cleaner layout with Context/Delivery groups, help text |
| `views/crm_lead_views.xml` | Improved icons, `btn-secondary` for WhatsApp button to not compete with CRM primary actions |

---

## Menu Structure (New)

```
WhatsApp CRM                    (group_whatsapp_crm_user — all users)
├── Operations                  (sequence 10)
│   ├── Conversations           (sequence 10) — group_whatsapp_crm_user
│   ├── Messages                (sequence 20) — group_whatsapp_crm_user
│   └── Webhook Events          (sequence 30) — group_whatsapp_integration_manager
├── Reporting                   (sequence 20)
│   ├── Message Analysis        (sequence 10) — group_whatsapp_crm_manager
│   ├── Webhook Analysis        (sequence 20) — group_whatsapp_crm_manager
│   └── Conversation Analysis   (sequence 30) — group_whatsapp_crm_manager
└── Configuration               (sequence 100)
    └── WhatsApp Accounts       — group_whatsapp_integration_manager
```

**Previously:** all screens (Conversations, Messages, Webhook Events) were under
`Configuration`, which is incorrect UX for operational screens.

**Now:** Operational screens are under `Operations`. Analysis views under `Reporting`.
Credentials/accounts under `Configuration`.

---

## UX Improvements Made

### All list views
- Added row-level `decoration-danger/warning/success/muted` based on status fields
- Added `widget="badge"` to status and direction fields for visual color-coding
- Moved technical/secondary fields to `optional="hide"` so they don't clutter default view
- Added `widget="boolean_toggle"` for boolean fields

### WhatsApp Account
- Form: Credentials moved to `API Credentials` notebook page (manager-only group)
- Form: Technical status moved to `Webhook & Test Status` tab
- Form: `mode` field shows as radio buttons instead of dropdown
- List: No token fields visible at any point

### WhatsApp Conversations
- List: `needs_reply` shows as boolean toggle badge; row turns danger when needs reply
- Form: `Needs Reply` alert box appears at top when applicable
- Form: Messages tab shows badge-decorated direction/status columns
- Form: Activity tab shows message timeline and counters
- Form: Lifecycle tab shows close reason, closed_at, closed_by, state audit
- Search: Added `Has CRM Lead`, `Has Customer` filters
- New `action_whatsapp_conversation_reporting` (pivot/graph/list) for Reporting menu

### WhatsApp Messages
- Form: Redesigned with title from message body, grouped sections
- Form: Status Timeline tab cleanly splits inbound vs outbound timestamps
- Form: Error Details tab only shows when error exists
- Form: Technical/Raw Payload tab restricted to `group_whatsapp_integration_manager`
- Search: Added `Has Conversation`, `Has CRM Lead`, `Has Customer` filters
- Search: Group By Date now uses `create_date:day` for useful daily grouping
- New `action_whatsapp_message_reporting` (pivot/graph/list) for Reporting menu

### WhatsApp Webhook Events
- Form: Grouped into Event Summary / Processing Result / Sender Information / Matching Result
- Form: Raw Payload in manager-only tab
- Form: `message_body` section invisible when empty
- List: `normalized_sender_phone`, `external_event_id`, `processed_at` moved to `optional="hide"`
- New `action_whatsapp_webhook_event_reporting` (pivot/graph/list) for Reporting menu

### Send Message Wizard
- Added title `h2` heading
- Context group (lead/partner/conversation) vs Delivery group (account/phone)
- Help text explaining MVP scope (no templates/media)
- Send button renamed to `Send Message` for clarity

### CRM Lead Extension
- Smart button icon changed from `fa-whatsapp` to `fa-comments` (WhatsApp icon not in standard FontAwesome)
- Smart button string shortened to `WhatsApp` for clean stat display
- Send WhatsApp header button changed to `btn-secondary` + `fa-whatsapp` icon

---

## Tests Run

```
python -m compileall .
# Result: Clean — no Python errors
```

```
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge -u whatsapp_crm_bridge \
  --stop-after-init --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge$
# Result: Module loaded in ~0.74s, 533 queries. No ERROR. No CRITICAL.
# Pre-existing WARNING: message_count/message_ids share label "Messages" (model issue, not view).
```

```
python odoo-bin -c odoo.conf -d whatsapp_crm_bridge_demo -u whatsapp_crm_bridge \
  --stop-after-init --max-cron-threads=0 --db-filter=^whatsapp_crm_bridge_demo$
# Result: Module loaded in ~0.93s, 541 queries. No ERROR. No CRITICAL.
# Same pre-existing WARNING only.
```

---

## Manual UI Checks (Recommended)

After starting the demo server on port 8070:

- [ ] `WhatsApp CRM` menu appears with Operations / Reporting / Configuration sub-menus
- [ ] `Operations > Conversations` shows list with colored rows (danger=needs reply, warning=pending, muted=closed)
- [ ] Conversation form opens; statusbar shows open/pending/closed; tabs load correctly
- [ ] `Send WhatsApp` button in conversation form opens wizard
- [ ] `Open CRM Lead` button in conversation form works
- [ ] Lifecycle buttons (Mark Pending, Close, Reopen) still change state correctly
- [ ] `Operations > Messages` list shows badge-decorated direction/status columns
- [ ] Message form opens with Body / Status Timeline / Error Details / Technical tabs
- [ ] `Operations > Webhook Events` list shows concise columns; technical fields hidden by default
- [ ] Webhook Event form opens; Raw Payload visible only for Integration Managers
- [ ] `Reporting > Message Analysis` opens in pivot view
- [ ] `Reporting > Webhook Analysis` opens in pivot view
- [ ] `Reporting > Conversation Analysis` opens in pivot view
- [ ] `Configuration > WhatsApp Accounts` list shows no token values
- [ ] Account form `API Credentials` tab is hidden for non-manager users
- [ ] CRM lead form shows `Send WhatsApp` button in header and WhatsApp smart button
- [ ] No Owl/JS errors in browser console on any screen

---

## Known Risks

| Risk | Severity | Notes |
|---|---|---|
| `fa-whatsapp` icon on CRM button | Low | Not in standard FontAwesome 4 — may render as empty icon in some Odoo builds |
| Pre-existing `message_count/message_ids` label collision | Low | Model-level warning, not a view bug. Separate fix if needed |
| Raw payload `widget="code"` | Low | Supported in Odoo 18 but degrades gracefully if not available |
| `widget="boolean_toggle"` in list | Low | Supported in Odoo 18; renders as checkbox fallback if not |

---

## Screenshots Recommended

1. **Conversations list** — colored rows showing Open/Pending/Closed states with Needs Reply badge
2. **Conversation form** — header buttons + statusbar + Needs Reply alert
3. **Conversation form → Messages tab** — badge-decorated message rows
4. **Messages list** — direction/status badge columns
5. **Message form** — Status Timeline tab showing sent/delivered/read timestamps
6. **Webhook Events list** — concise view with processing status badges
7. **Webhook Event form** — Event Summary + Processing Result sections
8. **WhatsApp Account form** — masked credentials in API Credentials tab
9. **Reporting → Message Analysis** — pivot view with direction/status breakdown
10. **CRM Lead** — WhatsApp smart button + Send WhatsApp header button

---

*Implemented: 2026-06-09 | Branch: feature/uc-14-view-ux-polish*
