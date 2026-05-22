import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_USER = os.getenv("OMIOS_DB_USER", "root")
DB_PASSWORD = os.getenv("OMIOS_DB_PASSWORD", "")
DB_HOST = os.getenv("OMIOS_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("OMIOS_DB_PORT", "3306"))
DB_NAME = os.getenv("OMIOS_DB_NAME", "omios")

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