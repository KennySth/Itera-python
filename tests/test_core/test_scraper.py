"""
Tests for scrapers - Phase 4.

Tests the updated scrapers with skill_extractor integration.
Note: actual scraping (HTTP calls) is not tested - only unit methods.
"""

import pytest
from app.core.computrabajo_scraper import ComputrabajoScraper
from app.core.linkedin_scraper import LinkedInScraper


@pytest.fixture
def scraper():
    return ComputrabajoScraper()


@pytest.fixture
def linkedin_scraper():
    return LinkedInScraper()


def test_linkedin_initialization(linkedin_scraper):
    assert linkedin_scraper.source_name == "LinkedIn"
    assert "https://www.linkedin.com" in linkedin_scraper.base_url


def test_computrabajo_initialization(scraper):
    assert scraper.source_name == "Computrabajo"
    assert "https://pe.computrabajo.com" in scraper.base_url


def test_clean_company_name(scraper):
    assert scraper._clean_company_name("4,8 Empresa SAC") == "Empresa SAC"
    assert (
        scraper._clean_company_name("4,3\r\n \n\n Overall Strategy")
        == "Overall Strategy"
    )
    assert scraper._clean_company_name("Confidencial") == "Confidencial"
    assert scraper._clean_company_name("   Muchos   Espacios   ") == "Muchos Espacios"
    assert scraper._clean_company_name("") == "Confidencial"


def test_extract_salary(scraper):
    assert scraper._extract_salary("Salario no mostrado") is None

    # S/ 3.000 -> 3000 / 3.7 -> ~810.81
    salario_usd = scraper._extract_salary("S/ 3.000,00 (Mensual)")
    assert salario_usd is not None
    assert isinstance(salario_usd, float)
    assert 800 < salario_usd < 820

    # S/ 5,000 -> 5000 / 3.7 = ~1351
    salario_usd2 = scraper._extract_salary("S/ 5,000")
    assert salario_usd2 is not None
    assert 1300 < salario_usd2 < 1400


def test_scrape_accepts_use_ai_param(scraper):
    """Verify scrape method signature accepts use_ai parameter."""
    import inspect

    sig = inspect.signature(scraper.scrape)
    params = list(sig.parameters.keys())
    assert "query" in params
    assert "use_ai" in params


def test_linkedin_scrape_accepts_use_ai_param(linkedin_scraper):
    """Verify LinkedIn scrape also accepts use_ai parameter."""
    import inspect

    sig = inspect.signature(linkedin_scraper.scrape)
    params = list(sig.parameters.keys())
    assert "query" in params
    assert "use_ai" in params


def test_generate_mock_vector(scraper):
    """Verify mock vector generation."""
    vector = scraper._generate_mock_vector()
    assert len(vector) == 5
    assert all(-1 <= v <= 1 for v in vector)
