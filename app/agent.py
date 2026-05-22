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

    def _load_questions_payload(self, path: Path) -> Dict[str, Any]:
        global _QUESTIONS_CACHE
        if _QUESTIONS_CACHE is not None:
            return _QUESTIONS_CACHE

        part_files = sorted(path.parent.glob(_QUESTION_PARTS_GLOB))
        merged_questions: List[dict] = []
        merged_tiebreakers: Dict[str, str] = {}
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
    specific_role: Optional[str] = None   # chosen specific job title target
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
    MIN_QUESTIONS = 16
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

        # --- subdomain selection and specific role mapping ---
        elif question_id.startswith("Q_G0_SUBDOMAIN_"):
            _SUBDOMAIN_JOB_MAP = {
                "Q_G0_SUBDOMAIN_SOFTWARE": {
                    "A": "Web Developer",
                    "B": "Software Developer",
                    "C": "Full Stack Developer",
                    "D": "Flutter Developer",
                    "E": "Software Developer",
                },
                "Q_G0_SUBDOMAIN_DATA_AI": {
                    "A": "Data Scientist",
                    "B": "ML Engineer",
                    "C": "Data Analyst",
                    "D": "Data Scientist",
                },
                "Q_G0_SUBDOMAIN_CREATIVE": {
                    "A": "Graphic Designer",
                    "B": "UI/UX Designer",
                    "C": "Video Editor",
                    "D": "Content Creator",
                },
                "Q_G0_SUBDOMAIN_SALES_MKT": {
                    "A": "Sales Representative",
                    "B": "Digital Marketer",
                    "C": "Marketing Manager",
                },
                "Q_G0_SUBDOMAIN_ACCOUNTING": {
                    "A": "Accountant",
                    "B": "Senior Accountant",
                    "C": "Junior Accountant",
                    "D": "Cashier",
                },
                "Q_G0_SUBDOMAIN_ADMIN": {
                    "A": "Secretary",
                    "B": "Office Manager",
                    "C": "Project Manager",
                },
                "Q_G0_SUBDOMAIN_ENGINEERING": {
                    "A": "Architect",
                    "B": "Junior Architect",
                    "C": "Site Engineer",
                }
            }
            state.specific_role = _SUBDOMAIN_JOB_MAP.get(question_id, {}).get(option)
            state._pending_route = None

        return state

    def get_next_question(self, state: AgentState) -> Optional[str]:
        """Determine the next question ID based on the current state.

        Returns ``None`` when the assessment should terminate.
        """
        # --- termination checks ---
        if state.question_count >= self.MAX_QUESTIONS:
            return None

        has_exp = self.bank.get("Q_EXP") is not None
        has_project = self.bank.get("Q_PROJECT") is not None

        # If we have reached MIN_QUESTIONS (16) and have asked both final metadata questions, we can terminate
        if state.question_count >= self.MIN_QUESTIONS:
            if (not has_exp or "Q_EXP" in state.asked) and (not has_project or "Q_PROJECT" in state.asked):
                return None

        # --- Phase 1: Sector/Domain Selection (Question 1) ---
        if state.question_count == 0:
            if self.bank.get("Q_G0_DOMAIN_001") is not None:
                return "Q_G0_DOMAIN_001"
            return "Q0_1"

        # --- Phase 2: Subdomain Selection (Question 2) ---
        if state.question_count == 1:
            if state.domain:
                subdomain_qid = f"Q_G0_SUBDOMAIN_{state.domain}"
                if subdomain_qid in self.bank.all_ids and subdomain_qid not in state.asked:
                    return subdomain_qid
            # Fallback if subdomain question is missing or no domain is detected

        # --- Phase 5: Metadata (Questions 15-16 / Q_EXP and Q_PROJECT) ---
        # When we are near MIN_QUESTIONS (at count 14 or 15), we must ask Q_EXP and Q_PROJECT
        if state.question_count >= 14 or state.question_count >= self.MIN_QUESTIONS - 2:
            if has_exp and "Q_EXP" not in state.asked:
                return "Q_EXP"
            if has_project and "Q_PROJECT" not in state.asked:
                return "Q_PROJECT"

        # --- follow pending route if it is valid and exists in the bank ---
        if state._pending_route and state._pending_route not in state.asked:
            if state._pending_route not in ("Q_EXP", "Q_PROJECT") and self.bank.get(state._pending_route) is not None:
                return state._pending_route

        # --- Phase 3: Gate 1 Practical/Debugging Tasks (Questions 3-4) ---
        # Ask up to 2 unasked questions where gate == 1 and domain matches
        asked_gate1_count = sum(1 for qid in state.asked if (self.bank.get(qid) and self.bank.get(qid).get("gate") == 1))
        if asked_gate1_count < 2:
            for qid in self.bank.all_ids:
                if qid in state.asked or qid in ("Q_EXP", "Q_PROJECT"):
                    continue
                q = self.bank.get(qid)
                if q and q.get("gate") == 1:
                    scope = q.get("domain_scope", "").upper()
                    if scope == state.domain:
                        return qid
                    # Special fallback: DATA_AI can draw SQL from SOFTWARE domain
                    if state.domain == "DATA_AI" and scope == "SOFTWARE":
                        role_targets = [r.lower() for r in q.get("role_targets", [])]
                        if "data-analyst" in role_targets or "data-scientist" in role_targets or "ml-engineer" in role_targets:
                            return qid

        # --- Phase 4: Gate 2 Deep Technical (Questions 5-14) ---
        # 4a. First try to find 2 role-specific questions for state.specific_role
        if state.specific_role:
            asked_role_specific = 0
            for qid in state.asked:
                q = self.bank.get(qid)
                if q and q.get("gate") == 2:
                    # check if matches role
                    for ev in q.get("job_evidence", []):
                        titles = ev.get("job_titles", [])
                        if any(t.strip().lower() == state.specific_role.strip().lower() for t in titles):
                            asked_role_specific += 1
                            break
            
            if asked_role_specific < 2:
                for qid in self.bank.all_ids:
                    if qid in state.asked or qid in ("Q_EXP", "Q_PROJECT"):
                        continue
                    q = self.bank.get(qid)
                    if q and q.get("gate") == 2:
                        for ev in q.get("job_evidence", []):
                            titles = ev.get("job_titles", [])
                            if any(t.strip().lower() == state.specific_role.strip().lower() for t in titles):
                                return qid

        # 4b. Then find domain-specific Gate 2 questions
        db_domain_map = {
            "SOFTWARE": "TECH",
            "DATA_AI": "TECH",
            "ENGINEERING": "TECH",
            "ACCOUNTING": "FINANCE",
            "SALES_MKT": "SALES_MARKETING",
            "CREATIVE": "CREATIVE",
            "ADMIN": "ADMIN"
        }
        target_scope = db_domain_map.get(state.domain) if state.domain else None
        
        if target_scope:
            for qid in self.bank.all_ids:
                if qid in state.asked or qid in ("Q_EXP", "Q_PROJECT"):
                    continue
                q = self.bank.get(qid)
                if q and q.get("gate") == 2:
                    if q.get("domain_scope", "").upper() == target_scope:
                        return qid

        # 4c. General Fallback Gate 2 questions
        for qid in self.bank.all_ids:
            if qid in state.asked or qid in ("Q_EXP", "Q_PROJECT"):
                continue
            q = self.bank.get(qid)
            if q and q.get("gate") == 2:
                if q.get("domain_scope", "").upper() == "GENERAL":
                    return qid

        # 4d. Absolute Fallback: any unasked non-metadata question
        for qid in self.bank.all_ids:
            if qid not in state.asked and qid not in ("Q_EXP", "Q_PROJECT"):
                return qid

        # --- Phase 5 fallback ---
        if has_exp and "Q_EXP" not in state.asked:
            return "Q_EXP"
        if has_project and "Q_PROJECT" not in state.asked:
            return "Q_PROJECT"

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
