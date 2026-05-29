# OMIOS Product Likes API

상품 찜/좋아요 기능은 현재 인증 기능이 없는 백엔드 구조를 고려해 `clientId` 기반으로 동작한다. 프론트엔드는 브라우저별 UUID 등을 생성해 `clientId` query parameter 또는 `X-OMIOS-Client-Id` header로 전달하면 된다.

## 사용자 식별자

- Query: `clientId=browser-or-session-uuid`
- Header: `X-OMIOS-Client-Id: browser-or-session-uuid`
- 허용 문자: 영문/숫자/`.`/`_`/`:`/`-`
- 최대 길이: 100자

## 상품 찜 추가

```http
POST /api/products/PRD_041/like?clientId=omios-client-uuid
```

이미 찜한 상품이어도 에러가 아니라 성공으로 응답한다.

```json
{
  "statusCode": 200,
  "data": {
    "productCode": "PRD_041",
    "liked": true,
    "likeCount": 1
  }
}
```

## 상품 찜 취소

```http
DELETE /api/products/PRD_041/like?clientId=omios-client-uuid
```

이미 취소된 상태여도 에러가 아니라 성공으로 응답한다.

```json
{
  "statusCode": 200,
  "data": {
    "productCode": "PRD_041",
    "liked": false,
    "likeCount": 0
  }
}
```

## 상품 찜 토글

```http
POST /api/products/PRD_041/like/toggle?clientId=omios-client-uuid
```

현재 사용자의 찜 상태를 반대로 변경한다.

## 상품 찜 상태/수 조회

```http
GET /api/products/PRD_041/like?clientId=omios-client-uuid
```

`clientId`를 생략하면 전체 찜 수만 확인할 수 있고 `liked`는 `false`로 반환된다.

## 특정 사용자가 찜한 상품 목록

```http
GET /api/product-likes?clientId=omios-client-uuid&page=1&limit=20&sort=likes_desc
```

- `sort=liked_at_desc` 기본값: 최근 찜한 순
- `sort=likes_desc`: 전체 찜 수 내림차순, 같은 찜 수는 `productCode` 오름차순


## Error cases

기존 백엔드 에러 응답 형식과 동일하게 `statusCode`, `error`, `message`를 반환한다.

### clientId 누락 또는 형식 오류

`POST`, `DELETE`, `toggle`, `GET /api/product-likes`는 사용자 식별이 필요하므로 `clientId` query 또는 `X-OMIOS-Client-Id` header가 없거나 허용 문자/길이를 벗어나면 `400 INVALID_PARAMETER`를 반환한다.

```json
{
  "statusCode": 400,
  "error": "INVALID_PARAMETER",
  "message": "요청 파라미터가 올바르지 않습니다."
}
```

### 존재하지 않는 상품

```json
{
  "statusCode": 404,
  "error": "PRODUCT_NOT_FOUND",
  "message": "상품을 찾을 수 없습니다."
}
```

### 잘못된 정렬값 또는 필터값

`sort=likes_desc` 외에 허용되지 않은 정렬값, 존재하지 않는 지역/구매처/필터 코드가 들어오면 `400 INVALID_PARAMETER`를 반환한다.

## 상품 목록 응답 확장

아래 상품 목록 API의 각 item에 `likeCount`, `likedByCurrentUser`가 추가된다.

- `GET /api/products`
- `GET /api/products/search`
- `GET /api/regions/{regionCode}/products`
- `GET /api/purchase-locations/{locationCode}/products`

예시:

```http
GET /api/regions/REG_001/products?sort=likes_desc&page=1&limit=20&clientId=omios-client-uuid
```

```json
{
  "statusCode": 200,
  "data": {
    "region": { "regionCode": "REG_001", "nameKo": "도쿠시마" },
    "items": [
      {
        "productCode": "PRD_041",
        "nameKo": "나루토 킨토키 타르트",
        "region": { "regionCode": "REG_001", "nameKo": "도쿠시마", "nameJp": "徳島" },
        "keywords": ["단맛", "빵/케이크"],
        "likeCount": 12,
        "likedByCurrentUser": true
      }
    ],
    "page": 1,
    "limit": 20,
    "totalCount": 65
  }
}
```

## 지역/구매처 내부 찜 수 정렬

- `sort=likes_desc`를 전달하면 `likeCount DESC, product_code ASC` 순서로 정렬한다.
- 지역 상품 목록은 기존 `p.primary_region_code = :regionCode` 필터 이후 정렬하므로 다른 지역 상품이 섞이지 않는다.
- 구매처 상품 목록은 `product_purchase_locations.location_code = :locationCode` 필터 이후 정렬한다.

## 1시간 단위 집계 갱신

별도 워커/Celery 의존성을 추가하지 않고 다음 테이블을 사용한다.

- `product_likes`: 원본 찜 이벤트 저장
- `product_like_counts`: 상품별 찜 수 집계 캐시

API 요청 시 `product_like_counts`가 비어 있거나 가장 오래된 `refreshed_at`이 3600초 이상 지났으면 전체 집계를 갱신한다. 찜 추가/취소 요청 직후에는 해당 상품의 집계를 즉시 갱신해 응답의 `likeCount`가 최신 상태가 되도록 했다.
