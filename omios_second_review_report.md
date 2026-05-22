# OMIOS FastAPI + MySQL 백엔드 2차 검토 리포트

작성일: 2026-05-23  
검토 범위: DB 구조 문서, API 명세서 2개, 실제 MySQL 스키마/데이터, `app/main.py`, `app/database.py`, 실제 API 응답  
검토 원칙: 코드/CSV/DB 데이터 미수정, DB는 SELECT/SHOW/INFORMATION_SCHEMA 조회만 사용, `.env` 내용 미출력

---

## 1. 2차 검토 요약

### 전체 판단: 부분 통과

### 핵심 결론

- MySQL 연결, 주요 테이블, PK/FK, 다대다 연결, row count, API 핵심 동작은 MVP 기준으로 정상이다.
- API 명세서에 적힌 필수 엔드포인트는 모두 구현되어 있고, 실제 호출도 대부분 정상 응답을 반환한다.
- 다만 실제 DB 스키마는 `DB 구조 365aead1b34980188042d0aa45d29c33.md`와 완전히 같지는 않다. 특히 `products.view_count`, `products.link_click_count`, 여러 테이블의 `created_at/updated_at`, `is_active` 일부 컬럼이 실제 DB에 없다.
- `sort=popular`는 문서상 통계 컬럼 기반 정렬이어야 하나 실제 DB에 통계 컬럼이 없어 현재 `product_code ASC` fallback으로 동작한다. 오류 방지 목적의 임시 대응으로는 적절하지만, 인기순 기능으로는 미완성이다.
- `app/data` 폴더와 FastAPI 서버의 CSV 직접 조회 의존성은 제거된 것으로 확인된다.

---

## 2. 읽은 기준 파일

다음 파일을 실제로 읽고 기준으로 사용했다.

1. `DB 구조 365aead1b34980188042d0aa45d29c33.md`
2. `API 명세서 fc96fb140e988257930d018dd8bce4ce.csv`
3. `API 명세서 fc96fb140e988257930d018dd8bce4ce_all.csv`

---

## 3. DB 구조 문서 대비 실제 DB 비교

### 3-1. 테이블 존재 여부

문서/요구사항 기준 핵심 테이블은 모두 존재한다.

| 테이블 | 존재 여부 | 판단 |
| --- | --- | --- |
| products | 존재 | 통과 |
| regions | 존재 | 통과 |
| price_ranges | 존재 | 통과 |
| keywords | 존재 | 통과 |
| gift_targets | 존재 | 통과 |
| age_groups | 존재 | 통과 |
| purchase_locations | 존재 | 통과 |
| product_keywords | 존재 | 통과 |
| product_targets | 존재 | 통과 |
| product_age_groups | 존재 | 통과 |
| product_purchase_locations | 존재 | 통과 |
| product_links | 존재 | 통과 |

실제 `SHOW TABLES` 결과:

```txt
age_groups
gift_targets
keywords
price_ranges
product_age_groups
product_keywords
product_links
product_purchase_locations
product_targets
products
purchase_locations
regions
```

### 3-2. 컬럼 일치 여부 요약

#### products

문서상 주요 컬럼 중 실제 DB에 존재하는 컬럼:

- `product_code`
- `name_ko`
- `name_jp`
- `brand_name`
- `primary_region_code`
- `price_range_code`
- `price`
- `description`
- `purchase_tip`
- `is_region_limited`
- `image_url`
- `source_note`
- `created_at`
- `updated_at`

문서상 있으나 실제 DB에 없는 컬럼:

- `is_active`
- `view_count`
- `link_click_count`

실제 DB에 추가로 있는 컬럼:

- `collector`
- `collected_date`
- `note`

타입 차이:

| 컬럼 | 문서 | 실제 DB | 판단 |
| --- | --- | --- | --- |
| name_ko | VARCHAR(150) | VARCHAR(255) | 실제 DB가 더 넓음 |
| name_jp | VARCHAR(150) | VARCHAR(255) | 실제 DB가 더 넓음 |
| brand_name | VARCHAR(100) | VARCHAR(255) | 실제 DB가 더 넓음 |
| purchase_tip | VARCHAR(255) | TEXT | 실제 DB가 더 넓음 |
| image_url | VARCHAR(500) | TEXT | 실제 DB가 더 넓음 |
| source_note | VARCHAR(500) | TEXT | 실제 DB가 더 넓음 |
| created_at/updated_at | DATETIME | TIMESTAMP | 의미상 유사하지만 타입 다름 |

#### regions

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

문서상 비고에는 `parent_region` 제거라고 되어 있으나 실제 DB에는 다음 컬럼/FK가 존재한다.

- `parent_region_code`
- `fk_regions_parent`

실제 DB에 추가로 있는 컬럼:

- `parent_region_code`
- `note`

타입 차이:

| 컬럼 | 문서 | 실제 DB |
| --- | --- | --- |
| description | VARCHAR(255) | TEXT |

#### price_ranges

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `note`

#### keywords

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `description`
- `note`

#### gift_targets

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `description`
- `note`

#### age_groups

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `note`

#### purchase_locations

문서상 있으나 실제 DB에 없는 컬럼:

- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `note`

타입 차이:

| 컬럼 | 문서 | 실제 DB |
| --- | --- | --- |
| name | VARCHAR(150) | VARCHAR(255) |
| location_type | VARCHAR(50) | VARCHAR(100) |
| description | VARCHAR(255) | TEXT |
| address | VARCHAR(255) | TEXT |
| website_url | VARCHAR(500) | TEXT |

#### 연결 테이블

문서상 연결 테이블에는 대부분 `created_at`이 있으나 실제 DB에서는 `created_at` 대신 `note` 또는 `availability_status`가 존재한다.

| 테이블 | 문서상 추가 컬럼 | 실제 DB 컬럼 차이 |
| --- | --- | --- |
| product_keywords | created_at | 실제는 note |
| product_targets | created_at | 실제는 note |
| product_age_groups | created_at | 실제는 note |
| product_purchase_locations | is_active, created_at | 실제는 availability_status, note |

#### product_links

문서상 있으나 실제 DB에 없는 컬럼:

- `is_active`
- `created_at`
- `updated_at`

실제 DB에 추가로 있는 컬럼:

- `note`

타입 차이:

| 컬럼 | 문서 | 실제 DB |
| --- | --- | --- |
| url | VARCHAR(500) | TEXT |

### 3-3. view_count/link_click_count 관련 판단

- DB 구조 문서의 `products` 컬럼 목록과 “정렬 및 통계 기능 관련” 섹션에는 `view_count`, `link_click_count`가 명시되어 있다.
- 실제 `products` 테이블에는 두 컬럼이 없다.
- 따라서 이전 완료 보고의 “문서에는 있으나 실제 SQL 스키마에는 없음”이라는 주의 사항은 사실로 확인된다.

---

## 4. PK/FK 검증 결과

### 4-1. 문서 기준 PK와 실제 DB PK

| 테이블 | 문서 기준 PK | 실제 DB PK | 판단 |
| --- | --- | --- | --- |
| products | product_code | product_code | 통과 |
| regions | region_code | region_code | 통과 |
| price_ranges | price_range_code | price_range_code | 통과 |
| keywords | keyword_code | keyword_code | 통과 |
| gift_targets | target_code | target_code | 통과 |
| age_groups | age_group_code | age_group_code | 통과 |
| purchase_locations | location_code | location_code | 통과 |
| product_keywords | product_code, keyword_code | product_code, keyword_code | 통과 |
| product_targets | product_code, target_code | product_code, target_code | 통과 |
| product_age_groups | product_code, age_group_code | product_code, age_group_code | 통과 |
| product_purchase_locations | product_code, location_code | product_code, location_code | 통과 |
| product_links | link_code | link_code | 통과 |

### 4-2. 문서/요구사항 기준 FK와 실제 DB FK

| FK | 실제 DB 존재 여부 | 판단 |
| --- | --- | --- |
| products.primary_region_code → regions.region_code | 존재 | 통과 |
| products.price_range_code → price_ranges.price_range_code | 존재 | 통과 |
| purchase_locations.region_code → regions.region_code | 존재 | 통과 |
| product_keywords.product_code → products.product_code | 존재 | 통과 |
| product_keywords.keyword_code → keywords.keyword_code | 존재 | 통과 |
| product_targets.product_code → products.product_code | 존재 | 통과 |
| product_targets.target_code → gift_targets.target_code | 존재 | 통과 |
| product_age_groups.product_code → products.product_code | 존재 | 통과 |
| product_age_groups.age_group_code → age_groups.age_group_code | 존재 | 통과 |
| product_purchase_locations.product_code → products.product_code | 존재 | 통과 |
| product_purchase_locations.location_code → purchase_locations.location_code | 존재 | 통과 |
| product_links.product_code → products.product_code | 존재 | 통과 |

추가 FK:

- `regions.parent_region_code → regions.region_code`가 실제 DB에 존재한다. 문서 비고에서는 parent region 제거라고 되어 있어 문서와 실제 DB가 불일치한다.

---

## 5. row count 검증 결과

| 테이블 | 기대값 | 실제값 | 일치 여부 |
| --- | ---: | ---: | --- |
| regions | 32 | 32 | 일치 |
| price_ranges | 6 | 6 | 일치 |
| gift_targets | 8 | 8 | 일치 |
| age_groups | 8 | 8 | 일치 |
| keywords | 70 | 70 | 일치 |
| purchase_locations | 328 | 328 | 일치 |
| products | 1525 | 1525 | 일치 |
| product_targets | 5561 | 5561 | 일치 |
| product_age_groups | 5522 | 5522 | 일치 |
| product_keywords | 7416 | 7416 | 일치 |
| product_links | 0 | 0 | 일치 |
| product_purchase_locations | 1294 | 1294 | 일치 |

결론: 완료 보고의 row count는 모두 사실로 확인된다.

---

## 6. 다대다 연결 테이블 검증 결과

### 6-1. 복합 PK 여부

| 테이블 | 기대 복합 PK | 실제 복합 PK | 판단 |
| --- | --- | --- | --- |
| product_keywords | product_code, keyword_code | product_code, keyword_code | 통과 |
| product_targets | product_code, target_code | product_code, target_code | 통과 |
| product_age_groups | product_code, age_group_code | product_code, age_group_code | 통과 |
| product_purchase_locations | product_code, location_code | product_code, location_code | 통과 |

### 6-2. 중복 연결 여부

| 테이블 | 중복 조합 수 | 판단 |
| --- | ---: | --- |
| product_keywords | 0 | 통과 |
| product_targets | 0 | 통과 |
| product_age_groups | 0 | 통과 |
| product_purchase_locations | 0 | 통과 |

### 6-3. 외래키 무결성 여부

LEFT JOIN 기반으로 orphan 데이터를 재검증했다.

| 항목 | 누락 참조 수 | 판단 |
| --- | ---: | --- |
| products.primary_region_code가 regions에 없음 | 0 | 통과 |
| products.price_range_code가 price_ranges에 없음 | 0 | 통과 |
| purchase_locations.region_code가 regions에 없음 | 0 | 통과 |
| product_keywords.product_code가 products에 없음 | 0 | 통과 |
| product_keywords.keyword_code가 keywords에 없음 | 0 | 통과 |
| product_targets.product_code가 products에 없음 | 0 | 통과 |
| product_targets.target_code가 gift_targets에 없음 | 0 | 통과 |
| product_age_groups.product_code가 products에 없음 | 0 | 통과 |
| product_age_groups.age_group_code가 age_groups에 없음 | 0 | 통과 |
| product_purchase_locations.product_code가 products에 없음 | 0 | 통과 |
| product_purchase_locations.location_code가 purchase_locations에 없음 | 0 | 통과 |
| product_links.product_code가 products에 없음 | 0 | 통과 |

결론: 다대다 연결 구조와 참조 무결성은 정상이다.

---

## 7. API 명세서 대비 구현 상태

### 7-1. 구현된 API

명세서에 있는 다음 API는 모두 `app/main.py`에 구현되어 있다.

| API | 구현 여부 | 비고 |
| --- | --- | --- |
| GET /api/health | 구현 | 명세와 동일하게 `status`, `message` 반환 |
| GET /api/regions | 구현 | `statusCode`, `data` 반환 |
| GET /api/regions/{regionCode} | 구현 | 지역 상세 + keywords 반환 |
| GET /api/regions/{regionCode}/products | 구현 | pagination, totalCount 포함 |
| GET /api/regions/{regionCode}/keywords | 구현 | 지역별 keyword 객체 배열 반환 |
| GET /api/products | 구현 | 필터, 정렬, pagination, totalCount 포함 |
| GET /api/products/{productCode} | 구현 | 상세 관계 데이터 포함 |
| GET /api/products/search | 구현 | keyword 검색, pagination도 추가 지원 |
| GET /api/price-ranges | 구현 | master data 반환 |
| GET /api/keywords | 구현 | master data 반환 |
| GET /api/gift-targets | 구현 | master data 반환 |
| GET /api/age-groups | 구현 | master data 반환 |
| GET /api/products/{productCode}/purchase-locations | 구현 | 구매처 배열 반환 |
| GET /api/products/{productCode}/links | 구현 | product_links 또는 source_note fallback 반환 |

### 7-2. 누락된 API

- 명세서 기준 누락 API 없음.

### 7-3. 경로/메서드/파라미터 불일치

- 경로와 HTTP method는 명세와 일치한다.
- 필터 query parameter 이름은 명세와 일치한다.
  - `regionCode`
  - `priceRangeCode`
  - `keywordCode`
  - `targetCode`
  - `ageGroupCode`
  - `sort`
  - `page`
  - `limit`
- `/api/products/search`는 명세상 `keyword`만 예시로 있지만, 구현은 `page`, `limit`도 추가 지원한다. 추가 기능이며 호환성을 깨지는 않는다.

### 7-4. 응답 구조 일치 여부

대체로 명세와 일치한다.

확인된 사항:

- 일반 성공 응답은 대부분 `{ "statusCode": 200, "data": ... }` 구조다.
- `/api/health`는 명세 예시대로 `{ "status": "OK", "message": "server is running" }` 구조다.
- 상품 목록은 `items`, `page`, `limit`, `totalCount`를 포함한다.
- 상품 상세는 다음 필드를 포함한다.
  - `productCode`
  - `nameKo`
  - `nameJp`
  - `brandName`
  - `price`
  - `description`
  - `purchaseTip`
  - `imageUrl`
  - `isRegionLimited`
  - `region`
  - `priceRange`
  - `keywords`
  - `targets`
  - `ageGroups`
  - `purchaseLocations`
  - `links`
- DB snake_case 컬럼을 API camelCase로 변환한다.
- 에러 응답은 명세와 일치한다.
  - `PRODUCT_NOT_FOUND`
  - `REGION_NOT_FOUND`
  - `INVALID_PARAMETER`

주의할 응답 차이:

- `/api/products/{productCode}/links`의 fallback 링크는 `linkCode: null`, `linkType: "source_note"`, `siteName: "대표 링크"`로 반환된다. 명세 예시는 `linkCode: "LNK_001"`, `siteName: "Rakuten"`이지만, 현재 `product_links`가 0행인 상황에서 합리적인 임시 응답이다.
- `/api/regions/{regionCode}/products` 응답의 `data` 객체에는 명세와 같은 필드가 있으나, 코드상 `region` 필드는 `query_products` 결과에 나중에 추가된다. JSON 객체 순서는 API 의미상 중요하지 않으므로 문제로 보지 않았다.

---

## 8. 실제 API 테스트 결과

테스트 방식:

- 서버가 실행 중인지 먼저 `/api/health`로 확인했다.
- 실행 중이 아니어서 `uvicorn app.main:app --host 127.0.0.1 --port 8000`로 임시 실행했다.
- 테스트 완료 후 임시 서버를 종료했다.
- 한글 검색어는 `curl -G --data-urlencode` 방식으로 호출해 URL 인코딩 문제를 피했다.

| 요청 URL | HTTP status | JSON 파싱 | 통과/실패 | 주요 확인 |
| --- | ---: | --- | --- | --- |
| /api/health | 200 | 성공 | 통과 | `status=OK`, `message` 반환 |
| /api/products?page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 1525 |
| /api/products/PRD_001 | 200 | 성공 | 통과 | 상세 필드 포함 |
| /api/products/NO_SUCH_PRODUCT | 404 | 성공 | 통과 | PRODUCT_NOT_FOUND |
| /api/regions | 200 | 성공 | 통과 | data 32개 |
| /api/regions/REG_001 | 200 | 성공 | 통과 | 지역 상세 + keywords |
| /api/regions/NO_SUCH_REGION | 404 | 성공 | 통과 | REGION_NOT_FOUND |
| /api/regions/REG_001/products?page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 65 |
| /api/products?regionCode=REG_001&page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 65 |
| /api/products?targetCode=TGT_001&page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 788 |
| /api/products?keywordCode=KEY_001&page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 483 |
| /api/products?ageGroupCode=AGE_003&page=1&limit=20 | 200 | 성공 | 통과 | items 20, totalCount 1172 |
| /api/products?sort=price_asc&page=1&limit=20 | 200 | 성공 | 통과 | 가격 오름차순 응답 |
| /api/products?sort=popular&page=1&limit=20 | 200 | 성공 | 부분 통과 | 오류 없음, 단 실제 인기순 아님 |
| /api/products?priceRangeCode=INVALID | 400 | 성공 | 통과 | INVALID_PARAMETER |
| /api/products/search?keyword=타르트 | 200 | 성공 | 통과 | items 12, totalCount 12 |
| /api/price-ranges | 200 | 성공 | 통과 | data 6개 |
| /api/keywords | 200 | 성공 | 통과 | data 70개 |
| /api/gift-targets | 200 | 성공 | 통과 | data 8개 |
| /api/age-groups | 200 | 성공 | 통과 | data 8개 |
| /api/products/PRD_031/purchase-locations | 200 | 성공 | 통과 | data 2개 |
| /api/products/PRD_001/links | 200 | 성공 | 통과 | source_note fallback 1개 |

추가 확인:

- `/api/products?page=1&limit=20` 첫 상품: `PRD_001`
- `/api/products?sort=popular&page=1&limit=20` 첫 상품: `PRD_001`
- 기본 정렬과 `popular` 첫 페이지 상품 코드 배열이 동일했다. 코드상 fallback이 `product_code ASC`이므로 예상과 일치한다.

---

## 9. app/data 및 CSV 직접 조회 제거 여부

### 9-1. app/data 존재 여부

현재 `app` 하위 디렉터리:

```txt
app
```

- `app/data` 없음
- `app/data_backup`도 없음

### 9-2. pandas 사용 여부

`app/main.py`, `app/database.py`, `requirements.txt` 기준:

- `pandas` import 없음
- `read_csv` 없음
- `app/data/products.csv` 직접 조회 없음
- `requirements.txt`에도 pandas 없음

### 9-3. CSV 직접 조회 코드 잔존 여부

- FastAPI 앱 코드에는 CSV 직접 조회 코드가 없다.
- `import_omios_csv_to_mysql.py`에는 CSV import 스크립트 목적상 `products.csv` 문자열이 남아 있지만, 이는 FastAPI 런타임 API 조회 의존성이 아니다.

결론: FastAPI 서버의 `app/data` 및 CSV 직접 조회 의존성은 제거된 것으로 판단된다.

---

## 10. 이전 완료 보고 내용 검증

### 10-1. 보고 내용 중 사실로 확인된 항목

| 이전 보고 내용 | 검증 결과 |
| --- | --- |
| pandas/CSV 직접 조회 구조 제거 | 사실 |
| MySQL 기반 API 구현 | 사실 |
| `/api/*` 명세 기반 엔드포인트 추가 | 사실 |
| 상품/지역 404, 잘못된 파라미터 400 응답 형식 적용 | 사실 |
| SQLAlchemy `text()` + 바인딩 파라미터 방식 사용 | 사실 |
| requirements.txt 핵심 패키지 정리 | 사실 |
| app/database.py가 `.env`를 읽어 MySQL 연결 | 사실. 단 `.env` 내용은 열람/출력하지 않음 |
| DB row count 기대값과 일치 | 사실 |
| `/api/products?page=1&limit=20` totalCount 1525 | 사실 |
| `/api/products/PRD_001` 200 | 사실 |
| 없는 상품 404 | 사실 |
| `/api/regions` count 32 | 사실 |
| 필터 API 동작 | 사실 |
| `/api/products/search?keyword=타르트` 200 | 사실 |
| master data API count 일치 | 사실 |
| `/api/products/PRD_031/purchase-locations` count 2 | 사실 |
| `/api/products/PRD_001/links` source_note fallback 반환 | 사실 |
| `priceRangeCode=INVALID` 400 | 사실 |
| 없는 지역 404 | 사실 |
| `product_links` 0행 | 사실 |
| `view_count`, `link_click_count` 실제 products 테이블에 없음 | 사실 |
| `sort=popular`는 `product_code ASC` fallback | 사실 |
| `app/data` 폴더 없음 | 사실 |

### 10-2. 보고 내용 중 다른 항목

- “CSV 원본 데이터와 코드값을 수정하지 않음”은 현재 검토만으로 완전 증명할 수 없다. 현재 폴더가 Git 저장소가 아니어서 변경 이력 비교가 불가능했다. 다만 DB row count와 FK 무결성, 코드 의존성 제거 상태는 정상이다.

### 10-3. 추가로 발견된 항목

- DB 구조 문서와 실제 DB 스키마 사이에 누락/추가 컬럼 차이가 여럿 있다.
- `regions.parent_region_code`는 문서 비고에서 제거되었다고 되어 있으나 실제 DB에는 컬럼과 self-FK가 남아 있다.
- 문서상 여러 테이블에 `created_at`, `updated_at`이 있으나 실제 DB에는 없는 경우가 많다.
- 모든 `products.source_note` 1525개가 현재 URL 형태다. 따라서 현재 데이터에서는 links fallback이 모든 상품에 대해 대표 링크를 만들 수 있다.

---

## 11. 즉시 수정이 필요한 문제

즉시 수정 필요 항목 개수: 1

### 1) `sort=popular`가 실제 인기순이 아님

- 문서와 API 명세의 `sort=popular`는 인기순 정렬을 기대한다.
- DB 구조 문서에는 이를 위해 `view_count`, `link_click_count` 컬럼을 유지한다고 되어 있다.
- 실제 DB에는 두 컬럼이 없고, API 코드는 `popular`를 `product_code ASC`로 fallback한다.
- 현재 상태는 API 오류 방지에는 적절하지만, “인기순” 기능으로 시연하면 오해가 생길 수 있다.

권장 수정안:

- 시연/FE 연동에서 `popular` 의미가 필요하다면 `products.view_count`, `products.link_click_count`를 스키마에 추가하고 API 정렬을 문서대로 구현한다.
- 당장 통계 데이터가 없다면 API 문서/프론트 표시에서 `popular`를 임시 정렬 또는 기본 정렬로 명확히 표시한다.

---

## 12. 나중에 개선해도 되는 문제

MVP 이후 개선 가능 항목:

1. DB 구조 문서와 실제 SQL 스키마 동기화
   - 타입 길이 차이
   - `note`, `collector`, `collected_date` 등 실제 컬럼 문서화
   - `created_at`, `updated_at`, `is_active` 누락 여부 정리

2. `regions.parent_region_code` 정책 결정
   - 문서대로 제거할지, 실제 DB처럼 유지할지 결정 필요

3. `product_links` 정식 데이터 적재
   - 현재는 0행이며 `products.source_note` fallback에 의존
   - 다중 링크 기능이 필요하면 `product_links` import를 별도 구현해야 함

4. API 응답 세부 정렬/필드 순서 정리
   - 기능상 문제는 아니지만 프론트 문서와 더 엄격히 맞추려면 response schema를 Pydantic 모델로 고정 가능

5. 테스트 자동화
   - 현재는 curl 기반 수동/스크립트 검증
   - `httpx` 또는 별도 테스트 클라이언트를 dev dependency로 두고 pytest 기반 API 테스트를 구성하면 안정적

---

## 13. 최종 판단

### 해당 DB가 기준 문서 구조를 따르고 있는가?

부분적으로 따른다.

- 테이블 구성, 코드 기반 PK, FK, 다대다 연결 구조, import row count, 참조 무결성은 기준 문서의 핵심 설계를 따른다.
- 그러나 컬럼 수준에서는 문서와 실제 DB 차이가 있다. 특히 `view_count`, `link_click_count`, 일부 `created_at/updated_at`, `is_active`, `regions.parent_region_code` 정책 차이가 존재한다.

### API가 명세서를 따르고 있는가?

대체로 따른다.

- 명세서에 있는 API는 모두 구현되어 있고 실제 호출도 성공했다.
- 성공/에러 응답 구조도 대부분 명세와 맞다.
- 단, `sort=popular`는 명세 의미와 달리 현재 기본 정렬 fallback이다.
- `product_links`가 비어 있어 링크 응답은 `source_note` fallback 형태이며, 이 점은 현재 데이터 상태를 고려하면 적절하다.

### 현재 상태로 백엔드 개발을 계속 진행해도 되는가?

가능하다.

- MVP 개발을 계속 진행하기에는 충분히 안정적이다.
- 다만 인기순 정렬을 실제 기능으로 보여줄 예정이면 `view_count/link_click_count` 문제를 우선 정리해야 한다.
- DB 문서와 실제 SQL 스키마의 차이는 추후 혼선을 막기 위해 빠르게 문서 또는 스키마 중 하나로 단일화하는 것을 권장한다.
