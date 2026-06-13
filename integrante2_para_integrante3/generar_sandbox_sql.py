"""
Plataforma Analítica de Mortalidad End-to-End — Fase 1

Lee todos los archivos del bucket S3 y genera un archivo .sql completo
con la estructura del Sandbox (DDL) y todos los datos utilizando 
el comando ultra-rápido COPY FROM STDIN de PostgreSQL.

El .sql resultante es autocontenido: puede ejecutarse en cualquier
máquina con psql sin necesitar Python ni acceso a AWS.

Uso:
    python generar_sandbox_sql.py
    python generar_sandbox_sql.py --output mi_archivo.sql
    python generar_sandbox_sql.py --bucket otro-bucket --output salida.sql

Requisitos:
    pip install boto3 pandas pyarrow openpyxl pyreadstat

Credenciales AWS:
    Configuradas previamente con: aws configure
    O mediante variables de entorno: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
"""

import argparse
import boto3
import io
import json
import pandas as pd
from datetime import datetime
from botocore.config import Config

# ------------------------------------------------------------------------------
# Argumentos
# ------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Genera sandbox_setup.sql con DDL + datos via COPY")
parser.add_argument("--output", default="sandbox_setup.sql",
                    help="Archivo SQL de salida (default: sandbox_setup.sql)")
parser.add_argument("--bucket", default="mortalidad-gtm-2026",
                    help="Nombre del bucket S3 (default: mortalidad-gtm-2026)")
args = parser.parse_args()

BUCKET = args.bucket
OUTPUT = args.output

# ------------------------------------------------------------------------------
# Cliente S3 con manejo de timeouts y reintentos
# ------------------------------------------------------------------------------
configuracion_s3 = Config(
    read_timeout=120,
    connect_timeout=120,
    retries={"max_attempts": 3}
)
s3 = boto3.client("s3", config=configuracion_s3)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def escribir_copy_stdin(f, df, schema_tabla, fuente_archivo):
    """
    Escribe el DataFrame en el archivo SQL usando COPY FROM STDIN.
    Esto inyecta los datos en formato CSV directamente dentro del script SQL.
    """
    if df.empty:
        return

    df = df.copy()
    df.insert(0, "fuente_archivo", fuente_archivo)
    df.insert(1, "fecha_carga", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    columnas = ", ".join(df.columns.tolist())
    
    # Se declara el inicio del bloque COPY
    f.write(f"COPY {schema_tabla} ({columnas}) FROM STDIN WITH (FORMAT csv, NULL 'NULL');\n")
    
    # Se convierte el DataFrame a formato CSV y se escribe en el archivo
    # pandas maneja automaticamente el escapado de comillas y comas internas
    csv_data = df.to_csv(index=False, header=False, na_rep='NULL')
    f.write(csv_data)
    
    # Se declara el fin del bloque COPY
    f.write("\\.\n\n")

def leer_objeto(key):
    return s3.get_object(Bucket=BUCKET, Key=key)

def leer_parquet(key):
    obj = leer_objeto(key)
    buf = io.BytesIO(obj["Body"].read())
    return pd.read_parquet(buf)

def leer_xlsx(key):
    obj = leer_objeto(key)
    buf = io.BytesIO(obj["Body"].read())
    return pd.read_excel(buf)

def leer_json_wb(key):
    obj = leer_objeto(key)
    raw = json.loads(obj["Body"].read().decode("utf-8"))
    if isinstance(raw, list) and len(raw) == 2 and isinstance(raw[1], list):
        return pd.json_normalize(raw[1])
    return pd.json_normalize(raw if isinstance(raw, list) else [raw])

def leer_json_oms(key):
    obj = leer_objeto(key)
    raw = json.loads(obj["Body"].read().decode("utf-8"))
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, list) and len(v) > 0:
                return pd.json_normalize(v)
    if isinstance(raw, list):
        return pd.json_normalize(raw)
    return pd.DataFrame()

def normalizar_ine(df, key):
    rename = {
        "Depreg": "depreg", "Mupreg": "mupreg",
        "Mesreg": "mesreg", "Añoreg": "anoreg", "Anoreg": "anoreg",
        "Depocu": "depocu", "Mupocu": "mupocu",
        "Areag":  "areag",
        "Sexo":   "sexo",
        "Diaocu": "diaocu", "Mesocu": "mesocu",
        "Añoocu": "anoocu", "Anoocu": "anoocu",
        "Edadif": "edadif", "Perdif": "perdif",  "Puedif": "puedif",
        "Ecidif": "ecidif", "Escodif": "escodif", "Ciuodif": "ciuodif",
        "Pnadif": "pnadif", "Dnadif": "dnadif",  "Mnadif": "mnadif",
        "Nacdif": "nacdif", "Predif": "predif",  "Dredif": "dredif",
        "Mredif": "mredif", "Caudef": "caudef",
        "Asist":  "asist",  "Ocur":   "ocur",    "Cerdef": "cerdef",
    }
    df = df.rename(columns=rename)

    todas = [
        "depreg","mupreg","mesreg","anoreg",
        "depocu","mupocu","diaocu","mesocu","anoocu",
        "areag","sexo",
        "edadif","perdif","puedif","ecidif","escodif","ciuodif",
        "pnadif","dnadif","mnadif","nacdif","predif","dredif","mredif",
        "caudef","asist","ocur","cerdef",
    ]
    for col in todas:
        if col not in df.columns:
            df[col] = None

    return df[todas]

def normalizar_oms(df):
    rename = {
        "Id":                 "id_oms",
        "IndicatorCode":      "indicator_code",
        "SpatialDimType":     "spatial_dim_type",
        "SpatialDim":         "spatial_dim",
        "ParentLocationCode": "parent_location_code",
        "ParentLocation":     "parent_location",
        "TimeDimType":        "time_dim_type",
        "TimeDim":            "time_dim",
        "Dim1Type":           "dim1_type",
        "Dim1":               "dim1",
        "Dim2Type":           "dim2_type",
        "Dim2":               "dim2",
        "Value":              "value_text",
        "NumericValue":       "numeric_value",
        "Low":                "low_value",
        "High":               "high_value",
        "Date":               "date_registro",
        "TimeDimensionValue": "time_dimension_value",
        "TimeDimensionBegin": "time_dimension_begin",
        "TimeDimensionEnd":   "time_dimension_end",
    }
    df = df.rename(columns=rename)
    columnas = [
        "id_oms","indicator_code",
        "spatial_dim_type","spatial_dim","parent_location_code","parent_location",
        "time_dim_type","time_dim",
        "dim1_type","dim1","dim2_type","dim2",
        "value_text","numeric_value","low_value","high_value",
        "date_registro","time_dimension_value","time_dimension_begin","time_dimension_end",
    ]
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    return df[columnas]

def normalizar_wb(df):
    rename = {
        "indicator.id":    "indicator_id",
        "indicator.value": "indicator_value",
        "country.id":      "country_id",
        "country.value":   "country_value",
        "countryiso3code": "countryiso3code",
        "date":            "date_year",
        "value":           "value",
        "unit":            "unit",
        "obs_status":      "obs_status",
        "decimal":         "decimal_places",
    }
    df = df.rename(columns=rename)
    columnas = [
        "indicator_id","indicator_value",
        "country_id","country_value","countryiso3code",
        "date_year","value","unit","obs_status","decimal_places",
    ]
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    return df[columnas]

def normalizar_diccionario(df):
    rename = {
        "Valores de las variables defunciones": "variable",
        "Unnamed: 1": "codigo",
        "Unnamed: 2": "etiqueta",
    }
    df = df.rename(columns=rename)
    columnas = ["variable", "codigo", "etiqueta"]
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    return df[columnas]

# ------------------------------------------------------------------------------
# DDL
# ------------------------------------------------------------------------------

DDL = f"""\
-- =============================================================================
-- sandbox_setup.sql
-- Plataforma Analítica de Mortalidad End-to-End
-- Fase 1 — Sandbox: estructura + datos
--
-- Generado por : generar_sandbox_sql.py (Versión Optimizada con COPY STDIN)
-- Fecha        : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
-- Bucket S3    : {BUCKET}
--
-- Prerequisito : la base de datos ya debe existir.
-- Ejecución    : psql -U usuario -d nombre_db -f {OUTPUT}
-- =============================================================================

DROP TABLE IF EXISTS sandbox.sandbox_ine_defunciones        CASCADE;
DROP TABLE IF EXISTS sandbox.sandbox_oms_indicadores        CASCADE;
DROP TABLE IF EXISTS sandbox.sandbox_worldbank_indicadores  CASCADE;
DROP TABLE IF EXISTS sandbox.sandbox_gdrive_diccionario     CASCADE;
DROP TABLE IF EXISTS sandbox.sandbox_log_carga              CASCADE;

CREATE SCHEMA IF NOT EXISTS sandbox;
SET search_path TO sandbox, public;

CREATE TABLE IF NOT EXISTS sandbox.sandbox_ine_defunciones (
    id_sandbox      SERIAL         PRIMARY KEY,
    fuente_archivo  VARCHAR(100)   NOT NULL,
    fecha_carga     TIMESTAMP      NOT NULL DEFAULT NOW(),
    depreg          NUMERIC(4,0),
    mupreg          VARCHAR(10),
    mesreg          NUMERIC(2,0),
    anoreg          NUMERIC(4,0),
    depocu          NUMERIC(4,0),
    mupocu          VARCHAR(10),
    diaocu          NUMERIC(2,0),
    mesocu          NUMERIC(2,0),
    anoocu          NUMERIC(4,0),
    areag           NUMERIC(1,0),
    sexo            NUMERIC(1,0),
    edadif          NUMERIC(3,0),
    perdif          NUMERIC(1,0),
    puedif          NUMERIC(4,0),
    ecidif          NUMERIC(1,0),
    escodif         NUMERIC(2,0),
    ciuodif         VARCHAR(10),
    pnadif          NUMERIC(4,0),
    dnadif          NUMERIC(4,0),
    mnadif          VARCHAR(10),
    nacdif          NUMERIC(4,0),
    predif          NUMERIC(4,0),
    dredif          NUMERIC(4,0),
    mredif          VARCHAR(10),
    caudef          VARCHAR(10),
    asist           NUMERIC(1,0),
    ocur            NUMERIC(1,0),
    cerdef          NUMERIC(1,0)
);

CREATE TABLE IF NOT EXISTS sandbox.sandbox_oms_indicadores (
    id_sandbox              SERIAL        PRIMARY KEY,
    fuente_archivo          VARCHAR(100)  NOT NULL,
    fecha_carga             TIMESTAMP     NOT NULL DEFAULT NOW(),
    id_oms                  BIGINT,
    indicator_code          VARCHAR(50),
    spatial_dim_type        VARCHAR(20),
    spatial_dim             VARCHAR(10),
    parent_location_code    VARCHAR(10),
    parent_location         VARCHAR(50),
    time_dim_type           VARCHAR(20),
    time_dim                INTEGER,
    dim1_type               VARCHAR(30),
    dim1                    VARCHAR(30),
    dim2_type               VARCHAR(30),
    dim2                    VARCHAR(50),
    value_text              VARCHAR(50),
    numeric_value           NUMERIC,
    low_value               NUMERIC,
    high_value              NUMERIC,
    date_registro           VARCHAR(50),
    time_dimension_value    VARCHAR(10),
    time_dimension_begin    VARCHAR(50),
    time_dimension_end      VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS sandbox.sandbox_worldbank_indicadores (
    id_sandbox      SERIAL        PRIMARY KEY,
    fuente_archivo  VARCHAR(100)  NOT NULL,
    fecha_carga     TIMESTAMP     NOT NULL DEFAULT NOW(),
    indicator_id    VARCHAR(50),
    indicator_value VARCHAR(200),
    country_id      VARCHAR(5),
    country_value   VARCHAR(50),
    countryiso3code VARCHAR(5),
    date_year       VARCHAR(10),
    value           NUMERIC,
    unit            VARCHAR(20),
    obs_status      VARCHAR(10),
    decimal_places  INTEGER
);

CREATE TABLE IF NOT EXISTS sandbox.sandbox_gdrive_diccionario (
    id_sandbox      SERIAL        PRIMARY KEY,
    fuente_archivo  VARCHAR(100)  NOT NULL,
    fecha_carga     TIMESTAMP     NOT NULL DEFAULT NOW(),
    variable        VARCHAR(200),
    codigo          VARCHAR(50),
    etiqueta        VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS sandbox.sandbox_log_carga (
    id_log              SERIAL        PRIMARY KEY,
    fecha_inicio        TIMESTAMP     NOT NULL DEFAULT NOW(),
    fecha_fin           TIMESTAMP,
    fuente_archivo      VARCHAR(100)  NOT NULL,
    tabla_destino       VARCHAR(100)  NOT NULL,
    filas_insertadas    INTEGER,
    estado              VARCHAR(20),
    mensaje_error       TEXT,
    script_version      VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_ine_anoocu   ON sandbox.sandbox_ine_defunciones (anoocu);
CREATE INDEX IF NOT EXISTS idx_ine_caudef   ON sandbox.sandbox_ine_defunciones (caudef);
CREATE INDEX IF NOT EXISTS idx_ine_depocu   ON sandbox.sandbox_ine_defunciones (depocu);
CREATE INDEX IF NOT EXISTS idx_ine_fuente   ON sandbox.sandbox_ine_defunciones (fuente_archivo);
CREATE INDEX IF NOT EXISTS idx_oms_spatial  ON sandbox.sandbox_oms_indicadores (spatial_dim);
CREATE INDEX IF NOT EXISTS idx_oms_timedim  ON sandbox.sandbox_oms_indicadores (time_dim);
CREATE INDEX IF NOT EXISTS idx_oms_code     ON sandbox.sandbox_oms_indicadores (indicator_code);
CREATE INDEX IF NOT EXISTS idx_wb_country   ON sandbox.sandbox_worldbank_indicadores (countryiso3code);
CREATE INDEX IF NOT EXISTS idx_wb_year      ON sandbox.sandbox_worldbank_indicadores (date_year);

-- =============================================================================
-- SECCIÓN DE CARGA DE DATOS (COPY)
-- =============================================================================
"""

# ------------------------------------------------------------------------------
# Listar archivos en S3
# ------------------------------------------------------------------------------

log(f"Conectando al bucket: {BUCKET}")
paginator = s3.get_paginator("list_objects_v2")
keys = [
    obj["Key"]
    for page in paginator.paginate(Bucket=BUCKET)
    for obj in page.get("Contents", [])
]
log(f"{len(keys)} archivos encontrados")

# ------------------------------------------------------------------------------
# Clasificar archivos por destino (omitimos .sav)
# ------------------------------------------------------------------------------

ine_parquet = sorted([k for k in keys if k.startswith("raw/ine/") and k.endswith(".parquet")])
ine_xlsx    = sorted([k for k in keys if k.startswith("raw/ine/") and k.endswith(".xlsx")])
oms_json    = sorted([k for k in keys if k.startswith("raw/oms/")])
wb_json     = sorted([k for k in keys if k.startswith("raw/centroamerica/")])
gdrive      = sorted([k for k in keys if k.startswith("raw/gdrive/")])

log(f"INE parquet: {len(ine_parquet)} | INE xlsx: {len(ine_xlsx)} | "
    f"OMS: {len(oms_json)} | WB: {len(wb_json)} | GDrive: {len(gdrive)}")

# ------------------------------------------------------------------------------
# Escribir el SQL
# ------------------------------------------------------------------------------

errores   = []
total_ins = 0

with open(OUTPUT, "w", encoding="utf-8") as f:

    f.write(DDL)

    # -- INE parquet ----------------------------------------------------------
    f.write("\n-- INE — Defunciones (parquet 2015-2017)\n")
    for key in ine_parquet:
        log(f"Leyendo {key} ...")
        try:
            df = leer_parquet(key)
            df = normalizar_ine(df, key)
            escribir_copy_stdin(f, df, "sandbox.sandbox_ine_defunciones", key)
            total_ins += len(df)
            log(f"  -> {len(df):,} filas agregadas al archivo SQL")
        except Exception as e:
            msg = f"ERROR {key}: {e}"
            errores.append(msg)
            f.write(f"-- {msg}\n")
            log(msg)

    # -- INE xlsx -------------------------------------------------------------
    f.write("\n-- INE — Defunciones (xlsx 2018-2024)\n")
    for key in ine_xlsx:
        log(f"Leyendo {key} ...")
        try:
            df = leer_xlsx(key)
            df = normalizar_ine(df, key)
            escribir_copy_stdin(f, df, "sandbox.sandbox_ine_defunciones", key)
            total_ins += len(df)
            log(f"  -> {len(df):,} filas agregadas al archivo SQL")
        except Exception as e:
            msg = f"ERROR {key}: {e}"
            errores.append(msg)
            f.write(f"-- {msg}\n")
            log(msg)

    # -- OMS ------------------------------------------------------------------
    f.write("\n-- OMS — Indicadores de salud\n")
    for key in oms_json:
        log(f"Leyendo {key} ...")
        try:
            df = leer_json_oms(key)
            df = normalizar_oms(df)
            escribir_copy_stdin(f, df, "sandbox.sandbox_oms_indicadores", key)
            total_ins += len(df)
            log(f"  -> {len(df):,} filas agregadas al archivo SQL")
        except Exception as e:
            msg = f"ERROR {key}: {e}"
            errores.append(msg)
            f.write(f"-- {msg}\n")
            log(msg)

    # -- World Bank -----------------------------------------------------------
    f.write("\n-- Banco Mundial — Centroamérica\n")
    for key in wb_json:
        log(f"Leyendo {key} ...")
        try:
            df = leer_json_wb(key)
            df = normalizar_wb(df)
            escribir_copy_stdin(f, df, "sandbox.sandbox_worldbank_indicadores", key)
            total_ins += len(df)
            log(f"  -> {len(df):,} filas agregadas al archivo SQL")
        except Exception as e:
            msg = f"ERROR {key}: {e}"
            errores.append(msg)
            f.write(f"-- {msg}\n")
            log(msg)

    # -- Google Drive (diccionario) -------------------------------------------
    f.write("\n-- Google Drive — Diccionario INE\n")
    for key in gdrive:
        log(f"Leyendo {key} ...")
        try:
            df = leer_xlsx(key)
            df = normalizar_diccionario(df)
            escribir_copy_stdin(f, df, "sandbox.sandbox_gdrive_diccionario", key)
            total_ins += len(df)
            log(f"  -> {len(df):,} filas agregadas al archivo SQL")
        except Exception as e:
            msg = f"ERROR {key}: {e}"
            errores.append(msg)
            f.write(f"-- {msg}\n")
            log(msg)

    f.write(f"""
-- =============================================================================
-- FIN DEL SCRIPT
-- Total de filas preparadas para COPY : {total_ins:,}
-- Errores durante generación: {len(errores)}
-- =============================================================================
""")

# ------------------------------------------------------------------------------
# Resumen en consola
# ------------------------------------------------------------------------------
log("=" * 60)
log(f"Archivo SQL generado : {OUTPUT}")
log(f"Filas totales preparadas : {total_ins:,}")
log(f"Errores encontrados      : {len(errores)}")
if errores:
    for e in errores:
        log(f"  {e}")
log("=" * 60)