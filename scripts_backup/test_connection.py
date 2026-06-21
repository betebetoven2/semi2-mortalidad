import os
import socket
import psycopg2
import config

print("1. Internet (TCP a 8.8.8.8:53)...")
try:
    socket.setdefaulttimeout(3)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
    print("   OK")
except OSError as e:
    print(f"   FALLO: {e}")

print("2. PostgreSQL local...")
try:
    conn = psycopg2.connect(**config.DB_CONFIG)
    print("   OK")
    conn.close()
except Exception as e:
    print(f"   FALLO: {e}")

print("3. NAS (escritura)...")
try:
    os.makedirs(config.NAS_BACKUP_PATH, exist_ok=True)
    test_file = os.path.join(config.NAS_BACKUP_PATH, "_write_test.tmp")
    with open(test_file, "w") as f:
        f.write("ok")
    os.remove(test_file)
    print("   OK")
except Exception as e:
    print(f"   FALLO: {e}")

print("4. Databricks (host/token/http_path configurados)...")
if config.DATABRICKS_HOST and config.DATABRICKS_TOKEN and config.DATABRICKS_HTTP_PATH:
    print("   Valores presentes en .env (no se prueba conexion aqui)")
else:
    print("   FALTAN valores en .env")

print("5. Email (SMTP_USER/PASS/EMAIL_TO configurados)...")
if config.SMTP_USER and config.SMTP_PASS and config.EMAIL_TO:
    print("   Valores presentes en .env")
else:
    print("   FALTAN valores en .env")
