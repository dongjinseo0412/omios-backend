# OMIOS 백엔드 Railway 배포 가이드

이 문서는 `omios-backend`를 Railway에 배포하기 전 확인해야 할 코드 상태, Railway Variables 매핑, DB import/검증, smoke test 절차를 정리합니다.

## 1. 현재 저장소 배포 준비 상태

필수 파일 확인 결과, Railway 배포에 필요한 핵심 파일은 모두 존재합니다.

| 항목 | 파일/디렉터리 | 상태 |
| --- | --- | --- |
| FastAPI 앱 진입점 | `app/main.py` | 확인됨 |
| DB 연결 설정 | `app/database.py` | 확인됨 |
| CORS 설정 | `app/config.py` | 확인됨 |
| 운영 시작 명령 | `Procfile` | 확인됨 |
| Python 의존성 | `requirements.txt` | 확인됨 |
| MySQL 스키마 | `omios_mysql_schema.sql` | 확인됨 |
| CSV 원천 데이터 | `data/*.csv` | 확인됨 |
| CSV import | `import_omios_csv_to_mysql.py` | 확인됨 |
| DB count 검증 | `scripts/check_db_counts.py` | 확인됨 |
| API smoke test | `scripts/smoke_test.py` | 확인됨 |
| 일반 배포 문서 | `DEPLOYMENT.md` | 확인됨 |
| Railway 배포 문서 | `RAILWAY_DEPLOYMENT.md` | 확인됨 |
| 로컬 env 예시 | `.env.example` | 확인됨 |

현재 치명적인 누락 항목은 없습니다. `railway.toml`은 없습니다. 현재 `Procfile`만으로 Railway start command 요구사항을 충족하므로 필수는 아닙니다.

## 2. Railway 실행 명령

현재 `Procfile`은 다음과 같습니다.

```Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Railway public service는 `0.0.0.0:$PORT`로 listen해야 합니다. 현재 명령은 이 조건을 만족합니다.

Railway 대시보드에서 Start Command를 직접 지정해야 하는 경우에는 아래 값을 사용합니다.

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

`railway.toml`을 추가하고 싶다면 아래 형태를 사용할 수 있지만, 현재 저장소에서는 `Procfile`과 중복될 수 있으므로 필수로 추가하지 않습니다.

```toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

## 3. 환경변수

### 3.1 백엔드가 읽는 변수

`app/database.py`는 다음 DB 변수를 읽습니다.

```txt
OMIOS_DB_HOST
OMIOS_DB_PORT
OMIOS_DB_USER
OMIOS_DB_PASSWORD
OMIOS_DB_NAME
```

`app/config.py`는 다음 CORS 변수를 읽습니다.

```txt
OMIOS_CORS_ORIGINS
OMIOS_CORS_ALLOW_CREDENTIALS
```

`.env.example`에는 예시 값만 두고, 실제 DB 비밀번호나 운영 secret은 절대 커밋하지 않습니다. `.gitignore`는 `.env`, `.env.*`를 제외하고 `.env.example`만 허용합니다.

### 3.2 Railway MySQL 변수 매핑

Railway MySQL은 보통 다음 변수를 제공합니다.

```txt
MYSQLHOST
MYSQLPORT
MYSQLUSER
MYSQLPASSWORD
MYSQLDATABASE
MYSQL_URL
```

현재 코드는 `OMIOS_DB_*`를 읽으므로 백엔드 서비스 Variables에 아래처럼 매핑합니다.

```txt
OMIOS_DB_HOST=${{ MySQL.MYSQLHOST }}
OMIOS_DB_PORT=${{ MySQL.MYSQLPORT }}
OMIOS_DB_USER=${{ MySQL.MYSQLUSER }}
OMIOS_DB_PASSWORD=${{ MySQL.MYSQLPASSWORD }}
OMIOS_DB_NAME=${{ MySQL.MYSQLDATABASE }}
```

주의: `MySQL` 부분은 실제 Railway DB 서비스 이름에 맞게 수정해야 합니다. 예를 들어 DB 서비스명이 `omios-db`라면 `${{ omios-db.MYSQLHOST }}` 형태로 바꿉니다.

### 3.3 CORS 변수

프론트엔드 배포 주소를 백엔드 CORS에 반드시 포함해야 합니다.

```txt
OMIOS_CORS_ORIGINS=https://your-frontend.vercel.app
OMIOS_CORS_ALLOW_CREDENTIALS=false
```

현재 코드는 여러 origin을 쉼표로 구분해서 파싱합니다.

```txt
OMIOS_CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

운영 배포에서 로컬 개발 주소만 허용된 상태라면 브라우저에서 CORS 오류가 발생할 수 있습니다.

## 4. Railway 대시보드 수동 작업

다음 작업은 코드가 아니라 사용자가 Railway 대시보드에서 직접 처리해야 합니다.

- Railway 계정 생성 및 GitHub 연결
- Railway 프로젝트 생성
- GitHub repo에서 `omios-backend` 서비스 생성
- 같은 Railway 프로젝트 안에 MySQL 서비스 추가
- 백엔드 서비스 Variables 설정
- 백엔드 서비스 Start Command 확인
- Public Domain 생성
- 생성된 백엔드 URL을 프론트엔드 `VITE_API_BASE_URL`에 반영
- 프론트엔드 배포 주소를 백엔드 `OMIOS_CORS_ORIGINS`에 반영

## 5. Railway CLI 배포 흐름

이미 Railway 프로젝트가 있는 경우:

```bash
railway login
railway link
railway up
```

새 프로젝트를 만드는 경우:

```bash
railway login
railway init
railway up
```

## 6. DB 스키마 생성, CSV import, row count 검증

최초 Railway MySQL 세팅 시 아래 명령으로 스키마를 재생성하고 CSV 데이터를 import합니다.

```bash
railway run python import_omios_csv_to_mysql.py --data-dir ./data --schema ./omios_mysql_schema.sql --reset
```

주의: `--reset`은 기존 테이블을 삭제하고 재생성합니다. 최초 세팅 외에는 운영 데이터 삭제 위험이 있으므로 사용하지 마세요.

import 후 row count를 검증합니다.

```bash
railway run python scripts/check_db_counts.py
```

기대 row count:

```txt
regions: 32
price_ranges: 6
gift_targets: 8
age_groups: 8
keywords: 70
purchase_locations: 328
products: 1525
product_targets: 5561
product_age_groups: 5522
product_keywords: 7416
product_links: 0
product_purchase_locations: 1294
```

## 7. 배포 후 health check와 smoke test

Health check URL:

```txt
https://your-backend.up.railway.app/api/health
```

기대 응답:

```json
{
  "status": "OK",
  "message": "server is running"
}
```

배포 API smoke test:

```bash
OMIOS_API_BASE_URL=https://your-backend.up.railway.app python scripts/smoke_test.py
```

`scripts/smoke_test.py`는 최소한 다음 항목을 확인합니다.

- `/api/health`
- 상품 목록
- 상품 상세
- 존재하지 않는 상품 에러
- 지역 목록/상세
- 필터
- 검색
- 가격대
- 키워드
- 선물 대상
- 연령대
- 구매처
- 외부 링크

## 8. 현재 주의사항

- `product_links` 테이블은 현재 0건입니다.
- API는 `products.source_note`가 URL이면 fallback 링크로 반환할 수 있습니다.
- `sort=popular`는 실제 인기순이 아닙니다.
- 현재 스키마에 `view_count`, `link_click_count`가 없으므로 `product_code ASC` fallback일 수 있습니다.
- `requirements.txt`는 현재 패키지 버전이 고정되어 있지 않습니다. 운영 재현성 측면에서 향후 버전 고정을 권장합니다.
- Docker 기반 배포를 원한다면 `Dockerfile`이 필요하지만, 현재 Railway 배포는 `Procfile`/Start Command 기반으로 충분할 수 있습니다.
