# Reporte de Perfilamiento y Guía de Construcción **Bronze → Stage** (Fase 2)
### Proyecto: Plataforma Analítica de Mortalidad End-to-End — PNUD / MSPAS
### Consultoría de Ingeniería de Datos · Plataforma Databricks (Lakehouse, serverless)

> **Alcance de este documento:** corresponde a la **Fase 2** (*Transformación, arquitectura por capas y almacenamiento*), específicamente al tramo **Sandbox → Stage** y su preparación para el **DW (Fact-Dimensiones)**. El profiling de Bronze y las reglas de conformidad aquí descritas alimentan la capa Stage y el plan de anonimización. No se desarrolla ML ni BI (Fase 3).
>
> *Documento en Markdown para integrarse directamente en la documentación desplegada con MkDocs / GitHub Actions del proyecto.*

---

## 0. Resumen ejecutivo

Este documento cumple **dos funciones**: (1) **reporte de hallazgos** del análisis exploratorio / perfilamiento de la capa Bronze, y (2) **guía operativa** para que la persona encargada construya la capa **Stage** de forma correcta, justificada y compatible con el plan de anonimización.

**Veredicto:** la información del profiling **es suficiente** para definir las reglas de Stage. Se ejecutó además una **segunda iteración** de chequeos (notebook `stage_profiling_fase2.ipynb`) para cubrir lo que la Fase 2 exige y el primer profiling no medía: factibilidad de **k-anonimato**, semántica de las columnas usadas en la anonimización y soporte al modelo dimensional.

**Hallazgos que cambian decisiones (evidencia en §3 y §5):**

| # | Hallazgo | Impacto |
|---|---|---|
| H1 | La única diferencia de esquema entre las dos tablas INE es `Areag` | Se **unifican** en una sola `stage.defunciones` (2015–2024) |
| H2 | El legacy 2015–2017 trae **artefacto float** (`"1.0"` en vez de `"1"`) | Normalizar **antes** de unir y de k-anonimizar |
| H3 | `Perdif` **no es etnia**: es la **unidad de edad** (3=años, 9=ignorado). La etnia es **`Puedif`** | **Corrige** las técnicas de anonimización (§5) |
| H4 | La edad (`Edadif`) está en años, meses o días según `Perdif`; ~46 mil registros no están en años | **Corrige** la generalización de edad del plan (§5) |
| H5 | `Areag` (urbano/rural) **solo existe 2015–2017** | Limitación para el análisis urbano/rural pre/post-COVID |
| H6 | `Caudef` 100% en formato CIE-10; fuerte presencia del capítulo R y `U071` (COVID-19) | Buena base para `dim_causa`; documentar calidad de causa |
| H7 | La etnia (`Puedif`) tiene **16–19% de "Ignorado"** | Convertir a `NULL` antes del k-anonimato; afecta el análisis étnico |

**Cifras macro.**

| Tabla Bronze | Filas | Columnas | Rol en Fase 2 |
|---|---:|---:|---|
| `bronze.xlsx_ine` | 674,064 | 30 | Defunciones INE 2018–2024 (hecho) |
| `bronze.sav_ine_legacy` | 245,167 | 31 | Defunciones INE 2015–2017 (hecho) |
| `bronze.json_oms` | 1,708 | 27 | Referencia OMS |
| `bronze.json_worldbank` | 450 | 10 | Referencia Banco Mundial |
| `bronze.gdrive_docs` | 1,837 | 5 | Diccionario de variables |

> Total de defunciones a consolidar en `stage.defunciones`: **919,231** (2015–2024).

---

## 1. Marco metodológico y reconciliación de capas

### 1.1 Por qué se perfila antes de construir Stage
El perfilamiento corresponde a la fase de *Data Understanding* de **CRISP-DM** (explorar para detectar problemas de calidad **antes** de preparar/limpiar) y a la transición *Bronze → Silver* de la arquitectura **medallion**: Bronze conserva el crudo sin validación; la limpieza, validación, deduplicación, tipado y estandarización ocurren en la capa de conformación (Stage/Silver). El diagnóstico se estructuró sobre las **6 dimensiones de calidad de datos** (Completitud, Unicidad, Validez, Consistencia, Exactitud, Vigencia). Referencias en §12.

### 1.2 Reconciliación de nomenclatura (para no confundir al equipo)
El enunciado, la arquitectura *medallion* y el plan de anonimización usan nombres distintos para capas equivalentes. Equivalencia adoptada:

| Enunciado (Fase 2) | Implementación física del equipo | Rol |
|---|---|---|
| **Tabla Sandbox** | `bronze` (Databricks, crudo desde S3) **+** `sandbox` (PostgreSQL, tipado/normalizado, no destructivo) | Aterrizaje fiel al origen |
| **Tabla Stage** | `silver` — **conformado**: limpio, tipado, estandarizado, reglas de negocio y calidad (+ anonimización) | **Foco de este documento** |
| **DW (Fact-Dim)** | Modelo dimensional estrella; capa `gold` para vistas agregadas/públicas | Repositorio analítico |

> En este documento, **"Stage" = la capa conformada (`silver` del equipo)**. El profiling corrió sobre `bronze` (Databricks). La construcción de Stage descrita aquí produce el insumo limpio que luego se modela como Fact-Dimensiones en el DW (nube + local).

### 1.3 Compatibilidad con serverless
El profiling es **read-only** y lee **tablas Delta directo** (`spark.table("bronze.…")`), sin credenciales S3. Esto respeta el principio medallion de no "arreglar" en Bronze, evita el error `fs.s3a.access.key is not available` del clúster serverless y no depende de credenciales (ya rotadas).

---

## 2. Inventario y estructura

Las cinco tablas se cargaron en Bronze con **todas las columnas como `string`** (correcto: preservar el crudo evita pérdidas por cambios de esquema).

**Esquema INE.** Ambas comparten 27 columnas de negocio + 3 de linaje (`_anio`, `_archivo_origen`, `_fuente`). El legacy tiene **una columna adicional: `Areag`** (urbano/rural).

| Diferencia de esquema INE | Columnas |
|---|---|
| Solo en `xlsx_ine` (2018–2024) | *(ninguna)* |
| Solo en `sav_ine_legacy` (2015–2017) | `Areag` |
| Comunes | 30 |

**Catálogo de columnas INE** (confirmar códigos exactos con `stage.dim_diccionario`):

| Columna | Significado | Columna | Significado |
|---|---|---|---|
| `Depreg`/`Mupreg` | Depto./municipio de **registro** | `Pnadif`/`Dnadif`/`Mnadif` | País/depto/municipio de **nacimiento** |
| `Mesreg`/`Añoreg` | Mes/año de **registro** | `Nacdif` | Nacionalidad |
| `Depocu`/`Mupocu` | Depto./municipio de **ocurrencia** | `Predif`/`Dredif`/`Mredif` | País/depto/municipio de **residencia** |
| `Diaocu`/`Mesocu`/`Añoocu` | Fecha de **ocurrencia** | `Caudef` | Causa de defunción (**CIE-10**) |
| `Sexo` | Sexo (1=hombre, 2=mujer) | `Asist` | Asistencia médica recibida |
| `Edadif` | Edad del difunto | `Ocur` | Sitio de ocurrencia |
| `Perdif` | **Período de edad** (oficial): 1=Menos de un mes, 2=1 a 11 meses, 3=1 año y más, 9=Ignorado (`Edadif`=999) | `Cerdef` | Quién certificó (1=Médico, 2=Paramédico, 3=Autoridad, 9=Ignorado) |
| `Puedif` | **Pueblo / etnia** | `Ecidif` | Estado civil |
| `Escodif` | Escolaridad | `Ciuodif` | Ocupación (CIUO) |
| `Areag` | Área urbano/rural (**solo legacy 2015–2017**) | | |

>  **Atención (H3):** en el plan de anonimización original `perdif` aparece como "etnia". Es incorrecto: **`Perdif` = unidad de edad**, **`Puedif` = pueblo/etnia**. Evidencia en §5.1.

---

## 3. Hallazgos por dimensión de calidad

### 3.1 Completitud
- `xlsx_ine`: solo `Ciuodif` y `Escodif` con faltantes (**14.78%; 99,593 c/u**, mismo número → mismos registros). `sav_ine_legacy`: 0% **textual**.
- `json_oms`: 100% vacías → `Dim3`, `Dim3Type`, `Comments`, `DataSourceDim`, `DataSourceDimType`; `Dim2`/`Dim2Type` 38.64%.
- `json_worldbank`: 100% vacías → `unit`, `obs_status`; `value` 40% faltante.

>  **La cifra de 0% es engañosa.** El chequeo midió solo centinelas **textuales**. Como los microdatos del INE están en **código numérico**, el "ignorado" real se expresa como código (`9`/`99`/`999`) y se mide tras cruzar con el diccionario (§9.2).

**Reglas:** **R-COMP-1** centinelas → `NULL`, **por columna según el diccionario** (no en bloque): `9`=Ignorado en categóricas (`Puedif`, `Escodif`, `Asist`, `Ocur`, `Cerdef`, `Ecidif`), `999`=Ignorado en `Edadif`; **no** nulificar `9` en `Mes` (=Septiembre) ni en `Día`/`Edadif` (valores reales). **R-COMP-2** eliminar columnas 100% vacías; **R-COMP-3** documentar cobertura parcial de `Ciuodif`/`Escodif`, sin imputar en Stage.

### 3.2 Unicidad

| Tabla | Filas | Dups (sin metadata) | % |
|---|---:|---:|---:|
| `xlsx_ine` | 674,064 | 167 | 0.02% |
| `sav_ine_legacy` | 245,167 | 79 | 0.03% |
| `gdrive_docs` | 1,837 | 1,193 | 64.94% (artefacto de estructura) |

> Las defunciones **no tienen folio/ID único**: dos filas idénticas pueden ser dos muertes reales. **R-UNIQ-1** no `dropDuplicates` global; marcar `dup_exacto`. **R-UNIQ-2** el diccionario se **reestructura**, no se deduplica (§9.4).

### 3.3 Validez
- `Sexo`: `xlsx = {1: 374,733; 2: 299,331}`; `legacy = {"1.0": 137,506; "2.0": 107,661}` ← **artefacto float (H2)**.
- `Mesocu`/`Mesreg` (1–12), `Diaocu` (1–31): **0 violaciones**.
- `Edadif`: 1,997 (xlsx) / 1,300 (legacy) "fuera de 0–120" → **coinciden exactamente con `Perdif=9`** (edad ignorada).
- `Caudef`: **100%** formato CIE-10. Top: `I219`, `R99X`, `J189`, `E149`, `R98X`, `U071` (COVID-19), `R54X`.

**Reglas:** **R-VALID-1** (prioritaria) corregir artefacto float antes de unir; **R-VALID-2** `edad_anios` desde `Edadif`+`Perdif` (NULL si `Perdif=9`); **R-VALID-3** dominio de `Sexo`={1,2}; **R-VALID-4** `Caudef` mayúsculas/`trim`.

### 3.4 Consistencia

| Regla | `xlsx_ine` | `sav_ine_legacy` |
|---|---|---|
| `Añoocu ≤ Añoreg` | 0 violaciones | 0 violaciones |
| `_anio == Añoreg` | 23,971 difieren | 6,043 difieren |
| Rango `Añoocu` | 2018–2024 ✓ | 2015–2017 ✓ |

> Las diferencias `_anio` vs `Añoreg` son **registros rezagados**, no errores. **R-CONS-1** construir `fecha_ocurrencia` (date) validada; **R-CONS-2** usar la **ocurrencia** como dimensión temporal y partición; **R-CONS-3** conservar `_anio`/`_archivo_origen` como linaje.

### 3.5 Cardinalidad
`Depreg`/`Depocu`=22 (departamentos ✓), `Mupreg`/`Mupocu`=324, `Mesreg`/`Mesocu`=12, `Areag`=3, `Caudef`≈2,692/2,110 (CIE-10). Todo plausible. **R-CARD-1** `lpad(municipio,4,'0')` para joins con catálogos y la unión entre periodos (el float pudo perder ceros iniciales en el legacy).

---

## 4. Hallazgos por tabla (resumen accionable)

- **`xlsx_ine`** — limpia; `Ciuodif`/`Escodif` 14.78% faltante; sin artefacto float.
- **`sav_ine_legacy`** — **requiere normalización float**; posible pérdida de ceros iniciales en municipios; incluye `Areag`.
- **`json_oms`** — 5 países (GTM, CRI, HND, SLV, PAN); indicadores `MDG_0000000001` (mortalidad <5), `WHOSIS_000001/000002`; desagregación por sexo; `NumericValue` completo. Drop de 5 columnas vacías.
- **`json_worldbank`** — **6 países** (incluye **NIC**, ausente en OMS → inconsistencia de cobertura); `indicator`/`country` como **dict serializado con comillas simples** (no JSON → regex); `value` 40% faltante. Drop de `unit`/`obs_status`.
- **`gdrive_docs`** — nombre de variable solo en la primera fila de cada bloque (celdas combinadas → *forward-fill*); confirma departamentos `1–22` y municipios de 4 dígitos `0101…`.

---

## 5. Correcciones al Plan de Anonimización (con evidencia)

El plan es sólido en estructura y en su fundamentación EU Data Act / GDPR. El profiling detectó **dos errores de mapeo de columnas** que deben corregirse para que las técnicas funcionen.

### 5.1 Corrección C1 — `Perdif` es unidad de edad, no etnia; la etnia es `Puedif`
**Evidencia confirmada en la corrida (`stage_profiling_fase2.ipynb`, celda 1):**
- `Perdif` = `{3: 626,139; 1: 24,168; 2: 21,760; 9: 1,997}` → 4 valores → **unidad de edad** (confirmado por celda 2: 1=días, 2=meses, 3=años, 9=ignorado con `Edadif`=999).
- `Puedif` = `{4: 363,398; 1: 189,911; 9: 110,328; 5: 9,391; 3: 826; 2: 210}` (xlsx) → cardinalidad **6** → **pueblo/etnia**, etiquetas **confirmadas por el diccionario**: 1=Maya, 2=Garífuna, 3=Xinka, 4=Mestizo/Ladino, 5=Otro, 9=Ignorado.

**Consecuencias:**
- **Técnica 4 (k-anonimato de etnia):** particionar por **`Puedif`**, no por `Perdif`.
- **Hallazgo nuevo — incompletitud de etnia (H7):** `Puedif=9` (Ignorado) = **110,328 en xlsx (16.4%)** y **47,678 en legacy (19.4%)**. Es un faltante alto en una variable sensible. **Convertir `9`→`NULL` antes del k-anonimato** (R-COMP-1); de lo contrario "Ignorado" se trata como un grupo étnico real y distorsiona conteos y supresión.
- **Tabla de decisiones:** si el análisis étnico es deseable (relevante por el Convenio 169 OIT), **conservar `Puedif` con k-anonimato** en lugar de eliminarlo; eliminarlo destruye una dimensión analítica legítima.

### 5.2 Corrección C2 — La generalización de edad debe usar `Edadif` **junto con** `Perdif`
**Evidencia confirmada (celda 2):** la edad cambia de unidad según `Perdif`:

| `Perdif` | Unidad | Rango observado de `Edadif` | Registros (xlsx) |
|---|---|---|---:|
| 1 | días | 0–29 | 24,168 |
| 2 | meses | 1–11 | 21,760 |
| 3 | años | 1–120 | 626,139 |
| 9 | ignorado | **999** (centinela) | 1,997 |

~46,000 registros (días/meses) son **infantes <1 año**. El SQL original `WHEN edadif < 1 … WHEN edadif < 5 THEN '1–4 años'` interpreta `edadif` como **años**, por lo que un bebé con `Edadif=3, Perdif=2` (3 meses) se codificaría como "1–4 años"; y `Perdif=9` (`Edadif=999`) caería fuera de todo rango. **Todos estos ~46 mil infantes quedarían mal clasificados**, lo cual es grave porque la mortalidad infantil es un indicador central del análisis.

**Corrección:** calcular primero `edad_anios` (R-VALID-2) y luego agrupar:
```sql
CASE
    WHEN edad_anios IS NULL THEN 'No especificado'  -- Perdif = 9
    WHEN edad_anios < 1   THEN '< 1 año'            -- incluye meses/días (Perdif 1/2)
    WHEN edad_anios < 5   THEN '1–4 años'
    WHEN edad_anios < 15  THEN '5–14 años'
    WHEN edad_anios < 25  THEN '15–24 años'
    WHEN edad_anios < 45  THEN '25–44 años'
    WHEN edad_anios < 65  THEN '45–64 años'
    ELSE                       '65+ años'
END AS grupo_edad
```

### 5.3 Corrección C3 — La conformidad es **prerrequisito** del k-anonimato
El k-anonimato cuenta ocurrencias por grupo (`PARTITION BY mupocu, anoocu, …`). Si el legacy tiene `"101.0"` y el xlsx `"0101"`, el **mismo municipio se parte en dos grupos**, los conteos quedan mal y la supresión se aplica incorrectamente. Por tanto **R-VALID-1** (fix float) y **R-CARD-1** (`lpad`) deben ejecutarse **antes** de anonimizar. Orden obligatorio: *conformar → anonimizar*.

### 5.4 Limitación C4 — `Areag` solo cubre 2015–2017 (pre-COVID)
El desglose **urbano/rural** solo es posible para el periodo pre-COVID. Confirmado: `xlsx_ine` (2018–2024) **no tiene** la columna; `sav_ine_legacy` (2015–2017) trae `Areag = {1: 137,056; 2: 104,322; 9: 3,789}`. **Nota:** `Areag` **no aparece en el diccionario**, así que sus etiquetas (presuntamente 1=Urbano, 2=Rural, 9=Ignorado) **quedan sin confirmar** — verificar antes de usarlas. Para 2018–2024, `Areag = NULL`. Documentar como **limitación del análisis pre/post-COVID**.

### 5.5 Hallazgo C5 — ~13.5% de causas mal definidas (capítulo R), y el k-anonimato de causa a 4 dígitos es inviable
**Evidencia (celdas 5 y 4):**
- La causa (`Caudef`) tiene una jerarquía CIE-10 limpia: **3,087 códigos → 1,102 categorías (3 chars) → 23 capítulos (1 char)**.
- El **capítulo R** (síntomas/hallazgos mal definidos) es el **2.º más frecuente: 124,564 registros (~13.5%)**, solo detrás de I (circulatorio, 154,438). La OMS considera el exceso de causas mal definidas un **indicador de baja calidad** del registro de causa.
- El k-anonimato sobre `(municipio, año, causa 4 dígitos)` **suprimiría ~30% de los registros a k=5** (ver §7), porque el código de 4 dígitos es demasiado granular.

**Consecuencias:**
- **Caveat analítico (pre/post-COVID y ML de Fase 3):** ~13.5% de las muertes no tienen causa específica. Reportar este porcentaje y, si se requiere, analizarlo por separado (no atribuirlo a una causa concreta).
- **Regla de anonimización:** para cualquier cruce **causa × municipio**, generalizar CIE-10 a **categoría (3) o capítulo (1) antes** del k-anonimato, o llevar la causa a nivel **departamento**. Esto justifica con número la generalización de CIE-10 que ya estaba en el plan.

---

## 6. Decisiones de diseño de Stage (justificación)

| # | Decisión | Justificación (ver §12) |
|---|---|---|
| **D1** | Unificar las dos INE → **`stage.defunciones`** (2015–2024), `Areag=NULL` para 2018–2024 | Único delta = `Areag`. Representación validada y no agregada del hecho (medallion). |
| **D2** | Stage conserva **códigos crudos limpios**; el etiquetado y las dimensiones se construyen en el **DW/Gold** | dbt staging (renombrar/castear/categorizar sin joins); Kimball ubica dimensiones en el estrella. |
| **D3** | Centinelas de "ignorado" → `NULL` | Completitud. |
| **D4** | Corregir artefacto float antes de unir y de anonimizar | Consistencia + prerrequisito del k-anonimato (C3). |
| **D5** | No deduplicar a ciegas; marcar `dup_exacto` | Unicidad sin ID. |
| **D6** | Drop de columnas 100% vacías; **aplanar** structs de World Bank | Completitud + Validez. |

### 6.1 Nota de diseño — preservar una representación granular fiel
La buena práctica medallion indica que la capa conformada debe incluir **al menos una representación validada y no agregada de cada registro**. Por eso se recomienda **separar dos sub-capas dentro de Stage/Silver**:

- **`stage.defunciones` (conformada, granular, acceso restringido):** dato limpio, tipado, estandarizado, con `edad_anios`, código CIE-10 completo (4 chars) y municipio. Insumo del **DW Fact** y única copia fiel no agregada.
- **`stage.defunciones_anon` / vistas (anonimizadas):** generalización (rangos de edad, CIE-10 a 3/1 chars), k-anonimato (k≥5) y supresión, para compartición B2G y dashboards (Gold).

Así se cumple el EU Data Act/GDPR **sin destruir** la granularidad que el DW necesita para sus dimensiones.

---

## 7. Integración del Plan de Anonimización en Stage

**Cadena lógica (orden obligatorio):**
```
Bronze (crudo) → CONFORMAR (R-VALID-1, R-CARD-1, R-COMP-1, fecha, edad_anios)
              → stage.defunciones (granular, restringido)
              → ANONIMIZAR (generalización + k-anonimato k≥5 + supresión)
              → vistas/Gold (compartición B2G, dashboards)
```

**Técnicas (corregidas):**

| Técnica | Columna(s) correcta(s) | Regla en Stage |
|---|---|---|
| Generalización de edad | `edad_anios` (de `Edadif`+`Perdif`) | 7 grupos OPS; `NULL`→"No especificado" (C2) |
| Generalización CIE-10 | `Caudef` | Silver: categoría 3 chars; público: capítulo 1 char |
| k-anonimato geográfico | `Mupocu`/`Mupreg` (ya `lpad`) | suprimir si `count(*) OVER (PARTITION BY municipio, año) < k` |
| k-anonimato étnico | **`Puedif`** (no `Perdif`) | suprimir si `< k` por municipio-año (C1) |
| Supresión de variables | `Diaocu`, `Ciuodif`, `Pnadif`/`Nacdif`, `Mnadif`, `Mredif` | minimización (Data Act/GDPR) |

**Factibilidad de k-anonimato — resultados reales (celda 3, sobre 919,231 registros):**

| Cuasi-identificador | k=5 (% suprimido) | k=10 (% suprimido) | Lectura |
|---|---|---|---|
| municipio + año | 10 (**0.00%**) | 56 (0.01%) | trivial → seguro |
| municipio + año + etnia (`Puedif`) | 5,923 (**0.64%**) | 15,571 (1.69%) | bajo → **factible** |
| municipio + año + causa (CIE-10 4 díg.) | 271,046 (**29.49%**) | 391,258 (42.56%) | **inviable** → generalizar causa primero |

> **Conclusión:** las dos técnicas que el plan **sí** usa (municipio y etnia) cuestan **<1% a k=5** → muy favorable, el plan es defendible tal cual. La tercera fila es una **prueba de estrés**: confirma que la causa a 4 dígitos no debe cruzarse con municipio sin generalizar (C5). El % es el **costo de utilidad** de la privacidad y justifica el umbral (k=5 mínimo; k=10 más conservador) ante el cliente y el tutor.

---

## 8. Mapa Stage → DW (modelo dimensional, Fase 2)

El DW es un **esquema estrella**; grano del hecho = **una defunción**. Las dimensiones se materializan en el DW, no en Stage (D2):

| Elemento DW | Fuente en `stage.defunciones` | Notas |
|---|---|---|
| `fact_defunciones` | una fila por registro | medida: conteo (1); FKs a dimensiones; degenerate dims de linaje |
| `dim_tiempo` | `fecha_ocurrencia` (`Añoocu`, `Mesocu`) | usar ocurrencia (R-CONS-2); marca pre/post-COVID |
| `dim_geografia` | `Depocu`/`Mupocu` (y `*reg`, `*redif`, `*nadif`) | **dimensión con roles** (ocurrencia/registro/residencia/nacimiento) |
| `dim_causa_cie10` | `Caudef` | niveles código(4) → categoría(3) → capítulo(1) |
| `dim_sexo` | `Sexo` | {1,2} |
| `dim_grupo_etario` | `edad_anios` (+`Perdif`) | 7 grupos OPS (C2) |
| `dim_pueblo` *(opcional)* | `Puedif` | tratamiento ético (Convenio 169); k-anon en vistas públicas |

> El DW se carga en **nube y local** (requisito Fase 2). Stage debe quedar en un formato que ambos motores puedan leer (p. ej. replicación/exportación de las tablas Delta).

---

## 9. Guía paso a paso **Bronze → Stage** (para el encargado)

### 9.1 Orden de ejecución
1. `CREATE SCHEMA IF NOT EXISTS stage`.
2. Ejecutar **validaciones previas** (9.2) y registrar en bitácora.
3. Construir `stage.dim_diccionario` (9.4).
4. Construir `stage.defunciones` conformada (9.3).
5. Construir `stage.oms_indicadores` y `stage.worldbank_indicadores` (9.5).
6. (Anonimización) construir vistas/`stage.defunciones_anon` (§7).
7. Ejecutar **checklist de aceptación** (9.6).

### 9.2 Validaciones previas (notebooks `stage_profiling.ipynb` y `stage_profiling_fase2.ipynb`)
Cubren: artefacto float por columna del legacy; centinelas numéricos vía diccionario; año que genera el 14.78% faltante de `Ciuodif`/`Escodif`; ceros iniciales en municipios; **factibilidad k-anonimato**; semántica `Perdif`/`Puedif`; cobertura `Areag`.

### 9.3 `stage.defunciones` (conformación + unión)
```python
from pyspark.sql import functions as F

def norm_float(df):
    for c in df.columns:
        if c.startswith("_"): continue
        df = df.withColumn(c, F.when(F.lower(F.trim(F.col(f"`{c}`"))).isin("nan","none",""), None)
                               .otherwise(F.regexp_replace(F.col(f"`{c}`"), r"\.0$", "")))
    return df

xls = norm_float(spark.table("bronze.xlsx_ine")).withColumn("Areag", F.lit(None).cast("string"))
leg = norm_float(spark.table("bronze.sav_ine_legacy"))
cols = xls.columns
defun = xls.select(*cols).unionByName(leg.select(*cols))

defun = (defun
    .withColumn("Mupocu", F.lpad("Mupocu",4,"0"))
    .withColumn("Mupreg", F.lpad("Mupreg",4,"0"))
    .withColumn("fecha_ocurrencia",
        F.expr("try_to_date(concat(lpad(Diaocu,2,'0'),'-',lpad(Mesocu,2,'0'),'-',Añoocu),'dd-MM-yyyy')"))
    .withColumn("edad_anios",
        F.when(F.col("Perdif") == "9", None)                          # ignorado (Edadif=999)
         .when(F.col("Perdif") == "3", F.col("Edadif").cast("int"))   # años
         .when(F.col("Perdif").isin("1","2"), F.lit(0))               # 1=días / 2=meses -> <1 año
         .otherwise(F.lit(None)))
    .withColumn("dup_exacto", F.lit(False)))

defun.write.format("delta").mode("overwrite").option("overwriteSchema","true") \
     .partitionBy("Añoocu").saveAsTable("stage.defunciones")
```
> Confirmar con el diccionario el significado exacto de `Perdif` 1 y 2 antes de fijar `edad_anios`.

### 9.4 `stage.dim_diccionario` (reestructuración con forward-fill)
```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

d = spark.table("bronze.gdrive_docs").toDF("variable","codigo","etiqueta","_archivo_origen","_fuente")
d = d.filter(~((F.col("codigo")=="Código") & (F.col("etiqueta")=="Etiqueta")))
w = Window.orderBy(F.monotonically_increasing_id()).rowsBetween(Window.unboundedPreceding, 0)
d = d.withColumn("variable", F.last("variable", ignorenulls=True).over(w))
d.filter(F.col("codigo").isNotNull()) \
 .write.format("delta").mode("overwrite").saveAsTable("stage.dim_diccionario")
```

### 9.5 OMS y World Bank
```python
from pyspark.sql import functions as F

drop_oms = ["Dim3","Dim3Type","Comments","DataSourceDim","DataSourceDimType"]
oms = (spark.table("bronze.json_oms").drop(*drop_oms)
       .withColumn("valor", F.col("NumericValue").cast("double"))
       .withColumn("anio",  F.col("TimeDim").cast("int")))
oms.write.format("delta").mode("overwrite").saveAsTable("stage.oms_indicadores")

wb = spark.table("bronze.json_worldbank").drop("unit","obs_status")
wb = (wb.withColumn("indicador_id",  F.regexp_extract("indicator", r"'id':\s*'([^']*)'", 1))
        .withColumn("indicador_desc",F.regexp_extract("indicator", r"'value':\s*'([^']*)'", 1))
        .withColumn("pais",          F.regexp_extract("country",   r"'value':\s*'([^']*)'", 1))
        .withColumn("anio",          F.col("date").cast("int"))
        .withColumn("valor",         F.col("value").cast("double")))
wb.write.format("delta").mode("overwrite").saveAsTable("stage.worldbank_indicadores")
```

### 9.6 Checklist de aceptación (*Definition of Done* de Stage)
- [ ] `stage.defunciones` con **919,231** filas (salvo descartes documentados).
- [ ] Ningún valor con sufijo `.0`; `Sexo` ∈ {1,2,NULL}.
- [ ] `Mupocu`/`Mupreg` de longitud 4 en el 100% de filas no nulas.
- [ ] `fecha_ocurrencia` válida; nulos cuantificados.
- [ ] `edad_anios` nula exactamente donde `Perdif=9`; correcta para `Perdif`∈{1,2}.
- [ ] Centinelas de "ignorado" → `NULL`, cuantificados por columna.
- [ ] Columnas 100% vacías de OMS/WB eliminadas; `indicator`/`country` de WB aplanados.
- [ ] `stage.dim_diccionario` sin `variable` nula.
- [ ] **k-anonimato** sobre `Puedif` (no `Perdif`); % suprimido a k=5/k=10 registrado.
- [ ] Códigos huérfanos (en defunciones, ausentes en diccionario) registrados.

---

## 10. Estado de la 2ª iteración — ejecutada y validada
El notebook `stage_profiling_fase2.ipynb` ya se corrió. Su salida **confirma** todas las correcciones (C1–C5) y aportó números reales: semántica `Perdif` (1=días/2=meses/3=años/9=ignorado con `Edadif`=999), etnia `Puedif` con 16–19% Ignorado, **factibilidad de k-anonimato** (§7), jerarquía CIE-10 (3,087→1,102→23) con ~13.5% capítulo R, y cobertura de `Areag`. Las tablas de §5 y §7 ya están rellenadas con esos resultados. **No se requieren más pasadas de profiling** para construir Stage.

---

## 11. Limitaciones y trabajo diferido
- **Centinelas numéricos** y **códigos huérfanos**: se cuantifican en Stage con `stage.dim_diccionario` (9.2/9.6).
- **Calidad de causa:** ~13.5% de las muertes son capítulo R (mal definidas); reportarlo como caveat del análisis pre/post-COVID y del ML (C5).
- **Etnia incompleta:** `Puedif` con 16–19% Ignorado → limita el alcance del análisis étnico (H7).
- **`Areag`** solo cubre 2015–2017 → sin desglose urbano/rural post-COVID (C4).
- **Etiquetas confirmadas:** `Sexo`, `Perdif`, `Puedif`, `Escodif`, `Ecidif`, `Asist`, `Ocur`, `Cerdef`, `Edadif` y geografía ya están decodificadas por el diccionario (ver §14). Pendiente: las etiquetas de **`Areag`** (no está en el diccionario).
- **Decodificación a etiquetas y dimensiones**: trabajo del **DW/Gold** (D2), usando el diccionario de §14.

---

## 12. Bibliografía (referencias verificables para la defensa)

**Arquitectura por capas y transformación**
1. Databricks. *What is the medallion lakehouse architecture?* https://docs.databricks.com/aws/en/lakehouse/medallion
2. Microsoft. *What is the medallion lakehouse architecture?* Azure Databricks — Microsoft Learn. https://learn.microsoft.com/azure/databricks/lakehouse/medallion
3. dbt Labs. *How we structure our dbt projects* (capa *staging*). https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview

**Metodología de ciencia de datos**
4. Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C., & Wirth, R. (2000). *CRISP-DM 1.0: Step-by-step data mining guide.* SPSS Inc.

**Modelado dimensional (DW)**
5. Kimball, R., & Ross, M. (2013). *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling* (3rd ed.). Wiley.

**Calidad y perfilamiento de datos**
6. DAMA International. (2017). *DAMA-DMBOK: Data Management Body of Knowledge* (2nd ed.). Technics Publications.
7. DAMA UK Working Group. (2013). *The Six Primary Dimensions for Data Quality Assessment.*
8. Wang, R. Y., & Strong, D. M. (1996). *Beyond Accuracy: What Data Quality Means to Data Consumers.* Journal of Management Information Systems, 12(4), 5–33.
9. Olson, J. E. (2003). *Data Quality: The Accuracy Dimension.* Morgan Kaufmann.

**Privacidad y anonimización**
10. Sweeney, L. (2002). *k-anonymity: A model for protecting privacy.* International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems, 10(5), 557–570.
11. Reglamento (UE) 2023/2854 (**EU Data Act**), de 13 de diciembre de 2023. En vigor desde el 11/01/2024; aplicable desde el 12/09/2025. EUR-Lex: https://eur-lex.europa.eu/eli/reg/2023/2854 · Comisión Europea: https://digital-strategy.ec.europa.eu/en/policies/data-act
12. Reglamento (UE) 2016/679 (**GDPR**), arts. 5 (minimización) y 25 (protección por diseño y por defecto); Considerando 26 (anonimización). https://eur-lex.europa.eu/eli/reg/2016/679
13. Organización Internacional del Trabajo. *Convenio 169 sobre Pueblos Indígenas y Tribales* (1989).

> **Nota para la defensa (matiz jurídico):** el EU Data Act regula sobre todo datos de productos conectados/IoT y la compartición B2G de datos **no personales**; para **datos personales de salud** se aplica **junto al GDPR y subordinado a él** (es "sin perjuicio" del GDPR). Por eso, el fundamento legal **directo** de la anonimización de microdatos de mortalidad es el **GDPR (minimización + Considerando 26)** y el *statistical disclosure control* (k-anonimato, Sweeney 2002); el Data Act aporta el **marco de compartición/reutilización** hacia el organismo público (PNUD/MSPAS). Presentarlo así evita una observación del tutor.

**Estándares de dominio (salud)**
14. Organización Mundial de la Salud (OMS). *Clasificación Internacional de Enfermedades, 10.ª revisión (CIE-10).*
15. INE Guatemala. *Estadísticas Vitales — Defunciones.* https://datos.ine.gob.gt/dataset/estadisticas-vitales-defunciones

---

## 13. Trazabilidad metodológica (síntesis)
- **Medallion:** Bronze crudo → Stage/Silver conformado → DW/Gold (dimensional/agregación).
- **CRISP-DM:** *Data Understanding* (este profiling) justifica *Data Preparation* (construcción de Stage).
- **dbt staging:** renombrar/castear/categorizar sin cambiar el grano → decodificación diferida al DW.
- **6 dimensiones de calidad:** eje de §3, §9.6.
- **Privacidad:** k-anonimato (Sweeney) + GDPR (minimización) bajo el marco de compartición del EU Data Act.

*Fin del documento (versión 2 — Fase 2, con plan de anonimización integrado y corregido).*

---

## 14. Anexo — Catálogo de códigos confirmado (`bronze.gdrive_docs`)

Decodificación verificada contra el diccionario (reestructurado con *forward-fill*). Insumo directo para las dimensiones del DW y para definir los centinelas de "Ignorado" por columna.

**Centinela de faltante por columna (R-COMP-1):**

| Columna(s) | Código = "Ignorado" |
|---|---|
| `Puedif`, `Escodif`, `Ecidif`, `Asist`, `Ocur`, `Cerdef`, (`Areag`?) | `9` |
| `Edadif` | `999` |
| `Mes*`, `Dia*`, dígitos de edad | *no aplica* (`9`/`999` son valores reales) |

**Decodificación de categóricas (código → etiqueta):**

| Variable (col.) | Códigos |
|---|---|
| Sexo (`Sexo`) | 1=Hombre · 2=Mujer |
| Período de edad (`Perdif`) | 1=Menos de un mes · 2=1 a 11 meses · 3=1 año y más · 9=Ignorado |
| Pueblo/etnia (`Puedif`) | 1=Maya · 2=Garífuna · 3=Xinka · 4=Mestizo/Ladino · 5=Otro · 9=Ignorado |
| Estado civil (`Ecidif`) | 1=Soltero · 2=Casado · 3=Unido · 9=Ignorado |
| Escolaridad (`Escodif`) | 1=Ninguno · 2=Primaria · 3=Básica · 4=Diversificado · 5=Universitario · 6=Post grado · 9=Ignorado |
| Asistencia recibida (`Asist`) | 1=Médica · 2=Paramédica · 3=Comadrona · 4=Empírica · 5=Ninguna · 9=Ignorado |
| Sitio de ocurrencia (`Ocur`) | 1=Hospital público · 2=Hospital privado · 3=Centro de salud · 4=Seguro social · 5=Vía pública · 6=Domicilio · 7=Lugar de trabajo · 8=Otro · 9=Ignorado |
| Quién certifica (`Cerdef`) | 1=Médico · 2=Paramédico · 3=Autoridad · 9=Ignorado |
| Mes (`Mesocu`/`Mesreg`) | 1=Enero … 12=Diciembre |
| Edad (`Edadif`) | 0–120 (años) · **999=Ignorado** |
| Departamento (`Dep*`) | 1=Guatemala … 22=Jutiapa (22 deptos.) |
| Municipio (`Mup*`) | código de **4 dígitos con cero inicial** (`0101`=Guatemala …) — confirma R-CARD-1 (`lpad` a 4) |

> **`Areag` no figura en el diccionario** → sus etiquetas (urbano/rural/ignorado) deben confirmarse con el INE antes de usarse.
>
> Las variables geográficas (`Dep*`, `Mup*`) comparten catálogo entre roles (registro/ocurrencia/residencia/nacimiento) → respalda la **dimensión geográfica con roles** del DW (§8).
