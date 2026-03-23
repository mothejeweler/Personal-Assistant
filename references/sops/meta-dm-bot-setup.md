# SOP: Meta DM Bot Setup

Auto-responds to Instagram and Facebook Messenger DMs using Claude.
The bot lives in `tools/meta-dm-bot/`.

---

## Step 1 — Get Your Anthropic API Key

1. Go to https://console.anthropic.com
2. Click **API Keys** → **Create Key**
3. Copy it — you'll need it in Step 4

---

## Step 2 — Deploy to Railway

1. Go to https://railway.app and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo** → select this repo
3. Set the **Root Directory** to `tools/meta-dm-bot`
4. Railway will detect it's a Python app automatically
5. Once deployed, copy your **public URL** (looks like `https://your-app.up.railway.app`)
   - You'll need this for the Meta webhook

---

## Step 3 — Set Environment Variables on Railway

In your Railway project → **Variables**, add these:

| Variable | Value |
|---|---|
| `META_VERIFY_TOKEN` | Make up any secret string (e.g., `saif-jewelers-2024`) |
| `META_FB_PAGE_ACCESS_TOKEN` | From Step 4 below |
| `META_IG_PAGE_ACCESS_TOKEN` | Same as FB token (if Instagram is connected to the same Page) |
| `ANTHROPIC_API_KEY` | From Step 1 |

---

## Step 4 — Set Up Your Meta Developer App

1. Go to https://developers.facebook.com
2. Click **My Apps** → **Create App**
3. Choose **Business** type → name it (e.g., "Saif Jewelers DM Bot")
4. From the app dashboard, add these products:
   - **Messenger** (for Facebook DMs)
   - **Instagram** (for Instagram DMs)

### Get Your Page Access Token
1. In the Messenger settings → **Access Tokens** → select your Facebook Page
2. Click **Generate Token** → copy it
3. Paste it into Railway as `META_FB_PAGE_ACCESS_TOKEN` and `META_IG_PAGE_ACCESS_TOKEN`

### Connect Instagram
1. In the Instagram settings → **Instagram Accounts** → connect your Instagram Business account
2. Make sure your Instagram is set to **Business** or **Creator** account

---

## Step 5 — Register the Webhook

1. In your Meta app → **Messenger** settings → **Webhooks** → **Add Callback URL**
2. **Callback URL:** `https://your-app.up.railway.app/webhook`
3. **Verify Token:** the exact string you set for `META_VERIFY_TOKEN`
4. Click **Verify and Save**
5. Subscribe to: `messages` field
6. Repeat in the **Instagram** settings → Webhooks → same URL and token

---

## Step 6 — Submit for App Review

Meta requires review before the bot can message real users outside your test accounts.

1. In your app → **App Review** → **Permissions and Features**
2. Request these permissions:
   - `pages_messaging` (Facebook Messenger)
   - `instagram_manage_messages` (Instagram DMs)
3. Fill in the use case: "Automated customer service responses for our jewelry store"
4. Submit — review typically takes a few days to 2 weeks

While waiting, you can test with your own accounts.

---

## Testing Before Approval

1. Add yourself as a **Tester** in App Roles
2. Send a DM to your Page or Instagram from your personal account
3. The bot should reply within seconds

---

## How the Bot Works

- Customer sends a DM → Meta sends it to your Railway server
- Server calls Claude (Haiku model — fast and cheap) with your full store knowledge
- Claude drafts a reply in Mo's voice
- Server sends it back through Meta's API automatically

**Cost estimate:** Roughly $0.001–0.003 per DM exchange (Claude Haiku pricing). Very low.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Webhook not verifying | Check `META_VERIFY_TOKEN` matches exactly in Railway and Meta |
| Bot not replying | Check Railway logs for errors; verify Page Access Token is valid |
| Token expired | Page Access Tokens can expire — regenerate in Meta Developer portal and update Railway variable |
| Reply not sending | Make sure the Page is subscribed to the `messages` webhook field |

---

## Maintenance

- Page Access Tokens may need to be refreshed periodically (or generate a long-lived token)
- If response quality drifts, update `SYSTEM_PROMPT` in `tools/meta-dm-bot/server.py`
- Monitor Railway logs periodically for errors
