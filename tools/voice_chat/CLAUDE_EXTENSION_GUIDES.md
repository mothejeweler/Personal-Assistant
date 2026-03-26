# 🔧 CLAUDE EXTENSION QUICK GUIDES

Use these instructions **before each setup step** for AI-assisted guidance.

---

## 🤖 Guide 1: Using Claude Extension to Get Anthropic API Key

**When to use:** Step 2.1 of SETUP_ONE_BY_ONE.md

**Plugin Command:**
```
"Help me get an Anthropic API key for my personal assistant application"
```

**What the extension will do:**
1. Guide you to console.anthropic.com
2. Show you exactly where to click
3. Explain billing (free trial available)
4. Help you generate and copy the key

**What you do:**
1. Open Claude extension in Chrome
2. Paste the command above
3. Follow the visual steps
4. Copy the key when ready
5. **Save it in notepad** (don't lose it!)

**Expected result:**
- Key format: `sk-ant-` followed by random characters
- 44-48 characters total
- Keep it SECRET (don't share or commit to Git)

---

## 🤖 Guide 2: Using Claude Extension to Set Up Twilio

**When to use:** Step 2.2 of SETUP_ONE_BY_ONE.md

**Plugin Command:**
```
"Help me set up Twilio for WhatsApp messaging and SMS. I need: Account SID, Auth Token, and a phone number"
```

**What the extension will do:**
1. Guide you to twilio.com signup
2. Explain free trial ($15 credit)
3. Show where to find credentials
4. Help buy a phone number

**What you do:**
1. Open Claude extension
2. Paste command above
3. Complete each step the extension shows
4. Copy three values:
   - Account SID (from Console dashboard)
   - Auth Token (below Account SID)
   - Phone number (from Phone Numbers section)
5. **Save all three**

**Expected result:**
- Account SID: ~35 characters, starts with `AC`
- Auth Token: ~34 characters, random alphanumeric
- Phone: `+1` followed by 10 digits (US) or varies by country
- All three needed for Raj to send messages

---

## 🤖 Guide 3: Using Claude Extension to Set Up Instagram API

**When to use:** Step 2.3 of SETUP_ONE_BY_ONE.md

**Plugin Command:**
```
"Help me set up the Instagram Graph API. I need: Access Token and Business Account ID. I have a business Instagram account."
```

**What the extension will do:**
1. Guide you to developers.facebook.com
2. Show where to create an app
3. Explain Instagram graph permissions
4. Help generate access token
5. Show where to find business account ID

**What you do:**
1. Open Claude extension
2. Paste command above
3. Follow each step carefully (this one is multi-step)
4. When extension asks "Do you have a Facebook business account?", say YES
5. Link your Instagram account
6. Copy:
   - Access Token (very long string)
   - Business Account ID (numbers only, ~10 digits)
7. **Convert short-lived token to long-lived** (extension will guide)

**Expected result:**
- Access Token: Starts with `IGQVR...`, ~150+ characters
- Business Account ID: All numbers, like `1234567890`
- Both needed for Raj to send Instagram DMs

---

## 🤖 Guide 4: Using Claude Extension to Create .env Template

**When to use:** Step 3.1 of SETUP_ONE_BY_ONE.md (before creating file)

**Plugin Command:**
```
"Create a .env configuration template for a Django/FastAPI app. Include:
- Anthropic API key
- Twilio Account SID, Auth Token, Phone
- Instagram Access Token, Business Account ID
- PostgreSQL credentials (user: mo, database: raj_db)
- Redis port: 6379
- My contact phone number: +1 (YOUR NUMBER)
- Mo's WhatsApp phone number: +1 (YOUR NUMBER)

Format for: environment variables, with placeholders I can fill in manually"
```

**What the extension will do:**
1. Generate a complete .env template
2. Show which values are secrets (dangerous to share)
3. Explain what each one does
4. Provide security tips

**What you do:**
1. Open Claude extension
2. Paste command above (replace YOUR NUMBER with actual)
3. Copy the generated template
4. Open terminal: `nano ~/.env` (or in the Raj directory)
5. Paste template
6. Replace each placeholder with actual values
7. Save and exit

**Expected result:**
- .env file in Raj directory
- ~12-15 lines
- Contains all secrets needed to run Raj
- Looks like: `KEY=value` on each line
- Never commit to Git (it's in .gitignore)

---

## 🤖 Guide 5: Using Claude Extension to Debug Docker Errors

**When to use:** Step 4.2 or later if containers won't start

**Plugin Command:**
```
"I'm trying to run: docker-compose up -d

But I got this error: [PASTE THE ERROR HERE]

Help me fix it. I'm on macOS with Docker Desktop."
```

**What the extension will do:**
1. Identify the specific problem
2. Give step-by-step fix instructions
3. Explain what went wrong
4. Suggest prevention

**What you do:**
1. If containers fail, copy the error message
2. Open Claude extension
3. Paste the command above
4. Follow the fix steps
5. Try again: `docker-compose up -d`

**Common fixes:**
- "Port already in use" → Kill process or change port
- "Image not found" → Build manually: `docker-compose build`
- "Connection refused" → Wait longer or restart Docker
- "out of disk space" → Clean up: `docker system prune`

---

## 🤖 Guide 6: Using Claude Extension to Test API Endpoints

**When to use:** Step 4.4 if test message doesn't work

**Plugin Command:**
```
"Test my Raj API. The endpoint is: http://localhost/message/incoming

The expected response should be JSON with fields:
- status (success/error)
- customer_id (number)
- queued_message_id (number)
- delay_info (text about 1-5 min delay)

Help me craft a test request using curl or another method."
```

**What the extension will do:**
1. Give you exact curl command to use
2. Explain what each field means
3. Show what SUCCESS looks like
4. Suggest debugging if it fails

**What you do:**
1. Open Claude extension
2. Paste command above
3. Run the curl command in terminal
4. Check if response matches expected
5. If not, ask extension for help debugging

---

## 🤖 Guide 7: Using Claude Extension to Interpret Logs

**When to use:** Something's wrong and logs are confusing

**Plugin Command:**
```
"Here are my Docker logs. Help me understand what's happening:

[PASTE THE LOG OUTPUT HERE]

Is there an error? Should I be concerned?"
```

**What the extension will do:**
1. Highlight any ERROR or CRITICAL lines
2. Explain what each important line means
3. Recommend action (restart, investigate, wait, etc.)
4. Suggest next debugging step

**What you do:**
1. Get logs: `docker-compose logs` (all) or `docker-compose logs raj_server_1` (one service)
2. Copy the output
3. Open Claude extension
4. Paste the command and logs
5. Follow recommendations
6. Check logs again after action

---

## 🤖 Guide 8: Using Claude Extension for Production Deployment

**When to use:** Step 7 (ready to go live)

**Plugin Command:**
```
"I'm deploying Raj (a 24/7 business assistant) to production. I want:
- High availability (if one server dies, stay online)
- Easy to monitor
- Handle 100+ customers

Should I use AWS, DigitalOcean, or my own server? 
Help me decide and give first steps."
```

**What the extension will do:**
1. Compare AWS vs DigitalOcean vs self-hosted
2. Recommend based on your needs
3. Give cost estimates
4. Link to official docs
5. Outline first 3 setup steps

**What you do:**
1. Open Claude extension
2. Paste command above
3. Read recommendation
4. Choose one option
5. Follow first-steps guide
6. Ask extension for help on each step

---

## 🤖 Guide 9: Using Claude Extension to Review Your Config

**When to use:** Before starting Raj (Step 4.1)

**Plugin Command:**
```
"Review my Raj configuration. Here's my .env file:

[PASTE.env CONTENTS HERE - but replace actual API keys with REDACTED]

Are all required values present? Any security issues? Any misspellings?"
```

**What the extension will do:**
1. Check all required fields present
2. Flag any typos or wrong format
3. Point out security issues
4. Suggest improvements

**What you do:**
1. Open .env file: `cat .env`
2. Copy contents
3. Replace actual keys with `REDACTED` (for security)
4. Open Claude extension
5. Paste command + redacted .env
6. Fix any issues it mentions
7. Save and try again

---

## 🤖 Guide 10: Using Claude Extension for Custom Troubleshooting

**When to use:** Anything not in this list

**Plugin Command:**
```
"I'm setting up Raj (a FastAPI + PostgreSQL + Docker application). 

Problem: [DESCRIBE THE PROBLEM]

What I tried: [WHAT YOU ATTEMPTED]

System: macOS, Docker Desktop

Help me fix this."
```

**What the extension will do:**
1. Ask clarifying questions if needed
2. Diagnose root cause
3. Give exact fix steps
4. Prevent future issues

**What you do:**
1. Be specific about the problem
2. Mention what you already tried
3. Include error messages if any
4. Follow recommended fixes
5. Report back if fixes work

---

## ⚡ TL;DR - Quick Reference

| Step | Task | Extension Command |
|------|------|-------------------|
| 2.1 | Get API Key | "Help me get Anthropic API key" |
| 2.2 | Setup Twilio | "Help me setup Twilio for WhatsApp" |
| 2.3 | Setup Instagram | "Help me setup Instagram Graph API" |
| 3.1 | Create .env | "Create .env template with..." |
| 4.2 | Debug Docker | "I got this Docker error: [ERROR]" |
| 4.4 | Test API | "Test my API endpoint..." |
| Issues | Understand logs | "Here are my Docker logs: [LOGS]" |
| Issues | General help | "Problem: [DESCRIBE]" |

---

## 💡 Pro Tips

1. **Always redact API keys** when pasting logs/config to Claude extension (replace with `REDACTED`)
2. **Save responses** from Claude extension for reference later
3. **Test each step** before moving to next (don't skip ahead)
4. **Use extension for API setup** (it's faster than doing manually)
5. **Ask for clarification** if extension advice seems unclear
6. **Check official docs** for latest changes (Facebook/Twilio frequently update)

---

## 🔒 Security Reminder

- 🚨 **NEVER** commit .env to Git
- 🚨 **NEVER** share your API keys
- 🚨 **ALWAYS** use `REDACTED` when asking for help with config
- 🚨 **ROTATE** your keys every 3 months
- 🚨 **USE** strong database passwords

---

**Ready to get started?** Go to: SETUP_ONE_BY_ONE.md → Step 1.1
