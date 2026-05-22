#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import engine

EXPECTED_COUNTS = {
    "regions": 32,
    "price_ranges": 6,
    "gift_targets": 8,
    "age_groups": 8,
    "keywords": 70,
    "purchase_locations": 328,
    "products": 1525,
    "product_targets": 5561,
    "product_age_groups": 5522,
    "product_keywords": 7416,
    "product_links": 0,
    "product_purchase_locations": 1294,
}


def main() -> int:
    failures = 0
    with engine.connect() as connection:
        for table, expected in EXPECTED_COUNTS.items():
            actual = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            ok = actual == expected
            print(f"{'PASS' if ok else 'FAIL'} {table}: expected={expected} actual={actual}")
            if not ok:
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
