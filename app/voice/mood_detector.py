"""
Mood Detection from Voice

Uses AssemblyAI or Hume AI to detect emotional state from voice input.
Falls back to text analysis if voice detection unavailable.
"""
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import anthropic

from ..config import settings


@dataclass
class MoodAnalysis:
    primary_mood: str
    confidence: float
    secondary_moods: Dict[str, float]
    energy_level: str  # "low", "medium", "high"
    suggested_tone: str  # How companion should respond


class MoodDetector:
    def __init__(self):
        self.anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.assemblyai_enabled = bool(settings.assemblyai_api_key)

    async def detect_from_voice(self, audio_data: bytes) -> Optional[MoodAnalysis]:
        """
        Detect mood from voice audio using AssemblyAI

        Returns None if detection fails or is unavailable.
        """
        if not self.assemblyai_enabled:
            return None

        try:
            import assemblyai as aai

            aai.settings.api_key = settings.assemblyai_api_key

            # Configure with sentiment analysis
            config = aai.TranscriptionConfig(
                sentiment_analysis=True,
                entity_detection=True
            )

            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_data, config=config)

            if transcript.status == aai.TranscriptStatus.error:
                return None

            # Analyze sentiment results
            sentiments = transcript.sentiment_analysis_results or []

            if not sentiments:
                return None

            # Aggregate sentiment scores
            mood_scores = {"positive": 0, "negative": 0, "neutral": 0}
            for s in sentiments:
                mood_scores[s.sentiment.value] += s.confidence

            # Normalize
            total = sum(mood_scores.values()) or 1
            mood_scores = {k: v / total for k, v in mood_scores.items()}

            # Determine primary mood
            primary = max(mood_scores, key=mood_scores.get)

            # Map to more specific moods based on context
            mood_mapping = {
                "positive": "happy",
                "negative": "sad",
                "neutral": "calm"
            }

            return MoodAnalysis(
                primary_mood=mood_mapping.get(primary, primary),
                confidence=mood_scores[primary],
                secondary_moods=mood_scores,
                energy_level=self._estimate_energy(sentiments),
                suggested_tone=self._suggest_tone(primary)
            )

        except Exception as e:
            print(f"Voice mood detection error: {e}")
            return None

    async def detect_from_text(self, text: str) -> MoodAnalysis:
        """
        Detect mood from text using Claude

        This is the fallback when voice detection isn't available.
        """
        prompt = """Analyze the emotional state expressed in this message.

Message: "{text}"

Provide analysis in this exact JSON format:
{{
    "primary_mood": "happy|sad|anxious|angry|tired|excited|calm|frustrated|lonely|hopeful",
    "confidence": 0.0-1.0,
    "secondary_moods": {{"mood": confidence}},
    "energy_level": "low|medium|high",
    "suggested_tone": "gentle|upbeat|calm|empathetic|encouraging"
}}

Only return the JSON, no other text."""

        response = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": prompt.format(text=text)
            }]
        )

        try:
            import json
            result = json.loads(response.content[0].text)

            return MoodAnalysis(
                primary_mood=result.get("primary_mood", "neutral"),
                confidence=result.get("confidence", 0.5),
                secondary_moods=result.get("secondary_moods", {}),
                energy_level=result.get("energy_level", "medium"),
                suggested_tone=result.get("suggested_tone", "empathetic")
            )
        except:
            # Default fallback
            return MoodAnalysis(
                primary_mood="neutral",
                confidence=0.3,
                secondary_moods={},
                energy_level="medium",
                suggested_tone="empathetic"
            )

    def _estimate_energy(self, sentiments) -> str:
        """Estimate energy level from sentiment intensity"""
        if not sentiments:
            return "medium"

        avg_confidence = sum(s.confidence for s in sentiments) / len(sentiments)

        if avg_confidence > 0.8:
            return "high"
        elif avg_confidence < 0.4:
            return "low"
        return "medium"

    def _suggest_tone(self, primary_mood: str) -> str:
        """Suggest companion response tone based on detected mood"""
        tone_map = {
            "positive": "upbeat",
            "negative": "gentle",
            "neutral": "calm",
            "happy": "upbeat",
            "sad": "gentle",
            "anxious": "calm",
            "angry": "empathetic",
            "tired": "gentle",
            "excited": "upbeat",
            "frustrated": "empathetic",
            "lonely": "warm",
            "hopeful": "encouraging"
        }
        return tone_map.get(primary_mood, "empathetic")
