#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import certifi

BASE_URL = os.getenv("OMIOS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass
class Check:
    name: str
    path: str
    expected_status: int = 200
    expect_data: bool = True
    expected_error: str | None = None
    expected_total_count: int | None = None
    min_items: int | None = None


def parse_json(body: str) -> Any:
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


def request_json(path: str) -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10, context=SSL_CONTEXT) as response:
            body = response.read().decode("utf-8")
            return response.status, parse_json(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, parse_json(body)
    except urllib.error.URLError as exc:
        return 0, {"error": "REQUEST_FAILED", "message": str(exc.reason)}


def validate(check: Check) -> tuple[bool, str]:
    status, payload = request_json(check.path)
    if status == 0:
        return False, f"{check.name}: request failed ({payload.get('message', 'unknown error')})"

    if status != check.expected_status:
        return False, f"{check.name}: expected HTTP {check.expected_status}, got {status}"

    if check.expected_error:
        if payload.get("error") != check.expected_error:
            return False, f"{check.name}: expected error {check.expected_error}, got {payload.get('error')}"
        return True, f"{check.name}: HTTP {status} {check.expected_error}"

    if check.name == "health":
        expected = {"status": "OK", "message": "server is running"}
        if payload != expected:
            return False, f"{check.name}: expected {expected}, got {payload}"

    if check.expect_data and "data" not in payload:
        return False, f"{check.name}: missing data field"

    data = payload.get("data")
    if check.expected_total_count is not None:
        total_count = data.get("totalCount") if isinstance(data, dict) else None
        if total_count != check.expected_total_count:
            return False, f"{check.name}: expected totalCount {check.expected_total_count}, got {total_count}"

    if check.min_items is not None:
        if isinstance(data, dict):
            items = data.get("items", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []
        if len(items) < check.min_items:
            return False, f"{check.name}: expected at least {check.min_items} item(s), got {len(items)}"

    return True, f"{check.name}: HTTP {status} OK"


def main() -> int:
    keyword = urllib.parse.quote("타르트")
    checks = [
        Check("health", "/api/health", expect_data=False),
        Check("products_page", "/api/products?page=1&limit=20", expected_total_count=1525, min_items=20),
        Check("product_detail", "/api/products/PRD_001"),
        Check("missing_product", "/api/products/NO_SUCH_PRODUCT", 404, False, "PRODUCT_NOT_FOUND"),
        Check("regions", "/api/regions", min_items=32),
        Check("region_detail", "/api/regions/REG_001"),
        Check("missing_region", "/api/regions/NO_SUCH_REGION", 404, False, "REGION_NOT_FOUND"),
        Check("region_products", "/api/regions/REG_001/products?page=1&limit=20", min_items=1),
        Check("filter_region", "/api/products?regionCode=REG_001&page=1&limit=20", min_items=1),
        Check("filter_target", "/api/products?targetCode=TGT_001&page=1&limit=20", min_items=1),
        Check("filter_keyword", "/api/products?keywordCode=KEY_001&page=1&limit=20", min_items=1),
        Check("filter_age", "/api/products?ageGroupCode=AGE_003&page=1&limit=20", min_items=1),
        Check("sort_price_asc", "/api/products?sort=price_asc&page=1&limit=20", min_items=1),
        Check("sort_popular", "/api/products?sort=popular&page=1&limit=20", min_items=1),
        Check("invalid_filter", "/api/products?priceRangeCode=INVALID", 400, False, "INVALID_PARAMETER"),
        Check("search", f"/api/products/search?keyword={keyword}", min_items=1),
        Check("price_ranges", "/api/price-ranges", min_items=6),
        Check("keywords", "/api/keywords", min_items=70),
        Check("gift_targets", "/api/gift-targets", min_items=8),
        Check("age_groups", "/api/age-groups", min_items=8),
        Check("purchase_locations", "/api/products/PRD_031/purchase-locations", min_items=1),
        Check("links", "/api/products/PRD_001/links", min_items=1),
    ]

    failures = 0
    print(f"Smoke test target: {BASE_URL}")
    for check in checks:
        ok, message = validate(check)
        print(("PASS" if ok else "FAIL"), message)
        if not ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
