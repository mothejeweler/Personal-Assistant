"""
Saif Jewelers — Auto DM Response Bot
Handles incoming Instagram and Facebook Messenger DMs,
generates replies using Claude, and sends them automatically.
"""

import os
import requests
from flask import Flask, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
FB_PAGE_ACCESS_TOKEN = os.getenv("META_FB_PAGE_ACCESS_TOKEN")
IG_PAGE_ACCESS_TOKEN = os.getenv("META_IG_PAGE_ACCESS_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_text}]
    )
    return response.content[0].text


def send_message(recipient_id: str, text: str, access_token: str) -> None:
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": access_token
    }
    resp = requests.post(url, json=payload, timeout=10)
    if not resp.ok:
        print(f"[ERROR] Failed to send message: {resp.status_code} {resp.text}")


def process_messaging_events(entry: dict, access_token: str) -> None:
    for event in entry.get("messaging", []):
        # Skip echo (our own sent messages)
        if event.get("message", {}).get("is_echo"):
            continue

        sender_id = event.get("sender", {}).get("id")
        message = event.get("message", {})
        text = message.get("text", "").strip()

        if sender_id and text:
            print(f"[DM] From {sender_id}: {text}")
            reply = generate_reply(text)
            send_message(sender_id, reply, access_token)
            print(f"[REPLY] To {sender_id}: {reply}")


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
    data = request.json
    obj_type = data.get("object")

    if obj_type == "page":
        token = FB_PAGE_ACCESS_TOKEN
    elif obj_type == "instagram":
        token = IG_PAGE_ACCESS_TOKEN
    else:
        return jsonify({"status": "ignored"}), 200

    for entry in data.get("entry", []):
        process_messaging_events(entry, token)

    return jsonify({"status": "ok"}), 200


@app.route("/subscribe", methods=["GET"])
def subscribe_page():
    """Subscribe the Facebook Page to receive message webhooks."""
    resp = requests.post(
        "https://graph.facebook.com/v21.0/me/subscribed_apps",
        params={
            "subscribed_fields": "messages",
            "access_token": FB_PAGE_ACCESS_TOKEN
        },
        timeout=10
    )
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
