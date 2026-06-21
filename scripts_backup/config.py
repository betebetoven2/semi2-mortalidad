import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# PostgreSQL local
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "law",
    "user": "betebetoven",
    "password": "betebetoven",
}

# Databricks
DATABRICKS_HOST      = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN     = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")

# Email
SMTP_HOST       = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER       = os.getenv("SMTP_USER")
SMTP_PASS       = os.getenv("SMTP_PASS")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Mortalidad GTM - Backup DW")
EMAIL_TO        = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]

# NAS
NAS_BACKUP_PATH = os.getenv("NAS_BACKUP_PATH", "/mnt/extra/cys/cys_u/semi2/backup_dw")

# Tablas del DW (Databricks, catálogo workspace)
TABLAS_DW = [
    "workspace.dw.fact_defunciones",
    "workspace.dw.dim_tiempo",
    "workspace.dw.dim_geografia",
    "workspace.dw.dim_causa_cie10",
    "workspace.dw.dim_sexo",
    "workspace.dw.dim_grupo_etario",
    "workspace.dw.dim_pueblo",
    "workspace.dw.dim_lugar",
]
TABLAS_BRONZE = [
    "workspace.bronze.xlsx_ine",
    "workspace.bronze.sav_ine_legacy",
    "workspace.bronze.json_oms",
    "workspace.bronze.json_worldbank",
    "workspace.bronze.gdrive_docs",
]

TABLAS_STAGE = [
    "workspace.stage.defunciones"
]

TABLAS_TODAS = TABLAS_BRONZE + TABLAS_STAGE + TABLAS_DW