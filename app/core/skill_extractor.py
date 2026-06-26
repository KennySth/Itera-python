"""
Skill Extractor - Hybrid Regex + AI - Phase 2.

ponytail: Fast path = regex on title/short desc.
Slow path = AI on full description (only if text is long enough).
Never extracts from empty text.
"""

import re
import logging
from typing import Optional

from app.core.ai_client import get_ai_client
from app.core.ai_cache import get_ai_cache
from app.core.skill_taxonomy import (
    ALIAS_TO_SKILL,
    ALL_SKILL_NAMES,
    PREMIUM_SKILLS,
    SKILL_BY_NAME,
)

logger = logging.getLogger(__name__)

# Min text length to bother with AI extraction
MIN_AI_TEXT_LENGTH = 200

# Min confidence score for regex matches
MIN_REGEX_CONFIDENCE = 0.6


class ExtractionResult:
    """Result of skill extraction with confidence metadata."""

    def __init__(
        self,
        skills: list[str],
        method: str,  # "regex", "ai", "mixed", "none"
        ai_used: bool = False,
        total_found: int = 0,
    ):
        self.skills = skills
        self.method = method
        self.ai_used = ai_used
        self.total_found = total_found

    def __repr__(self):
        return f"ExtractionResult(skills={len(self.skills)}, method={self.method}, ai={self.ai_used})"


def _regex_extract(text: str) -> tuple[list[str], float]:
    """
    Fast path: regex-based skill extraction from text.

    Returns:
        Tuple of (matched_skills, confidence_score)
    """
    if not text:
        return [], 0.0

    text_lower = text.lower()
    matched: list[str] = []
    match_count = 0

    # Check each alias against the text
    for alias, canonical in ALIAS_TO_SKILL.items():
        # Use word boundary matching to avoid partial matches
        # e.g., "Java" shouldn't match in "JavaScript"
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower, re.IGNORECASE):
            if canonical not in matched:
                matched.append(canonical)
                match_count += 1

    # Confidence based on how many skills matched relative to text length
    if not matched:
        return [], 0.0

    # Longer text = more confident (less likely to be accidental mention)
    text_length_factor = min(len(text) / 500, 1.0)  # Cap at 500 chars
    confidence = min(0.5 + (len(matched) * 0.1) + (text_length_factor * 0.2), 1.0)

    return matched, confidence


def _ai_extract(text: str, existing_skills: list[str]) -> Optional[list[str]]:
    """
    Slow path: AI-assisted skill extraction from full job description.

    Uses Groq to find skills that the regex pass might have missed.
    Results are cached for 1 hour.
    """
    if not text or len(text) < MIN_AI_TEXT_LENGTH:
        return None

    ai_client = get_ai_client()
    ai_cache = get_ai_cache()

    # Check cache
    cache_key = f"skills:ai:{hash(text[:500])}"
    cached = ai_cache.get(text[:500], extra="ai_extract")
    if cached:
        return cached.get("skills")

    # Exclude already-found skills to avoid duplicates
    available_skills = [s for s in ALL_SKILL_NAMES if s not in existing_skills]

    if not available_skills:
        return None

    # Limit to 80 skills to avoid token overflow
    available_skills = available_skills[:80]

    ai_result = ai_client.extract_skills(
        job_description=text,
        skill_list=available_skills,
    )

    if not ai_result:
        return None

    # Validate: ensure returned skills are in our taxonomy
    valid_skills = [s for s in ai_result if s in ALL_SKILL_NAMES]

    if valid_skills:
        ai_cache.set(
            text[:500],
            {"skills": valid_skills},
            extra="ai_extract",
            ttl_seconds=3600,
        )

    return valid_skills


def extract(
    title: str = "",
    company: str = "",
    short_description: str = "",
    full_description: str = "",
    use_ai: bool = True,
) -> ExtractionResult:
    """
    Extract skills from job posting text using hybrid regex + AI.

    Strategy:
    1. Fast regex on title + short_description (almost always available)
    2. AI on full_description (only if >200 chars and no strong regex match)
    3. Combine and deduplicate

    Args:
        title: Job title
        company: Company name (context only)
        short_description: Short job description (card-level, usually available)
        full_description: Full job description (detail page, not always available)
        use_ai: Whether to use AI for ambiguous/long descriptions

    Returns:
        ExtractionResult with matched skills and metadata.
    """
    # Step 1: Regex extraction from title + short desc (high availability)
    primary_text = " ".join(filter(None, [title, company, short_description]))
    regex_skills, regex_confidence = _regex_extract(primary_text)

    # Step 2: If regex was strong, skip AI
    if regex_confidence >= 0.8 and len(regex_skills) >= 3:
        return ExtractionResult(
            skills=regex_skills,
            method="regex",
            ai_used=False,
            total_found=len(regex_skills),
        )

    # Step 3: Try AI on full description (if available and long enough)
    ai_skills: list[str] = []
    if use_ai and full_description and len(full_description) >= MIN_AI_TEXT_LENGTH:
        ai_skills = _ai_extract(full_description, existing_skills=regex_skills) or []

    # Step 4: Combine results
    all_skills = list(dict.fromkeys(regex_skills + ai_skills))  # Preserve order, dedupe

    # Determine method
    if not all_skills:
        method = "none"
    elif regex_skills and ai_skills:
        method = "mixed"
    elif ai_skills:
        method = "ai"
    else:
        method = "regex"

    return ExtractionResult(
        skills=all_skills,
        method=method,
        ai_used=bool(ai_skills),
        total_found=len(all_skills),
    )


def extract_from_offer(
    offer: dict,  # JobOffer as dict
    use_ai: bool = True,
) -> ExtractionResult:
    """
    Extract skills from a JobOffer dict (from MongoDB).

    Args:
        offer: JobOffer document with fields like 'puesto', 'empresa',
               'habilidades_requeridas' (existing), etc.
        use_ai: Whether to use AI enhancement

    Returns:
        ExtractionResult.
    """
    title = offer.get("puesto", "")
    empresa = offer.get("empresa", "")

    # If already has skills and no AI requested, return early
    existing_skills = offer.get("habilidades_requeridas", [])
    if not use_ai and existing_skills:
        return ExtractionResult(
            skills=existing_skills[:50],  # Cap at 50
            method="existing",
            ai_used=False,
            total_found=len(existing_skills),
        )

    return extract(
        title=title,
        company=empresa,
        short_description="",  # Not stored in offer schema
        full_description="",
        use_ai=use_ai,
    )


def extract_batch(
    texts: list[dict],  # List of {"title": str, "description": str}
    use_ai: bool = False,  # AI off by default for batch
) -> list[ExtractionResult]:
    """
    Extract skills from multiple texts efficiently.

    Args:
        texts: List of dicts with optional "title", "description" keys
        use_ai: Whether to use AI. Recommended False for batch.

    Returns:
        List of ExtractionResult in same order as input.
    """
    results = []
    for item in texts:
        result = extract(
            title=item.get("title", ""),
            short_description=item.get("description", ""),
            use_ai=use_ai,
        )
        results.append(result)
    return results


def normalize_skill_name(raw_name: str) -> Optional[str]:
    """
    Normalize a raw skill name to canonical form.

    Args:
        raw_name: Raw skill string from job posting

    Returns:
        Canonical skill name, or None if not in taxonomy.
    """
    normalized = raw_name.strip().lower()
    return ALIAS_TO_SKILL.get(normalized)


__all__ = [
    "ExtractionResult",
    "extract",
    "extract_from_offer",
    "extract_batch",
    "normalize_skill_name",
    "MIN_AI_TEXT_LENGTH",
]
