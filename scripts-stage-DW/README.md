# Plataforma Analítica de Mortalidad — ETL Bronze → Stage → DW

> **Proyecto:** Plataforma Analítica de Mortalidad End-to-End — PNUD / MSPAS
> **Fase 2:** Transformación, arquitectura por capas y almacenamiento
> **Plataforma:** Databricks (Lakehouse, Serverless) · Modelo dimensional en Oracle SQL Developer Data Modeler
> **Alcance de este documento:** tramo **Bronze → Stage → DW (modelo estrella)** y la generación del ERD. No cubre ML ni BI (Fase 3).

Este README es la **guía maestra** para reproducir y documentar el proceso ETL. Está dirigido a quien continúe la documentación formal del proyecto: contiene el contexto, las decisiones de diseño con su justificación, los pasos exactos de ejecución y los resultados esperados para validar cada etapa.

---

## 1. Resumen del proceso

El pipeline toma microdatos crudos de defunciones del INE Guatemala (2015–2024) y los lleva, por capas, hasta un modelo dimensional analítico:

```
Bronze (crudo, Delta)  →  Stage (conformado, limpio)  →  DW (modelo estrella)  →  ERD (Data Modeler)
   [ya existía]              etl_bronze_to_stage           etl_stage_to_dw         dw_modelo_estrella.sql
```

| Capa | Qué contiene | Quién la crea |
|---|---|---|
| **Bronze** | Datos crudos sin validar, todas las columnas como `string`. Origen S3 vía Delta. | Fase 1 (ya existe) |
| **Stage** | Una tabla `stage.defunciones` limpia, tipada, estandarizada (919,231 filas). | `etl_bronze_to_stage.ipynb` |
| **DW** | Esquema estrella: 1 tabla de hechos + 7 dimensiones. | `etl_stage_to_dw.ipynb` |
| **ERD** | Diagrama entidad-relación del modelo estrella. | `dw_modelo_estrella.sql` + Data Modeler |

**Marco metodológico:** arquitectura *medallion* (Bronze→Silver→Gold), CRISP-DM (*Data Understanding* → *Data Preparation*), modelado dimensional de Kimball, y las 6 dimensiones de calidad de datos (Completitud, Unicidad, Validez, Consistencia, Exactitud, Vigencia).

> **Nota de nomenclatura:** en la documentación, **"Stage" = capa conformada** (equivalente a *Silver* en medallion). El **DW** es el modelo estrella (equivalente a *Gold*).

---

## 2. Estructura de archivos del entregable

| Archivo | Tipo | Descripción |
|---|---|---|
| `etl_bronze_to_stage.ipynb` | Notebook Databricks | ETL de limpieza y conformación. Produce `stage.defunciones`. |
| `etl_stage_to_dw.ipynb` | Notebook Databricks | ETL dimensional. Produce las 8 tablas `dw.*`. |
| `consultas_prueba_dw.ipynb` | Notebook Databricks | 7 consultas analíticas de validación del DW. |
| `dw_modelo_estrella.sql` | DDL SQL | Definición del modelo estrella con PK/FK, para importar en Data Modeler. |
| `reporte_bronze_a_stage_v2_fase2.md` | Reporte EDA | Perfilamiento de Bronze y justificación de cada regla de limpieza. **Fuente de verdad de las decisiones.** |
| `README.md` | Este archivo | Guía maestra de reproducción y documentación. |

---

## 3. Datos de origen (Bronze)

| Tabla Bronze | Filas | Columnas | Rol |
|---|---:|---:|---|
| `bronze.xlsx_ine` | 674,064 | 30 | Defunciones INE 2018–2024 |
| `bronze.sav_ine_legacy` | 245,167 | 31 | Defunciones INE 2015–2017 (incluye `Areag`) |
| `bronze.json_oms` | 1,708 | 27 | Referencia OMS (no usada en este tramo) |
| `bronze.json_worldbank` | 450 | 10 | Referencia Banco Mundial (no usada en este tramo) |
| `bronze.gdrive_docs` | 1,837 | 5 | Diccionario de variables |

> Total de defunciones a consolidar: **919,231** (2015–2024).

**Catálogo de columnas INE clave** (las que usa el ETL):

| Columna origen | Significado | Notas |
|---|---|---|
| `Añoocu` / `Mesocu` / `Diaocu` | Fecha de **ocurrencia** | Nombres con tilde/ñ → requieren backticks en SQL |
| `Depocu` / `Mupocu` | Depto. / municipio de **ocurrencia** | Municipio = 4 dígitos con cero inicial |
| `Sexo` | Sexo | 1=Hombre, 2=Mujer |
| `Edadif` | Edad del difunto | **Su unidad depende de `Perdif`** |
| `Perdif` | **Unidad de edad** (NO etnia) | 1=días, 2=meses, 3=años, 9=ignorado |
| `Puedif` | **Pueblo/etnia** (la etnia real) | 1=Maya, 2=Garífuna, 3=Xinka, 4=Mestizo/Ladino, 5=Otro, 9=Ignorado |
| `Caudef` | Causa de defunción | Formato CIE-10 (100% válido) |
| `Escodif` / `Ecidif` | Escolaridad / estado civil | 9=Ignorado |
| `Ocur` / `Asist` / `Cerdef` | Sitio / asistencia / certificador | 9=Ignorado |
| `Areag` | Área urbano/rural | **Solo existe en legacy 2015–2017** |

---

## 4. Hallazgos del EDA que determinan las reglas de limpieza

Las reglas del ETL **no son genéricas**: derivan del perfilamiento documentado en `reporte_bronze_a_stage_v2_fase2.md`. Estos son los hallazgos críticos y cómo se traducen en código. **Para la documentación, esta es la sección más importante: explica el *porqué* de cada transformación.**

| ID | Hallazgo | Regla de limpieza derivada |
|---|---|---|
| **H1** | La única diferencia de esquema entre las dos tablas INE es `Areag`. | Se unifican en una sola `stage.defunciones`; a `xlsx` se le agrega `Areag = NULL`. |
| **H2 / C3** | El legacy 2015–2017 trae **artefacto float**: `"1.0"` en vez de `"1"`, `"101.0"` en municipios. | `norm_float()` quita el sufijo `.0` **antes** de unir. Crítico: sin esto el mismo municipio se parte en dos grupos. |
| **H3 / C1** | `Perdif` **no es etnia**: es la unidad de edad. La etnia es **`Puedif`**. | La dimensión de etnia se construye sobre `Puedif`, no `Perdif`. |
| **H4 / C2** | `Edadif` está en días/meses/años según `Perdif`; ~46 mil registros no están en años. | Se calcula `edad_anios` usando `Perdif` antes de agrupar por edad. **Sin esto, ~46 mil infantes quedan mal clasificados.** |
| **H5 / C4** | `Areag` (urbano/rural) **solo existe 2015–2017**. | Se conserva como `area`, NULL para 2018–2024. Limitación documentada del análisis urbano/rural. |
| **H6** | `Caudef` es **100% formato CIE-10** válido; jerarquía 3,087 códigos → 1,102 categorías → 23 capítulos. | **NO** se filtra `Caudef` por longitud. La jerarquía alimenta `dim_causa_cie10`. |
| **H7** | La etnia (`Puedif`) tiene **16–19% de "Ignorado"** (código 9). | Se convierte `9 → NULL` antes de cualquier análisis étnico. |

### Errores del código de ejemplo del enunciado (corregidos en estos notebooks)

> Documentar estos puntos demuestra criterio técnico en la defensa. El código de ejemplo del enunciado contenía cinco errores que el propio EDA desmiente:

1. **Unión sin normalizar el float** → datos rotos. *Corrección:* `norm_float()` antes de `unionByName`.
2. **Edad tratada como años siempre** → ~46 mil infantes mal clasificados. *Corrección:* `edad_anios` con `Perdif`.
3. **`Sexo` admitía el valor 9** que no existe en el dominio. *Corrección:* dominio {1,2}, resto NULL.
4. **Filtro `caudef < 3 chars → NULL`** que contradice el hallazgo H6. *Corrección:* eliminado.
5. **Faltaba nulificar centinelas "Ignorado"** (9/999) por columna. *Corrección:* aplicado según diccionario.

---

## 5. Reglas de conformación aplicadas (Bronze → Stage)

Referencia rápida de cada regla con su código (las siglas remiten al reporte EDA §3 y §6):

| Regla | Descripción | Implementación |
|---|---|---|
| **R-VALID-1** | Corregir artefacto float antes de unir. | `norm_float()`: `regexp_replace(col, r"\.0$", "")` + `nan/none/"" → NULL`. |
| **R-CARD-1** | Municipio a 4 dígitos. | `lpad(Mupocu, 4, '0')`. |
| **R-CONS-1** | Construir fecha de ocurrencia validada. | `try_to_date(concat(...), 'dd-MM-yyyy')` sobre día/mes/año de ocurrencia. |
| **R-CONS-2** | Usar **ocurrencia** (no registro) como dimensión temporal. | `anio = Añoocu`, partición por `anio`. |
| **R-VALID-2 / C2** | `edad_anios` desde `Edadif` + `Perdif`. | `Perdif=3→años`; `Perdif∈{1,2}→0` (<1 año); `Perdif=9→NULL`. |
| **R-VALID-3** | Dominio de `Sexo` = {1,2}. | Otros valores → NULL. |
| **R-VALID-4** | `Caudef` en mayúsculas y sin espacios. | `trim(upper(Caudef))`. |
| **R-COMP-1** | Centinela "Ignorado" → NULL por columna. | `9→NULL` en `Puedif`, `Escodif`, `Asist`, `Ocur`, `Cerdef`, `Ecidif`. **No** en Mes/Día. |
| **R-UNIQ-1** | No deduplicar a ciegas (no hay ID único). | Marcar `dup_exacto = false`; no `dropDuplicates` global. |
| **periodo** | Marca pre/post-COVID. | `anio <= 2019 → PRE_COVID`, si no `POST_COVID`. |

**Filtros de validez finales:** `anio ∈ [2015, 2024]` y `depto ∈ [1, 22]`.

### Esquema resultante de `stage.defunciones` (23 columnas)

```
anio, mes, dia, fecha_ocurrencia, periodo,          -- temporales
depto, muni_ocu, muni_reg,                           -- geografía
caudef,                                              -- causa CIE-10
sexo, edad_anios, perdif, pueblo, escolaridad, estado_civil,  -- demografía
sitio_ocurrencia, asistencia, certificador, area,    -- lugar/certificación
dup_exacto,                                          -- control
lin_anio_archivo, lin_archivo, lin_fuente            -- linaje
```

Partición: por `anio`. Formato: Delta.

---

## 6. Modelo estrella (Stage → DW)

Grano del hecho: **una defunción**. Una tabla de hechos central rodeada de 7 dimensiones.

```
                  dim_tiempo   dim_sexo   dim_pueblo
                       \          |          /
        dim_geografia ── fact_defunciones ── dim_grupo_etario
                       /          |          \
              dim_causa_cie10  dim_lugar
```

| Tabla | Filas | Llave | Descripción |
|---|---:|---|---|
| `fact_defunciones` | 919,231 | (7 FKs + medida) | Una fila por defunción. Medida = `cantidad` (1). |
| `dim_tiempo` | 120 | `id_tiempo` (AAAAMM) | 10 años × 12 meses. Trimestre y periodo COVID. |
| `dim_geografia` | 1,348 | `id_geografia` | depto + municipio + área (urbano/rural). |
| `dim_causa_cie10` | 3,087 | `id_causa` | Jerarquía CIE-10: completo(4)→categoría(3)→capítulo(1) + flag `mal_definida`. |
| `dim_sexo` | 3 | `id_sexo` | 1=Hombre, 2=Mujer, 9=Ignorado. |
| `dim_grupo_etario` | 8 | `id_grupo_etario` | 7 grupos OPS + "No especificado". |
| `dim_pueblo` | 6 | `id_pueblo` | Etnia (`Puedif` decodificado). |
| `dim_lugar` | 129 | `id_lugar` | Sitio + asistencia médica + certificador. |

**Decisiones de diseño dimensional:**
- `dim_grupo_etario` se construye sobre `edad_anios` (ya corregida con `Perdif`), con bucket "No especificado" (id=9) para `edad_anios IS NULL`.
- `dim_sexo` y `dim_pueblo` están **separadas** (corrige la confusión `Perdif`/`Puedif`).
- Las FKs demográficas usan `COALESCE(..., 9)` para apuntar a filas "Ignorado"/"No especificado" en lugar de quedar huérfanas.
- `periodo` se conserva como *degenerate dimension* en el hecho.

---

## 7. Cómo reproducir el proceso (paso a paso)

### 7.1 Requisitos previos

- Acceso al workspace de Databricks con compute **Serverless**.
- **Permisos de escritura** (`CREATE SCHEMA`, `CREATE TABLE`) en el catálogo `workspace`.
  > Como colaborador, la lectura de `bronze` suele venir por defecto, pero la escritura para crear `stage` y `dw` debe solicitarse al administrador del catálogo.
- Las tablas Bronze ya cargadas (Fase 1).

### 7.2 Configuración del catálogo

El `bronze` del proyecto vive en `workspace.bronze`. **Agregar como primera celda de cada notebook:**

```python
spark.sql("USE CATALOG workspace")
```

Esto hace que `bronze.x`, `stage.x` y `dw.x` se resuelvan dentro del catálogo correcto. Verificar con:

```python
spark.sql("SELECT current_catalog()").show()   # debe decir: workspace
spark.sql("SHOW SCHEMAS IN workspace").show()   # debe listar: bronze, default, ...
```

### 7.3 Orden de ejecución

1. **Importar** los notebooks en Workspace (no en Catalog): `Workspace → Import`.
2. **Conectar** cada notebook al compute Serverless (círculo verde).
3. Ejecutar **`etl_bronze_to_stage.ipynb`** celda por celda, en orden. Revisar el checklist final.
4. Solo si el checklist pasa, ejecutar **`etl_stage_to_dw.ipynb`**. Revisar la integridad referencial.
5. (Opcional) Ejecutar **`consultas_prueba_dw.ipynb`** para validar analíticamente.
6. Importar **`dw_modelo_estrella.sql`** en Oracle Data Modeler para el ERD (§8).

> **Nota sobre Spark "perezoso":** las transformaciones no se ejecutan hasta que una acción (`.count()`, `.show()`, `saveAsTable`) las fuerza. Por eso un error de una celda puede aparecer en una celda posterior. Si algo falla, revisar la celda donde se *definió* la operación, no solo donde estalló.

### 7.4 Resultados esperados (criterios de aceptación)

**Checklist de `etl_bronze_to_stage`:**
```
[1] filas totales: 919,231          (esperado ~919,231)
[2] dominio sexo: [1, 2]            (esperado [1, 2])
[3] muni_ocu con longitud != 4: 0   (esperado 0)
[4] perdif=9: 3,297 | edad_anios NULL: 3,297  (deben coincidir)
[5] caudef no nulo: 919,231 (100.0%)
    periodo: PRE_COVID=413,838 | POST_COVID=505,393
```

**Carga de `etl_stage_to_dw`:**
```
fact_defunciones: 919,231 | dim_tiempo: 120 | dim_geografia: 1,348
dim_causa_cie10: 3,087 | dim_sexo: 3 | dim_grupo_etario: 8
dim_pueblo: 6 | dim_lugar: 129
Integridad referencial: 0 huérfanos en las 7 dimensiones.
```

---

## 8. Limitaciones documentadas (caveats para el análisis)

Estos puntos deben constar en la documentación y tenerse en cuenta para la Fase 3 (ML/BI):

- **Causas mal definidas:** ~13.5% de las muertes son capítulo R (síntomas/hallazgos mal definidos). Es un indicador de calidad del registro de causa; no atribuir a una causa concreta.
- **Etnia incompleta:** `Puedif` tiene 16–19% de "Ignorado" → limita el alcance del análisis étnico.
- **Urbano/rural parcial:** `Areag` solo cubre 2015–2017, sin desglose post-COVID. Además, sus etiquetas no figuran en el diccionario (confirmar con INE antes de usarlas).
- **Sin ID único:** las defunciones no tienen folio; dos filas idénticas pueden ser dos muertes reales (no se deduplica a ciegas).
- **Cobertura parcial:** `Ciuodif`/`Escodif` con ~14.78% de faltantes en 2018–2024; no se imputa en Stage.

---

## 10. Trabajo pendiente / próximos pasos

- **Capa anonimizada (Gold):** construir `stage.defunciones_anon` o vistas con k-anonimato (k≥5) sobre `Puedif` y generalización de CIE-10. El EDA confirma factibilidad: municipio+año+etnia suprime <1% a k=5. Fundamento legal: GDPR (minimización, Considerando 26) + k-anonimato (Sweeney 2002).
- **Decodificación a etiquetas:** unir las dimensiones con `stage.dim_diccionario` para mostrar descripciones legibles (Maya, Hospital público, etc.) en lugar de códigos.
- **Réplica nube + local:** el DW debe quedar accesible en ambos entornos (requisito Fase 2).
- **Tablas de referencia OMS/World Bank:** `stage.oms_indicadores` y `stage.worldbank_indicadores` (ver §9.5 del reporte EDA) para benchmarking internacional.

---

## 11. Glosario rápido

| Término | Significado |
|---|---|
| **Medallion** | Arquitectura por capas: Bronze (crudo) → Silver/Stage (limpio) → Gold/DW (analítico). |
| **Esquema estrella** | Modelo dimensional con una tabla de hechos central y dimensiones alrededor. |
| **Grano** | Nivel de detalle de una fila del hecho. Aquí: una defunción. |
| **Degenerate dimension** | Atributo descriptivo guardado en el hecho sin tabla de dimensión propia (ej. `periodo`). |
| **Artefacto float** | Códigos guardados como `"1.0"` por conversión float→string en el legacy. |
| **Centinela** | Código que representa "Ignorado"/faltante (9, 99, 999 según la columna). |
| **k-anonimato** | Técnica de privacidad: cada combinación de cuasi-identificadores aparece ≥ k veces. |
| **Serverless** | Compute de Databricks sin clúster dedicado; read-only sobre Bronze, sin credenciales S3. |

---

*Documento de referencia para la documentación formal del proceso ETL Bronze → Stage → DW (Fase 2). Las decisiones de limpieza están justificadas en `reporte_bronze_a_stage_v2_fase2.md`.*
