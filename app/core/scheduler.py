"""
Proactive Scheduler - SQLite Edition

Handles automatic check-ins and follow-ups.
"""
from datetime import datetime, timedelta
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from ..config import settings
from ..memory import MemoryManager
from ..memory.models import UserProfile
from ..personality.companion import Companion
from ..notifications.notifier import Notifier


class ProactiveScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.memory = MemoryManager()
        self.companion = Companion()
        self.notifier = Notifier()

    def start(self):
        """Start scheduler"""
        # Morning check-ins
        self.scheduler.add_job(
            self.run_morning_checkins,
            CronTrigger(hour=settings.morning_checkin_hour, minute=0),
            id="morning_checkins"
        )

        # Evening check-ins
        self.scheduler.add_job(
            self.run_evening_checkins,
            CronTrigger(hour=settings.evening_checkin_hour, minute=0),
            id="evening_checkins"
        )

        # Inactivity check (every 6 hours)
        self.scheduler.add_job(
            self.check_inactive_users,
            CronTrigger(hour="*/6"),
            id="inactivity_checks"
        )

        # Follow-ups (every 2 hours)
        self.scheduler.add_job(
            self.process_followups,
            CronTrigger(hour="*/2", minute=30),
            id="followup_processing"
        )

        self.scheduler.start()
        print(f"[{settings.companion_name}] Proactive scheduler started")

    def stop(self):
        self.scheduler.shutdown()

    async def run_morning_checkins(self):
        """Send morning check-ins"""
        print("Running morning check-ins...")
        users = await self.memory.get_all_users_for_checkin("morning")

        for user in users:
            if not user.phone_number:
                continue

            try:
                tz = pytz.timezone(user.timezone)
                hour = datetime.now(tz).hour
                if not (7 <= hour <= 10):
                    continue
            except:
                pass

            message = await self.companion.generate_proactive_message(user.id, "morning")
            await self.notifier.send_checkin(user.phone_number, message)

    async def run_evening_checkins(self):
        """Send evening check-ins"""
        print("Running evening check-ins...")
        users = await self.memory.get_all_users_for_checkin("evening")

        for user in users:
            if not user.phone_number:
                continue

            try:
                tz = pytz.timezone(user.timezone)
                hour = datetime.now(tz).hour
                if not (19 <= hour <= 22):
                    continue
            except:
                pass

            message = await self.companion.generate_proactive_message(user.id, "evening")
            await self.notifier.send_checkin(user.phone_number, message)

    async def check_inactive_users(self):
        """Check on users who haven't talked recently"""
        print("Checking inactive users...")
        users = await self.memory.get_inactive_users(settings.inactivity_hours_before_checkin)

        for user in users:
            if not user.phone_number:
                continue

            message = await self.companion.generate_proactive_message(user.id, "inactivity")
            await self.notifier.send_checkin(user.phone_number, message)

    async def process_followups(self):
        """Process event follow-ups"""
        print("Processing follow-ups...")
        # Get all users and check their follow-ups
        users = await self.memory.get_all_users_for_checkin("proactive")

        for user in users:
            if not user.phone_number:
                continue

            followups = await self.memory.get_upcoming_followups(user.id)
            if followups:
                message = await self.companion.generate_proactive_message(user.id, "followup")
                await self.notifier.send_checkin(user.phone_number, message)
