"""
Company Filter - TOP Companies Whitelist - Phase 3.

ponytail: Thin module. Re-exports from company_ranker.
Keeps whitelist data separate for easy maintenance.
"""

from app.core.company_ranker import (
    is_top_company,
    filter_top_companies,
    rank_company,
    rank_companies,
    CompanyRank,
    TIER_1_TOP,
    TIER_2_KNOWN,
    TIER_3_MIDSIZE,
    TIER_4_UNKNOWN,
)

# ─────────────────────────────────────────────────────────────────────────────
# Explicit Whitelist of Known TOP Companies (Peru/Latam focus)
# ─────────────────────────────────────────────────────────────────────────────
# Companies that appear in job postings but might be misclassified.
# Add variants here for fuzzy matching support.

TOP_COMPANY_ALIASES: dict[str, str] = {
    # Canonical name → preferred display name
    "mercado libre": "Mercado Libre",
    "mercadopago": "Mercado Pago",
    "mercadOLibre": "Mercado Libre",
    "mercadolibre": "Mercado Libre",
    "globant": "Globant",
    "belvo": "Belvo",
    "linio": "Linio",
    "interbank": "Interbank",
    "bbva": "BBVA",
    "bcp": "Banco de Crédito del Perú",
    "scotiabank": "Scotiabank",
    "nu": "Nubank",
    "nubank": "Nubank",
    "stripe": "Stripe",
    "salesforce": "Salesforce",
    "accenture": "Accenture",
    "oracle": "Oracle",
    "sap": "SAP",
    "deel": "Deel",
    "toptal": "Toptal",
    "bairesdev": "BairesDev",
    "thoughtworks": "Thoughtworks",
    "clip": "Clip",
    "kavak": "Kavak",
    "claro": "Claro",
    "movistar": "Movistar",
    "entel": "Entel",
    "amazon": "Amazon",
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "meta": "Meta",
    "netflix": "Netflix",
    "ibm": "IBM",
    "cognizant": "Cognizant",
    "softtek": "Softtek",
    "banco de chile": "Banco de Chile",
    "banorte": "Banorte",
}


def normalize_company_name(raw_name: str) -> str:
    """
    Normalize a company name using the alias whitelist.

    Args:
        raw_name: Raw company name from job posting

    Returns:
        Canonical company name if matched, original cleaned name otherwise.
    """
    if not raw_name:
        return "Confidencial"

    cleaned = raw_name.lower().strip()

    # Check alias whitelist
    if cleaned in TOP_COMPANY_ALIASES:
        return TOP_COMPANY_ALIASES[cleaned]

    return raw_name


def is_whitelisted_company(raw_name: str) -> bool:
    """Check if a company is in the TOP whitelist."""
    if not raw_name:
        return False
    cleaned = raw_name.lower().strip()
    return cleaned in TOP_COMPANY_ALIASES


__all__ = [
    # Re-exports from company_ranker
    "is_top_company",
    "filter_top_companies",
    "rank_company",
    "rank_companies",
    "CompanyRank",
    "TIER_1_TOP",
    "TIER_2_KNOWN",
    "TIER_3_MIDSIZE",
    "TIER_4_UNKNOWN",
    # Whitelist utilities
    "TOP_COMPANY_ALIASES",
    "normalize_company_name",
    "is_whitelisted_company",
]
