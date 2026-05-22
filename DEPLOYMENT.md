# OMIOS Backend Deployment Guide

This backend is a FastAPI + MySQL API for the OMIOS React frontend.

## 1. Runtime requirements

- Python 3.11+
- MySQL 8-compatible server
- Environment variables for DB connection
- Network access from the API server to MySQL

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

## 2. Required environment variables

Do not commit real secrets. Configure these in your deployment platform's environment/secret settings.

```txt
OMIOS_DB_USER
OMIOS_DB_PASSWORD
OMIOS_DB_HOST
OMIOS_DB_PORT
OMIOS_DB_NAME
```

Optional deployment variables:

```txt
OMIOS_CORS_ORIGINS
OMIOS_CORS_ALLOW_CREDENTIALS
PORT
ENV
```

### React frontend CORS

If `OMIOS_CORS_ORIGINS` is not set, the backend allows common React local dev origins:

```txt
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

For production, set exact frontend origins, comma-separated:

```txt
OMIOS_CORS_ORIGINS=https://your-react-frontend.example.com
```

Use `OMIOS_CORS_ALLOW_CREDENTIALS=true` only if the frontend uses cookies or credentialed requests.

## 3. Local run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:

```txt
http://127.0.0.1:8000/api/health
```

## 4. Production start command

Most platforms can use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

If the platform does not support shell expansion in start commands, set the port explicitly according to that platform's docs.

## 5. Database setup/import

For a new non-production database, initialize schema and import CSV data:

```bash
python import_omios_csv_to_mysql.py --data-dir ./data --schema ./omios_mysql_schema.sql --reset
```

Warning: `--reset` drops/recreates tables. Do not use it against production data unless you intentionally want a destructive reset.

Read-only row count verification:

```bash
python scripts/check_db_counts.py
```

Expected counts:

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

## 6. Smoke tests

Start the server, then run:

```bash
python scripts/smoke_test.py
```

For a deployed API:

```bash
OMIOS_API_BASE_URL=https://your-api.example.com python scripts/smoke_test.py
```

The smoke test verifies health, product list/detail, filters, search, master data, purchase locations, links, and documented error responses.

## 7. Deployment checklist

Before deploy:

- [ ] `.env` is not committed.
- [ ] MySQL is reachable from the API runtime.
- [ ] DB row counts pass with `python scripts/check_db_counts.py`.
- [ ] `OMIOS_CORS_ORIGINS` contains the React frontend production origin.
- [ ] `python scripts/smoke_test.py` passes locally.
- [ ] Start command is configured.

After deploy:

- [ ] `/api/health` returns 200.
- [ ] `/api/products?page=1&limit=20` returns `totalCount: 1525`.
- [ ] React frontend can call the API without a CORS error.
- [ ] Logs do not print DB passwords or `.env` contents.

## 8. Known MVP limitations

- `product_links` currently has 0 rows. `/api/products/{productCode}/links` uses `products.source_note` as a fallback when it looks like a URL.
- `sort=popular` currently falls back to `product_code ASC` because the live `products` table does not have `view_count` or `link_click_count` columns.
- If the demo needs real popular sorting, add those columns to the schema/import flow and update API ordering to `view_count DESC, link_click_count DESC`.
