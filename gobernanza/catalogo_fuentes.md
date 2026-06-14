# Catálogo de Fuentes de Datos
## Plataforma Analítica de Mortalidad — Seminario de Sistemas 2 | USAC 2026

**Elaborado por:** Grupo 3  
**Fecha:** 2026-06-14  
**Versión:** 1.0  
**Estado:** Fase 1 completada (923,226 registros cargados en Sandbox)

---

## Resumen Ejecutivo

Este catálogo documenta las cuatro fuentes de datos heterogéneas que alimentan la Plataforma Analítica de Mortalidad de Guatemala y Centroamérica. Los datos atraviesan un pipeline ELT que parte de fuentes públicas, pasa por una zona de aterrizaje en AWS S3, y aterriza en la capa Sandbox de PostgreSQL y tablas Delta de Databricks para análisis posterior.

---

## 1. INE Guatemala — Estadísticas Vitales de Defunciones (2018–2024)

| Atributo | Detalle |
|---|---|
| **Institución** | Instituto Nacional de Estadística de Guatemala (INE) |
| **URL de origen** | `datos.ine.gob.gt/dataset/estadisticas-vitales-defunciones` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/ine/defunciones_{año}.xlsx` |
| **Tabla Databricks** | `bronze.xlsx_ine` |
| **Formato** | Microsoft Excel (.xlsx) |
| **Años cubiertos** | 2018, 2019, 2020, 2021, 2022, 2023, 2024 (7 archivos) |
| **Volumen** | 674,064 registros (parte de los 921,208 totales de INE) |
| **Método de acceso** | Descarga directa HTTP GET sin autenticación |
| **Frecuencia de actualización** | Anual (publicación con rezago de ~12 meses) |
| **Cobertura geográfica** | República de Guatemala, nivel municipio |
| **Clasificación de causa** | CIE-10 (Clasificación Internacional de Enfermedades, 10.ª revisión) |
| **Licencia** | Datos públicos del Estado de Guatemala |

### Limitaciones y Advertencias

- **Rezago temporal:** La publicación anual implica que el año más reciente disponible puede tener hasta 12 meses de retraso respecto al año calendario corriente.
- **Esquema variable por año:** Las columnas no son uniformes entre años. Se detectaron versiones con 25 y otras con 28 columnas. Se resolvió con un "Súper Esquema" de 30+ columnas y relleno de `NULL` donde la variable no existía.
- **Subregistro:** El INE reconoce que no todos los fallecimientos llegan al registro civil, particularmente en áreas rurales e indígenas. Las cifras pueden subestimar la mortalidad real.
- **Codificación de CIE-10:** Algunas causas de defunción (`caudef`) están codificadas de forma incompleta o con códigos no estándar, requiriendo limpieza en la capa analítica.
- **Calidad del dato de ocupación (`ciuodif`):** Alta tasa de valores nulos o genéricos. No se recomienda para análisis socioeconómico sin tratamiento previo.

---

## 2. INE Guatemala — Estadísticas Vitales de Defunciones (2015–2017)

| Atributo | Detalle |
|---|---|
| **Institución** | Instituto Nacional de Estadística de Guatemala (INE) |
| **URL de origen** | `ine.gob.gt/publicaciones3.php?c=82` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/ine/defunciones_{año}.sav` y `.parquet` |
| **Tabla Databricks** | `bronze.sav_ine_legacy` |
| **Formato** | SPSS Statistics (.sav), convertido a Parquet vía `pyreadstat` |
| **Años cubiertos** | 2015, 2016, 2017 (3 archivos SAV + 3 Parquet) |
| **Volumen** | 245,167 registros |
| **Método de acceso** | Playwright Chromium headless (bypass WAF Radware Bot Manager) |
| **Frecuencia de actualización** | Estático — publicación histórica, no se espera actualización |
| **Cobertura geográfica** | República de Guatemala, nivel municipio |
| **Clasificación de causa** | CIE-10 |
| **Licencia** | Datos públicos del Estado de Guatemala |

### Limitaciones y Advertencias

- **Barrera técnica de acceso:** El portal legacy está protegido por Radware Bot Manager (WAF). El acceso requiere simulación de navegador completo con Playwright, lo que hace la descarga frágil ante cambios en el portal INE.
- **Formato propietario (SAV/SPSS):** Los archivos originales son binarios propietarios de IBM SPSS. La conversión a Parquet vía `pyreadstat` introduce una dependencia de software; cualquier bug en la librería puede afectar la fidelidad del dato.
- **Metadatos del SAV no migrados:** Las etiquetas de valor y variable embebidas en el SAV de SPSS no se preservan automáticamente en Parquet; se depende del diccionario de Google Drive como fuente externa de decodificación.
- **Incompatibilidad de esquema con serie 2018-2024:** Las columnas del período legacy pueden diferir en nombre o tipo con las versiones modernas, lo que exige lógica de homologación en la capa Silver/Gold.

---

## 3. WHO / OMS — Global Health Observatory (GHO)

| Atributo | Detalle |
|---|---|
| **Institución** | Organización Mundial de la Salud (OMS / WHO) |
| **URL de la API** | `ghoapi.azureedge.net/api` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/oms/who_{indicador}_{país}.json` |
| **Tabla Databricks** | `bronze.json_oms` |
| **Formato** | JSON (protocolo OData) |
| **Años cubiertos** | Variable por indicador; rango aproximado 1990–2023 |
| **Archivos generados** | 15 archivos JSON (3 indicadores × 5 países) |
| **Volumen** | 1,708 registros |
| **Países** | GTM, CRI, HND, SLV, PAN (Centroamérica) |
| **Indicadores consultados** | Esperanza de vida al nacer, Mortalidad infantil (<5 años), Tasa de mortalidad |
| **Autenticación** | Ninguna (API pública) |
| **Frecuencia de actualización** | Anual — la OMS actualiza el GHO una vez por año |
| **Licencia** | CC BY-NC-SA 3.0 IGO (uso no comercial con atribución) |

### Limitaciones y Advertencias

- **Granularidad nacional únicamente:** La API del GHO provee datos a nivel país, no subnacional. No es posible cruzar con datos departamentales del INE sin metodología de desagregación adicional.
- **Intervalos de confianza amplios:** Los valores `low_value` y `high_value` reflejan incertidumbre estadística significativa, especialmente en países con sistemas de registro civil débiles.
- **Latencia de actualización:** Los datos más recientes suelen tener 1–2 años de rezago respecto al año corriente. El año 2024 puede no estar disponible hasta 2025-2026.
- **Dependencia de CDN (Azure):** La API usa Azure CDN (`azureedge.net`) como proxy. Interrupciones en este servicio afectan la ingesta aunque la fuente original de OMS esté disponible.
- **Formato OData:** El campo de datos útiles está anidado bajo la clave `value` en el JSON de respuesta; los cambios en la especificación OData de la OMS podrían romper la ingesta.
- **Licencia no comercial:** El uso de estos datos está restringido a fines académicos y de salud pública. No pueden redistribuirse con fines comerciales.

---

## 4. World Bank — Indicadores de Desarrollo Mundial

| Atributo | Detalle |
|---|---|
| **Institución** | Banco Mundial (World Bank) |
| **URL de la API** | `api.worldbank.org/v2/country` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/centroamerica/worldbank_{indicador}_centroamerica.json` |
| **Tabla Databricks** | `bronze.json_worldbank` |
| **Formato** | JSON (estructura propia del Banco Mundial) |
| **Años cubiertos** | 2010–2024 |
| **Archivos generados** | 5 archivos JSON (1 por indicador) |
| **Volumen** | 450 registros |
| **Países** | GTM, CRI, HND, SLV, PAN, NIC (Centroamérica) |
| **Indicadores** | Tasa bruta de mortalidad, mortalidad infantil, mortalidad materna, esperanza de vida, causas de muerte |
| **Autenticación** | Ninguna (API pública) |
| **Frecuencia de actualización** | Anual |
| **Licencia** | Creative Commons CC BY 4.0 |

### Limitaciones y Advertencias

- **Fuente alternativa:** Esta fuente reemplazó a CEPALSTAT (CEPAL), cuyo dominio `api.cepal.org` no fue resolvible durante la ejecución. El fallo quedó documentado en la tabla de auditoría (run_id 22, estado `FALLIDO`).
- **Datos derivados y estimados:** Los indicadores del Banco Mundial son en su mayoría estimaciones calculadas a partir de registros nacionales y ajustes metodológicos propios, no cifras de registro directo. El campo `obs_status` indica si el dato es estimado, real o proyectado.
- **Paginación de la API:** La respuesta JSON tiene estructura de array donde el índice 0 es metadata de paginación y el índice 1 son los datos. Cambios en esta estructura romperían la ingesta.
- **Cobertura limitada para años recientes:** Los datos de 2023 y 2024 suelen ser estimaciones preliminares que el Banco Mundial revisa retroactivamente.
- **Granularidad nacional:** Al igual que la OMS, los datos son únicamente a nivel país.

---

## 5. Google Drive — Diccionario de Variables INE

| Atributo | Detalle |
|---|---|
| **Institución** | Equipo del proyecto (fuente interna/complementaria) |
| **URL de origen** | Carpeta compartida de Google Drive, ID: `198lQfATsiCSEwJIaIlijq9N0vyVIdRq8` |
| **Ruta S3** | `s3://mortalidad-gtm-2026/raw/gdrive/diccionario_defunciones_ine.xlsx` |
| **Tabla Databricks** | `bronze.gdrive_docs` |
| **Tabla Sandbox** | `sandbox.sandbox_gdrive_diccionario` |
| **Formato** | Microsoft Excel (.xlsx) |
| **Volumen** | 1,837 registros (pares variable-código-etiqueta) |
| **Autenticación** | Ninguna (carpeta compartida públicamente vía URL de exportación) |
| **Licencia** | Uso interno del equipo |

### Limitaciones y Advertencias

- **Fuente no oficial:** Este diccionario es una compilación del equipo, no una publicación oficial del INE. Puede contener omisiones o interpretaciones.
- **Sin versionamiento formal:** El archivo en Drive puede ser editado sin control de versiones. La copia en S3 es la versión canónica para el pipeline.
- **Cobertura parcial de CIE-10:** El diccionario puede no incluir todos los códigos CIE-10 válidos, especialmente los de uso poco frecuente.
- **Dependencia de Drive:** Si la carpeta deja de ser pública o cambia de ID, la descarga automatizada falla.

---

## Resumen Consolidado

| # | Fuente | Institución | Formato | Años | Registros | Acceso |
|---|---|---|---|---|---|---|
| 1 | INE Defunciones 2018-2024 | INE Guatemala | Excel (.xlsx) | 2018–2024 | 674,064 | Público directo |
| 2 | INE Defunciones 2015-2017 | INE Guatemala | SAV/Parquet | 2015–2017 | 245,167 | Público (requiere Playwright) |
| 3 | WHO/OMS GHO | OMS | JSON (OData) | 1990–2023 aprox. | 1,708 | API pública |
| 4 | World Bank | Banco Mundial | JSON | 2010–2024 | 450 | API pública |
| 5 | Diccionario INE | Equipo (interno) | Excel (.xlsx) | N/A | 1,837 | Google Drive compartido |
| | **TOTAL** | | | | **923,226** | |

---

## Matriz de Riesgos de Disponibilidad

| Fuente | Riesgo de Discontinuidad | Mitigación en Pipeline |
|---|---|---|
| INE 2018-2024 | Bajo — portal estable, descarga directa | Copia persistida en S3 y NAS |
| INE 2015-2017 | Alto — portal legacy + WAF Radware | Archivos SAV y Parquet ya en S3; re-descarga frágil |
| OMS GHO | Medio — dependencia de CDN Azure | 15 archivos JSON en S3; re-ingesta por indicador |
| Banco Mundial | Bajo — API robusta y versionada | 5 archivos JSON en S3 |
| Diccionario Drive | Medio — sin control de versiones | Excel en S3 es la copia canónica |

---

*Documento generado como parte de la capa de Gobernanza — Fase 1. Actualizar para Fase 2 cuando se incorporen nuevas fuentes en la capa Data Warehouse.*
