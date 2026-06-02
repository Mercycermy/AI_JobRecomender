"""
Interview-style assessment questions (10+ per canonical role).

Each role receives 12 questions: behavioral, technical/scenario, and practical
exercises modeled on real hiring interviews.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.quiz_engine import (  # noqa: E402
	CATEGORY_TO_ROLES,
	ROLE_DISPLAY_LABELS,
	ROLE_TO_CATEGORY,
)

MIN_QUESTIONS_PER_ROLE = 12

ROLE_SKILLS: Dict[str, List[str]] = {
	"frontend-dev": ["fe-react", "fe-css", "lang-js", "fe-html"],
	"backend-dev": ["be-api", "be-sql", "lang-py"],
	"fullstack-dev": ["fe-react", "be-api", "be-sql", "lang-js"],
	"mobile-dev": ["fe-react", "lang-js"],
	"devops": ["be-api", "lang-py"],
	"tech": ["it-support", "tech-docker"],
	"data-analyst": ["finance-excel", "be-sql"],
	"data-scientist": ["lang-py", "lang-py"],
	"ml-engineer": ["lang-py", "tech-docker"],
	"graphic-designer": ["design-uiux"],
	"ui-ux-designer": ["design-uiux"],
	"video-editor": ["design-uiux"],
	"creative": ["design-uiux", "marketing-digital"],
	"project-manager": ["admin-hr", "freelance-management"],
	"sales": ["sales-inbound"],
	"digital-marketer": ["marketing-digital"],
	"sales_marketing": ["marketing-digital", "sales-inbound"],
	"accounting": ["finance-excel"],
	"finance": ["finance-excel"],
	"admin": ["admin-hr", "admin-data-entry"],
	"architect": ["eng-autocad", "eng-construction-mgmt"],
	"teacher": ["edu-instructional-design"],
	"trainer": ["edu-instructional-design"],
	"education": ["edu-instructional-design"],
	"transport": ["supply-chain-mgmt", "logistics-safety"],
	"medical": ["med-health-science"],
	"general": ["admin-data-entry"],
}


def _domain_for_role(role: str) -> str:
	return ROLE_TO_CATEGORY.get(role, "GENERAL")


def _skills(role: str) -> Dict[str, int]:
	ids = ROLE_SKILLS.get(role, ["admin-data-entry"])
	weight = max(10, 80 // len(ids))
	return {skill_id: weight for skill_id in ids}


def _rubric(*rows: tuple[str, int, str]) -> List[Dict[str, Any]]:
	return [
		{"criterion": criterion, "points": points, "strong_evidence": evidence}
		for criterion, points, evidence in rows
	]


def _base_question(
	role: str,
	index: int,
	*,
	difficulty: str,
	question_type: str,
	stem: str,
	context: str,
	practical_task: Optional[Dict[str, Any]] = None,
	extra_skills: Optional[Dict[str, int]] = None,
	rubric_rows: Optional[List[tuple[str, int, str]]] = None,
	ai_hint: str = "",
	minutes: int = 6,
) -> Dict[str, Any]:
	title = ROLE_DISPLAY_LABELS.get(role, role.replace("-", " ").title())
	skill_weights = _skills(role)
	if extra_skills:
		skill_weights.update(extra_skills)

	rows = rubric_rows or [
		(
			"Role relevance",
			40,
			f"Answer demonstrates hands-on {title} experience with concrete examples.",
		),
		(
			"Structured thinking",
			35,
			"Clear steps, tradeoffs, and conclusions — like a strong interview answer.",
		),
		(
			"Communication",
			25,
			"Concise, professional language appropriate for a hiring manager.",
		),
	]

	return {
		"id": f"Q_ROLE_INT_{role.upper().replace('-', '_')}_{index:02d}",
		"gate": 2,
		"domain_scope": _domain_for_role(role),
		"question_type": question_type,
		"role_targets": [role],
		"difficulty": difficulty,
		"experience_level_target": "any",
		"stem": stem.format(role=title, role_slug=role, title=title),
		"context": context.format(role=title, role_slug=role, title=title),
		"answer_mode": "free_text",
		"options": None,
		"practical_task": practical_task,
		"scoring": {
			"max_score": 100,
			"pass_score": 70,
			"category_weights": {role: 40},
			"skill_weights": skill_weights,
			"rubric": _rubric(*rows),
			"red_flags": [
				"Vague answer with no examples",
				"Claims expertise but cannot explain basic workflow",
			],
			"partial_credit_rules": [
				"Award partial credit when the approach is sound but missing metrics or edge cases.",
			],
		},
		"ai_evaluation_prompt": (
			ai_hint
			or f"Evaluate this as a hiring manager interviewing a {title} candidate. "
			"Score against the rubric; reward specifics, metrics, and tradeoffs."
		).format(role=title, role_slug=role),
		"job_evidence": [
			{
				"category": role,
				"job_titles": [title],
				"evidence_skills": ", ".join(skill_weights.keys()),
				"dataset_frequency_note": "Role interview bank v1",
				"source_url": None,
				"source_note": "Curated interview-style assessment",
			}
		],
		"routing": {"strong": "PASS", "partial": "PASS", "weak": "FAIL"},
		"estimated_minutes": minutes,
	}


# Role-specific technical / scenario blocks (interview depth)
ROLE_BLOCKS: Dict[str, List[Dict[str, Any]]] = {
	"frontend-dev": [
		{
			"difficulty": "beginner",
			"type": "experience",
			"stem": "Walk me through a {role} project you shipped. What was the user problem, your technical choices, and how you validated the UI worked?",
			"context": "Opening interview question — tests ownership and communication.",
		},
		{
			"difficulty": "beginner",
			"type": "behavioral",
			"stem": "Tell me about a time you disagreed with a designer or PM on a UI decision. How did you resolve it while protecting user experience?",
			"context": "Behavioral — collaboration under pressure.",
		},
		{
			"difficulty": "intermediate",
			"type": "technical",
			"stem": "A React page re-renders on every keystroke and feels sluggish. How do you diagnose and fix it without rewriting the whole screen?",
			"context": "Live troubleshooting — performance and React mental model.",
			"rubric": [
				("Diagnosis", 30, "Mentions profiling, React DevTools, state placement, memoization."),
				("Fix plan", 40, "Concrete steps: lift state, useMemo/useCallback, virtualization, debouncing."),
				("Validation", 30, "Describes measuring before/after (Lighthouse, UX metrics)."),
			],
		},
		{
			"difficulty": "intermediate",
			"type": "technical",
			"stem": "How do you approach accessibility (WCAG) when building a new component library or form flow?",
			"context": "Tests professional frontend standards.",
		},
		{
			"difficulty": "intermediate",
			"type": "scenario",
			"stem": "Production bug: checkout works in staging but fails for 5% of users in Chrome only. Walk through your investigation from browser to API.",
			"context": "Incident-style interview scenario.",
		},
		{
			"difficulty": "advanced",
			"type": "technical",
			"stem": "Compare client-side vs server-side rendering for a marketing site vs a logged-in dashboard. What would you choose and why?",
			"context": "Architecture tradeoffs — senior signal.",
		},
		{
			"difficulty": "intermediate",
			"type": "practical",
			"stem": "Practical: Design the state and component breakdown for a searchable, filterable job list (loading, empty, error states).",
			"context": "Written exercise — no code required, but structure matters.",
			"practical": {
				"language": "none",
				"starter_code": None,
				"expected_output": "Component tree, state ownership, and UX states documented.",
				"constraints": ["Include loading and error handling", "Explain where filters live"],
				"edge_cases": ["Slow network", "zero results"],
				"tools_allowed": ["Plain text / pseudocode"],
			},
		},
		{
			"difficulty": "beginner",
			"type": "behavioral",
			"stem": "Describe a mistake you shipped to production as a {role}. What happened, how you fixed it, and what guardrail you added?",
			"context": "Accountability and learning.",
		},
		{
			"difficulty": "intermediate",
			"type": "technical",
			"stem": "How do you structure API error handling and loading states when consuming REST/GraphQL from the frontend?",
			"context": "Integration competency.",
		},
		{
			"difficulty": "advanced",
			"type": "scenario",
			"stem": "You have one week to migrate a legacy jQuery page to React behind a feature flag. How do you scope and de-risk the rollout?",
			"context": "Planning under constraints.",
		},
		{
			"difficulty": "intermediate",
			"type": "metrics",
			"stem": "Which frontend metrics would you track after launching a new onboarding flow, and what would make you roll back?",
			"context": "Product-aware engineering.",
		},
		{
			"difficulty": "advanced",
			"type": "judgment",
			"stem": "A stakeholder asks you to add a third-party script that may hurt performance but boosts revenue tracking. How do you respond?",
			"context": "Ethics, performance, and stakeholder management.",
		},
	],
	"backend-dev": [
		{"difficulty": "beginner", "type": "experience", "stem": "Describe the most complex API or service you built as a {role}. Include scale, data store, and failure modes you planned for.", "context": "Opening — depth of experience."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a production outage you helped resolve. What was your role and what did you change afterward?", "context": "Operational maturity."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Design a REST API for user registration with email verification. What endpoints, status codes, and idempotency rules apply?", "context": "API design interview classic."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain how you would find and fix an N+1 query problem in a Python/Node service backed by PostgreSQL.", "context": "Database performance."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Latency on a critical endpoint jumped from 120ms to 2s after a deploy. Outline your debugging steps.", "context": "Live incident response."},
		{"difficulty": "advanced", "type": "technical", "stem": "When would you choose SQL vs a document store vs a cache for a new feature? Give a concrete example.", "context": "Data architecture judgment."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Write pseudocode for rate-limiting login attempts per IP and per account (explain data structures and TTL).", "context": "Security-minded design exercise.", "practical": {"language": "none", "starter_code": None, "expected_output": "Clear limits, storage choice, and reset rules.", "constraints": ["Handle distributed deployment"], "edge_cases": ["Shared NAT IP", "account lockout UX"], "tools_allowed": ["Pseudocode"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe a time you pushed back on a deadline because of technical debt. What was the outcome?", "context": "Prioritization."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you approach authentication and authorization for internal admin tools vs public APIs?", "context": "Security fundamentals."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You need to run a long-running report without blocking web workers. Sketch the architecture.", "context": "Async patterns — queues, workers."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "What SLIs/SLOs would you define for a payment webhook service?", "context": "Reliability engineering."},
		{"difficulty": "advanced", "type": "judgment", "stem": "A PM wants to expose raw SQL reporting to customers for speed. What risks do you raise and what alternatives do you offer?", "context": "Risk communication."},
	],
	"data-analyst": [
		{"difficulty": "beginner", "type": "experience", "stem": "Walk me through an analysis you delivered that changed a business decision. What data, methods, and audience?", "context": "Impact-focused opening."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a time stakeholders challenged your numbers. How did you validate and communicate your findings?", "context": "Influence and rigor."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain the difference between a metric, a dimension, and a KPI — with an example from e-commerce or SaaS.", "context": "Foundations."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How would you investigate a sudden 20% drop in weekly active users using SQL and dashboards?", "context": "Analytical troubleshooting."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Marketing says campaign A wins; finance says margins fell. How do you reconcile conflicting narratives?", "context": "Cross-functional analysis."},
		{"difficulty": "advanced", "type": "technical", "stem": "When do you use cohort analysis vs funnel analysis vs A/B testing? Give hiring-relevant examples.", "context": "Method selection."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Define metrics and one SQL outline to measure feature adoption for a new checkout button.", "context": "Hands-on analytics.", "practical": {"language": "sql", "starter_code": "-- tables: events(user_id, event_name, created_at)\n", "expected_output": "Metric definitions + query sketch with assumptions stated.", "constraints": ["State assumptions", "Address seasonality"], "edge_cases": ["Duplicate events", "bot traffic"], "tools_allowed": ["SQL pseudocode"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe a dashboard you built that nobody used. What did you learn?", "context": "Humility and iteration."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you document data definitions so marketing and product interpret charts consistently?", "context": "Data governance lite."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You have dirty event data after a tracking bug. How do you estimate impact on last month's report?", "context": "Data quality under pressure."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "What would you put on an executive one-pager for a growth review vs an ops review?", "context": "Communication layers."},
		{"difficulty": "advanced", "type": "judgment", "stem": "Leadership wants to cut a feature based on one week's data. How do you advise them?", "context": "Statistical judgment."},
	],
	"ui-ux-designer": [
		{"difficulty": "beginner", "type": "experience", "stem": "Present a {role} case study: problem, research, iterations, and measured outcome.", "context": "Portfolio-style interview opener."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about receiving harsh critique on your designs. How did you respond?", "context": "Resilience and growth."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Walk through your process from ambiguous brief to testable prototype.", "context": "End-to-end UX process."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you decide between usability testing, A/B tests, and analytics when validating a redesign?", "context": "Research methods."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Engineering says your design will slip the sprint by two weeks. How do you negotiate scope without harming UX?", "context": "Cross-functional scenario."},
		{"difficulty": "advanced", "type": "technical", "stem": "Explain how you design for accessibility and inclusive language in forms and error messages.", "context": "Professional UX standards."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Sketch (in words) a mobile flow for password reset including error states and success confirmation.", "context": "Whiteboard substitute.", "practical": {"language": "none", "starter_code": None, "expected_output": "Step-by-step screens with copy examples.", "constraints": ["Mobile-first", "Security-conscious copy"], "edge_cases": ["Expired link", "weak password"], "tools_allowed": ["Text description"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe a time user research contradicted your initial design intuition.", "context": "Evidence-based design."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you hand off specs to developers so implementation matches intent?", "context": "Delivery quality."},
		{"difficulty": "advanced", "type": "scenario", "stem": "Leadership wants dark patterns to boost conversions. How do you handle it?", "context": "Ethics interview question."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "Which UX metrics would you track after launching a redesigned onboarding?", "context": "Outcome orientation."},
		{"difficulty": "advanced", "type": "judgment", "stem": "You have 48 hours to improve activation. What do you do first and what do you explicitly not do?", "context": "Prioritization under pressure."},
	],
	"sales": [
		{"difficulty": "beginner", "type": "experience", "stem": "Walk me through your biggest closed deal as a {role}: discovery, stakeholders, objections, and close.", "context": "Sales interview classic."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a deal you lost. What would you do differently?", "context": "Coachability."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you qualify inbound leads so you spend time on the right opportunities?", "context": "Pipeline discipline."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Prospect says: 'Your competitor is 30% cheaper.' Role-play your response.", "context": "Live objection handling."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you run discovery calls without turning them into free consulting?", "context": "Methodology."},
		{"difficulty": "advanced", "type": "scenario", "stem": "A champion left the account mid-cycle. How do you save the deal?", "context": "Complex B2B scenario."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Write a 3-email follow-up sequence after a demo where the prospect went silent.", "context": "Written sales exercise.", "practical": {"language": "none", "starter_code": None, "expected_output": "Three emails with distinct angles and clear CTAs.", "constraints": ["No desperation tone", "Add value each touch"], "edge_cases": ["Legal/procurement delay"], "tools_allowed": ["Plain text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe handling an angry customer while protecting long-term relationship.", "context": "Emotional intelligence."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Which CRM fields and activities do you track to forecast accurately?", "context": "Operations hygiene."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You must hit quota but the product has a known bug affecting new logos. What do you do?", "context": "Ethics and escalation."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "Which metrics define a healthy pipeline for your segment (SMB vs enterprise)?", "context": "Quantitative sales thinking."},
		{"difficulty": "advanced", "type": "judgment", "stem": "Leadership offers a discount you believe will hurt renewals. How do you push back?", "context": "Judgment and negotiation."},
	],
	"fullstack-dev": [
		{"difficulty": "beginner", "type": "experience", "stem": "Describe an end-to-end feature you owned as a {role} — UI, API, database, and deployment.", "context": "Full ownership signal."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you decide what logic belongs in the frontend vs the backend for a new feature?", "context": "Architecture boundaries."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "A bug only appears when frontend and backend versions mismatch in production. How do you debug and prevent recurrence?", "context": "Integration incident."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain your approach to authentication sessions across SPA and API.", "context": "Security across stack."},
		{"difficulty": "advanced", "type": "technical", "stem": "How would you design a file upload feature with virus scanning and progress UI?", "context": "Cross-stack design."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: List API contracts and UI states for a 'save draft' feature on a multi-step form.", "context": "Spec discipline.", "practical": {"language": "none", "starter_code": None, "expected_output": "Endpoints, payloads, conflict rules, UI states.", "constraints": ["Versioning or timestamps"], "edge_cases": ["Two tabs open"], "tools_allowed": ["Text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about balancing speed vs quality when you are the only developer on a feature.", "context": "Prioritization."},
		{"difficulty": "intermediate", "type": "technical", "stem": "What is your testing strategy across unit, integration, and E2E for full stack work?", "context": "Quality practices."},
		{"difficulty": "advanced", "type": "scenario", "stem": "Database migration must ship with a UI change on the same day. How do you sequence and roll back?", "context": "Release planning."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "Which metrics would you monitor after launching a new billing flow?", "context": "Product impact."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe feedback from a designer or PM that improved your implementation.", "context": "Collaboration."},
		{"difficulty": "advanced", "type": "judgment", "stem": "Would you accept a monolith vs split services for a 5-person startup? Defend your answer.", "context": "System design judgment."},
	],
	"data-scientist": [
		{"difficulty": "beginner", "type": "experience", "stem": "Walk me through a modeling or experimentation project you led as a {role}.", "context": "Technical storytelling."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you detect and handle data leakage before training a model?", "context": "ML fundamentals."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain how you would design an A/B test for a product change — including power and guardrails.", "context": "Experiment design."},
		{"difficulty": "advanced", "type": "scenario", "stem": "Stakeholders want 'AI' in the deck but your model barely beats a baseline. How do you communicate results?", "context": "Honesty and influence."},
		{"difficulty": "intermediate", "type": "technical", "stem": "When is logistic regression enough, and when do you need gradient boosting or deep learning?", "context": "Model selection."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Define target, features, and validation strategy for predicting customer churn.", "context": "Problem framing.", "practical": {"language": "none", "starter_code": None, "expected_output": "Clear ML problem statement with metrics.", "constraints": ["Address class imbalance"], "edge_cases": ["Seasonality"], "tools_allowed": ["Text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a time your analysis was wrong. What did you change in your process?", "context": "Scientific mindset."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you document experiments so others can reproduce them?", "context": "Reproducibility."},
		{"difficulty": "advanced", "type": "scenario", "stem": "A model performs well offline but poorly online after deployment. What do you check?", "context": "Train-serve skew."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "Which metrics besides accuracy matter for imbalanced fraud detection?", "context": "Evaluation depth."},
		{"difficulty": "advanced", "type": "judgment", "stem": "How do you handle sensitive attributes (fairness) in hiring or credit models?", "context": "Responsible AI."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Describe feature engineering you did on messy real-world data.", "context": "Hands-on skill."},
	],
	"devops": [
		{"difficulty": "beginner", "type": "experience", "stem": "Describe a CI/CD or infrastructure improvement you shipped as a {role} and how you measured success.", "context": "Impact opening."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain blue/green vs rolling deployments and when each is risky.", "context": "Release engineering."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Production CPU is pegged after a deploy. Outline your triage in the first 15 minutes.", "context": "Incident command."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you manage secrets in pipelines and runtime (not in git)?", "context": "Security basics."},
		{"difficulty": "advanced", "type": "technical", "stem": "Design monitoring and alerting for a microservice that processes payments.", "context": "Observability design."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Write a checklist for a safe database migration in production.", "context": "Operational rigor.", "practical": {"language": "none", "starter_code": None, "expected_output": "Ordered steps with rollback.", "constraints": ["Backups", "Communication"], "edge_cases": ["Long-running migration"], "tools_allowed": ["Text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a time you said no to a risky release.", "context": "Judgment."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you approach Infrastructure as Code reviews?", "context": "Terraform/K8s hygiene."},
		{"difficulty": "advanced", "type": "scenario", "stem": "Cluster autoscaler keeps scaling but costs doubled. How do you investigate?", "context": "FinOps angle."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "What SLOs and error budgets would you set for an API gateway?", "context": "Reliability metrics."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Compare containers vs serverless for a spiky batch job.", "context": "Platform choice."},
		{"difficulty": "advanced", "type": "judgment", "stem": "Developers want SSH access to prod for debugging. What policy do you recommend?", "context": "Security vs velocity."},
	],
	"admin": [
		{"difficulty": "beginner", "type": "experience", "stem": "Summarize your {role} experience supporting teams — calendars, travel, documents, or HR coordination.", "context": "Scope of work."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Two executives need the same conference room at the same time. How do you handle it?", "context": "Prioritization and diplomacy."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you organize confidential files and access so the right people see the right data?", "context": "Information handling."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about juggling urgent requests from multiple managers.", "context": "Stress management."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Draft a brief meeting agenda and follow-up email for a cross-team planning session.", "context": "Written communication.", "practical": {"language": "none", "starter_code": None, "expected_output": "Agenda with timeboxes + action-oriented follow-up.", "constraints": ["Clear owners"], "edge_cases": ["Missing decisions"], "tools_allowed": ["Text"]}},
		{"difficulty": "intermediate", "type": "technical", "stem": "Which tools do you use for scheduling, ticketing, and document control?", "context": "Tooling fluency."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You discover a sensitive document was emailed to the wrong distribution list. Steps?", "context": "Incident response."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe improving an office process that saved time for the team.", "context": "Initiative."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "A visitor arrives without an appointment while leadership is in meetings. What do you do?", "context": "Front-desk judgment."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "How do you measure whether your admin support is effective?", "context": "Outcome thinking."},
		{"difficulty": "advanced", "type": "judgment", "stem": "You are asked to share employee information you are not sure is authorized. Response?", "context": "Confidentiality."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you prepare materials for board meetings or audits?", "context": "Attention to detail."},
	],
	"accounting": [
		{"difficulty": "beginner", "type": "experience", "stem": "Walk me through your experience with month-end close, AP/AR, or reconciliations as a {role}.", "context": "Technical opening."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you investigate a variance between the general ledger and a subsidiary report?", "context": "Reconciliation skill."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "A vendor invoice is missing PO approval but payment is due today. What do you do?", "context": "Controls vs deadlines."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain deferrals vs accruals with a simple example.", "context": "Accounting fundamentals."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You find duplicate payments in a batch. Steps to correct and prevent?", "context": "Error handling."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: List documents and checks you require before approving a large capital expense.", "context": "Control design.", "practical": {"language": "none", "starter_code": None, "expected_output": "Checklist with control purpose for each item.", "constraints": ["Segregation of duties"], "edge_cases": ["Urgent request"], "tools_allowed": ["Text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about meeting a tight filing or audit deadline.", "context": "Pressure handling."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you use Excel or ERP reports to support decision-making?", "context": "Systems skill."},
		{"difficulty": "advanced", "type": "judgment", "stem": "A manager asks you to reclassify expenses to hit budget. How do you respond?", "context": "Ethics."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "Which KPIs do you track for cash flow health?", "context": "Business partnership."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "Sales tax nexus changes for online orders. How do you research and implement?", "context": "Compliance awareness."},
		{"difficulty": "advanced", "type": "technical", "stem": "How would you design a chart of accounts for a new product line?", "context": "Structural thinking."},
	],
	"medical": [
		{"difficulty": "beginner", "type": "experience", "stem": "Summarize your clinical or patient-facing experience relevant to a {role} role and setting.", "context": "Regulated environment opener."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a time you caught a safety risk before harm occurred.", "context": "Patient safety priority."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you ensure accurate documentation while working under time pressure?", "context": "Documentation standards."},
		{"difficulty": "intermediate", "type": "scenario", "stem": "A patient refuses a standard protocol that the team recommends. How do you respond?", "context": "Ethics and communication."},
		{"difficulty": "intermediate", "type": "technical", "stem": "Explain infection control or hygiene steps relevant to your specialty.", "context": "Clinical competency."},
		{"difficulty": "advanced", "type": "scenario", "stem": "You notice a colleague bypassing protocol. What actions do you take?", "context": "Professional duty."},
		{"difficulty": "intermediate", "type": "practical", "stem": "Practical: Outline a handoff report when transferring a patient to the next shift.", "context": "Structured communication.", "practical": {"language": "none", "starter_code": None, "expected_output": "SBAR or equivalent with key fields.", "constraints": ["Include allergies and critical orders"], "edge_cases": ["Incomplete records"], "tools_allowed": ["Text template"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Describe supporting a distressed patient or family while staying professional.", "context": "Empathy under stress."},
		{"difficulty": "intermediate", "type": "technical", "stem": "How do you stay current with guidelines or training in your area?", "context": "Continuous learning."},
		{"difficulty": "advanced", "type": "scenario", "stem": "Equipment fails during a time-sensitive task. Walk through your immediate steps.", "context": "Crisis response."},
		{"difficulty": "intermediate", "type": "metrics", "stem": "What quality indicators matter in your setting (wait times, readmissions, satisfaction)?", "context": "Systems thinking."},
		{"difficulty": "advanced", "type": "judgment", "stem": "You are asked to work outside your scope of practice. How do you respond?", "context": "Scope and compliance."},
	],
}


def _generic_block(role: str) -> List[Dict[str, Any]]:
	"""Fallback 12-question interview set for roles without a custom block."""
	title = ROLE_DISPLAY_LABELS.get(role, role.replace("-", " ").title())
	return [
		{"difficulty": "beginner", "type": "experience", "stem": f"Walk me through your background and why you are pursuing a {title} role today.", "context": "Standard opening interview question."},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a time you had to learn a new tool or process quickly for {title} work. How did you ramp up?", "context": "Learning agility."},
		{"difficulty": "intermediate", "type": "technical", "stem": f"What are the core skills a strong {title} must demonstrate day to day? Give examples from your experience.", "context": "Role fundamentals."},
		{"difficulty": "intermediate", "type": "scenario", "stem": f"Describe a challenging situation on the job as a {title}. What made it hard and how did you handle it?", "context": "Situational judgment."},
		{"difficulty": "intermediate", "type": "technical", "stem": f"How do you prioritize when you have multiple deadlines as a {title}?", "context": "Organization and communication."},
		{"difficulty": "advanced", "type": "scenario", "stem": f"A stakeholder challenges your approach. How do you respond while keeping quality high?", "context": "Influence without authority."},
		{"difficulty": "intermediate", "type": "practical", "stem": f"Practical: Outline a step-by-step plan you would follow to deliver a typical weekly deliverable in a {title} role.", "context": "Process clarity exercise.", "practical": {"language": "none", "starter_code": None, "expected_output": "Ordered steps with owners and checkpoints.", "constraints": ["Include quality check"], "edge_cases": ["Blocked dependency"], "tools_allowed": ["Text"]}},
		{"difficulty": "beginner", "type": "behavioral", "stem": "Tell me about a mistake you made professionally. What did you learn?", "context": "Accountability."},
		{"difficulty": "intermediate", "type": "technical", "stem": f"What tools or methods do you rely on most as a {title}, and why?", "context": "Tooling depth."},
		{"difficulty": "advanced", "type": "scenario", "stem": f"You must cut scope by 30% but keep the outcome acceptable. How do you decide what to cut?", "context": "Tradeoffs under constraints."},
		{"difficulty": "intermediate", "type": "metrics", "stem": f"How do you know you did a good job in a {title} role? What signals or metrics do you use?", "context": "Outcome orientation."},
		{"difficulty": "advanced", "type": "judgment", "stem": f"Where do you see the biggest risks or compliance issues in {title} work, and how do you mitigate them?", "context": "Professional judgment."},
	]


def _build_role_questions(role: str) -> List[Dict[str, Any]]:
	block = ROLE_BLOCKS.get(role) or _generic_block(role)
	questions: List[Dict[str, Any]] = []
	for index, spec in enumerate(block[:MIN_QUESTIONS_PER_ROLE], start=1):
		rubric_rows = spec.get("rubric")
		questions.append(
			_base_question(
				role,
				index,
				difficulty=spec["difficulty"],
				question_type=spec.get("type", "free_response"),
				stem=spec["stem"],
				context=spec["context"],
				practical_task=spec.get("practical"),
				rubric_rows=rubric_rows,
				ai_hint=spec.get("ai_hint", ""),
				minutes=spec.get("minutes", 6),
			)
		)
	while len(questions) < MIN_QUESTIONS_PER_ROLE:
		index = len(questions) + 1
		questions.append(
			_base_question(
				role,
				index,
				difficulty="intermediate",
				question_type="scenario",
				stem="Describe another real situation where you had to make a tough judgment call as a {role}.",
				context="Additional depth question to round out the interview set.",
			)
		)
	return questions


def build_all_roles() -> List[Dict[str, Any]]:
	all_roles = sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles})
	questions: List[Dict[str, Any]] = []
	for role in all_roles:
		questions.extend(_build_role_questions(role))
	return questions


def write_bank(path: Optional[str] = None) -> str:
	path = path or os.path.join(BASE_DIR, "data", "questions_role_interviews.json")
	questions = build_all_roles()
	payload = {
		"metadata": {
			"version": "role-interviews-v1",
			"min_per_role": MIN_QUESTIONS_PER_ROLE,
			"roles": sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles}),
			"total": len(questions),
		},
		"questions": questions,
	}
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8") as handle:
		json.dump(payload, handle, indent=2)
	return path


if __name__ == "__main__":
	out = write_bank()
	roles = sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles})
	print(f"Wrote {out}")
	print(f"Roles: {len(roles)}, questions: {len(build_all_roles())}, per role: {MIN_QUESTIONS_PER_ROLE}")
