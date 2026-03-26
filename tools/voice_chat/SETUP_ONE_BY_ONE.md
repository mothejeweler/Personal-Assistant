# 🎯 RAJ DEPLOYMENT - ONE-BY-ONE SETUP GUIDE

**Status**: Complete step-by-step walkthrough  
**Time to Live**: ~2 hours total  
**Difficulty**: Medium (mostly copy-paste + API keys)

---

## 📍 PHASE 1: Preparation (15 minutes)

### Step 1.1: Choose Your Deployment Path

**What this means:**
- **Local Testing** = Run on your Mac (test before going live)
- **Production** = Run on cloud (AWS, DigitalOcean, etc.)

**Decision:**
- First time? → **Start with LOCAL**
- Ready to go live? → **Jump to PRODUCTION**

### Step 1.2: Check Prerequisites

Run this in terminal:

```bash
# Is Docker installed?
docker --version

# Is Docker Compose installed?
docker-compose --version

# Should see versions like:
# Docker version 20.10.21
# Docker Compose version 2.15.1
```

**If NOT installed:**
- **Mac**: Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
- **Linux**: Follow [Docker official docs](https://docs.docker.com/engine/install/)

---

## 📍 PHASE 2: Gather API Keys (30 minutes)

You'll need credentials from 4 services. **Use Claude extension to help with each one.**

### Step 2.1: Anthropic (Claude API) - **REQUIRED**

**What you need:** API Key for Claude AI

**How to get it:**

Using **Claude/Anthropic Chrome Extension**:
1. Open the extension
2. Ask: "Help me get an Anthropic API key for Raj"
3. Extension will guide you to [console.anthropic.com](https://console.anthropic.com)
4. Or follow manual steps below:

**Manual:**
1. Go to [console.anthropic.com](https://console.anthropic.com/account/keys)
2. Sign in (create account if needed)
3. Click "Create Key"
4. Name it: `raj_production`
5. Copy the key (it starts with `sk-ant-`)
6. **Save to notepad temporarily** (we'll add to .env later)

**Expected format:**
```
sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

---

### Step 2.2: Twilio (WhatsApp/SMS) - **REQUIRED**

**What you need:** Account SID, Auth Token, Phone Number

**How to get it:**

Using **Claude/Anthropic Chrome Extension**:
1. Ask: "Help me set up Twilio for WhatsApp and SMS"
2. Extension will guide you through account setup
3. Or follow manual steps:

**Manual:**
1. Go to [twilio.com](https://www.twilio.com/console)
2. Sign up (free trial: $15 credit)
3. Verify phone number
4. Go to **Console** (dashboard)
5. Copy these three values:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (long string at top)
   - **Get a Twilio Phone** (Phone Numbers → Buy → Search → Choose)
6. Save all three

**Expected format:**
```
Account SID: ACxxxxxxxxxxxxxxxxxxxxxxx
Auth Token: your_long_token_here
Phone: +1234567890
```

---

### Step 2.3: Instagram Business API - **REQUIRED FOR INSTAGRAM**

**What you need:** Access Token, Business Account ID

**How to get it:**

Using **Claude/Anthropic Chrome Extension**:
1. Ask: "Help me set up Instagram Graph API for Raj"
2. Extension will guide through Facebook Developers
3. Or follow manual steps:

**Manual:**
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create App (if not existing)
3. Add "Instagram Basic Display" product
4. Go to Settings → Basic → Copy **App ID** and **App Secret**
5. Go to Tools → Graph API Explorer
6. Get **Access Token** (short-lived → convert to long-lived)
7. Find your **Instagram Business Account ID**

**Expected format:**
```
Access Token: IGQVR...xxx...
Business Account ID: 1234567890
```

---

### Step 2.4: Your Contact Info - **REQUIRED**

**What you need:** Your WhatsApp and phone numbers (for approvals/overrides)

**How to get it:**
Just use your actual numbers!

**Expected format:**
```
MO_WHATSAPP_PHONE: +1 (your country code) (your phone)
MO_PHONE: +1 (same number usually)
```

---

## 📍 PHASE 3: Prepare Configuration (10 minutes)

### Step 3.1: Create .env File

**What this is:** A file with all your secrets (API keys, passwords, etc.)

**How to create it using Claude extension:**

1. Open Claude extension
2. Ask: "Create a .env file for Raj with placeholders for: Anthropic key, Twilio credentials, Instagram, database password, my phone number"
3. Extension will generate template
4. Copy the template
5. On your Mac, open Terminal and run:

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Open text editor to create .env
nano .env
```

6. Paste the template from extension
7. Replace `PLACEHOLDER` values with your actual credentials:

```bash
# Example (with REAL values):
ANTHROPIC_API_KEY=sk-ant-abc123def456...
TWILIO_ACCOUNT_SID=ACxxxxxxxx...
TWILIO_AUTH_TOKEN=your_long_token...
TWILIO_PHONE=+18005551234
INSTAGRAM_ACCESS_TOKEN=IGQVR...
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000
MO_WHATSAPP_PHONE=+1234567890
MO_PHONE=+1234567890

# Database (leave these for local dev)
DB_USER=mo
DB_PASSWORD=my_secure_password_123
DB_NAME=raj_db
REDIS_PORT=6379
```

8. Save file (Ctrl+O, Enter, Ctrl+X in nano)

---

### Step 3.2: Verify .env File Created

```bash
# Check if file exists
ls -la .env

# Should show: -rw-r--r--  1 user  staff  1234 Mar 25 10:30 .env
```

---

## 📍 PHASE 4: Start Raj (Local Testing) - 15 minutes

### Step 4.1: Navigate to Raj Directory

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Verify you're in right place
pwd

# Should end with: /tools/voice_chat
```

---

### Step 4.2: Build and Start All Services

```bash
# Download/build all Docker images and start services
docker-compose up -d

# Wait 30-60 seconds for services to initialize
sleep 45

# Check if all services are healthy
docker-compose ps
```

**You should see:**
```
CONTAINER ID   NAMES                 STATUS           PORTS
xxxxx          raj_postgres          Up (healthy)     0.0.0.0:5432->5432/tcp
xxxxx          raj_redis            Up (healthy)     0.0.0.0:6379->6379/tcp
xxxxx          raj_server_1         Up (healthy)     0.0.0.0:8001->8001/tcp
xxxxx          raj_server_2         Up (healthy)     0.0.0.0:8002->8002/tcp
xxxxx          raj_scheduler        Up               (no ports)
xxxxx          raj_nginx            Up (healthy)     0.0.0.0:80->80/tcp
```

---

### Step 4.3: Verify Raj is Working

```bash
# Health check (should return 200 OK with JSON)
curl http://localhost/health

# Should see:
# {"status":"online","timestamp":"2026-03-25T10:30:45.123456","version":"1.0.0"}
```

✅ **Good!** Raj is running.

---

### Step 4.4: Test Message Flow

```bash
# Send a test WhatsApp message
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "from": "+1234567890",
    "message": "Hey interested in custom piece",
    "customer_name": "Ahmed"
  }'
```

**Expected response:**
```json
{
  "status": "success",
  "customer_id": 1,
  "response": "Hey what's up Ahmed...",
  "channel": "whatsapp",
  "queued_message_id": 1,
  "urgency": false,
  "consecutive_count": 1,
  "delay_info": "Queued with 145s delay (human-like response time)"
}
```

✅ **Perfect!** Message was queued for delayed sending.

---

### Step 4.5: Wait for Message to Send

```bash
# Messages send after 1-5 minutes randomly
# Wait 5 minutes, then check if it was sent

# Check message queue status
docker exec -it raj_postgres psql -U mo -d raj_db -c "SELECT id, status, sent_at FROM message_queue ORDER BY created_at DESC LIMIT 1;"

# Should eventually show:
# id | status | sent_at
# 1  | sent   | 2026-03-25 10:35:45
```

---

### Step 4.6: View Logs (See What's Happening)

```bash
# Real-time logs from all services
docker-compose logs -f

# Logs show: message processing, job runs, etc.
# Press Ctrl+C to stop
```

---

## 📍 PHASE 5: Test Advanced Features (Optional, 15 minutes)

### Step 5.1: Test First-Contact Approval

```bash
# Send message from NEW customer (first time)
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "instagram",
    "from": "@newcustomer",
    "message": "Saw your work on TikTok!",
    "customer_name": "Jane"
  }'

# Response should show:
# "status": "awaiting_approval"

# Raj sends you a WhatsApp asking for approval
# Check /first-contact/pending endpoint:
curl http://localhost/first-contact/pending
```

---

### Step 5.2: Test Dashboard

```bash
# Get all messages across all channels
curl http://localhost/dashboard/messages

# Get summary (stats)
curl http://localhost/dashboard/summary
```

---

## 📍 PHASE 6: Stop Services (Clean Up)

```bash
# Stop all services (keeps data)
docker-compose down

# Stop and DELETE all data (fresh slate)
docker-compose down -v
```

---

## 📍 PHASE 7: Deploy to Production (If Ready)

### When to deploy:
- ✅ Local testing works
- ✅ All API keys configured
- ✅ Ready for real customers
- ✅ Want high availability (2 servers)

### Options:

**Option A: AWS EC2 (Recommended)**
See DEPLOYMENT_GUIDE.md → "Production Deployment (Cloud)" → "Option A: AWS EC2 + RDS"

**Option B: DigitalOcean (Simplest)**
See DEPLOYMENT_GUIDE.md → "Option B: DigitalOcean App Platform"

**Option C: Your Own Server**
See DEPLOYMENT_GUIDE.md → Full instructions

---

## 🆘 Troubleshooting

### Issue: Docker command not found

```bash
# Docker not installed
# Install: docker.com/products/docker-desktop

# Or check if it's running
docker info
```

### Issue: Containers won't start

```bash
# Check why
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose up -d
```

### Issue: Health check failing

```bash
# Wait longer (sometimes takes 60 seconds)
sleep 30
docker-compose ps

# Or check logs
docker-compose logs postgres
```

### Issue: Port already in use

```bash
# Something else using port 80
# Find what's using it
lsof -i :80

# Kill it, or change port in docker-compose.yml
```

---

## ✅ Success Criteria

- [ ] .env file created with all API keys
- [ ] `docker-compose ps` shows 6 services
- [ ] `curl http://localhost/health` returns 200
- [ ] Test message sent successfully
- [ ] Message appeared after 1-5 minute delay
- [ ] First-contact approval works
- [ ] Dashboard shows messages

**If all checked:** ✅ **Raj is ready!**

---

## 📞 Next Steps

1. **If testing locally**: Play with API endpoints, test different scenarios
2. **If going to production**: Choose platform (AWS/DigitalOcean) and follow deployment guide
3. **If something breaks**: Check troubleshooting section or ask Claude extension for help

---

**Questions?** Ask Claude extension or check logs with: `docker-compose logs -f`
