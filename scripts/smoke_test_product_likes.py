#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

import certifi

BASE_URL = os.getenv("OMIOS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CLIENT_ID = os.getenv("OMIOS_SMOKE_CLIENT_ID", f"omios-like-smoke-{int(time.time())}")
REGION_PRODUCT_CODE = os.getenv("OMIOS_SMOKE_REGION_PRODUCT_CODE", "PRD_041")
REGION_CODE = os.getenv("OMIOS_SMOKE_REGION_CODE", "REG_001")
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def request_json(method: str, path: str) -> tuple[int, Any]:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        method=method,
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10, context=SSL_CONTEXT) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8") or "{}")
    except urllib.error.URLError as exc:
        return 0, {"error": "REQUEST_FAILED", "message": str(exc.reason)}


def assert_ok(name: str, status: int, payload: Any) -> Any:
    if status != 200 or "data" not in payload:
        raise AssertionError(f"{name}: expected HTTP 200 with data, got status={status} payload={payload}")
    print(f"PASS {name}")
    return payload["data"]


def main() -> int:
    print(f"Smoke test target: {BASE_URL}")
    print(f"Temporary clientId: {CLIENT_ID}")
    like_path = f"/api/products/{REGION_PRODUCT_CODE}/like?clientId={CLIENT_ID}"
    try:
        # Cleanup first so reruns are deterministic for the temporary client id.
        request_json("DELETE", like_path)

        initial = assert_ok("initial_status", *request_json("GET", like_path))
        if initial["liked"] is not False:
            raise AssertionError(f"initial_status: expected liked=false, got {initial}")

        liked = assert_ok("like", *request_json("POST", like_path))
        if liked["liked"] is not True:
            raise AssertionError(f"like: expected liked=true, got {liked}")

        duplicate = assert_ok("duplicate_like_idempotent", *request_json("POST", like_path))
        if duplicate["likeCount"] != liked["likeCount"]:
            raise AssertionError(f"duplicate_like_idempotent: likeCount changed {liked} -> {duplicate}")

        region = assert_ok(
            "region_likes_desc",
            *request_json("GET", f"/api/regions/{REGION_CODE}/products?sort=likes_desc&page=1&limit=3&clientId={CLIENT_ID}"),
        )
        items = region.get("items", [])
        if not items or items[0]["productCode"] != REGION_PRODUCT_CODE:
            raise AssertionError(f"region_likes_desc: expected {REGION_PRODUCT_CODE} first, got {items[:3]}")
        if any(item.get("region", {}).get("regionCode") != REGION_CODE for item in items):
            raise AssertionError(f"region_likes_desc: mixed region result {items[:3]}")

        liked_products = assert_ok("liked_products", *request_json("GET", f"/api/product-likes?clientId={CLIENT_ID}&sort=likes_desc"))
        if not any(item["productCode"] == REGION_PRODUCT_CODE for item in liked_products.get("items", [])):
            raise AssertionError(f"liked_products: missing {REGION_PRODUCT_CODE}")

        unliked = assert_ok("unlike", *request_json("DELETE", like_path))
        if unliked["liked"] is not False:
            raise AssertionError(f"unlike: expected liked=false, got {unliked}")
        return 0
    finally:
        request_json("DELETE", like_path)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
