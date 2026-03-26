"""Runtime editor for owner-approved live behavior changes.

Allows owner-only proposals like:
- "learn new habit: ..."
- "set refresh minutes to 30"
- "set sales tone to calm"

Every change requires explicit CONFIRM from the same owner.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RuntimeEditor:
    def __init__(self, path: str = "data/runtime_editor.json", default_refresh_minutes: int = 60) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.default_refresh_minutes = default_refresh_minutes
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.data = self._load()

    def _default_data(self) -> Dict[str, Any]:
        return {
            "settings": {
                "personality_refresh_minutes": int(self.default_refresh_minutes),
                "realtime_edit_permissions": True,
                "sales_tone_bias": "balanced",
            },
            "habits": [],
            "updated_at": None,
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            data = self._default_data()
            self._save(data)
            return data
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            base = self._default_data()
            base["settings"].update(loaded.get("settings", {}))
            base["habits"] = loaded.get("habits", [])
            base["updated_at"] = loaded.get("updated_at")
            return base
        except Exception:
            data = self._default_data()
            self._save(data)
            return data

    def _save(self, data: Optional[Dict[str, Any]] = None) -> None:
        payload = data if data is not None else self.data
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.data.get("settings", {}).get(key, default)

    def get_status(self) -> Dict[str, Any]:
        return {
            "settings": self.data.get("settings", {}),
            "habit_count": len(self.data.get("habits", [])),
            "habits": self.data.get("habits", []),
            "pending_owner_count": len(self.pending),
            "updated_at": self.data.get("updated_at"),
        }

    def get_prompt_appendix(self) -> str:
        settings = self.data.get("settings", {})
        habits: List[str] = self.data.get("habits", [])[-15:]

        lines = [
            "LIVE OWNER OVERRIDES (RUNTIME)",
            f"- sales_tone_bias: {settings.get('sales_tone_bias', 'balanced')}",
        ]

        if habits:
            lines.append("- Learned habits to follow:")
            for habit in habits:
                lines.append(f"  - {habit}")

        return "\n".join(lines)

    def _parse_bool(self, value: str) -> Optional[bool]:
        v = value.strip().lower()
        if v in {"true", "on", "yes", "enabled", "enable"}:
            return True
        if v in {"false", "off", "no", "disabled", "disable"}:
            return False
        return None

    def _normalize_setting_key(self, raw: str) -> Optional[str]:
        key = re.sub(r"\s+", "_", raw.strip().lower())
        aliases = {
            "refresh": "personality_refresh_minutes",
            "refresh_minutes": "personality_refresh_minutes",
            "personality_refresh": "personality_refresh_minutes",
            "personality_refresh_minutes": "personality_refresh_minutes",
            "auto_learning_refresh_minutes": "personality_refresh_minutes",
            "realtime_edit_permissions": "realtime_edit_permissions",
            "realtime_permissions": "realtime_edit_permissions",
            "live_edit_permissions": "realtime_edit_permissions",
            "sales_tone": "sales_tone_bias",
            "sales_tone_bias": "sales_tone_bias",
            "tone": "sales_tone_bias",
        }
        return aliases.get(key)

    def _parse_proposal(self, text: str) -> Optional[Dict[str, Any]]:
        stripped = text.strip()

        # Habit learning
        habit_match = re.search(r"(?:learn(?:\s+a)?\s+new\s+habit|new\s+habit|habit)\s*[:\-]?\s*(.+)$", stripped, re.I)
        if habit_match:
            habit = habit_match.group(1).strip().strip('"')
            if habit:
                return {
                    "action": "add_habit",
                    "habit": habit,
                    "summary": f"Add new habit: {habit}",
                }

        # Remove habit by index
        remove_match = re.search(r"remove\s+habit\s+#?(\d+)", stripped, re.I)
        if remove_match:
            idx = int(remove_match.group(1))
            return {
                "action": "remove_habit",
                "index": idx,
                "summary": f"Remove habit #{idx}",
            }

        # Set/change setting
        set_match = re.search(r"(?:set|change|update)\s+(?:setting\s+)?([a-zA-Z_ ]+?)\s*(?:to|=)\s*(.+)$", stripped, re.I)
        if set_match:
            raw_key = set_match.group(1)
            raw_value = set_match.group(2).strip().strip('"')
            key = self._normalize_setting_key(raw_key)
            if not key:
                return {
                    "action": "invalid",
                    "summary": "Unknown setting key.",
                    "error": "Unknown setting key. Allowed: refresh minutes, realtime edit permissions, sales tone.",
                }

            if key == "personality_refresh_minutes":
                num_match = re.search(r"\d+", raw_value)
                if not num_match:
                    return {
                        "action": "invalid",
                        "summary": "Invalid refresh minutes value.",
                        "error": "Refresh minutes must be a number between 5 and 1440.",
                    }
                value = int(num_match.group(0))
                if value < 5 or value > 1440:
                    return {
                        "action": "invalid",
                        "summary": "Refresh minutes out of range.",
                        "error": "Refresh minutes must be between 5 and 1440.",
                    }
            elif key == "realtime_edit_permissions":
                bool_value = self._parse_bool(raw_value)
                if bool_value is None:
                    return {
                        "action": "invalid",
                        "summary": "Invalid boolean value.",
                        "error": "Use on/off, true/false, yes/no for realtime edit permissions.",
                    }
                value = bool_value
            elif key == "sales_tone_bias":
                tone = raw_value.lower().strip()
                allowed = {"balanced", "calm", "hype", "protective", "negotiation"}
                if tone not in allowed:
                    return {
                        "action": "invalid",
                        "summary": "Invalid tone value.",
                        "error": "Tone must be one of: balanced, calm, hype, protective, negotiation.",
                    }
                value = tone
            else:
                return None

            return {
                "action": "set_setting",
                "key": key,
                "value": value,
                "summary": f"Set {key} to {value}",
            }

        return None

    def _apply(self, proposal: Dict[str, Any]) -> str:
        action = proposal.get("action")
        if action == "add_habit":
            habit = proposal["habit"]
            self.data["habits"].append(habit)
            self._save()
            return f"Confirmed. Learned new habit: {habit}"

        if action == "remove_habit":
            idx = int(proposal["index"])
            habits = self.data.get("habits", [])
            if idx < 1 or idx > len(habits):
                return f"Cannot remove habit #{idx}. Current habit count is {len(habits)}."
            removed = habits.pop(idx - 1)
            self._save()
            return f"Confirmed. Removed habit #{idx}: {removed}"

        if action == "set_setting":
            key = proposal["key"]
            value = proposal["value"]
            self.data["settings"][key] = value
            self._save()
            return f"Confirmed. Updated setting: {key} = {value}"

        return "No actionable change found."

    def handle_owner_message(self, owner_id: str, message_text: str) -> Tuple[bool, str]:
        text = (message_text or "").strip()
        lower = text.lower()

        if lower in {"show settings", "raj settings", "show habits", "status"}:
            status = self.get_status()
            habits = status.get("habits", [])
            habit_lines = "\n".join([f"{i+1}. {h}" for i, h in enumerate(habits[-10:])]) if habits else "(none)"
            reply = (
                "Runtime settings:\n"
                f"- personality_refresh_minutes: {status['settings'].get('personality_refresh_minutes')}\n"
                f"- realtime_edit_permissions: {status['settings'].get('realtime_edit_permissions')}\n"
                f"- sales_tone_bias: {status['settings'].get('sales_tone_bias')}\n"
                "Learned habits (latest):\n"
                f"{habit_lines}"
            )
            return True, reply

        if lower in {"confirm", "yes confirm", "approve", "yes, confirm"}:
            pending = self.pending.pop(owner_id, None)
            if not pending:
                return True, "No pending change to confirm."
            return True, self._apply(pending)

        if lower in {"cancel", "no", "deny", "reject"}:
            existed = owner_id in self.pending
            self.pending.pop(owner_id, None)
            return True, "Pending change canceled." if existed else "No pending change to cancel."

        proposal = self._parse_proposal(text)
        if proposal is None:
            return False, ""

        if proposal.get("action") == "invalid":
            return True, proposal.get("error", "Invalid request.")

        self.pending[owner_id] = proposal
        return (
            True,
            "I can do that. Please reply CONFIRM to apply this change or CANCEL to discard.\n"
            f"Proposed: {proposal.get('summary')}"
        )
