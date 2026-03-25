"""
Notification System

Handles:
- SMS notifications via Twilio (optional)
- Push notifications via Firebase (future)
- Email notifications (future)
"""
from typing import Optional

from ..config import settings

# Optional Twilio import
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None


class Notifier:
    def __init__(self):
        self.twilio_enabled = TWILIO_AVAILABLE and bool(
            settings.twilio_account_sid and
            settings.twilio_auth_token and
            settings.twilio_phone_number
        )

        if self.twilio_enabled:
            self.twilio = TwilioClient(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
        else:
            self.twilio = None

    async def send_sms(self, to_number: str, message: str) -> bool:
        """Send an SMS message"""
        if not self.twilio_enabled:
            print(f"[SMS disabled] Would send to {to_number}: {message[:50]}...")
            return False

        try:
            self.twilio.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to_number
            )
            return True
        except Exception as e:
            print(f"SMS send failed: {e}")
            return False

    async def send_checkin(
        self,
        user_phone: str,
        message: str,
        companion_name: str = None
    ) -> bool:
        """Send a check-in message from the companion"""
        name = companion_name or settings.companion_name
        formatted = f"[{name}] {message}"
        return await self.send_sms(user_phone, formatted)

    async def send_push_notification(
        self,
        user_id: str,
        title: str,
        body: str
    ) -> bool:
        """Send push notification - placeholder for Firebase"""
        print(f"[Push disabled] {user_id}: {title}")
        return False
