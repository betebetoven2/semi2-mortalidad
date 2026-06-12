# Ingesta de Datos — Fase 1

Plataforma Analítica de Mortalidad End-to-End  
Seminario de Sistemas 2 | Escuela de Vacaciones 2026 | USAC

## Descripción general

Este módulo implementa el pipeline de ingesta de datos de mortalidad desde fuentes públicas heterogéneas hacia un landing zone en AWS S3 y tablas Delta en Databricks. Toda operación queda registrada en una base de datos de auditoría PostgreSQL con trazabilidad completa desde el origen hasta el almacenamiento final.

## Arquitectura de despliegue

El pipeline opera sobre una arquitectura híbrida compuesta por un nodo de cómputo perimetral permanente en red local y servicios en nube.

### Nodo perimetral permanente (Always-On Edge Node)

El componente central de ejecución es una Raspberry Pi 5 de 8 GB RAM con procesador ARM64 corriendo Debian Bookworm, configurada como nodo de ejecución continua dentro de la red local. Esta decisión arquitectónica es intencional: la máquina opera sin intervención humana, ejecuta los scrapers de forma programada y gestiona la transferencia hacia la nube. No es un servidor de desarrollo sino un nodo de campo dedicado a la ingesta.

El almacenamiento raw local se resuelve mediante un NAS Toshiba de 2 TB compartido por Samba en la misma red local (LAN 192.168.1.0/24), montado en la Raspberry Pi en `/mnt/extra/cys/cys_u/semi2/raw/`. Este dispositivo actúa como zona de aterrizaje local antes de la transferencia a S3, garantizando persistencia ante fallos de conectividad.

### Stack tecnológico

| Componente | Tecnología | Rol |
|---|---|---|
| Edge Node | Raspberry Pi 5 8 GB, ARM64, Debian Bookworm | Ejecución continua de scrapers |
| Almacenamiento local | NAS Samba 2 TB, LAN | Landing zone local, raw files |
| Base de auditoría | PostgreSQL 16, Docker, schema semi2 | Registro de comportamiento de ingesta |
| Lenguaje | Python 3.11, entorno virtual venv | Scripts de descarga y conversión |
| Automatización de browser | Playwright Chromium headless | Bypass WAF Radware portal INE legacy |
| Conversión de formatos | pyreadstat, pandas, pyarrow | SAV (SPSS) a Parquet |
| Object storage nube | AWS S3, bucket mortalidad-gtm-2026, us-east-1 | Landing zone en nube |
| Sandbox analítico | Databricks Free Edition, schema bronze | Tablas Delta sin relaciones |
| SDK nube | boto3 | Transferencia local a S3 |

## Estructura del repositorio

```
ingesta/
    scripts/
        scripts/bronze_ingesta.ipynb ingesta hacia databricks con logs incluidos
        config.py                   Carga de variables de entorno (.env)
        scraper_base.py             Clase base con auditoría PostgreSQL integrada
        download_ine.py             Descarga INE Guatemala 2018-2024 (XLSX)
        download_ine_legacy.py      Descarga INE Guatemala 2015-2017 (SAV, Playwright)
        download_oms.py             Descarga WHO/OMS via GHO API
        download_ca.py              Descarga World Bank API, Centroamérica
        run_all.py                  Orquestador secuencial de todas las fuentes
    logs/
        *.log                       Logs de ejecución con timestamp
```

## Configuración

Crear el archivo `.env` en la raíz del módulo con los siguientes valores:

```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=mortalidad-gtm-2026

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=law
POSTGRES_USER=betebetoven
POSTGRES_PASSWORD=betebetoven
POSTGRES_SCHEMA=semi2

RAW_DATA_PATH=/mnt/extra/cys/cys_u/semi2/raw
```



## Ejecución

Para correr todas las fuentes en secuencia:

```bash
python3 run_all.py
```

Para correr una fuente individual:

```bash
python3 download_ine.py
python3 download_ine_legacy.py
python3 download_oms.py
python3 download_ca.py
```

## Fuentes de datos y enfoque por fuente

### INE Guatemala — Estadísticas Vitales de Defunciones (2018-2024)

Portal: `datos.ine.gob.gt/dataset/estadisticas-vitales-defunciones`

Los archivos están disponibles como descarga directa sin autenticación en formato XLSX. El script realiza peticiones HTTP GET a cada URL con User-Agent estándar de browser, escribe el binario en el NAS local y lo transfiere a S3 mediante boto3. El portal no presenta protección adicional para estos años. Cada descarga genera un run en la tabla de auditoría con checksum MD5 para verificación de integridad.

### INE Guatemala — Estadísticas Vitales de Defunciones (2015-2017)

Portal: `ine.gob.gt/publicaciones3.php?c=82`

Los archivos de estos años están en formato SAV de SPSS y el portal está protegido por Radware Bot Manager, un WAF que bloquea cualquier cliente sin ejecución real de JavaScript devolviendo una página de CAPTCHA. Se descartaron los enfoques de requests con sesión, headers X-Requested-With y playwright context.request porque ninguno porta el estado de validación JavaScript que Radware requiere.

La solución implementada usa Playwright con Chromium headless simulando interacción humana completa: navegación a la página base para validar el cliente ante Radware, selección del año en el dropdown HTML que dispara la función componer_periodo() del portal, selección del periodo anual que dispara el jQuery .load() con el fragmento AJAX, espera del selector CSS sobre el DOM real y click() sobre el enlace de Defunciones envuelto en expect_download(). Los archivos SAV se convierten a Parquet mediante pyreadstat para compatibilidad con Spark. Ambos formatos se preservan en S3.

### WHO / OMS — Global Health Observatory

API: `ghoapi.azureedge.net/api`

La API pública del GHO no requiere autenticación. Se consultan tres indicadores de mortalidad para cinco países centroamericanos (GTM, CRI, HND, SLV, PAN) generando un archivo JSON independiente por combinación indicador-país, lo que facilita reintentos individuales y trazabilidad granular. La respuesta sigue el formato OData con los datos en el campo `value`.

### World Bank — Indicadores de Desarrollo

API: `api.worldbank.org/v2/country`

La API del Banco Mundial permite consultar múltiples países en una sola petición separando los códigos ISO3 con punto y coma. Se descargan cinco indicadores de mortalidad y causa de muerte para seis países centroamericanos con rango temporal 2010-2024. La respuesta es un array JSON donde el índice 0 contiene la metadata de paginación y el índice 1 los registros. Esta fuente reemplazó a CEPAL CEPALSTAT cuyo dominio `api.cepal.org` no fue resolvible durante la ejecución, fallo documentado en la tabla de auditoría (run_id 22, estado FALLIDO).

### Google Drive — Archivos del equipo

Carpeta compartida del equipo con ID `198lQfATsiCSEwJIaIlijq9N0vyVIdRq8`.

El script `download_gdrive.py` descarga el diccionario de variables del INE publicado en la carpeta compartida mediante una petición HTTP GET al endpoint de exportación de Drive usando el ID del archivo, sin autenticación adicional. El archivo se almacena en `raw/gdrive/` en el NAS local y se transfiere a S3.

## Base de datos de auditoría

El schema `semi2` dentro de la base `law` en PostgreSQL registra cada operación de ingesta. El diagrama ERD se encuentra en `docs/erd_auditoria.png`.

La tabla `scraping_runs` registra cada ejecución con su estado final, fuente, URL de origen, bytes transferidos y mensaje de error cuando aplica. La tabla `archivos_descargados` registra cada archivo individual con su checksum MD5, ruta en S3 y estado de subida. La vista `resumen_ingesta` agrega las ejecuciones por fuente para monitoreo rápido.

Para consultar el estado de la última ingesta:

```sql
SELECT * FROM semi2.resumen_ingesta;
```

## Tablas Delta — Schema bronze (Databricks)

Las tablas se crean en Databricks Free Edition leyendo los raw files desde S3 mediante boto3. Cada tabla corresponde a una fuente de datos sin relaciones entre ellas.

| Tabla | Fuente | Filas |
|---|---|---|
| bronze.xlsx_ine | INE Guatemala 2018-2024, XLSX | 674,064 |
| bronze.sav_ine_legacy | INE Guatemala 2015-2017, SAV convertido a Parquet | 245,167 |
| bronze.json_oms | WHO/OMS GHO API, JSON | 1,708 |
| bronze.json_worldbank | World Bank API, JSON | 450 |
| bronze.gdrive_docs | Google Drive, diccionario de variables INE | 1,837 |

## Evidencia de ejecución

Al término de la ingesta completa, el bucket S3 contiene:

```
raw/ine/           defunciones_2015.sav   defunciones_2015.parquet
                   defunciones_2016.sav   defunciones_2016.parquet
                   defunciones_2017.sav   defunciones_2017.parquet
                   defunciones_2018.xlsx  ...  defunciones_2024.xlsx
raw/oms/           who_life_expectancy_gtm.json  ... (15 archivos)
raw/centroamerica/ worldbank_crude_death_rate_centroamerica.json  ... (5 archivos)
raw/gdrive/        diccionario_defunciones_ine.xlsx
```

La tabla `semi2.resumen_ingesta` muestra 44 ejecuciones registradas: 28 exitosas para INE (incluyendo legacy), 15 para WHO/OMS, 5 para World Bank y 1 para Google Drive.