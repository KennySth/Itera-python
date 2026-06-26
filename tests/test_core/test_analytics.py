"""
Tests for analytics.py - Phase 5.

Tests the new _get_category_for_offer function and SALARY_BASELINES.
Note: update_career_metrics is async and requires DB - tested separately.
"""

import pytest
from app.core.analytics import (
    _get_category_for_offer,
    _get_fallback_salary,
    SALARY_BASELINES_MONTHLY,
)


class TestGetCategoryForOffer:
    """Tests for smart category resolution from offer dicts."""

    def test_enriched_offer_uses_categoria_carrera_nombre(self):
        offer = {
            "puesto": "Data Scientist",
            "empresa": "Google",
            "categoria_carrera_nombre": "Ciencia de Datos e IA",
        }
        result = _get_category_for_offer(offer)
        assert result == "Ciencia de Datos e IA"

    def test_legacy_offer_uses_classifier(self):
        offer = {
            "puesto": "Python Backend Developer",
            "empresa": "Tech Corp",
        }
        result = _get_category_for_offer(offer)
        assert result == "Desarrollo Backend"

    def test_frontend_legacy_offer(self):
        offer = {
            "puesto": "React Frontend Developer",
            "empresa": "Startup XYZ",
        }
        result = _get_category_for_offer(offer)
        assert result == "Desarrollo Frontend"

    def test_empty_offer_returns_fallback(self):
        offer = {}
        result = _get_category_for_offer(offer)
        assert result == "Desarrollo de Software General"


class TestGetFallbackSalary:
    """Tests for fallback salary by category."""

    def test_data_science_highest(self):
        salary = _get_fallback_salary("Ciencia de Datos e IA")
        assert salary == 4000.0

    def test_devops_high(self):
        salary = _get_fallback_salary("DevOps y Cloud")
        assert salary == 3500.0

    def test_backend(self):
        salary = _get_fallback_salary("Desarrollo Backend")
        assert salary == 3200.0

    def test_frontend(self):
        salary = _get_fallback_salary("Desarrollo Frontend")
        assert salary == 2500.0

    def test_qa_lower(self):
        salary = _get_fallback_salary("QA y Testing")
        assert salary == 2000.0

    def test_unknown_category_defaults(self):
        salary = _get_fallback_salary("Unknown Category")
        assert salary == 2000.0

    def test_general_fallback(self):
        salary = _get_fallback_salary("Desarrollo de Software General")
        assert salary == 2200.0


class TestSalaryBaselines:
    """Tests that salary baselines cover all 17 categories."""

    def test_all_baselines_are_positive(self):
        for cat, salary in SALARY_BASELINES_MONTHLY.items():
            assert salary > 0, f"Category {cat} has invalid salary {salary}"

    def test_all_baselines_are_reasonable(self):
        for cat, salary in SALARY_BASELINES_MONTHLY.items():
            assert 1000 <= salary <= 10000, (
                f"Category {cat} salary {salary} out of range"
            )

    def test_data_science_is_highest(self):
        ds = SALARY_BASELINES_MONTHLY["Ciencia de Datos e IA"]
        general = SALARY_BASELINES_MONTHLY["Desarrollo de Software General"]
        assert ds > general

    def test_covers_all_17_categories(self):
        # SALARY_BASELINES should have entries for all 17 categories
        # This verifies nothing was accidentally removed
        from app.core.career_taxonomy import ALL_CATEGORY_NAMES

        for cat_name in ALL_CATEGORY_NAMES:
            assert cat_name in SALARY_BASELINES_MONTHLY, (
                f"Missing baseline for {cat_name}"
            )
