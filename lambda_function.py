import asyncio
import logging
import os
from typing import Optional

from service.GithubAutoFollowNUnfollow import GithubAutoFollowNUnfollow


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_bool(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def lambda_handler(event, context):
    try:
        username = os.getenv("GITHUB_USERNAME")
        token = os.getenv("GITHUB_TOKEN")
        api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        concurrency = int(os.getenv("CONCURRENCY", "5"))
        dry_run = _as_bool(os.getenv("DRY_RUN"))
        exclude_follow = _parse_csv(os.getenv("EXCLUDE_FOLLOW"))
        exclude_unfollow = _parse_csv(os.getenv("EXCLUDE_UNFOLLOW"))

        if not username or not token:
            msg = "Please setup environment variables before execute"
            logger.error(msg)
            return {"statusCode": 400, "body": {"error": msg}}

        service = GithubAutoFollowNUnfollow(
            username=username,
            token=token,
            api_url=api_url,
            concurrency=concurrency,
            dry_run=dry_run,
            exclude_follow=exclude_follow,
            exclude_unfollow=exclude_unfollow,
        )
        summary = asyncio.run(service.run())

        return {
            "statusCode": 200,
            "body": {"message": "Github Follow/Unfollow completed", "summary": summary},
        }

    except Exception as e:
        error_msg = f"Unexpected error occurred: {e}"
        logger.error(error_msg)
        return {"statusCode": 500, "body": {"error": error_msg}}
