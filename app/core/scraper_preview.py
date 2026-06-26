"""
Scraper Preview - Dry-Run Mode - Phase 3.

ponytail: Runs extraction pipeline WITHOUT saving to MongoDB.
Returns a structured list so you can verify AI-classified data before committing.
Use case: call /scraper/preview, inspect results in API response, then call /scraper/run to save.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.core.career_classifier import classify, ClassificationResult
from app.core.skill_extractor import extract, ExtractionResult
from app.core.company_ranker import rank_company, CompanyRank
from app.core.company_filter import normalize_company_name

logger = logging.getLogger(__name__)


@dataclass
class PreviewOffer:
    """
    A job offer in preview mode - shows what WOULD be saved.

    Includes all extracted/enriched fields plus metadata about how
    each field was derived (regex vs AI).
    """

    # Raw fields (as scraped)
    raw_title: str
    raw_company: str
    raw_salary: Optional[float]
    raw_skills: list[str]  # From short desc only (regex)

    # Enriched fields (AI/advanced extraction)
    normalized_company: str = ""
    company_tier: int = 4
    company_tier_name: str = ""
    company_rank_confidence: float = 0.0

    career_category_id: str = ""
    career_category_name: str = ""
    career_classification_method: str = ""  # "regex" | "ai" | "keyword" | "fallback"
    career_confidence: float = 0.0

    skills_extracted: list[str] = field(default_factory=list)
    skills_extraction_method: str = ""  # "regex" | "ai" | "mixed" | "none"
    skills_ai_used: bool = False

    # Metadata
    source: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "url": self.url,
            "raw_title": self.raw_title,
            "raw_company": self.raw_company,
            "normalized_company": self.normalized_company,
            "company_tier": self.company_tier,
            "company_tier_name": self.company_tier_name,
            "company_rank_confidence": self.company_rank_confidence,
            "career_category_id": self.career_category_id,
            "career_category_name": self.career_category_name,
            "career_classification_method": self.career_classification_method,
            "career_confidence": self.career_confidence,
            "raw_skills": self.raw_skills,
            "skills_extracted": self.skills_extracted,
            "skills_extraction_method": self.skills_extraction_method,
            "skills_ai_used": self.skills_ai_used,
            "raw_salary_usd": self.raw_salary,
        }


@dataclass
class PreviewResult:
    """Result of a preview run - list of offers + summary stats."""

    offers: list[PreviewOffer]
    total_raw: int = 0
    total_enriched: int = 0
    ai_used_count: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_raw": self.total_raw,
            "total_enriched": self.total_enriched,
            "ai_used_count": self.ai_used_count,
            "offers": [o.to_dict() for o in self.offers],
            "errors": self.errors,
        }


def preview_offer(
    title: str,
    company: str,
    source: str,
    url: str,
    short_description: str = "",
    salary: Optional[float] = None,
    use_ai: bool = True,
) -> PreviewOffer:
    """
    Run the full enrichment pipeline on a single offer WITHOUT saving.

    Pipeline:
    1. Company ranking (tier 1-4) + normalization
    2. Career category classification (regex → AI fallback)
    3. Skill extraction (regex → AI fallback)

    Args:
        title: Job title
        company: Company name
        source: Source scraper name (e.g., "LinkedIn", "Computrabajo")
        url: Job posting URL
        short_description: Short description (card-level)
        salary: Salary in USD (if available)
        use_ai: Whether to use AI for ambiguous cases

    Returns:
        PreviewOffer with all raw + enriched fields.
    """
    offer = PreviewOffer(
        raw_title=title,
        raw_company=company,
        raw_salary=salary,
        raw_skills=[],  # Will be filled by extraction
        source=source,
        url=url,
    )

    # Step 1: Company ranking + normalization
    try:
        company_rank: CompanyRank = rank_company(company)
        offer.normalized_company = normalize_company_name(company)
        offer.company_tier = company_rank.tier
        offer.company_tier_name = company_rank.tier_name
        offer.company_rank_confidence = company_rank.confidence
    except Exception as e:
        logger.warning(f"Company ranking error: {e}")
        offer.normalized_company = company
        offer.company_tier = 4
        offer.company_tier_name = "Tier 4 - Empresas Pequeñas o Desconocidas"

    # Step 2: Career classification
    try:
        result: ClassificationResult = classify(title, company, use_ai=use_ai)
        offer.career_category_id = result.category_id
        offer.career_category_name = result.category_name
        offer.career_classification_method = result.method
        offer.career_confidence = result.confidence
    except Exception as e:
        logger.warning(f"Career classification error: {e}")
        offer.career_category_id = "desarrollo-software-general"
        offer.career_category_name = "Desarrollo de Software General"
        offer.career_classification_method = "fallback"
        offer.career_confidence = 0.3

    # Step 3: Skill extraction
    try:
        skill_result: ExtractionResult = extract(
            title=title,
            company=company,
            short_description=short_description,
            use_ai=use_ai,
        )
        offer.skills_extracted = skill_result.skills
        offer.skills_extraction_method = skill_result.method
        offer.skills_ai_used = skill_result.ai_used
        offer.raw_skills = (
            skill_result.skills
        )  # ponytail: unify - skills shown are the enriched ones
    except Exception as e:
        logger.warning(f"Skill extraction error: {e}")
        offer.skills_extraction_method = "none"
        offer.skills_ai_used = False

    return offer


def preview_offers(
    raw_offers: list[dict],
    source: str,
    use_ai: bool = True,
) -> PreviewResult:
    """
    Run enrichment pipeline on multiple raw offers.

    Args:
        raw_offers: List of dicts with keys: title, company, url,
                    short_description (optional), salary (optional)
        source: Scraper source name
        use_ai: Whether to use AI

    Returns:
        PreviewResult with list of PreviewOffer + summary stats.
    """
    result = PreviewResult(offers=[], total_raw=len(raw_offers))
    ai_count = 0

    for raw in raw_offers:
        try:
            preview = preview_offer(
                title=raw.get("title", ""),
                company=raw.get("company", ""),
                source=source,
                url=raw.get("url", ""),
                short_description=raw.get("short_description", ""),
                salary=raw.get("salary"),
                use_ai=use_ai,
            )
            result.offers.append(preview)
            if preview.skills_ai_used or preview.career_classification_method == "ai":
                ai_count += 1
        except Exception as e:
            logger.error(f"Preview error for offer: {e}")
            result.errors.append(f"Error processing: {raw.get('title', 'unknown')}")

    result.total_enriched = len(result.offers)
    result.ai_used_count = ai_count

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_PREVIEW_INPUTS: list[dict] = [
    {
        "title": "Senior Python Developer - Machine Learning",
        "company": "Mercado Libre",
        "url": "https://example.com/job/1",
        "short_description": "Buscamos desarrollador Python con experiencia en ML y datos.",
        "salary": 15000.0,
    },
    {
        "title": "Frontend React Developer",
        "company": "Globant",
        "url": "https://example.com/job/2",
        "short_description": "Desarrollador React con TypeScript y Angular.",
        "salary": 12000.0,
    },
    {
        "title": "DevOps Engineer - AWS Kubernetes",
        "company": "Confidencial",
        "url": "https://example.com/job/3",
        "short_description": "Ingeniero DevOps con experiencia en contenedores y cloud.",
        "salary": None,
    },
    {
        "title": "Data Engineer - Spark Airflow",
        "company": "Banorte",
        "url": "https://example.com/job/4",
        "short_description": "Data Engineer con Python, Spark y Airflow.",
        "salary": 18000.0,
    },
]


__all__ = [
    "PreviewOffer",
    "PreviewResult",
    "preview_offer",
    "preview_offers",
    "SAMPLE_PREVIEW_INPUTS",
]
