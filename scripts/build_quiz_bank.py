"""
Generate a minimal adaptive quiz bank (data/questions.json) for local dev and tests.

The full production question bank may be split into data/questions_part*.json;
this script provides the subset required by tests/test_agent.py and GET /quiz.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = BASE_DIR / "data" / "questions.json"


def q(qid: str, stem: str, option_defs: dict) -> dict:
    opts = {}
    routing = {}
    for letter, (signals, skills, exp, route) in option_defs.items():
        entry = {}
        if signals:
            entry["signals"] = signals
        if skills:
            entry["skills"] = skills
        if exp:
            entry["experience_level"] = exp
        opts[letter] = entry
        if route:
            routing[letter] = route
    question = {"id": qid, "stem": stem, "options": opts}
    if routing:
        question["routing"] = routing
    return question


def main() -> None:
    questions = [
        q("Q0_1", "Which domain fits you best?", {
            "A": ({"SOFTWARE": 40}, [], None, "Q0_2_SW"),
            "B": ({"DATA_AI": 40}, [], None, "Q0_2_DA"),
            "C": ({"CREATIVE": 40}, [], None, "Q1_CREATIVE_A"),
            "D": ({"BUSINESS": 40}, [], None, None),
            "E": ({"SOFTWARE": 20}, [], None, "Q0_2_SW"),
        }),
        q("Q0_2_SW", "Software focus?", {
            "A": ({"frontend-dev": 35}, [], None, "Q1_SW_A"),
            "B": ({"backend-dev": 35}, [], None, "Q1_SW_B"),
            "C": ({"fullstack-dev": 35}, [], None, "Q1_SW_FS"),
            "D": ({"backend-dev": 25}, [], None, "Q1_SW_B"),
            "E": ({"software-engineer": 15}, [], None, None),
        }),
        q("Q0_2_DA", "Data/AI focus?", {
            "A": ({"data-analyst": 30}, [], None, "Q1_DA_A"),
            "B": ({"data-analyst": 20, "data-scientist": 15}, [], None, "Q1_DA_A"),
            "C": ({"data-engineer": 30}, [], None, "Q1_DE_A"),
            "D": ({"ml-engineer": 35}, [], None, "Q1_ML_A"),
            "E": ({"nlp-engineer": 30}, [], None, "Q1_NLP_A"),
        }),
        q("Q1_SW_A", "Frontend depth?", {
            "A": ({"frontend-dev": 10}, ["fe-html"], None, None),
            "B": ({"frontend-dev": 15}, ["fe-js"], None, None),
            "C": ({"frontend-dev": 25}, ["fe-react"], None, None),
            "D": ({"frontend-dev": 20}, ["fe-vue"], None, None),
        }),
        q("Q1_SW_A2", "CSS approach?", {
            "A": ({"frontend-dev": 20}, ["fe-css"], None, None),
            "B": ({"frontend-dev": 10}, ["fe-tailwind"], None, None),
            "C": ({"frontend-dev": 10}, [], None, None),
            "D": ({"frontend-dev": 5}, [], None, None),
        }),
        q("Q1_SW_B", "Backend pattern?", {
            "A": ({"backend-dev": 15}, ["be-sql"], None, None),
            "B": ({"backend-dev": 15}, ["be-rest"], None, None),
            "C": ({"backend-dev": 25}, ["be-api-design"], None, None),
            "D": ({"backend-dev": 10}, ["be-graphql"], None, None),
        }),
        q("Q1_SW_B2", "Data modeling?", {
            "A": ({"backend-dev": 20}, ["be-db-design"], None, None),
            "B": ({"backend-dev": 10}, [], None, None),
            "C": ({"backend-dev": 10}, [], None, None),
            "D": ({"backend-dev": 5}, [], None, None),
        }),
        q("Q1_SW_FS", "Full-stack preference?", {
            "A": ({"fullstack-dev": 25}, [], None, None),
            "B": ({"fullstack-dev": 20}, [], None, None),
            "C": ({"fullstack-dev": 15}, [], None, None),
            "D": ({"fullstack-dev": 10}, [], None, None),
        }),
        q("Q1_DA_A", "Analyst tooling?", {
            "A": ({"data-analyst": 20}, ["da-sql"], None, None),
            "B": ({"data-analyst": 25}, ["da-excel"], None, None),
            "C": ({"data-analyst": 15, "data-scientist": 15}, [], None, None),
            "D": ({"data-scientist": 20}, [], None, None),
        }),
        q("Q1_DA_B", "Visualization?", {
            "A": ({"data-analyst": 15}, [], None, None),
            "B": ({"data-analyst": 20}, [], None, None),
            "C": ({"data-analyst": 15, "data-scientist": 10}, [], None, None),
            "D": ({"data-scientist": 15}, [], None, None),
        }),
        q("Q1_DE_A", "Pipeline tooling?", {
            "A": ({"data-engineer": 25}, ["de-airflow"], None, None),
            "B": ({"data-engineer": 20}, [], None, None),
            "C": ({"data-engineer": 15}, [], None, None),
            "D": ({"data-engineer": 10}, [], None, None),
        }),
        q("Q1_DS_A", "Statistics depth?", {
            "A": ({"data-scientist": 25}, [], None, None),
            "B": ({"data-scientist": 20}, [], None, None),
            "C": ({"data-scientist": 15}, [], None, None),
            "D": ({"data-scientist": 10}, [], None, None),
        }),
        q("Q1_ML_A", "ML deployment?", {
            "A": ({"ml-engineer": 15}, [], None, None),
            "B": ({"ml-engineer": 25}, ["ml-deployment"], None, None),
            "C": ({"ml-engineer": 20}, [], None, None),
            "D": ({"ml-engineer": 10}, [], None, None),
        }),
        q("Q1_ML_B", "Model training?", {
            "A": ({"ml-engineer": 15}, [], None, None),
            "B": ({"ml-engineer": 15}, [], None, None),
            "C": ({"ml-engineer": 10}, [], None, None),
            "D": ({"ml-engineer": 25}, ["nlp-hf"], None, None),
        }),
        q("Q1_NLP_A", "NLP focus?", {
            "A": ({"nlp-engineer": 25}, [], None, None),
            "B": ({"nlp-engineer": 20}, [], None, None),
            "C": ({"nlp-engineer": 15}, [], None, None),
            "D": ({"nlp-engineer": 10}, [], None, None),
        }),
        q("Q1_CREATIVE_A", "Design focus?", {
            "A": ({"ui-ux-designer": 30}, ["ux-research"], None, None),
            "B": ({"graphic-designer": 25}, [], None, None),
            "C": ({"ui-ux-designer": 20}, [], None, None),
            "D": ({"creative-director": 15}, [], None, None),
        }),
        q("Q1_GRAPHIC_A", "Brand work?", {
            "A": ({"graphic-designer": 25}, [], None, None),
            "B": ({"graphic-designer": 20}, [], None, None),
            "C": ({"ui-ux-designer": 15}, [], None, None),
            "D": ({"creative-director": 10}, [], None, None),
        }),
        q("Q_DIFF_DS_vs_DA", "Scientist vs analyst?", {
            "A": ({"data-scientist": 30}, [], None, None),
            "B": ({"data-analyst": 30}, [], None, None),
            "C": ({"data-scientist": 15, "data-analyst": 15}, [], None, None),
            "D": ({"data-scientist": 10}, [], None, None),
        }),
        q("Q_EXP", "Experience level?", {
            "A": ({}, [], "intern", None),
            "B": ({}, [], "junior", None),
            "C": ({}, [], "mid", None),
            "D": ({}, [], "senior", None),
        }),
        q("Q_PROJECT", "Recent project type?", {
            "A": ({"frontend-dev": 10, "backend-dev": 10}, [], None, None),
            "B": ({"ml-engineer": 15}, [], None, None),
            "C": ({"data-scientist": 10}, [], None, None),
            "D": ({"backend-dev": 15}, [], None, None),
            "E": ({"ui-ux-designer": 15}, [], None, None),
        }),
    ]

    payload = {
        "questions": questions,
        "tiebreaker_map": {
            "data-scientist|data-analyst": "Q_DIFF_DS_vs_DA",
            "data-analyst|data-scientist": "Q_DIFF_DS_vs_DA",
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(questions)} questions to {OUT_PATH}")


if __name__ == "__main__":
    main()
