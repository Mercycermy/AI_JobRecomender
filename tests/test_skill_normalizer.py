import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.skill_normalizer import SkillNormalizer


def test_exact_aliases_and_legacy_ids_resolve():
    normalizer = SkillNormalizer()

    assert normalizer.to_skill_id("Python") == "lang-py"
    assert normalizer.to_skill_id("structured query language") == "lang-sql"
    assert normalizer.to_skill_id("tech-docker") == "ops-docker"
    assert normalizer.to_skill_id("finance-excel") == "fin-excel"


def test_ambiguous_aliases_use_explicit_preference():
    normalizer = SkillNormalizer()

    assert len(normalizer.candidates_for("Excel")) > 1
    assert normalizer.to_skill_id("Excel") == "ba-excel"
    assert normalizer.to_skill_id("SEO") == "sm-seo"
    assert normalizer.to_skill_id("CRM") == "ba-crm"


def test_compound_manual_skill_value_extracts_multiple_skills():
    normalizer = SkillNormalizer()
    skill_ids = normalizer.normalize_list(["HTML/CSS/JavaScript"])

    assert {"fe-html", "fe-css", "lang-js"} <= set(skill_ids)


def test_resume_or_telegram_sentence_extracts_skills():
    normalizer = SkillNormalizer()
    skill_ids = normalizer.extract_skills(
        "Built REST APIs with Python, PostgreSQL, Docker and React.js."
    )

    assert {"be-rest", "lang-py", "db-postgres", "ops-docker", "fe-react"} <= set(
        skill_ids
    )


def test_unresolved_values_are_reported():
    normalizer = SkillNormalizer()
    skill_ids, unresolved = normalizer.normalize_with_unresolved(
        ["Python", "Quantum Basket Weaving"]
    )

    assert skill_ids == ["lang-py"]
    assert unresolved == ["Quantum Basket Weaving"]


def test_question_and_resource_legacy_terms_resolve():
    normalizer = SkillNormalizer()

    assert normalizer.to_skill_id("design-uiux") == "design-uiux"
    assert normalizer.to_skill_id("be-api") == "be-rest"
    assert normalizer.to_skill_id("soft-communication") == "soft-comm"
    assert normalizer.to_skill_id("MLOps") == "ml-ops"
    assert normalizer.to_skill_id("Design Systems") == "des-design-system"
