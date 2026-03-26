# First-Contact Confirmation & Override Workflow

## Overview

Raj now includes intelligent first-contact confirmation and Mo override capabilities to protect personal relationships and maintain control over automated responses.

## Features

### 1. First-Contact Confirmation (Option A via WhatsApp)

When a **new customer** messages Raj on a **personal channel** (Instagram DM, TikTok, Messenger), Raj will:

1. **Detect** that this is a first-contact from a new customer
2. **Send WhatsApp** to Mo asking for approval
3. **Wait** for Mo's decision before responding
4. **Remember** the approval for future messages from this customer

#### Channels That Trigger First-Contact Ask
- Instagram DM (personal message, not General tab)
- TikTok DM
- Facebook Messenger

#### Channels That Auto-Respond (No Ask)
- WhatsApp (trusted channel)
- SMS (trusted channel)
- Instagram General Tab (business tab, existing customers)
- Facebook Page messages (new landing zone)
- Web form

#### Database Fields
```python
Customer.first_contact_flagged  # New customers waiting for approval
Customer.is_personal            # Mark as "hands-off" for Raj
Customer.raj_can_respond        # Pause flag for specific customers

FirstContactRequest.status      # 'pending', 'approved', 'rejected'
FirstContactRequest.decision    # 'raj' or 'mo' (who should respond)
FirstContactRequest.mo_decision_at  # When Mo made decision
```

### 2. Mo Override (24-Hour Auto-Pause)

When Mo replies to a customer, Raj automatically **pauses** for that customer for **24 hours**:

#### How It Works
1. **Mo replies** to a customer conversation
2. **Backend detects** that Mo is taking over (sets `mo_override = True`)
3. **Raj stops responding** to that customer for 24 hours
4. **Auto-resumes** after 24 hours, OR Mo can manually resume earlier

#### Database Fields
```python
Customer.mo_override            # Is Raj currently paused?
Customer.override_at            # When Mo took over
Customer.auto_resume_at         # When Raj auto-resumes (24h later)
```

#### Background Job
A job runs **every 5 minutes** to check for expired overrides:
- Finds customers with `auto_resume_at <= now()`
- Resets override flags
- Logs auto-resume event

### 3. Instagram General Tab Auto-Response

Existing customers who message in Instagram General Tab (business tab) get **auto-response** without first-contact ask.

- **New customers on General Tab** = (Very rare, ask first)
- **Existing customers on General Tab** = Auto-respond
- **Any customer on Instagram DM** = Ask first (personal channel)

### 4. Facebook Replacement

Facebook messages now route to Raj instead of previous assistant:
- **All Facebook messages** = Auto-respond (no ask)
- **Facebook is considered a business channel**

### 5. Unified Dashboard

Access all messages across channels in one place:

#### Endpoints
```
GET /dashboard/messages           # All unified messages
GET /dashboard/summary            # High-level stats
GET /first-contact/pending        # Pending approvals waiting for Mo
```

#### Dashboard Features
- Filter by: `all`, `pending`, `raj-handled`, `mo-handled`
- See customer name, channel, message preview
- Quick-action buttons (approve/reject/override)
- Current override status for each customer

## API Endpoints

### Approve First Contact
```
POST /first-contact/approve

Body:
{
    "first_contact_id": 123,
    "decision": "raj"  # or "mo" or "reject"
}

Response:
{
    "status": "success",
    "first_contact_id": 123,
    "decision": "raj",
    "customer_id": 45
}
```

### Get Pending First Contacts
```
GET /first-contact/pending

Response:
{
    "pending_requests": [
        {
            "id": 123,
            "customer_id": 45,
            "customer_name": "Ahmed",
            "channel": "instagram",
            "message_preview": "Hey, I saw your rings on TikTok...",
            "created_at": "2024-01-15T10:30:00",
            "reminder_sent": true
        }
    ],
    "count": 5
}
```

### Mo Takes Over Conversation
```
POST /customer/{customer_id}/override

Response:
{
    "status": "success",
    "message": "Raj paused for customer Ahmed. Auto-resume in 24 hours.",
    "override_at": "2024-01-15T10:30:00",
    "auto_resume_at": "2024-01-16T10:30:00"
}
```

### Manually Resume Raj (Before 24h Expires)
```
POST /customer/{customer_id}/resume

Response:
{
    "status": "success",
    "message": "Raj resumed for customer Ahmed"
}
```

### Get Unified Messages
```
GET /dashboard/messages?filter_by=all&limit=50

Query Parameters:
- filter_by: 'all' | 'pending' | 'raj-handled' | 'mo-handled'
- limit: number (default 50)

Response:
{
    "filter": "all",
    "total": 23,
    "messages": [
        {
            "id": 1,
            "customer_id": 45,
            "customer_name": "Ahmed",
            "channel": "instagram",
            "direction": "inbound",
            "message": "Hey, can you make a custom piece...",
            "response_by": "raj",
            "mo_override": false,
            "timestamp": "2024-01-15T10:30:00"
        }
    ]
}
```

### Get Dashboard Summary
```
GET /dashboard/summary

Response:
{
    "conversations": {
        "total": 127,
        "raj_handled": 103,
        "mo_handled": 24,
        "by_channel": {
            "instagram": 45,
            "whatsapp": 38,
            "tiktok": 22,
            "facebook": 12,
            "sms": 10
        }
    },
    "customers": {
        "total": 89,
        "personal": 8,
        "currently_overridden": 2
    },
    "pending": {
        "first_contacts": 3
    }
}
```

## Configuration

### Environment Variables
```
MO_WHATSAPP_PHONE=+1234567890          # Mo's WhatsApp for approval asks
MO_PHONE=+1234567890                    # Mo's phone for override detection
INSTAGRAM_GENERAL_TAB_ID=...           # (Advanced) Distinguish General vs DM
```

## Message Processing Flow

### New Message Arrives (Instagram DM)
```
1. Message received from @ahmed
2. Backend checks: Is @ahmed existing customer? NO
3. Backend checks: Is instagram_dm a personal channel? YES
4. Backend checks: Is customer.mo_override active? NO
5. → Create FirstContactRequest (status='pending')
6. → Send WhatsApp to Mo: "New customer Ahmed on Instagram: '...message...'"
7. → Return "awaiting_approval" status to webhook
8. → Raj does NOT respond yet
9. Mo sees pending request in dashboard
10. Mo clicks "Approve" → raj_can_respond=True for Ahmed
11. Next message from Ahmed → Raj responds normally
```

### Mo Overrides (Raj Takes Over)
```
1. Message from Ahmed (existing customer)
2. Raj processes & sends response
3. Mo replies manually to Ahmed
4. Backend detects: message from Mo's phone number
5. → Sets Customer.mo_override = True
6. → Sets override_at = now
7. → Sets auto_resume_at = now + 24h
8. Raj stops responding to Ahmed
9. After 24h, auto-resume job runs
10. → Sets mo_override = False
11. → Raj resumes responding normally
```

### Instagram General Tab (Existing Customer)
```
1. Message in Instagram General Tab from @oldcustomer
2. Backend detects: instagram + is_general_tab=True
3. Backend checks: customer has conversation history? YES
4. → Skip first-contact ask
5. → Raj auto-responds normally
```

## Personal Customers (Hands-Off)

Mark specific customers as personal (like family or close friends):

```sql
UPDATE customers SET is_personal = TRUE WHERE id = 99;
UPDATE customers SET raj_can_respond = FALSE WHERE is_personal = TRUE;
```

- Raj will never auto-respond to personal customers
- Mo must manually respond or approve each time
- Protects relationships by preventing automation

## Monitoring & Debugging

### Check Override Status
```sql
SELECT id, first_name, mo_override, override_at, auto_resume_at 
FROM customers WHERE mo_override = TRUE;
```

### Check Pending First Contacts
```sql
SELECT * FROM first_contact_requests 
WHERE status = 'pending' 
ORDER BY created_at DESC;
```

### View All FirstContactRequests
```sql
SELECT 
    fcr.id, 
    fcr.customer_id, 
    c.first_name, 
    fcr.channel, 
    fcr.status, 
    fcr.mo_decision,
    fcr.created_at
FROM first_contact_requests fcr
JOIN customers c ON c.id = fcr.customer_id
ORDER BY fcr.created_at DESC;
```

### Check Auto-Resume Job Logs
The background job logs all auto-resumes to console:
```
INFO: Auto-resumed Raj for customer Ahmed
INFO: Auto-resumed 2 customers
```

## Next Steps

1. ✅ Database schema updated with new fields
2. ✅ Message handler now implements first-contact logic
3. ✅ Override detection and auto-pause working
4. ✅ Auto-resume job running every 5 minutes
5. ✅ Dashboard endpoints for unified messages
6. 📋 **NEXT**: Voice profile interview to calibrate Mo's communication style
   - Series of 10 questions
   - Captures greeting style, formality, tone preferences
   - Updates RAJ_BASE_PERSONALITY system prompt
   - Makes responses sound more like Mo

## Integration w/ Message Handlers

When implementing channel-specific handlers (Instagram, TikTok, Facebook), pass the `is_general_tab` parameter:

```python
# Instagram DM (personal channel)
handler.process_incoming_message(
    message="Hi, can you...",
    channel='instagram',
    customer_identifier='@ahmed',
    customer_name='Ahmed',
    is_general_tab=False  # Personal DM
)

# Instagram General Tab (business channel)
handler.process_incoming_message(
    message="Hi, can you...",
    channel='instagram',
    customer_identifier='@ahmed',
    customer_name='Ahmed',
    is_general_tab=True   # Business tab
)
```

---

**Status**: ✅ Implementation Complete
**Last Updated**: 2024
**Related Files**: 
- `database/models.py` - FirstContactRequest model
- `raj_core/message_handler.py` - First-contact & override logic
- `jobs.py` - Auto-resume background job
- `main.py` - Dashboard & approval endpoints
