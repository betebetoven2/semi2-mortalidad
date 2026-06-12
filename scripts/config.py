import os
from dotenv import load_dotenv
from pathlib import Path

# Sube un nivel para encontrar el .env (semi2/.env)
load_dotenv(Path(__file__).parent.parent / ".env")

# AWS
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET             = os.getenv("S3_BUCKET", "mortalidad-gtm-2026")

# PostgreSQL
DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "law"),
    "user":     os.getenv("POSTGRES_USER", "betebetoven"),
    "password": os.getenv("POSTGRES_PASSWORD", "betebetoven"),
}
SCHEMA = os.getenv("POSTGRES_SCHEMA", "semi2")

# Rutas
RAW_PATH = os.getenv("RAW_DATA_PATH", "/mnt/extra/cys/cys_u/semi2/raw")
