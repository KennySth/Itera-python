"""
Career Classifier - Hybrid Regex + AI - Phase 1.

ponytail: Fast path = regex, slow path = AI for ambiguous titles.
Always returns a category (never None) - fallback to "general" ensures this.
AI fallback rate target: < 10% of calls.
"""

import re
import logging
from typing import Optional

from app.core.ai_client import get_ai_client
from app.core.ai_cache import get_ai_cache
from app.core.career_taxonomy import (
    CAREER_CATEGORIES,
    CATEGORY_BY_ID,
    ALL_CATEGORY_NAMES,
    CareerCategory,
)

logger = logging.getLogger(__name__)

# Confidence thresholds
HIGH_CONFIDENCE = 0.85  # Regex matched strongly - no AI needed
MEDIUM_CONFIDENCE = 0.60  # Some signals - AI can confirm
LOW_CONFIDENCE = 0.30  # Weak signals - AI as tiebreaker
FALLBACK_CATEGORY = "desarrollo-software-general"


class ClassificationResult:
    """Result of a career classification with confidence metadata."""

    def __init__(
        self,
        category_id: str,
        category_name: str,
        confidence: float,
        method: str,  # "regex", "ai", "fallback"
        matched_pattern: Optional[str] = None,
    ):
        self.category_id = category_id
        self.category_name = category_name
        self.confidence = confidence
        self.method = method
        self.matched_pattern = matched_pattern

    def __repr__(self):
        return (
            f"ClassificationResult("
            f"category={self.category_name}, "
            f"confidence={self.confidence:.2f}, "
            f"method={self.method})"
        )


def _regex_classify(title: str) -> Optional[ClassificationResult]:
    """
    Fast path: regex-only classification.

    Returns a ClassificationResult if a high-confidence regex match is found,
    or None if the title is too ambiguous for regex alone.
    """
    title_lower = title.lower()

    for category in CAREER_CATEGORIES:
        for pattern in category.patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return ClassificationResult(
                    category_id=category.id,
                    category_name=category.name,
                    confidence=HIGH_CONFIDENCE,
                    method="regex",
                    matched_pattern=pattern,
                )

    return None


def _keyword_based_score(title: str) -> Optional[tuple[CareerCategory, float]]:
    """
    Score categories by keyword overlap. Returns best match if score > threshold.

    ponytail: Simple bag-of-words scoring. Good enough for tiebreaking.
    """
    title_lower = title.lower()
    title_words = set(title_lower.split())

    best_category: Optional[CareerCategory] = None
    best_score = 0.0

    for category in CAREER_CATEGORIES:
        score = 0.0
        for kw in category.keywords:
            if kw.lower() in title_words:
                score += 1.0

        if score > best_score:
            best_score = score
            best_category = category

    if best_score >= 2 and best_category:
        confidence = min(0.5 + (best_score * 0.1), MEDIUM_CONFIDENCE)
        return (best_category, confidence)

    return None


def _ai_classify(title: str, company: str = "") -> Optional[ClassificationResult]:
    """
    Slow path: AI classification with caching.

    Uses Groq to classify the job title. Results are cached for 1 hour.
    """
    ai_client = get_ai_client()
    ai_cache = get_ai_cache()

    # Check cache first
    cache_key = f"career:{title}:{company}"
    cached = ai_cache.get(title, extra=cache_key)
    if cached:
        return ClassificationResult(
            category_id=cached["category_id"],
            category_name=cached["category_name"],
            confidence=cached.get("confidence", 0.9),
            method="ai",
        )

    # Try AI classification
    input_text = f"{title} - {company}" if company else title

    ai_result = ai_client.classify(
        text=input_text,
        categories=ALL_CATEGORY_NAMES,
    )

    if not ai_result:
        return None

    # Map name back to category
    category = None
    for cat in CAREER_CATEGORIES:
        if cat.name.lower() == ai_result.lower():
            category = cat
            break

    if not category:
        # Try partial match
        for cat in CAREER_CATEGORIES:
            if (
                cat.name.lower() in ai_result.lower()
                or ai_result.lower() in cat.name.lower()
            ):
                category = cat
                break

    if not category:
        logger.warning(f"AI returned unknown category: {ai_result}")
        return None

    result = ClassificationResult(
        category_id=category.id,
        category_name=category.name,
        confidence=0.85,
        method="ai",
    )

    # Cache the result
    ai_cache.set(
        title,
        {
            "category_id": category.id,
            "category_name": category.name,
            "confidence": 0.85,
        },
        extra=cache_key,
    )

    return result


def classify(
    title: str, company: str = "", use_ai: bool = True
) -> ClassificationResult:
    """
    Classify a job title into a career category using hybrid regex + AI.

    Strategy:
    1. Fast regex pass - if high confidence, return immediately
    2. Keyword scoring - if decent overlap, use as signal
    3. AI classification - if enabled and available, use for ambiguous cases
    4. Fallback to general software category

    Args:
        title: Job title to classify
        company: Company name (optional, helps AI disambiguate)
        use_ai: Whether to use AI fallback. Set False for batch processing.

    Returns:
        ClassificationResult with category, confidence, and method.
    """
    if not title or not title.strip():
        return _fallback_result()

    title = title.strip()

    # Step 1: Fast regex pass
    regex_result = _regex_classify(title)
    if regex_result and regex_result.confidence >= HIGH_CONFIDENCE:
        return regex_result

    # Step 2: Keyword scoring for tiebreaking
    keyword_match = _keyword_based_score(title)

    # Step 3: AI classification for ambiguous cases
    ai_result = None
    if use_ai:
        ai_result = _ai_classify(title, company)

    # Decision logic: pick the best non-fallback result
    candidates = []
    if regex_result:
        candidates.append(regex_result)
    if keyword_match:
        cat, conf = keyword_match
        candidates.append(
            ClassificationResult(
                category_id=cat.id,
                category_name=cat.name,
                confidence=conf,
                method="keyword",
            )
        )
    if ai_result:
        candidates.append(ai_result)

    if candidates:
        # Sort by confidence descending
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        best = candidates[0]

        # If regex matched with medium confidence and AI agrees, boost confidence
        if (
            regex_result
            and ai_result
            and regex_result.category_id == ai_result.category_id
        ):
            best.confidence = min(best.confidence + 0.1, 0.95)

        return best

    # Step 4: Fallback
    return _fallback_result()


def _fallback_result() -> ClassificationResult:
    """Return the fallback category for unrecognized titles."""
    fallback = CATEGORY_BY_ID[FALLBACK_CATEGORY]
    return ClassificationResult(
        category_id=fallback.id,
        category_name=fallback.name,
        confidence=0.3,
        method="fallback",
    )


def classify_batch(
    titles: list[tuple[str, str]],  # List of (title, company)
    use_ai: bool = False,  # AI off by default for batch (too slow)
) -> list[ClassificationResult]:
    """
    Classify multiple job titles efficiently.

    Args:
        titles: List of (title, company) tuples
        use_ai: Whether to use AI for ambiguous cases. Recommended: False for batch.

    Returns:
        List of ClassificationResult in same order as input.
    """
    return [classify(title, company, use_ai=use_ai) for title, company in titles]


def get_category_name(category_id: str) -> str:
    """Get display name for a category ID."""
    cat = CATEGORY_BY_ID.get(category_id)
    return cat.name if cat else "Desarrollo de Software General"


__all__ = [
    "ClassificationResult",
    "classify",
    "classify_batch",
    "get_category_name",
    "FALLBACK_CATEGORY",
]
