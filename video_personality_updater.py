"""
Video Personality Updater for Raj

Checks a YouTube channel feed for newly posted videos, analyzes personality signals,
and stores incremental personality insights that Raj can load at response time.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests
from anthropic import Anthropic

logger = logging.getLogger(__name__)

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


class PersonalityVideoUpdater:
    """Keeps a rolling personality delta based on newly posted YouTube videos."""

    def __init__(
        self,
        channel_id: Optional[str],
        rss_url: Optional[str] = None,
        state_path: str = "data/video_personality_state.json",
        insights_path: str = "data/personality_delta.md",
    ) -> None:
        self.channel_id = (channel_id or "").strip()
        self.rss_url = (rss_url or "").strip() or self._default_rss_url(self.channel_id)
        self.state_path = Path(state_path)
        self.insights_path = Path(insights_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.insights_path.parent.mkdir(parents=True, exist_ok=True)

        self.client = Anthropic()

    @staticmethod
    def _default_rss_url(channel_id: str) -> str:
        if not channel_id:
            return ""
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    def enabled(self) -> bool:
        return bool(self.rss_url)

    def load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {
                "processed_video_ids": [],
                "last_sync_at": None,
                "last_success_at": None,
            }
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed reading video personality state. Rebuilding state.")
            return {
                "processed_video_ids": [],
                "last_sync_at": None,
                "last_success_at": None,
            }

    def save_state(self, state: Dict[str, Any]) -> None:
        state["last_sync_at"] = datetime.now(timezone.utc).isoformat()
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def fetch_feed_entries(self) -> List[Dict[str, str]]:
        if not self.rss_url:
            return []

        response = requests.get(self.rss_url, timeout=20)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        entries: List[Dict[str, str]] = []

        for entry in root.findall("atom:entry", ATOM_NS):
            video_id = (entry.findtext("yt:videoId", default="", namespaces=ATOM_NS) or "").strip()
            title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ATOM_NS) or "").strip()
            link_elem = entry.find("atom:link", ATOM_NS)
            video_url = (link_elem.attrib.get("href", "") if link_elem is not None else "").strip()

            if video_id:
                entries.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "published": published,
                        "video_url": video_url,
                    }
                )

        return entries

    def analyze_video(self, video: Dict[str, str]) -> str:
        """
        Analyze one new video for personality drift and evolving speaking patterns.

        Note: this version uses available feed metadata. If transcript ingestion is added,
        the prompt can include transcript text for higher-fidelity learning.
        """
        system_prompt = (
            "You are analyzing Mo The Jeweler's latest content to extract ONLY NEW personality deltas. "
            "Return compact markdown with sections: New Phrases, Tone Shifts, Audience Signals, "
            "Do/Don't Adjustments. Only include changes relative to prior voice."
        )

        user_prompt = (
            "Analyze this newly posted video metadata for personality evolution. "
            "If signal is weak, explicitly say low-confidence and avoid overfitting.\n\n"
            f"Video Title: {video.get('title', '')}\n"
            f"Published: {video.get('published', '')}\n"
            f"URL: {video.get('video_url', '')}\n"
        )

        result = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return result.content[0].text.strip()

    def append_delta(self, video: Dict[str, str], delta_text: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        block = (
            f"\n## {timestamp} | {video.get('title', 'Untitled')}\n"
            f"- Video: {video.get('video_url', '')}\n"
            f"- Published: {video.get('published', '')}\n\n"
            f"{delta_text}\n"
        )

        if not self.insights_path.exists():
            header = (
                "# Raj Personality Delta Log\n"
                "Auto-generated incremental updates from newly posted channel videos.\n"
                "Use these deltas as additive adjustments, not replacements for base personality.\n"
            )
            self.insights_path.write_text(header + block, encoding="utf-8")
        else:
            with self.insights_path.open("a", encoding="utf-8") as f:
                f.write(block)

    def get_runtime_delta_text(self, max_chars: int = 6000) -> str:
        if not self.insights_path.exists():
            return ""
        content = self.insights_path.read_text(encoding="utf-8")
        return content[-max_chars:]

    def sync_once(self, max_new_videos: int = 3) -> Dict[str, Any]:
        if not self.enabled():
            logger.info("Video personality updater disabled: no RSS/channel configured.")
            return {"status": "disabled", "processed": 0}

        state = self.load_state()
        processed_ids = set(state.get("processed_video_ids", []))

        entries = self.fetch_feed_entries()
        new_entries = [e for e in entries if e["video_id"] not in processed_ids]

        if not new_entries:
            state["last_success_at"] = datetime.now(timezone.utc).isoformat()
            self.save_state(state)
            return {"status": "ok", "processed": 0, "message": "No new videos"}

        # Process oldest-to-newest to preserve timeline.
        new_entries = list(reversed(new_entries))[:max_new_videos]

        processed_count = 0
        for video in new_entries:
            try:
                delta = self.analyze_video(video)
                self.append_delta(video, delta)
                processed_ids.add(video["video_id"])
                processed_count += 1
            except Exception:
                logger.exception("Failed processing video %s", video.get("video_id"))

        state["processed_video_ids"] = sorted(processed_ids)
        state["last_success_at"] = datetime.now(timezone.utc).isoformat()
        self.save_state(state)

        return {
            "status": "ok",
            "processed": processed_count,
            "new_found": len(new_entries),
            "insights_path": str(self.insights_path),
            "state_path": str(self.state_path),
        }
