"""Validate Step 14 connected frontend flow wiring."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(source: str, needle: str, label: str, failures: list[str]) -> None:
    if needle not in source:
        failures.append(label)


def main() -> None:
    failures: list[str] = []

    app = read("frontend/src/App.jsx")
    layout = read("frontend/src/components/Layout.jsx")
    flow = read("frontend/src/components/FlowProgress.jsx")
    results = read("frontend/src/pages/Results.jsx")
    css = read("frontend/src/App.css")

    route_checks = {
        "/quiz": "quiz route",
        "/manual": "manual skill input route",
        "/results": "results route",
        "/results/resources": "learning resources route",
        "/results/resume": "resume tips route",
        "/resume-builder": "resume builder route",
        "/telegram-jobs": "Telegram jobs route",
        "/admin": "admin dashboard route",
        "/results/gap/": "skill gap details route",
    }
    for route, label in route_checks.items():
        require(app, route, label, failures)

    nav_checks = [
        "/quiz",
        "/manual",
        "/results",
        "/results/resources",
        "/results/resume",
        "/telegram-jobs",
        "/admin",
    ]
    for href in nav_checks:
        require(layout, f"href: '{href}'", f"navigation link {href}", failures)

    flow_checks = ["Profile", "Matches", "Gaps", "Learning", "Resume", "Jobs"]
    for label in flow_checks:
        require(flow, f"label: '{label}'", f"flow step {label}", failures)

    result_checks = [
        "profile-summary-grid",
        "Skill level",
        "Next learning action",
        "Resume action",
        "Current jobs",
        "missing-skill-strip",
        "job-card-actions",
        "/telegram-jobs",
        "/resume-builder",
    ]
    for needle in result_checks:
        require(results, needle, f"results surface {needle}", failures)

    page_flow_checks = {
        "frontend/src/pages/Home.jsx": "home flow strip",
        "frontend/src/pages/ManualInput.jsx": "manual flow strip",
        "frontend/src/pages/Quiz.jsx": "quiz flow strip",
        "frontend/src/pages/SkillGap.jsx": "skill gap flow strip",
        "frontend/src/pages/LearningResources.jsx": "learning flow strip",
        "frontend/src/pages/ResumeTips.jsx": "resume tips flow strip",
        "frontend/src/pages/ResumeBuilder.jsx": "resume builder flow strip",
        "frontend/src/pages/TelegramJobs.jsx": "Telegram flow strip",
    }
    for path, label in page_flow_checks.items():
        require(read(path), "FlowProgress", label, failures)

    css_checks = [
        ".flow-progress",
        ".flow-steps",
        ".flow-step",
        ".profile-summary-grid",
        ".missing-skill-strip",
        ".job-card-actions",
        "@media (max-width: 980px)",
        "@media (max-width: 760px)",
    ]
    for needle in css_checks:
        require(css, needle, f"style {needle}", failures)

    if failures:
        raise SystemExit(
            "Step 14 frontend flow validation failed: " + "; ".join(failures)
        )

    print(
        json.dumps(
            {
                "status": "passed",
                "routes_checked": len(route_checks),
                "nav_links_checked": len(nav_checks),
                "flow_steps_checked": len(flow_checks),
                "flow_pages_checked": len(page_flow_checks),
                "style_checks": len(css_checks),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
