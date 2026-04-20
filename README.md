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

# AWS Lambda + EventBridge 배포 가이드

## 1. Docker 이미지 빌드 및 ECR 푸시

```bash
# ECR 리포지토리 생성
aws ecr create-repository --repository-name ECR레포지토리이름

# Docker 이미지 빌드 (Ubuntu/Linux)
docker build -t ECRIMAGE경로 .
# (MAC)
docker buildx build --platform linux/amd64 -t ECRIMAGE경로 .

# ECR 로그인
aws ecr get-login-password --region <aws-region> | docker login --username AWS --password-stdin <password>

# 이미지 푸시
docker push ECRIMAGE경로
```

## 2. IAM 역할 생성

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
    ]
}
```
이렇게 Assume Role을 지정해주고, 연결되는 정책에 AWSLambdaBasicExecutionRole 또는 귀찮으면 FullAcces 추가 `!해당 정책 ARN 기억해두기!`

## 3. Lambda 함수 생성

```bash
# Lambda 함수 생성 (Container Image)
aws lambda create-function \
    --function-name LAMBDA_NAME \
    --package-type Image \
    --code ImageUri=이미지경로 \
    --role 2번에서지정한RoleARN \
    --timeout 300 \
    --memory-size 512 \
    --environment "Variables={GITHUB_USERNAME=깃허브사용자이름,GITHUB_TOKEN=토큰이름,GITHUB_API_URL=https://api.github.com}"
  
# 확인 방법
aws lambda get-function --function-name LAMBDA_NAME
```

## 4. EventBridge 스케줄 생성

```bash
# EventBridge 규칙 생성 (한국시간 기준 매일 오전 9시 실행)
aws events put-rule \
    --name EVENTBRIDGE_NAME \
    --schedule-expression "cron(0 9 * * ? *)" \
    --description "Daily GitHub auto follow/unfollow"

# 이거 생성하고 ARN확인하는 방법
aws events list-rules --name-prefix EVENTBRIDGE_NAME

# Lambda에 Eventbridge 권한 부여
aws lambda add-permission \
    --function-name LAMBDA_NAME \
    --statement-id allow-eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn EVENTBRIDGE_ARN
    
# Lambda 함수를 타겟으로 추가
aws events put-targets \
  --rule EVENTBRIDGE_NAME \
  --targets "Id"="1","Arn"="LAMBDA_ARN"
```

## 5. 이미지 업데이트 시
```bash
aws lambda update-function-code \
  --function-name LAMBDA_NAME \
  --image-uri ECR이미지경로
```

## 6. 람다함수 환경변수 교체 시
```bash
aws lambda update-function-configuration \
  --function-name LAMBDA_NAME \
  --environment "Variables={KEY1=VAL1,KEY2=VAL2,....}"
```
