"""
Tests for company_ranker.py - Phase 3.
"""

import pytest
from app.core.company_ranker import (
    rank_company,
    rank_companies,
    is_top_company,
    filter_top_companies,
    _clean_company_name,
    TIER_1_TOP,
    TIER_2_KNOWN,
    TIER_3_MIDSIZE,
    TIER_4_UNKNOWN,
    TIER_DEFINITIONS,
    TIER_BY_NUMBER,
)
from app.core.company_filter import normalize_company_name, TOP_COMPANY_ALIASES


class TestCleanCompanyName:
    """Tests for company name cleaning."""

    def test_removes_rating(self):
        assert _clean_company_name("4.3 Google") == "Google"
        assert _clean_company_name("4,5 Tech Corp") == "Tech Corp"

    def test_normalizes_whitespace(self):
        assert _clean_company_name("  Google   LLC  ") == "Google LLC"

    def test_empty_returns_empty(self):
        assert _clean_company_name("") == ""
        assert _clean_company_name("   ") == ""


class TestRankCompany:
    """Tests for company tier ranking."""

    def test_google_is_tier_1(self):
        result = rank_company("Google")
        assert result.tier == 1
        assert result.tier_name == TIER_1_TOP.name
        assert result.confidence >= 0.9

    def test_amazon_is_tier_1(self):
        result = rank_company("Amazon")
        assert result.tier == 1

    def test_mercado_pago_is_tier_1(self):
        # "Mercado Pago" (not "Mercado Libre") is in Tier 1 patterns
        result = rank_company("Mercado Pago")
        assert result.tier == 1
        assert result.confidence >= 0.9

    def test_globant_is_tier_2(self):
        # Globant is Tier 2 (Regional known company)
        result = rank_company("Globant")
        assert result.tier == 2
        assert result.tier_name == TIER_2_KNOWN.name

    def test_bbva_is_tier_2(self):
        result = rank_company("BBVA")
        assert result.tier == 2
        assert result.tier_name == TIER_2_KNOWN.name

    def test_interbank_is_tier_2(self):
        result = rank_company("Interbank")
        assert result.tier == 2

    def test_belvo_is_tier_3(self):
        result = rank_company("Belvo")
        assert result.tier == 3

    def test_toptal_is_tier_3(self):
        result = rank_company("Toptal")
        assert result.tier == 3

    def test_confidential_is_tier_4(self):
        result = rank_company("Confidencial")
        assert result.tier == 4
        assert result.cleaned_name == "Confidencial"

    def test_unknown_small_company_is_tier_4(self):
        result = rank_company("Mi Pyme Tech S.A.C.")
        assert result.tier == 4

    def test_case_insensitive(self):
        result = rank_company("GOOGLE")
        assert result.tier == 1

    def test_removes_rating_prefix(self):
        result = rank_company("4.3 Accenture")
        assert result.tier == 1

    def test_original_name_preserved(self):
        result = rank_company("Google LLC")
        assert result.original_name == "Google LLC"
        assert result.cleaned_name == "Google LLC"

    def test_to_dict(self):
        result = rank_company("Google")
        d = result.to_dict()
        assert d["tier"] == 1
        assert d["original"] == "Google"
        assert d["confidence"] >= 0.9


class TestRankCompanies:
    """Tests for batch ranking."""

    def test_ranks_multiple(self):
        companies = ["Google", "BBVA", "Unknown Corp"]
        results = rank_companies(companies)
        assert len(results) == 3
        assert results[0].tier == 1
        assert results[1].tier == 2
        assert results[2].tier == 4


class TestIsTopCompany:
    """Tests for top-company checks."""

    def test_google_is_top(self):
        assert is_top_company("Google") is True
        assert is_top_company("Google", min_tier=1) is True

    def test_google_not_top_if_min_tier_0(self):
        assert is_top_company("Google", min_tier=0) is False

    def test_bbva_is_top_tier_2(self):
        assert is_top_company("BBVA", min_tier=1) is False
        assert is_top_company("BBVA", min_tier=2) is True

    def test_unknown_is_not_top(self):
        assert is_top_company("Small Tech S.A.") is False

    def test_confidential_is_not_top(self):
        assert is_top_company("Confidencial") is False


class TestFilterTopCompanies:
    """Tests for filtering top companies."""

    def test_filters_correctly(self):
        companies = ["Google", "Small Corp", "BBVA", "Unknown Inc"]
        top = filter_top_companies(companies)
        assert "Google" in top
        assert "BBVA" in top
        assert "Small Corp" not in top
        assert "Unknown Inc" not in top


class TestTierDefinitions:
    """Tests for tier definitions and constants."""

    def test_all_tiers_defined(self):
        assert len(TIER_DEFINITIONS) == 4

    def test_tier_by_number(self):
        assert TIER_BY_NUMBER[1] == TIER_1_TOP
        assert TIER_BY_NUMBER[4] == TIER_4_UNKNOWN

    def test_tier_4_is_catchall(self):
        # Tier 4 always matches
        result = rank_company("Absolutely Unknown Company XYZ")
        assert result.tier == 4


class TestNormalizeCompanyName:
    """Tests for company name normalization via whitelist."""

    def test_mercado_libre_normalization(self):
        assert normalize_company_name("mercado libre") == "Mercado Libre"
        assert normalize_company_name("MERCADOLIBRE") == "Mercado Libre"

    def test_globant_normalization(self):
        assert normalize_company_name("globant") == "Globant"

    def test_bbva_normalization(self):
        assert normalize_company_name("bbva") == "BBVA"

    def test_unknown_returns_original(self):
        assert normalize_company_name("Unknown Tech S.A.") == "Unknown Tech S.A."

    def test_empty_returns_confidencial(self):
        assert normalize_company_name("") == "Confidencial"


class TestCompanyAliases:
    """Tests that TOP_COMPANY_ALIASES is comprehensive."""

    def test_has_mercadolibre_alias(self):
        assert "mercado libre" in TOP_COMPANY_ALIASES

    def test_has_globant_alias(self):
        assert "globant" in TOP_COMPANY_ALIASES

    def test_has_major_tech_companies(self):
        assert "google" in TOP_COMPANY_ALIASES
        assert "amazon" in TOP_COMPANY_ALIASES
        assert "microsoft" in TOP_COMPANY_ALIASES
        assert "apple" in TOP_COMPANY_ALIASES
