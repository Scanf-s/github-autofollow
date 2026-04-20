from aioresponses import aioresponses

from service.GithubAutoFollowNUnfollow import GithubAutoFollowNUnfollow


BASE = "https://api.github.com"


def _make_service(**kwargs) -> GithubAutoFollowNUnfollow:
    defaults = dict(username="me", token="tkn", api_url=BASE, concurrency=2, max_retries=2)
    defaults.update(kwargs)
    return GithubAutoFollowNUnfollow(**defaults)


async def test_run_follows_non_mutuals_and_unfollows_non_followers():
    service = _make_service()
    with aioresponses() as m:
        m.get(f"{BASE}/users/me/followers?per_page=100&page=1", payload=[{"login": "a"}, {"login": "b"}])
        m.get(f"{BASE}/users/me/followers?per_page=100&page=2", payload=[])
        m.get(f"{BASE}/users/me/following?per_page=100&page=1", payload=[{"login": "b"}, {"login": "c"}])
        m.get(f"{BASE}/users/me/following?per_page=100&page=2", payload=[])
        m.put(f"{BASE}/user/following/a", status=204)
        m.delete(f"{BASE}/user/following/c", status=204)

        summary = await service.run()

    assert summary["follow_attempts"] == 1
    assert summary["follow_success"] == 1
    assert summary["unfollow_attempts"] == 1
    assert summary["unfollow_success"] == 1


async def test_dry_run_does_not_call_mutation_endpoints():
    service = _make_service(dry_run=True)
    with aioresponses() as m:
        m.get(f"{BASE}/users/me/followers?per_page=100&page=1", payload=[{"login": "a"}])
        m.get(f"{BASE}/users/me/followers?per_page=100&page=2", payload=[])
        m.get(f"{BASE}/users/me/following?per_page=100&page=1", payload=[{"login": "z"}])
        m.get(f"{BASE}/users/me/following?per_page=100&page=2", payload=[])
        # PUT/DELETE 는 등록하지 않음 — 호출되면 aioresponses 가 ConnectionError 발생시킴

        summary = await service.run()

    assert summary["dry_run"] is True
    assert summary["follow_success"] == 1
    assert summary["unfollow_success"] == 1


async def test_exclude_lists_filter_targets():
    service = _make_service(exclude_follow=["A"], exclude_unfollow=["c"])
    with aioresponses() as m:
        m.get(f"{BASE}/users/me/followers?per_page=100&page=1", payload=[{"login": "a"}, {"login": "b"}])
        m.get(f"{BASE}/users/me/followers?per_page=100&page=2", payload=[])
        m.get(f"{BASE}/users/me/following?per_page=100&page=1", payload=[{"login": "c"}, {"login": "d"}])
        m.get(f"{BASE}/users/me/following?per_page=100&page=2", payload=[])
        m.put(f"{BASE}/user/following/b", status=204)
        m.delete(f"{BASE}/user/following/d", status=204)

        summary = await service.run()

    assert summary["follow_attempts"] == 1
    assert summary["unfollow_attempts"] == 1


async def test_retry_on_secondary_rate_limit():
    service = _make_service(max_retries=3)
    with aioresponses() as m:
        m.get(f"{BASE}/users/me/followers?per_page=100&page=1", payload=[{"login": "a"}])
        m.get(f"{BASE}/users/me/followers?per_page=100&page=2", payload=[])
        m.get(f"{BASE}/users/me/following?per_page=100&page=1", payload=[])

        # 첫 번째 PUT 은 Retry-After 와 함께 429, 두 번째는 성공
        m.put(f"{BASE}/user/following/a", status=429, headers={"Retry-After": "1"})
        m.put(f"{BASE}/user/following/a", status=204)

        summary = await service.run()

    assert summary["follow_success"] == 1
    assert summary["follow_failed"] == 0


async def test_failed_follow_counted_in_summary():
    service = _make_service(max_retries=1)
    with aioresponses() as m:
        m.get(f"{BASE}/users/me/followers?per_page=100&page=1", payload=[{"login": "a"}])
        m.get(f"{BASE}/users/me/followers?per_page=100&page=2", payload=[])
        m.get(f"{BASE}/users/me/following?per_page=100&page=1", payload=[])
        m.put(f"{BASE}/user/following/a", status=500)

        summary = await service.run()

    assert summary["follow_attempts"] == 1
    assert summary["follow_success"] == 0
    assert summary["follow_failed"] == 1
