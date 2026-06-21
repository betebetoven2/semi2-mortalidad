## Fase 2 — Plan de Trabajo por Integrante

---

## Tu parte

### Paso 1 — EDA y perfilamiento sobre Bronze (Databricks)

Creas un notebook llamado eda_bronze_profiling en Databricks. El output de este notebook es el insumo que le pasas a Integrante 2 para que defina las reglas de Stage.

*Notebook 1 — Perfil de nulos y completitud:*
python
from pyspark.sql.functions import col, sum, when, count, round as spark_round

df = spark.table("bronze.xlsx_ine")
total = df.count()

perfil = df.select([
    spark_round(
        sum(when(col(c).isNull() | (col(c) == ""), 1)) / total * 100, 2
    ).alias(c)
    for c in df.columns
])
display(perfil)


*Notebook 2 — Outliers en edad:*
python
from pyspark.sql.functions import min, max, avg, percentile_approx, count

df = spark.table("bronze.xlsx_ine")

display(df.select(
    count("Edadif").alias("registros_con_edad"),
    min("Edadif").alias("min"),
    max("Edadif").alias("max"),
    avg("Edadif").alias("promedio"),
    percentile_approx("Edadif", 0.25).alias("p25"),
    percentile_approx("Edadif", 0.50).alias("mediana"),
    percentile_approx("Edadif", 0.75).alias("p75"),
    percentile_approx("Edadif", 0.99).alias("p99")
))

# Valores fuera de rango biológico
display(df.filter(
    (col("Edadif").cast("int") > 120) |
    (col("Edadif").cast("int") < 0)
).count())


*Notebook 3 — Validación de dominios:*
python
# Departamentos fuera de rango 1-22
df = spark.table("bronze.xlsx_ine")

print("Deptos inválidos:", df.filter(
    (col("Depocu").cast("int") < 1) |
    (col("Depocu").cast("int") > 22) |
    col("Depocu").isNull()
).count())

# Sexo fuera de dominio 1=H, 2=M, 9=Ignorado
display(df.groupBy("Sexo").count().orderBy("Sexo"))

# Años fuera de 2015-2024
display(df.groupBy("Añoocu").count().orderBy("Añoocu"))

# Longitud de CIE-10 — debe ser 3-4 chars
from pyspark.sql.functions import length
display(df.groupBy(length("Caudef").alias("len_caudef")).count().orderBy("len_caudef"))


*Notebook 4 — Duplicados:*
python
from pyspark.sql.functions import count

df = spark.table("bronze.xlsx_ine")
total = df.count()
distintos = df.distinct().count()
print(f"Total: {total:,} | Distintos: {distintos:,} | Duplicados: {total - distintos:,}")


*Notebook 5 — Comparar esquema legacy vs moderno:*
python
cols_xlsx = set(spark.table("bronze.xlsx_ine").columns)
cols_sav  = set(spark.table("bronze.sav_ine_legacy").columns)

print("Solo en legacy (SAV):", cols_sav - cols_xlsx)
print("Solo en moderno (XLSX):", cols_xlsx - cols_sav)
print("Columnas en ambos:", len(cols_xlsx & cols_sav))


*Notebook 6 — Calidad CIE-10 cruzada con diccionario:*
python
# Cuántos códigos CIE-10 del INE están en el diccionario
df_ine  = spark.table("bronze.xlsx_ine").select("Caudef").distinct()
df_dict = spark.table("bronze.gdrive_docs") \
               .select(col("Unnamed:_1").alias("codigo"))

cruzados = df_ine.join(df_dict, df_ine.Caudef == df_dict.codigo, "left")
sin_match = cruzados.filter(col("codigo").isNull()).count()
print(f"Códigos CIE-10 sin descripción en diccionario: {sin_match:,}")


El output de estos 6 notebooks se lo pasas a Integrante 2 con los hallazgos concretos: cuántos nulos, qué valores están fuera de rango, cuántos duplicados, qué columnas difieren entre legacy y moderno. Con eso él define las reglas de Stage.

---

### Paso 2 — Script de backup IoT + NAS con auditoría

Este script corre en la Raspberry vía cronjob. Lee las tablas del DW en Databricks, las escribe en PostgreSQL local y en el NAS, y registra cada operación en la tabla de auditoría.

Primero agrega la tabla de backup al schema semi2:

bash
docker exec -i postgres_db psql -U betebetoven -d law << 'EOF'
CREATE TABLE IF NOT EXISTS semi2.backup_runs (
    backup_id     SERIAL PRIMARY KEY,
    tabla_origen  VARCHAR(100) NOT NULL,
    fecha_inicio  TIMESTAMP DEFAULT NOW(),
    fecha_fin     TIMESTAMP,
    estado        VARCHAR(20) CHECK (estado IN ('EN_PROGRESO','EXITOSO','FALLIDO')),
    filas         INTEGER DEFAULT 0,
    bytes_local   BIGINT DEFAULT 0,
    ruta_nas      TEXT,
    error_msg     TEXT
);
EOF


Luego crea el script scripts/sync_dw_local.py:

python
import os
import time
import psycopg2
import pandas as pd
from databricks import sql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Databricks connection
DATABRICKS_HOST  = os.getenv("DATABRICKS_HOST")   # ej: adb-xxx.azuredatabricks.net
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP  = os.getenv("DATABRICKS_HTTP_PATH")

# PostgreSQL local
DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "dbname": "law", "user": "betebetoven", "password": "betebetoven"
}

NAS_PATH = "/mnt/extra/cys/cys_u/semi2/backup_dw"

# Tablas del DW a replicar
TABLAS_DW = [
    "dw.fact_defunciones",
    "dw.dim_tiempo",
    "dw.dim_geografia",
    "dw.dim_causa_cie10",
    "dw.dim_demografico",
    "dw.dim_lugar",
]


def registrar_inicio(conn, tabla):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO semi2.backup_runs (tabla_origen, fecha_inicio, estado)
        VALUES (%s, NOW(), 'EN_PROGRESO') RETURNING backup_id
    """, (tabla,))
    backup_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return backup_id


def registrar_fin(conn, backup_id, estado, filas, bytes_local, ruta_nas, error=None):
    cur = conn.cursor()
    cur.execute("""
        UPDATE semi2.backup_runs
        SET fecha_fin=NOW(), estado=%s, filas=%s,
            bytes_local=%s, ruta_nas=%s, error_msg=%s
        WHERE backup_id=%s
    """, (estado, filas, bytes_local, ruta_nas, error, backup_id))
    conn.commit()
    cur.close()


def sync_tabla(tabla, db_conn, dbc_conn):
    backup_id = registrar_inicio(db_conn, tabla)
    schema, nombre = tabla.split(".")

    try:
        # Leer de Databricks
        with dbc_conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {tabla}")
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]

        df = pd.DataFrame(rows, columns=cols)
        filas = len(df)

        # Guardar en NAS como parquet
        os.makedirs(NAS_PATH, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_nas = f"{NAS_PATH}/{nombre}_{ts}.parquet"
        df.to_parquet(ruta_nas, index=False)
        bytes_local = os.path.getsize(ruta_nas)

        # Escribir en PostgreSQL local
        cur_pg = db_conn.cursor()
        cur_pg.execute(f"DROP TABLE IF EXISTS {schema}_local.{nombre}")
        db_conn.commit()

        cols_sql = ", ".join([f"{c} TEXT" for c in cols])
        cur_pg.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}_local.{nombre} ({cols_sql})
        """)
        db_conn.commit()

        from io import StringIO
        import csv
        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        cur_pg.copy_from(buffer, f"{schema}_local.{nombre}", sep=",")
        db_conn.commit()
        cur_pg.close()

        registrar_fin(db_conn, backup_id, "EXITOSO", filas, bytes_local, ruta_nas)
        print(f"✓ {tabla}: {filas:,} filas → {ruta_nas}")

    except Exception as e:
        registrar_fin(db_conn, backup_id, "FALLIDO", 0, 0, None, str(e))
        print(f"✗ {tabla}: {e}")


def run():
    print(f"[{datetime.now()}] Iniciando sync DW → local")

    db_conn = psycopg2.connect(**DB_CONFIG)

    # Crear schema local si no existe
    cur = db_conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS dw_local")
    db_conn.commit()
    cur.close()

    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP,
        access_token=DATABRICKS_TOKEN
    ) as dbc_conn:
        for tabla in TABLAS_DW:
            sync_tabla(tabla, db_conn, dbc_conn)

    db_conn.close()
    print(f"[{datetime.now()}] Sync completado")


if __name__ == "__main__":
    run()


Agrega al .env:

DATABRICKS_HOST=adb-XXXXXXXXX.X.azuredatabricks.net
DATABRICKS_TOKEN=dapi...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/XXXX


Instala el conector:
bash
source venv/bin/activate
pip install databricks-sql-connector


Programa el cronjob:
bash
crontab -e
# Agregar esta línea — corre cada 6 horas
0 */6 * * * /home/alber/Desktop/semi2/venv/bin/python /home/alber/Desktop/semi2/scripts/sync_dw_local.py >> /home/alber/Desktop/semi2/logs/backup_dw.log 2>&1


---

### Paso 3 — Draw.io actualizado con Fase 2

4 vistas que ahora muestran el flujo completo: Bronze → Stage → DW cloud → backup local vía Raspberry.

---

## Integrante 2

### Paso 4 — ETL Bronze → Stage (basado en hallazgos del EDA)

Notebook etl_bronze_to_stage en Databricks. Las reglas de limpieza las define con base en lo que tú le reportes del EDA.

Estructura base que siempre va independientemente del EDA:

python
from pyspark.sql.functions import col, when, trim, upper, length, lit

spark.sql("CREATE SCHEMA IF NOT EXISTS stage")

df_xlsx   = spark.table("bronze.xlsx_ine")
df_legacy = spark.table("bronze.sav_ine_legacy")

# Unificar esquema — agregar Areag con NULL a xlsx que no la tiene
df_xlsx = df_xlsx.withColumn("Areag", lit(None).cast("string"))

df_unificado = df_xlsx.unionByName(df_legacy)

df_stage = df_unificado \
    .withColumn("anio",   col("Añoocu").cast("integer")) \
    .withColumn("mes",    col("Mesocu").cast("integer")) \
    .withColumn("depto",  col("Depocu").cast("integer")) \
    .withColumn("edad",   col("Edadif").cast("integer")) \
    .withColumn("sexo",   col("Sexo").cast("integer")) \
    .withColumn("caudef", trim(upper(col("Caudef")))) \
    .filter(col("anio").between(2015, 2024)) \
    .filter(col("depto").between(1, 22)) \
    .filter(col("sexo").isin(1, 2, 9)) \
    .withColumn("caudef",
        when(length(col("caudef")) < 3, None).otherwise(col("caudef"))
    ) \
    .withColumn("periodo",
        when(col("anio") <= 2019, "PRE_COVID").otherwise("POST_COVID")
    )

df_stage.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("stage.defunciones")

print(f"stage.defunciones: {spark.table('stage.defunciones').count():,} filas")


### Paso 5 — ETL Stage → DW (modelo estrella)

Notebook etl_stage_to_dw:

python
spark.sql("CREATE SCHEMA IF NOT EXISTS dw")

# dim_tiempo
spark.sql("""
CREATE OR REPLACE TABLE dw.dim_tiempo AS
SELECT DISTINCT
    CAST(CONCAT(anio, LPAD(mes, 2, '0')) AS INT) AS id_tiempo,
    anio,
    mes,
    CEIL(mes / 3.0)                               AS trimestre,
    periodo
FROM stage.defunciones
""")

# dim_geografia
spark.sql("""
CREATE OR REPLACE TABLE dw.dim_geografia AS
SELECT DISTINCT
    CAST(CONCAT(depto, LPAD(CAST(Mupocu AS STRING), 4, '0')) AS BIGINT) AS id_geografia,
    depto   AS codigo_depto,
    Mupocu  AS codigo_muni,
    Areag   AS area
FROM stage.defunciones
WHERE depto IS NOT NULL
""")

# dim_causa_cie10
spark.sql("""
CREATE OR REPLACE TABLE dw.dim_causa_cie10 AS
SELECT DISTINCT
    caudef                              AS id_causa,
    caudef                              AS codigo_completo,
    SUBSTRING(caudef, 1, 3)             AS categoria_3chars,
    LEFT(caudef, 1)                     AS capitulo_1char
FROM stage.defunciones
WHERE caudef IS NOT NULL
""")

# dim_demografico
spark.sql("""
CREATE OR REPLACE TABLE dw.dim_demografico AS
SELECT DISTINCT
    CAST(CONCAT(
        COALESCE(sexo, 9),
        COALESCE(CASE
            WHEN edad < 1   THEN 0
            WHEN edad < 5   THEN 1
            WHEN edad < 15  THEN 2
            WHEN edad < 25  THEN 3
            WHEN edad < 45  THEN 4
            WHEN edad < 65  THEN 5
            ELSE 6
        END, 9)
    ) AS INT)                           AS id_demografico,
    sexo,
    CASE
        WHEN edad < 1   THEN '< 1 año'
        WHEN edad < 5   THEN '1-4 años'
        WHEN edad < 15  THEN '5-14 años'
        WHEN edad < 25  THEN '15-24 años'
        WHEN edad < 45  THEN '25-44 años'
        WHEN edad < 65  THEN '45-64 años'
        ELSE '65+ años'
    END                                 AS grupo_edad
FROM stage.defunciones
""")

# dim_lugar
spark.sql("""
CREATE OR REPLACE TABLE dw.dim_lugar AS
SELECT DISTINCT
    CAST(CONCAT(COALESCE(Ocur,9), COALESCE(Asist,9)) AS INT) AS id_lugar,
    Ocur    AS tipo_lugar,
    Asist   AS asistencia_medica,
    Cerdef  AS certificador
FROM stage.defunciones
""")

# fact_defunciones
spark.sql("""
CREATE OR REPLACE TABLE dw.fact_defunciones AS
SELECT
    CAST(CONCAT(anio, LPAD(mes,2,'0'))  AS INT)     AS id_tiempo,
    CAST(CONCAT(depto, LPAD(CAST(Mupocu AS STRING),4,'0')) AS BIGINT) AS id_geografia,
    caudef                                            AS id_causa,
    CAST(CONCAT(COALESCE(sexo,9), COALESCE(CASE
        WHEN edad < 1  THEN 0 WHEN edad < 5  THEN 1
        WHEN edad < 15 THEN 2 WHEN edad < 25 THEN 3
        WHEN edad < 45 THEN 4 WHEN edad < 65 THEN 5
        ELSE 6 END,9)) AS INT)                        AS id_demografico,
    CAST(CONCAT(COALESCE(Ocur,9),COALESCE(Asist,9)) AS INT) AS id_lugar,
    1                                                 AS cantidad,
    periodo
FROM stage.defunciones
WHERE caudef IS NOT NULL AND depto IS NOT NULL
""")

print("DW cargado:")
for t in ["fact_defunciones","dim_tiempo","dim_geografia","dim_causa_cie10","dim_demografico","dim_lugar"]:
    print(f"  dw.{t}: {spark.table(f'dw.{t}').count():,} filas")


### Paso 6 — ERD en DataModeler

Genera el DDL del modelo estrella y lo importa igual que en Fase 1.

---

## Integrante 3

### Paso 7 — GitHub Actions para MkDocs

Archivo .github/workflows/docs.yml:

yaml
name: Deploy MkDocs
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force


### Paso 8 — Documentación Stage y DW

Actualizar MkDocs con las reglas de limpieza que surgieron del EDA y la justificación del modelo dimensional.

---

## Checklist final Fase 2

| Entregable | Responsable |
|---|---|
| Notebooks EDA profiling Bronze | Tú |
| Script sync_dw_local.py + cronjob | Tú |
| Tabla semi2.backup_runs en auditoría | Tú |
| Draw.io 4 vistas Fase 2 | Tú |
| Notebook ETL Bronze → Stage | Integrante 2 |
| Notebook ETL Stage → DW estrella | Integrante 2 |
| ERD modelo estrella en DataModeler | Integrante 2 |
| GitHub Actions MkDocs | Integrante 3 |
| Documentación Stage + DW + reglas EDA | Integrante 3 |
| Todo versionado con git blame | Todos |

---

## Iteración de validación

Revisando contra el enunciado punto por punto:

*Sandbox → Stage → Fact-Dimensiones* — cubierto. Bronze existe de Fase 1, Stage se construye con el ETL de Integrante 2, Fact-Dim es el esquema estrella en dw.*.

*ETL/ELT Jobs, no GitHub/GitLab Runner* — cubierto. Los notebooks de Databricks son los jobs ETL. El cronjob de la Raspberry no es un Runner de CI.

*DW en la nube* — cubierto. Schema dw.* en Databricks.

*DW local / réplica* — cubierto. sync_dw_local.py replica en PostgreSQL local y NAS, con registro en semi2.backup_runs.

*Interoperabilidad nube-local demostrable* — cubierto. En la defensa abres el notebook de Databricks, muestras dw.fact_defunciones, luego abres psql en la Raspberry y muestras dw_local.fact_defunciones con los mismos datos.

*ERD Fact-Dim en DataModeler* — Integrante 2.

*Draw.io 4 vistas* — tú.

*Pipelines versionadas en GitHub con git blame* — todos.

*MkDocs con GitHub Actions* — Integrante 3.

Lo único que falta definir antes de arrancar es que corras el EDA y le pases los hallazgos a Integrante 2 para que las reglas de Stage sean específicas y justificadas. ¿Arrancamos con eso?