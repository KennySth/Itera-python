"""
Company Ranker - 4-Tier Classification - Phase 3.

ponytail: Regex + list matching. No AI needed for company ranking -
well-known companies are deterministic. Tier 4 = catch-all unknown.
"""

import re
from typing import NamedTuple, Optional


class TierDefinition(NamedTuple):
    """A company tier with its display name and matching rules."""

    tier: int  # 1 = TOP, 4 = unknown
    name: str  # Display name
    patterns: list[str]  # Company name patterns (case-insensitive)
    aliases: list[str]  # Common aliases/spellings


# Tier 1: TOP multinational/Latam tech companies
TIER_1_TOP = TierDefinition(
    tier=1,
    name="TOP - Big Tech & Multinacionales",
    patterns=[
        # Big Tech
        r"\bgoogle\b",
        r"\bamazon\b",
        r"\bmicrosoft\b",
        r"\bapple\b",
        r"\bmeta\b",
        r"\bfacebook\b",
        r"\bnetflix\b",
        r"\bsalesforce\b",
        r"\boracle\b",
        r"\bibm\b",
        r"\bintel\b",
        r"\bnvidia\b",
        r"\badobe\b",
        r"\bshopify\b",
        # Latam Tech Unicorns
        r"mercado.*libre",  # handles "Mercado Libre", "MercadoLibre", "MERCADO LIBRE"
        r"mercado.*pago",  # handles "Mercado Pago", "MercadoPago"
        r"\bebury\b",
        r"\bnu\b",
        r"\bnubank\b",
        r"\bpicpay\b",
        r"\bclip\b",
        r"\bkavak\b",
        r"\bcarousell\b",
        # Global IT Consulting
        r"\baccenture\b",
        r"\bibm\b",
        r"\bcognizant\b",
        r"\btcs\b",
        r"\binfosys\b",
        r"\bwipro\b",
        r"\bhcl\b",
        # Fintech USA
        r"\bstripe\b",
        r"\bplaid\b",
        r"\bbrex\b",
        r"\bblockfi\b",
        r"\bcoinbase\b",
        r"\bblock\b",
        r"\bsquare\b",
    ],
    aliases=[
        "Mercado Libre",
        "Mercado Pago",
        "Google",
        "Amazon",
        "Microsoft",
        "Apple",
        "Meta",
        "Netflix",
        "Salesforce",
        "Oracle",
        "IBM",
        "Intel",
        "NVIDIA",
        "Adobe",
        "Shopify",
        "Nubank",
        "Nu",
        "PicPay",
        "Clip",
        "Kavak",
        "Carousell",
        "Accenture",
        "Cognizant",
        "TCS",
        "Infosys",
        "Wipro",
        "HCL",
        "Stripe",
        "Plaid",
        "Brex",
        "Coinbase",
    ],
)

# Tier 2: Known regional/enterprise companies
TIER_2_KNOWN = TierDefinition(
    tier=2,
    name="Tier 2 - Empresas Regionales Conocidas",
    patterns=[
        # Peru Top
        r"\binterbank\b",
        r"\bbcp\b",
        r"\bbbva\b",
        r"\bscotiabank\b",
        r"\bripley\b",
        r"\bfalabella\b",
        r"\b Sodimac\b",
        r"\b Backus\b",
        r"\bcoca-cola\b",
        r"\b Backus\b",
        # Latam Enterprise
        r"\bglobant\b",
        r"\bthoughtworks\b",
        r"\bgojek\b",
        r"\bgrab\b",
        r"\btravelport\b",
        r"\bamadeus\b",
        # Enterprise SaaS
        r"\bsap\b",
        r"\bservicenow\b",
        r"\bworkday\b",
        r"\bvmware\b",
        r"\bslack\b",
        r"\bzoom\b",
        r"\batlassian\b",
        r"\bgithub\b",
        r"\bgitlab\b",
        r"\bjetbrains\b",
        # Banking Latam
        r"\bbanco de chile\b",
        r"\bbci\b",
        r"\bbancoppel\b",
        r"\bbanorte\b",
        r"\bsantander\b",
        r"\bhsbc\b",
    ],
    aliases=[
        "Globant",
        "Interbank",
        "BBVA",
        "BCP",
        "Scotiabank",
        "Ripley",
        "Falabella",
        "Sodimac",
        "Backus",
        "Coca-Cola",
        "Thoughtworks",
        "Gojek",
        "Grab",
        "Travelport",
        "Amadeus",
        "SAP",
        "ServiceNow",
        "Workday",
        "VMware",
        "Slack",
        "Zoom",
        "Atlassian",
        "GitHub",
        "GitLab",
        "JetBrains",
        "Banco de Chile",
        "BCI",
        "Bancoppel",
        "Banorte",
        "Santander",
        "HSBC",
    ],
)

# Tier 3: Mid-size / growing companies
TIER_3_MIDSIZE = TierDefinition(
    tier=3,
    name="Tier 3 - Empresas Medianas en Crecimiento",
    patterns=[
        # Growing startups
        r"\bbelvo\b",
        r"\bunkount\b",
        r"\bclara\b",
        r"\bfitbank\b",
        r"\bclaro\b",
        r"\bmovistar\b",
        r"\bentel\b",
        r"\btigo\b",
        # Remote-first companies
        r"\bdeel\b",
        r"\bremote\b",
        r"\bworkiva\b",
        r"\bmasterclass\b",
        # E-commerce Latam
        r"\blinio\b",
        r"\bamazon\s*latin\b",
        r"\bcarulla\b",
        # IT Services Latam
        r"\bsofttek\b",
        r"\bpragma\b",
        r"\bhexaware\b",
        r"\bbairesdev\b",
        r"\btoptal\b",
        r"\bturing\b",
        r"\bgurudev\b",
        # EdTech
        r"\bcoursera\b",
        r"\budemy\b",
        r"\bedx\b",
        r"\bduolingo\b",
    ],
    aliases=[
        "Belvo",
        "Linio",
        "Deel",
        "Toptal",
        "Turing",
        "Bairesdev",
        "Softtek",
        "Pragma",
        "Hexaware",
        "Claro",
        "Movistar",
        "Entel",
        "Tigo",
        "Remote",
        "Workiva",
        "MasterClass",
        "Coursera",
        "Udemy",
        "edX",
        "Duolingo",
    ],
)

# Tier 4: Catch-all for unknown/small companies
TIER_4_UNKNOWN = TierDefinition(
    tier=4,
    name="Tier 4 - Empresas Pequeñas o Desconocidas",
    patterns=[r".*"],  # Catch-all - always matches last
    aliases=[],
)

TIER_DEFINITIONS = [TIER_1_TOP, TIER_2_KNOWN, TIER_3_MIDSIZE, TIER_4_UNKNOWN]

# Fast lookup
TIER_BY_NUMBER: dict[int, TierDefinition] = {t.tier: t for t in TIER_DEFINITIONS}


class CompanyRank:
    """Result of ranking a company into a tier."""

    def __init__(
        self,
        original_name: str,
        cleaned_name: str,
        tier: int,
        tier_name: str,
        matched_pattern: Optional[str] = None,
        confidence: float = 1.0,
    ):
        self.original_name = original_name
        self.cleaned_name = cleaned_name
        self.tier = tier
        self.tier_name = tier_name
        self.matched_pattern = matched_pattern
        self.confidence = confidence

    def __repr__(self):
        return f"CompanyRank({self.cleaned_name} → Tier {self.tier})"

    def to_dict(self) -> dict:
        return {
            "original": self.original_name,
            "cleaned": self.cleaned_name,
            "tier": self.tier,
            "tier_name": self.tier_name,
            "matched_pattern": self.matched_pattern,
            "confidence": self.confidence,
        }


def _clean_company_name(name: str) -> str:
    """Clean a company name before matching."""
    if not name:
        return ""
    # Remove \r\n and normalize whitespace first (some company names have "4,3\r\n\t\t\t\n\n\n\r\n\t\t\tCompany Name")
    name = name.replace("\r", " ").replace("\n", " ")
    # Remove ratings like "4.3" or "4,3" at the start
    name = re.sub(r"^\d[.,]\d\s*", "", name)
    # Normalize whitespace
    name = " ".join(name.split())
    return name.strip()


def rank_company(raw_name: str) -> CompanyRank:
    """
    Rank a company into one of 4 tiers.

    Tier 1: TOP multinational/Latam unicorns
    Tier 2: Known regional/enterprise
    Tier 3: Mid-size/growing
    Tier 4: Unknown/small (catch-all)

    Args:
        raw_name: Raw company name from job posting

    Returns:
        CompanyRank with tier, confidence, and matched pattern.
    """
    cleaned = _clean_company_name(raw_name)

    if not cleaned or cleaned.lower() in (
        "confidencial",
        "confidential",
        "na",
        "n/a",
        "-",
    ):
        return CompanyRank(
            original_name=raw_name,
            cleaned_name="Confidencial",
            tier=4,
            tier_name=TIER_4_UNKNOWN.name,
            confidence=0.5,
        )

    cleaned_lower = cleaned.lower()

    for tier_def in TIER_DEFINITIONS[:-1]:  # Skip catch-all
        for pattern in tier_def.patterns:
            if re.search(pattern, cleaned_lower, re.IGNORECASE):
                return CompanyRank(
                    original_name=raw_name,
                    cleaned_name=cleaned,
                    tier=tier_def.tier,
                    tier_name=tier_def.name,
                    matched_pattern=pattern,
                    confidence=0.9,
                )

    # Tier 4 - unknown
    return CompanyRank(
        original_name=raw_name,
        cleaned_name=cleaned,
        tier=4,
        tier_name=TIER_4_UNKNOWN.name,
        matched_pattern=None,
        confidence=0.3,
    )


def rank_companies(raw_names: list[str]) -> list[CompanyRank]:
    """Rank multiple companies."""
    return [rank_company(name) for name in raw_names]


def is_top_company(raw_name: str, min_tier: int = 1) -> bool:
    """
    Check if a company is considered TOP (tier 1 or 2).

    Args:
        raw_name: Company name to check
        min_tier: Maximum tier to consider "top" (default 1 = only tier 1)

    Returns:
        True if company is in tier <= min_tier.
    """
    rank = rank_company(raw_name)
    return rank.tier <= min_tier


def filter_top_companies(raw_names: list[str]) -> list[str]:
    """
    Return only companies that are TOP (tier 1 or 2).

    Args:
        raw_names: List of company names

    Returns:
        List of company names that are tier 1 or 2.
    """
    return [name for name in raw_names if is_top_company(name, min_tier=2)]


__all__ = [
    "TierDefinition",
    "CompanyRank",
    "rank_company",
    "rank_companies",
    "is_top_company",
    "filter_top_companies",
    "TIER_DEFINITIONS",
    "TIER_BY_NUMBER",
    "TIER_1_TOP",
    "TIER_2_KNOWN",
    "TIER_3_MIDSIZE",
    "TIER_4_UNKNOWN",
]
