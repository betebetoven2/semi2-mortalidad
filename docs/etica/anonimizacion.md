# Plan de Anonimización y Agregación

Este plan define **qué** se transforma, **cómo** y **en qué capa**, garantizando que los usuarios finales nunca accedan a datos individuales crudos.

---

## Marco Normativo — EU Data Act y GDPR

Este plan se fundamenta en el **EU Data Act — Reglamento (UE) 2023/2854** del Parlamento Europeo y del Consejo, de 13 de diciembre de 2023, sobre normas armonizadas para un acceso justo a los datos y su utilización. El Reglamento **entró en vigor el 11 de enero de 2024** y es **aplicable desde el 12 de septiembre de 2025**, y **complementa al GDPR (Reglamento (UE) 2016/679)** en lo relativo a la protección de datos personales.

Aunque el proyecto se desarrolla en Guatemala, se adopta el EU Data Act como **estándar de referencia internacional** por ser el marco más exigente y actual en materia de gobernanza, compartición y reutilización de datos. El proyecto simula una consultoría de datos para el **PNUD** y el **MSPAS** —organismos del sector público con fines de interés público en salud—, escenario que encaja directamente en el supuesto de compartición **B2G (*business-to-government*) por necesidad excepcional** que regula el **Capítulo V del Data Act**, el cual cubre expresamente las **emergencias de salud pública** (p. ej. pandemias) y la **producción de estadística oficial**.

### Principios del Data Act aplicados en este plan

| Principio / Artículo del Data Act | Cómo lo implementa nuestra arquitectura |
|---|---|
| **Anonimización y agregación de datos personales** (Art. 20(2) y considerandos sobre compartición B2G): cuando los datos puestos a disposición de un organismo público contienen datos personales, deben anonimizarse o agregarse. | Capas **Silver** y **Gold**: generalización de edad y CIE-10, k-anonimato (k≥5) en municipio y etnia, y agregación a nivel departamento/nacional **antes** de cualquier acceso externo. |
| **Minimización de datos y protección desde el diseño y por defecto** (*data minimisation*, *data protection by design and by default*). | Supresión de variables no analíticas (`diaocu`, `ciuodif`, `pnadif`, `mnadif`) y exposición del mínimo nivel de detalle necesario por perfil de usuario. |
| **B2G — necesidad excepcional / interés público** (Cap. V, Art. 15): emergencias de salud pública y estadística oficial. | El análisis **pre/post-COVID** y la entrega a PNUD/MSPAS se tratan como compartición de interés público; el dato crudo permanece **inmutable** y solo se comparten vistas anonimizadas/agregadas. |
| **Transmisión únicamente de datos no personales o anonimizados a terceros** (considerandos del Art. 5). | La capa **Gold** (pública / dashboards) no contiene ningún dato individual ni columna de etnia; solo cifras agregadas sin posibilidad de reidentificación. |
| **Supleción del GDPR**: el Data Act no sustituye al GDPR, sino que se aplica **junto a él**. | Se mantienen como base el principio de proporcionalidad (GDPR art. 5) y la protección de datos étnicos (Convenio 169 OIT), descritos en el [Marco Ético](index.md). |

!!! info "Por qué el Data Act y no solo el GDPR"
    El GDPR regula *cómo se protegen* los datos personales; el **Data Act regula *cómo se comparten y reutilizan* los datos** —incluido el flujo hacia organismos públicos—, exigiendo anonimización y agregación como **condición** de esa compartición. Por eso el Data Act es el instrumento que da fundamento directo a este plan de anonimización/agregación por capas.

---

## Arquitectura de Capas

| Capa | Schema | Contenido | Acceso |
|---|---|---|---|
| **BRONZE** (Raw) | Databricks `bronze` | Datos crudos tal como vienen de S3. Sin transformación. | Solo ingeniería de datos |
| **SANDBOX** (Normalizado) | PostgreSQL `sandbox` | Datos tipados y normalizados. Sin transformación destructiva. | Solo ingeniería de datos |
| **SILVER** (Restringida) | `silver` | Edad en rangos OPS · CIE-10 a categoría (3 chars) · Etnia con k-anonimato (k≥5) · Municipio suprimido si k<5 | Investigadores autorizados |
| **GOLD** (Pública) | `gold` | Solo nivel departamento/nacional · Causa a capítulo CIE-10 (1 char) · Sin etnia individual · Celdas <5 suprimidas | Público general / dashboards |

```
BRONZE ──[ETL Fase 2]──► SANDBOX ──[Vistas SQL]──► SILVER ──[Agregación]──► GOLD
```

!!! abstract "Correspondencia con el Data Act"
    Esta arquitectura por capas es la implementación técnica del mandato del Data Act: el dato personal individual nunca abandona Bronze/Sandbox; toda compartición (interna o B2G) ocurre sobre Silver/Gold, donde la anonimización y la agregación ya fueron aplicadas.

---

## Técnicas Aplicadas

### Técnica 1 — Generalización de Edad

**Columna:** `edadif` · **Nivel de sensibilidad:** ALTO

La edad exacta combinada con causa de muerte y municipio permite identificar a individuos en comunidades pequeñas.

**Solución:** reemplazar la edad exacta por rangos etarios estándar de la OPS/OMS.

```sql
CASE
    WHEN edadif < 1   THEN '< 1 año'
    WHEN edadif < 5   THEN '1–4 años'
    WHEN edadif < 15  THEN '5–14 años'
    WHEN edadif < 25  THEN '15–24 años'
    WHEN edadif < 45  THEN '25–44 años'
    WHEN edadif < 65  THEN '45–64 años'
    WHEN edadif >= 65 THEN '65+ años'
    ELSE                   'No especificado'
END AS grupo_edad
```

---

### Técnica 2 — k-Anonimato Geográfico

**Columnas:** `mupocu`, `mupreg`, `mredif`, `mnadif` · **Nivel de sensibilidad:** ALTO

En municipios con pocos fallecidos, la combinación municipio + causa + etnia puede identificar a una persona concreta.

**Solución:** umbral mínimo k=5. Si un municipio tiene menos de 5 fallecimientos en un año para una combinación de atributos, se suprime elevando al nivel departamento.

```sql
CASE
    WHEN COUNT(*) OVER (PARTITION BY mupocu, anoocu) < 5
    THEN NULL          -- suprimido, solo se expone el departamento
    ELSE mupocu
END AS municipio_anonimizado
```

!!! note "Umbral ajustable"
    El umbral k=5 es el mínimo recomendado. Para análisis más conservadores puede elevarse a k=10.

---

### Técnica 3 — Generalización de Causa de Muerte (CIE-10)

**Columna:** `caudef` · **Nivel de sensibilidad:** ALTO

El código CIE-10 a 4 caracteres es extremadamente específico. Cruzado con etnia y municipio puede ser estigmatizante.

**Solución:** elevar la causa al nivel de capítulo según la capa de acceso.

| Capa | Nivel CIE-10 | Ejemplo | Chars |
|---|---|---|---|
| Sandbox | Código completo | `I219` = Infarto STEMI | 4 |
| Silver | Categoría | `I21` = Infarto agudo de miocardio | 3 |
| Gold | Capítulo | `I` = Enfermedades del sistema circulatorio | 1 |

```sql
-- En Silver: categoría (3 chars)
SUBSTRING(caudef, 1, 3) AS caudef_categoria

-- En Gold: capítulo (1 char)
LEFT(caudef, 1) AS capitulo_cie10
```

---

### Técnica 4 — Enmascaramiento de Etnia

**Columnas:** `perdif`, `puedif` · **Nivel de sensibilidad:** ALTO

La etnia es un dato protegido internacionalmente (Convenio 169 OIT). En municipios con mayoría étnica conocida, revelarla junto con la causa de muerte puede usarse para discriminación.

**Solución:** mismo umbral k=5 aplicado por grupo étnico en municipio-año.

```sql
CASE
    WHEN COUNT(*) OVER (
        PARTITION BY perdif, mupocu, anoocu
    ) < 5 THEN NULL
    ELSE perdif
END AS perdif_anon
```

---

### Técnica 5 — Supresión de Variables No Analíticas

Columnas que no aportan valor analítico significativo pero sí riesgo de reidentificación se eliminan desde Silver o Gold. Esta supresión materializa el principio de **minimización de datos** del Data Act y del GDPR.

| Columna | Eliminada en | Motivo |
|---|---|---|
| `diaocu` | Silver | Día exacto innecesario para tendencias temporales |
| `ciuodif` | Silver | Alta tasa de nulos; riesgo de reidentificación por cruce |
| `pnadif` / `nacdif` | Silver | País de nacimiento/nacionalidad; permite cruce identificante |
| `puedif` | Silver | Pueblo específico dentro de etnia — demasiado granular |
| `mnadif` | Silver | Municipio de nacimiento — dato biográfico innecesario |

---

## Vista SQL de Referencia — Capa Silver

```sql
CREATE OR REPLACE VIEW silver.vw_defunciones_anon AS
SELECT
    -- Linaje (no identificante)
    fuente_archivo,
    DATE_TRUNC('month', fecha_carga)    AS mes_carga,

    -- Geografía
    depocu,
    CASE
        WHEN COUNT(*) OVER (
            PARTITION BY mupocu, anoocu
        ) < 5 THEN NULL
        ELSE mupocu
    END                                 AS municipio_anon,
    areag,

    -- Tiempo (año y mes; sin día)
    anoocu,
    mesocu,

    -- Demografía generalizada
    sexo,
    CASE
        WHEN edadif < 1   THEN 0   -- < 1 año
        WHEN edadif < 5   THEN 1   -- 1–4 años
        WHEN edadif < 15  THEN 2   -- 5–14 años
        WHEN edadif < 25  THEN 3   -- 15–24 años
        WHEN edadif < 45  THEN 4   -- 25–44 años
        WHEN edadif < 65  THEN 5   -- 45–64 años
        ELSE 6                     -- 65+ años
    END                                 AS grupo_edad_id,

    -- Etnia con k-anonimato
    CASE
        WHEN COUNT(*) OVER (
            PARTITION BY perdif, mupocu, anoocu
        ) < 5 THEN NULL
        ELSE perdif
    END                                 AS etnia_anon,

    -- Causa de muerte (categoría CIE-10, 3 chars)
    SUBSTRING(caudef, 1, 3)             AS caudef_categoria,

    -- Contexto clínico (no identificante)
    asist,
    ocur,
    ecidif,
    escodif
FROM sandbox.sandbox_ine_defunciones;
```

---

## Tabla de Decisiones por Columna

| Columna | Silver | Gold | Técnica |
|---|---|---|---|
| `edadif` | Rangos etarios (7 grupos) | Mismo rango | Generalización |
| `diaocu` | **Eliminar** | **Eliminar** | Supresión |
| `mupocu` / `mupreg` | NULL si k<5 | **Eliminar** (solo depto.) | k-anonimato |
| `mredif` / `mnadif` | **Eliminar** | **Eliminar** | Supresión |
| `perdif` | NULL si k<5 por municipio-año | **Eliminar** | k-anonimato |
| `puedif` | **Eliminar** | **Eliminar** | Supresión |
| `caudef` | Categoría 3 chars | Capítulo 1 char | Generalización |
| `ciuodif` | **Eliminar** | **Eliminar** | Supresión |
| `pnadif` / `nacdif` | **Eliminar** | **Eliminar** | Supresión |
| `sexo` | Mantener | Mantener | — |
| `anoocu` / `mesocu` | Mantener | Mantener | — |
| `depocu` | Mantener | Mantener | — |
| `asist` / `ocur` | Mantener | Mantener | — |
| `ecidif` / `escodif` | Mantener | **Eliminar** | Supresión en Gold |

---

## Referencia normativa

- **Reglamento (UE) 2023/2854 (Data Act)** — Parlamento Europeo y Consejo, 13 de diciembre de 2023. En vigor desde el 11/01/2024, aplicable desde el 12/09/2025. Capítulo V (compartición B2G por necesidad excepcional), Art. 15 y Art. 20(2) (costos de anonimización, pseudonimización y agregación).
- **Reglamento (UE) 2016/679 (GDPR)** — principio de proporcionalidad y minimización (art. 5); protección de datos por diseño y por defecto (art. 25).
- **Convenio 169 OIT** — protección de datos de pueblos indígenas (`perdif`, `puedif`).
- **OPS/OMS** — estándares de rangos etarios y buenas prácticas en microdatos de mortalidad.