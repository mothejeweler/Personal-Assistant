"""
TikTok DM integration.

This backend uses a generic inbound webhook and outbound relay so it can work
with an official TikTok messaging app, Make, Zapier, Pipedream, or a custom
bridge without changing Raj's core message pipeline.
"""

import hashlib
import hmac
import os
from typing import Any, Dict, Optional

import requests


class TikTokClient:
    def __init__(self):
        self.outbound_webhook_url = os.getenv("TIKTOK_DM_OUTBOUND_WEBHOOK_URL")
        self.outbound_token = os.getenv("TIKTOK_DM_OUTBOUND_TOKEN")
        self.verify_token = os.getenv("TIKTOK_DM_WEBHOOK_VERIFY_TOKEN")
        self.signing_secret = os.getenv("TIKTOK_DM_WEBHOOK_SECRET")
        self.timeout_seconds = int(os.getenv("TIKTOK_DM_TIMEOUT_SECONDS", "15"))

    def verify_webhook_signature(self, body: bytes, signature: Optional[str]) -> bool:
        if not self.signing_secret:
            return True
        if not signature:
            return False

        digest = hmac.new(
            self.signing_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        candidates = [signature.strip()]
        if "=" in signature:
            candidates.append(signature.split("=", 1)[1].strip())

        return any(hmac.compare_digest(digest, candidate) for candidate in candidates)

    def verify_challenge(self, token: Optional[str], challenge: Optional[str]) -> tuple[bool, str]:
        if not challenge:
            return False, "Missing challenge"
        if self.verify_token and token != self.verify_token:
            return False, "Invalid verify token"
        return True, challenge

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = payload.get("event") or payload.get("data") or payload
        sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
        user = event.get("user") if isinstance(event.get("user"), dict) else {}
        message_obj = event.get("message") if isinstance(event.get("message"), dict) else {}

        raw_message = event.get("message")
        if isinstance(raw_message, dict):
            message_text = raw_message.get("text") or raw_message.get("body")
        else:
            message_text = raw_message or event.get("text") or payload.get("message")

        sender_id = (
            payload.get("from")
            or event.get("from")
            or sender.get("id")
            or sender.get("username")
            or user.get("username")
            or user.get("id")
        )
        customer_name = (
            payload.get("customer_name")
            or sender.get("display_name")
            or sender.get("name")
            or user.get("display_name")
            or user.get("name")
        )
        event_id = (
            payload.get("event_id")
            or event.get("event_id")
            or event.get("message_id")
            or message_obj.get("id")
        )
        is_general_tab = bool(payload.get("is_general_tab") or event.get("is_general_tab"))

        if not sender_id or not message_text:
            raise ValueError("TikTok webhook payload must include sender and message text")

        return {
            "from": str(sender_id),
            "message": str(message_text),
            "customer_name": customer_name,
            "event_id": str(event_id) if event_id else None,
            "is_general_tab": is_general_tab,
        }

    def send_direct_message(self, recipient_id: str, message: str) -> dict:
        if not self.outbound_webhook_url:
            return {
                "status": "error",
                "error": "TikTok outbound relay is not configured",
                "channel": "tiktok",
            }

        headers = {"Content-Type": "application/json"}
        if self.outbound_token:
            headers["Authorization"] = f"Bearer {self.outbound_token}"

        payload = {
            "channel": "tiktok",
            "recipient_id": recipient_id,
            "message": message,
        }

        try:
            response = requests.post(
                self.outbound_webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

            body: Dict[str, Any]
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}

            return {
                "status": body.get("status", "success"),
                "message_id": body.get("message_id") or body.get("id"),
                "channel": "tiktok",
                "raw": body,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "channel": "tiktok",
            }
