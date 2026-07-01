"""Run the Step 15 validation and quality-check gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _python_command(*args: str) -> List[str]:
    return [sys.executable, "-B", *args]


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _tail(value: str, lines: int = 20) -> str:
    parts = value.strip().splitlines()
    return "\n".join(parts[-lines:])


def _run_check(check: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        check["cmd"],
        cwd=check.get("cwd", ROOT),
        text=True,
        capture_output=True,
    )
    elapsed = round(time.perf_counter() - started, 2)
    result = {
        "area": check["area"],
        "name": check["name"],
        "status": "passed" if completed.returncode == 0 else "failed",
        "seconds": elapsed,
        "command": " ".join(str(part) for part in check["cmd"]),
    }
    if completed.returncode != 0:
        result["stdout_tail"] = _tail(completed.stdout)
        result["stderr_tail"] = _tail(completed.stderr)
    return result


def _checks(include_frontend: bool) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = [
        {
            "area": "quiz_routing",
            "name": "Quiz role coverage and adaptive routing",
            "cmd": _python_command("scripts/validate_quiz_adaptivity.py"),
        },
        {
            "area": "manual_profile_mapping",
            "name": "Manual profile canonical mapping",
            "cmd": _python_command("scripts/validate_manual_profile.py"),
        },
        {
            "area": "job_match_accuracy",
            "name": "Recommendation accuracy and stable ordering",
            "cmd": _python_command("scripts/validate_recommendation_accuracy.py"),
        },
        {
            "area": "skill_gap_quality",
            "name": "Skill-gap analysis structure and ordering",
            "cmd": _python_command("scripts/validate_skill_gap_analysis.py"),
        },
        {
            "area": "learning_resource_selection",
            "name": "Learning resource ranking",
            "cmd": _python_command("scripts/validate_learning_resources.py"),
        },
        {
            "area": "resume_tip_quality",
            "name": "Resume upload extraction and ATS tips",
            "cmd": _python_command("scripts/validate_resume_upload.py"),
        },
        {
            "area": "resume_export",
            "name": "Resume builder preview and exports",
            "cmd": _python_command("scripts/validate_resume_generator.py"),
        },
        {
            "area": "telegram_extraction_and_deduping",
            "name": "Telegram extraction, dedupe, storage, and matching",
            "cmd": _python_command("scripts/validate_telegram_jobs.py"),
        },
        {
            "area": "frontend_checks",
            "name": "Frontend flow wiring validator",
            "cmd": _python_command("scripts/validate_frontend_flow.py"),
        },
        {
            "area": "api_and_fixture_regression_tests",
            "name": "Focused API and fixture-backed pytest suite",
            "cmd": _python_command(
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "tests/test_routes.py",
                "tests/test_quiz_adaptive.py",
                "tests/test_profile_service.py",
                "tests/test_recommender.py",
                "tests/test_learning_path.py",
                "tests/test_resume_upload.py",
                "tests/test_resume_generator.py",
                "tests/test_telegram_jobs.py",
                "tests/test_step15_quality_fixtures.py",
                "-q",
            ),
        },
    ]
    if include_frontend:
        npm = _npm_command()
        checks.extend(
            [
                {
                    "area": "frontend_checks",
                    "name": "Frontend lint",
                    "cmd": [npm, "run", "lint"],
                    "cwd": ROOT / "frontend",
                },
                {
                    "area": "frontend_checks",
                    "name": "Frontend production build",
                    "cmd": [npm, "run", "build"],
                    "cwd": ROOT / "frontend",
                },
            ]
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Step 15 validation and quality checks."
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip npm lint/build checks when Node dependencies are unavailable.",
    )
    args = parser.parse_args()

    results = [_run_check(check) for check in _checks(not args.skip_frontend)]
    failed = [result for result in results if result["status"] != "passed"]
    report = {
        "status": "failed" if failed else "passed",
        "checks_run": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
