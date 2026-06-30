"""Refresh active Telegram job posts from configured public channels."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai_tips import GroqResumeCoach
from app.skill_normalizer import SkillNormalizer
from app.telegram_jobs import DEFAULT_TELEGRAM_CHANNELS, TelegramJobIngestionService


def main() -> None:
    service = TelegramJobIngestionService(
        normalizer=SkillNormalizer(),
        ai_extractor=GroqResumeCoach(),
    )
    result = service.refresh_channels(DEFAULT_TELEGRAM_CHANNELS, per_channel_limit=12)
    print(json.dumps({
        "fetched_posts": result["fetched_posts"],
        "inserted": result["inserted"],
        "updated": result["updated"],
        "deduped": result["deduped"],
        "skipped": result["skipped"],
        "active_total": result["active_total"],
        "channels": result["channels"],
    }, indent=2))


if __name__ == "__main__":
    main()
