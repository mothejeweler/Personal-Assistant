"""Voice synthesis helper for Raj.

Supports provider-based text-to-speech with a simple interface.
Current provider: ElevenLabs.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

import requests


class VoiceSynthesizer:
    """Provider-agnostic wrapper for Raj voice generation."""

    def __init__(self, provider: str = "none") -> None:
        self.provider = (provider or "none").strip().lower()

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
        self.elevenlabs_model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()

    def status(self) -> Dict[str, object]:
        if self.provider == "elevenlabs":
            return {
                "provider": self.provider,
                "configured": bool(self.elevenlabs_api_key and self.elevenlabs_voice_id),
                "missing": [
                    key
                    for key, ok in {
                        "ELEVENLABS_API_KEY": bool(self.elevenlabs_api_key),
                        "ELEVENLABS_VOICE_ID": bool(self.elevenlabs_voice_id),
                    }.items()
                    if not ok
                ],
                "model": self.elevenlabs_model_id,
            }

        return {
            "provider": self.provider,
            "configured": False,
            "missing": ["VOICE_PROVIDER=elevenlabs"],
        }

    def synthesize(self, text: str) -> Tuple[bytes, str]:
        """Convert text into speech audio bytes.

        Returns:
            (audio_bytes, content_type)
        """
        text = (text or "").strip()
        if not text:
            raise ValueError("Text is required for voice synthesis")

        if self.provider != "elevenlabs":
            raise RuntimeError("Voice provider is not enabled. Set VOICE_PROVIDER=elevenlabs")

        if not self.elevenlabs_api_key or not self.elevenlabs_voice_id:
            raise RuntimeError("Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": self.elevenlabs_model_id,
            "voice_settings": {
                "stability": 0.35,
                "similarity_boost": 0.8,
                "style": 0.2,
                "use_speaker_boost": True,
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.content, "audio/mpeg"
