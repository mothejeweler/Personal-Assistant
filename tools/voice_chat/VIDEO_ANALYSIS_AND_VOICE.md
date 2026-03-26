# 🎥 RAJ VIDEO ANALYSIS & VOICE EXTRACTION

**Goal:** Make Raj sound and respond like you by learning from your videos  
**Timeline:** ~30 minutes setup + ongoing improvement  
**Difficulty:** Medium (requires video URLs)

---

## 📍 PART A: How Video Analysis Works

### What Raj Can Extract:
1. **Jewelry Design Style**
   - What materials you use (gold, silver, rose gold, mixed)
   - Design preferences (minimalist, ornate, statement pieces)
   - Techniques you mention (hand-carved, 3D printed, traditional)
   - Pricing tier (luxury, mid-range, affordable)

2. **Communication Style**
   - How you greet customers
   - Technical vs casual language
   - Emotional tone (enthusiastic, calm, energetic)
   - Humor patterns
   - How you explain complex things
   - Objection handling (discount negotiation)

3. **Speaking Patterns**
   - Words you use frequently
   - Phrases that are "you"
   - Pacing (fast/slow talker)
   - Accent/dialect quirks
   - Filler words (uh, um, like, you know)

### What Raj CANNOT Do (YET):
- ❌ Clone your voice (generate audio that sounds like you)
- ❌ Exactly replicate you word-for-word
- ❌ Handle deep video analysis (requires human review still)

### What Raj WILL Do:
- ✅ Adopt your vocabulary and phrasing
- ✅ Match your tone in written responses
- ✅ Reference your design philosophy
- ✅ Use your communication patterns
- ✅ Handle objections like you would

---

## 📍 PART B: Setup Video Analysis (30 minutes)

### Step B.1: Gather Your Videos

**Where to get them:**
- TikTok (jewelry videos, customer interactions)
- Instagram Reels (personal brand content)
- YouTube (longer tutorials/design shows)
- Facebook Videos (customer testimonials, live streams)

**Which videos to use:**
- ✅ Customer interactions (how you talk to them)
- ✅ Design process videos (your jewelry style)
- ✅ Q&A sessions (your personality)
- ✅ Sales/pitch videos (your confidence)
- ❌ Don't need: Intros, outros, music-only content

**How many:**
- Minimum: 3-5 videos (15-30 minutes total)
- Ideal: 10+ videos (different topics)
- Best practice: Mix of customer service + design

### Step B.2: Download or Get Video URLs

**Option A: Use Public URLs (Easiest)**

If videos are on public platforms:
- TikTok: Right-click video → Copy video URL
- Instagram Reels: Share → Copy link
- YouTube: Copy URL from address bar
- Facebook: Share → Get video link

**Option B: Download Videos Locally**

If you want to upload files:

Using **Claude extension to help:**
```
"Help me download a TikTok/Instagram Reel video without watermark. 
Video URL: [PASTE URL]
Should I use an online tool or command line?"
```

Then upload to your Raj server directory.

### Step B.3: Analyze Videos with Claude

Use **Claude extension - Video Analysis Mode:**

```
"Analyze these jewelry business videos and extract:

1. DESIGN STYLE: What materials, design aesthetic, and techniques does this creator use?
2. COMMUNICATION TONE: How does the creator talk to customers? (formal, casual, enthusiastic, etc.)
3. KEY PHRASES: What phrases does the creator repeat?
4. PERSONALITY: What's the overall vibe? (luxury, fun, educational, sales-focused?)
5. OBJECTION HANDLING: How do they handle price questions?

Videos:
- [VIDEO URL 1]
- [VIDEO URL 2]
- [VIDEO URL 3]

Format output as:
## Design Style
[summary]

## Communication Tone
[summary]

## Repeated Phrases
- [phrase 1]
- [phrase 2]
- [phrase 3]

## Personality Keywords
- [keyword 1]
- [keyword 2]

## How They Handle Objections
[example & pattern]
"
```

**What the extension will do:**
1. Analyze video content (Claude can watch videos)
2. Extract communication patterns
3. Identify design preferences
4. Generate a profile

### Step B.4: Save Analysis Results

**Create a new file:** `RAJ_STYLE_PROFILE.md`

Use the extension output + add this template:

```markdown
# RAJ STYLE PROFILE
## Extracted from Video Analysis
**Videos analyzed:** [NUMBER]-[DATE]
**Last updated:** [TODAY]

### DESIGN PHILOSOPHY
[From your videos]

### COMMUNICATION STYLE
- Tone: [formal/casual/enthusiastic/etc]
- Energy: [high/moderate/calm]
- Humor: [yes/no - what type]
- Technical level: [expert/accessible/beginner-friendly]

### SIGNATURE PHRASES
- "Hey what's up" (greeting)
- "Ok" or "Bet" (closing)
- "Let me get back to you" (delay/escalation)
- "That's a custom piece" (common topic)

### DESIGN STYLE
- Materials: [what you use]
- Aesthetic: [your style]
- Price points: [your range]
- Signature technique: [what you're known for]

### OBJECTION PATTERNS
- Discount requests: [how you handle]
- Rush orders: [your response]
- Complaints: [your pattern]

### CUSTOMER INTERACTION EXAMPLES
[Copy exact phrases from videos]

### TONE EXAMPLES
Good message: [example of how you'd respond]
Bad message: [what Raj should NOT say]
```

---

## 📍 PART C: Integrate into Raj (15 minutes)

### Step C.1: Update Raj Personality System

**Use Claude extension:**

```
"I have this profile of my communication style extracted from my videos:

[PASTE YOUR RAJ_STYLE_PROFILE.md]

Create a detailed system prompt for Raj (an AI assistant) that:
1. Adopts this exact communication style
2. References my design philosophy when appropriate
3. Uses my signature phrases naturally
4. Handles customer objections exactly like I would
5. Never mentions Raj or being AI

Format as a complete system prompt that would go in Python code."
```

**What the extension will generate:**
- Enhanced system prompt
- Your actual voice patterns embedded
- Communication guidelines
- Examples of what to say/avoid

### Step C.2: Update Raj Code

**File to edit:** `raj_core/personality.py`

In terminal:

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Open personality file
nano raj_core/personality.py
```

**Find the section:**
```python
RAJ_BASE_PERSONALITY = """
You are Raj, Mo's personal assistant...
```

**Replace with the enhanced system prompt** from Claude extension (Step C.1)

**Add your design philosophy:**
```python
# Add after the main personality description:
"""
## MO'S DESIGN STYLE
- Materials: [your materials]
- Aesthetic: [your style]
- Price: [your range]
- Signature: [what makes you unique]

When discussing jewelry, reference this style. When customers ask about design,
guide them toward what Mo specializes in.
"""
```

### Step C.3: Restart Raj

```bash
# Stop current instance
docker-compose down

# Restart with new personality
docker-compose up -d

# Wait 30 seconds for services
sleep 30

# Verify health
curl http://localhost/health
```

---

## 📍 PART D: Test Your New Voice

### Step D.1: Send Test Messages

```bash
# Test 1: Design question (should match your style)
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "from": "+1234567890",
    "message": "Can you make a rose gold engagement ring with moissanite?",
    "customer_name": "Jane"
  }'

# Expected response: Uses your design language, references materials you like

# Test 2: Price concern (should handle objection like you)
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "from": "+1234567890",
    "message": "Your designs are beautiful but expensive. Can you do cheaper?",
    "customer_name": "Jane"
  }'

# Expected response: Handles price objection YOUR way
```

### Step D.2: Compare to Your Video

Listen to yourself in your videos, read Raj's responses:

- **Good** ✅: "Yeah, we can do rose gold. Let me check our moissanite stock."
- **Bad** ❌: "Certainly, I can fabricate a rose gold engagement ring with moissanite stones."

Raj should sound more like you, less robotic.

### Step D.3: Refine Profile

If Raj doesn't sound quite like you:

```bash
# Get latest message responses
docker-compose logs raj_server_1 | grep "response:" | tail -5

# Compare to your videos
# Ask Claude extension: "Does this response sound like me?"
```

**Update RAJ_STYLE_PROFILE.md** with corrections, then restart.

---

## 📍 PART E: Ongoing Video Updates

### Monthly Refresh

Every month, add new videos:

```bash
# 1. Gather 2-3 new videos from your latest posts
# 2. Ask Claude extension to extract new patterns
# 3. Update RAJ_STYLE_PROFILE.md
# 4. Restart Raj with fresh personality
```

### Watch for Changes

If you notice Raj NOT sounding like you:
- You might have new speaking patterns
- New design style emerged
- Different customer base now
- → Update the profile monthly

---

## 🤖 Using Claude Extension for Video Analysis

### Command 1: Initial Profile Extraction

```
"Analyze these jewelry business videos to create a customer service profile:

1. Jewelry design style (materials, techniques, price range)
2. Communication style (tone, energy, formality level)
3. Repeated phrases and signature language
4. How you handle common objections (price, timeline, modifications)
5. Personality (energetic? calm? funny? educational?)

Videos:
[PASTE VIDEO URLS HERE]

Output: A detailed profile I can use to train an AI to respond like me."
```

### Command 2: System Prompt Generation

```
"Create a system prompt for an AI assistant named 'Raj' based on this profile:

[PASTE RAJ_STYLE_PROFILE.md]

Requirements:
- Use exact phrases from the profile
- Match communication tone exactly
- Handle objections the same way
- Never reveal being AI
- Refer to jewelry style naturally
- Sound like a real person, not a bot

Format as Python string that can go in code."
```

### Command 3: Response Quality Check

```
"Does this response sound like ME based on my video analysis profile?

My profile:
[PASTE RELEVANT SECTION]

Response to test:
[PASTE AI RESPONSE]

Give it a score (1-10) and suggest improvements."
```

---

## ✅ Success Criteria

- [ ] Extracted 5+ videos for analysis
- [ ] Created RAJ_STYLE_PROFILE.md
- [ ] Updated personality.py with new voice
- [ ] Restarted Raj successfully
- [ ] Test messages sound like YOU
- [ ] Price objections handled your way
- [ ] No robotic/AI-like language
- [ ] Customer feels like talking to you

---

## 🚀 Advanced: Continuous Learning

If you want Raj to learn from conversations:

**Database track:**
- Message asking Claude to respond
- Your approval (or Mo's correction)
- Original response vs corrected version
- → Over time, Raj learns your preferences

*This requires dashboard + approval system (already built)*

---

## 📞 Next: Facebook Bot Integration

Once Raj has your voice, we need to connect it to your existing Facebook bot.

See: FACEBOOK_BOT_MIGRATION.md
