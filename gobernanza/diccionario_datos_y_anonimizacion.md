# Diccionario de Datos y Plan de Anonimización/Agregación
## Plataforma Analítica de Mortalidad — Seminario de Sistemas 2 | USAC 2026

**Elaborado por:** Grupo 3  
**Fecha:** 2026-06-14  
**Versión:** 1.0  
**Capa documentada:** Sandbox (Raw) — PostgreSQL, esquema `sandbox`

---

## Parte I — Diccionario de Datos

### Convenciones de Lectura

| Símbolo | Significado |
|---|---|
| `PK` | Llave primaria (Primary Key) |
| `[LINAJE]` | Columna de metadatos de trazabilidad, no dato de dominio |
| `[SENSIBLE]` | Columna que contiene o permite inferir información personal o privada |
| `[CRITICA]` | Columna esencial para los análisis principales del proyecto |
| `NULL` | El campo puede estar vacío legítimamente (diseño "Cero Destrucción") |

---

### Tabla 1: `sandbox.sandbox_ine_defunciones`

**Descripción:** Tabla transaccional principal. Contiene el registro completo de defunciones reportadas al INE Guatemala para el período 2015–2024. Cada fila representa un fallecimiento individual con sus atributos demográficos, geográficos y de causa de muerte. Es la base de todos los análisis de mortalidad del proyecto.

**Fuente origen:** INE Guatemala — Estadísticas Vitales  
**Volumen:** 921,208 registros  
**Filas en Databricks (`bronze.xlsx_ine` + `bronze.sav_ine_legacy`):** 919,231 (diferencia por metadatos de ingesta)

| Nombre de Columna | Tipo | Etiqueta Legible | Descripción | Valores / Dominio | Banderas |
|---|---|---|---|---|---|
| `id_sandbox` | SERIAL | ID de Ingesta | Identificador único asignado durante la carga. No proviene del INE. | Entero autoincremental | `PK` `[LINAJE]` |
| `fuente_archivo` | VARCHAR(100) | Archivo de Origen | Ruta exacta en S3 del archivo que originó esta fila. Ej: `raw/ine/defunciones_2018.xlsx` | Cadena de texto | `[LINAJE]` |
| `fecha_carga` | TIMESTAMP | Fecha de Carga | Marca de tiempo exacta de inserción en la base de datos Sandbox. | UTC | `[LINAJE]` |
| `depreg` | NUMERIC(4,0) | Departamento de Registro | Código del departamento donde se registró legalmente la defunción. Ver `sandbox_gdrive_diccionario` para la etiqueta. | 1–22 (departamentos de Guatemala) | NULL |
| `mupreg` | VARCHAR(10) | Municipio de Registro | Código del municipio de registro legal. | Código numérico del INE | NULL `[SENSIBLE]` |
| `mesreg` | NUMERIC(2,0) | Mes de Registro | Mes calendario del registro legal. | 1–12 | NULL |
| `anoreg` | NUMERIC(4,0) | Año de Registro | Año del registro legal ante el registro civil. | 2015–2024 | NULL |
| `depocu` | NUMERIC(4,0) | Departamento de Ocurrencia | Código del departamento donde físicamente ocurrió la muerte. **Variable geográfica principal para análisis.** | 1–22 | `[CRITICA]` NULL |
| `mupocu` | VARCHAR(10) | Municipio de Ocurrencia | Código del municipio donde ocurrió la muerte. Granularidad más alta disponible. | Código numérico del INE | `[CRITICA]` `[SENSIBLE]` NULL |
| `diaocu` | NUMERIC(2,0) | Día de Ocurrencia | Día calendario del fallecimiento. | 1–31 | `[SENSIBLE]` NULL |
| `mesocu` | NUMERIC(2,0) | Mes de Ocurrencia | Mes calendario del fallecimiento. | 1–12 | NULL |
| `anoocu` | NUMERIC(4,0) | Año de Ocurrencia | Año exacto del fallecimiento. Variable temporal primaria para series de tiempo. | 2015–2024 | `[CRITICA]` NULL |
| `areag` | NUMERIC(1,0) | Área Geográfica | Clasificación del área de ocurrencia. | 1=Urbano, 2=Rural | NULL |
| `sexo` | NUMERIC(1,0) | Sexo | Sexo biológico registrado del fallecido. | 1=Hombre, 2=Mujer, 9=Ignorado | `[CRITICA]` NULL |
| `edadif` | NUMERIC(3,0) | Edad del Fallecido | Edad en años cumplidos al momento del fallecimiento. Para menores de 1 año, el INE puede usar codificaciones especiales. | 0–120 (años) | `[CRITICA]` `[SENSIBLE]` NULL |
| `perdif` | NUMERIC(1,0) | Pertenencia Étnica | Grupo étnico autodeclarado o registrado. | 1=Maya, 2=Garífuna, 3=Xinca, 4=Mestizo/Ladino, 5=Otro | `[SENSIBLE]` NULL |
| `puedif` | NUMERIC(4,0) | Pueblo de Pertenencia | Pueblo específico dentro del grupo étnico (ej. pueblo K'iche', Mam). Desagregación de `perdif`. | Catálogo INE (~30 pueblos) | `[SENSIBLE]` NULL |
| `ecidif` | NUMERIC(1,0) | Estado Civil | Estado civil del fallecido al momento de la defunción. | 1=Soltero, 2=Casado, 3=Unido, 4=Viudo, 5=Divorciado, 9=Ignorado | NULL |
| `escodif` | NUMERIC(2,0) | Nivel de Escolaridad | Último nivel educativo alcanzado por el fallecido. | 0=Ninguno, 1=Pre-primaria, 2=Primaria, 3=Básico, 4=Diversificado, 5=Superior, 9=Ignorado | NULL |
| `ciuodif` | VARCHAR(10) | Ocupación | Código de la ocupación o profesión del fallecido. Alta tasa de nulos. | Clasificación CIUO del INE | `[SENSIBLE]` NULL |
| `pnadif` | NUMERIC(4,0) | País de Nacimiento | Código ISO del país de nacimiento del fallecido. | Códigos de país del INE | NULL |
| `dnadif` | NUMERIC(4,0) | Departamento de Nacimiento | Departamento guatemalteco de nacimiento (aplica solo si `pnadif` = Guatemala). | 1–22 | NULL |
| `mnadif` | VARCHAR(10) | Municipio de Nacimiento | Municipio de nacimiento. | Código numérico del INE | `[SENSIBLE]` NULL |
| `nacdif` | NUMERIC(4,0) | Nacionalidad | Nacionalidad legal registrada del fallecido. | Códigos de país/nacionalidad del INE | NULL |
| `predif` | NUMERIC(4,0) | País de Residencia | País de residencia habitual del fallecido. | Códigos de país | NULL |
| `dredif` | NUMERIC(4,0) | Departamento de Residencia | Departamento de residencia habitual en Guatemala. | 1–22 | `[SENSIBLE]` NULL |
| `mredif` | VARCHAR(10) | Municipio de Residencia | Municipio de residencia habitual. Combinado con `dredif`, permite reconstruir la ubicación de residencia. | Código numérico del INE | `[SENSIBLE]` NULL |
| `caudef` | VARCHAR(10) | Causa de Defunción (CIE-10) | **Columna más crítica del dataset.** Código de causa de muerte según la CIE-10. Ej: I219=Infarto agudo de miocardio, J18=Neumonía, X95=Agresión por arma. | Códigos CIE-10 (A00–Z99) | `[CRITICA]` NULL |
| `asist` | NUMERIC(1,0) | Asistencia Médica | Tipo de asistencia médica recibida antes del fallecimiento. | 1=Con asistencia, 2=Sin asistencia, 3=En tránsito, 9=Ignorado | NULL |
| `ocur` | NUMERIC(1,0) | Lugar de Ocurrencia | Tipo de establecimiento o lugar donde ocurrió la muerte. | 1=Hospital público, 2=IGSS, 3=Clínica privada, 4=Domicilio, 5=Vía pública, 9=Otro | NULL |
| `cerdef` | NUMERIC(1,0) | Tipo de Certificador | Quién certificó oficialmente la defunción. | 1=Médico tratante, 2=Médico forense, 3=Autoridad local, 4=Comadronas, 9=Otro | NULL |

---

### Tabla 2: `sandbox.sandbox_oms_indicadores`

**Descripción:** Indicadores de salud a nivel país extraídos de la API del Global Health Observatory (GHO) de la OMS. Cubre principalmente métricas de esperanza de vida y mortalidad para cinco países centroamericanos. No contiene datos individuales — es estadística agregada oficial.

**Fuente origen:** WHO/OMS GHO API  
**Volumen:** 1,708 registros  
**Granularidad:** País × Indicador × Año × Sexo

| Nombre de Columna | Tipo | Etiqueta Legible | Descripción | Valores / Dominio | Banderas |
|---|---|---|---|---|---|
| `id_sandbox` | SERIAL | ID de Ingesta | Identificador único de ingesta. | Autoincremental | `PK` `[LINAJE]` |
| `fuente_archivo` | VARCHAR(100) | Archivo JSON Origen | Nombre del archivo JSON de S3. Incluye indicador y país. | Ej: `who_life_expectancy_gtm.json` | `[LINAJE]` |
| `fecha_carga` | TIMESTAMP | Fecha de Carga | Momento de inserción en Sandbox. | UTC | `[LINAJE]` |
| `id_oms` | BIGINT | ID Registro OMS | Identificador primario del registro en la base de datos interna de la OMS. Útil para trazabilidad. | Entero largo | NULL |
| `indicator_code` | VARCHAR(50) | Código de Indicador | Código alfanumérico que identifica el indicador de salud en el catálogo GHO. | Ej: `WHOSIS_000001` (esperanza de vida) | `[CRITICA]` |
| `spatial_dim_type` | VARCHAR(20) | Tipo Dimensión Espacial | Nivel de desagregación geográfica. En este dataset siempre es "COUNTRY". | `COUNTRY` | NULL |
| `spatial_dim` | VARCHAR(10) | Código País (ISO-3) | Código ISO 3166-1 alpha-3 del país. **Llave de cruce con Banco Mundial.** | GTM, CRI, HND, SLV, PAN | `[CRITICA]` |
| `parent_location_code` | VARCHAR(10) | Código Región OMS | Código de la región OMS a la que pertenece el país. | `AMR` (Américas) | NULL |
| `parent_location` | VARCHAR(50) | Nombre Región OMS | Nombre descriptivo de la región OMS. | "Americas" | NULL |
| `time_dim_type` | VARCHAR(20) | Tipo Dimensión Temporal | Granularidad temporal. En este dataset siempre es "YEAR". | `YEAR` | NULL |
| `time_dim` | INTEGER | Año de Medición | Año de la medición estadística. **Llave temporal principal.** | 1990–2023 aprox. | `[CRITICA]` |
| `dim1_type` | VARCHAR(30) | Tipo Sub-Dimensión 1 | Primera categoría de desagregación. Generalmente es "SEX". | `SEX` | NULL |
| `dim1` | VARCHAR(30) | Valor Sub-Dimensión 1 | Valor de la desagregación por sexo. | `Male`, `Female`, `Both sexes` | NULL |
| `dim2_type` | VARCHAR(30) | Tipo Sub-Dimensión 2 | Segunda categoría de desagregación (cuando aplica). | Variable según indicador | NULL |
| `dim2` | VARCHAR(50) | Valor Sub-Dimensión 2 | Valor de la segunda desagregación. | Variable | NULL |
| `value_text` | VARCHAR(50) | Valor Texto | Valor del indicador tal como lo entrega la API, en formato cadena. Puede incluir rangos o notas. | Cadena | NULL |
| `numeric_value` | NUMERIC | **Valor Numérico** | Valor numérico del indicador para cálculos analíticos. **Columna de análisis principal.** | Real positivo | `[CRITICA]` NULL |
| `low_value` | NUMERIC | Límite Inferior IC | Límite inferior del intervalo de confianza estadístico de la OMS. | Real positivo | NULL |
| `high_value` | NUMERIC | Límite Superior IC | Límite superior del intervalo de confianza estadístico de la OMS. | Real positivo | NULL |
| `date_registro` | VARCHAR(50) | Fecha de Publicación OMS | Fecha en que la OMS publicó o actualizó esta métrica. | Cadena ISO 8601 | NULL |
| `time_dimension_value` | VARCHAR(10) | Período (Texto) | Representación textual del período de medición. | Ej: "2019" | NULL |
| `time_dimension_begin` | VARCHAR(50) | Inicio de Cobertura | Fecha de inicio exacta de la cobertura temporal de la métrica. | Cadena ISO 8601 | NULL |
| `time_dimension_end` | VARCHAR(50) | Fin de Cobertura | Fecha de fin exacta de la cobertura temporal de la métrica. | Cadena ISO 8601 | NULL |

---

### Tabla 3: `sandbox.sandbox_worldbank_indicadores`

**Descripción:** Indicadores macroeconómicos y de salud del Banco Mundial para seis países centroamericanos, período 2010–2024. Datos agregados a nivel país, ideales para contextualizar los datos individuales del INE con tendencias regionales.

**Fuente origen:** World Bank API  
**Volumen:** 450 registros  
**Granularidad:** País × Indicador × Año

| Nombre de Columna | Tipo | Etiqueta Legible | Descripción | Valores / Dominio | Banderas |
|---|---|---|---|---|---|
| `id_sandbox` | SERIAL | ID de Ingesta | Identificador único de ingesta. | Autoincremental | `PK` `[LINAJE]` |
| `fuente_archivo` | VARCHAR(100) | Archivo JSON Origen | Ruta del archivo en S3. | Ej: `worldbank_crude_death_rate_centroamerica.json` | `[LINAJE]` |
| `fecha_carga` | TIMESTAMP | Fecha de Carga | Momento de inserción en Sandbox. | UTC | `[LINAJE]` |
| `indicator_id` | VARCHAR(50) | Código Indicador BM | Código técnico único del indicador en el catálogo del Banco Mundial. | Ej: `SP.DYN.CDRT.IN`=Tasa Bruta de Mortalidad, `SP.DYN.IMRT.IN`=Mortalidad infantil | `[CRITICA]` |
| `indicator_value` | VARCHAR(200) | Nombre del Indicador | Nombre completo y descriptivo del indicador en inglés. | Texto libre | NULL |
| `country_id` | VARCHAR(5) | Código País (BM) | Código interno del Banco Mundial para el país (2 caracteres). | GT, CR, HN, SV, PA, NI | NULL |
| `country_value` | VARCHAR(50) | Nombre del País | Nombre oficial del país en inglés según el Banco Mundial. | Guatemala, Costa Rica, Honduras, El Salvador, Panama, Nicaragua | NULL |
| `countryiso3code` | VARCHAR(5) | Código País ISO-3 | Código estándar ISO 3166-1 alpha-3. **Llave de cruce con OMS.** | GTM, CRI, HND, SLV, PAN, NIC | `[CRITICA]` |
| `date_year` | VARCHAR(10) | Año de Medición | Año de la medición. Almacenado como VARCHAR por la estructura de la API. | 2010–2024 | `[CRITICA]` |
| `value` | NUMERIC | **Valor del Indicador** | Valor numérico del indicador (tasa, porcentaje o número bruto). **Columna de análisis principal.** | Real (puede ser NULL si el BM no tiene dato para ese año-país) | `[CRITICA]` NULL |
| `unit` | VARCHAR(20) | Unidad de Medida | Unidad del indicador cuando el BM la especifica. Frecuentemente vacío. | Texto o vacío | NULL |
| `obs_status` | VARCHAR(10) | Estado de Observación | Indica si el dato es una observación real, estimación o proyección. | Vacío=dato real, `E`=estimado, `P`=preliminar | NULL |
| `decimal_places` | INTEGER | Decimales | Precisión de decimales definida por el Banco Mundial para esa métrica. | 0–4 | NULL |

---

### Tabla 4: `sandbox.sandbox_gdrive_diccionario`

**Descripción:** Catálogo maestro de decodificación de variables del INE. Cada fila relaciona un código numérico de una columna de `sandbox_ine_defunciones` con su etiqueta legible por humanos. Es el "rosetta stone" del dataset: sin esta tabla, los datos del INE son ininterpretables.

**Fuente origen:** Diccionario elaborado por el equipo, subido en Google Drive  
**Volumen:** 1,837 registros

| Nombre de Columna | Tipo | Etiqueta Legible | Descripción | Valores / Dominio | Banderas |
|---|---|---|---|---|---|
| `id_sandbox` | SERIAL | ID de Ingesta | Identificador único de ingesta. | Autoincremental | `PK` `[LINAJE]` |
| `fuente_archivo` | VARCHAR(100) | Archivo de Origen | Nombre del Excel en S3. | `raw/gdrive/diccionario_defunciones_ine.xlsx` | `[LINAJE]` |
| `fecha_carga` | TIMESTAMP | Fecha de Carga | Momento de inserción en Sandbox. | UTC | `[LINAJE]` |
| `variable` | VARCHAR(200) | Nombre de Variable | Nombre exacto de la columna en `sandbox_ine_defunciones` a la que aplica este catálogo. | Ej: `depocu`, `sexo`, `caudef` | `[CRITICA]` |
| `codigo` | VARCHAR(50) | Código Crudo | Valor numérico o alfanumérico tal como aparece en la tabla del INE. VARCHAR para soportar CIE-10. | Ej: `1`, `2`, `I219` | `[CRITICA]` |
| `etiqueta` | VARCHAR(200) | Etiqueta Descriptiva | Significado real del código en lenguaje natural. | Ej: `Guatemala`, `Hombre`, `Infarto agudo de miocardio` | `[CRITICA]` |

---

### Tabla 5: `sandbox.sandbox_log_carga`

**Descripción:** Tabla de auditoría operativa. Registra cada evento de carga del pipeline de ingesta, permitiendo trazabilidad completa del proceso ETL y diagnóstico de fallos. Es la evidencia de calidad del proceso de ingeniería de datos.

**Fuente origen:** Generada automáticamente por el script Python de ingesta  
**Volumen:** Variable (crece con cada ejecución)

| Nombre de Columna | Tipo | Etiqueta Legible | Descripción | Valores / Dominio | Banderas |
|---|---|---|---|---|---|
| `id_log` | SERIAL | ID de Evento | Identificador del evento de carga. | Autoincremental | `PK` |
| `fecha_inicio` | TIMESTAMP | Inicio de Carga | Hora exacta de inicio de la ingesta de un archivo. | UTC | |
| `fecha_fin` | TIMESTAMP | Fin de Carga | Hora exacta de fin del bloque de carga. | UTC | NULL |
| `fuente_archivo` | VARCHAR(100) | Archivo Procesado | Ruta S3 del archivo procesado en este evento. | Cadena de texto | |
| `tabla_destino` | VARCHAR(100) | Tabla Destino | Nombre de la tabla Sandbox que recibió los datos. | `sandbox_ine_defunciones`, `sandbox_oms_indicadores`, etc. | |
| `filas_insertadas` | INTEGER | Filas Insertadas | Conteo exacto de registros inyectados en esta operación. Herramienta de auditoría de volumetría. | Entero positivo | NULL |
| `estado` | VARCHAR(20) | Estado | Resultado final de la operación de carga. | `EXITO`, `ERROR`, `OMITIDO` | |
| `mensaje_error` | TEXT | Mensaje de Error | Traza técnica del error si el estado es `ERROR`. Incluye errores de conexión S3, formato de archivo, timeouts. | Texto o NULL | NULL |
| `script_version` | VARCHAR(20) | Versión del Script | Versión del script Python que realizó la carga. Permite correlacionar cambios de código con comportamientos. | Semver (Ej: `1.2.0`) | NULL |

---

## Parte II — Plan de Anonimización y Agregación

### Marco Ético y Legal

Los datos del INE en la capa Sandbox contienen información individual sobre personas fallecidas, incluyendo atributos demográficos sensibles como edad exacta, causa de muerte, etnia, municipio de residencia y ocupación. Aunque las personas ya fallecieron, la normativa de protección de datos y las mejores prácticas de salud pública exigen que los análisis se realicen sobre datos agregados o anonimizados para:

1. **Proteger la privacidad de los deudos** y evitar la identificación de familias por combinación de atributos.
2. **Prevenir la estigmatización** de grupos étnicos o comunidades basándose en causas de muerte específicas.
3. **Cumplir con el principio de proporcionalidad:** usar solo el nivel de detalle necesario para el análisis.

> **Regla de Oro:** El dato crudo en Sandbox es **inmutable e inaccesible** para usuarios finales. Todo acceso analítico ocurre exclusivamente sobre la capa Silver/Gold del Data Warehouse, donde las transformaciones de privacidad ya han sido aplicadas.

---

### Clasificación de Sensibilidad por Columna

| Columna | Tabla | Nivel de Sensibilidad | Justificación |
|---|---|---|---|
| `edadif` | ine_defunciones | **ALTO** | Edad exacta individual; combinada con otros atributos permite reidentificación |
| `mupocu` | ine_defunciones | **ALTO** | Municipio de ocurrencia en comunidades pequeñas (<100 hab.) puede identificar al fallecido |
| `mupreg` | ine_defunciones | **ALTO** | Ídem municipio de ocurrencia |
| `mredif` | ine_defunciones | **ALTO** | Municipio de residencia habitual — dato de localización |
| `mnadif` | ine_defunciones | **ALTO** | Municipio de nacimiento |
| `perdif` / `puedif` | ine_defunciones | **ALTO** | Etnia; dato protegido por derechos de pueblos indígenas |
| `caudef` | ine_defunciones | **ALTO** | Causa exacta CIE-10; estigmatizante si se cruza con etnia o localidad |
| `diaocu` | ine_defunciones | **MEDIO** | Día exacto; redundante para análisis de tendencias |
| `ciuodif` | ine_defunciones | **MEDIO** | Ocupación; puede usarse para análisis socioeconómico pero es dato personal |
| `sexo` | ine_defunciones | **BAJO** | Variable necesaria para análisis epidemiológico; no identificante por sí sola |
| `anoocu` | ine_defunciones | **BAJO** | Año necesario para series de tiempo; no identificante |
| `depocu` | ine_defunciones | **BAJO** | Departamento; granularidad suficientemente agregada |
| `numeric_value` | oms_indicadores | **NINGUNO** | Dato agregado nacional; no contiene información individual |
| `value` | worldbank_indicadores | **NINGUNO** | Dato agregado nacional; no contiene información individual |

---

### Técnicas de Anonimización Aplicables

#### Técnica 1: Generalización (Edad)

**Columna afectada:** `edadif`  
**Problema:** La edad exacta en años permite, combinada con causa de muerte y municipio, identificar a individuos en comunidades pequeñas.  
**Solución:** Reemplazar la edad exacta por un rango etario estándar de salud pública.

```sql
-- Vista en capa Silver/Gold (ejemplo)
CASE
    WHEN edadif < 1   THEN '<1 año'
    WHEN edadif < 5   THEN '1-4 años'
    WHEN edadif < 15  THEN '5-14 años'
    WHEN edadif < 25  THEN '15-24 años'
    WHEN edadif < 45  THEN '25-44 años'
    WHEN edadif < 65  THEN '45-64 años'
    WHEN edadif >= 65 THEN '65+ años'
    ELSE 'No especificado'
END AS grupo_edad
```

**Grupos:** <1 año, 1-4, 5-14, 15-24, 25-44, 45-64, 65+  
**Justificación:** Estándar de la OMS y OPS para reportes de mortalidad; permite cálculo de mortalidad infantil, adulta y en edad productiva.

---

#### Técnica 2: Supresión de Localidades Pequeñas (k-anonimato geográfico)

**Columnas afectadas:** `mupocu`, `mupreg`, `mredif`, `mnadif`  
**Problema:** En municipios con pocos fallecidos (< k registros), la combinación municipio + causa + etnia puede identificar a una persona concreta.  
**Solución:** Aplicar umbral mínimo de k=5. Si un municipio tiene menos de 5 fallecimientos en un año para una combinación de atributos, suprimir o elevar al nivel departamento.

```sql
-- Regla de supresión geográfica
CASE
    WHEN COUNT(*) OVER (PARTITION BY mupocu, anoocu) < 5
    THEN depocu::VARCHAR || '-SUPRIMIDO'
    ELSE mupocu
END AS municipio_anonimizado
```

**Umbral recomendado:** k=5 (ajustable a k=10 para conjuntos más conservadores).

---

#### Técnica 3: Generalización de Causa de Muerte (CIE-10 → Capítulo)

**Columna afectada:** `caudef`  
**Problema:** El código CIE-10 a 3–4 caracteres es extremadamente específico. Cruzado con etnia y municipio, puede ser estigmatizante o identificante.  
**Solución:** Elevar la causa al nivel de Capítulo CIE-10 (categoría de letra) para el dataset público; mantener código completo solo en vistas restringidas para epidemiólogos.

| Nivel | Ejemplo | Uso recomendado |
|---|---|---|
| Código completo (4 chars) | `I219` = Infarto de miocardio STEMI | Interno — solo investigadores con acceso restringido |
| Categoría (3 chars) | `I21` = Infarto agudo de miocardio | Analistas con acceso Silver |
| Bloque (letra + rango) | `I20-I25` = Enfermedades isquémicas del corazón | Dataset público |
| Capítulo (letra) | `I` = Enfermedades del sistema circulatorio | Dashboard público general |

```sql
-- Generalización a Capítulo CIE-10
LEFT(caudef, 1) AS capitulo_cie10
```

---

#### Técnica 4: Enmascaramiento de Etnia en Localidades Pequeñas

**Columnas afectadas:** `perdif`, `puedif`  
**Problema:** La etnia es un dato protegido internacionalmente (Convenio 169 OIT). En municipios con mayoría étnica conocida, revelar la etnia junto con causa de muerte puede usarse para discriminación.  
**Solución:** Aplicar el mismo umbral de k-anonimato geográfico. Si el conteo por grupo étnico en un municipio-año es < k=5, sustituir por "No especificado".

---

#### Técnica 5: Eliminación de Variables No Analíticas con Riesgo Alto

**Columnas candidatas a eliminar en capa Silver/Gold:**
- `diaocu` — El día exacto no aporta a análisis de tendencias; solo mes y año son necesarios.
- `ciuodif` — Alta tasa de nulos y riesgo de reidentificación; usar solo si el análisis lo requiere explícitamente.
- `pnadif`, `nacdif` — País de nacimiento/nacionalidad irrelevante para mayoría de análisis y permite cruce identificante.

---

### Arquitectura del Plan de Anonimización por Capa

```
┌─────────────────────────────────────────────────────────────────┐
│  CAPA SANDBOX (Raw)                                             │
│  PostgreSQL: schema sandbox                                     │
│  • Datos crudos originales, sin transformar                     │
│  • Acceso: SOLO ingeniería de datos (acceso técnico)            │
│  • Retención: Indefinida (regla de Cero Destrucción)            │
└─────────────────┬───────────────────────────────────────────────┘
                  │  Transformaciones ETL (Fase 2)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPA SILVER (Analítica Restringida)                            │
│  PostgreSQL/Databricks: schema silver                           │
│  • Generalización de edad (rangos etarios)                      │
│  • CIE-10 a nivel categoría (3 chars)                           │
│  • Etnia con k-anonimato (k≥5)                                  │
│  • Geografía a nivel municipio (con supresión k<5)              │
│  • Acceso: Analistas e investigadores autorizados               │
└─────────────────┬───────────────────────────────────────────────┘
                  │  Agregación adicional
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPA GOLD (Dashboard Público)                                  │
│  PostgreSQL/Databricks: schema gold                             │
│  • Datos solo a nivel departamento o nacional                   │
│  • Causa de muerte a nivel Capítulo CIE-10 (letra)              │
│  • Sin variables de etnia a nivel individual                    │
│  • Conteos con supresión si < 5 en cualquier celda              │
│  • Acceso: Público general, dashboards, reportes                │
└─────────────────────────────────────────────────────────────────┘
```

---

### Mecanismo de Implementación: Vistas SQL

Las transformaciones de anonimización se implementarán mediante **Vistas SQL** y **transformaciones ETL** al pasar del Sandbox al Data Warehouse (Fase 2). El dato crudo permanece inmutable.

**Ejemplo de vista Silver para `sandbox_ine_defunciones`:**

```sql
CREATE OR REPLACE VIEW silver.vw_defunciones_anon AS
SELECT
    -- Linaje (no identificante)
    fuente_archivo,
    DATE_TRUNC('month', fecha_carga) AS mes_carga,

    -- Geografía (departamento siempre, municipio con supresión)
    depocu,
    CASE
        WHEN COUNT(*) OVER (PARTITION BY mupocu, anoocu) < 5
        THEN NULL
        ELSE mupocu
    END AS mupocu_anon,
    areag,

    -- Tiempo (año y mes; no día)
    anoocu,
    mesocu,

    -- Demografía (generalizada)
    sexo,
    CASE
        WHEN edadif < 1   THEN 0   -- Menos de 1 año
        WHEN edadif < 5   THEN 1   -- 1-4 años
        WHEN edadif < 15  THEN 2   -- 5-14 años
        WHEN edadif < 25  THEN 3   -- 15-24 años
        WHEN edadif < 45  THEN 4   -- 25-44 años
        WHEN edadif < 65  THEN 5   -- 45-64 años
        ELSE 6                     -- 65+ años
    END AS grupo_edad_id,

    -- Etnia (con k-anonimato)
    CASE
        WHEN COUNT(*) OVER (PARTITION BY perdif, mupocu, anoocu) < 5
        THEN NULL
        ELSE perdif
    END AS perdif_anon,

    -- Causa (categoría CIE-10, 3 chars)
    SUBSTRING(caudef, 1, 3) AS caudef_categoria,

    -- Contexto clínico
    asist,
    ocur
FROM sandbox.sandbox_ine_defunciones;
```

---

### Tabla de Decisiones de Anonimización (Resumen)

| Columna | Acción en Silver | Acción en Gold | Técnica |
|---|---|---|---|
| `edadif` | Reemplazar por `grupo_edad_id` (7 rangos) | Mismo rango | Generalización |
| `diaocu` | **Eliminar** | **Eliminar** | Supresión de variable |
| `mupocu` / `mupreg` | Mantener si k≥5; NULL si k<5 | **Eliminar** (solo depto.) | k-anonimato |
| `mredif` / `mnadif` | **Eliminar** | **Eliminar** | Supresión de variable |
| `perdif` | Mantener si k≥5 por municipio; NULL si k<5 | **Eliminar** | k-anonimato |
| `puedif` | **Eliminar** | **Eliminar** | Supresión de variable |
| `caudef` | Truncar a 3 chars (categoría CIE-10) | Truncar a 1 char (capítulo) | Generalización |
| `ciuodif` | **Eliminar** | **Eliminar** | Supresión de variable |
| `pnadif` / `nacdif` | **Eliminar** | **Eliminar** | Supresión de variable |
| `sexo` | Mantener | Mantener | Sin cambio |
| `anoocu` / `mesocu` | Mantener | Mantener | Sin cambio |
| `depocu` | Mantener | Mantener | Sin cambio |
| `asist` / `ocur` | Mantener | Mantener | Sin cambio |
| `ecidif` / `escodif` | Mantener | **Eliminar** | Supresión en Gold |

---

### Criterios de Acceso por Perfil de Usuario

| Perfil | Capa Accesible | Justificación |
|---|---|---|
| Ingeniero de datos (equipo) | Sandbox + Silver + Gold | Necesita acceso completo para ETL y debugging |
| Epidemiólogo / Investigador | Silver + Gold | Requiere causa detallada pero no dato individual crudo |
| Analista de políticas públicas | Gold | Solo necesita tendencias agregadas por departamento |
| Público general / Dashboard | Gold (vistas curadas) | Solo cifras consolidadas sin posibilidad de reidentificación |

---

*Este documento es el insumo para la documentación MkDocs de Fase 2. Las vistas SQL del plan de anonimización se implementarán durante el paso Sandbox → Silver del Data Warehouse.*
