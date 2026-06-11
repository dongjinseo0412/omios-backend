from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_cors_allow_credentials, get_cors_origins
from app.database import engine

app = FastAPI(title="OMIOS Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=get_cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
LIKE_COUNT_CACHE_TTL_SECONDS = 3600
VALID_SORTS = {"popular", "price_asc", "price_desc", "newest", "likes_desc"}
VALID_LIKED_PRODUCT_SORTS = {"liked_at_desc", "likes_desc"}

PRODUCT_LIKES_DDL = """
CREATE TABLE IF NOT EXISTS product_likes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_likes_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    UNIQUE KEY uq_product_likes_product_client (product_code, client_id),
    INDEX idx_product_likes_product (product_code),
    INDEX idx_product_likes_client (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

PRODUCT_LIKE_COUNTS_DDL = """
CREATE TABLE IF NOT EXISTS product_like_counts (
    product_code VARCHAR(20) PRIMARY KEY,
    like_count INT NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_like_counts_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_product_like_counts_count (like_count),
    INDEX idx_product_like_counts_refreshed_at (refreshed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

PRODUCT_IS_ACTIVE_COLUMN = "is_active"


def ensure_products_is_active_column() -> None:
    """Ensure product soft-hide flag exists without touching product/like rows."""
    with engine.begin() as connection:
        column_exists = connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'products'
                  AND COLUMN_NAME = :columnName
                LIMIT 1
                """
            ),
            {"columnName": PRODUCT_IS_ACTIVE_COLUMN},
        ).scalar()
        if not column_exists:
            connection.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1
                    AFTER is_region_limited
                    """
                )
            )
        index_exists = connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'products'
                  AND INDEX_NAME = 'idx_products_is_active'
                LIMIT 1
                """
            )
        ).scalar()
        if not index_exists:
            connection.execute(text("CREATE INDEX idx_products_is_active ON products (is_active)"))


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "error": "INVALID_PARAMETER" if exc.status_code == 400 else "ERROR",
            "message": str(exc.detail),
        },
    )


def success(data: Any, status_code: int = 200) -> dict[str, Any]:
    return {"statusCode": status_code, "data": data}


def invalid_parameter() -> None:
    raise HTTPException(
        status_code=400,
        detail={
            "statusCode": 400,
            "error": "INVALID_PARAMETER",
            "message": "요청 파라미터가 올바르지 않습니다.",
        },
    )


def product_not_found() -> None:
    raise HTTPException(
        status_code=404,
        detail={
            "statusCode": 404,
            "error": "PRODUCT_NOT_FOUND",
            "message": "상품을 찾을 수 없습니다.",
        },
    )


def region_not_found() -> None:
    raise HTTPException(
        status_code=404,
        detail={
            "statusCode": 404,
            "error": "REGION_NOT_FOUND",
            "message": "지역 정보를 찾을 수 없습니다.",
        },
    )


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(text(sql), params or {}).mappings().fetchone()
    return dict(row) if row else None


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def execute_write(sql: str, params: dict[str, Any] | None = None) -> None:
    with engine.begin() as connection:
        connection.execute(text(sql), params or {})


def init_like_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text(PRODUCT_LIKES_DDL))
        connection.execute(text(PRODUCT_LIKE_COUNTS_DDL))


@app.on_event("startup")
def startup() -> None:
    ensure_products_is_active_column()
    init_like_tables()


def code_exists(table: str, column: str, value: str | None) -> bool:
    if not value:
        return True
    row = fetch_one(f"SELECT 1 AS ok FROM {table} WHERE {column} = :value LIMIT 1", {"value": value})
    return row is not None


def active_product_exists(productCode: str | None) -> bool:
    if not productCode:
        return False
    row = fetch_one(
        """
        SELECT 1 AS ok
        FROM products
        WHERE product_code = :productCode
          AND is_active = 1
        LIMIT 1
        """,
        {"productCode": productCode},
    )
    return row is not None


def validate_positive_pagination(page: int, limit: int) -> None:
    if page < 1 or limit < 1 or limit > 100:
        invalid_parameter()


def normalize_client_id(client_id: str | None) -> str | None:
    if client_id is None:
        return None
    client_id = client_id.strip()
    if not client_id:
        return None
    if not CLIENT_ID_PATTERN.fullmatch(client_id):
        invalid_parameter()
    return client_id


def resolve_client_id(client_id: str | None, header_client_id: str | None = None, required: bool = False) -> str | None:
    resolved = normalize_client_id(client_id) or normalize_client_id(header_client_id)
    if required and not resolved:
        invalid_parameter()
    return resolved


def validate_product_filters(
    regionCode: str | None,
    locationCode: str | None,
    priceRangeCode: str | None,
    keywordCode: str | None,
    targetCode: str | None,
    ageGroupCode: str | None,
    sort: str | None,
) -> None:
    if sort and sort not in VALID_SORTS:
        invalid_parameter()
    checks = [
        ("regions", "region_code", regionCode),
        ("purchase_locations", "location_code", locationCode),
        ("price_ranges", "price_range_code", priceRangeCode),
        ("keywords", "keyword_code", keywordCode),
        ("gift_targets", "target_code", targetCode),
        ("age_groups", "age_group_code", ageGroupCode),
    ]
    if any(value and not code_exists(table, column, value) for table, column, value in checks):
        invalid_parameter()


def in_clause(prefix: str, values: list[str]) -> tuple[str, dict[str, str]]:
    params = {f"{prefix}_{index}": value for index, value in enumerate(values)}
    placeholders = ", ".join(f":{key}" for key in params)
    return placeholders, params


def region_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row or row.get("region_code") is None:
        return None
    return {
        "regionCode": row["region_code"],
        "nameKo": row.get("region_name_ko") or row.get("name_ko"),
        "nameJp": row.get("region_name_jp") or row.get("name_jp"),
    }


def price_range_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row or row.get("price_range_code") is None:
        return None
    return {
        "priceRangeCode": row["price_range_code"],
        "label": row.get("price_range_label") or row.get("label"),
        "minPrice": row.get("min_price"),
        "maxPrice": row.get("max_price"),
    }


def product_list_item(row: dict[str, Any], keywords: list[str] | None = None) -> dict[str, Any]:
    return {
        "productCode": row["product_code"],
        "nameKo": row["name_ko"],
        "nameJp": row.get("name_jp"),
        "brandName": row.get("brand_name"),
        "price": row.get("price"),
        "imageUrl": row.get("image_url"),
        "region": region_summary(row),
        "keywords": keywords or [],
        "likeCount": int(row.get("like_count") or 0),
        "likedByCurrentUser": bool(row.get("liked_by_current_user")),
    }


def get_keywords_by_products(product_codes: list[str]) -> dict[str, list[str]]:
    if not product_codes:
        return {}
    placeholders, params = in_clause("code", product_codes)
    rows = fetch_all(
        f"""
        SELECT pk.product_code, k.name
        FROM product_keywords pk
        JOIN keywords k ON pk.keyword_code = k.keyword_code
        WHERE pk.product_code IN ({placeholders})
        ORDER BY pk.product_code, k.keyword_code
        """,
        params,
    )
    grouped: dict[str, list[str]] = {code: [] for code in product_codes}
    for row in rows:
        grouped.setdefault(row["product_code"], []).append(row["name"])
    return grouped


def product_base_select(include_liked_status: bool = False) -> str:
    liked_status_sql = (
        """
            CASE
                WHEN :clientId IS NULL THEN 0
                WHEN EXISTS (
                    SELECT 1
                    FROM product_likes upl
                    WHERE upl.product_code = p.product_code
                      AND upl.client_id = :clientId
                ) THEN 1
                ELSE 0
            END AS liked_by_current_user
        """
        if include_liked_status
        else "0 AS liked_by_current_user"
    )
    return """
        SELECT
            p.product_code,
            p.name_ko,
            p.name_jp,
            p.brand_name,
            p.price,
            p.description,
            p.purchase_tip,
            p.image_url,
            p.is_region_limited,
            p.source_note,
            p.created_at,
            p.primary_region_code AS region_code,
            r.name_ko AS region_name_ko,
            r.name_jp AS region_name_jp,
            p.price_range_code,
            pr.label AS price_range_label,
            pr.min_price,
            pr.max_price,
            COALESCE(plc.like_count, 0) AS like_count,
            {liked_status_sql}
        FROM products p
        LEFT JOIN regions r ON p.primary_region_code = r.region_code
        LEFT JOIN price_ranges pr ON p.price_range_code = pr.price_range_code
        LEFT JOIN product_like_counts plc ON p.product_code = plc.product_code
    """.format(liked_status_sql=liked_status_sql)


def build_product_filter_sql(
    regionCode: str | None,
    locationCode: str | None,
    priceRangeCode: str | None,
    keywordCode: str | None,
    targetCode: str | None,
    ageGroupCode: str | None,
    keyword: str | None = None,
) -> tuple[str, dict[str, Any]]:
    where = ["p.is_active = 1"]
    params: dict[str, Any] = {}
    if regionCode:
        where.append("p.primary_region_code = :regionCode")
        params["regionCode"] = regionCode
    if locationCode:
        where.append(
            "EXISTS (SELECT 1 FROM product_purchase_locations fppl WHERE fppl.product_code = p.product_code AND fppl.location_code = :locationCode)"
        )
        params["locationCode"] = locationCode
    if priceRangeCode:
        where.append("p.price_range_code = :priceRangeCode")
        params["priceRangeCode"] = priceRangeCode
    if keywordCode:
        where.append(
            "EXISTS (SELECT 1 FROM product_keywords fpk WHERE fpk.product_code = p.product_code AND fpk.keyword_code = :keywordCode)"
        )
        params["keywordCode"] = keywordCode
    if targetCode:
        where.append(
            "EXISTS (SELECT 1 FROM product_targets fpt WHERE fpt.product_code = p.product_code AND fpt.target_code = :targetCode)"
        )
        params["targetCode"] = targetCode
    if ageGroupCode:
        where.append(
            "EXISTS (SELECT 1 FROM product_age_groups fag WHERE fag.product_code = p.product_code AND fag.age_group_code = :ageGroupCode)"
        )
        params["ageGroupCode"] = ageGroupCode
    if keyword:
        where.append(
            """
            (
                p.name_ko LIKE :keywordLike
                OR p.name_jp LIKE :keywordLike
                OR p.brand_name LIKE :keywordLike
                OR p.description LIKE :keywordLike
                OR EXISTS (
                    SELECT 1
                    FROM product_keywords spk
                    JOIN keywords sk ON spk.keyword_code = sk.keyword_code
                    WHERE spk.product_code = p.product_code
                      AND sk.name LIKE :keywordLike
                )
            )
            """
        )
        params["keywordLike"] = f"%{keyword}%"
    return " AND ".join(where), params


def product_order_by(sort: str | None) -> str:
    if sort == "likes_desc":
        return "COALESCE(plc.like_count, 0) DESC, p.product_code ASC"
    if sort == "price_asc":
        return "p.price IS NULL ASC, p.price ASC, p.product_code ASC"
    if sort == "price_desc":
        return "p.price IS NULL ASC, p.price DESC, p.product_code ASC"
    if sort == "newest":
        return "p.created_at DESC, p.product_code ASC"
    # Current SQL schema has no view_count/link_click_count columns, so popular safely falls back.
    return "p.product_code ASC"


def refresh_all_like_counts() -> None:
    # Lightweight backend-side 1-hour refresh strategy:
    # keep an aggregate table refreshed by API requests instead of adding a scheduler/worker.
    execute_write(
        """
        INSERT INTO product_like_counts (product_code, like_count, refreshed_at)
        SELECT p.product_code, COUNT(pl.id) AS like_count, CURRENT_TIMESTAMP AS refreshed_at
        FROM products p
        LEFT JOIN product_likes pl ON p.product_code = pl.product_code
        GROUP BY p.product_code
        ON DUPLICATE KEY UPDATE
            like_count = VALUES(like_count),
            refreshed_at = VALUES(refreshed_at)
        """
    )


def refresh_product_like_count(productCode: str) -> None:
    execute_write(
        """
        INSERT INTO product_like_counts (product_code, like_count, refreshed_at)
        SELECT p.product_code, COUNT(pl.id) AS like_count, CURRENT_TIMESTAMP AS refreshed_at
        FROM products p
        LEFT JOIN product_likes pl ON p.product_code = pl.product_code
        WHERE p.product_code = :productCode
        GROUP BY p.product_code
        ON DUPLICATE KEY UPDATE
            like_count = VALUES(like_count),
            refreshed_at = VALUES(refreshed_at)
        """,
        {"productCode": productCode},
    )


def ensure_like_counts_fresh() -> None:
    summary = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM products) AS product_count,
            COUNT(*) AS cached_count,
            COALESCE(TIMESTAMPDIFF(SECOND, MIN(refreshed_at), CURRENT_TIMESTAMP), :ttlSeconds + 1) AS oldest_age_seconds
        FROM product_like_counts
        """,
        {"ttlSeconds": LIKE_COUNT_CACHE_TTL_SECONDS},
    )
    if not summary:
        refresh_all_like_counts()
        return
    if summary["cached_count"] < summary["product_count"] or summary["oldest_age_seconds"] >= LIKE_COUNT_CACHE_TTL_SECONDS:
        refresh_all_like_counts()


def product_like_state(productCode: str, clientId: str | None = None) -> dict[str, Any]:
    refresh_product_like_count(productCode)
    row = fetch_one(
        """
        SELECT
            p.product_code,
            COALESCE(plc.like_count, 0) AS like_count,
            CASE
                WHEN :clientId IS NULL THEN 0
                WHEN EXISTS (
                    SELECT 1
                    FROM product_likes upl
                    WHERE upl.product_code = p.product_code
                      AND upl.client_id = :clientId
                ) THEN 1
                ELSE 0
            END AS liked
        FROM products p
        LEFT JOIN product_like_counts plc ON p.product_code = plc.product_code
        WHERE p.product_code = :productCode
          AND p.is_active = 1
        """,
        {"productCode": productCode, "clientId": clientId},
    )
    if not row:
        product_not_found()
    return {
        "productCode": row["product_code"],
        "liked": bool(row.get("liked")),
        "likeCount": int(row.get("like_count") or 0),
    }


def query_products(
    *,
    page: int,
    limit: int,
    sort: str | None = None,
    regionCode: str | None = None,
    locationCode: str | None = None,
    priceRangeCode: str | None = None,
    keywordCode: str | None = None,
    targetCode: str | None = None,
    ageGroupCode: str | None = None,
    keyword: str | None = None,
    clientId: str | None = None,
) -> dict[str, Any]:
    validate_positive_pagination(page, limit)
    validate_product_filters(regionCode, locationCode, priceRangeCode, keywordCode, targetCode, ageGroupCode, sort)
    ensure_like_counts_fresh()
    where_sql, params = build_product_filter_sql(
        regionCode, locationCode, priceRangeCode, keywordCode, targetCode, ageGroupCode, keyword
    )
    total = fetch_one(f"SELECT COUNT(*) AS total_count FROM products p WHERE {where_sql}", params)["total_count"]
    params = {**params, "clientId": clientId, "limit": limit, "offset": (page - 1) * limit}
    rows = fetch_all(
        f"""
        {product_base_select(include_liked_status=True)}
        WHERE {where_sql}
        ORDER BY {product_order_by(sort)}
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    product_codes = [row["product_code"] for row in rows]
    keywords_map = get_keywords_by_products(product_codes)
    return {
        "items": [product_list_item(row, keywords_map.get(row["product_code"], [])) for row in rows],
        "page": page,
        "limit": limit,
        "totalCount": total,
    }


def get_purchase_locations_data(productCode: str, require_product: bool = True) -> list[dict[str, Any]]:
    if require_product and not active_product_exists(productCode):
        product_not_found()
    rows = fetch_all(
        """
        SELECT
            pl.location_code,
            pl.name,
            pl.location_type,
            pl.description,
            pl.address,
            pl.website_url,
            pl.region_code,
            r.name_ko AS region_name_ko
        FROM product_purchase_locations ppl
        JOIN products p ON ppl.product_code = p.product_code
        JOIN purchase_locations pl ON ppl.location_code = pl.location_code
        LEFT JOIN regions r ON pl.region_code = r.region_code
        WHERE ppl.product_code = :productCode
          AND p.is_active = 1
        ORDER BY pl.location_code
        """,
        {"productCode": productCode},
    )
    return [
        {
            "locationCode": row["location_code"],
            "name": row["name"],
            "locationType": row.get("location_type"),
            "description": row.get("description"),
            "address": row.get("address"),
            "websiteUrl": row.get("website_url"),
            "region": {
                "regionCode": row.get("region_code"),
                "nameKo": row.get("region_name_ko"),
            }
            if row.get("region_code")
            else None,
        }
        for row in rows
    ]


def get_links_data(productCode: str, require_product: bool = True) -> list[dict[str, Any]]:
    product = fetch_one(
        "SELECT product_code, source_note FROM products WHERE product_code = :productCode AND is_active = 1",
        {"productCode": productCode},
    )
    if not product:
        if require_product:
            product_not_found()
        return []

    rows = fetch_all(
        """
        SELECT link_code, link_type, site_name, url, is_primary
        FROM product_links
        WHERE product_code = :productCode
        ORDER BY is_primary DESC, link_code
        """,
        {"productCode": productCode},
    )
    if rows:
        return [
            {
                "linkCode": row["link_code"],
                "linkType": row.get("link_type"),
                "siteName": row.get("site_name"),
                "url": row["url"],
                "isPrimary": bool(row.get("is_primary")),
            }
            for row in rows
        ]

    source_note = (product.get("source_note") or "").strip()
    if URL_PATTERN.match(source_note):
        return [
            {
                "linkCode": None,
                "linkType": "source_note",
                "siteName": "대표 링크",
                "url": source_note,
                "isPrimary": True,
            }
        ]
    return []


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "OMIOS backend is running"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "OK", "message": "server is running"}


@app.get("/api/regions")
def get_regions() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT region_code, name_ko, name_jp, description
        FROM regions
        WHERE is_active = 1
        ORDER BY region_code
        """
    )
    return success(
        [
            {
                "regionCode": row["region_code"],
                "nameKo": row["name_ko"],
                "nameJp": row.get("name_jp"),
                "description": row.get("description"),
            }
            for row in rows
        ]
    )


@app.get("/api/regions/{regionCode}")
def get_region(regionCode: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT region_code, name_ko, name_jp, description
        FROM regions
        WHERE region_code = :regionCode
        """,
        {"regionCode": regionCode},
    )
    if not row:
        region_not_found()
    keywords = fetch_all(
        """
        SELECT DISTINCT k.keyword_code, k.name
        FROM products p
        JOIN product_keywords pk ON p.product_code = pk.product_code
        JOIN keywords k ON pk.keyword_code = k.keyword_code
        WHERE p.primary_region_code = :regionCode
          AND p.is_active = 1
        ORDER BY k.keyword_code
        LIMIT 20
        """,
        {"regionCode": regionCode},
    )
    return success(
        {
            "regionCode": row["region_code"],
            "nameKo": row["name_ko"],
            "nameJp": row.get("name_jp"),
            "description": row.get("description"),
            "keywords": [keyword["name"] for keyword in keywords],
        }
    )


@app.get("/api/regions/{regionCode}/products")
def get_region_products(
    regionCode: str,
    page: int = Query(default=1),
    limit: int = Query(default=20),
    sort: str | None = Query(default=None),
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    validate_positive_pagination(page, limit)
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    region = fetch_one(
        "SELECT region_code, name_ko FROM regions WHERE region_code = :regionCode",
        {"regionCode": regionCode},
    )
    if not region:
        region_not_found()
    data = query_products(page=page, limit=limit, sort=sort, regionCode=regionCode, clientId=resolved_client_id)
    data["region"] = {"regionCode": region["region_code"], "nameKo": region["name_ko"]}
    return success(data)


@app.get("/api/purchase-locations/{locationCode}/products")
def get_purchase_location_products(
    locationCode: str,
    page: int = Query(default=1),
    limit: int = Query(default=20),
    sort: str | None = Query(default=None),
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    validate_positive_pagination(page, limit)
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    location = fetch_one(
        """
        SELECT pl.location_code, pl.name, pl.region_code, r.name_ko AS region_name_ko
        FROM purchase_locations pl
        LEFT JOIN regions r ON pl.region_code = r.region_code
        WHERE pl.location_code = :locationCode
        """,
        {"locationCode": locationCode},
    )
    if not location:
        invalid_parameter()
    data = query_products(page=page, limit=limit, sort=sort, locationCode=locationCode, clientId=resolved_client_id)
    data["location"] = {
        "locationCode": location["location_code"],
        "name": location["name"],
        "region": {
            "regionCode": location.get("region_code"),
            "nameKo": location.get("region_name_ko"),
        }
        if location.get("region_code")
        else None,
    }
    return success(data)


@app.get("/api/regions/{regionCode}/keywords")
def get_region_keywords(regionCode: str) -> dict[str, Any]:
    region = fetch_one(
        "SELECT region_code, name_ko FROM regions WHERE region_code = :regionCode",
        {"regionCode": regionCode},
    )
    if not region:
        region_not_found()
    rows = fetch_all(
        """
        SELECT DISTINCT k.keyword_code, k.name, k.category
        FROM products p
        JOIN product_keywords pk ON p.product_code = pk.product_code
        JOIN keywords k ON pk.keyword_code = k.keyword_code
        WHERE p.primary_region_code = :regionCode
          AND p.is_active = 1
        ORDER BY k.keyword_code
        """,
        {"regionCode": regionCode},
    )
    return success(
        {
            "regionCode": region["region_code"],
            "regionName": region["name_ko"],
            "keywords": [
                {"keywordCode": row["keyword_code"], "name": row["name"], "category": row.get("category")}
                for row in rows
            ],
        }
    )


@app.get("/api/products/search")
def search_products(
    keyword: str = Query(..., min_length=1),
    page: int = Query(default=1),
    limit: int = Query(default=20),
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    validate_positive_pagination(page, limit)
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    data = query_products(page=page, limit=limit, keyword=keyword, clientId=resolved_client_id)
    return success({"keyword": keyword, **data})


@app.get("/api/products")
def get_products(
    regionCode: str | None = Query(default=None),
    locationCode: str | None = Query(default=None),
    priceRangeCode: str | None = Query(default=None),
    keywordCode: str | None = Query(default=None),
    targetCode: str | None = Query(default=None),
    ageGroupCode: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    page: int = Query(default=1),
    limit: int = Query(default=20),
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    data = query_products(
        page=page,
        limit=limit,
        sort=sort,
        regionCode=regionCode,
        locationCode=locationCode,
        priceRangeCode=priceRangeCode,
        keywordCode=keywordCode,
        targetCode=targetCode,
        ageGroupCode=ageGroupCode,
        clientId=resolved_client_id,
    )
    filters = {
        "regionCode": regionCode,
        "locationCode": locationCode,
        "priceRangeCode": priceRangeCode,
        "keywordCode": keywordCode,
        "targetCode": targetCode,
        "ageGroupCode": ageGroupCode,
        "sort": sort,
    }
    if any(value is not None for value in filters.values()):
        data["filters"] = filters
    return success(data)


@app.post("/api/products/{productCode}/like")
def like_product(
    productCode: str,
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id, required=True)
    if not active_product_exists(productCode):
        product_not_found()
    execute_write(
        """
        INSERT IGNORE INTO product_likes (product_code, client_id)
        VALUES (:productCode, :clientId)
        """,
        {"productCode": productCode, "clientId": resolved_client_id},
    )
    return success(product_like_state(productCode, resolved_client_id))


@app.delete("/api/products/{productCode}/like")
def unlike_product(
    productCode: str,
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id, required=True)
    if not active_product_exists(productCode):
        product_not_found()
    execute_write(
        """
        DELETE FROM product_likes
        WHERE product_code = :productCode
          AND client_id = :clientId
        """,
        {"productCode": productCode, "clientId": resolved_client_id},
    )
    return success(product_like_state(productCode, resolved_client_id))


@app.post("/api/products/{productCode}/like/toggle")
def toggle_product_like(
    productCode: str,
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id, required=True)
    if not active_product_exists(productCode):
        product_not_found()
    existing = fetch_one(
        """
        SELECT 1 AS liked
        FROM product_likes
        WHERE product_code = :productCode
          AND client_id = :clientId
        LIMIT 1
        """,
        {"productCode": productCode, "clientId": resolved_client_id},
    )
    if existing:
        execute_write(
            """
            DELETE FROM product_likes
            WHERE product_code = :productCode
              AND client_id = :clientId
            """,
            {"productCode": productCode, "clientId": resolved_client_id},
        )
    else:
        execute_write(
            """
            INSERT IGNORE INTO product_likes (product_code, client_id)
            VALUES (:productCode, :clientId)
            """,
            {"productCode": productCode, "clientId": resolved_client_id},
        )
    return success(product_like_state(productCode, resolved_client_id))


@app.get("/api/products/{productCode}/like")
def get_product_like(
    productCode: str,
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    if not active_product_exists(productCode):
        product_not_found()
    return success(product_like_state(productCode, resolved_client_id))


@app.get("/api/product-likes")
def get_liked_products(
    clientId: str | None = Query(default=None),
    page: int = Query(default=1),
    limit: int = Query(default=20),
    sort: str | None = Query(default="liked_at_desc"),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    validate_positive_pagination(page, limit)
    if sort not in VALID_LIKED_PRODUCT_SORTS:
        invalid_parameter()
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id, required=True)
    ensure_like_counts_fresh()
    params = {"clientId": resolved_client_id, "limit": limit, "offset": (page - 1) * limit}
    total = fetch_one(
        """
        SELECT COUNT(*) AS total_count
        FROM product_likes user_likes
        JOIN products p ON user_likes.product_code = p.product_code
        WHERE user_likes.client_id = :clientId
          AND p.is_active = 1
        """,
        {"clientId": resolved_client_id},
    )["total_count"]
    order_by = "user_likes.created_at DESC, p.product_code ASC" if sort == "liked_at_desc" else product_order_by(sort)
    rows = fetch_all(
        f"""
        {product_base_select(include_liked_status=True)}
        JOIN product_likes user_likes
          ON user_likes.product_code = p.product_code
         AND user_likes.client_id = :clientId
        WHERE p.is_active = 1
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    product_codes = [row["product_code"] for row in rows]
    keywords_map = get_keywords_by_products(product_codes)
    return success(
        {
            "items": [product_list_item(row, keywords_map.get(row["product_code"], [])) for row in rows],
            "page": page,
            "limit": limit,
            "totalCount": total,
            "sort": sort,
        }
    )


@app.get("/api/products/{productCode}")
def get_product(
    productCode: str,
    clientId: str | None = Query(default=None),
    x_omios_client_id: str | None = Header(default=None, alias="X-OMIOS-Client-Id"),
) -> dict[str, Any]:
    resolved_client_id = resolve_client_id(clientId, x_omios_client_id)
    ensure_like_counts_fresh()
    row = fetch_one(
        f"{product_base_select(include_liked_status=True)} WHERE p.product_code = :productCode AND p.is_active = 1",
        {"productCode": productCode, "clientId": resolved_client_id},
    )
    if not row:
        product_not_found()

    keywords = fetch_all(
        """
        SELECT k.keyword_code, k.name, k.category
        FROM product_keywords pk
        JOIN keywords k ON pk.keyword_code = k.keyword_code
        WHERE pk.product_code = :productCode
        ORDER BY k.keyword_code
        """,
        {"productCode": productCode},
    )
    targets = fetch_all(
        """
        SELECT gt.target_code, gt.name
        FROM product_targets pt
        JOIN gift_targets gt ON pt.target_code = gt.target_code
        WHERE pt.product_code = :productCode
        ORDER BY gt.target_code
        """,
        {"productCode": productCode},
    )
    age_groups = fetch_all(
        """
        SELECT ag.age_group_code, ag.name, ag.min_age, ag.max_age
        FROM product_age_groups pag
        JOIN age_groups ag ON pag.age_group_code = ag.age_group_code
        WHERE pag.product_code = :productCode
        ORDER BY ag.age_group_code
        """,
        {"productCode": productCode},
    )

    return success(
        {
            "productCode": row["product_code"],
            "nameKo": row["name_ko"],
            "nameJp": row.get("name_jp"),
            "brandName": row.get("brand_name"),
            "price": row.get("price"),
            "description": row.get("description"),
            "purchaseTip": row.get("purchase_tip"),
            "imageUrl": row.get("image_url"),
            "isRegionLimited": bool(row.get("is_region_limited")),
            "region": region_summary(row),
            "priceRange": price_range_summary(row),
            "likeCount": int(row.get("like_count") or 0),
            "likedByCurrentUser": bool(row.get("liked_by_current_user")),
            "keywords": [
                {"keywordCode": item["keyword_code"], "name": item["name"], "category": item.get("category")}
                for item in keywords
            ],
            "targets": [{"targetCode": item["target_code"], "name": item["name"]} for item in targets],
            "ageGroups": [
                {
                    "ageGroupCode": item["age_group_code"],
                    "name": item["name"],
                    "minAge": item.get("min_age"),
                    "maxAge": item.get("max_age"),
                }
                for item in age_groups
            ],
            "purchaseLocations": get_purchase_locations_data(productCode, require_product=False),
            "links": get_links_data(productCode, require_product=False),
        }
    )


@app.get("/api/price-ranges")
def get_price_ranges() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT price_range_code, label, min_price, max_price, sort_order
        FROM price_ranges
        WHERE is_active = 1
        ORDER BY sort_order, price_range_code
        """
    )
    return success(
        [
            {
                "priceRangeCode": row["price_range_code"],
                "label": row["label"],
                "minPrice": row.get("min_price"),
                "maxPrice": row.get("max_price"),
                "sortOrder": row.get("sort_order"),
            }
            for row in rows
        ]
    )


@app.get("/api/keywords")
def get_keywords() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT keyword_code, name, category
        FROM keywords
        WHERE is_active = 1
        ORDER BY keyword_code
        """
    )
    return success(
        [
            {"keywordCode": row["keyword_code"], "name": row["name"], "category": row.get("category")}
            for row in rows
        ]
    )


@app.get("/api/gift-targets")
def get_gift_targets() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT target_code, name
        FROM gift_targets
        WHERE is_active = 1
        ORDER BY target_code
        """
    )
    return success([{"targetCode": row["target_code"], "name": row["name"]} for row in rows])


@app.get("/api/age-groups")
def get_age_groups() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT age_group_code, name, min_age, max_age
        FROM age_groups
        WHERE is_active = 1
        ORDER BY age_group_code
        """
    )
    return success(
        [
            {
                "ageGroupCode": row["age_group_code"],
                "name": row["name"],
                "minAge": row.get("min_age"),
                "maxAge": row.get("max_age"),
            }
            for row in rows
        ]
    )


@app.get("/api/products/{productCode}/purchase-locations")
def get_product_purchase_locations(productCode: str) -> dict[str, Any]:
    return success(get_purchase_locations_data(productCode))


@app.get("/api/products/{productCode}/links")
def get_product_links(productCode: str) -> dict[str, Any]:
    return success(get_links_data(productCode))
