"""
Tests for career_classifier.py - Phase 1.
"""

import pytest
from app.core.career_classifier import (
    classify,
    classify_batch,
    _regex_classify,
    _keyword_based_score,
    _fallback_result,
    get_category_name,
    FALLBACK_CATEGORY,
)
from app.core.career_taxonomy import ALL_CATEGORY_NAMES


class TestRegexClassify:
    """Tests for fast-path regex classification."""

    def test_data_science_titles(self):
        result = _regex_classify("Data Scientist")
        assert result is not None
        assert result.category_id == "ciencia-datos-ia"
        assert result.method == "regex"
        assert result.confidence >= 0.85

    def test_backend_java(self):
        result = _regex_classify("Backend Java Developer")
        assert result is not None
        assert result.category_id == "desarrollo-backend"

    def test_frontend_react(self):
        result = _regex_classify("React Frontend Developer")
        assert result is not None
        assert result.category_id == "desarrollo-frontend"

    def test_fullstack(self):
        result = _regex_classify("Full Stack Developer")
        assert result is not None
        assert result.category_id == "desarrollo-fullstack"

    def test_mobile(self):
        result = _regex_classify("Android Developer")
        assert result is not None
        assert result.category_id == "desarrollo-mobile"

    def test_devops(self):
        result = _regex_classify("DevOps Engineer AWS")
        assert result is not None
        assert result.category_id == "devops-cloud"

    def test_qa(self):
        result = _regex_classify("QA Automation Engineer")
        assert result is not None
        assert result.category_id == "qa-testing"

    def test_security(self):
        result = _regex_classify("Cybersecurity Analyst")
        assert result is not None
        assert result.category_id == "seguridad-informatica"

    def test_product_manager(self):
        result = _regex_classify("Product Manager")
        assert result is not None
        assert result.category_id == "product-manager"

    def test_ux_ui(self):
        result = _regex_classify("UX Designer")
        assert result is not None
        assert result.category_id == "ux-ui-design"

    def test_unknown_title_returns_none(self):
        # Ambiguous title with no strong signal
        result = _regex_classify("Senior Consultant")
        assert result is None


class TestKeywordBasedScore:
    """Tests for keyword-based scoring (tiebreaker)."""

    def test_python_keywords(self):
        result = _keyword_based_score("Python Django Developer")
        assert result is not None
        cat, conf = result
        assert cat.id == "desarrollo-backend"
        assert conf >= 0.5

    def test_react_keywords(self):
        result = _keyword_based_score("React TypeScript Developer")
        assert result is not None
        cat, conf = result
        assert cat.id == "desarrollo-frontend"

    def test_insufficient_keywords(self):
        # Only 1 keyword match = insufficient
        result = _keyword_based_score("Senior Developer")
        assert result is None


class TestClassify:
    """Tests for full classify() pipeline."""

    def test_clear_title_uses_regex(self):
        result = classify("Data Scientist", use_ai=False)
        assert result.category_id == "ciencia-datos-ia"
        assert result.method == "regex"

    def test_fallback_for_unknown(self):
        result = classify("Senior Consultant", use_ai=False)
        assert result.category_id == FALLBACK_CATEGORY
        assert result.method == "fallback"
        assert result.confidence == 0.3

    def test_empty_title_returns_fallback(self):
        result = classify("", use_ai=False)
        assert result.method == "fallback"

    def test_ai_flag_false_skips_ai(self):
        result = classify("Ambiguous Title", use_ai=False)
        # With AI off, will fallback if no regex match
        assert result.method in ("fallback", "regex", "keyword")

    def test_company_helps_disambiguation(self):
        # "ML Engineer" at Google should be clearly data science
        result = classify("ML Engineer", company="Google", use_ai=False)
        assert result.category_id == "ciencia-datos-ia"

    def test_classify_batch(self):
        titles = [
            ("Data Scientist", ""),
            ("React Developer", ""),
            ("DevOps Engineer", ""),
        ]
        results = classify_batch(titles, use_ai=False)
        assert len(results) == 3
        assert results[0].category_id == "ciencia-datos-ia"
        assert results[1].category_id == "desarrollo-frontend"
        assert results[2].category_id == "devops-cloud"


class TestGetCategoryName:
    """Tests for category name lookup."""

    def test_valid_id(self):
        name = get_category_name("ciencia-datos-ia")
        assert name == "Ciencia de Datos e IA"

    def test_invalid_id_returns_fallback(self):
        name = get_category_name("invalid-id")
        assert name == "Desarrollo de Software General"


class TestAllCategories:
    """Verify all 17 categories are reachable."""

    def test_all_categories_have_names(self):
        for name in ALL_CATEGORY_NAMES:
            assert len(name) > 0

    def test_fallback_is_always_available(self):
        result = _fallback_result()
        assert result.category_id == FALLBACK_CATEGORY
        assert result.confidence == 0.3
