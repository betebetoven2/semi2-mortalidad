import os
import hashlib
import boto3
import psycopg2
from datetime import datetime
from config import DB_CONFIG, SCHEMA, S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION


class ScraperAuditado:
    def __init__(self, fuente: str):
        self.fuente = fuente
        self.run_id = None
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        print(f"[{self.fuente}] Conexión a PostgreSQL y S3 OK")

    def iniciar_run(self, url: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.scraping_runs (fuente, url_origen, fecha_inicio, estado)
            VALUES (%s, %s, NOW(), 'EN_PROGRESO')
            RETURNING run_id
            """,
            (self.fuente, url),
        )
        self.run_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        print(f"[{self.fuente}] Run #{self.run_id} iniciado — {url}")
        return self.run_id

    def registrar_archivo(self, nombre: str, url: str, filepath: str, s3_key: str):
        md5 = hashlib.md5(open(filepath, "rb").read()).hexdigest()
        size = os.path.getsize(filepath)
        cur = self.conn.cursor()
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.archivos_descargados
                (run_id, nombre, url_origen, bytes, checksum_md5, s3_bucket, s3_key, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'SUBIDO')
            """,
            (self.run_id, nombre, url, size, md5, S3_BUCKET, s3_key),
        )
        self.conn.commit()
        cur.close()
        print(f"[{self.fuente}] Archivo registrado: {nombre} ({size/1024:.1f} KB) md5={md5[:8]}...")

    def finalizar_run(self, estado: str, registros: int = 0, bytes_total: int = 0, error: str = None):
        cur = self.conn.cursor()
        cur.execute(
            f"""
            UPDATE {SCHEMA}.scraping_runs
            SET fecha_fin  = NOW(),
                estado     = %s,
                registros  = %s,
                bytes      = %s,
                error_msg  = %s
            WHERE run_id = %s
            """,
            (estado, registros, bytes_total, error, self.run_id),
        )
        self.conn.commit()
        cur.close()
        print(f"[{self.fuente}] Run #{self.run_id} → {estado} | {registros} registros | {bytes_total/1024:.1f} KB")

    def subir_a_s3(self, filepath: str, s3_key: str):
        self.s3.upload_file(filepath, S3_BUCKET, s3_key)
        print(f"[{self.fuente}] Subido a s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    def cerrar(self):
        self.conn.close()
