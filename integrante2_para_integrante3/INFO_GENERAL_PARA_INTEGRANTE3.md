###  Handoff Técnico Detallado: Arquitectura y Datos Capa Sandbox (Fase 1)

**De:** Integrante 2 (Ingeniería de Datos / Modelado)
**Para:** Integrante 3 (Gobernanza, Diccionario de Datos y Documentación MkDocs)

Hola equipo. A continuación detallo las especificaciones técnicas, decisiones de arquitectura y perfilado de datos de la carga masiva en nuestra zona de aterrizaje (Sandbox). Esta información es el insumo directo para el Diccionario de Datos, el esquema de Data Lineage y el Plan de Gobernanza.

---

#### 1. Arquitectura de Ingesta y Almacenamiento

* **Motor de Base de Datos:** PostgreSQL 15 (Alpine) desplegado vía Docker.
* **Base de datos y Esquema:** `mortalidad_gtm_db`, esquema `sandbox`.
* **Modelo Relacional:** **Aislado (Sin Foreign Keys).** Por definición arquitectónica, la capa *Raw/Sandbox* no cuenta con integridad referencial (relaciones entre tablas) para permitir ingestas masivas ultrarrápidas y evitar bloqueos. El modelo estrella se construirá en la Fase 2 (Data Warehouse).
* **Método de Carga:** Extracción ELT desde AWS S3 vía Python (`boto3` y `pandas`), generando un único artefacto DDL/DML (`sandbox_setup.sql`) que utiliza el comando nativo `COPY FROM STDIN` de PostgreSQL.
* **Tolerancia a fallos:** Se implementaron reintentos automáticos (max 3 intentos, timeout de 120s) para mitigar latencias de red en S3 (específicamente con archivos pesados como `defunciones_2018.xlsx`).

#### 2. Volumetría Exacta y Orígenes (Corte Fase 1)

Se procesaron un total de **34 archivos** desde el bucket S3, consolidando **923,226 registros** sin pérdida de datos.

* **INE (Mortalidad GTM):** 3 archivos Parquet y 7 archivos Excel.
* **OMS (Esperanza de vida/Mortalidad infantil):** 15 archivos JSON.
* **Banco Mundial (Indicadores Macro CA):** 5 archivos JSON.
* **Google Drive (Diccionarios):** 1 archivo Excel.

#### 3. Estructura para el Diccionario de Datos

Se crearon 5 entidades físicas. Aquí tienes el propósito y la estructura clave para tu documentación:

1. `sandbox_ine_defunciones`: Tabla transaccional core. Contiene 921,208 registros de defunciones. Columnas críticas: `depocu` (Depto. Ocurrencia), `anoreg` (Año registro), `sexo`, `edadif` (Edad), `caudef` (Causa defunción CIE-10).
2. `sandbox_oms_indicadores`: Datos de la OMS. Contiene las métricas espaciales (`spatial_dim`), temporales (`time_dim`) y los valores numéricos (`numeric_value`, `low_value`, `high_value`) de salud.
3. `sandbox_worldbank_indicadores`: Datos macro del Banco Mundial. Clasificados por país (`countryiso3code`), año (`date_year`) y tipo de indicador (`indicator_id`).
4. `sandbox_gdrive_diccionario`: Catálogo maestro para decodificar el INE. Contiene `variable`, `codigo` y `etiqueta`.
5. `sandbox_log_carga`: Tabla de auditoría. Registra `fecha_inicio`, `tabla_destino`, `filas_insertadas` y `estado` de cada lote procesado.

#### 4. Data Lineage (Procedencia y Trazabilidad)

Para cumplir con la política de linaje de datos exigida, el script de ingesta inyectó **metadatos de procedencia** en la cabecera de todas las filas de todas las tablas. Tu diagrama de linaje en MkDocs debe reflejar que cada registro cuenta con:

* `id_sandbox` (SERIAL): Identificador único de ingesta.
* `fuente_archivo` (VARCHAR): La ruta exacta del S3 (Ej. `raw/ine/defunciones_2016.parquet`).
* `fecha_carga` (TIMESTAMP): Marca de tiempo exacta de cuando el registro tocó la base de datos local.

#### 5. Gobernanza, Calidad de Datos (DQ) y Regla de Cero Destrucción

Para tu reporte de políticas de datos, estas fueron las reglas de transformación aplicadas en memoria antes del aterrizaje:

* **Estandarización de Nomenclatura:** Todos los nombres de columnas se forzaron a minúsculas, sin espacios y sin caracteres especiales (ej. "Añoreg" pasó a `anoreg`).
* **Manejo de Asimetrías (Cero Destrucción):** Descubrimos que los esquemas del INE variaban por año (unos tenían 25 columnas, otros 28). Para no destruir ni perder datos, se consolidó un "Súper Esquema" de más de 30 columnas. Si un año carecía de una variable, la celda se rellenó con `NULL` lógico. **No se eliminó ninguna fila.**

#### 6. Notas para el Plan Ético y de Anonimización

**Atención aquí:** Actualmente, el esquema `sandbox` contiene **datos sensibles en crudo** (como edades exactas, causas de muerte precisas y ubicaciones a nivel municipio).
Para tu documento del Plan Ético, debes estipular que las reglas de anonimización (como la generalización de edades en rangos o el enmascaramiento de localidades muy pequeñas) se ejecutarán mediante *Vistas SQL* o transformaciones *ETL* durante el paso del Sandbox hacia la Capa Analítica (Data Warehouse) en la Fase 2, garantizando que el dato crudo permanezca inmutable e inaccesible para usuarios finales.




# DICCIONARIO DE DATOS
¡Claro que lo recuerdo! Esta es la pieza clave que faltaba para justificar el diseño de tu base de datos y que el Integrante 3 pueda armar un **Diccionario de Datos** de nivel profesional.

Para que sea fácil de leer y copiar, he dividido la información en tablas por cada entidad. He incluido las descripciones exactas de lo que significa cada código (especialmente los del INE, que son estándares de estadísticas vitales en Guatemala) y la justificación de por qué elegimos esos tipos de datos.

Aquí tienes el detalle completo de tu capa Sandbox:

### 1. `sandbox_ine_defunciones`

Esta es tu tabla principal (transaccional). Su diseño se justifica en mantener los datos originales del INE intactos, utilizando tipos `NUMERIC` o `VARCHAR` según la naturaleza del código, para evitar la pérdida de ceros a la izquierda y soportar valores nulos.

| Nombre de Columna | Tipo de Dato | Descripción y Justificación (Diccionario) |
| --- | --- | --- |
| **id_sandbox** | SERIAL (PK) | Llave primaria subrogada. Necesaria para identificar unívocamente cada fila tras la carga masiva. |
| **fuente_archivo** | VARCHAR(100) | Linaje de datos: Ruta exacta del archivo de origen en S3. |
| **fecha_carga** | TIMESTAMP | Linaje de datos: Fecha y hora exacta de inserción en la base de datos. |
| **depreg** | NUMERIC(4,0) | Código del departamento donde se registró la defunción. |
| **mupreg** | VARCHAR(10) | Código del municipio donde se registró la defunción. |
| **mesreg** | NUMERIC(2,0) | Mes en el que se realizó el registro legal de la defunción. |
| **anoreg** | NUMERIC(4,0) | Año en el que se realizó el registro. |
| **depocu** | NUMERIC(4,0) | Código del departamento donde **ocurrió** la defunción (vital para análisis geográfico). |
| **mupocu** | VARCHAR(10) | Código del municipio donde ocurrió la defunción. |
| **diaocu** | NUMERIC(2,0) | Día en el que ocurrió el fallecimiento. |
| **mesocu** | NUMERIC(2,0) | Mes en el que ocurrió el fallecimiento. |
| **anoocu** | NUMERIC(4,0) | Año exacto del fallecimiento. |
| **areag** | NUMERIC(1,0) | Área geográfica de ocurrencia (ej. 1=Urbano, 2=Rural). |
| **sexo** | NUMERIC(1,0) | Sexo biológico del fallecido (ej. 1=Hombre, 2=Mujer). |
| **edadif** | NUMERIC(3,0) | Edad del fallecido. Crítica para cálculos de esperanza de vida. |
| **perdif** | NUMERIC(1,0) | Pertenencia étnica del fallecido (Mestizo, Maya, Xinca, Garífuna). |
| **puedif** | NUMERIC(4,0) | Pueblo específico de pertenencia (especificación étnica). |
| **ecidif** | NUMERIC(1,0) | Estado civil del fallecido. |
| **escodif** | NUMERIC(2,0) | Nivel de escolaridad alcanzado. |
| **ciuodif** | VARCHAR(10) | Ocupación o profesión del fallecido. |
| **pnadif** | NUMERIC(4,0) | País de nacimiento. |
| **dnadif** | NUMERIC(4,0) | Departamento de nacimiento. |
| **mnadif** | VARCHAR(10) | Municipio de nacimiento. |
| **nacdif** | NUMERIC(4,0) | Nacionalidad legal del fallecido. |
| **predif** | NUMERIC(4,0) | País de residencia habitual. |
| **dredif** | NUMERIC(4,0) | Departamento de residencia habitual. |
| **mredif** | VARCHAR(10) | Municipio de residencia habitual. |
| **caudef** | VARCHAR(10) | **Columna Crítica:** Código de la Causa de Defunción según la clasificación internacional CIE-10 (ej. I219 = Infarto). |
| **asist** | NUMERIC(1,0) | Asistencia médica recibida durante la enfermedad o evento previo a la muerte. |
| **ocur** | NUMERIC(1,0) | Sitio de ocurrencia (Hospital público, IGSS, domicilio, vía pública). |
| **cerdef** | NUMERIC(1,0) | Quién certificó la defunción (Médico tratante, forense, autoridad local). |

---

### 2. `sandbox_oms_indicadores`

Extraída vía API OData de la Organización Mundial de la Salud. Contiene mucha metadata de dimensiones que justificamos guardar como texto (`VARCHAR`) para mantener la flexibilidad del catálogo internacional.

| Nombre de Columna | Tipo de Dato | Descripción y Justificación (Diccionario) |
| --- | --- | --- |
| **id_sandbox** | SERIAL (PK) | Identificador único de ingesta. |
| **fuente_archivo** | VARCHAR(100) | Linaje: Archivo JSON de origen. |
| **fecha_carga** | TIMESTAMP | Linaje: Momento de inserción. |
| **id_oms** | BIGINT | ID original del registro en la base de datos de la OMS. |
| **indicator_code** | VARCHAR(50) | Código alfanumérico del indicador de salud (ej. esperanza de vida). |
| **spatial_dim_type** | VARCHAR(20) | Tipo de dimensión espacial (generalmente "COUNTRY"). |
| **spatial_dim** | VARCHAR(10) | Código ISO de 3 letras del país (ej. GTM, SLV, HND). |
| **parent_location_code** | VARCHAR(10) | Código de la región superior (ej. AMR para las Américas). |
| **parent_location** | VARCHAR(50) | Nombre descriptivo de la región superior. |
| **time_dim_type** | VARCHAR(20) | Tipo de dimensión temporal (generalmente "YEAR"). |
| **time_dim** | INTEGER | Año numérico de la medición (ej. 2019). |
| **dim1_type** | VARCHAR(30) | Sub-dimensión 1 (Suele ser "SEX"). |
| **dim1** | VARCHAR(30) | Valor de la sub-dimensión (Male, Female, Both sexes). |
| **dim2_type** | VARCHAR(30) | Sub-dimensión 2 (si aplica). |
| **dim2** | VARCHAR(50) | Valor de la sub-dimensión 2. |
| **value_text** | VARCHAR(50) | Valor del indicador almacenado como texto por la API. |
| **numeric_value** | NUMERIC | **Columna Crítica:** Valor del indicador en formato numérico para cálculos analíticos. |
| **low_value** | NUMERIC | Límite inferior del intervalo de confianza estadístico de la OMS. |
| **high_value** | NUMERIC | Límite superior del intervalo de confianza estadístico de la OMS. |
| **date_registro** | VARCHAR(50) | Fecha en la que la OMS publicó la métrica. |
| **time_dimension_value** | VARCHAR(10) | Representación en texto del periodo temporal. |
| **time_dimension_begin** | VARCHAR(50) | Inicio exacto de la cobertura de la métrica. |
| **time_dimension_end** | VARCHAR(50) | Fin exacto de la cobertura de la métrica. |

---

### 3. `sandbox_worldbank_indicadores`

Indicadores macroeconómicos y de salud del Banco Mundial. El esquema refleja la estructura tabular plana clásica de los archivos de salida de su API.

| Nombre de Columna | Tipo de Dato | Descripción y Justificación (Diccionario) |
| --- | --- | --- |
| **id_sandbox** | SERIAL (PK) | Identificador único de ingesta. |
| **fuente_archivo** | VARCHAR(100) | Linaje: Archivo JSON de origen. |
| **fecha_carga** | TIMESTAMP | Linaje: Momento de inserción. |
| **indicator_id** | VARCHAR(50) | Código del indicador del BM (ej. SP.DYN.CDRT.IN para Tasa Bruta de Mortalidad). |
| **indicator_value** | VARCHAR(200) | Nombre completo y descriptivo del indicador. |
| **country_id** | VARCHAR(5) | Código interno de país del Banco Mundial (2 caracteres). |
| **country_value** | VARCHAR(50) | Nombre oficial del país (ej. Guatemala, Honduras). |
| **countryiso3code** | VARCHAR(5) | Código ISO-3 estándar del país. Vital para cruzar datos con la OMS en Fase 2. |
| **date_year** | VARCHAR(10) | Año de la medición estadística. |
| **value** | NUMERIC | **Columna Crítica:** El valor numérico del indicador (tasa, porcentaje o número bruto). |
| **unit** | VARCHAR(20) | Unidad de medida (usualmente viene vacío pero se mantiene por estructura). |
| **obs_status** | VARCHAR(10) | Estado de la observación estadística (estimación, dato real, proyecciones). |
| **decimal_places** | INTEGER | Precisión de decimales definidos por el Banco Mundial para esa métrica. |

---

### 4. `sandbox_gdrive_diccionario`

El catálogo maestro para decodificar todo lo que el INE manda como números. Es un diseño simple y genérico para soportar cualquier tipo de catálogo.

| Nombre de Columna | Tipo de Dato | Descripción y Justificación (Diccionario) |
| --- | --- | --- |
| **id_sandbox** | SERIAL (PK) | Identificador único de ingesta. |
| **fuente_archivo** | VARCHAR(100) | Linaje de datos (el Excel de diccionario). |
| **fecha_carga** | TIMESTAMP | Linaje de datos. |
| **variable** | VARCHAR(200) | El nombre de la columna en la tabla del INE a la que aplica (ej. `depocu`, `sexo`). |
| **codigo** | VARCHAR(50) | El valor numérico crudo que viene en la tabla (ej. `1`). Se deja como VARCHAR para soportar letras (ej. CIE-10). |
| **etiqueta** | VARCHAR(200) | El significado real legible por humanos de ese código (ej. `Guatemala`, `Hombre`). |

---

### 5. `sandbox_log_carga`

Tabla de metadatos operativos. Justifica tu control de calidad (Data Quality) demostrando que registras el éxito o fracaso de los procesos de ingeniería de datos.

| Nombre de Columna | Tipo de Dato | Descripción y Justificación (Diccionario) |
| --- | --- | --- |
| **id_log** | SERIAL (PK) | Identificador del evento de carga. |
| **fecha_inicio** | TIMESTAMP | Hora exacta en la que inició la ingesta de un archivo. |
| **fecha_fin** | TIMESTAMP | Hora exacta en la que finalizó el bloque de carga. |
| **fuente_archivo** | VARCHAR(100) | El archivo procesado durante este evento (ej. dataset INE 2024). |
| **tabla_destino** | VARCHAR(100) | En qué tabla aterrizaron los datos. |
| **filas_insertadas** | INTEGER | Conteo de registros inyectados. Crucial para auditar volumetría. |
| **estado** | VARCHAR(20) | Resultado de la operación (`EXITO`, `ERROR`, `OMITIDO`). |
| **mensaje_error** | TEXT | Si hubo un fallo de conexión a S3 o formato, se almacena aquí la traza de error. |
| **script_version** | VARCHAR(20) | Versión del código de Python utilizado (trazabilidad del código). |