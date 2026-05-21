from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.gap_analyzer import GapAnalyzer


def test_gap_analyzer_basic():
	analyzer = GapAnalyzer()
	profile = {
		"detected_skills": ["python", "sql"],
		"experience_level": "junior",
		"top_category": "engineering",
	}
	# 3 recommended jobs with different missing skills
	recommendations = [
		{"job_id": 1, "missing_skills": ["docker", "kubernetes", "aws"]},
		{"job_id": 2, "missing_skills": ["docker", "kubernetes"]},
		{"job_id": 3, "missing_skills": ["docker"]},
	]

	gaps = analyzer.analyze(profile, recommendations)

	# docker is in 3/3 = 100% (High Priority)
	# kubernetes is in 2/3 = 67% (Medium Priority)
	# aws is in 1/3 = 33% (Low Priority)
	assert len(gaps) > 0
	
	docker_gap = next((g for g in gaps if g["skill_id"] == "docker"), None)
	kubernetes_gap = next((g for g in gaps if g["skill_id"] == "kubernetes"), None)
	aws_gap = next((g for g in gaps if g["skill_id"] == "aws"), None)

	assert docker_gap is not None
	assert docker_gap["priority"] == 100
	assert docker_gap["priority_label"] == "High"
	assert docker_gap["occurrences"] == 3

	assert kubernetes_gap is not None
	assert kubernetes_gap["priority"] == 67
	assert kubernetes_gap["priority_label"] == "Medium"
	assert kubernetes_gap["occurrences"] == 2

	assert aws_gap is not None
	assert aws_gap["priority"] == 33
	assert aws_gap["priority_label"] == "Low"
	assert aws_gap["occurrences"] == 1
