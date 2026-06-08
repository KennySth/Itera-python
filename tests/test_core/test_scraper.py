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
    assert len(linkedin_scraper.skill_keywords) > 0

def test_clean_company_name(scraper):
    assert scraper._clean_company_name("4,8 Empresa SAC") == "Empresa SAC"
    assert scraper._clean_company_name("4,3\r\n \n\n Overall Strategy") == "Overall Strategy"
    assert scraper._clean_company_name("Confidencial") == "Confidencial"
    assert scraper._clean_company_name("   Muchos   Espacios   ") == "Muchos Espacios"
    assert scraper._clean_company_name("") == "Confidencial"
    assert scraper._clean_company_name(None) == "Confidencial"

def test_extract_salary(scraper):
    assert scraper._extract_salary("Salario no mostrado") is None
    
    # Probando S/ 3.000 -> 3000 / 3.7 -> ~810.81
    salario_usd = scraper._extract_salary("S/ 3.000,00 (Mensual)")
    assert salario_usd is not None
    assert isinstance(salario_usd, float)
    assert 800 < salario_usd < 820  # Asumiendo tasa 3.7

    salario_usd2 = scraper._extract_salary("S/ 5,000")
    assert salario_usd2 is not None
    assert 1300 < salario_usd2 < 1400 # 5000 / 3.7 = 1351.35
