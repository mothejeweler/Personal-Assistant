# Raj Backend — Complete Setup Guide

## What is This?

Raj's backend infrastructure that turns the voice assistant into a **proactive, always-watching business automation system**.

**Capabilities:**
- ✅ Multi-channel messaging (WhatsApp, Instagram, SMS, web)
- ✅ Deep customer context (purchase history, preferences, intent scoring)
- ✅ Real-time trend monitoring (hip hop jewelry, viral trends)
- ✅ Inventory alerts (low stock, reorder notifications)
- ✅ DM analysis (intent detection, lead scoring)
- ✅ Proactive monitoring (hourly trends, daily standups)

---

## Prerequisites

**System Requirements:**
- macOS (Monterey or later)
- Python 3.9+
- PostgreSQL (local or cloud)

**APIs Required:**
- Claude API key (Anthropic)
- Shopify API credentials
- Twilio account (for WhatsApp/SMS)
- Instagram Business Account (for DMs)
- Tavily API key (for trend searches)

**Accounts:**
- Shopify store: `saifjewelers.com`
- Instagram Business: `saifjewelers`

---

## STEP 1: Set Up PostgreSQL Database

### Option A: PostgreSQL via Homebrew (Easiest)

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Create database and user
psql postgres

# In PostgreSQL terminal:
CREATE USER mo WITH PASSWORD 'change_this_password';
CREATE DATABASE raj_db OWNER mo;
GRANT ALL PRIVILEGES ON DATABASE raj_db TO mo;
\q
```

### Option B: Docker (Alternative)

```bash
docker run --name raj-postgres \
  -e POSTGRES_USER=mo \
  -e POSTGRES_PASSWORD=change_this_password \
  -e POSTGRES_DB=raj_db \
  -p 5432:5432 \
  -d postgres:15
```

### Verify Connection

```bash
psql -U mo -d raj_db -h localhost
```

---

## STEP 2: Clone Backend & Install Dependencies

```bash
# Navigate to voice_chat directory
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend"

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## STEP 3: Configure Environment Variables

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Fill in these values:**

```env
# API Keys
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx

# Database (change password from default)
DATABASE_URL=postgresql://mo:YOUR_PASSWORD@localhost:5432/raj_db
POSTGRES_USER=mo
POSTGRES_PASSWORD=YOUR_PASSWORD
POSTGRES_DB=raj_db

# Shopify
SHOPIFY_STORE_URL=saifjewelers.com
SHOPIFY_API_KEY=your_api_key
SHOPIFY_ACCESS_TOKEN=your_access_token

# Instagram
INSTAGRAM_USERNAME=saifjewelers
INSTAGRAM_PASSWORD=your_password
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id

# Twilio (WhatsApp + SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+1234567890
TWILIO_SMS_FROM=+1234567890

# Backend
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
ENVIRONMENT=development

# Mo's Contact
MO_WHATSAPP=whatsapp:+1234567890
MO_PHONE=+1234567890
```

**Getting API Keys:**

### Claude API
1. Go to https://console.anthropic.com
2. Create account / sign in
3. Generate API key
4. Paste in `.env`

### Shopify
1. Go to Shopify admin: https://saifjewelers.myshopify.com/admin
2. Settings → Apps & Integrations → Develop Apps
3. Create custom app
4. Generate API credentials
5. Copy into `.env`

### Twilio
1. Go to https://www.twilio.com
2. Create account
3. Get trial credentials
4. Add WhatsApp number (free trial includes $15 credit)
5. Copy SID, Auth Token, number into `.env`

### Instagram
1. Convert to Business Account: https://help.instagram.com/502981923235522
2. Get Business Account ID from Instagram Graph API
3. Create app at Meta Developer Console

### Tavily
1. Go to https://tavily.com
2. Sign up for API access
3. Get API key

---

## STEP 4: Initialize Database

```bash
# Create all tables from schema
psql -U mo -d raj_db -f database/schema.sql

# Verify tables were created
psql -U mo -d raj_db -c "\dt"
```

---

## STEP 5: Start the Backend

### Terminal 1: Main API Server

```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend"
source venv/bin/activate
python main.py
```

You should see:
```
🚀 Raj Backend starting...
✅ Database initialized
INFO:     Application startup complete [press enter to quit]
```

### Terminal 2: Background Job Scheduler

```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend"
source venv/bin/activate
python jobs.py
```

You should see:
```
🚀 Background scheduler started with 4 monitoring jobs
```

---

## STEP 6: Test the System

### Test API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "online",
  "timestamp": "2024-03-25T14:30:00.123456",
  "version": "1.0.0"
}
```

### Test Incoming Message

```bash
curl -X POST http://localhost:8000/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "from": "customer123",
    "message": "I want a custom burst diamond design",
    "customer_name": "Jamie"
  }'
```

Expected response:
```json
{
  "status": "success",
  "response": "Yo, burst designs are going crazy right now...",
  "channel": "web"
}
```

### Get Daily Standup

```bash
curl http://localhost:8000/status/standup
```

### Get Current Trends

```bash
curl http://localhost:8000/trends/current
```

---

## What's Running Now?

### API Endpoints (Main Server)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check backend status |
| `/message/incoming` | POST | Receive incoming messages |
| `/message/send` | POST | Send outgoing messages |
| `/customer/{id}` | GET | Get customer context |
| `/status/standup` | GET | Get daily briefing |
| `/trends/current` | GET | Get trending topics |
| `/inventory/status` | GET | Get inventory alerts |

### Background Jobs (Scheduler)

| Job | Schedule | Purpose |
|-----|----------|---------|
| Trend Monitor | Every hour | Check TikTok/Instagram trends |
| Inventory Monitor | Every 2 hours | Check stock levels |
| DM Monitor | Every 30 min | Analyze incoming messages |
| Morning Standup | 8 AM daily | Send Mo a briefing |

---

## Next Steps

### Week 1 Checkpoint (By Friday, March 31)

- [ ] Verify all APIs working (check `.env`)
- [ ] Database tables created and accessible
- [ ] Backend running stably for 24+ hours
- [ ] First customer messages logged
- [ ] Trends being monitored
- [ ] Inventory sync working

### What to Monitor

1. **Check logs regularly:**
   ```bash
   tail -f backend.log  # API server logs
   ```

2. **Database health:**
   ```bash
   psql -U mo -d raj_db -c "SELECT COUNT(*) FROM conversations;"
   ```

3. **Active jobs:**
   ```bash
   curl http://localhost:8000/jobs/monitor/trends
   curl http://localhost:8000/jobs/monitor/inventory
   curl http://localhost:8000/jobs/monitor/dms
   ```

---

## Troubleshooting

### Database Connection Failed
```
Error: could not translate host name "localhost" to address
```
**Fix:** Make sure PostgreSQL is running
```bash
brew services start postgresql
psql -U mo -d raj_db  # Test connection
```

### Port 8000 Already in Use
```bash
lsof -i :8000
kill -9 <PID>
```

### Missing API Keys
```
Error: CLAUDE_API_KEY not set
```
**Fix:** Verify `.env` file has all values and no typos

### No Data in Database
```bash
psql -U mo -d raj_db -c "SELECT * FROM conversations LIMIT 5;"
```
If empty, check that `/message/incoming` endpoint is being called

---

## Architecture Overview

```
Frontend (Browser)           Backend (Python/FastAPI)        Database (PostgreSQL)
   ↓                              ↓                                 ↓
index.html (Voice)      →  main.py (API Server)      →     raj_db (all data)
                        ↓
                    raj_core/
                    ├─ context_engine.py (intelligence)
                    ├─ message_handler.py (responses)
                    └─ personality.py (system prompt)
                        ↓
                    monitors/ (background jobs)
                    ├─ trend_monitor.py (hourly)
                    ├─ inventory_monitor.py (2hr)
                    └─ dm_monitor.py (30min)
                        ↓
                    integrations/
                    ├─ shopify_sync.py
                    ├─ twilio_handler.py (WhatsApp/SMS)
                    └─ instagram_connector.py
```

---

## Support & Issues

If something breaks:

1. Check `.env` values (most common issue)
2. Verify PostgreSQL is running
3. Check API logs for error messages
4. Test individual endpoints with `curl`
5. Review database directly with `psql`

---

**You're all set! Raj is now running 24/7, watching trends, analyzing DMs, and getting ready to help scale Saif Jewelers.** 🚀
