"""
RAJ FastAPI Application Entry Point
For Railway deployment
"""

import os
import sys
from pathlib import Path

# Add the current directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from anthropic import Anthropic

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Create app
app = FastAPI(title="Raj Assistant", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Claude client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "online",
        "service": "Raj Assistant",
        "version": "1.0.0"
    }

# ============================================
# FACEBOOK WEBHOOK VERIFICATION
# ============================================

@app.get("/webhook/facebook")
async def verify_facebook_webhook(hub_mode: str = None, hub_challenge: str = None, hub_verify_token: str = None):
    """Verify Facebook webhook"""
    verify_token = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "saifjewelers2024")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)
    
    return {"error": "Invalid verification"}, 403

# ============================================
# FACEBOOK MESSAGE WEBHOOK
# ============================================

@app.post("/webhook/facebook")
async def handle_facebook_webhook(request: dict):
    """Handle incoming Facebook messages"""
    
    # Import here to avoid circular imports
    from raj_core.personality import RAJ_BASE_PERSONALITY
    
    # Process each entry
    for entry in request.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            
            # Only process message events (not postbacks, etc.)
            if "message" not in messaging_event:
                continue
            
            sender_id = messaging_event["sender"]["id"]
            recipient_id = messaging_event["recipient"]["id"]
            message_text = messaging_event["message"].get("text", "")
            
            if not message_text:
                continue
            
            # Generate response using Claude
            try:
                response = anthropic_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    system=RAJ_BASE_PERSONALITY,
                    messages=[{"role": "user", "content": message_text}]
                )
                reply_text = response.content[0].text
            except Exception as e:
                print(f"[ERROR] Claude API error: {e}")
                reply_text = "Hey, let me get back to you in a second!"
            
            # Send response back to Facebook
            try:
                send_facebook_message(sender_id, reply_text)
            except Exception as e:
                print(f"[ERROR] Failed to send Facebook message: {e}")
    
    return {"status": "ok"}

# ============================================
# MESSAGE ENDPOINTS (for testing/other channels)
# ============================================

@app.post("/message/incoming")
async def handle_incoming_message(request: dict):
    """Generic message endpoint"""
    
    channel = request.get("channel")
    message_text = request.get("message")
    from_user = request.get("from")
    
    if not all([channel, message_text, from_user]):
        return {"error": "Missing required fields"}, 400
    
    # Generate response
    from raj_core.personality import RAJ_BASE_PERSONALITY
    
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=RAJ_BASE_PERSONALITY,
            messages=[{"role": "user", "content": message_text}]
        )
        reply_text = response.content[0].text
    except Exception as e:
        print(f"[ERROR] Claude API error: {e}")
        reply_text = "Let me get back to you!"
    
    return {
        "status": "success",
        "channel": channel,
        "from": from_user,
        "response": reply_text
    }

# ============================================
# HELPER: Send Facebook Message
# ============================================

def send_facebook_message(recipient_id: str, text: str) -> None:
    """Send a message via Facebook"""
    import requests
    
    access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not access_token:
        print("[ERROR] No Facebook access token configured")
        return
    
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": access_token
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"[ERROR] Facebook API error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
