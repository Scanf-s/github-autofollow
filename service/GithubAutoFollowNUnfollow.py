import asyncio
import logging
import time
from typing import Any, Iterable, Optional

import aiohttp


logger = logging.getLogger(__name__)


class GithubAutoFollowNUnfollow:
    def __init__(
        self,
        username: str,
        token: str,
        api_url: str = "https://api.github.com",
        concurrency: int = 5,
        max_retries: int = 3,
        dry_run: bool = False,
        exclude_follow: Optional[Iterable[str]] = None,
        exclude_unfollow: Optional[Iterable[str]] = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.dry_run = dry_run
        self.exclude_follow = {u.lower() for u in (exclude_follow or [])}
        self.exclude_unfollow = {u.lower() for u in (exclude_unfollow or [])}
        self._headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        session: aiohttp.ClientSession,
        sem: asyncio.Semaphore,
        method: str,
        url: str,
    ) -> Any:
        """
        GitHub API 요청 헬퍼 함수
        primary/secondary rate limit 을 감지해서 재시도.
        """
        for attempt in range(1, self.max_retries + 1):
            async with sem:
                async with session.request(method, url, headers=self._headers) as resp:
                    if resp.status in (403, 429):
                        wait = self._rate_limit_wait_seconds(resp)
                        if wait is not None:
                            logger.warning(
                                "Rate limited on %s %s (status=%d). Sleeping %ds (attempt %d/%d)",
                                method, url, resp.status, wait, attempt, self.max_retries,
                            )
                            await asyncio.sleep(wait)
                            continue
                    resp.raise_for_status()
                    if method == "GET":
                        return await resp.json()
                    return None
        raise RuntimeError(f"Exhausted retries for {method} {url}")

    @staticmethod
    def _rate_limit_wait_seconds(resp: aiohttp.ClientResponse) -> Optional[int]:
        retry_after = resp.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(1, int(retry_after))
            except ValueError:
                return 1
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining == "0" and reset is not None:
            try:
                return max(1, int(reset) - int(time.time()) + 1)
            except ValueError:
                return 1
        return None

    async def _get_users(
        self,
        session: aiohttp.ClientSession,
        sem: asyncio.Semaphore,
        behavior: str,
    ) -> set[str]:
        users: set[str] = set()
        page = 1
        while True:
            url = f"{self.api_url}/users/{self.username}/{behavior}?per_page=100&page={page}"
            try:
                page_users = await self._request(session, sem, "GET", url)
            except (aiohttp.ClientError, RuntimeError) as e:
                logger.error("Failed to fetch %s page %d: %s", behavior, page, e)
                break
            if not page_users:
                break
            users.update(u["login"] for u in page_users)
            page += 1
        return users

    async def _follow(self, session: aiohttp.ClientSession, sem: asyncio.Semaphore, target: str) -> bool:
        if self.dry_run:
            logger.info("[dry-run] follow %s", target)
            return True
        try:
            await self._request(session, sem, "PUT", f"{self.api_url}/user/following/{target}")
            logger.info("Followed %s", target)
            return True
        except (aiohttp.ClientError, RuntimeError) as e:
            logger.error("Failed to follow %s: %s", target, e)
            return False

    async def _unfollow(self, session: aiohttp.ClientSession, sem: asyncio.Semaphore, target: str) -> bool:
        if self.dry_run:
            logger.info("[dry-run] unfollow %s", target)
            return True
        try:
            await self._request(session, sem, "DELETE", f"{self.api_url}/user/following/{target}")
            logger.info("Unfollowed %s", target)
            return True
        except (aiohttp.ClientError, RuntimeError) as e:
            logger.error("Failed to unfollow %s: %s", target, e)
            return False

    async def run(self) -> dict:
        sem = asyncio.Semaphore(self.concurrency)
        async with aiohttp.ClientSession() as session:
            followers = await self._get_users(session, sem, "followers")
            following = await self._get_users(session, sem, "following")

            logger.info("Followers: %d, Following: %d", len(followers), len(following))

            to_follow = {u for u in (followers - following) if u.lower() not in self.exclude_follow}
            to_unfollow = {u for u in (following - followers) if u.lower() not in self.exclude_unfollow}

            logger.info("Targets — follow: %d, unfollow: %d", len(to_follow), len(to_unfollow))
            if self.dry_run:
                logger.info("Dry-run 활성화: 실제 팔로우/언팔로우는 수행되지 않습니다.")

            follow_results = await asyncio.gather(
                *(self._follow(session, sem, u) for u in to_follow)
            ) if to_follow else []
            unfollow_results = await asyncio.gather(
                *(self._unfollow(session, sem, u) for u in to_unfollow)
            ) if to_unfollow else []

        summary = {
            "followers": len(followers),
            "following": len(following),
            "follow_attempts": len(to_follow),
            "follow_success": sum(follow_results),
            "follow_failed": len(to_follow) - sum(follow_results),
            "unfollow_attempts": len(to_unfollow),
            "unfollow_success": sum(unfollow_results),
            "unfollow_failed": len(to_unfollow) - sum(unfollow_results),
            "dry_run": self.dry_run,
        }
        logger.info("Summary: %s", summary)
        return summary
