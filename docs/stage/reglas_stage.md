# Reglas de Conformidad — Bronze a Stage

## Introducción

La transformación de Bronze a Stage implementa 12 reglas de conformidad, organizadas en 6 categorías de calidad de datos. Cada regla tiene:
- Código identificador (R- para "Regla" general, C- para "Caveat" o corrección específica)
- Fundamento técnico basado en EDA
- Implementación en SQL/PySpark
- Validación esperada

El resultado es `stage.defunciones`: una tabla única (919,231 registros, 2015–2024) limpia, tipada, estandarizada y lista para modelado dimensional.

---

## 1. Completitud (R-COMP)

### R-COMP-1: Normalización de centinelas por columna

**Descripción:**
Convierte códigos de "Ignorado" / "No especificado" a NULL de forma selectiva, respetando la semántica de cada columna.

**Regla:**
- Columnas categóricas con código `9` para "Ignorado": `Puedif`, `Escodif`, `Asist`, `Ocur`, `Cerdef`, `Ecidif`
  - `9` → NULL
- Columna edad: `Edadif=999` (edad desconocida) → NULL
- **NO aplicar:** `9` en `Mes` (que es Septiembre) o en `Día` (9 es un día válido)

**Impacto:**
- Mejora k-anonimato: valores "Ignorado" no son cuasi-identificadores útiles
- Precisión en análisis agregados (GROUP BY sin ruido)

**Ejemplo PySpark:**
```python
sentinela_9 = ["Puedif", "Escodif", "Asist", "Ocur", "Cerdef", "Ecidif"]
for col in sentinela_9:
    df = df.withColumn(col, 
        F.when(F.col(col) == "9", None).otherwise(F.col(col)))
df = df.withColumn("Edadif",
    F.when(F.col("Edadif") == "999", None).otherwise(F.col("Edadif")))
```

---

### R-COMP-2: Eliminación de columnas 100% vacías

**Descripción:**
En `bronze.json_oms` y `bronze.json_worldbank`, existen columnas completamente vacías (`Dim3`, `DataSourceDim`, etc.).

**Regla:**
Descartar columnas con 100% de valores faltantes o nulos.

**Impacto:**
Simplifica esquema de Stage; reduce confusión en diccionario de datos.

---

### R-COMP-3: Documentación de cobertura parcial

**Descripción:**
Columnas con faltantes parciales (`Ciuodif`, `Escodif` con 14.78% faltante en xlsx) se documentan sin imputación.

**Regla:**
- **No imputar** en Stage; marcar en metadatos
- Dejar NULL tal como está
- Reportar sesgo potencial en análisis

**Impacto:**
Transparencia en auditoría; decisiones sobre análisis no sesgado.

---

## 2. Unicidad (R-UNIQ)

### R-UNIQ-1: Deduplicación selectiva

**Descripción:**
A diferencia de tablas de entidades (clientes, productos), las defunciones son eventos. Dos registros idénticos pueden representar dos muertes reales (coincidencia); no se deduplican globalmente.

**Regla:**
- **No ejecutar** `dropDuplicates()` global
- Marcar registro con flag `dup_exacto` si es completamente idéntico a otro
- Mantener ambos en Stage para auditoría

**Evidencia EDA:**
- xlsx: 167 duplicados exactos (0.02%)
- legacy: 79 duplicados exactos (0.03%)

**Impacto:**
Preserva integridad de datos de mortalidad; permite auditoría posterior.

---

### R-UNIQ-2: Reestructuración del diccionario

**Descripción:**
La tabla `bronze.gdrive_docs` contiene el diccionario CIE-10 con 64.94% de duplicados exactos (artefacto de estructura).

**Regla:**
- Reestructurar tabla de diccionario (no es hecho; es dimensión)
- Eliminar duplicados con `SELECT DISTINCT`
- Crear tabla `stage.dim_diccionario` de referencia para validaciones

**Impacto:**
Diccionario limpio para joins con `Caudef` sin amplificación de filas.

---

## 3. Validez (R-VALID)

### R-VALID-1: Normalización de artefacto float (Corrección fundamental)

**Descripción:**
Los datos legacy (SAV, 2015–2017) guardaron valores numéricos como punto flotante: `"1.0"`, `"0101.0"`.

**Regla:**
Aplicar **antes de cualquier otro procesamiento**:
```python
def norm_float(df):
    for col in df.columns:
        if col.startswith("_"):  # Excluir metadata
            continue
        df = df.withColumn(col,
            F.when(F.lower(F.trim(F.col(col))).isin("nan", "none", ""), None)
             .otherwise(F.regexp_replace(F.col(col), r"\.0$", "")))
    return df
```

**Impacto:**
- Sexo: {`"1.0"`, `"2.0"`} → {`1`, `2`}
- Municipios: `"0101.0"` → `"0101"` (sin pérdida de ceros)
- Prerequisito para k-anonimato y joins

---

### R-VALID-2: Recuperación de ceros iniciales en geografía

**Descripción:**
Municipios en el legacy se pueden haber perdido ceros iniciales durante conversión.

**Regla (R-CARD-1):**
```sql
LPAD(municipio, 4, '0')  -- Garantiza formato '0101'...'2201'
```

**Impacto:**
Garantiza joins correctos con catálogos de municipios en dim_geografia.

---

### R-VALID-3: Validación de dominio — Sexo

**Descripción:**
Sexo debe estar en {1=Hombre, 2=Mujer}. Cualquier otro valor es error de codificación.

**Regla:**
```python
df = df.withColumn("sexo",
    F.when(F.col("Sexo").isin("1", "2"), F.col("Sexo").cast("int"))
     .otherwise(None))
```

**Impacto:**
- Elimina ruido; facilita análisis por género
- ~100% de validez en datos (solo desviaciones mínimas)

---

### R-VALID-4: Validación y estandarización de causa CIE-10

**Descripción:**
El 100% de `Caudef` está en formato CIE-10. Se estandariza (mayúsculas, trim) y se preserva jerarquía.

**Regla:**
```python
df = df.withColumn("caudef", 
    F.trim(F.upper(F.col("Caudef"))))
```

**Jerarquía preservada en dim_causa_cie10:**
- Nivel 4: Código completo (ej: U071, R992)
- Nivel 3: Categoría (ej: U07, R99)
- Nivel 1: Capítulo (ej: U, R)

**Impacto:**
Habilita análisis multidimensional por capítulo, categoría o código específico.

---

## 4. Consistencia (R-CONS)

### R-CONS-1: Construcción de fecha de ocurrencia validada

**Descripción:**
Los campos `Diaocu`, `Mesocu`, `Añoocu` pueden tener errores de fecha (30 de febrero, etc.).

**Regla:**
```sql
fecha_ocurrencia = TRY_TO_DATE(
    CONCAT(LPAD(Diaocu, 2, '0'), '-', LPAD(Mesocu, 2, '0'), '-', Añoocu),
    'dd-MM-yyyy'
)
```

- Conversión segura: fechas inválidas → NULL
- Detecta errores de tipeo (ej: mes=13)

**Impacto:**
Garantiza integridad temporal para análisis time-series.

---

### R-CONS-2: Primacía de "ocurrencia" sobre "registro"

**Descripción:**
Existen dos marcas de tiempo: ocurrencia de defunción vs. registro administrativo. Para epidemiología, importa la **ocurrencia**.

**Regla:**
- Dimensión temporal: construida desde `Año/Mes/Día de ocurrencia` (R-CONS-1)
- Conservar `Año/Mes de registro` en linaje para auditoría
- Partición de fact: por año de ocurrencia

**Impacto:**
Análisis correcto de tendencias pre/post-COVID (evita sesgo por rezagos administrativos).

---

### R-CONS-3: Metadatos de linaje

**Descripción:**
Las columnas `_anio`, `_archivo_origen`, `_fuente` se preservan sin modificación (transporte de linaje).

**Regla:**
- No tocar columnas que comienzan con `_`
- Conservarlas en Stage para trazabilidad
- Están disponibles para auditoría (git blame + esta tabla)

**Impacto:**
Toda fila puede rastrearse a su archivo de origen y año de ingesta.

---

## 5. Exactitud (Correcciones semánticas — C1 a C6)

### C1: Separación de pueblo (etnia) de período de edad

**Descripción:**
`Perdif` (período de edad: 1=días, 2=meses, 3=años) fue mal interpretado como etnia.

**Corrección:**
- `Puedif` = pueblo/etnia real
- `Perdif` = unidad de edad (no se nulifica; es necesaria para normalizar `Edadif`)

**Impacto en Stage:**
- Columna `Puedif` tal cual (con sentinela 9→NULL por R-COMP-1)
- Columna `edad_anios` derivada de `Edadif` + `Perdif` (ver C2)

---

### C2: Normalización de edad a años

**Descripción:**
`Edadif` tiene 3 unidades posibles según `Perdif`. Normalizar a años evita sesgos.

**Regla:**
```python
df = df.withColumn("edad_anios",
    F.when(F.col("Perdif") == 3, F.col("Edadif").cast("int"))  # ya está en años
     .when(F.col("Perdif").isin(1, 2), None)  # días/meses → NULL, se marca como <1 año en dim_grupo_etario
     .when(F.col("Perdif") == 9, None))  # ignorado
```

**Grupo etario derivado:**
```python
df = df.withColumn("grupo_etario",
    F.when((F.col("Perdif").isin(1, 2)) | (F.col("edad_anios") < 1), "0-Menor de 1 año")
     .when((F.col("edad_anios") >= 1) & (F.col("edad_anios") <= 4), "1-1 a 4 años")
     ...
     .when(F.col("edad_anios") >= 65, "6-65 y más años")
     .otherwise(None))
```

**Impacto:**
- ~46,000 registros infantiles (días/meses) se clasifican correctamente en <1 año
- Mortalidad infantil se analiza de forma precisa

---

### C3: Unificación y normalización pre-k-anonimato

**Descripción:**
Antes de cualquier técnica de anonimización, converger artefactos y estandarizar:
- Floats normalizados (R-VALID-1)
- Centinelas a NULL (R-COMP-1)
- Ceros iniciales recuperados (R-VALID-2)

**Prerequisito:**
k-anonimato requiere quasiidentificadores limpios.

---

### C4: Limitación de análisis urbano/rural

**Descripción:**
`Areag` solo existe 2015–2017 (Hallazgo H5).

**Regla:**
- Se incluye en `dim_geografia` como nullable
- Análisis urbano/rural: solo 2015–2017, o imputación consciente con caveat

**Impacto en Stage:**
Columna Areag se preserva; NULL para 2018–2024.

---

### C5: Flag de causa mal definida

**Descripción:**
~13.5% de defunciones tienen `Caudef` en capítulo R (síntomas, signos, hallazgos anormales — mal definido).

**Regla en Stage:**
```python
df = df.withColumn("es_mal_definida",
    F.when(F.substring(F.col("caudef"), 1, 1) == "R", True)
     .otherwise(False))
```

**Impacto:**
Permite análisis filtrado (excluyendo causas mal definidas) para estudios de precisión epidemiológica.

---

### C6: Cobertura documentada de etnia

**Descripción:**
Etnia (`Puedif`) tiene ~16–19% "Ignorado" (Hallazgo H7).

**Regla:**
- Se convierte a NULL por R-COMP-1
- Se reporta % de faltantes por año en metadatos
- Análisis por etnia: solo con n ≥ 5

**Impacto:**
Análisis desagregado étnico con garantía de privacidad y representatividad.

---

## 6. Vigencia / Temporalidad (R-TEMP)

### Marca de período: PRE-COVID vs POST-COVID

**Descripción:**
Para análisis comparativo, se marca cada registro con su período.

**Regla:**
```python
df = df.withColumn("periodo",
    F.when(F.col("anio") <= 2019, "PRE_COVID")
     .when(F.col("anio") >= 2020, "POST_COVID")
     .otherwise(None))
```

**Períodos definidos:**
- PRE-COVID: 2015–2019 (245,167 registros)
- POST-COVID: 2020–2024 (674,064 registros)

**Impacto:**
Habilita análisis de comparación pre/post en todas las dimensiones.

---

## Resultado final de Stage

Al aplicar estas 12 reglas, se obtiene:

| Aspecto | Garantía |
|---|---|
| Registros | 919,231 filas, sin deduplicación destructiva |
| Esquema | Tipado, normalizado, 40+ columnas conformadas |
| Calidad | Completo, único (con marcas), válido, consistente, exacto, vigente |
| Linaje | Conservado en metadatos (`_anio`, `_archivo_origen`, `_fuente`) |
| Anonimización | Prerequisito: centinelas nulificados, quasiidentificadores limpios |
| Auditoría | Reproducible mediante código comentado (git blame disponible) |

La tabla `stage.defunciones` está lista para modelado dimensional.
