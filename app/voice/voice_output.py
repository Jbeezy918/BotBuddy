"""
Voice Output via ElevenLabs

Generates natural, emotionally-appropriate voice responses.
"""
from typing import Optional
import io

from ..config import settings


class VoiceOutput:
    def __init__(self):
        self.enabled = bool(settings.elevenlabs_api_key)
        self.voice_id = settings.companion_voice_id

        if self.enabled:
            from elevenlabs import ElevenLabs
            self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        else:
            self.client = None

    async def generate_speech(
        self,
        text: str,
        emotion: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate speech audio from text

        Args:
            text: The text to speak
            emotion: Emotional style hint (happy, sad, calm, etc.)

        Returns:
            Audio bytes (MP3) or None if generation fails
        """
        if not self.enabled:
            return None

        try:
            # Add SSML-like hints for emotion (ElevenLabs interprets these)
            styled_text = self._apply_emotional_style(text, emotion)

            # Generate audio
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=styled_text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            # Collect audio chunks
            audio_bytes = b""
            for chunk in audio:
                audio_bytes += chunk

            return audio_bytes

        except Exception as e:
            print(f"Voice generation error: {e}")
            return None

    def _apply_emotional_style(self, text: str, emotion: Optional[str]) -> str:
        """
        Add emotional hints to text for better voice rendering

        ElevenLabs picks up on punctuation, ellipses, and phrasing.
        """
        if not emotion:
            return text

        # Add subtle markers that influence voice output
        style_hints = {
            "happy": lambda t: t.replace(".", "!").replace("?", "?!") if "!" not in t else t,
            "sad": lambda t: t.replace(".", "...").replace("!", "."),
            "calm": lambda t: t,  # Keep as-is
            "excited": lambda t: t.replace(".", "!"),
            "gentle": lambda t: t.replace("!", ".").replace("?!", "?"),
            "empathetic": lambda t: t,
            "encouraging": lambda t: t.replace(".", "!") if t.count("!") < 2 else t,
        }

        styler = style_hints.get(emotion, lambda t: t)
        return styler(text)

    async def generate_greeting_audio(
        self,
        greeting: str,
        time_of_day: str = "day"
    ) -> Optional[bytes]:
        """Generate audio for a greeting with appropriate energy"""
        emotion_map = {
            "morning": "calm",
            "afternoon": "happy",
            "evening": "calm",
            "night": "gentle"
        }
        emotion = emotion_map.get(time_of_day, "calm")
        return await self.generate_speech(greeting, emotion)
