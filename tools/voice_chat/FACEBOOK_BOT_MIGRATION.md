# 🔗 FACEBOOK BOT MIGRATION & CONSOLIDATION

**Goal:** Connect your existing Facebook bot to Raj (or replace it)  
**Timeline:** ~15 minutes to assess + 30 minutes to migrate  
**Difficulty:** Medium (requires Facebook credentials)

---

## 📍 PART A: Check What You Already Have

### Step A.1: Inventory Your Current Setup

**First, answer these questions:**

- ✓ Do you have a Facebook bot running right now?
- ✓ Where is it hosted? (You could, AWS, local machine, etc.)
- ✓ What does it do? (Auto-responder, appointment booking, etc.)
- ✓ How many customers use it monthly?
- ✓ Do you have Facebook Page credentials?

### Step A.2: Check Your Facebook Pages

Go to [facebook.com/manage](https://facebook.com/manage):

1. Find your business page (should be "Saif Jewelers" or similar)
2. Check if it has a **Messenger bot** active
3. Go to **Settings → Messenger → Connected Apps**
4. Note what's connected:
   - Is it running on Zapier? (cloud service)
   - Is it running on your own server?
   - Is it third-party app? (ManyChat, etc.)

### Step A.3: Find Existing Bot Credentials

**Look for:**

```bash
# In your files or notes, find:
- Facebook App ID
- Facebook App Secret
- Facebook Page Access Token
- Webhook URL (where messages go)
- Webhook Verify Token
```

**If you don't have these:**

Using **Claude extension:**

```
"I have a Facebook Messenger bot. Where do I find:
- Facebook App ID
- Facebook App Secret
- Page Access Token
- Webhook URL it's using

I have admin access to the page."
```

---

## 📍 PART B: Three Integration Options

### Option 1: Migrate to Raj ⭐ (RECOMMENDED)
- **What it is:** Replace your old bot with Raj completely
- **Pros:** Single system, one maintenance point, consistent voice
- **Cons:** Need to reconfigure credentials
- **Time:** 30 minutes
- **Customers impact:** None (seamless handoff)

### Option 2: Run in Parallel
- **What it is:** Keep old bot, add Raj alongside
- **Pros:** Safe fallback, test without risk
- **Cons:** Redundant, confusing if both respond
- **Time:** 15 minutes setup
- **Customers impact:** Might get double responses

### Option 3: Hybrid (ADVANCED)
- **What it is:** Use old bot for automation, Raj for intelligent responses
- **Pros:** Best of both worlds
- **Cons:** Complex setup
- **Time:** 1-2 hours
- **Customers impact:** Seamless upgrade

**Decision:**
- **First time using Raj?** → **Option 1 (Migrate)**
- **Want to test first?** → **Option 2 (Parallel)**
- **Have complex workflows?** → **Option 3 (Hybrid)**

---

## 📍 PART C: Option 1 - Full Migration (RECOMMENDED)

**This: Disconnects your old bot and connects Raj instead**

### Step C.1: Get Facebook Credentials

Using **Claude extension:**

```
"Help me collect my Facebook bot credentials for migration.
I need to find these from my Facebook Page settings:
- Facebook App ID
- Facebook App Secret
- Page Access Token

Walk me through the Facebook Developers console."
```

**Manual process:**

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Select your app (or create new)
3. Go to **Settings → Basic**
4. Copy:
   - **App ID**: Large number at top
   - **App Secret**: Button says "Show" (don't share!)
5. Go to **Messenger → Settings**
6. Scroll to "Access Tokens"
7. Find your page name (e.g., "Saif Jewelers")
8. Copy the **Page Access Token** (starts with `EAA...`)

### Step C.2: Update Raj Configuration

**Edit your .env file:**

```bash
nano ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat/.env
```

**Find or add these lines:**

```bash
# Facebook credentials (from Step C.1)
FACEBOOK_APP_ID=123456789
FACEBOOK_APP_SECRET=your_app_secret_here
FACEBOOK_PAGE_ACCESS_TOKEN=EAA...very_long_token...
FACEBOOK_BUSINESS_ACCOUNT_ID=123456789

# Your page details
FACEBOOK_PAGE_ID=987654321
FACEBOOK_PAGE_NAME=Saif Jewelers
```

**Save file:** Ctrl+O, Enter, Ctrl+X

### Step C.3: Update Raj Code for Facebook

**File to edit:** `integrations/facebook_messenger.py`

In terminal:

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Check if Facebook messenger file exists
ls integrations/facebook*

# Should show: facebook_messenger.py (if not, we'll create it)
```

**If file doesn't exist, create it:**

Using **Claude extension:**

```
"Create a Facebook Messenger integration for Raj. Requirements:
- Receives messages from Facebook Messenger webhook
- Sends responses back via Facebook API
- Handles first-name mentions
- Rate limits (100 messages/sec max)
- Format: Python class FacebookMessenger with methods:
  - send_message(recipient_id, message)
  - receive_webhook(payload)
  - parse_incoming_message(payload)

Framework: Python, requests library, FastAPI compatible."
```

Copy the generated code and save to:
```
integrations/facebook_messenger.py
```

### Step C.4: Add Facebook Endpoint to Raj API

**File to edit:** `main.py`

Find this section:

```python
@app.post("/message/incoming")
async def handle_incoming_message(request: dict):
    # Current code handles WhatsApp, Instagram, etc.
```

Add Facebook endpoint:

```python
@app.post("/webhook/facebook")
async def handle_facebook_webhook(request: dict):
    """Webhook for Facebook Messenger"""
    from integrations.facebook_messenger import FacebookMessenger
    
    messenger = FacebookMessenger()
    
    # Verify webhook token
    challenge = request.get("hub.challenge")
    if challenge:
        return {"hub.challenge": challenge}
    
    # Process messages
    for entry in request.get("entry", []):
        for message_event in entry.get("messaging", []):
            if "message" in message_event:
                # Extract message
                sender_id = message_event["sender"]["id"]
                message = message_event["message"].get("text", "")
                
                # Process through Raj
                response = await handle_incoming_message({
                    "channel": "facebook",
                    "from": sender_id,
                    "message": message,
                    "customer_name": "Facebook User"  # Lookup from DB if needed
                })
                
                # Send response back
                await messenger.send_message(sender_id, response["response"])
    
    return {"status": "ok"}
```

### Step C.5: Configure Facebook Webhook

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Select your app
3. Go to **Messenger → Settings**
4. Find "Webhooks" section
5. Click **Edit Settings**
6. Enter:
   - **Callback URL**: `https://your-domain.com/webhook/facebook`
   - **Verify Token**: Create one (e.g., `my_facebook_webhook_token_123`)
   - **Subscribe to Webhook Fields**: ✓ message_deliveries ✓ messages ✓ messaging_postbacks

### Step C.6: Restart Raj with Facebook

```bash
# Stop current services
docker-compose down

# Start again
docker-compose up -d

# Wait 30 seconds
sleep 30

# Check if running
curl http://localhost/health
```

### Step C.7: Test Facebook Messages

**Send a test message via Facebook Messenger:**

1. From a different Facebook account, send message to your page
2. Should receive Raj's response within 1-5 minutes (with delay)
3. Check logs:

```bash
docker-compose logs -f raj_server_1
# Should see: "Processing Facebook message from [user] ..."
```

**Success!** ✅ Your Facebook bot is now Raj

---

## 📍 PART D: Option 2 - Run in Parallel (SAFE TEST)

**This keeps your old bot, adds Raj alongside**

**How it works:**
1. Your old bot runs on its current URL
2. Raj runs on new URL (e.g., new server)
3. Facebook NOT routed to Raj yet (just testing)
4. Send test messages directly to Raj endpoint

### Step D.1: Set up Raj without Facebook change

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Configure .env with Facebook creds (but don't activate webhook yet)
nano .env
# Add Facebook credentials

# Start Raj
docker-compose up -d

# Test locally with curl
curl -X POST http://localhost/webhook/facebook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "messaging": [{
        "sender": {"id": "123456789"},
        "message": {"text": "Hey, interested in custom ring"}
      }]
    }]
  }'
```

### Step D.2: Monitor Both Systems

```bash
# Watch Raj logs
docker-compose logs -f raj_server_1

# Separately: Monitor your old bot
# (Depends on where it's hosted)
```

### Step D.3: When Ready to Switch

Once Raj is working well:

```bash
# Follow Option 1 steps: Update Facebook webhook to point to Raj
# This deactivates old bot, activates Raj
```

---

## 📍 PART E: Option 3 - Hybrid Setup (ADVANCED)

**This uses old bot for simple tasks, Raj for complex ones**

### Step E.1: Architecture Overview

```
Customer Message (Facebook)
         ↓
    Old Bot (Fast)
         ↓
    Is it a FAQ? → Answer immediately
    Is it a booking? → Create appointment
    Is it complex? → Forward to Raj
         ↓
    Raj (AI)
         ↓
    Generates intelligent response
         ↓
    Send via old bot to customer
```

### Step E.2: Configure Message Routing

This requires your old bot to have **conditional logic**:

```
If message contains: "custom", "design", "looks like"
  → Route to Raj AI endpoint
  
Else if message contains: "appointment", "book", "when"
  → Auto-book logic
  
Else
  → Simple FAQ response
```

Using **Claude extension to help:**

```
"I have an existing Facebook bot and want to add AI responses for complex inquiries.

My bot currently handles:
- FAQ responses (fast)
- Appointment booking (automated)

And I want to add:
- Design consultations (complex, needs AI)
- Custom piece inquiries (needs AI)
- Pricing questions (needs AI)

Help me set up conditional routing where complex messages go to Raj API."
```

*This approach is complex - only if you have high-volume AND specific automation needs.*

---

## 📍 PART F: Data Migration (IF NEEDED)

### If Your Old Bot Stored Customer Data

**Move conversation history:**

```bash
# Export old bot data (format depends on old bot)
# 1. Download conversations CSV/JSON
# 2. Map to Raj database schema
# 3. Import:

docker exec -it raj_postgres psql -U mo -d raj_db << EOF
COPY conversations FROM '/tmp/old_conversations.csv' WITH CSV HEADER;
EOF
```

Using **Claude extension:**

```
"Help me migrate customer data from [OLD BOT] to Raj.

Old bot format:
[PASTE SAMPLE DATA]

Raj expects:
- customer_id (numeric)
- channel (text)
- from (phone/ID)
- message (text)
- created_at (timestamp)

How do I map and import?"
```

---

## 🤖 Using Claude Extension for Facebook Setup

### Command 1: Credential Collection

```
"Help me collect Facebook Bot credentials for migration.
Step-by-step, show me where to find:
- Facebook App ID
- Facebook App Secret  
- Page Access Token
I have Instagram Business account set up already."
```

### Command 2: Facebook Messenger Class

```
"Create a FacebookMessenger Python class with methods:
- send_message(recipient_id, text)
- receive_webhook(payload) -> dict
- verify_token(token) -> bool
Format: class-based, use requests library, include error handling"
```

### Command 3: Webhook Configuration

```
"I'm setting up a webhook for Facebook Messenger bot.

My app is deployed at: https://raj.example.com
Webhook endpoint: /webhook/facebook
Webhook token: my_secret_token_123

Give me exact steps to configure in Facebook Developers console."
```

### Command 4: Debug Facebook Issues

```
"Facebook Messages not coming through to my bot.

Current setup:
- Endpoint: [URL]
- Status: [shows error]

Debug checklist (tell me what to check):
1. [item]
2. [item]
3. [item]
..."
```

---

## ✅ Success Criteria (Choose One)

**If Option 1 (Full Migration):**
- [ ] Facebook credentials found
- [ ] Raj updated with Facebook config
- [ ] Webhook endpoint created
- [ ] Facebook webhook pointing to Raj
- [ ] Test message received and responded
- [ ] Old bot disabled

**If Option 2 (Parallel):**
- [ ] Raj running independently
- [ ] Can send test Facebook messages locally
- [ ] Old bot still running
- [ ] Ready when you decide to switch

**If Option 3 (Hybrid):**
- [ ] Old bot has conditional routing
- [ ] Raj endpoint accessible
- [ ] Complex messages route to Raj
- [ ] Simple messages still auto-respond

---

## 📞 Troubleshooting Facebook Integration

### Issue: Webhook not receiving messages

```bash
# 1. Check if endpoint is accessible
curl https://your-domain.com/webhook/facebook

# 2. Verify webhook configured in Facebook
# Go to: developers.facebook.com → Messenger → Settings → Webhooks

# 3. Check if token matches
echo "Token in .env: $(grep FACEBOOK_WEBHOOK_VERIFY_TOKEN .env)"
```

### Issue: Response not sending back

```bash
# 1. Check if Page Access Token valid
curl -X GET "https://graph.facebook.com/me?access_token=YOUR_TOKEN"

# 2. Check Raj logs
docker-compose logs raj_server_1 | grep "facebook"

# 3. Manually test sending
curl -X POST "https://graph.facebook.com/me/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": {"id": "CUSTOMER_ID"},
    "message": {"text": "Test message"}
  }' \
  -d "access_token=YOUR_PAGE_TOKEN"
```

### Issue: Old bot and Raj both responding

```bash
# Immediately disable old bot webhook:
# 1. Go to: developers.facebook.com
# 2. Find old app/webhook
# 3. Either disable or delete webhook
# 4. Or change its callback URL to dummy endpoint
```

---

## 🎯 NEXT STEPS

1. **Decide:** (Option 1, 2, or 3)
2. **Gather:** Facebook credentials
3. **Update:** .env file + code
4. **Test:** Send test message via Facebook
5. **Monitor:** Check logs for errors
6. **Celebrate:** Your Facebook bot is now powered by Raj! 🎉

**Need help?** Use Claude extension commands above or check:
- SETUP_ONE_BY_ONE.md (general setup)
- DEPLOYMENT_GUIDE.md (server issues)
- CLAUDE_EXTENSION_GUIDES.md (when stuck)
