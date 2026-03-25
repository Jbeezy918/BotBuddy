"""
Anonymous Event Tracking

Tracks feature usage without any personal identification.
All data is aggregate - we know "memory import was used 500 times"
but NOT "user X imported memories about Y".
"""

import asyncio
import json
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
import httpx

from ..config import settings


class EventType(str, Enum):
    """Anonymous event types - just feature names, no personal data"""
    APP_STARTED = "app_started"
    CHAT_MESSAGE = "chat_message"  # Just counts, no content
    MEMORY_IMPORTED = "memory_imported"
    MEMORY_CREATED = "memory_created"
    GREETING_REQUESTED = "greeting_requested"
    CHECKIN_MORNING = "checkin_morning"
    CHECKIN_EVENING = "checkin_evening"
    SETTINGS_CHANGED = "settings_changed"
    MODEL_SWITCHED = "model_switched"
    ERROR_OCCURRED = "error_occurred"
    FEEDBACK_SENT = "feedback_sent"
    SESSION_ENDED = "session_ended"


class Analytics:
    """
    Privacy-respecting analytics tracker.

    What we track:
    - Feature usage counts (how many times X was used)
    - Success/failure rates
    - App version
    - General session info (duration, not timestamps)

    What we DON'T track:
    - User identity (no IDs, no IPs, no names)
    - Conversation content
    - Memory content
    - Personal information of any kind
    - Exact timestamps (just date for aggregation)
    """

    def __init__(self):
        self.enabled = False
        self.endpoint = settings.analytics_endpoint
        self.local_cache: list = []
        self.session_events: Dict[str, int] = {}
        self._consent_path = Path.home() / ".robobuddy" / "analytics_consent.json"
        self._load_consent()

    def _load_consent(self):
        """Load user's analytics consent preference"""
        try:
            if self._consent_path.exists():
                with open(self._consent_path) as f:
                    data = json.load(f)
                    self.enabled = data.get("enabled", False)
        except:
            self.enabled = False

    def _save_consent(self, enabled: bool):
        """Save user's analytics consent preference"""
        self._consent_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._consent_path, "w") as f:
            json.dump({
                "enabled": enabled,
                "consented_at": date.today().isoformat(),
                "version": "1.0"
            }, f)
        self.enabled = enabled

    def opt_in(self):
        """User opts into anonymous analytics"""
        self._save_consent(True)
        return True

    def opt_out(self):
        """User opts out of analytics"""
        self._save_consent(False)
        self.local_cache.clear()
        return True

    def get_consent_status(self) -> dict:
        """Get current consent status for UI"""
        return {
            "enabled": self.enabled,
            "what_we_track": [
                "Feature usage counts (e.g., 'chat used 50 times')",
                "Success/failure rates",
                "App version",
                "Session duration (not times)"
            ],
            "what_we_dont_track": [
                "Your identity",
                "Your conversations",
                "Your memories",
                "Your IP address",
                "Any personal information"
            ]
        }

    async def track(
        self,
        event: EventType,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track an anonymous event.

        Args:
            event: The type of event (feature used)
            success: Whether the action succeeded
            metadata: Optional non-personal metadata (e.g., {"model": "ollama"})
        """
        if not self.enabled:
            return

        # Build anonymous event - NO personal data
        event_data = {
            "event": event.value,
            "success": success,
            "date": date.today().isoformat(),  # Just date, not time
            "version": "1.0.0",
            "metadata": self._sanitize_metadata(metadata or {})
        }

        # Count in session
        self.session_events[event.value] = self.session_events.get(event.value, 0) + 1

        # Add to local cache
        self.local_cache.append(event_data)

        # Batch send if we have enough events
        if len(self.local_cache) >= 10:
            await self._send_batch()

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any potentially personal data from metadata"""
        safe_keys = {"model", "feature", "error_type", "duration_bucket"}
        return {k: v for k, v in metadata.items() if k in safe_keys}

    async def _send_batch(self):
        """Send batched events to analytics endpoint"""
        if not self.endpoint or not self.local_cache:
            return

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    self.endpoint,
                    json={"events": self.local_cache},
                    headers={"Content-Type": "application/json"}
                )
            self.local_cache.clear()
        except:
            # Silently fail - analytics should never break the app
            pass

    async def flush(self):
        """Flush any remaining events (call on app shutdown)"""
        if self.enabled and self.local_cache:
            await self._send_batch()

    def get_session_summary(self) -> Dict[str, int]:
        """Get summary of events in current session"""
        return dict(self.session_events)


# Global instance
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    """Get the global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics


async def track_event(
    event: EventType,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
):
    """Convenience function to track an event"""
    analytics = get_analytics()
    await analytics.track(event, success, metadata)
