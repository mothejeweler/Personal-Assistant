"""
RAJ ASSISTANT - AI-Powered Facebook Messenger Bot
Trained to sound exactly like Mo The Jeweler

Handles Facebook webhook verification and incoming messages,
responds with Claude using Mo's complete personality profile.
"""

import os
import json
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from anthropic import Anthropic
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Raj Assistant - Mo The Jeweler Bot")

# Initialize Anthropic client
client = Anthropic()

# Get credentials from environment
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_WEBHOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import personality system prompt
try:
    from personality import get_raj_complete_system_prompt
    RAJ_SYSTEM_PROMPT = get_raj_complete_system_prompt()
except ImportError:
    logger.warning("Could not import personality module, using fallback system prompt")
    RAJ_SYSTEM_PROMPT = "You are Raj, an AI assistant trained to sound like Mo The Jeweler, owner of Saif Jewelers in Texas. Be authentic, transparent, and helpful when discussing jewelry, pricing, and custom services."

try:
    from video_personality_updater import PersonalityVideoUpdater
except ImportError:
    PersonalityVideoUpdater = None

YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CHANNEL_RSS_URL = os.getenv("YOUTUBE_CHANNEL_RSS_URL", "")
PERSONALITY_REFRESH_MINUTES = int(os.getenv("PERSONALITY_REFRESH_MINUTES", "60"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

video_updater = None
if PersonalityVideoUpdater is not None:
    video_updater = PersonalityVideoUpdater(
        channel_id=YOUTUBE_CHANNEL_ID,
        rss_url=YOUTUBE_CHANNEL_RSS_URL,
    )

sync_task = None


def build_runtime_system_prompt() -> str:
    """Build the current system prompt including fresh personality deltas from new videos."""
    if not video_updater:
        return RAJ_SYSTEM_PROMPT

    delta = video_updater.get_runtime_delta_text(max_chars=6000)
    if not delta:
        return RAJ_SYSTEM_PROMPT

    return (
        f"{RAJ_SYSTEM_PROMPT}\n\n"
        "---\n"
        "LATEST VOICE DELTAS FROM NEW VIDEOS\n"
        "Apply these as incremental adjustments to the base voice.\n\n"
        f"{delta}"
    )


def _check_admin_key(request: Request) -> None:
    if not ADMIN_API_KEY:
        return
    incoming = request.headers.get("x-admin-key", "")
    if incoming != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


async def personality_sync_loop() -> None:
    """Background loop: keeps Raj updated when new channel videos are posted."""
    if not video_updater or not video_updater.enabled():
        logger.info("Video personality sync loop not started (missing channel config).")
        return

    while True:
        try:
            result = video_updater.sync_once(max_new_videos=3)
            logger.info("Video personality sync result: %s", result)
        except Exception as e:
            logger.error("Video personality sync failed: %s", e, exc_info=True)

        await asyncio.sleep(max(PERSONALITY_REFRESH_MINUTES, 5) * 60)


# ============================================================================
# FACEBOOK WEBHOOK HANDLERS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Raj Assistant - Mo The Jeweler Bot",
        "version": "2.0"
    }


@app.get("/webhook/facebook")
async def verify_facebook_webhook(request: Request):
    """
    Facebook webhook verification endpoint.
    Required for Facebook to confirm our webhook is legitimate.
    """
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if verify_token == FACEBOOK_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(challenge)
    else:
        logger.error("Webhook verification failed - invalid token")
        raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhook/facebook")
async def handle_facebook_webhook(request: Request):
    """
    Handle incoming Facebook messages.
    Receives webhook data, extracts message, generates response via Claude, sends back.
    """
    try:
        data = await request.json()
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        
        # Verify it's a message event from a page we manage
        if data.get("object") != "page":
            return {"status": "ok"}
        
        # Process each entry in the webhook
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                recipient_id = messaging_event.get("recipient", {}).get("id")
                
                # Handle incoming message
                if messaging_event.get("message"):
                    message_text = messaging_event["message"].get("text")
                    
                    if message_text:
                        logger.info(f"Message from {sender_id}: {message_text}")
                        
                        # Generate response using Claude
                        response_text = await generate_response(message_text)
                        
                        # Send response back to Facebook
                        await send_facebook_message(sender_id, response_text)
                        
                        logger.info(f"Response sent to {sender_id}")
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================================
# MESSAGE GENERATION
# ============================================================================

async def generate_response(user_message: str) -> str:
    """
    Generate a response using Claude with Raj's personality system prompt.
    
    Args:
        user_message: The incoming customer message
    
    Returns:
        Response text in Mo's voice
    """
    try:
        runtime_system_prompt = build_runtime_system_prompt()
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=runtime_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        # Extract response text
        response_text = response.content[0].text
        logger.info(f"Generated response: {response_text[:100]}...")
        
        return response_text
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        # Fallback response
        return "My boy, got you. Hit the DM directly and we'll hook you up. Let's run some numbers. 🔥"


# ============================================================================
# FACEBOOK API
# ============================================================================

async def send_facebook_message(recipient_id: str, message_text: str) -> bool:
    """
    Send a message back to the Facebook user via Facebook API.
    
    Args:
        recipient_id: Facebook user ID
        message_text: Message content to send
    
    Returns:
        True if sent successfully, False otherwise
    """
    # Facebook Messenger Send API endpoint
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        },
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Message sent successfully to {recipient_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending message to Facebook: {str(e)}")
        return False


@app.post("/admin/personality/sync")
async def admin_sync_personality(request: Request):
    """Manually trigger sync from newly posted channel videos."""
    _check_admin_key(request)
    if not video_updater:
        return {"status": "disabled", "reason": "updater_not_available"}

    result = video_updater.sync_once(max_new_videos=5)
    return result


@app.get("/admin/personality/status")
async def admin_personality_status(request: Request):
    """Show auto-update configuration and latest sync metadata."""
    _check_admin_key(request)
    if not video_updater:
        return {"status": "disabled", "reason": "updater_not_available"}

    state = video_updater.load_state()
    return {
        "status": "ok",
        "enabled": video_updater.enabled(),
        "refresh_minutes": PERSONALITY_REFRESH_MINUTES,
        "rss_url": video_updater.rss_url,
        "processed_video_count": len(state.get("processed_video_ids", [])),
        "last_sync_at": state.get("last_sync_at"),
        "last_success_at": state.get("last_success_at"),
    }


# ============================================================================
# TEST ENDPOINT (for manual testing)
# ============================================================================

@app.post("/test/message")
async def test_message(request: Request):
    """
    Test endpoint to verify Raj responds in Mo's voice.
    
    Usage:
        curl -X POST http://localhost:8000/test/message \
        -H "Content-Type: application/json" \
        -d '{"message": "Hey, what kind of grillz do you make?"}'
    """
    try:
        data = await request.json()
        user_message = data.get("message", "")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message field required")
        
        response = await generate_response(user_message)
        return {
            "user_message": user_message,
            "raj_response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONVERSATION HISTORY (for future multi-turn support)
# ============================================================================

# This is a placeholder for future conversation persistence
# In production, you'd want to store conversations in PostgreSQL
conversation_history = {}


def get_or_create_conversation(user_id: str):
    """Get conversation history for user, or create new one"""
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    return conversation_history[user_id]


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup"""
    global sync_task
    logger.info("🔥 Raj Assistant starting up...")
    logger.info(f"API Key configured: {bool(ANTHROPIC_API_KEY)}")
    logger.info(f"Facebook tokens configured: {bool(FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_WEBHOOK_VERIFY_TOKEN)}")
    logger.info(f"System prompt loaded: {len(RAJ_SYSTEM_PROMPT)} characters")

    if video_updater and video_updater.enabled():
        # One immediate sync at startup, then background polling.
        try:
            logger.info("Running startup personality sync from channel videos...")
            startup_result = video_updater.sync_once(max_new_videos=5)
            logger.info("Startup sync result: %s", startup_result)
        except Exception as e:
            logger.error("Startup personality sync failed: %s", e, exc_info=True)

        sync_task = asyncio.create_task(personality_sync_loop())
        logger.info("Background personality sync loop started (%s min).", PERSONALITY_REFRESH_MINUTES)


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
    global sync_task
    if sync_task:
        sync_task.cancel()
    logger.info("🔥 Raj Assistant shutting down...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get PORT from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
