"""
RoboBuddy Configuration - Multi-Model Edition

Now uses local Ollama models by default (100% free).
Anthropic API is optional fallback.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    # App
    app_name: str = "RoboBuddy"
    debug: bool = False

    # Database (SQLite - free, local)
    # Use /tmp on cloud, ~/.robobuddy locally
    database_path: str = str(Path("/tmp/robobuddy.db") if Path("/opt/render").exists() else Path.home() / ".robobuddy" / "robobuddy.db")

    # Ollama (primary - free)
    ollama_url: str = "http://localhost:11434"

    # Model assignments (customize these!)
    model_conversation: str = "gemma3:12b"
    model_fast: str = "llama3.2:latest"
    model_smart: str = "qwen3:14b"

    # Anthropic API (optional fallback)
    anthropic_api_key: Optional[str] = None

    # Groq API (free tier - 14,400 requests/day)
    groq_api_key: Optional[str] = None

    # Optional - Voice
    elevenlabs_api_key: Optional[str] = None
    assemblyai_api_key: Optional[str] = None

    # Optional - Notifications
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # Companion Personality
    companion_name: str = "Sage"

    # Proactive Settings
    morning_checkin_hour: int = 8
    evening_checkin_hour: int = 20
    inactivity_hours_before_checkin: int = 24

    # Analytics (anonymous, opt-in only)
    analytics_endpoint: Optional[str] = None  # Set to your endpoint to collect
    feedback_endpoint: Optional[str] = None   # Set to your endpoint for feedback

    # Public Launch Controls
    service_enabled: bool = True  # Kill switch - set to False to disable all API access
    paywall_enabled: bool = False  # When True, requires valid API key
    api_keys: str = ""  # Comma-separated list of valid API keys (when paywall enabled)
    rate_limit_per_minute: int = 30  # Requests per minute per IP
    trial_expires: Optional[str] = None  # ISO date when free trial ends (e.g., "2026-04-01")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure database directory exists (skip for /tmp)
try:
    db_parent = Path(settings.database_path).parent
    if str(db_parent) != "/tmp":
        db_parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass  # Cloud deployments may have restricted filesystem
