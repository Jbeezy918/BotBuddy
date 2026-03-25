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
    database_path: str = str(Path.home() / ".robobuddy" / "robobuddy.db")

    # Ollama (primary - free)
    ollama_url: str = "http://localhost:11434"

    # Model assignments (customize these!)
    model_conversation: str = "gemma3:12b"
    model_fast: str = "llama3.2:latest"
    model_smart: str = "qwen3:14b"

    # Anthropic API (optional fallback)
    anthropic_api_key: Optional[str] = None

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure database directory exists
Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
