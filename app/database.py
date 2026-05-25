import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Prefer OMIOS_* variables for explicit app configuration, but fall back to
# Railway MySQL plugin variables so a linked Railway MySQL service works without
# duplicating secrets in code.
DB_USER = os.getenv("OMIOS_DB_USER") or os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("OMIOS_DB_PASSWORD") or os.getenv("MYSQLPASSWORD", "")
DB_HOST = os.getenv("OMIOS_DB_HOST") or os.getenv("MYSQLHOST", "127.0.0.1")
DB_PORT = int(os.getenv("OMIOS_DB_PORT") or os.getenv("MYSQLPORT", "3306"))
DB_NAME = os.getenv("OMIOS_DB_NAME") or os.getenv("MYSQLDATABASE", "omios")

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)