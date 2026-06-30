from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.learning_path import LearningPath


def test_learning_path_ranks_by_gap_priority_difficulty_usefulness_and_cost(tmp_path):
	resources_path = tmp_path / "learning_resources.json"
	resources_path.write_text(
		json.dumps(
			{
				"resources": [
					{
						"resource_id": "paid-advanced",
						"skill_id": "ops-docker",
						"title": "Advanced Paid Docker Course",
						"platform": "CourseCo",
						"url": "https://example.com/paid",
						"resource_type": "course",
						"difficulty": "advanced",
						"is_free": 0,
						"estimated_hours": 40,
						"covers": ["Docker"],
						"job_gap_alignment": {
							"gap_priority": "low",
							"why_this_resource": "Deep but not the first Docker step.",
						},
						"verification_status": "verified",
						"source_quality": "community",
					},
					{
						"resource_id": "free-official",
						"skill_id": "ops-docker",
						"title": "Docker Official Quickstart",
						"platform": "official-docs",
						"url": "https://example.com/docker",
						"resource_type": "documentation",
						"difficulty": "beginner",
						"is_free": 1,
						"estimated_hours": 6,
						"covers": ["Docker", "Images", "Compose"],
						"job_gap_alignment": {
							"gap_priority": "high",
							"why_this_resource": "Best first step for Docker gaps.",
						},
						"verification_status": "verified",
						"source_quality": "official",
					},
				]
			}
		),
		encoding="utf-8",
	)

	path = LearningPath(resources_path=str(resources_path))
	groups = path.recommend_resources(
		[
			{
				"skill_id": "ops-docker",
				"skill": "Docker",
				"priority": 90,
				"priority_label": "High",
				"current": 20,
				"required": 80,
			}
		],
		limit_per_skill=2,
	)

	assert len(groups) == 1
	resources = groups[0]["resources"]
	assert resources[0]["resource_id"] == "free-official"
	assert resources[0]["cost"] == "free"
	assert resources[0]["link"] == "https://example.com/docker"
	assert resources[0]["recommendation_score"] > resources[1]["recommendation_score"]
	assert resources[0]["explanation"] == "Best first step for Docker gaps."


def test_learning_path_keeps_plain_skill_id_compatibility(tmp_path):
	resources_path = tmp_path / "learning_resources.json"
	resources_path.write_text(
		json.dumps(
			{
				"resources": [
					{
						"resource_id": "sql-1",
						"skill_id": "lang-sql",
						"title": "SQL Basics",
						"platform": "Docs",
						"url": "https://example.com/sql",
						"difficulty": "beginner",
						"is_free": 1,
						"estimated_hours": 4,
						"job_gap_alignment": {"gap_priority": "medium"},
					}
				]
			}
		),
		encoding="utf-8",
	)

	path = LearningPath(resources_path=str(resources_path))
	groups = path.recommend_resources(["lang-sql"])

	assert groups[0]["skill_id"] == "lang-sql"
	assert groups[0]["resources"][0]["title"] == "SQL Basics"
	assert groups[0]["resources"][0]["cost"] == "free"
