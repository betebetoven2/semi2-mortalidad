# Catálogo de Fuentes de Datos

**Elaborado por:** Grupo 3 | **Fecha:** 2026-06-14 | **Versión:** 1.0

La **procedencia** (o *provenance*) documenta el origen de cada dato: quién lo produce, cómo se accede, en qué formato llega y qué limitaciones tiene. Este catálogo es la base para cualquier auditoría de calidad o reproducibilidad del análisis.

---

## 1. INE Guatemala — Defunciones 2018–2024

!!! success "Acceso directo sin autenticación"

| Atributo | Detalle |
|---|---|
| **Institución** | Instituto Nacional de Estadística de Guatemala (INE) |
| **URL** | `datos.ine.gob.gt/dataset/estadisticas-vitales-defunciones` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/ine/defunciones_{año}.xlsx` |
| **Tabla Databricks** | `bronze.xlsx_ine` |
| **Formato** | Microsoft Excel (.xlsx) |
| **Años** | 2018 · 2019 · 2020 · 2021 · 2022 · 2023 · 2024 |
| **Volumen** | 674,064 registros |
| **Método** | HTTP GET directo, sin autenticación |
| **Actualización** | Anual (rezago ~12 meses) |
| **Cobertura** | República de Guatemala, nivel municipio |
| **Causa de muerte** | CIE-10 (Clasificación Internacional de Enfermedades, 10.ª rev.) |
| **Licencia** | Datos públicos del Estado de Guatemala |

??? warning "Limitaciones conocidas"
    - **Esquema variable por año:** versiones con 25 y otras con 28 columnas. Se resolvió con un "Súper Esquema" de 30+ columnas y relleno `NULL` donde la variable no existía.
    - **Subregistro:** el INE reconoce que no todos los fallecimientos llegan al registro civil, especialmente en áreas rurales e indígenas.
    - **CIE-10 incompleto:** algunas causas (`caudef`) usan códigos no estándar o truncados, requiriendo limpieza en la capa analítica.
    - **Dato de ocupación (`ciuodif`):** alta tasa de nulos o valores genéricos; no recomendado para análisis socioeconómico sin tratamiento previo.

---

## 2. INE Guatemala — Defunciones 2015–2017 (Legacy)

!!! warning "Requiere bypass de WAF con Playwright"

| Atributo | Detalle |
|---|---|
| **Institución** | Instituto Nacional de Estadística de Guatemala (INE) |
| **URL** | `ine.gob.gt/publicaciones3.php?c=82` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/ine/defunciones_{año}.sav` y `.parquet` |
| **Tabla Databricks** | `bronze.sav_ine_legacy` |
| **Formato** | SPSS Statistics (.sav) convertido a Parquet vía `pyreadstat` |
| **Años** | 2015 · 2016 · 2017 |
| **Volumen** | 245,167 registros |
| **Método** | Playwright Chromium headless (bypass Radware Bot Manager) |
| **Actualización** | Estático — publicación histórica sin actualizaciones esperadas |
| **Cobertura** | República de Guatemala, nivel municipio |
| **Licencia** | Datos públicos del Estado de Guatemala |

??? warning "Limitaciones conocidas"
    - **Barrera técnica (WAF):** el portal legacy está protegido por Radware Bot Manager. Requiere simulación de navegador real; frágil ante cambios en el portal INE.
    - **Formato propietario SAV:** conversión a Parquet introduce dependencia de `pyreadstat`; bugs en la librería pueden afectar la fidelidad del dato.
    - **Metadatos SAV no migrados:** las etiquetas embebidas en SPSS no se preservan en Parquet; se depende del diccionario de Google Drive para decodificación.
    - **Incompatibilidad de esquema con 2018–2024:** exige lógica de homologación en la capa Silver/Gold.

---

## 3. WHO / OMS — Global Health Observatory (GHO)

!!! success "API pública sin autenticación"

| Atributo | Detalle |
|---|---|
| **Institución** | Organización Mundial de la Salud (OMS / WHO) |
| **API** | `ghoapi.azureedge.net/api` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/oms/who_{indicador}_{país}.json` |
| **Tabla Databricks** | `bronze.json_oms` |
| **Formato** | JSON (protocolo OData) |
| **Años** | ~1990–2023 (variable por indicador) |
| **Archivos** | 15 JSON (3 indicadores × 5 países) |
| **Volumen** | 1,708 registros |
| **Países** | GTM · CRI · HND · SLV · PAN |
| **Indicadores** | Esperanza de vida, Mortalidad infantil (<5 años), Tasa de mortalidad |
| **Actualización** | Anual |
| **Licencia** | CC BY-NC-SA 3.0 IGO (uso no comercial con atribución) |

??? warning "Limitaciones conocidas"
    - **Granularidad nacional únicamente:** no es posible cruzar con datos departamentales del INE sin metodología de desagregación adicional.
    - **Intervalos de confianza amplios:** especialmente en países con sistemas de registro civil débiles.
    - **Latencia de 1–2 años:** el año 2024 puede no estar disponible hasta 2025–2026.
    - **Dependencia de CDN Azure:** interrupciones en `azureedge.net` afectan la ingesta aunque la OMS esté disponible.
    - **Licencia no comercial:** uso restringido a fines académicos y de salud pública.

---

## 4. World Bank — Indicadores de Desarrollo Mundial

!!! success "API pública sin autenticación — CC BY 4.0"

| Atributo | Detalle |
|---|---|
| **Institución** | Banco Mundial (World Bank) |
| **API** | `api.worldbank.org/v2/country` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/centroamerica/worldbank_{indicador}_centroamerica.json` |
| **Tabla Databricks** | `bronze.json_worldbank` |
| **Formato** | JSON |
| **Años** | 2010–2024 |
| **Archivos** | 5 JSON (1 por indicador) |
| **Volumen** | 450 registros |
| **Países** | GTM · CRI · HND · SLV · PAN · NIC |
| **Indicadores** | Tasa bruta de mortalidad · Mortalidad infantil · Mortalidad materna · Esperanza de vida · Causas de muerte |
| **Actualización** | Anual |
| **Licencia** | Creative Commons CC BY 4.0 |

??? warning "Limitaciones conocidas"
    - **Fuente alternativa:** reemplazó a CEPALSTAT cuyo dominio `api.cepal.org` no fue resolvible (fallo documentado en auditoría, run_id 22, estado `FALLIDO`).
    - **Datos estimados:** la mayoría son estimaciones con ajustes metodológicos propios, no registros directos. Ver campo `obs_status`.
    - **Datos 2023–2024 preliminares:** el Banco Mundial revisa retroactivamente; sujetos a cambio.
    - **Solo nivel país:** sin desagregación subnacional.

---

## 5. Google Drive — Diccionario de Variables INE

!!! note "Fuente interna del equipo"

| Atributo | Detalle |
|---|---|
| **Institución** | Equipo del proyecto (fuente complementaria) |
| **URL** | Carpeta compartida Google Drive, ID: `198lQfATsiCSEwJIaIlijq9N0vyVIdRq8` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/gdrive/diccionario_defunciones_ine.xlsx` |
| **Tabla Databricks** | `bronze.gdrive_docs` |
| **Tabla Sandbox** | `sandbox.sandbox_gdrive_diccionario` |
| **Formato** | Microsoft Excel (.xlsx) |
| **Volumen** | 1,837 registros (pares variable–código–etiqueta) |
| **Licencia** | Uso interno del equipo |

??? warning "Limitaciones conocidas"
    - **Fuente no oficial:** compilación del equipo, no publicación del INE. Puede contener omisiones.
    - **Sin control de versiones:** el archivo en Drive puede editarse sin historial. La copia en S3 es la versión canónica.
    - **CIE-10 parcial:** puede no incluir todos los códigos de uso poco frecuente.

---

## Resumen y Matriz de Riesgos

| # | Fuente | Registros | Acceso | Riesgo disponibilidad | Mitigación |
|---|---|---|---|---|---|
| 1 | INE 2018–2024 | 674,064 | Directo | Bajo | Copia S3 + NAS |
| 2 | INE 2015–2017 | 245,167 | Playwright | Alto | SAV y Parquet ya en S3 |
| 3 | OMS GHO | 1,708 | API pública | Medio | 15 JSON en S3 |
| 4 | Banco Mundial | 450 | API pública | Bajo | 5 JSON en S3 |
| 5 | Diccionario Drive | 1,837 | Drive compartido | Medio | Excel en S3 como copia canónica |
| | **Total** | **923,226** | | | |
