import os
import json
import requests
from config import RAW_PATH
from scraper_base import ScraperAuditado

OUTPUT_DIR = os.path.join(RAW_PATH, "centroamerica")

# World Bank API — pública, sin autenticación, muy estable
# SP.DYN.CDRT.IN = Crude death rate (por 1000 habitantes)
# SP.DYN.IMRT.IN = Infant mortality rate
# SH.DTH.COMM.ZS = Cause of death communicable diseases %
PAISES = "GTM;CRI;HND;SLV;PAN;NIC"
INDICADORES = {
    "SP.DYN.CDRT.IN": "crude_death_rate",
    "SP.DYN.IMRT.IN": "infant_mortality",
    "SH.DTH.COMM.ZS": "death_communicable_pct",
    "SH.DTH.NCOM.ZS": "death_noncommunicable_pct",
    "SH.DTH.INJR.ZS": "death_injuries_pct",
}
BASE_URL = "https://api.worldbank.org/v2/country"


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scraper = ScraperAuditado(fuente="WORLDBANK_CENTROAMERICA")

    for indicator_code, indicator_name in INDICADORES.items():
        url = (
            f"{BASE_URL}/{PAISES}/indicator/{indicator_code}"
            f"?format=json&per_page=500&date=2010:2024"
        )
        scraper.iniciar_run(url)

        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()

            # World Bank devuelve [metadata, datos]
            records = data[1] if len(data) > 1 else []

            filename = f"worldbank_{indicator_name}_centroamerica.json"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            s3_key = f"raw/centroamerica/{filename}"
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
            print(f"  ✗ Error {indicator_code}: {e}")

    scraper.cerrar()
    print("\n✓ World Bank / Centroamérica completo")


if __name__ == "__main__":
    run()
