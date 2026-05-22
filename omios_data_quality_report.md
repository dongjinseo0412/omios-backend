# OMIOS CSV Data Quality Report

## 확인 요약

- 기준 위치: `data/` 디렉터리의 현재 CSV 파일.
- 검증 명령: `venv/bin/python import_omios_csv_to_mysql.py --data-dir ./data --schema ./omios_mysql_schema.sql --validate-only`
- 검증 결과: `Validation passed. No rows were imported.`
- 전체 필수값, 기본키 중복, 외래키 참조 검사는 통과했습니다.
- 현재 MySQL 구축 전 실제 보완이 필요한 데이터 이슈는 `PRD_1246`의 키워드 연결 누락과 일부 CSV 헤더/컬럼 정리입니다.

## CSV별 import 가능 행 수

| CSV | 원본 행 수 | import 가능 행 수 | 제외 행 수 | 비고 |
| --- | ---: | ---: | ---: | --- |
| `regions.csv` | 32 | 32 | 0 | 지역 코드 |
| `price_ranges.csv` | 6 | 6 | 0 | 가격대 코드 |
| `gift_targets.csv` | 8 | 8 | 0 | 선물 대상 코드 |
| `age_groups.csv` | 8 | 8 | 0 | 연령대 코드 |
| `keywords.csv` | 70 | 70 | 0 | 중복 기본키 없음 |
| `purchase_locations.csv` | 328 | 328 | 0 | 구매 장소 |
| `products.csv` | 1,525 | 1,525 | 0 | 상품 |
| `product_targets.csv` | 5,561 | 5,561 | 0 | 상품-대상 연결 |
| `product_age_groups.csv` | 5,522 | 5,522 | 0 | 상품-연령대 연결 |
| `product_keywords.csv` | 7,416 | 7,416 | 0 | 상품-키워드 연결 |
| `product_links.csv` | 0 | 0 | 0 | 확장용 빈 CSV |
| `product_purchase_locations.csv` | 1,294 | 1,294 | 0 | 상품-구매장소 연결 |

## MySQL import 전 확인 사항

### 1. 기본키와 외래키

- 현재 import 대상 행 기준으로 기본키 중복은 없습니다.
- `products.primary_region_code`, `products.price_range_code`, 연결 테이블의 `product_code`, `target_code`, `age_group_code`, `keyword_code`, `location_code` 참조는 모두 유효합니다.
- 따라서 현재 CSV는 schema 기준 관계 무결성 검사를 통과합니다.

### 2. `PRD_1246`의 키워드 연결 누락

`products.csv`에는 `PRD_1246` 상품이 있지만 `product_keywords.csv`에는 연결 행이 없습니다.

- 상품명: `사레도시오 모시오`
- 일본어명: `されど塩 藻塩`
- 브랜드: `사레도시오(されど塩)`
- 권장 조치: 추천/검색 품질을 위해 `product_keywords.csv`에 적절한 `keyword_code`를 1개 이상 연결합니다.

### 3. `product_links.csv` placeholder 정리

기존 `product_links.csv`는 `LNK_001` placeholder 행만 있고 `product_code`, `url` 필수값이 비어 있어 import 대상에서 제외됐습니다.

- `product_links` 테이블은 향후 상품별 다중 링크 관리를 위해 유지합니다.
- 현재 대표 링크는 `products.source_note`에 임시 저장되어 있습니다.
- CSV에는 정상 헤더만 남기고 빈 데이터 파일로 정리했습니다.

### 4. schema/import 컬럼과 CSV 헤더 불일치

현재 import 스크립트는 schema에 맞춰 누락 컬럼을 `NULL` 또는 기본값으로 처리합니다. import 자체는 통과하지만, 장기 유지보수를 위해 다음 컬럼 정리가 필요합니다.

- `product_purchase_locations.csv`: 현재 `is_active` 컬럼은 schema/import의 `availability_status`, `note`와 맞지 않아 import 시 무시됩니다.
- `products.csv`, `purchase_locations.csv`: 빈 trailing header 컬럼이 있습니다.
- 일부 기준 CSV에는 schema에 있는 `note`, `description`, `collector`, `collected_date` 등이 없어서 import 시 `NULL`로 들어갑니다.

### 5. 의존성 정리 후보

현재 코드 검색 기준으로 `pandas`와 `numpy`는 사용되지 않습니다.

- `requirements.txt`에는 남겨두되, 실제 앱/API와 CSV import만 운영한다면 제거 후보입니다.
- import 전용 최소 의존성은 `omios_import_requirements.txt`의 `pymysql`, `python-dotenv`입니다.

## 안전 정리 완료/대상

MySQL 구축 전 로컬 산출물은 데이터와 코드 품질을 흐리므로 제거 대상입니다.

- 제거 대상: `.DS_Store`, `app/__pycache__/`, `venv/`
- 보존 대상: `.env`, `.omx/`, `data/*.csv`, `omios_mysql_schema.sql`, `import_omios_csv_to_mysql.py`
- 재생성 방지: `.gitignore`에 `.DS_Store`, `__pycache__/`, `*.py[cod]`, `venv/`, `.venv/`, `.env`를 등록합니다.

## 권장 다음 단계

1. `product_keywords.csv`에 `PRD_1246`의 키워드 연결을 추가합니다.
2. `product_purchase_locations.csv`의 `is_active` 사용 여부를 결정하고, 필요하면 schema/import 컬럼명에 맞춰 `availability_status` 또는 `note`로 정리합니다.
3. 운영용 Python 환경을 새로 만들고 `requirements.txt` 또는 `omios_import_requirements.txt`로 의존성을 재설치합니다.
4. 로컬 MySQL 접속 정보가 준비된 뒤 `--reset` 옵션으로 schema 생성과 CSV import를 실행합니다.
