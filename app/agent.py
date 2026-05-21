"""
Adaptive Assessment Agent — Brain of the AI Job Recommender.

Reads user answers, accumulates category confidence scores, routes to the
correct branch of questions, and terminates with a structured SkillProfile.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_QUESTIONS_PATH = _DATA_DIR / "questions.json"
_QUESTION_PARTS_GLOB = "questions_part*.json"

_QUESTIONS_CACHE: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# QuestionBank — loads questions.json and provides lookup
# ---------------------------------------------------------------------------

class QuestionBank:
    """Loads the static question bank from JSON and provides random-access
    lookup by question ID."""

    def __init__(self, path: Optional[Path] = None) -> None:
        path = path or _QUESTIONS_PATH
        raw = self._load_questions_payload(path)
        self._questions = {q["id"]: q for q in raw.get("questions", [])}
        self._tiebreaker_map = raw.get("tiebreaker_map", {})

        # Programmatically inject standard high-level questions Q_EXP and Q_PROJECT
        # to ensure downstream API, manual input workflows, and test coverage remains robust
        if "Q_EXP" not in self._questions:
            self._questions["Q_EXP"] = {
                "id": "Q_EXP",
                "gate": 3,
                "stem": "What is your current experience level?",
                "options": {
                    "A": {
                        "text": "Internship / Entry-level",
                        "experience_level": "intern"
                    },
                    "B": {
                        "text": "Junior (0-2 years)",
                        "experience_level": "junior"
                    },
                    "C": {
                        "text": "Mid-level (3-5 years)",
                        "experience_level": "mid"
                    },
                    "D": {
                        "text": "Senior (6+ years)",
                        "experience_level": "senior"
                    }
                }
            }

        if "Q_PROJECT" not in self._questions:
            self._questions["Q_PROJECT"] = {
                "id": "Q_PROJECT",
                "gate": 3,
                "stem": "What kind of project have you worked on recently?",
                "options": {
                    "A": {
                        "text": "Full-stack web application with user authentication",
                        "signals": {
                            "frontend-dev": 10,
                            "backend-dev": 10
                        }
                    },
                    "B": {
                        "text": "End-to-end Machine Learning model training and deployment",
                        "signals": {
                            "ml-engineer": 15
                        }
                    },
                    "C": {
                        "text": "Data analysis, visualization dashboard, and predictive modeling",
                        "signals": {
                            "data-scientist": 10
                        }
                    },
                    "D": {
                        "text": "Scalable backend APIs, database modeling, and caching layers",
                        "signals": {
                            "backend-dev": 15
                        }
                    },
                    "E": {
                        "text": "Interactive user interfaces, wireframes, and design systems",
                        "signals": {
                            "ui-ux-designer": 15
                        }
                    }
                }
            }

    def _load_questions_payload(self, path: Path) -> Dict[str, Any]:
        global _QUESTIONS_CACHE
        if _QUESTIONS_CACHE is not None:
            return _QUESTIONS_CACHE

        part_files = sorted(path.parent.glob(_QUESTION_PARTS_GLOB))
        if part_files:
            merged_questions: List[dict] = []
            merged_tiebreakers: Dict[str, str] = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                merged_questions.extend(payload.get("questions", []))
                merged_tiebreakers.update(payload.get("tiebreaker_map", {}))
            for part in part_files:
                with open(part, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                merged_questions.extend(payload.get("questions", []))
                merged_tiebreakers.update(payload.get("tiebreaker_map", {}))
            _QUESTIONS_CACHE = {
                "questions": merged_questions,
                "tiebreaker_map": merged_tiebreakers,
            }
            return _QUESTIONS_CACHE

        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                _QUESTIONS_CACHE = json.load(fh)
                return _QUESTIONS_CACHE

        _QUESTIONS_CACHE = {"questions": [], "tiebreaker_map": {}}
        return _QUESTIONS_CACHE

    # -- public API ---------------------------------------------------------

    def get(self, question_id: str) -> Optional[dict]:
        """Return a question dict by ID, or *None* if not found."""
        return self._questions.get(question_id)

    def get_tiebreaker(self, cat1: str, cat2: str) -> Optional[str]:
        """Return the question ID that differentiates *cat1* vs *cat2*,
        or *None* if no tiebreaker exists for this pair."""
        key = f"{cat1}|{cat2}"
        return self._tiebreaker_map.get(key)

    @property
    def all_ids(self) -> List[str]:
        return list(self._questions.keys())

    def __len__(self) -> int:
        return len(self._questions)


# ---------------------------------------------------------------------------
# AgentState — mutable state carried across the assessment
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    """Tracks accumulated scores, detected skills, and routing context
    throughout a single assessment session."""

    scores: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    detected_skills: List[str] = field(default_factory=list)
    question_count: int = 0
    asked: Set[str] = field(default_factory=set)
    experience_level: Optional[str] = None
    domain: Optional[str] = None          # SOFTWARE | DATA_AI | CREATIVE | BUSINESS
    _pending_route: Optional[str] = None  # next question ID from routing table
    route_queue: List[str] = field(default_factory=list)

    # convenience helpers ---------------------------------------------------

    def top_category(self) -> Optional[str]:
        """Return the category_id with the highest accumulated score."""
        if not self.scores:
            return None
        return max(self.scores, key=self.scores.get)  # type: ignore[arg-type]

    def top_two(self) -> List[tuple]:
        """Return ``[(cat, score), (cat, score)]`` for the top-2 categories,
        sorted descending by score."""
        if len(self.scores) < 2:
            return list(self.scores.items())
        sorted_cats = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_cats[:2]

    def max_score(self) -> int:
        return max(self.scores.values()) if self.scores else 0


# ---------------------------------------------------------------------------
# AssessmentAgent — adaptive routing + scoring engine
# ---------------------------------------------------------------------------

# "high-level" domain detection keys produced by Q_G0_DOMAIN_001
_DOMAIN_KEYS = {"SOFTWARE", "DATA_AI", "CREATIVE", "BUSINESS", "SALES_MKT", "ACCOUNTING", "ADMIN", "ENGINEERING"}

# Gate-1 question sequences per sub-domain routing
_SW_ROUTES: Dict[str, List[str]] = {
    "A": ["Q1_SW_A", "Q1_SW_A2"],     # Frontend
    "B": ["Q1_SW_B", "Q1_SW_B2"],     # Backend
    "C": ["Q1_SW_FS"],                 # Full-stack
    "D": ["Q1_SW_B", "Q1_SW_B2"],     # Systems (same Q as backend for depth)
    "E": [],                           # Beginner — skip to experience
}

_DA_ROUTES: Dict[str, List[str]] = {
    "A": ["Q1_DA_A", "Q1_DA_B"],              # Analyst
    "B": ["Q1_DA_A", "Q1_DS_A"],              # Scientist
    "C": ["Q1_DE_A"],                          # Data Engineer
    "D": ["Q1_ML_A", "Q1_ML_B"],              # ML
    "E": ["Q1_NLP_A"],                         # NLP
}


class AssessmentAgent:
    """Adaptive assessment engine.

    Usage::

        agent = AssessmentAgent()
        profile = agent.run_assessment([
            ("Q0_1", "A"),
            ("Q0_2_SW", "A"),
            ...
        ])
    """

    MAX_QUESTIONS = 20
    MIN_QUESTIONS = 10
    CONFIDENCE_THRESHOLD = 85
    TIEBREAK_GAP = 15

    def __init__(self, question_bank: Optional[QuestionBank] = None) -> None:
        self.bank = question_bank or QuestionBank()

    # -- public API ---------------------------------------------------------

    def init_state(self) -> AgentState:
        """Return a fresh, empty assessment state."""
        return AgentState()

    def score_answer(
        self, state: AgentState, question_id: str, option: str
    ) -> AgentState:
        """Apply the signals and skills for *option* of *question_id* to
        *state*.  Also updates routing context.

        Returns the mutated *state* for convenience.
        """
        question = self.bank.get(question_id)
        if question is None:
            raise ValueError(f"Unknown question ID: {question_id}")

        options = question.get("options")
        
        # --- Handle free-text (options: None) ---
        if options is None:
            # Accumulate signals from category_weights in scoring rubric
            scoring = question.get("scoring", {})
            cat_weights = scoring.get("category_weights", {})
            for cat, weight in cat_weights.items():
                state.scores[cat] += weight

            # Accumulate skills from skill_weights
            skill_weights = scoring.get("skill_weights", {})
            for skill in skill_weights.keys():
                if skill not in state.detected_skills:
                    state.detected_skills.append(skill)

            # Accumulate skills from job_evidence
            for evidence in question.get("job_evidence", []):
                ev_skills = evidence.get("evidence_skills", [])
                if isinstance(ev_skills, list):
                    for skill in ev_skills:
                        if skill not in state.detected_skills:
                            state.detected_skills.append(skill)
                elif isinstance(ev_skills, str):
                    for skill in [s.strip() for s in ev_skills.split(",") if s.strip()]:
                        if skill not in state.detected_skills:
                            state.detected_skills.append(skill)

            # Bookkeeping
            state.asked.add(question_id)
            state.question_count += 1

            # Free-text routing: follow "strong" or "partial" or default
            routing = question.get("routing", {})
            state._pending_route = routing.get("strong") or routing.get("partial") or routing.get("PASS")
            if state._pending_route in ("PASS", "FAIL"):
                state._pending_route = None

            return state

        # --- Handle multiple-choice (options present) ---
        opt_data = options.get(option)
        if opt_data is None:
            raise ValueError(
                f"Invalid option '{option}' for question '{question_id}'"
            )

        # --- accumulate signals ---
        for cat, delta in opt_data.get("signals", {}).items():
            state.scores[cat] += delta

        # --- accumulate skills ---
        for skill in opt_data.get("skills", []):
            if skill not in state.detected_skills:
                state.detected_skills.append(skill)

        # --- experience level (Gate-3: Q_EXP) ---
        if "experience_level" in opt_data:
            state.experience_level = opt_data["experience_level"]

        # --- bookkeeping ---
        state.asked.add(question_id)
        state.question_count += 1

        # --- routing context ---
        routing = question.get("routing", {})
        state._pending_route = routing.get(option)

        # --- sub-route queue for Software/Data tracks ---
        if question_id == "Q0_2_SW":
            state.route_queue = _SW_ROUTES.get(option, []).copy()
            state._pending_route = state.route_queue[0] if state.route_queue else None
        elif question_id == "Q0_2_DA":
            state.route_queue = _DA_ROUTES.get(option, []).copy()
            state._pending_route = state.route_queue[0] if state.route_queue else None
        elif state.route_queue and question_id == state.route_queue[0]:
            state.route_queue.pop(0)
            if state.route_queue:
                state._pending_route = state.route_queue[0]

        # --- domain detection (from Gate-0 starting questions) ---
        if question_id == "Q0_1":
            domain_map = {"A": "SOFTWARE", "B": "DATA_AI",
                          "C": "CREATIVE", "D": "BUSINESS", "E": "SOFTWARE"}
            state.domain = domain_map.get(option, "SOFTWARE")
        elif question_id == "Q_G0_DOMAIN_001":
            domain_map = {
                "A": "SOFTWARE",
                "B": "DATA_AI",
                "C": "CREATIVE",
                "D": "SALES_MKT",
                "E": "ACCOUNTING",
                "F": "ADMIN",
                "G": "ENGINEERING"
            }
            state.domain = domain_map.get(option, "SOFTWARE")
            
            # Route directly to domain-specific Gate 1 questions from real parts
            first_q_map = {
                "SOFTWARE": "Q_TECH_FE_REACT_001",
                "DATA_AI": "Q_TECH_DS_MODEL_001",
                "CREATIVE": "Q_CREATIVE_DESIGN_BRIEF_001",
                "SALES_MKT": "Q_BIZ_SALES_PIPE_001",
                "ACCOUNTING": "Q_BIZ_ACC_JOURNAL_001",
                "ADMIN": "Q_BIZ_ADMIN_WORKFLOW_001",
                "ENGINEERING": "Q_ENG_CAD_001"
            }
            state._pending_route = first_q_map.get(state.domain)

        return state

    def get_next_question(self, state: AgentState) -> Optional[str]:
        """Determine the next question ID based on the current state.

        Returns ``None`` when the assessment should terminate.
        """
        # --- termination checks ---
        if (
            state.question_count >= self.MIN_QUESTIONS
            and state.max_score() >= self.CONFIDENCE_THRESHOLD
        ):
            # High confidence reached — but still need Q_EXP / Q_PROJECT
            if "Q_EXP" not in state.asked:
                return "Q_EXP"
            if "Q_PROJECT" not in state.asked:
                return "Q_PROJECT"
            return None

        if state.question_count >= self.MAX_QUESTIONS:
            return None

        # --- nothing asked yet → always start with Q_G0_DOMAIN_001 (or fallback Q0_1) ---
        if state.question_count == 0:
            if self.bank.get("Q_G0_DOMAIN_001") is not None:
                return "Q_G0_DOMAIN_001"
            return "Q0_1"

        # --- follow routing table if available ---
        if state._pending_route and state._pending_route not in state.asked:
            return state._pending_route

        # --- Domain-based Fallback ---
        # If pending route is exhausted or was already asked, find the first unasked
        # question in the bank that matches the user's selected domain
        if state.domain:
            for q_id in self.bank.all_ids:
                if q_id not in state.asked and q_id not in ("Q_EXP", "Q_PROJECT"):
                    q = self.bank.get(q_id)
                    if q:
                        # Match either by domain scope or by role targets in subjective interview questions
                        scope = q.get("domain_scope", "").upper()
                        role_targets = [r.lower() for r in q.get("role_targets", [])]
                        if scope == state.domain or state.domain.lower() in role_targets:
                            return q_id

        # --- Gate-2: tiebreaker ---
        top2 = state.top_two()
        if len(top2) >= 2:
            cat1, score1 = top2[0]
            cat2, score2 = top2[1]
            # skip domain-level keys for tiebreaker logic
            if cat1 not in _DOMAIN_KEYS and cat2 not in _DOMAIN_KEYS:
                if abs(score1 - score2) <= self.TIEBREAK_GAP:
                    tb_id = self.bank.get_tiebreaker(cat1, cat2)
                    if tb_id and tb_id not in state.asked:
                        return tb_id

        # --- Gate-3: always ask experience + project ---
        if "Q_EXP" not in state.asked:
            return "Q_EXP"
        if "Q_PROJECT" not in state.asked:
            return "Q_PROJECT"

        # --- done ---
        return None

    def generate_skill_profile(self, state: AgentState) -> Dict[str, Any]:
        """Build the final SkillProfile dict from accumulated state."""

        # Filter out high-level domain keys from category scores
        category_scores = {
            k: v for k, v in state.scores.items() if k not in _DOMAIN_KEYS
        }

        top_cat = None
        confidence = 0
        if category_scores:
            top_cat = max(category_scores, key=category_scores.get)  # type: ignore[arg-type]
            confidence = category_scores[top_cat]

        return {
            "source": "adaptive_quiz",
            "experience_level": state.experience_level,
            "detected_skills": list(dict.fromkeys(state.detected_skills)),  # dedup, preserve order
            "top_category": top_cat,
            "category_scores": dict(category_scores),
            "question_count": state.question_count,
            "confidence": confidence,
            "profile_vector": None,
        }

    def run_assessment(self, answers: List[tuple]) -> Dict[str, Any]:
        """End-to-end entry point.

        *answers* is a list of ``(question_id, option)`` tuples **in the order
        in which the user answered them**.  The method replays them through the
        scoring engine and then produces a SkillProfile.

        Example::

            profile = agent.run_assessment([
                ("Q0_1", "A"),
                ("Q0_2_SW", "A"),
                ("Q1_SW_A", "C"),
                ("Q1_SW_A2", "A"),
                ("Q_EXP", "C"),
                ("Q_PROJECT", "A"),
            ])
        """
        state = self.init_state()
        for qid, option in answers:
            state = self.score_answer(state, qid, option)
        return self.generate_skill_profile(state)
