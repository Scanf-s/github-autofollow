# GitHub Auto Follow/Unfollow Script (Serverless)

A small automation script for GitHub follow/unfollow that I built because doing it manually was tedious. It runs on AWS Serverless components on a configurable schedule (e.g. once a day). Cost stays within the AWS Free Tier under typical usage.

When you have many followers, processing them synchronously takes a long time, so the script is written using `aiohttp` and coroutines to run requests asynchronously.

<img width="1108" height="223" alt="screenshot 2025-09-16 15 45 36" src="https://github.com/user-attachments/assets/3b573ad4-91bc-480e-9f80-5c6671eb2b3e" />

# Local Execution Guide

## 1. Requirements
- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## 2. Environment variables

Copy `.env.example` to `.env` and fill in the values.

```bash
cp .env.example .env
```

You can issue a GitHub Personal Access Token [here](https://github.com/settings/tokens). The required scopes are `user:follow` and `read:user`.

## 3. Install dependencies and run

### Using uv (recommended)
```bash
uv sync
uv run python main.py
```

### Using pip
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python main.py
```

When executed, the script performs the following actions on the current account:
- Users who follow you but you do not follow back → follow
- Users you follow but who do not follow you → unfollow

## 4. Options

### CLI flags
- `--dry-run` : List the target users without making any actual changes
- `--concurrency N` : Number of concurrent API requests (default: 5)

```bash
uv run python main.py --dry-run
uv run python main.py --concurrency 10
```

### Environment variables (optional)
- `CONCURRENCY` : Number of concurrent requests (CLI flag takes precedence)
- `EXCLUDE_FOLLOW` : Comma-separated list of users to skip when following
- `EXCLUDE_UNFOLLOW` : Comma-separated list of users to skip when unfollowing
- `DRY_RUN` : Run in dry-run mode on Lambda (`1` / `true`)

## 5. Tests

```bash
uv run pytest
```

---

# AWS Deploy Guide

## 1. Prepare your own AWS account with an Access Key and Secret Key
- For simplicity, you can attach the Administrator role to your IAM user.

## 2. Issue your GitHub API key

## 3. Build the Lambda function
```bash
make build
```

## 4. Deploy AWS infrastructure (first time only)
```bash
sam deploy --guided
```

`--guided` will prompt you for the following. The values are saved to `samconfig.toml`, so subsequent deploys do not need them again.

| Prompt | Description | Example |
| --- | --- | --- |
| `Stack Name` | CloudFormation stack name (any unique name within the account/region) | `github-autofollow` |
| `AWS Region` | Region to deploy to | `ap-northeast-2` |
| `Parameter LambdaFunctionName` | Lambda function name | `GithubAutoFollowLambda` |
| `Parameter GithubUsername` | Your GitHub username | `blabla` |
| `Parameter GithubToken` | GitHub Personal Access Token (`user:follow`, `read:user` scopes) | `ghp_xxx...` |
| `Parameter GithubApiUrl` | GitHub API endpoint (press Enter to use the default) | `https://api.github.com` |
| `Parameter ScheduleExpression` | EventBridge schedule (rate or cron) — see section 6 | `rate(3 hours)` |
| `Confirm changes before deploy` | Review changesets before applying | `Y/N` |
| `Allow SAM CLI IAM role creation` | Required for the Lambda execution role | `Y/N` |
| `Save arguments to configuration file` | Save answers to `samconfig.toml` | `Y/N` |

You can just press Enter to accept the defaults for any other prompts.

## 5. (Optional) Update the function
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

Or edit `samconfig.toml` (`parameter_overrides`) so the new value persists across future deploys.
