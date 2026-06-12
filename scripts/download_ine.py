import os
import requests
from config import RAW_PATH
from scraper_base import ScraperAuditado

INE_URLS = {
    2018: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/326cfcf2-87c1-40f1-be1c-707a0993b98b/download/defunciones-2018.xlsx",
    2019: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/f607ea3a-3d31-4b47-b0b6-fc94bc383166/download/defunciones-2019.xlsx",
    2020: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/08528179-f8ed-495f-a82d-61cb618727fd/download/defunciones-2020.xlsx",
    2021: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/183bcdd9-ca7b-4979-b247-44f2a4b0f640/download/defunciones-2021.xlsx",
    2022: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/a3615e30-9fa9-4b40-a33a-4482b7bf7802/download/defunciones-2022.xlsx",
    2023: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/2c7cc9ee-dee4-44df-b83a-408435c6242a/download/defunciones2023da.xlsx",
    2024: "https://datos.ine.gob.gt/dataset/14f547c3-ad37-4ea1-9e74-16a3ed50ff54/resource/db7d7ce4-a450-466b-9bd9-8150eb55c34b/download/bd-defunciones-2024-da.xlsx",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto-academico-USAC-semi2)"}
OUTPUT_DIR = os.path.join(RAW_PATH, "ine")


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scraper = ScraperAuditado(fuente="INE_GUATEMALA")
    bytes_total = 0

    for year, url in INE_URLS.items():
        filepath = os.path.join(OUTPUT_DIR, f"defunciones_{year}.xlsx")

        # Saltar si ya existe (evita re-descargar lo que ya subimos)
        if os.path.exists(filepath):
            print(f"  ↷ {year} ya existe, omitiendo")
            continue

        scraper.iniciar_run(url)
        s3_key = f"raw/ine/defunciones_{year}.xlsx"

        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(r.content)

            scraper.subir_a_s3(filepath, s3_key)
            scraper.registrar_archivo(
                nombre=f"defunciones_{year}.xlsx",
                url=url,
                filepath=filepath,
                s3_key=s3_key,
            )
            size = os.path.getsize(filepath)
            bytes_total += size
            scraper.finalizar_run("EXITOSO", registros=1, bytes_total=size)

        except Exception as e:
            scraper.finalizar_run("FALLIDO", error=str(e))
            print(f"  ✗ Error año {year}: {e}")

    scraper.cerrar()
    print(f"\n✓ INE completo — {bytes_total/1024/1024:.1f} MB nuevos")


if __name__ == "__main__":
    run()
