# Personality System
from .companion import Companion
from .prompts import SYSTEM_PROMPT, get_time_aware_greeting

__all__ = ["Companion", "SYSTEM_PROMPT", "get_time_aware_greeting"]
