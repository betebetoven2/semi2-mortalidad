import os
import asyncio
import pyreadstat
import pandas as pd
from playwright.async_api import async_playwright
from config import RAW_PATH
from scraper_base import ScraperAuditado

OUTPUT_DIR = os.path.join(RAW_PATH, "ine")
BASE_PAGE  = "https://www.ine.gob.gt/publicaciones3.php?c=82"
YEARS      = [2015, 2016, 2017]


async def get_and_download(page, year, sav_path):
    print(f"  [{year}] Navegando a pagina base...")
    await page.goto(BASE_PAGE, wait_until="networkidle", timeout=30000)

    print(f"  [{year}] Seleccionando año {year}...")
    await page.select_option("#anio", str(year))
    await page.wait_for_timeout(800)

    print(f"  [{year}] Seleccionando periodo Anual...")
    await page.select_option("#periodo", "1")

    print(f"  [{year}] Esperando links en DOM...")
    await page.wait_for_selector("#tablaresultado a[href$='.sav']", timeout=15000)

    file_url = None
    links = await page.query_selector_all("#tablaresultado a[href$='.sav']")
    for link in links:
        texto = (await link.inner_text()).strip().lower()
        href  = await link.get_attribute("href")
        print(f"  [{year}] Link: '{texto}' → {href}")
        if "defunciones" in texto and "fetal" not in texto and texto != "":
            file_url = href
            target_link = link
            break

    if not file_url:
        raise ValueError(f"No se encontro link .sav para {year}")

    print(f"  [{year}] Descargando via expect_download + click...")
    async with page.expect_download(timeout=120000) as download_info:
        await target_link.click()

    download = await download_info.value
    suggested = download.suggested_filename
    print(f"  [{year}] Archivo sugerido: {suggested}")

    await download.save_as(sav_path)
    size_mb = os.path.getsize(sav_path) / 1024 / 1024
    print(f"  [{year}] Guardado: {size_mb:.2f} MB")

    if size_mb < 0.5:
        raise ValueError(f"Archivo muy pequeno: {size_mb:.3f} MB")

    return file_url


async def run_async():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scraper = ScraperAuditado(fuente="INE_GUATEMALA_LEGACY")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="es-GT",
            accept_downloads=True,
        )
        page = await context.new_page()

        for year in YEARS:
            sav_path     = os.path.join(OUTPUT_DIR, f"defunciones_{year}.sav")
            parquet_path = os.path.join(OUTPUT_DIR, f"defunciones_{year}.parquet")

            for f in [sav_path, parquet_path]:
                if os.path.exists(f) and os.path.getsize(f) < 10240:
                    os.remove(f)
                    print(f"  [{year}] archivo corrupto eliminado: {f}")

            if os.path.exists(parquet_path):
                print(f"  [{year}] ya existe, omitiendo")
                continue

            print(f"\n--- Procesando {year} ---")
            try:
                file_url = await get_and_download(page, year, sav_path)
                scraper.iniciar_run(file_url)

                print(f"  [{year}] Convirtiendo SAV → parquet...")
                df, meta = pyreadstat.read_sav(sav_path)
                df.to_parquet(parquet_path, index=False)
                print(f"  [{year}] Convertido: {len(df):,} filas")

                scraper.subir_a_s3(sav_path,     f"raw/ine/defunciones_{year}.sav")
                scraper.subir_a_s3(parquet_path, f"raw/ine/defunciones_{year}.parquet")
                scraper.registrar_archivo(
                    nombre=f"defunciones_{year}.parquet",
                    url=file_url,
                    filepath=parquet_path,
                    s3_key=f"raw/ine/defunciones_{year}.parquet",
                )
                scraper.finalizar_run(
                    "EXITOSO",
                    registros=len(df),
                    bytes_total=os.path.getsize(parquet_path),
                )

            except Exception as e:
                scraper.finalizar_run("FALLIDO", error=str(e))
                print(f"  Error {year}: {e}")

        await browser.close()

    scraper.cerrar()
    print("\nINE legacy 2015-2017 completo")


def run():
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
