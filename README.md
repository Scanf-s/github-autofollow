# Serverless 아키텍쳐 기반 깃허브 자동 팔로우/언팔로우 스크립트

깃허브 팔로우/언팔로우 수동으로 하기 귀찮아서 자동화 스크립트 만들었고,  
AWS Serverless 기능들 사용해서 하루에 한번씩 실행되도록 구성했습니다.  
Free tier 기준 비용 안나오니 안심해주세요.

팔로워 여러명있을 때 동기식으로 처리하면 오래걸리니까, aiohttp 사용해서 비동기로 처리하도록, 코루틴 함수 기반으로 작성되어 있습니다.

<img width="1108" height="223" alt="스크린샷 2025-09-16 오후 3 45 36" src="https://github.com/user-attachments/assets/3b573ad4-91bc-480e-9f80-5c6671eb2b3e" />

# 로컬 실행 가이드

## 1. 요구 사항
- Python 3.12 이상
- [uv](https://github.com/astral-sh/uv) (권장) 또는 pip

## 2. 환경변수 설정

`.env.example` 을 복사해서 `.env` 파일을 만들고 값을 채워 넣습니다.

```bash
cp .env.example .env
```

GitHub Personal Access Token 은 [여기](https://github.com/settings/tokens)에서 발급받을 수 있고,
필요한 scope 은 `user:follow`, `read:user` 입니다.

## 3. 의존성 설치 및 실행

### uv 사용 시 (권장)
```bash
uv sync
uv run python main.py
```

### pip 사용 시
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python main.py
```

실행하면 현재 계정 기준으로 다음 동작을 수행합니다.
- 나를 팔로우했지만 내가 맞팔하지 않은 사용자 → 팔로우
- 내가 팔로우했지만 나를 팔로우하지 않은 사용자 → 언팔로우

## 4. 옵션

### CLI 플래그
- `--dry-run` : 실제 변경 없이 대상 목록만 출력
- `--concurrency N` : 동시 API 요청 수 (기본 5)

```bash
uv run python main.py --dry-run
uv run python main.py --concurrency 10
```

### 환경변수 (선택)
- `CONCURRENCY` : 동시 요청 수 (CLI 플래그 우선)
- `EXCLUDE_FOLLOW` : 맞팔하지 않을 사용자 목록 (쉼표 구분)
- `EXCLUDE_UNFOLLOW` : 언팔하지 않을 사용자 목록 (쉼표 구분)
- `DRY_RUN` : Lambda 에서 dry-run 모드로 실행 (`1`/`true`)

## 5. 테스트

```bash
uv run pytest
```

---

# AWS Deploy Guide

## 1. Prepare your own AWS account with Access key and Secret key
- For easy management, you can attach Administrator role into your IAM User.

## 2. Issue your Github API Key

## 3. Build lambda function
```bash
make build
```

## 4. Deploy AWS infrastructure (Only for first time)
```bash
sam deploy --guided
```

`--guided` will prompt you for the following. Values are saved to `samconfig.toml`, so subsequent deploys do not need them again.

| Prompt | Description | Example |
| --- | --- | --- |
| `Stack Name` | CloudFormation stack name (any unique name within the account/region) | `github-autofollow` |
| `AWS Region` | Region to deploy to | `ap-northeast-2` |
| `Parameter LambdaFunctionName` | Lambda function name | `GithubAutoFollowLambda` |
| `Parameter GithubUsername` | Your GitHub username | `blabla` |
| `Parameter GithubToken` | GitHub Personal Access Token (`user:follow`, `read:user` scopes) | `ghp_xxx...` |
| `Parameter GithubApiUrl` | GitHub API endpoint (press Enter to use default) | `https://api.github.com` |
| `Parameter ScheduleExpression` | EventBridge schedule (rate or cron) — see section 6 | `rate(3 hours)` |
| `Confirm changes before deploy` | Review changesets before applying | `Y/N` |
| `Allow SAM CLI IAM role creation` | Required for the Lambda execution role | `Y/N` |
| `Save arguments to configuration file` | Save answers to `samconfig.toml` | `Y/N` |

You can just press Enter to accept the defaults.

## 5. (Optional) Update function
```bash
make build
sam deploy
```

## 6. Change the EventBridge schedule

The Lambda is triggered by an EventBridge rule defined via the `ScheduleExpression` parameter in `template.yml`. You can change it without editing the template by passing a parameter override.

Supported expression formats (see [AWS docs](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rate-expressions.html)):
- `rate(N minutes|hours|days)` — fixed interval. e.g. `rate(1 hour)`, `rate(1 day)`
- `cron(min hour day month day-of-week year)` — UTC, 6 fields. One of `day` / `day-of-week` must be `?`. e.g. `cron(0 0 * * ? *)` runs daily at 00:00 UTC (09:00 KST)

Update only the schedule on an existing stack:
```bash
sam deploy \
  --parameter-overrides ScheduleExpression="rate(1 day)"
```

Or edit `samconfig.toml` (`parameter_overrides`) so the new value sticks for future deploys.
