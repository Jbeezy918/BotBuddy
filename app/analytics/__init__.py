"""
RoboBuddy Anonymous Analytics

Privacy-first analytics that tracks WHAT features are used, not WHO uses them.
- No user IDs
- No IP addresses
- No personal data
- No conversation content
- Opt-in only
"""

from .tracker import Analytics, track_event
from .feedback import FeedbackCollector

__all__ = ["Analytics", "track_event", "FeedbackCollector"]
