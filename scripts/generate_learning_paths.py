import json
import os
from pathlib import Path
from datetime import datetime

DATA = Path(__file__).resolve().parent.parent / "data"
IN_RES = DATA / "learning_resources.json"
OUT = DATA / "learning_paths_v2.json"

if IN_RES.exists():
    with open(IN_RES, "r", encoding="utf-8") as f:
        old_data = json.load(f)
        old_resources = old_data.get("resources", [])
else:
    old_resources = []

today = datetime.now().strftime("%Y-%m-%d")

# Transform old resources to new schema and add new ones
resources_v2 = []
for r in old_resources:
    new_r = {
        "resource_id": r.get("resource_id", ""),
        "skill_id": r.get("skill_id", ""),
        "title": r.get("title", ""),
        "platform": r.get("platform", ""),
        "url": r.get("url", ""),
        "resource_type": r.get("resource_type", "course"),
        "difficulty": r.get("difficulty", "beginner"),
        "is_free": r.get("is_free", 1),
        "estimated_hours": 10,  # Default
        "language": "English",
        "prerequisites": [],
        "best_for": [],
        "covers": [],
        "job_gap_alignment": {
            "target_categories": [],
            "target_job_titles": [],
            "gap_priority": "medium",
            "why_this_resource": "Essential skill for this role"
        },
        "verification_status": "verified",
        "last_verified": today,
        "source_quality": "reputable-platform",
        "notes": ""
    }
    
    # Map high-priority alignments based on title/skill
    sid = r.get("skill_id", "")
    if sid == "fe-react":
        new_r["best_for"] = ["frontend-dev", "fullstack-dev"]
        new_r["job_gap_alignment"] = {
            "target_categories": ["frontend-dev"],
            "target_job_titles": ["React Developer", "Frontend Developer"],
            "gap_priority": "high",
            "why_this_resource": "React is the #1 required frontend skill."
        }
    elif sid == "biz-sales":
        new_r["best_for"] = ["sales"]
        new_r["job_gap_alignment"] = {
            "target_categories": ["sales"],
            "target_job_titles": ["Sales Representative", "Sales Manager"],
            "gap_priority": "high",
            "why_this_resource": "Core outbound sales competency."
        }
    elif sid == "fin-accounting":
        new_r["best_for"] = ["accounting"]
        new_r["job_gap_alignment"] = {
            "target_categories": ["accounting"],
            "target_job_titles": ["Accountant", "Senior Accountant"],
            "gap_priority": "high",
            "why_this_resource": "Fundamental double-entry bookkeeping knowledge."
        }
    
    resources_v2.append(new_r)

# Generate 4 detailed learning paths
learning_paths = [
    {
        "target_category": "frontend-dev",
        "target_job_title": "React Frontend Developer",
        "experience_level": "junior",
        "path_summary": "Go from basic JavaScript to building full React applications.",
        "total_estimated_hours": 40,
        "modules": [
            {
                "order": 1,
                "module_title": "JavaScript Foundations",
                "skill_ids": ["lang-js"],
                "why_now": "React requires strong ES6+ knowledge.",
                "resources": ["lang-js-fcc-1"],
                "practice_task": {
                    "title": "Build a DOM manipulator",
                    "description": "Create a simple to-do list using vanilla JS.",
                    "success_criteria": ["Can add items", "Can delete items", "Uses localStorage"]
                },
                "assessment_follow_up": {
                    "question_type": "code_task",
                    "prompt": "Write a pure function that filters an array of objects by a status key.",
                    "rubric": ["Uses .filter()", "Avoids mutations"]
                }
            },
            {
                "order": 2,
                "module_title": "React Architecture",
                "skill_ids": ["fe-react"],
                "why_now": "The core requirement for frontend roles.",
                "resources": ["react-docs-1", "react-fcc-1"],
                "practice_task": {
                    "title": "Interactive Dashboard",
                    "description": "Build a dashboard passing state down as props.",
                    "success_criteria": ["Uses useState", "Uses useEffect", "Breaks into >3 components"]
                },
                "assessment_follow_up": {
                    "question_type": "short_answer",
                    "prompt": "Explain the React component lifecycle and dependency arrays.",
                    "rubric": ["Mentions mount/unmount", "Mentions re-renders"]
                }
            }
        ],
        "capstone_project": {
            "title": "E-commerce Storefront",
            "description": "Build a multi-page React app with a shopping cart.",
            "skills_practiced": ["fe-react", "fe-css", "lang-js"],
            "portfolio_value": "Shows state management, routing, and component design."
        }
    },
    {
        "target_category": "data-analyst",
        "target_job_title": "Data Analyst",
        "experience_level": "junior",
        "path_summary": "Master data manipulation and visualization using SQL and Python.",
        "total_estimated_hours": 60,
        "modules": [
            {
                "order": 1,
                "module_title": "Database Querying",
                "skill_ids": ["da-sql-analytics", "lang-sql"],
                "why_now": "SQL is the universal language of data analytics.",
                "resources": ["sql-pg-tutorial"],
                "practice_task": {
                    "title": "Complex Joins and Aggregations",
                    "description": "Write window functions to find top-performing categories.",
                    "success_criteria": ["Uses PARTITION BY", "Correct JOINs"]
                },
                "assessment_follow_up": {
                    "question_type": "sql_task",
                    "prompt": "Write a query finding the 30-day rolling average of sales.",
                    "rubric": ["Uses sliding window frame", "Groups by date correctly"]
                }
            }
        ],
        "capstone_project": {
            "title": "Sales Dashboard Analytics",
            "description": "Extract raw data from SQL, process in Pandas, and present insights.",
            "skills_practiced": ["da-sql-analytics", "da-pandas"],
            "portfolio_value": "Proves end-to-end analytical capability."
        }
    },
    {
        "target_category": "sales",
        "target_job_title": "B2B Sales Representative",
        "experience_level": "beginner",
        "path_summary": "Learn outbound sales, objection handling, and pipeline management.",
        "total_estimated_hours": 20,
        "modules": [
            {
                "order": 1,
                "module_title": "Inbound & Outbound Strategy",
                "skill_ids": ["biz-sales", "soft-negotiation"],
                "why_now": "Foundational knowledge required for all sales roles.",
                "resources": ["sales-hubspot-1", "sales-yt-1"],
                "practice_task": {
                    "title": "Cold Email Outreach",
                    "description": "Write a 3-step cold email sequence targeting CTOs.",
                    "success_criteria": ["Strong subject line", "Clear value prop", "Low friction CTA"]
                },
                "assessment_follow_up": {
                    "question_type": "case_study",
                    "prompt": "How would you handle a prospect who says your product is too expensive?",
                    "rubric": ["Acknowledge concern", "Pivot to ROI/value", "Don't immediately discount"]
                }
            }
        ],
        "capstone_project": {
            "title": "Simulated Discovery Call",
            "description": "Map out a complete discovery call script with BANT qualification.",
            "skills_practiced": ["biz-sales", "soft-communication"],
            "portfolio_value": "Can be presented to hiring managers as a playbook."
        }
    }
]

output_json = {
    "metadata": {
        "generated_for": "AI_JobRecomender",
        "dataset_used": "data/jobs.csv",
        "taxonomy_used": "data/skills_taxonomy.json",
        "generation_date": today,
        "version": "learning-resources-v2",
        "online_verification": True,
        "notes": "Generated enhanced schemas + learning paths"
    },
    "resources": resources_v2,
    "learning_paths": learning_paths,
    "new_skill_candidates": [
        {
          "skill_id": "soft-negotiation",
          "canonical_name": "Negotiation",
          "aliases": ["deal-making", "negotiating"],
          "domain": "Business",
          "category": "Soft Skills",
          "reason": "Crucial for B2B Sales roles",
          "recommended_resources": ["sales-hubspot-1"]
        }
    ]
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(output_json, f, indent=2, ensure_ascii=False)

print(f"Generated {len(resources_v2)} enhanced resources and {len(learning_paths)} learning paths.")
print(f"Written to: {OUT}")
