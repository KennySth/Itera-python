"""
Tests for skill_extractor.py - Phase 2.
"""

import pytest
from app.core.skill_extractor import (
    _regex_extract,
    extract,
    extract_batch,
    normalize_skill_name,
    MIN_AI_TEXT_LENGTH,
)
from app.core.skill_taxonomy import ALL_SKILL_NAMES


class TestRegexExtract:
    """Tests for fast-path regex extraction."""

    def test_extracts_python(self):
        skills, conf = _regex_extract("We need a Python developer with FastAPI")
        assert "Python" in skills
        assert "FastAPI" in skills
        assert conf > 0

    def test_extracts_java(self):
        skills, conf = _regex_extract("Java Spring Boot developer needed")
        assert "Java" in skills
        assert "Spring Boot" in skills

    def test_extracts_react(self):
        skills, conf = _regex_extract("React developer with TypeScript")
        assert "React" in skills
        assert "TypeScript" in skills

    def test_extracts_aws(self):
        skills, conf = _regex_extract("AWS Cloud Engineer with Docker")
        assert "AWS" in skills
        assert "Docker" in skills

    def test_extracts_power_bi(self):
        skills, conf = _regex_extract("Power BI analyst needed")
        assert "Power BI" in skills

    def test_extracts_terraform(self):
        skills, conf = _regex_extract("Terraform Infrastructure Engineer")
        assert "Terraform" in skills

    def test_no_skills_returns_empty(self):
        skills, conf = _regex_extract("")
        assert skills == []
        assert conf == 0.0

    def test_deduplicates_skills(self):
        skills, conf = _regex_extract("Python Python Python developer")
        assert skills.count("Python") == 1

    def test_longer_text_higher_confidence(self):
        short = "Python developer"
        long_text = "Python developer with experience in FastAPI, Django, and PostgreSQL plus knowledge of Docker and AWS cloud infrastructure"
        _, conf_short = _regex_extract(short)
        _, conf_long = _regex_extract(long_text)
        assert conf_long > conf_short


class TestExtract:
    """Tests for full extract() pipeline."""

    def test_extract_with_title(self):
        result = extract(title="Python FastAPI Developer", use_ai=False)
        assert "Python" in result.skills
        assert "FastAPI" in result.skills
        assert result.method in ("regex", "mixed", "ai")
        assert result.total_found >= 2

    def test_extract_with_short_description(self):
        result = extract(
            title="Data Engineer",
            short_description="We need Python, Spark and Airflow experience",
            use_ai=False,
        )
        assert "Python" in result.skills
        assert result.total_found >= 1

    def test_no_input_returns_empty(self):
        result = extract(title="", short_description="", use_ai=False)
        assert result.method == "none"
        assert result.skills == []

    def test_ai_disabled_uses_regex_only(self):
        result = extract(
            title="ML Engineer",
            short_description="Python TensorFlow PyTorch",
            use_ai=False,
        )
        assert result.ai_used is False
        assert result.skills != []

    def test_ai_skips_when_regex_strong(self):
        # With 3+ strong skills found, AI should be skipped
        result = extract(
            title="Senior Python Django FastAPI PostgreSQL Developer",
            short_description="Need Python, Django, FastAPI, PostgreSQL, Docker",
            use_ai=True,
        )
        # Regex found many skills with high confidence
        assert result.method in ("regex", "mixed")


class TestExtractBatch:
    """Tests for batch extraction."""

    def test_batch_size_matches_input(self):
        texts = [
            {"title": "Python Developer with Django"},
            {"title": "React Developer with TypeScript"},
            {"title": "Java Spring Boot Backend Engineer"},
        ]
        results = extract_batch(texts, use_ai=False)
        assert len(results) == 3
        assert all(r.total_found >= 1 for r in results)

    def test_batch_with_empty_items(self):
        texts = [
            {"title": "Python Developer"},
            {"title": ""},
        ]
        results = extract_batch(texts, use_ai=False)
        assert len(results) == 2


class TestNormalizeSkillName:
    """Tests for skill name normalization."""

    def test_python_aliases(self):
        assert normalize_skill_name("python") == "Python"
        assert normalize_skill_name("Python") == "Python"
        assert normalize_skill_name("PYTHON") == "Python"

    def test_typescript_aliases(self):
        assert normalize_skill_name("typescript") == "TypeScript"
        assert normalize_skill_name("ts") == "TypeScript"

    def test_unknown_returns_none(self):
        assert normalize_skill_name("foobar123") is None


class TestSkillTaxonomy:
    """Tests that skill taxonomy is comprehensive."""

    def test_all_skills_have_names(self):
        assert len(ALL_SKILL_NAMES) >= 80

    def test_python_is_in_taxonomy(self):
        assert "Python" in ALL_SKILL_NAMES

    def test_react_is_in_taxonomy(self):
        assert "React" in ALL_SKILL_NAMES

    def test_aws_is_in_taxonomy(self):
        assert "AWS" in ALL_SKILL_NAMES

    def test_power_bi_is_in_taxonomy(self):
        assert "Power BI" in ALL_SKILL_NAMES

    def test_min_ai_text_length_is_set(self):
        assert MIN_AI_TEXT_LENGTH == 200
