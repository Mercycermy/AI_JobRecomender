"""Run the Step 16 reliability hardening validation gate."""

from __future__ import annotations

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


def _tail(value: str, lines: int = 20) -> str:
    parts = value.strip().splitlines()
    return "\n".join(parts[-lines:])


def _run_check(check: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    env = os.environ.copy()
    env.update(check.get("env", {}))
    completed = subprocess.run(
        check["cmd"],
        cwd=check.get("cwd", ROOT),
        env=env,
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


def _checks() -> List[Dict[str, Any]]:
    return [
        {
            "area": "reliability_tests",
            "name": "Config, auth, rate-limit, error-shape, and migration tests",
            "cmd": _python_command(
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "tests/test_reliability.py",
                "-q",
            ),
        },
        {
            "area": "fast_backend_tests",
            "name": "Backend fast lane without ML-heavy tests",
            "cmd": _python_command(
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-m",
                "not ml",
                "tests",
                "-q",
                "--tb=short",
            ),
        },
        {
            "area": "startup_config",
            "name": "Production startup rejects missing secret",
            "cmd": _python_command(
                "-c",
                (
                    "from app.config import AppConfig; "
                    "c=AppConfig(); "
                    "\ntry:\n c.validate_startup(); raise SystemExit(1)"
                    "\nexcept RuntimeError as exc:\n"
                    " raise SystemExit(0 if 'FLASK_SECRET_KEY' in str(exc) else 1)"
                ),
            ),
            "env": {"APP_ENV": "production", "FLASK_SECRET_KEY": ""},
        },
    ]


def main() -> int:
    results = [_run_check(check) for check in _checks()]
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
