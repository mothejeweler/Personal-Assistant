"""
Saif Jewelers — Auto DM Response Bot
Handles incoming Instagram and Facebook Messenger DMs,
generates replies using Claude, and sends them automatically.
"""

import os
import logging
import requests
from flask import Flask, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meta_dm_bot")

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
FB_PAGE_ACCESS_TOKEN = os.getenv("META_FB_PAGE_ACCESS_TOKEN")
IG_PAGE_ACCESS_TOKEN = os.getenv("META_IG_PAGE_ACCESS_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_DM_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"))
ANTHROPIC_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "ANTHROPIC_FALLBACK_MODELS",
        "claude-3-5-haiku-20241022,claude-3-5-sonnet-20241022"
    ).split(",") if m.strip()
]

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
You are the customer messaging assistant for Saif Jewelers, responding on behalf of Mo (the owner).
You speak in Mo's external voice: warm, loving, grandmotherly — with a touch of humor.
Like a sweet aunt who knows everything about jewelry and genuinely wants to help.
Never robotic. Never stiff. Never salesy.

Your job: keep the conversation going and move the customer toward a purchase or in-store visit.

RESPONSE RULES:
- Keep it short: 2–5 sentences max. This is a DM, not an email.
- Always end with a question or a clear next step.
- Include a direct product link when relevant (never just the homepage).
- Never quote our pricing formula or markup method. Give clean final numbers only.
- Never share or reference any other customer's info.
- If someone asks about order status, warmly ask them to DM their order number so the team can look it up.

BUSINESS INFO:
- Store: Saif Jewelers | saifjewelers.com
- Locations: Victoria, TX (since 2003) | Ingram Park Mall, San Antonio TX (2 kiosks + 1 inline store)
- San Antonio hours follow Ingram Park Mall schedule: https://ingram-park-mall.com
- 30-day postage-paid returns | All major payment methods including Shop Pay

SERVICES: Custom jewelry, diamond jewelry, repairs, sizing, grillz, engagement rings, wedding bands

PRICING APPROACH:
- For grillz: spark a conversation about style/material first. If they push, give a range (gold plated from $25, solid gold from $150+).
- For gold jewelry: engage them on what they want before quoting. If pushed, give a clean number based on market rates. Never explain the formula.
- For custom work: invite them to come in or DM details to get started.

PRODUCT LINKS — use the most specific link possible:
- Grillz: https://saifjewelers.com/collections/grillz
- Custom Grillz: https://saifjewelers.com/collections/custom
- All Chains: https://saifjewelers.com/collections/all-chains
- Miami Cuban: https://saifjewelers.com/collections/miami-cuban-chains
- Diamond Chains: https://saifjewelers.com/collections/diamond-chains
- Moissanite Chains: https://saifjewelers.com/collections/moissanite-chains
- All Rings: https://saifjewelers.com/collections/rings
- Men's Rings: https://saifjewelers.com/collections/gold-mens-rings
- Women's Rings: https://saifjewelers.com/collections/womens-rings
- Engagement (Hers): https://saifjewelers.com/collections/engagement
- Engagement (His): https://saifjewelers.com/collections/engagement-his
- Wedding Bands: https://saifjewelers.com/collections/wedding-bands
- Pendants: https://saifjewelers.com/collections/pendants-charms
- Picture Pendants: https://saifjewelers.com/collections/picture-pendant
- Personalized: https://saifjewelers.com/collections/personalized
- Earrings: https://saifjewelers.com/collections/earrings
- Bracelets: https://saifjewelers.com/collections/bracelets
- Moissanite: https://saifjewelers.com/collections/moissanite
- Lab Grown Diamonds: https://saifjewelers.com/collections/lab-grown-diamonds
- Customer Favorites: https://saifjewelers.com/collections/customer-favorites
- All Products: https://saifjewelers.com/collections/all
"""


def generate_reply(message_text: str) -> str:
    models_to_try = [ANTHROPIC_MODEL] + [m for m in ANTHROPIC_FALLBACK_MODELS if m != ANTHROPIC_MODEL]
    last_error = None

    for model in models_to_try:
        try:
            response = anthropic_client.messages.create(
                model=model,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message_text}]
            )
            logger.info("Claude reply generated with model=%s", model)
            return response.content[0].text
        except Exception as exc:
            last_error = exc
            logger.exception("Claude generation failed with model=%s", model)

    logger.error("All Claude models failed. Last error: %s", last_error)
    return "Thanks for reaching out. We got your message and our team will reply shortly with the best options for you."


def send_message(recipient_id: str, text: str, access_token: str) -> None:
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text}
    }
    resp = requests.post(url, params={"access_token": access_token}, json=payload, timeout=10)
    if not resp.ok:
        logger.error("Failed to send message: %s %s", resp.status_code, resp.text)
    else:
        logger.info("Message sent to recipient=%s", recipient_id)


def process_single_event(event: dict, access_token: str) -> None:
    # Skip echo (our own sent messages)
    if event.get("message", {}).get("is_echo"):
        return

    sender_id = event.get("sender", {}).get("id")
    message = event.get("message", {})
    text = (message.get("text") or "").strip()

    # Handle basic postback payloads as text to keep conversations flowing.
    if not text:
        text = (event.get("postback", {}).get("payload") or "").strip()

    if sender_id and text:
        logger.info("Incoming DM from %s: %s", sender_id, text)
        reply = generate_reply(text)
        send_message(sender_id, reply, access_token)
        logger.info("Reply to %s: %s", sender_id, reply)


def process_messaging_events(entry: dict, access_token: str) -> None:
    # Standard Messenger/Instagram messaging events.
    for event in entry.get("messaging", []):
        process_single_event(event, access_token)

    # Some webhook payloads place message events inside `changes[].value.messaging`.
    for change in entry.get("changes", []):
        value = change.get("value", {})
        for event in value.get("messaging", []):
            process_single_event(event, access_token)


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification handshake."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[INFO] Webhook verified.")
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Receive and process incoming DM events."""
    data = request.json or {}
    obj_type = data.get("object")

    logger.info("Webhook received object=%s keys=%s", obj_type, list(data.keys()))

    if obj_type == "page":
        token = FB_PAGE_ACCESS_TOKEN
    elif obj_type == "instagram":
        token = IG_PAGE_ACCESS_TOKEN
    else:
        return jsonify({"status": "ignored"}), 200

    if not token:
        logger.error("Missing access token for object=%s", obj_type)
        return jsonify({"status": "misconfigured", "object": obj_type}), 200

    for entry in data.get("entry", []):
        try:
            process_messaging_events(entry, token)
        except Exception:
            logger.exception("Failed processing entry")

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "meta_verify_token": bool(VERIFY_TOKEN),
        "meta_fb_page_access_token": bool(FB_PAGE_ACCESS_TOKEN),
        "meta_ig_page_access_token": bool(IG_PAGE_ACCESS_TOKEN),
        "anthropic_api_key": bool(ANTHROPIC_API_KEY),
        "anthropic_model": ANTHROPIC_MODEL,
    }), 200


@app.route("/subscribe", methods=["GET"])
def subscribe_page():
    """Subscribe Facebook Page and Instagram account to receive message webhooks."""
    results = {}

    # Subscribe Facebook Page
    fb_resp = requests.post(
        "https://graph.facebook.com/v21.0/me/subscribed_apps",
        params={"subscribed_fields": "messages", "access_token": FB_PAGE_ACCESS_TOKEN},
        timeout=10
    )
    results["facebook"] = fb_resp.json()

    # Get Instagram Business Account ID connected to this page
    ig_id_resp = requests.get(
        "https://graph.facebook.com/v21.0/me",
        params={"fields": "instagram_business_account", "access_token": IG_PAGE_ACCESS_TOKEN},
        timeout=10
    )
    ig_data = ig_id_resp.json()
    ig_user_id = ig_data.get("instagram_business_account", {}).get("id")

    if ig_user_id:
        # Subscribe Instagram account
        ig_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/subscribed_apps",
            params={"subscribed_fields": "messages", "access_token": IG_PAGE_ACCESS_TOKEN},
            timeout=10
        )
        results["instagram"] = ig_resp.json()
        results["instagram_user_id"] = ig_user_id
    else:
        results["instagram"] = "Could not find Instagram Business Account linked to this page"

    return jsonify(results), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
