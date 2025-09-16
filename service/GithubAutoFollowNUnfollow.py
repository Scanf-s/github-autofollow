import aiohttp
import logging

class GithubAutoFollowNUnfollow:

    def __init__(self, username, token: str, api_url: str):
        self.github_api_url = api_url
        self.github_username = username
        self.github_token = token
        self.request_headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def get_users(self, behavior: str) -> set:
        users = set()
        page = 1
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    async with session.get(
                            url=f"{self.github_api_url}/users/{self.github_username}/{behavior}?per_page=100&page={page}",
                            headers=self.request_headers
                    ) as response:
                        response.raise_for_status()
                        page_users = await response.json()
                        if not page_users:
                            break

                    users.update(user["login"] for user in page_users)
                    page += 1

        except aiohttp.ClientError as e:
            logging.error(f"Failed to get users for behavior '{behavior}': {e}")

        return users

    async def follow_user(self, follow_target: str) -> None:
        request_url = f"{self.github_api_url}/user/following/{follow_target}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url=request_url, headers=self.request_headers) as response:
                    response.raise_for_status()
                    logging.info(f"Successfully followed {follow_target}")
        except aiohttp.ClientError as e:
            logging.error(f"Failed to follow {follow_target}: {e}")

    async def unfollow_user(self, unfollow_target: str) -> None:
        request_url = f"{self.github_api_url}/user/following/{unfollow_target}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url=request_url, headers=self.request_headers) as response:
                    response.raise_for_status()
                    logging.info(f"Successfully unfollowed {unfollow_target}")
        except aiohttp.ClientError as e:
            logging.error(f"Failed to unfollow {unfollow_target}: {e}")

    async def run(self) -> None:
        followers: set = await self.get_users("followers")
        following: set = await self.get_users("following")

        logging.info(f"Followers: {len(followers)}")
        logging.info(f"Following: {len(following)}")

        # Follow users who follow you, but you don't follow back
        to_follow = followers - following
        if len(to_follow) > 0:
            logging.info(f"Follow target list: {to_follow}")
            for user in to_follow:
                await self.follow_user(user)

        # Unfollow users who don't follow you back
        to_unfollow = following - followers
        if len(to_unfollow) > 0:
            logging.info(f"Unfollow target list: {to_unfollow}")
            for user in to_unfollow:
                await self.unfollow_user(user)

        logging.info("Job Done!")
