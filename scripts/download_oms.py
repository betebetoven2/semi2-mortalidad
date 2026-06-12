import os
import json
import requests
from config import RAW_PATH
from scraper_base import ScraperAuditado

# WHO Global Health Observatory - API pública sin autenticación
WHO_INDICADORES = {
    "WHOSIS_000001": "life_expectancy",
    "WHOSIS_000002": "healthy_life_expectancy",
    "MDG_0000000001": "mortality_under5",
}
PAISES = ["GTM", "CRI", "HND", "SLV", "PAN"]  # Guatemala + Centroamérica
BASE_URL = "https://ghoapi.azureedge.net/api"
OUTPUT_DIR = os.path.join(RAW_PATH, "oms")


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scraper = ScraperAuditado(fuente="WHO_OMS")

    for code, name in WHO_INDICADORES.items():
        # Un país a la vez para trazabilidad
        for pais in PAISES:
            url = f"{BASE_URL}/{code}?$filter=SpatialDim eq '{pais}'"
            scraper.iniciar_run(url)

            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                data = r.json()
                records = data.get("value", [])

                filename = f"who_{name}_{pais.lower()}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                s3_key = f"raw/oms/{filename}"
                scraper.subir_a_s3(filepath, s3_key)
                scraper.registrar_archivo(
                    nombre=filename,
                    url=url,
                    filepath=filepath,
                    s3_key=s3_key,
                )
                size = os.path.getsize(filepath)
                scraper.finalizar_run("EXITOSO", registros=len(records), bytes_total=size)

            except Exception as e:
                scraper.finalizar_run("FALLIDO", error=str(e))
                print(f"  ✗ Error {code}/{pais}: {e}")

    scraper.cerrar()
    print("\n✓ OMS/WHO completo")


if __name__ == "__main__":
    run()
