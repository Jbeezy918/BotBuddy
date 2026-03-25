# Core components
# Note: Import scheduler only when needed to avoid circular imports
from .brain import CompanionBrain, get_brain

__all__ = ["CompanionBrain", "get_brain"]
