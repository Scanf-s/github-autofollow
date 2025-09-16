import logging
import os
import asyncio
from typing import Optional

from service.GithubAutoFollowNUnfollow import GithubAutoFollowNUnfollow


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Github의 팔로우 대상을 자동으로 팔로우해주고
    언팔로우 대상을 자동으로 언팔로우 해주는 자동화 스크립트
    """
    try:
        # Get GitHub credentials from environment variables
        github_username: Optional[str] = os.getenv("GITHUB_USERNAME")
        github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
        github_api_url: Optional[str] = os.getenv("GITHUB_API_URL", "https://api.github.com")

        if not github_username or not github_token:
            message: str = "해당 스크립트를 실행하기 위해 필요한 환경변수가 설정되지 않았습니다."
            logger.error("해당 스크립트를 실행하기 위해 필요한 환경변수가 설정되지 않았습니다.")
            return {
                'statusCode': 400,
                'body': {
                    'error': message
                }
            }

        # Run the GitHub auto follow/unfollow service
        logger.info("Github Follow/Unfollow script 실행")
        github_service: GithubAutoFollowNUnfollow = GithubAutoFollowNUnfollow(
            username=github_username,
            token=github_token,
            api_url=github_api_url
        )
        asyncio.run(github_service.run())

        logger.info("작업 완료")

        return {
            'statusCode': 200,
            'body': {
                'message': 'Github Follow/Unfollow 작업 완료',
            }
        }

    except Exception as e:
        error_msg: str = f"실행 도중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': {
                'error': error_msg
            }
        }