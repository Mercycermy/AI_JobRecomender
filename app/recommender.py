"""Deterministic, explainable hybrid job recommendation engine."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from app.config import settings
from app.skill_normalizer import SkillNormalizer, normalize_skill_text

DB_PATH = str(settings.recommender_db_path)
INDEX_PATH = str(settings.jobs_index_path)
MAPPER_PATH = str(settings.jobs_id_map_path)
_LOGGER = logging.getLogger("ai_job_recommender.recommender")

MATCH_WEIGHTS: Dict[str, float] = {
    "skill_fit": 0.40,
    "semantic_similarity": 0.15,
    "experience_match": 0.15,
    "role_match": 0.20,
    "location_match": 0.05,
    "freshness": 0.05,
}

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

ROLE_FAMILIES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "backend-dev": {
        "phrases": (
            "backend",
            "back end",
            "api developer",
            "server side",
            "python developer",
            "java developer",
        ),
        "categories": ("backend-dev", "Information Technology (IT)"),
    },
    "frontend-dev": {
        "phrases": (
            "frontend",
            "front end",
            "react developer",
            "web developer",
            "ui developer",
        ),
        "categories": ("frontend-dev", "Information Technology (IT)"),
    },
    "fullstack-dev": {
        "phrases": (
            "full stack",
            "fullstack",
            "software developer",
            "web application",
        ),
        "categories": ("fullstack-dev", "Information Technology (IT)"),
    },
    "mobile-dev": {
        "phrases": (
            "mobile developer",
            "android",
            "ios developer",
            "flutter",
            "react native",
        ),
        "categories": ("mobile-dev", "Information Technology (IT)"),
    },
    "devops-engineer": {
        "phrases": (
            "devops",
            "site reliability",
            "cloud engineer",
            "platform engineer",
            "infrastructure",
        ),
        "categories": ("devops-engineer", "Information Technology (IT)"),
    },
    "data-analyst": {
        "phrases": (
            "data analyst",
            "data analysis",
            "data analytics",
            "business intelligence",
            "bi analyst",
            "reporting analyst",
            "analytics",
            "power bi",
            "powerbi",
            "tableau",
            "dashboard",
            "excel analyst",
            "sql analyst",
            "statistics",
            "data collection",
            "data enumerator",
        ),
        "categories": (
            "data-analyst",
            "Information Technology (IT)",
            "Business, Management & HR",
        ),
    },
    "data-scientist": {
        "phrases": (
            "data scientist",
            "data science",
            "statistical modeling",
            "predictive analytics",
        ),
        "categories": ("data-scientist", "Information Technology (IT)"),
    },
    "ml-engineer": {
        "phrases": (
            "machine learning",
            "ml engineer",
            "artificial intelligence",
            "ai engineer",
        ),
        "categories": (
            "ml-engineer",
            "nlp-engineer",
            "Information Technology (IT)",
        ),
    },
    "ui-ux-designer": {
        "phrases": (
            "ui ux",
            "user experience",
            "product designer",
            "interface designer",
        ),
        "categories": ("ui-ux-designer", "Information Technology (IT)"),
    },
    "graphic-designer": {
        "phrases": (
            "graphic designer",
            "visual designer",
            "creative designer",
            "multimedia designer",
        ),
        "categories": ("graphic-designer", "Sales, Marketing & PR"),
    },
    "project-manager": {
        "phrases": (
            "project manager",
            "program manager",
            "project coordinator",
            "delivery manager",
        ),
        "categories": ("project-manager", "Business, Management & HR"),
    },
    "sales-representative": {
        "phrases": (
            "sales representative",
            "sales executive",
            "account executive",
            "business development",
        ),
        "categories": ("sales-representative", "Sales, Marketing & PR"),
    },
    "digital-marketer": {
        "phrases": (
            "digital marketing",
            "social media",
            "seo",
            "content marketing",
        ),
        "categories": ("digital-marketer", "Sales, Marketing & PR"),
    },
    "accountant": {
        "phrases": (
            "accountant",
            "accounting",
            "finance officer",
            "bookkeeper",
            "auditor",
        ),
        "categories": (
            "accountant",
            "junior-accountant",
            "Accounting, Banking & Finance",
        ),
    },
    "administration-hr": {
        "phrases": (
            "administrative",
            "human resources",
            "hr officer",
            "office administrator",
            "receptionist",
        ),
        "categories": ("administration-hr", "Business, Management & HR"),
    },
    "architect": {
        "phrases": (
            "architect",
            "architectural",
            "construction design",
            "building design",
        ),
        "categories": ("architect", "Engineering & Architecture"),
    },
    "teacher": {
        "phrases": (
            "teacher",
            "instructor",
            "lecturer",
            "educator",
            "trainer",
        ),
        "categories": ("teacher", "Education & Training"),
    },
    "transport-logistics": {
        "phrases": (
            "logistics",
            "supply chain",
            "transport",
            "warehouse",
            "driver",
        ),
        "categories": (
            "transport-logistics",
            "Logistics, Supply Chain & Transport",
        ),
    },
}

ROLE_ALIASES = {
    "software-engineer": "fullstack-dev",
    "backend-developer": "backend-dev",
    "frontend-developer": "frontend-dev",
    "full-stack-developer": "fullstack-dev",
    "mobile-developer": "mobile-dev",
    "business-analyst": "data-analyst",
    "digital-marketing": "digital-marketer",
    "accounting": "accountant",
    "administration": "administration-hr",
    "logistics": "transport-logistics",
}


def _tokens(value: Any) -> Set[str]:
    normalized = normalize_skill_text(value)
    return {
        token
        for token in re.findall(r"[a-z0-9+#.]+", normalized)
        if len(token) > 1 and token not in _STOP_WORDS
    }


class RecommendationEngine:
    """Retrieve broadly, then rerank every candidate with one scoring formula."""

    _RESOURCE_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def __init__(
        self,
        load_resources: bool = True,
        db_path: str = DB_PATH,
        index_path: str = INDEX_PATH,
        mapper_path: str = MAPPER_PATH,
        today: Optional[date] = None,
    ):
        self.db_path = db_path
        self.index_path = index_path
        self.mapper_path = mapper_path
        self.today = today
        self.model = None
        self.index = None
        self.job_ids: List[str] = []
        self.normalizer = SkillNormalizer()
        self.last_retrieval_mode = "database"
        self.last_candidate_count = 0
        self.last_retrieval_sources: Dict[str, int] = {}
        self.last_rejected_candidate_count = 0
        if load_resources:
            self._load_resources()

    def _load_resources(self) -> None:
        cache_key = (
            str(self.index_path),
            str(self.mapper_path),
            settings.embedding_model,
        )
        cached = self._RESOURCE_CACHE.get(cache_key)
        if cached is not None:
            self.model = cached["model"]
            self.index = cached["index"]
            self.job_ids = list(cached["job_ids"])
            _LOGGER.info("Reused cached recommender vector resources.")
            return

        _LOGGER.info("Initializing Recommendation Engine resources.")
        vector_artifacts_ready = (
            os.path.exists(self.index_path)
            and os.path.exists(self.mapper_path)
        )
        if vector_artifacts_ready:
            try:
                from sentence_transformers import SentenceTransformer

                # Runtime recommendation should work offline. The dedicated vector
                # build script remains responsible for downloading model assets.
                self.model = SentenceTransformer(
                    settings.embedding_model,
                    local_files_only=True,
                )
            except Exception as exc:
                _LOGGER.warning(
                    "Failed to load local SentenceTransformer model: %s",
                    exc,
                )
        else:
            _LOGGER.info("Skipping semantic model load; vector artifacts are missing.")

        try:
            import faiss

            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                _LOGGER.info("Loaded FAISS index from %s.", self.index_path)
            else:
                _LOGGER.warning("FAISS index file not found at %s.", self.index_path)
        except Exception as exc:
            _LOGGER.warning("Failed to load FAISS index: %s", exc)

        if os.path.exists(self.mapper_path):
            with open(self.mapper_path, "r", encoding="utf-8") as handle:
                self.job_ids = [str(job_id) for job_id in json.load(handle)]
                _LOGGER.info("Loaded %s job ID mappings.", len(self.job_ids))
        else:
            _LOGGER.warning("Job ID mapping file not found at %s.", self.mapper_path)

        if self.index is not None and self.index.ntotal != len(self.job_ids):
            _LOGGER.warning(
                "FAISS index and job ID map sizes differ; "
                "semantic retrieval will be disabled."
            )
            self.index = None

        self._RESOURCE_CACHE[cache_key] = {
            "model": self.model,
            "index": self.index,
            "job_ids": list(self.job_ids),
        }

    def info(self) -> Dict[str, Any]:
        return {
            "semantic_search": bool(self.model is not None and self.index is not None),
            "retrieval_mode": self.last_retrieval_mode,
            "candidate_count": self.last_candidate_count,
            "retrieval_sources": dict(self.last_retrieval_sources),
            "rejected_candidate_count": self.last_rejected_candidate_count,
            "weights": {
                key: round(value * 100)
                for key, value in MATCH_WEIGHTS.items()
            },
        }

    def _get_experience_weight(self, user_exp: str, job_exp: str) -> float:
        """Score seniority fit without penalizing qualified candidates."""
        if not user_exp or not job_exp:
            return 0.5

        exp_map = {
            "intern": 0,
            "internship": 0,
            "entry": 0,
            "junior": 1,
            "mid": 2,
            "middle": 2,
            "senior": 3,
            "research": 3,
            "lead": 3,
        }
        user_level = exp_map.get(str(user_exp).lower(), 1)
        job_level = exp_map.get(str(job_exp).lower(), 1)
        difference = job_level - user_level
        if difference <= 0:
            return 1.0
        if difference == 1:
            return 0.5
        if difference == 2:
            return 0.1
        return 0.0

    def _location_score(self, preference: str, job_location: str) -> float:
        preference_clean = normalize_skill_text(preference or "remote")
        job_clean = normalize_skill_text(job_location)
        if not job_clean:
            return 0.5
        if preference_clean in {"", "any", "anywhere", "flexible"}:
            return 1.0
        if preference_clean == "remote":
            return 1.0 if "remote" in job_clean else 0.25
        if preference_clean in job_clean or job_clean in preference_clean:
            return 1.0
        if "remote" in job_clean or "hybrid" in job_clean:
            return 0.75
        return 0.2

    def _freshness_score(
        self,
        date_added: Optional[str],
        today: Optional[date] = None,
    ) -> float:
        if not date_added:
            return 0.5
        parsed: Optional[date] = None
        text = str(date_added).strip()
        for parser in (
            lambda: date.fromisoformat(text[:10]),
            lambda: datetime.strptime(text[:10], "%m/%d/%Y").date(),
            lambda: datetime.strptime(text[:10], "%d/%m/%Y").date(),
        ):
            try:
                parsed = parser()
                break
            except (TypeError, ValueError):
                continue
        if parsed is None:
            return 0.5

        age_days = max(0, ((today or self.today or date.today()) - parsed).days)
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.9
        if age_days <= 60:
            return 0.75
        if age_days <= 90:
            return 0.6
        if age_days <= 180:
            return 0.4
        return 0.2

    def _role_family(self, target_role: str) -> Dict[str, Tuple[str, ...]]:
        normalized = normalize_skill_text(target_role).replace(" ", "-")
        key = ROLE_ALIASES.get(normalized, normalized)
        family = ROLE_FAMILIES.get(key)
        if family:
            return family
        phrase = normalize_skill_text(target_role)
        return {
            "phrases": (phrase,) if phrase else (),
            "categories": (target_role,) if target_role else (),
        }

    def _role_score(self, target_role: str, job: Dict[str, Any]) -> float:
        if not target_role:
            return 0.5

        family = self._role_family(target_role)
        title = normalize_skill_text(job.get("job_title"))
        category = normalize_skill_text(job.get("category"))
        target = normalize_skill_text(target_role)
        categories = {
            normalize_skill_text(value)
            for value in family.get("categories", ())
            if value
        }
        phrases = [
            normalize_skill_text(value)
            for value in family.get("phrases", ())
            if value
        ]

        if target and category == target:
            return 1.0
        if any(phrase and phrase in title for phrase in phrases):
            return 0.95

        target_tokens = _tokens(target)
        if not target_tokens and phrases:
            target_tokens = _tokens(phrases[0])
        title_tokens = _tokens(title)
        category_tokens = _tokens(category)
        title_overlap = (
            len(target_tokens & title_tokens) / len(target_tokens)
            if target_tokens
            else 0.0
        )
        if title_overlap:
            return min(0.9, 0.55 + 0.35 * title_overlap)
        if category in categories:
            # A neighboring canonical role is useful evidence, while a broad
            # board category such as "Information Technology (IT)" is only a
            # weak signal and must not outrank the job title.
            return 0.65 if "-" in category else 0.35
        category_overlap = (
            len(target_tokens & category_tokens) / len(target_tokens)
            if target_tokens
            else 0.0
        )
        return min(0.6, 0.2 + 0.4 * category_overlap) if category_overlap else 0.1

    def _lexical_semantic_score(
        self,
        user_skills: Sequence[str],
        target_role: str,
        job: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        job_text = normalize_skill_text(
            f"{job.get('job_title', '')} {job.get('description', '')} "
            f"{job.get('category', '')}"
        )
        if not job_text:
            return 0.0

        if context is None:
            context = self._semantic_context(user_skills, target_role)
        skill_signals = context["skill_signals"]

        job_tokens = _tokens(job_text)
        if skill_signals:
            skill_hits = [
                len(signal & job_tokens) / len(signal)
                for signal in skill_signals
            ]
            skill_semantic = sum(skill_hits) / len(skill_hits)
        else:
            skill_semantic = 0.0

        role_phrases = context["role_phrases"]
        role_hits = [
            1.0 if phrase in job_text else 0.0
            for phrase in role_phrases
            if phrase
        ]
        role_semantic = max(role_hits, default=0.0)
        if not role_semantic and target_role:
            role_tokens = context["role_tokens"]
            role_semantic = (
                len(role_tokens & job_tokens) / len(role_tokens)
                if role_tokens
                else 0.0
            )

        if skill_signals and target_role:
            return min(1.0, 0.7 * skill_semantic + 0.3 * role_semantic)
        return min(1.0, skill_semantic or role_semantic)

    def _semantic_context(
        self,
        user_skills: Sequence[str],
        target_role: str,
    ) -> Dict[str, Any]:
        skill_signals: List[Set[str]] = []
        for skill_id in user_skills:
            signal = _tokens(self.normalizer.name_for(skill_id))
            signal.update(
                token
                for tag in self.normalizer.tags_for(skill_id)
                for token in _tokens(tag)
            )
            if signal:
                skill_signals.append(signal)
        family = self._role_family(target_role)
        return {
            "skill_signals": skill_signals,
            "role_phrases": tuple(
                normalize_skill_text(phrase)
                for phrase in family.get("phrases", ())
                if phrase
            ),
            "role_tokens": _tokens(target_role),
        }

    def _skill_fit(
        self,
        user_skills: Set[str],
        skill_scores: Dict[str, float],
        required_skills: Set[str],
    ) -> Tuple[float, float, float]:
        if not required_skills:
            return 0.35, 0.35, 0.35
        total_weight = sum(
            self.normalizer.weight_for(skill_id)
            for skill_id in required_skills
        )
        if total_weight <= 0:
            return 0.0, 0.0, 0.0

        matched = user_skills & required_skills
        matched_weight = sum(
            self.normalizer.weight_for(skill_id)
            for skill_id in matched
        )
        overlap = matched_weight / total_weight
        proficiency = sum(
            self.normalizer.weight_for(skill_id)
            * max(0.0, min(1.0, float(skill_scores.get(skill_id, 0.65))))
            for skill_id in matched
        ) / total_weight
        fit = 0.75 * overlap + 0.25 * proficiency
        return min(1.0, fit), min(1.0, overlap), min(1.0, proficiency)

    def _profile_inputs(
        self,
        skill_profile: Dict[str, Any],
    ) -> Tuple[List[str], Set[str], Dict[str, float], str, str, str]:
        detected_skills = (
            skill_profile.get("skill_ids")
            or skill_profile.get("detected_skills")
            or skill_profile.get("skills")
            or list((skill_profile.get("skill_scores") or {}).keys())
        )
        raw_skills = [
            str(skill).strip()
            for skill in detected_skills
            if str(skill or "").strip()
        ]
        normalized_skills = self.normalizer.normalize_list(raw_skills)
        user_skills = set(normalized_skills)

        raw_scores = skill_profile.get("skill_scores") or {}
        skill_scores: Dict[str, float] = {}
        for raw_skill, score in raw_scores.items():
            skill_id = self.normalizer.to_skill_id(str(raw_skill))
            try:
                score_value = float(score)
            except (TypeError, ValueError):
                continue
            if skill_id:
                skill_scores[skill_id] = max(0.0, min(1.0, score_value))

        user_exp = (
            skill_profile.get("experience_level")
            or skill_profile.get("experience")
            or "junior"
        )
        target_role = (
            skill_profile.get("target_role")
            or skill_profile.get("detected_role")
            or skill_profile.get("top_category")
            or skill_profile.get("category")
            or ""
        )
        location_pref = skill_profile.get("location") or "remote"
        return (
            normalized_skills,
            user_skills,
            skill_scores,
            str(user_exp),
            str(target_role),
            str(location_pref),
        )

    def _semantic_candidates(
        self,
        user_skills: Sequence[str],
        target_role: str,
        limit: int = 80,
    ) -> Dict[str, float]:
        if self.model is None or self.index is None or not self.job_ids:
            return {}
        query_skills = ", ".join(
            self.normalizer.name_for(skill_id)
            for skill_id in user_skills
        )
        query_text = f"{target_role}. Skills: {query_skills}".strip(". ")
        if not query_text:
            return {}
        vector = self.model.encode([query_text], normalize_embeddings=True)[0]
        query_vector = np.array([vector]).astype("float32")
        size = min(limit, len(self.job_ids))
        similarities, indices = self.index.search(query_vector, size)
        return {
            self.job_ids[index]: max(0.0, min(1.0, float(similarity)))
            for index, similarity in zip(indices[0], similarities[0])
            if 0 <= index < len(self.job_ids)
        }

    def _add_candidate(
        self,
        candidates: Dict[str, Dict[str, Any]],
        job_id: Any,
        source: str,
        retrieval_score: float = 0.0,
        skill_overlap_count: Optional[int] = None,
        vector_similarity: Optional[float] = None,
    ) -> None:
        job_key = str(job_id or "").strip()
        if not job_key:
            return
        meta = candidates.setdefault(
            job_key,
            {
                "sources": [],
                "retrieval_score": 0.0,
                "skill_overlap_count": 0,
            },
        )
        if source and source not in meta["sources"]:
            meta["sources"].append(source)
        meta["retrieval_score"] = max(
            float(meta.get("retrieval_score", 0.0)),
            max(0.0, min(1.0, float(retrieval_score or 0.0))),
        )
        if skill_overlap_count is not None:
            meta["skill_overlap_count"] = max(
                int(meta.get("skill_overlap_count", 0)),
                int(skill_overlap_count),
            )
        if vector_similarity is not None:
            meta["vector_similarity"] = max(
                float(meta.get("vector_similarity", 0.0)),
                max(0.0, min(1.0, float(vector_similarity))),
            )

    def _merge_candidate_metadata(
        self,
        candidates: Dict[str, Dict[str, Any]],
        incoming: Dict[str, Dict[str, Any]],
    ) -> None:
        for job_id, meta in incoming.items():
            for source in meta.get("sources", []):
                self._add_candidate(
                    candidates,
                    job_id,
                    source,
                    retrieval_score=meta.get("retrieval_score", 0.0),
                    skill_overlap_count=meta.get("skill_overlap_count"),
                    vector_similarity=meta.get("vector_similarity"),
                )

    def _source_counts(
        self,
        candidates: Dict[str, Dict[str, Any]],
    ) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for meta in candidates.values():
            for source in meta.get("sources", []):
                counts[source] = counts.get(source, 0) + 1
        return dict(sorted(counts.items()))

    def _add_telegram_candidates(
        self,
        cursor: sqlite3.Cursor,
        candidates: Dict[str, Dict[str, Any]],
        target_role: str,
        limit: int,
    ) -> None:
        """Include normalized Telegram jobs when the feed is present."""
        family = self._role_family(target_role)
        categories = [
            str(value).strip()
            for value in family.get("categories", ())
            if value
        ]
        phrases = [
            normalize_skill_text(value)
            for value in family.get("phrases", ())
            if value
        ][:8]
        filters: List[str] = []
        params: List[str] = []
        if categories:
            filters.append(
                "category IN ({})".format(",".join("?" for _ in categories))
            )
            params.extend(categories)
        if phrases:
            filters.extend("LOWER(job_title) LIKE ?" for _ in phrases)
            params.extend(f"%{phrase}%" for phrase in phrases)
        role_filter = f"AND ({' OR '.join(filters)})" if filters else ""
        rows = cursor.execute(
            f"""
            SELECT job_id
            FROM jobs
            WHERE LOWER(COALESCE(source, '')) LIKE '%telegram%'
            {role_filter}
            ORDER BY date_added DESC, job_id
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        for row in rows:
            self._add_candidate(
                candidates,
                row["job_id"],
                "telegram_feed",
                retrieval_score=0.75,
            )

    def _database_candidate_metadata(
        self,
        user_skills: Sequence[str],
        target_role: str,
        limit: int = 120,
    ) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return {}

        candidates: Dict[str, Dict[str, Any]] = {}

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if user_skills:
                placeholders = ",".join("?" for _ in user_skills)
                rows = cursor.execute(
                    f"""
                    SELECT job_id, COUNT(*) AS overlap
                    FROM job_skills
                    WHERE skill_id IN ({placeholders})
                    GROUP BY job_id
                    ORDER BY overlap DESC, job_id
                    LIMIT ?
                    """,
                    [*user_skills, limit],
                ).fetchall()
                for row in rows:
                    overlap = int(row["overlap"])
                    self._add_candidate(
                        candidates,
                        row["job_id"],
                        "exact_skill_overlap",
                        retrieval_score=overlap / max(1, len(user_skills)),
                        skill_overlap_count=overlap,
                    )

            family = self._role_family(target_role)
            categories = [
                str(value).strip()
                for value in family.get("categories", ())
                if value
            ]
            phrases = [
                normalize_skill_text(value)
                for value in family.get("phrases", ())
                if value
            ][:8]
            if categories:
                rows = cursor.execute(
                    """
                    SELECT job_id
                    FROM jobs
                    WHERE category IN ({})
                    ORDER BY date_added DESC, job_id
                    LIMIT ?
                    """.format(",".join("?" for _ in categories)),
                    [*categories, limit],
                ).fetchall()
                for row in rows:
                    self._add_candidate(
                        candidates,
                        row["job_id"],
                        "role_category",
                        retrieval_score=0.65,
                    )

            if phrases:
                clauses = ["LOWER(job_title) LIKE ?" for _ in phrases]
                params = [f"%{phrase}%" for phrase in phrases]
                rows = cursor.execute(
                    f"""
                    SELECT job_id
                    FROM jobs
                    WHERE {" OR ".join(clauses)}
                    ORDER BY date_added DESC, job_id
                    LIMIT ?
                    """,
                    [*params, limit],
                ).fetchall()
                for row in rows:
                    self._add_candidate(
                        candidates,
                        row["job_id"],
                        "role_title",
                        retrieval_score=0.7,
                    )

            self._add_telegram_candidates(
                cursor,
                candidates,
                target_role,
                limit=max(20, min(limit, 80)),
            )

            if len(candidates) < min(100, limit):
                rows = cursor.execute(
                    """
                    SELECT job_id
                    FROM jobs
                    ORDER BY date_added DESC, job_id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                for row in rows:
                    self._add_candidate(
                        candidates,
                        row["job_id"],
                        "freshness_pool",
                        retrieval_score=0.25,
                    )
        finally:
            conn.close()
        return dict(list(candidates.items())[:limit])

    def _database_candidate_ids(
        self,
        user_skills: Sequence[str],
        target_role: str,
        limit: int = 120,
    ) -> List[str]:
        return list(
            self._database_candidate_metadata(
                user_skills,
                target_role,
                limit=limit,
            )
        )

    def _retrieve_candidates(
        self,
        user_skills: Sequence[str],
        target_role: str,
        limit: int = 160,
    ) -> Tuple[List[str], Dict[str, Dict[str, Any]], Dict[str, float]]:
        candidates: Dict[str, Dict[str, Any]] = {}
        vector_similarities = self._semantic_candidates(
            user_skills,
            target_role,
        )
        for job_id, similarity in vector_similarities.items():
            self._add_candidate(
                candidates,
                job_id,
                "semantic_embedding",
                retrieval_score=similarity,
                vector_similarity=similarity,
            )

        self._merge_candidate_metadata(
            candidates,
            self._database_candidate_metadata(
                user_skills,
                target_role,
            ),
        )

        candidate_ids = list(candidates)[:limit]
        sources = self._source_counts(candidates)
        has_database_source = any(
            source != "semantic_embedding"
            for source in sources
        )
        modes = []
        if vector_similarities:
            modes.append("semantic")
        if has_database_source:
            modes.append("database")
        self.last_retrieval_mode = "+".join(modes) if modes else "none"
        self.last_candidate_count = len(candidate_ids)
        self.last_retrieval_sources = sources
        return candidate_ids, candidates, vector_similarities

    def _load_candidates(
        self,
        job_ids: Sequence[str],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Set[str]]]:
        if not job_ids or not os.path.exists(self.db_path):
            return {}, {}
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in job_ids)
            cursor.execute(
                f"""
                SELECT job_id, job_title, description, category, source,
                       exp_level, job_type, location, date_added
                FROM jobs
                WHERE job_id IN ({placeholders})
                """,
                list(job_ids),
            )
            jobs = {
                str(row["job_id"]): dict(row)
                for row in cursor.fetchall()
            }
            cursor.execute(
                f"""
                SELECT job_id, skill_id
                FROM job_skills
                WHERE job_id IN ({placeholders}) AND is_required = 1
                """,
                list(job_ids),
            )
            skills: Dict[str, Set[str]] = {}
            for row in cursor.fetchall():
                skills.setdefault(str(row["job_id"]), set()).add(
                    str(row["skill_id"]).lower()
                )
            return jobs, skills
        finally:
            conn.close()

    def _validate_job_for_display(self, job: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        if not str(job.get("job_id") or "").strip():
            errors.append("missing job_id")
        if not str(job.get("job_title") or "").strip():
            errors.append("missing job_title")
        if not str(job.get("description") or "").strip():
            errors.append("missing description")
        return errors

    def _build_explanation(
        self,
        job: Dict[str, Any],
        matched_skills: Sequence[str],
        missing_skills: Sequence[str],
        factor_scores: Dict[str, float],
    ) -> Tuple[str, List[str]]:
        points: List[str] = []
        if matched_skills:
            names = ", ".join(
                self.normalizer.name_for(skill_id)
                for skill_id in matched_skills[:3]
            )
            points.append(f"Matches required skills: {names}.")
        else:
            points.append("No exact required-skill overlap was found yet.")

        if factor_scores["role_match"] >= 0.8:
            points.append("The role closely matches your target.")
        elif factor_scores["role_match"] >= 0.6:
            points.append("The role is in a related career family.")

        if factor_scores["experience_match"] >= 1.0:
            points.append("Your experience level meets the requirement.")
        elif factor_scores["experience_match"] < 0.5:
            points.append("The role currently asks for more experience.")

        if factor_scores["location_match"] >= 1.0:
            points.append("The location matches your preference.")
        elif factor_scores["location_match"] < 0.5:
            points.append("The location is a weaker fit.")

        if missing_skills:
            missing_names = ", ".join(
                self.normalizer.name_for(skill_id)
                for skill_id in missing_skills[:3]
            )
            points.append(f"Main skills to develop: {missing_names}.")

        return " ".join(points), points

    def _score_job(
        self,
        job: Dict[str, Any],
        required_skills: Set[str],
        user_skills: Set[str],
        skill_scores: Dict[str, float],
        user_exp: str,
        target_role: str,
        location_pref: str,
        vector_similarity: Optional[float] = None,
        semantic_context: Optional[Dict[str, Any]] = None,
        candidate_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_user_skills = {
            skill_id for skill_id in user_skills if self.normalizer.is_match_skill(skill_id)
        }
        match_required_skills = {
            skill_id
            for skill_id in required_skills
            if self.normalizer.is_match_skill(skill_id)
        }
        skill_fit, skill_overlap, skill_proficiency = self._skill_fit(
            match_user_skills,
            skill_scores,
            match_required_skills,
        )
        lexical_semantic = self._lexical_semantic_score(
            sorted(match_user_skills),
            target_role,
            job,
            context=semantic_context,
        )
        if vector_similarity is None:
            semantic_score = lexical_semantic
        else:
            semantic_score = min(
                1.0,
                0.8 * vector_similarity + 0.2 * lexical_semantic,
            )

        factor_scores = {
            "skill_fit": skill_fit,
            "semantic_similarity": semantic_score,
            "experience_match": self._get_experience_weight(
                user_exp,
                job.get("exp_level"),
            ),
            "role_match": self._role_score(target_role, job),
            "location_match": self._location_score(
                location_pref,
                job.get("location") or "",
            ),
            "freshness": self._freshness_score(job.get("date_added")),
        }
        contributions = {
            key: factor_scores[key] * weight * 100
            for key, weight in MATCH_WEIGHTS.items()
        }
        final_score = sum(contributions.values())
        matched_skills = sorted(
            match_user_skills & match_required_skills,
            key=lambda skill_id: (
                -self.normalizer.weight_for(skill_id),
                self.normalizer.name_for(skill_id),
            ),
        )
        missing_skills = sorted(
            match_required_skills - match_user_skills,
            key=lambda skill_id: (
                -self.normalizer.weight_for(skill_id),
                self.normalizer.name_for(skill_id),
            ),
        )
        explanation, explanation_points = self._build_explanation(
            job,
            matched_skills,
            missing_skills,
            factor_scores,
        )

        match_percent = round(final_score, 1)
        rerank_factors = {
            "exact_skill_overlap": round(skill_overlap * 100, 1),
            "seniority_fit": round(
                factor_scores["experience_match"] * 100,
                1,
            ),
            "location_fit": round(
                factor_scores["location_match"] * 100,
                1,
            ),
            "semantic_similarity": round(semantic_score * 100, 1),
        }
        candidate_meta = candidate_meta or {}
        return {
            **job,
            "match_score": match_percent,
            "match_percent": match_percent,
            "match_label": (
                "strong"
                if final_score >= 75
                else "good"
                if final_score >= 55
                else "developing"
            ),
            "breakdown": {
                "skill_fit": round(skill_fit * 100, 1),
                "skill_overlap": round(skill_overlap * 100, 1),
                "skill_proficiency": round(skill_proficiency * 100, 1),
                "semantic_similarity": round(semantic_score * 100, 1),
                "experience_match": round(
                    factor_scores["experience_match"] * 100,
                    1,
                ),
                "role_match": round(factor_scores["role_match"] * 100, 1),
                # Compatibility alias used by older clients.
                "category_match": round(factor_scores["role_match"] * 100, 1),
                "location_match": round(
                    factor_scores["location_match"] * 100,
                    1,
                ),
                "freshness": round(factor_scores["freshness"] * 100, 1),
            },
            "weighted_contributions": {
                key: round(value, 1)
                for key, value in contributions.items()
            },
            "score_weights": {
                key: round(value * 100)
                for key, value in MATCH_WEIGHTS.items()
            },
            "retrieval_sources": list(candidate_meta.get("sources", [])),
            "retrieval_score": round(
                float(candidate_meta.get("retrieval_score", 0.0)) * 100,
                1,
            ),
            "candidate_stage": {
                "retrieved": True,
                "skill_overlap_count": int(
                    candidate_meta.get("skill_overlap_count", 0)
                ),
                "vector_similarity": (
                    round(float(candidate_meta["vector_similarity"]) * 100, 1)
                    if candidate_meta.get("vector_similarity") is not None
                    else None
                ),
            },
            "rerank_factors": rerank_factors,
            "job_validated": True,
            "validation_errors": [],
            "matched_skills": matched_skills,
            "matched_skill_count": len(matched_skills),
            "matched_skill_names": [
                self.normalizer.name_for(skill_id)
                for skill_id in matched_skills
            ],
            "missing_skills": missing_skills,
            "missing_skill_count": len(missing_skills),
            "required_skill_count": len(match_required_skills),
            "missing_skill_names": [
                self.normalizer.name_for(skill_id)
                for skill_id in missing_skills
            ],
            "explanation": explanation,
            "explanation_points": explanation_points,
        }

    def rank_jobs(self, skill_profile: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
        """Return top jobs with a complete, explainable hybrid score."""
        (
            normalized_skills,
            user_skills,
            skill_scores,
            user_exp,
            target_role,
            location_pref,
        ) = self._profile_inputs(skill_profile)

        candidate_ids, candidate_metadata, vector_similarities = self._retrieve_candidates(
            normalized_skills,
            target_role,
            limit=160,
        )
        jobs, job_skills = self._load_candidates(candidate_ids)
        semantic_context = self._semantic_context(
            normalized_skills,
            str(target_role),
        )

        ranked = []
        rejected_count = 0
        for job_id in candidate_ids:
            job = jobs.get(job_id)
            if not job:
                rejected_count += 1
                continue
            validation_errors = self._validate_job_for_display(job)
            if validation_errors:
                rejected_count += 1
                continue
            ranked.append(
                self._score_job(
                    job=job,
                    required_skills=job_skills.get(job_id, set()),
                    user_skills=user_skills,
                    skill_scores=skill_scores,
                    user_exp=user_exp,
                    target_role=target_role,
                    location_pref=location_pref,
                    vector_similarity=vector_similarities.get(job_id),
                    semantic_context=semantic_context,
                    candidate_meta=candidate_metadata.get(job_id, {}),
                )
            )
        self.last_rejected_candidate_count = rejected_count
        ranked.sort(
            key=lambda item: (
                -item["match_score"],
                -item["rerank_factors"]["exact_skill_overlap"],
                -item["rerank_factors"]["seniority_fit"],
                -item["rerank_factors"]["location_fit"],
                -item["rerank_factors"]["semantic_similarity"],
                item["job_id"],
            )
        )
        return ranked[: max(1, min(int(top_n), 50))]

    def score_jobs(
        self,
        skill_profile: Dict[str, Any],
        jobs: Sequence[Dict[str, Any]],
        top_n: int = 50,
        source_label: str = "provided_jobs",
    ) -> List[Dict[str, Any]]:
        """Score supplied jobs with the same explainable formula as rank_jobs."""
        (
            normalized_skills,
            user_skills,
            skill_scores,
            user_exp,
            target_role,
            location_pref,
        ) = self._profile_inputs(skill_profile)
        semantic_context = self._semantic_context(normalized_skills, target_role)

        ranked: List[Dict[str, Any]] = []
        for job in jobs:
            job_payload = dict(job)
            if not job_payload.get("date_added") and job_payload.get("posted_at"):
                job_payload["date_added"] = job_payload.get("posted_at")
            if not job_payload.get("source"):
                job_payload["source"] = source_label

            if self._validate_job_for_display(job_payload):
                continue

            raw_required = (
                job_payload.get("required_skills")
                or job_payload.get("required_skill_ids")
                or job_payload.get("required_skill_names")
                or []
            )
            required_skills = set(
                self.normalizer.normalize_list(
                    [
                        str(skill)
                        for skill in raw_required
                        if str(skill or "").strip()
                    ]
                )
            )
            match_user_skills = {
                skill_id for skill_id in user_skills if self.normalizer.is_match_skill(skill_id)
            }
            match_required_skills = {
                skill_id
                for skill_id in required_skills
                if self.normalizer.is_match_skill(skill_id)
            }
            overlap_count = len(match_user_skills & match_required_skills)
            ranked.append(
                self._score_job(
                    job=job_payload,
                    required_skills=required_skills,
                    user_skills=user_skills,
                    skill_scores=skill_scores,
                    user_exp=user_exp,
                    target_role=target_role,
                    location_pref=location_pref,
                    semantic_context=semantic_context,
                    candidate_meta={
                        "sources": [source_label],
                        "retrieval_score": 1.0 if overlap_count else 0.35,
                        "skill_overlap_count": overlap_count,
                    },
                )
            )

        ranked.sort(
            key=lambda item: (
                -item["match_score"],
                -item["rerank_factors"]["exact_skill_overlap"],
                -item["rerank_factors"]["seniority_fit"],
                -item["rerank_factors"]["location_fit"],
                -item["rerank_factors"]["semantic_similarity"],
                item["job_id"],
            )
        )
        return ranked[: max(1, min(int(top_n), 100))]

    def _db_fallback_recommendations(
        self,
        detected_skills: List[str],
        user_exp: str,
        top_category: str,
        top_n: int,
        location_pref: str = "remote",
    ) -> List[Dict[str, Any]]:
        """Backward-compatible entry point using the unified matcher."""
        return self.rank_jobs(
            {
                "skill_ids": detected_skills,
                "experience_level": user_exp,
                "target_role": top_category,
                "location": location_pref,
            },
            top_n=top_n,
        )
