# Gmail Integration Setup Guide

This guide will walk you through connecting Gmail to Raj's inbox dashboard so that emails from customers automatically appear in the unified dashboard.

## Option 1: IMAP Method (Recommended for Local Dev) ⭐

This is the simplest method and requires no API key setup. Gmail IMAP is built into Gmail and works with an **app-specific password**.

### Step 1: Enable 2-Factor Authentication

Gmail requires 2FA for app-specific passwords to work:

1. Go to **myaccount.google.com**
2. Click **Security** (left sidebar)
3. Scroll to **2-Step Verification** and click **Get Started**
4. Follow the prompts (you'll need your phone to verify)

### Step 2: Generate App-Specific Password

Once 2FA is enabled:

1. Go back to **myaccount.google.com** → **Security**
2. Scroll to **App passwords** (appears only after 2FA is on)
3. Select **Mail** and **Mac** (or your OS)
4. Click **Generate**
5. Google will show a 16-character password like: `abcd efgh ijkl mnop`

**Copy this password** (without spaces) — you'll need it next.

### Step 3: Update .env File

In `/tools/voice_chat/backend/.env`:

```env
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
```

Replace:
- `your-email@gmail.com` with your actual Gmail address
- `abcdefghijklmnop` with the 16-character password you just generated

### Step 4: Enable IMAP in Gmail

1. Go to **Gmail Settings** → **Forwarding and POP/IMAP**
2. Under **IMAP Access**, select **Enable IMAP**
3. Click **Save**

### Step 5: Test the Connection

Restart the backend server:

```bash
cd /Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat/backend
/Users/mothejeweler/Documents/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8011
```

Send yourself an email, then check the dashboard:

```bash
curl "http://127.0.0.1:8011/dashboard/notifications"
```

You should see your email appear in the `unread` count within 2-3 minutes (the background job runs every 10 minutes).

---

## Option 2: Gmail API Method (For Production)

This method requires OAuth and is more robust but requires API setup.

### Step 1: Create a Google Cloud Project

1. Go to **console.cloud.google.com**
2. Create a new project (top-left dropdown → **New Project**)
3. Name it "Raj Email Connector"

### Step 2: Enable Gmail API

1. In the Google Cloud Console, search for **Gmail API**
2. Click **Enable**

### Step 3: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Choose **Desktop application**
4. Download the JSON file

### Step 4: Update .env

```env
GMAIL_API_KEY=your-api-key-from-json
GMAIL_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

*(API implementation coming soon — IMAP is recommended for now)*

---

## How It Works

1. **Every 10 minutes**, Raj checks your Gmail inbox for unread emails
2. **Automatically extracts:**
   - Sender email address (becomes customer name)
   - Subject line
   - Email body
   - Timestamp
3. **Posts to `/message/incoming`** with channel="email"
4. **Marks as read** once dashboard processes the email
5. **Appears in dashboard** with priority/sentiment calculated

### What You'll See in Dashboard

- **Channel**: Email icon / "email" label
- **From**: Sender's email address
- **Preview**: First 100 characters of subject + body
- **Intent**: Auto-detected (inquiry, custom_design, complaint, etc.)
- **Priority**: Calculated based on keywords and sentiment
- **Unread**: Stays unread until Mo responds

---

## Troubleshooting

### "Credentials are required"

**Problem**: Backend logs show "Gmail not configured"

**Solution**: Make sure both `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` are in `.env` file:

```bash
# Check if env vars are set
cd backend && python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GMAIL_ADDRESS:', os.getenv('GMAIL_ADDRESS')); print('GMAIL_APP_PASSWORD:', os.getenv('GMAIL_APP_PASSWORD'))"
```

### "Unable to authenticate"

**Problem**: Connection refused or authentication failed

**Solutions**:
- Double-check app password (no spaces)
- Verify 2FA is enabled
- Verify IMAP is enabled in Gmail Settings
- Try resetting the app password

### "No emails appearing in dashboard"

**Problem**: Raj is running but emails aren't showing up

**Troubleshooting**:
1. Check backend logs for Gmail sync errors
2. Send yourself a test email
3. Wait 10 minutes for the sync job to run (or manually test):

```bash
python -c "
import sys
sys.path.insert(0, '.')
from integrations.gmail_connector import sync_gmail_to_backend
result = sync_gmail_to_backend('http://127.0.0.1:8011')
print('Result:', result)
"
```

### "IMAP not enabled"

**Problem**: imaplib.IMAP4.error: b'[IMAP4rev1] Gmail IMAP service is disabled'

**Solution**: Go to Gmail Settings → **Forwarding and POP/IMAP** → Enable IMAP

---

## Security Notes

1. **App-Specific Password** (not your actual Gmail password) — safe to commit in `.env.example` as a placeholder
2. **IMAP credentials** stay local; never shared with Raj system
3. **Emails marked as read** but not deleted from Gmail
4. **Consider creating a separate Gmail inbox** for customer emails if you want to partition Saif Jewelers inquiries

---

## Next Steps

Once Gmail is working:

1. Test with a few customer emails
2. Set up the other integrations (website forms, Instagram, TikTok)
3. Configure notification alerts so Mo gets notified of high-priority emails
4. Adjust priority scoring based on your experience

Enjoy! 🚀
