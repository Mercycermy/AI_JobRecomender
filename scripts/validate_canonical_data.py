"""Validate current data/ files against the canonical step-2 model."""

from __future__ import annotations

import json
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.canonical import build_data_folder_report, build_full_data_folder_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate current data/ files against the canonical step-2 model."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Validate every CSV job row and every quiz question instead of samples.",
    )
    args = parser.parse_args()

    report = build_full_data_folder_report() if args.full else build_data_folder_report()
    print(json.dumps(report, indent=2))

    has_errors = any(
        report.get(key, 0)
        for key in (
            "skill_validation_errors",
            "learning_resource_validation_errors",
            "sample_job_validation_errors",
            "job_validation_errors",
            "quiz_question_validation_errors",
        )
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
