# OMIOS 백엔드 배포 가이드

이 백엔드는 OMIOS React 프론트엔드에서 사용하는 FastAPI + MySQL API 서버입니다.

## 1. 실행 환경 요구사항

- Python 3.11 이상
- MySQL 8 호환 서버
- DB 연결용 환경변수
- API 서버에서 MySQL 서버로 접근 가능한 네트워크 설정

런타임 의존성 설치:

```bash
pip install -r requirements.txt
```

## 2. 필수 환경변수

실제 비밀번호나 운영용 접속 정보는 커밋하지 마세요. 배포 플랫폼의 환경변수 또는 시크릿 설정에 등록해야 합니다.

```txt
OMIOS_DB_USER
OMIOS_DB_PASSWORD
OMIOS_DB_HOST
OMIOS_DB_PORT
OMIOS_DB_NAME
```

선택 환경변수:

```txt
OMIOS_CORS_ORIGINS
OMIOS_CORS_ALLOW_CREDENTIALS
PORT
ENV
```

### React 프론트엔드 CORS 설정

`OMIOS_CORS_ORIGINS`를 설정하지 않으면 백엔드는 로컬 React 개발 서버 주소만 허용합니다.

```txt
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

운영 배포에서는 실제 프론트엔드 배포 주소를 정확히 지정해야 합니다. 여러 개라면 쉼표로 구분합니다.

```txt
OMIOS_CORS_ORIGINS=https://your-react-frontend.example.com
```

프론트엔드가 쿠키나 인증 정보를 포함한 요청을 보내는 경우에만 `OMIOS_CORS_ALLOW_CREDENTIALS=true`를 사용하세요.

## 3. 로컬 실행

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

실행 후 아래 주소에서 상태를 확인합니다.

```txt
http://127.0.0.1:8000/api/health
```

## 4. 운영 서버 시작 명령

대부분의 배포 플랫폼에서는 아래 명령을 사용할 수 있습니다.

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

배포 플랫폼이 시작 명령에서 shell expansion을 지원하지 않는다면, 해당 플랫폼 문서에 맞게 포트를 직접 지정하세요.

## 5. 데이터베이스 생성 및 CSV import

새 비운영 DB를 준비하는 경우, 스키마를 생성하고 CSV 데이터를 import합니다.

```bash
python import_omios_csv_to_mysql.py --data-dir ./data --schema ./omios_mysql_schema.sql --reset
```

주의: `--reset` 옵션은 기존 테이블을 삭제한 뒤 다시 생성합니다. 운영 DB에서는 의도적으로 전체 초기화를 해야 하는 경우가 아니라면 사용하지 마세요.

읽기 전용 row count 검증:

```bash
python scripts/check_db_counts.py
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

## 6. Smoke test

서버를 실행한 뒤 아래 명령으로 기본 API 동작을 확인합니다.

```bash
python scripts/smoke_test.py
```

이미 배포된 API를 확인할 때는 배포 주소를 지정합니다.

```bash
OMIOS_API_BASE_URL=https://your-api.example.com python scripts/smoke_test.py
```

Smoke test는 health check, 상품 목록/상세, 필터, 검색, 마스터 데이터, 구매처, 링크, 문서화된 에러 응답을 확인합니다.

## 7. 배포 체크리스트

배포 전:

- [ ] `.env` 파일이 커밋되지 않았는지 확인합니다.
- [ ] API 런타임에서 MySQL에 접근할 수 있는지 확인합니다.
- [ ] `python scripts/check_db_counts.py`로 DB row count 검증을 통과합니다.
- [ ] `OMIOS_CORS_ORIGINS`에 React 프론트엔드 운영 배포 주소를 등록합니다.
- [ ] 로컬에서 `python scripts/smoke_test.py`가 통과하는지 확인합니다.
- [ ] 배포 플랫폼의 시작 명령을 설정합니다.

배포 후:

- [ ] `/api/health`가 200 응답을 반환합니다.
- [ ] `/api/products?page=1&limit=20`이 `totalCount: 1525`를 반환합니다.
- [ ] React 프론트엔드에서 CORS 오류 없이 API를 호출할 수 있습니다.
- [ ] 로그에 DB 비밀번호나 `.env` 내용이 출력되지 않습니다.

## 8. MVP 단계의 알려진 제한사항

- 현재 `product_links` 테이블에는 0건의 데이터가 있습니다. `/api/products/{productCode}/links`는 `products.source_note` 값이 URL 형식이면 fallback 링크로 사용합니다.
- 현재 운영 스키마의 `products` 테이블에는 `view_count`, `link_click_count` 컬럼이 없습니다. 따라서 `sort=popular`는 실제 인기순이 아니라 `product_code ASC` 정렬로 fallback됩니다.
- 데모나 운영 기능에서 실제 인기순 정렬이 필요하다면 스키마와 import 흐름에 해당 컬럼을 추가하고, API 정렬 로직을 `view_count DESC, link_click_count DESC` 기준으로 수정해야 합니다.
