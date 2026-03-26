"""
RAJ ASSISTANT - AI-Powered Facebook Messenger Bot
Trained to sound exactly like Mo The Jeweler

Handles Facebook webhook verification and incoming messages,
responds with Claude using Mo's complete personality profile.
"""

import os
import json
import logging
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
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=RAJ_SYSTEM_PROMPT,
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
    url = "https://graph.instagram.com/v18.0/me/messages"
    
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
    logger.info("🔥 Raj Assistant starting up...")
    logger.info(f"API Key configured: {bool(ANTHROPIC_API_KEY)}")
    logger.info(f"Facebook tokens configured: {bool(FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_WEBHOOK_VERIFY_TOKEN)}")
    logger.info(f"System prompt loaded: {len(RAJ_SYSTEM_PROMPT)} characters")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
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
