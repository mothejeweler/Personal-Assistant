# 🚀 Raj Backend — Quick Start (5 Minutes)

## Copy-Paste These Commands

### Step 1: Navigate to Backend

```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend"
```

### Step 2: Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Set Up PostgreSQL

#### If you don't have PostgreSQL installed:
```bash
brew install postgresql
brew services start postgresql
```

#### Create database:
```bash
psql postgres

# Paste these commands:
CREATE USER mo WITH PASSWORD 'rajpassword123';
CREATE DATABASE raj_db OWNER mo;
GRANT ALL PRIVILEGES ON DATABASE raj_db TO mo;
\q
```

### Step 4: Initialize Database

```bash
psql -U mo -d raj_db -f database/schema.sql
```

### Step 5: Create .env File

```bash
cp .env.example .env

# Open and fill in your API keys:
nano .env
```

**Minimum values needed:**
```env
CLAUDE_API_KEY=sk-ant-xxxxx (get from console.anthropic.com)
DATABASE_URL=postgresql://mo:rajpassword123@localhost:5432/raj_db
SHOPIFY_STORE_URL=saifjewelers.com
SHOPIFY_API_KEY=your_key
SHOPIFY_ACCESS_TOKEN=your_token
TAVILY_API_KEY=tvly-xxxxx
```

### Step 6: Start Backend

```bash
python main.py
```

You should see:
```
🚀 Raj Backend starting...
✅ Database initialized
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 7: In Another Terminal - Start Jobs Scheduler

```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend"
source venv/bin/activate
python jobs.py
```

---

## Test It Works

```bash
# In a third terminal:
curl http://localhost:8000/health
```

Should print:
```json
{"status":"online"}
```

---

## Send Your First Message

```bash
curl -X POST http://localhost:8000/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "from": "+1234567890",
    "message": "I want a custom burst diamond piece",
    "customer_name": "Jamie"
  }'
```

Raj should respond with something like:
```json
{
  "status": "success",
  "response": "Yo burst designs are going crazy right now, especially in the hip hop space...",
  "channel": "web"
}
```

---

## Next: Get Your API Keys

| Service | Link | Time |
|---------|------|------|
| Claude | https://console.anthropic.com | 2 min |
| Shopify | https://saifjewelers.myshopify.com/admin/apps | 3 min |
| Twilio | https://www.twilio.com | 5 min |
| Tavily | https://tavily.com | 2 min |

---

## Troubleshooting

**"postgresql: command not found"**
→ `brew install postgresql`

**"Port 8000 already in use"**
→ `lsof -i :8000` then `kill -9 <PID>`

**"FATAL: password authentication failed"**
→ Check password in `.env` matches database creation

**"No module named 'database'"**
→ Make sure you ran `source venv/bin/activate`

---

**That's it!** Raj is now running. Bookmark the [full README](./README.md) for detailed setup.

Next: Check [PROGRESS_TRACKER.md](./PROGRESS_TRACKER.md) to stay on track. ✅
