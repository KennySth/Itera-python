"""
AI Client for Groq (Llama 3.3 70B) - Phase 0 Infrastructure.

ponytail: Minimal implementation - sync httpx for simplicity, no async overhead.
Free tier: 280 tokens/sec, 30 req/min. Cache handles burst.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT = 30.0


class AIClient:
    """Minimal Groq client with retry logic and error handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.timeout = timeout

        if not self.api_key:
            logger.warning(
                "GROQ_API_KEY not set. AI classification will fallback to regex-only. "
                "Set GROQ_API_KEY in .env to enable AI features."
            )

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 256,
    ) -> Optional[str]:
        """
        Send a chat completion request to Groq.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": str}
            temperature: Lower = more deterministic (good for classification)
            max_tokens: Max response tokens

        Returns:
            Assistant's text response, or None on failure.
        """
        if not self.api_key:
            return None

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        GROQ_API_URL,
                        headers=self._get_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
            except httpx.TimeoutException:
                logger.warning(f"Groq timeout on attempt {attempt + 1}/3")
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Groq HTTP error {e.response.status_code} on attempt {attempt + 1}/3"
                )
            except (KeyError, ValueError) as e:
                logger.error(f"Groq response parse error: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected Groq error: {e}")
                return None

        logger.error("Groq failed after 3 attempts")
        return None

    def classify(
        self,
        text: str,
        categories: list[str],
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        Classify text into one of the given categories using AI.

        Args:
            text: Input text to classify
            categories: List of valid category names
            system_prompt: Optional custom system prompt

        Returns:
            Best matching category, or None if AI unavailable/failed.
        """
        if not self.api_key:
            return None

        categories_str = ", ".join(f'"{c}"' for c in categories)

        default_system = (
            "You are a job title classifier. Given a job posting title and company, "
            "classify it into exactly ONE of these categories. "
            "Reply with ONLY the category name, nothing else."
        )

        user_message = (
            f'Job Title: "{text}"\n\n'
            f"Categories: {categories_str}\n\n"
            f"What is the best category for this job title?"
        )

        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": user_message},
        ]

        result = self.complete(messages, temperature=0.1, max_tokens=64)

        if result and result in categories:
            return result
        return None

    def extract_skills(
        self,
        job_description: str,
        skill_list: list[str],
        system_prompt: Optional[str] = None,
    ) -> Optional[list[str]]:
        """
        Extract relevant skills from a job description using AI.

        Args:
            job_description: Full or partial job description text
            skill_list: List of valid skill names to pick from
            system_prompt: Optional custom system prompt

        Returns:
            List of matched skills, or None if AI unavailable/failed.
        """
        if not self.api_key:
            return None

        # Limit skill list to avoid token overflow
        skills_str = ", ".join(skill_list[:100])

        default_system = (
            "You are a skill extractor for job postings. "
            "Given a job description and a list of valid skills, extract ONLY the skills "
            "that are explicitly mentioned or clearly required. "
            "Reply with a JSON list of skill names, nothing else."
        )

        user_message = (
            f"Job Description:\n{job_description[:2000]}\n\n"  # Truncate to save tokens
            f"Valid Skills: {skills_str}\n\n"
            f"Extract the skills present in this job description as a JSON array."
        )

        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": user_message},
        ]

        result = self.complete(messages, temperature=0.1, max_tokens=256)

        if not result:
            return None

        # Parse JSON array from result
        import json

        try:
            # Try direct JSON parse
            skills = json.loads(result)
            if isinstance(skills, list):
                return [s for s in skills if s in skill_list]
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        try:
            import re

            match = re.search(r"\[.*\]", result, re.DOTALL)
            if match:
                skills = json.loads(match.group(0))
                if isinstance(skills, list):
                    return [s for s in skills if s in skill_list]
        except Exception:
            pass

        return None


# Singleton instance
_ai_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get or create the global AI client singleton."""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
