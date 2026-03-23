# Raj — Setup Guide

## What it does
Always-listening voice assistant. Say **"Hey Raj"** to wake him up, ask your question, and he talks back. Personality is a mix of Dave Chappelle, Andrew Schulz, Louis CK, and old-school Cat Williams — through the soul of an Indian tech support agent who has seen everything.

---

## Step 1 — Get the Indian Accent Voice (iPhone)

Raj will automatically use an Indian English voice if one is installed. Without it, he'll fall back to a default English voice.

To install:
1. iPhone **Settings** → **Accessibility** → **Spoken Content** → **Voices**
2. Tap **English** → **English (India)**
3. Download **Rishi** (tap the cloud icon next to "Enhanced")

That's it. The app picks it up automatically.

---

## Step 2 — Run the App

### On Mac (instant, no setup)
Open `index.html` directly in Safari. Works immediately.

---

### On iPhone — Option A: Local WiFi (Mac + iPhone on same network)

**One-time setup:**
```
xcode-select --install
```
Click Install in the dialog.

**Each time:**
```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat"
python3 -m http.server 8080
```

Find your Mac's IP:
```
ipconfig getifaddr en0
```

On iPhone, open Safari and go to: `http://[your-mac-ip]:8080`

> Note: Plain HTTP may block microphone in Safari on iOS. Use Option B if that happens.

---

### On iPhone — Option B: ngrok (HTTPS, works anywhere)

```bash
brew install ngrok
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/tools/voice_chat"
python3 -m http.server 8080 &
ngrok http 8080
```

Open the `https://xxxxx.ngrok.io` URL on your iPhone. Microphone will work.

---

### Permanent URL — Option C: GitHub Pages (best long-term)
1. Create a free GitHub repo
2. Upload `index.html`
3. Settings → Pages → Deploy from main branch
4. Get a permanent `https://yourusername.github.io/raj` URL — works anywhere, no Mac running

---

## Step 3 — Connect to HomePod Mini

No app changes needed. Just:
1. Open the app on iPhone
2. Swipe up (Control Center) → tap AirPlay icon → select your HomePod
3. All audio plays through HomePod. Mic stays on iPhone.
4. Leave phone on charger on your nightstand.

---

## Using Raj

| Action | What to do |
|---|---|
| Wake him up | Say **"Hey Raj"** |
| Ask in one breath | "Hey Raj what's on my calendar?" |
| Two-step | Say "Hey Raj" → wait for chime → ask your question |
| Tap to trigger | Tap the **HEY RAJ** button if voice isn't working |
| Stop speaking | Tap the ⏹️ button |
| Clear conversation | Tap 🗑 in the header |

---

## API Key
You'll be prompted on first launch. Stored in browser localStorage — goes directly to `api.anthropic.com`, nowhere else.
