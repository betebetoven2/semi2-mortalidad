import os
import subprocess
from datetime import datetime

import config
from email_service import EmailNotifier

NAS_AUDIT_PATH = os.path.join(
    os.path.dirname(config.NAS_BACKUP_PATH), "backup_auditoria_semi2"
)


def respaldar_schema_semi2():
    os.makedirs(NAS_AUDIT_PATH, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = os.path.join(NAS_AUDIT_PATH, f"semi2_{ts}.dump")

    cmd = [
        "docker", "exec", "postgres_db",
        "pg_dump",
        "-U", config.DB_CONFIG["user"],
        "-d", config.DB_CONFIG["dbname"],
        "--schema=semi2",
        "--format=custom",
        "--file", f"/tmp/semi2_{ts}.dump",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Copiar el dump de dentro del contenedor hacia el NAS
        cmd_cp = ["docker", "cp", f"postgres_db:/tmp/semi2_{ts}.dump", archivo]
        subprocess.run(cmd_cp, check=True, capture_output=True, text=True)

        # Limpiar el temporal dentro del contenedor
        subprocess.run(["docker", "exec", "postgres_db", "rm", f"/tmp/semi2_{ts}.dump"],
                        check=True, capture_output=True, text=True)

        bytes_local = os.path.getsize(archivo)
        return True, archivo, bytes_local, None

    except subprocess.CalledProcessError as e:
        return False, None, 0, e.stderr


def main():
    print(f"[{datetime.now()}] Iniciando backup_auditoria.py (schema semi2)")

    ok, archivo, bytes_local, error = respaldar_schema_semi2()
    notifier = None
    try:
        notifier = EmailNotifier()
    except Exception:
        pass

    if ok:
        print(f"  OK  schema semi2 -> {archivo} ({bytes_local/1024:.1f} KB)")
        if notifier:
            try:
                notifier.send_success(
                    "Backup del schema de auditoria (semi2) completado",
                    summary={"archivo": archivo, "kb": round(bytes_local / 1024, 1)},
                )
            except Exception:
                pass
    else:
        print(f"  ERROR respaldando semi2: {error}")
        if notifier:
            try:
                notifier.send_error("Fallo el backup del schema de auditoria (semi2)", str(error))
            except Exception:
                pass

    print(f"[{datetime.now()}] Finalizado")


if __name__ == "__main__":
    main()
