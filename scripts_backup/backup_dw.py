import os
import io
import csv
import socket
import argparse
import psycopg2
import pandas as pd
from datetime import datetime

import config
from email_service import EmailNotifier


def hay_internet(host="8.8.8.8", port=53, timeout=3, intentos=3) -> bool:
    """
    Verifica conectividad real intentando un handshake TCP contra el
    DNS publico de Google (8.8.8.8:53). Es el equivalente robusto a
    un 'ping' sin requerir privilegios ICMP en cron.
    """
    for i in range(intentos):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except OSError:
            if i < intentos - 1:
                import time
                time.sleep(5)
    return False


def log_fallback(mensaje: str):
    """Ultimo recurso: si Postgres tambien falla, al menos queda en disco local."""
    path = os.path.join(os.path.dirname(__file__), "..", "logs", "backup_fallback.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(f"[{datetime.now()}] {mensaje}\n")


def registrar_lote_inicio(conn, modo_test: bool) -> int:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO semi2.backup_lotes (fecha_inicio, estado, modo_test)
        VALUES (NOW(), 'EN_PROGRESO', %s) RETURNING lote_id
    """, (modo_test,))
    lote_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return lote_id


def registrar_lote_fin(conn, lote_id, estado, tablas_ok=0, tablas_fallidas=0,
                        notif_enviada=False, error=None):
    cur = conn.cursor()
    cur.execute("""
        UPDATE semi2.backup_lotes
        SET fecha_fin=NOW(), estado=%s, tablas_ok=%s, tablas_fallidas=%s,
            notificacion_enviada=%s, error_msg=%s
        WHERE lote_id=%s
    """, (estado, tablas_ok, tablas_fallidas, notif_enviada, error, lote_id))
    conn.commit()
    cur.close()


def registrar_run_inicio(conn, lote_id, tabla) -> int:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO semi2.backup_runs (lote_id, tabla_origen, fecha_inicio, estado)
        VALUES (%s, %s, NOW(), 'EN_PROGRESO') RETURNING backup_id
    """, (lote_id, tabla))
    backup_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return backup_id


def registrar_run_fin(conn, backup_id, estado, filas=0, bytes_local=0, ruta_nas=None, error=None):
    cur = conn.cursor()
    cur.execute("""
        UPDATE semi2.backup_runs
        SET fecha_fin=NOW(), estado=%s, filas=%s, bytes_local=%s, ruta_nas=%s, error_msg=%s
        WHERE backup_id=%s
    """, (estado, filas, bytes_local, ruta_nas, error, backup_id))
    conn.commit()
    cur.close()


def sync_tabla(tabla_fqn, db_conn, dbc_cursor, lote_id, schema_local, nas_dir, row_limit=None):
    nombre = tabla_fqn.split(".")[-1]
    backup_id = registrar_run_inicio(db_conn, lote_id, tabla_fqn)
    tmp = f"{nombre}_tmp"

    try:
        query = f"SELECT * FROM {tabla_fqn}"
        if row_limit:
            query += f" LIMIT {row_limit}"
        dbc_cursor.execute(query)
        rows = dbc_cursor.fetchall()
        cols = [d[0] for d in dbc_cursor.description]
        df = pd.DataFrame(rows, columns=cols)
        filas = len(df)

        # 1. Backup en NAS como parquet (espacio sobra, formato eficiente)
        os.makedirs(nas_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_nas = f"{nas_dir}/{nombre}_{ts}.parquet"
        df.to_parquet(ruta_nas, index=False)
        bytes_local = os.path.getsize(ruta_nas)

        # 2. Replica local en PostgreSQL — swap atomico (sin tabla a medio escribir)
        cur = db_conn.cursor()
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_local}')
        cur.execute(f'DROP TABLE IF EXISTS {schema_local}."{tmp}"')
        cols_sql = ", ".join([f'"{c}" TEXT' for c in cols])
        cur.execute(f'CREATE TABLE {schema_local}."{tmp}" ({cols_sql})')
        db_conn.commit()

        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False, na_rep="\\N", quoting=csv.QUOTE_MINIMAL)
        buf.seek(0)
        cur.copy_expert(
            f'COPY {schema_local}."{tmp}" FROM STDIN WITH (FORMAT csv, NULL \'\\N\', QUOTE \'"\')',
            buf
        )
        db_conn.commit()

        cur.execute(f'DROP TABLE IF EXISTS {schema_local}."{nombre}"')
        cur.execute(f'ALTER TABLE {schema_local}."{tmp}" RENAME TO "{nombre}"')
        db_conn.commit()
        cur.close()

        registrar_run_fin(db_conn, backup_id, "EXITOSO", filas, bytes_local, ruta_nas)
        print(f"  OK  {tabla_fqn}: {filas:,} filas -> {ruta_nas}")
        return True, bytes_local

    except Exception as e:
        db_conn.rollback()
        registrar_run_fin(db_conn, backup_id, "FALLIDO", error=str(e))
        print(f"  ERROR {tabla_fqn}: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                         help="Corre en modo prueba: LIMIT 200 filas, schema dw_local_test, carpeta NAS /test")
    args = parser.parse_args()
    modo_test = args.test

    print(f"[{datetime.now()}] Iniciando backup_dw.py (test={modo_test})")

    db_conn = psycopg2.connect(**config.DB_CONFIG)
    lote_id = registrar_lote_inicio(db_conn, modo_test)
    notifier = None
    estado_final = "FALLIDO"
    ok_count, fail_count = 0, 0
    notif_ok = False
    error_general = None

    try:
        # Paso 1: verificar internet ANTES de tocar nada
        if not hay_internet():
            error_general = "Sin conectividad a internet tras 3 intentos. No se modifico ninguna tabla local."
            estado_final = "SIN_INTERNET"
            print(f"[{datetime.now()}] {error_general}")
            log_fallback(f"lote {lote_id}: SIN_INTERNET - {error_general}")
            return

        try:
            notifier = EmailNotifier()
        except Exception as e:
            log_fallback(f"lote {lote_id}: no se pudo inicializar EmailNotifier - {e}")

        schema_local = "dw_local_test" if modo_test else "dw_local"
        nas_dir = f"{config.NAS_BACKUP_PATH}/test" if modo_test else config.NAS_BACKUP_PATH
        row_limit = 200 if modo_test else None

        try:
            from databricks import sql as dbsql
            dbc_conn = dbsql.connect(
                server_hostname=config.DATABRICKS_HOST,
                http_path=config.DATABRICKS_HTTP_PATH,
                access_token=config.DATABRICKS_TOKEN,
            )
            dbc_cursor = dbc_conn.cursor()
        except Exception as e:
            error_general = f"Conexion Databricks: {e}"
            estado_final = "FALLIDO"
            if notifier:
                try:
                    notifier.send_error("No se pudo conectar a Databricks", str(e),
                                         context={"lote_id": lote_id, "modo_test": modo_test})
                    notif_ok = True
                except Exception:
                    pass
            return

        total_bytes, errores = 0, []
        try:
            for tabla in config.TABLAS_TODAS:
                ok, b = sync_tabla(tabla, db_conn, dbc_cursor, lote_id, schema_local, nas_dir, row_limit)
                if ok:
                    ok_count += 1
                    total_bytes += b
                else:
                    fail_count += 1
                    errores.append(tabla)
        finally:
            dbc_cursor.close()
            dbc_conn.close()

        estado_final = "EXITOSO" if fail_count == 0 else ("PARCIAL" if ok_count > 0 else "FALLIDO")

        if notifier:
            try:
                resumen = {
                    "lote_id": lote_id, "modo_test": modo_test,
                    "tablas_ok": ok_count, "tablas_fallidas": fail_count,
                    "total_mb": round(total_bytes / 1024 / 1024, 2),
                    "schema_local": schema_local, "ruta_nas": nas_dir,
                }
                if estado_final == "EXITOSO":
                    notif_ok = notifier.send_success("Backup del DW completado correctamente", summary=resumen)
                else:
                    resumen["tablas_con_error"] = ", ".join(errores)
                    notif_ok = notifier.send_error("Backup del DW con fallos parciales o totales", context=resumen)
            except Exception as e:
                log_fallback(f"lote {lote_id}: fallo enviando notificacion - {e}")

    except KeyboardInterrupt:
        error_general = "Interrumpido manualmente (Ctrl-C)"
        estado_final = "FALLIDO"
        raise

    except Exception as e:
        error_general = f"Error no controlado: {e}"
        estado_final = "FALLIDO"
        log_fallback(f"lote {lote_id}: {error_general}")
        raise

    finally:
        # Esto corre SIEMPRE: exito, fallo, Ctrl-C, o excepcion sin manejar.
        # Garantiza que ningun lote quede en EN_PROGRESO para siempre.
        registrar_lote_fin(db_conn, lote_id, estado_final, ok_count, fail_count, notif_ok, error_general)
        db_conn.close()
        print(f"[{datetime.now()}] Lote {lote_id} finalizado: {estado_final} "
              f"({ok_count} ok, {fail_count} fallidas)")


if __name__ == "__main__":
    main()