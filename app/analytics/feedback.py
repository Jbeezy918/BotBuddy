"""
Voluntary Feedback Collection

Users can optionally send feedback about features they want,
issues they've encountered, or general suggestions.

This is 100% voluntary - the user chooses to send feedback.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import httpx

from ..config import settings


class FeedbackType(str, Enum):
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"
    LIKE = "like"  # What they liked
    IMPROVEMENT = "improvement"  # What could be better


@dataclass
class Feedback:
    """A piece of user feedback - voluntarily submitted"""
    feedback_type: FeedbackType
    message: str
    date: str  # Just the date, not exact time
    app_version: str = "1.0.0"

    # Optional context the user can choose to include
    feature_context: Optional[str] = None  # Which feature they're commenting on


class FeedbackCollector:
    """
    Collects voluntary user feedback.

    This is NOT automatic - users actively choose to send feedback.
    We don't collect any identifying information.
    """

    def __init__(self):
        self.endpoint = settings.feedback_endpoint
        self._local_path = Path.home() / ".robobuddy" / "feedback_queue.json"

    async def submit(
        self,
        feedback_type: FeedbackType,
        message: str,
        feature_context: Optional[str] = None
    ) -> bool:
        """
        Submit voluntary feedback.

        Args:
            feedback_type: Type of feedback
            message: The user's feedback message
            feature_context: Optional - which feature they're commenting on

        Returns:
            True if submitted successfully
        """
        feedback = Feedback(
            feedback_type=feedback_type,
            message=message,
            date=date.today().isoformat(),
            feature_context=feature_context
        )

        # Try to send immediately
        if self.endpoint:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        self.endpoint,
                        json=asdict(feedback),
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code == 200:
                        return True
            except:
                pass

        # If sending failed, save locally
        self._save_locally(feedback)
        return True  # Still return true - we saved it

    def _save_locally(self, feedback: Feedback):
        """Save feedback locally if we can't send it"""
        self._local_path.parent.mkdir(parents=True, exist_ok=True)

        queue = []
        if self._local_path.exists():
            try:
                with open(self._local_path) as f:
                    queue = json.load(f)
            except:
                queue = []

        queue.append(asdict(feedback))

        with open(self._local_path, "w") as f:
            json.dump(queue, f, indent=2)

    def get_pending_count(self) -> int:
        """Get count of feedback waiting to be sent"""
        if not self._local_path.exists():
            return 0
        try:
            with open(self._local_path) as f:
                return len(json.load(f))
        except:
            return 0

    async def flush_pending(self) -> int:
        """Try to send any pending feedback"""
        if not self._local_path.exists() or not self.endpoint:
            return 0

        try:
            with open(self._local_path) as f:
                queue = json.load(f)
        except:
            return 0

        if not queue:
            return 0

        sent = 0
        remaining = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for feedback_data in queue:
                try:
                    response = await client.post(
                        self.endpoint,
                        json=feedback_data,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code == 200:
                        sent += 1
                    else:
                        remaining.append(feedback_data)
                except:
                    remaining.append(feedback_data)

        # Update queue with unsent items
        with open(self._local_path, "w") as f:
            json.dump(remaining, f, indent=2)

        return sent


# Convenience function
async def send_feedback(
    feedback_type: FeedbackType,
    message: str,
    feature_context: Optional[str] = None
) -> bool:
    """Quick way to submit feedback"""
    collector = FeedbackCollector()
    return await collector.submit(feedback_type, message, feature_context)
