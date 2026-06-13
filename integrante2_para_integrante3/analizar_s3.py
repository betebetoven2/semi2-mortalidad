"""
analizar_s3.py
Analiza todos los archivos del bucket mortalidad-gtm-2026
Imprime estructura, columnas, tipos y primeras 3 filas de cada archivo.
"""

import boto3
import pandas as pd
import pyreadstat
import json
import io
import sys

BUCKET = "mortalidad-gtm-2026"
s3 = boto3.client("s3")

def separador(titulo):
    print("\n" + "="*70)
    print(f"  {titulo}")
    print("="*70)

def info_df(df, nombre):
    print(f"\n📋 Columnas ({len(df.columns)}): {list(df.columns)}")
    print(f"📊 Shape: {df.shape[0]} filas x {df.shape[1]} columnas")
    print(f"\n🔍 Tipos de datos:")
    for col, dtype in df.dtypes.items():
        nulos = df[col].isna().sum()
        print(f"   {col:<40} {str(dtype):<15} nulos: {nulos}")
    print(f"\n📄 Primeras 3 filas:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_colwidth', 40)
    print(df.head(3).to_string())

def leer_parquet(obj):
    buf = io.BytesIO(obj["Body"].read())
    return pd.read_parquet(buf)

def leer_xlsx(obj):
    buf = io.BytesIO(obj["Body"].read())
    return pd.read_excel(buf, nrows=200)  # solo 200 filas para no explotar memoria

def leer_sav(obj):
    buf = io.BytesIO(obj["Body"].read())
    df, meta = pyreadstat.read_sav(buf, row_limit=200)
    return df

def leer_json(obj):
    contenido = obj["Body"].read().decode("utf-8")
    data = json.loads(contenido)
    # World Bank / OMS devuelven listas o dicts anidados
    if isinstance(data, list):
        # WB format: [metadata, [records]]
        if len(data) == 2 and isinstance(data[1], list):
            return pd.json_normalize(data[1])
        return pd.json_normalize(data)
    elif isinstance(data, dict):
        # Buscar la lista principal dentro del dict
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0:
                return pd.json_normalize(val)
        return pd.json_normalize([data])
    return pd.DataFrame()

# Listar todos los objetos
print("🚀 Conectando al bucket:", BUCKET)
paginator = s3.get_paginator("list_objects_v2")
pages = paginator.paginate(Bucket=BUCKET)

keys = []
for page in pages:
    for obj in page.get("Contents", []):
        keys.append(obj["Key"])

print(f"✅ {len(keys)} archivos encontrados\n")

errores = []

for key in sorted(keys):
    separador(key)
    ext = key.split(".")[-1].lower()

    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)

        if ext == "parquet":
            df = leer_parquet(obj)
            info_df(df, key)

        elif ext in ("xlsx", "xls"):
            df = leer_xlsx(obj)
            info_df(df, key)

        elif ext == "sav":
            df = leer_sav(obj)
            info_df(df, key)

        elif ext == "json":
            df = leer_json(obj)
            if df.empty:
                print("⚠️  JSON vacío o estructura no reconocida")
                # Imprimir las primeras claves del JSON crudo
                obj2 = s3.get_object(Bucket=BUCKET, Key=key)
                raw = json.loads(obj2["Body"].read().decode("utf-8"))
                if isinstance(raw, list):
                    print(f"   Lista de {len(raw)} elementos")
                    print(f"   Primer elemento: {str(raw[0])[:300]}")
                elif isinstance(raw, dict):
                    print(f"   Dict con claves: {list(raw.keys())}")
            else:
                info_df(df, key)
        else:
            print(f"⚠️  Formato .{ext} no manejado")

    except Exception as e:
        msg = f"❌ ERROR en {key}: {e}"
        print(msg)
        errores.append(msg)

# Resumen final
separador("RESUMEN DE ERRORES")
if errores:
    for e in errores:
        print(e)
else:
    print("✅ Sin errores")