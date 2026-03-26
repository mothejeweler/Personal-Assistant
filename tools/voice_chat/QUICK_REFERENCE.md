# RAJ QUICK REFERENCE CARD
**Print this or save as PDF**

---

## 🎯 THE BIG PICTURE

**Raj = 24/7 AI assistant for your jewelry business**
- Responds on WhatsApp, Instagram, SMS, Facebook, TikTok
- Sounds like YOU (learns from your videos)
- Handles customer questions automatically
- You can override any time (24h auto-resume)
- Respects human-like delays (1-5 min random)

---

## ✅ QUICK START (30 minutes)

```bash
# 1. Create .env file with API keys
nano .env

# 2. Start all services
docker-compose up -d

# 3. Verify health
curl http://localhost/health

# 4. Send test message
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{"channel":"whatsapp","from":"+1234567890","message":"Hey"}'

# 5. Check logs
docker-compose logs -f
```

---

## 📋 REQUIRED API KEYS

| Service | What You Get | Where |
|---------|--------------|-------|
| **Anthropic** | API Key `sk-ant-...` | console.anthropic.com |
| **Twilio** | Account SID, Auth Token, Phone | twilio.com/console |
| **Instagram** | Access Token, Business Account ID | developers.facebook.com |
| **Your Contact** | Phone number for approvals | Just use your own! |

**Use Claude extension to get them** → CLAUDE_EXTENSION_GUIDES.md

---

## 🎥 MAKE RAJ SOUND LIKE YOU (30 min)

1. Gather 5-10 videos of yourself
2. Ask Claude extension: "Analyze my jewelry videos"
3. Create RAJ_STYLE_PROFILE.md with extracted style
4. Update `personality.py` with new voice
5. Restart: `docker-compose restart`
6. Test: Send messages, verify tone

**Full steps:** VIDEO_ANALYSIS_AND_VOICE.md

---

## 🔗 CONNECT FACEBOOK BOT (30 min)

1. Find your existing bot credentials
2. Add to .env:
   ```
   FACEBOOK_APP_ID=xxx
   FACEBOOK_APP_SECRET=xxx
   FACEBOOK_PAGE_ACCESS_TOKEN=xxx
   ```
3. Update webhook in Facebook → Point to Raj
4. Test: Send message in Facebook Messenger
5. Verify in logs

**3 options (full swap/parallel/hybrid):** FACEBOOK_BOT_MIGRATION.md

---

## 📁 IMPORTANT FILES

| File | Purpose | When |
|------|---------|------|
| `.env` | Your secrets | Before starting |
| `personality.py` | Raj's voice | After video analysis |
| `docker-compose.yml` | Start/stop all | Every time |
| `requirements.txt` | Dependencies | Rarely changed |

---

## 💻 COMMON COMMANDS

```bash
# Start Raj
docker-compose up -d

# Stop Raj
docker-compose down

# Full restart
docker-compose down && docker-compose up -d

# Check health
curl http://localhost/health

# View logs (real-time)
docker-compose logs -f

# View specific service
docker-compose logs -f raj_server_1

# Restart one service
docker-compose restart raj_server_1

# Stop services (keep data)
docker-compose down

# Stop + DELETE DATA (fresh start)
docker-compose down -v
```

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Services won't start | `docker-compose logs` to see why |
| Port already in use | Change port in docker-compose.yml |
| Messages not sending | Check Twilio creds in .env |
| Raj not responding | Verify health: `curl http://localhost/health` |
| Facebook not connected | Webhook URL must be https + publicly accessible |
| Still stuck? | Ask Claude extension + check CLAUDE_EXTENSION_GUIDES.md |

---

## 🚀 DEPLOYMENT TO PRODUCTION

```bash
# Choose platform:
AWS EC2        → See DEPLOYMENT_GUIDE.md
DigitalOcean   → Simplest option
Your own server → Most control

# Then:
1. Create .env with real credentials
2. docker-compose up -d
3. Configure SSL
4. Point domain
5. Enable webhooks
6. Monitor logs daily
```

---

## 📞 HELP ROUTES

| Need | Go To |
|------|-------|
| General setup | SETUP_ONE_BY_ONE.md |
| Video training | VIDEO_ANALYSIS_AND_VOICE.md |
| Facebook | FACEBOOK_BOT_MIGRATION.md |
| Claude extension | CLAUDE_EXTENSION_GUIDES.md |
| Production | DEPLOYMENT_GUIDE.md |
| Stuck? | README_MASTER_GUIDE.md |

---

## ⚡ CLAUDE EXTENSION COMMANDS

**Copy-paste these as needed:**

### Get API Key
```
"Help me get an Anthropic API key"
```

### Analyze Videos
```
"Analyze these jewelry videos to extract: design style, communication tone, signature phrases"
```

### Create .env
```
"Create .env template with: Anthropic, Twilio, Instagram, database credentials"
```

### Get Facebook Credentials
```
"Help me collect my Facebook Page Access Token and App Secret"
```

### Debug Errors
```
"I got this error: [PASTE ERROR]. Help me fix it."
```

---

## 📊 STATUS INDICATORS

```
✅ WORKING: Docker shows all services Up
❌ PROBLEM: Any service shows Down or Unhealthy
✅ API OK: curl http://localhost/health returns 200
❌ API DOWN: Connection refused or 500 error
✅ MESSAGE QUEUED: Response shows "queued_message_id"
❌ MESSAGE FAILED: Response shows "error"
```

---

## 🔐 SECURITY CHECKLIST

- [ ] .env not committed to Git
- [ ] .env not shared with anyone
- [ ] API keys rotated every 3 months
- [ ] Strong database password (not "password")
- [ ] Backup .env somewhere safe
- [ ] SSL enabled before production

---

## 📈 MONITORING

Check daily:

```bash
# Health
docker-compose ps  # All Up?

# Logs
docker-compose logs | grep -i error

# Performance
docker stats  # Which is using most resources?

# Database
docker exec raj_postgres psql -U mo -d raj_db \
  -c "SELECT COUNT(*) FROM conversations;"
```

---

## 🎯 SUCCESS METRICS

- [ ] All services running (docker-compose ps)
- [ ] Health check passes (curl /health)
- [ ] Test message queued (1-5 min delay)
- [ ] First-contact approval works
- [ ] Facebook messages received
- [ ] Override system responsive
- [ ] Mo override re-enables after 24h

When all checked: ✅ **Raj is Production Ready**

---

## 📞 FULL DOCUMENTATION

```
README_MASTER_GUIDE.md          ← You are here (index)
├── SETUP_ONE_BY_ONE.md         ← Phase by phase
├── CLAUDE_EXTENSION_GUIDES.md  ← 10 extension commands
├── VIDEO_ANALYSIS_AND_VOICE.md ← Learn from videos
├── FACEBOOK_BOT_MIGRATION.md   ← Facebook setup
├── FIRST_CONTACT_AND_OVERRIDE.md
├── VOICE_PROFILE.md
├── DEPLOYMENT_GUIDE.md
└── IMPLEMENTATION_STATUS.md
```

---

## 🚀 NEXT STEP

**Go to:** SETUP_ONE_BY_ONE.md → Phase 1 → Step 1.1

Good luck! 🎉
