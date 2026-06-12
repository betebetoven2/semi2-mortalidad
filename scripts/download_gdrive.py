import os
import requests
from config import RAW_PATH
from scraper_base import ScraperAuditado

FILE_ID = "198lQfATsiCSEwJIaIlijq9N0vyVIdRq8"
OUTPUT_DIR = os.path.join(RAW_PATH, "gdrive")
FILENAME = "diccionario_defunciones_ine.xlsx"

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scraper = ScraperAuditado(fuente="GOOGLE_DRIVE")
    url = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
    scraper.iniciar_run(url)
    try:
        session = requests.Session()
        r = session.get(url, timeout=60)
        for key, val in r.cookies.items():
            if "download_warning" in key:
                url = f"https://drive.google.com/uc?export=download&confirm={val}&id={FILE_ID}"
                r = session.get(url, timeout=60)
                break
        r.raise_for_status()
        filepath = os.path.join(OUTPUT_DIR, FILENAME)
        with open(filepath, "wb") as f:
            f.write(r.content)
        size = os.path.getsize(filepath)
        print(f"Descargado: {size/1024:.1f} KB")
        s3_key = f"raw/gdrive/{FILENAME}"
        scraper.subir_a_s3(filepath, s3_key)
        scraper.registrar_archivo(
            nombre=FILENAME,
            url=url,
            filepath=filepath,
            s3_key=s3_key,
        )
        scraper.finalizar_run("EXITOSO", registros=1, bytes_total=size)
    except Exception as e:
        scraper.finalizar_run("FALLIDO", error=str(e))
        print(f"Error: {e}")
    scraper.cerrar()

if __name__ == "__main__":
    run()
