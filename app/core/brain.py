"""
Companion Brain - Multi-model integration

Uses local Ollama models for 100% free operation.
Falls back to Anthropic API if configured.
"""
import httpx
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..config import settings


@dataclass
class ModelResult:
    response: str
    model: str
    success: bool


class CompanionBrain:
    """
    Smart model router for the companion app.

    Priority:
    1. Local Ollama models (free)
    2. Anthropic API (if configured, as fallback)
    """

    # Model assignments
    MODELS = {
        "fast": "llama3.2:latest",        # Quick tasks, extraction
        "conversation": "gemma3:12b",      # Main conversation
        "smart": "qwen3:14b",              # Analysis, complex tasks
        "reasoning": "deepseek-r1:32b",    # Deep reasoning
    }

    FALLBACK_ORDER = ["gemma3:12b", "qwen3:14b", "llama3.2:latest"]

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.client = httpx.AsyncClient(timeout=120.0)
        self._anthropic = None

        # Check if Anthropic is available as backup
        if settings.anthropic_api_key:
            try:
                import anthropic
                self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except:
                pass

    async def conversation(
        self,
        messages: List[Dict],
        system_prompt: str = None,
        temperature: float = 0.8
    ) -> str:
        """Main conversation - uses best available model"""

        # Try local models first
        for model in [self.MODELS["conversation"]] + self.FALLBACK_ORDER:
            try:
                result = await self._call_ollama(
                    model=model,
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
                if result.success:
                    return result.response
            except Exception as e:
                print(f"Model {model} failed: {e}")
                continue

        # Fall back to Anthropic if available
        if self._anthropic:
            return await self._call_anthropic(messages, system_prompt)

        return "I'm having trouble thinking right now. Please try again."

    async def quick(self, prompt: str, system: str = None) -> str:
        """Quick response for extraction, classification"""
        messages = [{"role": "user", "content": prompt}]

        for model in [self.MODELS["fast"], "llama3.2:latest"]:
            try:
                result = await self._call_ollama(
                    model=model,
                    messages=messages,
                    system_prompt=system,
                    max_tokens=512
                )
                if result.success:
                    return result.response
            except:
                continue

        # Fallback to Anthropic
        if self._anthropic:
            return await self._call_anthropic(messages, system)

        return ""

    async def extract_memories(self, message: str) -> List[Dict]:
        """Extract memorable info from a message"""
        prompt = f"""Extract facts from this text as JSON array:
"{message}"

Return only a JSON array like:
[{{"type": "fact", "content": "Name is Joe", "keywords": ["name"]}}]

JSON:"""

        # Use conversation model (gemma3) - best at structured output
        messages = [{"role": "user", "content": prompt}]

        for model in [self.MODELS["conversation"], self.MODELS["smart"], self.MODELS["fast"]]:
            try:
                result = await self._call_ollama(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=512
                )
                if result.success and result.response:
                    response = result.response
                    break
            except:
                continue
        else:
            return []

        # Clean up response - remove markdown code blocks
        response = response.replace("```json", "").replace("```", "").strip()

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return []

    async def detect_mood(self, text: str) -> Dict[str, Any]:
        """Detect mood from text"""
        prompt = f"""Analyze mood in this text. Return JSON:
{{"mood": "happy|sad|anxious|angry|tired|calm|excited", "confidence": 0.0-1.0, "energy": "low|medium|high"}}

Text: "{text}"

JSON only:"""

        response = await self.quick(prompt)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass

        return {"mood": "neutral", "confidence": 0.5, "energy": "medium"}

    async def _call_ollama(
        self,
        model: str,
        messages: List[Dict],
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> ModelResult:
        """Call Ollama API"""
        try:
            # Build messages with system prompt
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            response = await self.client.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": full_messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()
            data = response.json()

            return ModelResult(
                response=data.get("message", {}).get("content", ""),
                model=model,
                success=True
            )

        except Exception as e:
            return ModelResult(response="", model=model, success=False)

    async def _call_anthropic(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> str:
        """Fallback to Anthropic API"""
        if not self._anthropic:
            return ""

        try:
            response = self._anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt or "You are a helpful assistant.",
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic fallback failed: {e}")
            return ""

    async def check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            return response.status_code == 200
        except:
            return False

    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except:
            return []

    async def close(self):
        await self.client.aclose()


# Singleton instance
_brain: Optional[CompanionBrain] = None


def get_brain() -> CompanionBrain:
    global _brain
    if _brain is None:
        _brain = CompanionBrain()
    return _brain
