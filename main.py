import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from service.GithubAutoFollowNUnfollow import GithubAutoFollowNUnfollow


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> int:
    load_dotenv()

    github_username = os.getenv("GITHUB_USERNAME")
    github_token = os.getenv("GITHUB_TOKEN")
    github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")

    if not github_username or not github_token:
        logger.error(
            "GITHUB_USERNAME 또는 GITHUB_TOKEN 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인해주세요."
        )
        return 1

    logger.info("Github Follow/Unfollow script 실행")
    service = GithubAutoFollowNUnfollow(
        username=github_username,
        token=github_token,
        api_url=github_api_url,
    )
    await service.run()
    logger.info("작업 완료")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
