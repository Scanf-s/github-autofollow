import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from service.GithubAutoFollowNUnfollow import GithubAutoFollowNUnfollow


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


async def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub 자동 팔로우/언팔로우")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경 없이 대상만 출력")
    parser.add_argument("--concurrency", type=int, default=None, help="동시 요청 수 (기본 5)")
    args = parser.parse_args()

    load_dotenv()

    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    concurrency = args.concurrency or int(os.getenv("CONCURRENCY", "5"))
    exclude_follow = _parse_csv(os.getenv("EXCLUDE_FOLLOW"))
    exclude_unfollow = _parse_csv(os.getenv("EXCLUDE_UNFOLLOW"))

    if not username or not token:
        logger.error(
            "GITHUB_USERNAME 또는 GITHUB_TOKEN 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인해주세요."
        )
        return 1

    service = GithubAutoFollowNUnfollow(
        username=username,
        token=token,
        api_url=api_url,
        concurrency=concurrency,
        dry_run=args.dry_run,
        exclude_follow=exclude_follow,
        exclude_unfollow=exclude_unfollow,
    )
    await service.run()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
