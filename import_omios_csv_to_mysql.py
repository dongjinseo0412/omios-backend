"""
Import OMIOS CSV files into MySQL.

Usage example:
    pip install pymysql
    export OMIOS_DB_USER=root
    export OMIOS_DB_PASSWORD='your_mysql_password'
    python import_omios_csv_to_mysql.py --data-dir ./data --schema ./omios_mysql_schema.sql --reset

Expected CSV file names may be either:
    OMIOS_Data - products.csv
or:
    products.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


TABLE_FILES = {
    "regions": "regions.csv",
    "price_ranges": "price_ranges.csv",
    "gift_targets": "gift_targets.csv",
    "age_groups": "age_groups.csv",
    "keywords": "keywords.csv",
    "purchase_locations": "purchase_locations.csv",
    "products": "products.csv",
    "product_targets": "product_targets.csv",
    "product_age_groups": "product_age_groups.csv",
    "product_keywords": "product_keywords.csv",
    "product_links": "product_links.csv",
    "product_purchase_locations": "product_purchase_locations.csv",
}

IMPORT_ORDER = [
    "regions",
    "price_ranges",
    "gift_targets",
    "age_groups",
    "keywords",
    "purchase_locations",
    "products",
    "product_targets",
    "product_age_groups",
    "product_keywords",
    "product_links",
    "product_purchase_locations",
]

REQUIRED_KEYS = {
    "regions": ["region_code", "name_ko"],
    "price_ranges": ["price_range_code", "label"],
    "gift_targets": ["target_code", "name"],
    "age_groups": ["age_group_code", "name"],
    "keywords": ["keyword_code", "name"],
    "purchase_locations": ["location_code", "name"],
    "products": ["product_code", "name_ko", "primary_region_code", "price_range_code"],
    "product_targets": ["product_code", "target_code"],
    "product_age_groups": ["product_code", "age_group_code"],
    "product_keywords": ["product_code", "keyword_code"],
    "product_links": ["link_code", "product_code", "url"],
    "product_purchase_locations": ["product_code", "location_code"],
}

PRIMARY_KEYS = {
    "regions": ["region_code"],
    "price_ranges": ["price_range_code"],
    "gift_targets": ["target_code"],
    "age_groups": ["age_group_code"],
    "keywords": ["keyword_code"],
    "purchase_locations": ["location_code"],
    "products": ["product_code"],
    "product_targets": ["product_code", "target_code"],
    "product_age_groups": ["product_code", "age_group_code"],
    "product_keywords": ["product_code", "keyword_code"],
    "product_links": ["link_code"],
    "product_purchase_locations": ["product_code", "location_code"],
}

TABLE_COLUMNS = {
    "regions": ["region_code", "name_ko", "name_jp", "parent_region_code", "description", "is_active", "note"],
    "price_ranges": ["price_range_code", "label", "min_price", "max_price", "sort_order", "is_active", "note"],
    "gift_targets": ["target_code", "name", "description", "is_active", "note"],
    "age_groups": ["age_group_code", "name", "min_age", "max_age", "is_active", "note"],
    "keywords": ["keyword_code", "name", "category", "description", "is_active", "note"],
    "purchase_locations": ["location_code", "region_code", "name", "location_type", "description", "address", "website_url", "is_active", "note"],
    "products": ["product_code", "name_ko", "name_jp", "brand_name", "primary_region_code", "price_range_code", "price", "description", "purchase_tip", "is_region_limited", "image_url", "source_note", "collector", "collected_date", "note"],
    "product_targets": ["product_code", "target_code", "note"],
    "product_age_groups": ["product_code", "age_group_code", "note"],
    "product_keywords": ["product_code", "keyword_code", "note"],
    "product_links": ["link_code", "product_code", "link_type", "site_name", "url", "is_primary", "note"],
    "product_purchase_locations": ["product_code", "location_code", "availability_status", "note"],
}

FK_CHECKS = [
    ("products", "primary_region_code", "regions", "region_code"),
    ("products", "price_range_code", "price_ranges", "price_range_code"),
    ("purchase_locations", "region_code", "regions", "region_code"),
    ("product_targets", "product_code", "products", "product_code"),
    ("product_targets", "target_code", "gift_targets", "target_code"),
    ("product_age_groups", "product_code", "products", "product_code"),
    ("product_age_groups", "age_group_code", "age_groups", "age_group_code"),
    ("product_keywords", "product_code", "products", "product_code"),
    ("product_keywords", "keyword_code", "keywords", "keyword_code"),
    ("product_links", "product_code", "products", "product_code"),
    ("product_purchase_locations", "product_code", "products", "product_code"),
    ("product_purchase_locations", "location_code", "purchase_locations", "location_code"),
]

INT_COLUMNS = {"price", "min_price", "max_price", "sort_order", "min_age", "max_age"}
BOOL_COLUMNS = {"is_active", "is_region_limited", "is_primary"}
DATE_COLUMNS = {"collected_date"}


def norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def to_none(value: Any) -> Any:
    value = norm(value)
    return None if value == "" else value


def to_int(value: Any) -> int | None:
    value = norm(value)
    if value == "":
        return None
    return int(value)


def to_bool(value: Any, default: int = 1) -> int:
    value = norm(value)
    if value == "":
        return default
    if value in {"1", "true", "TRUE", "True", "Y", "y", "yes", "YES"}:
        return 1
    if value in {"0", "false", "FALSE", "False", "N", "n", "no", "NO"}:
        return 0
    raise ValueError(f"Invalid boolean value: {value}")


def to_date(value: Any) -> str | None:
    value = norm(value)
    if value == "":
        return None
    if re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    return datetime.fromisoformat(value).date().isoformat()


def find_csv(data_dir: Path, table: str) -> Path:
    plain = data_dir / TABLE_FILES[table]
    if plain.exists():
        return plain
    matches = sorted(data_dir.glob(f"* - {TABLE_FILES[table]}"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Missing CSV for {table}: expected {plain.name} or '* - {plain.name}'")


def read_table(data_dir: Path, table: str) -> list[dict[str, Any]]:
    path = find_csv(data_dir, table)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, Any]] = []
        for raw in reader:
            clean = {k: norm(v) for k, v in raw.items() if k is not None and norm(k) != ""}
            required = REQUIRED_KEYS[table]
            # Skip spreadsheet placeholder rows and blank rows.
            if not all(norm(clean.get(k)) for k in required):
                continue
            rows.append(clean)
        return rows


def load_all(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    return {table: read_table(data_dir, table) for table in TABLE_FILES}


def key_tuple(row: dict[str, Any], cols: list[str]) -> tuple[str, ...]:
    return tuple(norm(row.get(c)) for c in cols)


def validate(tables: dict[str, list[dict[str, Any]]]) -> None:
    errors: list[str] = []

    for table, pk_cols in PRIMARY_KEYS.items():
        keys = [key_tuple(row, pk_cols) for row in tables[table]]
        duplicates = [k for k, c in Counter(keys).items() if c > 1]
        if duplicates:
            sample = ", ".join(str(x) for x in duplicates[:5])
            errors.append(f"{table}: duplicate primary key(s): {sample}")

    sets = {
        table: {key_tuple(row, PRIMARY_KEYS[table])[0] for row in rows}
        for table, rows in tables.items()
        if len(PRIMARY_KEYS[table]) == 1
    }

    for table, col, ref_table, ref_col in FK_CHECKS:
        valid = sets.get(ref_table, set())
        bad = []
        for row in tables[table]:
            value = norm(row.get(col))
            if value and value not in valid:
                bad.append(value)
        if bad:
            sample = ", ".join(sorted(set(bad))[:10])
            errors.append(f"{table}.{col}: unknown reference(s) to {ref_table}.{ref_col}: {sample}")

    if errors:
        print("\nData validation failed. Fix these issues before importing:\n", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        print("\nNo rows were imported.", file=sys.stderr)
        sys.exit(1)


def convert_value(column: str, value: Any) -> Any:
    if column in INT_COLUMNS:
        return to_int(value)
    if column in BOOL_COLUMNS:
        default = 0 if column in {"is_region_limited", "is_primary"} else 1
        return to_bool(value, default=default)
    if column in DATE_COLUMNS:
        return to_date(value)
    return to_none(value)


def sql_statements(sql: str) -> Iterable[str]:
    # Good enough for this schema file because it does not contain procedures or delimiter changes.
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            yield stmt


def connect(database: str | None = None):
    import pymysql
    return pymysql.connect(
        host=os.getenv("OMIOS_DB_HOST", "localhost"),
        port=int(os.getenv("OMIOS_DB_PORT", "3306")),
        user=os.getenv("OMIOS_DB_USER", "root"),
        password=os.getenv("OMIOS_DB_PASSWORD", ""),
        database=database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.Cursor,
    )


def apply_schema(schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    conn = connect(database=None)
    try:
        with conn.cursor() as cur:
            for stmt in sql_statements(sql):
                cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def insert_table(conn, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    cols = TABLE_COLUMNS[table]
    placeholders = ", ".join(["%s"] * len(cols))
    col_sql = ", ".join(f"`{c}`" for c in cols)
    update_cols = [c for c in cols if c not in PRIMARY_KEYS[table]]
    update_sql = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in update_cols)

    sql = f"INSERT INTO `{table}` ({col_sql}) VALUES ({placeholders})"
    if update_sql:
        sql += f" ON DUPLICATE KEY UPDATE {update_sql}"

    values = [tuple(convert_value(c, row.get(c)) for c in cols) for row in rows]
    with conn.cursor() as cur:
        cur.executemany(sql, values)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=".", help="Directory containing OMIOS CSV files")
    parser.add_argument("--schema", default="omios_mysql_schema.sql", help="Path to schema SQL file")
    parser.add_argument("--db-name", default=os.getenv("OMIOS_DB_NAME", "omios"), help="MySQL database name")
    parser.add_argument("--reset", action="store_true", help="Drop/recreate OMIOS tables using the schema file before import")
    parser.add_argument("--validate-only", action="store_true", help="Only validate CSV structure and relationships, then exit")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    schema_path = Path(args.schema).resolve()

    tables = load_all(data_dir)
    validate(tables)

    if args.validate_only:
        print("Validation passed. No rows were imported.")
        return

    if args.reset:
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        apply_schema(schema_path)

    conn = connect(database=args.db_name)
    try:
        total = 0
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        for table in IMPORT_ORDER:
            inserted = insert_table(conn, table, tables[table])
            total += inserted
            print(f"{table}: {inserted} row(s) imported")
        conn.commit()
        print(f"\nDone. Total imported rows: {total}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
