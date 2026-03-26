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
from typing import Set
from fastapi import FastAPI, Request, HTTPException, Response
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

try:
    from voice_synth import VoiceSynthesizer
except ImportError:
    VoiceSynthesizer = None

try:
    from runtime_editor import RuntimeEditor
except ImportError:
    RuntimeEditor = None

YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CHANNEL_RSS_URL = os.getenv("YOUTUBE_CHANNEL_RSS_URL", "")
PERSONALITY_REFRESH_MINUTES = int(os.getenv("PERSONALITY_REFRESH_MINUTES", "60"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "none")
OWNER_FACEBOOK_IDS_RAW = os.getenv("OWNER_FACEBOOK_IDS", "")

OWNER_FACEBOOK_IDS: Set[str] = {
    x.strip() for x in OWNER_FACEBOOK_IDS_RAW.split(",") if x.strip()
}

video_updater = None
if PersonalityVideoUpdater is not None:
    video_updater = PersonalityVideoUpdater(
        channel_id=YOUTUBE_CHANNEL_ID,
        rss_url=YOUTUBE_CHANNEL_RSS_URL,
    )

sync_task = None

voice_synth = VoiceSynthesizer(provider=VOICE_PROVIDER) if VoiceSynthesizer else None
runtime_editor = RuntimeEditor(default_refresh_minutes=PERSONALITY_REFRESH_MINUTES) if RuntimeEditor else None


def is_owner_sender(sender_id: str) -> bool:
    if not sender_id:
        return False
    return sender_id in OWNER_FACEBOOK_IDS


def build_runtime_system_prompt() -> str:
    """Build the current system prompt including fresh personality deltas from new videos."""
    prompt = RAJ_SYSTEM_PROMPT

    if runtime_editor:
        prompt = f"{prompt}\n\n---\n{runtime_editor.get_prompt_appendix()}"

    if not video_updater:
        return prompt

    delta = video_updater.get_runtime_delta_text(max_chars=6000)
    if not delta:
        return prompt

    return (
        f"{prompt}\n\n"
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

        refresh_minutes = PERSONALITY_REFRESH_MINUTES
        if runtime_editor:
            refresh_minutes = int(runtime_editor.get_setting("personality_refresh_minutes", PERSONALITY_REFRESH_MINUTES))

        await asyncio.sleep(max(refresh_minutes, 5) * 60)


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

                        # Owner-only real-time runtime editing with explicit confirmation.
                        if runtime_editor and is_owner_sender(sender_id):
                            if runtime_editor.get_setting("realtime_edit_permissions", True):
                                handled, owner_reply = runtime_editor.handle_owner_message(sender_id, message_text)
                                if handled:
                                    await send_facebook_message(sender_id, owner_reply)
                                    logger.info("Processed owner runtime edit flow for %s", sender_id)
                                    continue
                        
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


@app.get("/admin/voice/status")
async def admin_voice_status(request: Request):
    """Show current Raj voice provider readiness."""
    _check_admin_key(request)
    if not voice_synth:
        return {"status": "disabled", "reason": "voice_synth_unavailable"}
    return {"status": "ok", "voice": voice_synth.status()}


@app.get("/admin/runtime/status")
async def admin_runtime_status(request: Request):
    """Show runtime-edit settings, learned habits, and pending confirmations."""
    _check_admin_key(request)
    if not runtime_editor:
        return {"status": "disabled", "reason": "runtime_editor_unavailable"}

    return {
        "status": "ok",
        "owner_ids_configured": len(OWNER_FACEBOOK_IDS),
        "runtime": runtime_editor.get_status(),
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


@app.post("/test/voice")
async def test_voice(request: Request):
    """Generate Raj text response and synthesize it to voice audio."""
    if not voice_synth:
        raise HTTPException(status_code=503, detail="Voice synth module unavailable")

    try:
        data = await request.json()
        user_message = (data.get("message") or "").strip()

        if not user_message:
            raise HTTPException(status_code=400, detail="Message field required")

        raj_text = await generate_response(user_message)
        audio_bytes, content_type = voice_synth.synthesize(raj_text)

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": 'inline; filename="raj-response.mp3"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice test endpoint: {str(e)}", exc_info=True)
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
    logger.info("Owner IDs configured: %s", len(OWNER_FACEBOOK_IDS))
    if voice_synth:
        logger.info("Voice provider status: %s", voice_synth.status())

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
