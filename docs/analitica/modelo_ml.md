# Modelo de Machine Learning

## Visión General

El pipeline de ML se compone de **tres notebooks secuenciales** ejecutados en **Databricks Serverless** con trazabilidad completa vía **MLflow**:

| # | Notebook | Rol | Salida |
|---|---|---|---|
| **1** | Feature Engineering | Aplana el esquema estrella en tablas listas para entrenar | `ml.dataset_defunciones`, `ml.dataset_mensual_depto_causa` |
| **2** | Regresión Logística | Clasificación binaria pre/post-COVID | Pesos JSON + registro MLflow |
| **3** | Regresión Ridge (L2) | Pronóstico de defunciones mensuales | Pesos JSON + registro MLflow |

Los notebooks 2 y 3 consumen las tablas producidas por el notebook 1 — ninguno repite el join contra el esquema estrella.

---

## Notebook 1 — Feature Engineering desde el DW

### Propósito

Los modelos lineales supervisados (Regresión Logística, Ridge) requieren una tabla con una fila por observación, columnas predictoras y una columna objetivo. Ningún algoritmo lineal puede operar directamente sobre un esquema estrella con joins — primero hay que **aplanarlo** en una única tabla de entrenamiento. Esta es la práctica estándar en pipelines ML sobre Spark/Databricks antes de vectorizar con `VectorAssembler`.

### Problema elegido y respaldo metodológico

Se eligió **detección de cambios estructurales pre/post-COVID** como problema de negocio, operacionalizado como **clasificación binaria**: dado un registro de defunción con sus atributos demográficos, geográficos y de causa, predecir si pertenece al período PRE\_COVID (2015–2019) o POST\_COVID (2020–2024).

Esta elección tiene respaldo metodológico formal: la OMS estima el impacto de la pandemia comparando la mortalidad observada contra una línea base construida con datos pre-pandemia, exactamente la misma dicotomia temporal que ya usa la columna `periodo` del modelo dimensional de la Fase 2 (Msemburi et al., *Nature*, 2023; WHO, 2021).

Complementariamente (notebook 3) se aplica **Regresión Ridge** sobre conteos mensuales agregados, alineado con el enfoque de regresión lineal para proyectar mortalidad esperada que la literatura de exceso de mortalidad reconoce como método válido junto a splines, Poisson y modelos Serfling.

### Decisiones de selección de features

```sql
SELECT
    f.id_sexo,
    f.id_grupo_etario,
    f.id_pueblo,
    f.periodo,
    t.anio,
    t.mes,
    t.trimestre,
    g.codigo_depto,       -- 22 valores (no codigo_muni: 1,348 valores, cardinalidad inmanejable)
    c.capitulo_1,         -- 23 valores (no codigo_completo: 3,087 valores distintos)
    c.mal_definida,
    l.tipo_lugar,
    l.asistencia_medica
FROM dw.fact_defunciones f
JOIN dw.dim_tiempo t        ON f.id_tiempo = t.id_tiempo
JOIN dw.dim_geografia g     ON f.id_geografia = g.id_geografia
JOIN dw.dim_causa_cie10 c   ON f.id_causa = c.id_causa
JOIN dw.dim_lugar l         ON f.id_lugar = l.id_lugar
```

Se excluyen explícitamente `codigo_muni` (1,348 valores) e `id_causa` / `codigo_completo` (3,087 valores) — su alta cardinalidad produciría un espacio de features inmanejable con `OneHotEncoder`. Se usa en su lugar `codigo_depto` (22 valores) y `capitulo_1` (23 valores), la generalización CIE-10 ya validada en el EDA de la Fase 2.

`anio` se mantiene como feature continua para que el modelo aprenda la tendencia temporal además del propio label binario derivado del año.

### Construcción del label y verificación de balance

```python
ml_base = (
    ml_base
    .withColumn("label_post_covid",
        F.when(F.col("periodo") == "POST_COVID", F.lit(1.0)).otherwise(F.lit(0.0)))
    .withColumn("mal_definida_int", F.col("mal_definida").cast("int"))
)

# Verificación de balance antes de entrenar
ml_base.groupBy("periodo", "label_post_covid").count().orderBy("periodo").show()
```

Antes de entrenar cualquier clasificador binario es obligatorio verificar el balance del target. Un desbalance fuerte (p. ej. 95/5) exigiría técnicas adicionales (class weights, submuestreo) que no son necesarias si el balance es razonable.

### Persistencia como tablas Delta

```python
# Tabla 1: registro individual — insumo para clasificación (Notebook 2)
ml_base.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("ml.dataset_defunciones")

# Tabla 2: agregado mensual — insumo para pronóstico (Notebook 3)
# Grano: departamento × capítulo CIE-10 × mes
mensual.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("ml.dataset_mensual_depto_causa")
```

Las tablas se materializan en formato Delta para que los notebooks 2 y 3 las consuman sin repetir el join, siguiendo el mismo patrón de capas ya usado en el pipeline Stage → DW de la Fase 2.

---

## Decisiones Transversales de Diseño (Notebooks 2 y 3)

### Por qué L2 (Ridge) y no L1 (Lasso)

Las variables predictoras en ambos modelos son categóricas, codificadas con `StringIndexer` + `OneHotEncoder`. Este proceso genera columnas **mutuamente correlacionadas** dentro de cada grupo (las dummies de un mismo campo son excluyentes entre sí). La regularización L1 (Lasso) en presencia de multicolinealidad tiende a eliminar arbitrariamente una de las variables correlacionadas. Ridge (L2) distribuye el peso entre ellas de forma suave sin anular ninguna — el comportamiento correcto para grupos de variables categóricas codificadas.

### Pipeline de *features* separado del modelo final

Spark Connect ML (motor de Databricks Serverless) impone un límite documentado de **256 MB** sobre cualquier objeto de modelo serializado (`CONNECT_ML.MODEL_SIZE_OVERFLOW_EXCEPTION`). Un `Pipeline` que encadena `StringIndexer` + `OneHotEncoder` + el estimador final supera ese límite al guardarse, aunque los coeficientes matemáticos pesen apenas unos kilobytes.

La solución adoptada en ambos notebooks separa el proceso en dos pasos:

1. **Pipeline de features** — se ajusta *solo* sobre el conjunto de entrenamiento y se usa para transformar train y test. No se persiste.
2. **Modelo final** — se ajusta sobre los datos ya transformados. Solo este objeto se guarda, porque su tamaño real (un vector de coeficientes) está muy por debajo del límite.

Esta separación preserva la propiedad de no fuga de datos: el pipeline de features nunca se entera de las distribuciones del conjunto de prueba.

### Persistencia de pesos

Los pesos de cada modelo se guardan como JSON liviano en `/Volumes/workspace/ml/modelos/`. En un modelo lineal, los pesos *son* el vector de coeficientes más el intercepto.

---

## Notebook 2 — Regresión Logística: Clasificación Pre/Post-COVID

### Problema de negocio

Dado un registro de defunción (sexo, grupo etario, etnia, departamento, capítulo de causa CIE-10, mes, tipo de lugar y nivel de asistencia médica), predecir si pertenece al período **PRE\_COVID (2015–2019)** o **POST\_COVID (2020–2024)**.

La Regresión Logística fue elegida sobre modelos de caja negra porque sus coeficientes son directamente legibles como el efecto de cada categoría sobre la probabilidad del evento — un requisito de interpretabilidad para un informe de política pública donde el cliente necesita explicaciones, no solo predicciones.

### Variables predictoras

```python
cat_cols = [
    "id_sexo", "id_grupo_etario", "id_pueblo", "mes", "trimestre",
    "codigo_depto", "capitulo_1", "tipo_lugar", "asistencia_medica"
]
# + variable binaria: mal_definida_int
```

### Partición train/test

```python
train_raw, test_raw = ml.randomSplit([0.8, 0.2], seed=42)
# Train: 735,384 registros | Test: 183,847 registros
```

### Configuración del modelo

```python
lr = LogisticRegression(
    featuresCol="features",
    labelCol="label_post_covid",
    maxIter=50,
    regParam=0.01,        # fuerza de regularización L2
    elasticNetParam=0.0,  # 0.0 = L2 puro (Ridge-style sobre la logística)
)
```

### Métricas de evaluación

| Métrica | Valor |
|---|---|
| Registros de entrenamiento | 735,384 |
| Registros de prueba | 183,847 |
| **Área bajo la curva ROC (AUC)** | **0.6171** |
| Exactitud (*Accuracy*) | 0.5867 |
| Puntuación F1 | 0.6656 |

Un AUC de 0.617 indica capacidad discriminativa real entre ambos períodos, moderada pero esperable: la mayoría de las causas de muerte no cambian radicalmente con la ocurrencia de una pandemia.

### Trazabilidad MLflow

```python
mlflow.set_experiment("/Shared/mortalidad_logistic_periodo")
# Parámetros: técnica, regParam, elasticNetParam, maxIter, features
# Métricas: auc, accuracy, f1
```

### Persistencia

```python
# /Volumes/workspace/ml/modelos/logistic_periodo_pesos.json
pesos = {
    "modelo": "LogisticRegression",
    "coeficientes": [...],
    "intercepto": ...,
    "features_categoricas": cat_cols,
    "regParam": 0.01,
    "elasticNetParam": 0.0,
    "mlflow_run_id": run_id,
}
```

---

## Notebook 3 — Regresión Ridge: Pronóstico de Defunciones Mensuales

### Problema de negocio

Pronosticar el **conteo mensual de defunciones** para una combinación departamento × capítulo CIE-10. El modelo se entrena sobre 2015–2022 y se evalúa sobre 2023–2024, operacionalizando el enfoque de exceso de mortalidad de la OMS.

### Variables predictoras

```python
cat_cols = ["mes", "trimestre", "codigo_depto", "capitulo_1", "periodo"]
# + variable numérica continua: anio
```

### Partición temporal train/test

```python
# Partición temporal, no aleatoria — correcta para series de tiempo
train_raw = mensual.filter(F.col("anio") <= 2022)  # 2015–2022
test_raw  = mensual.filter(F.col("anio") >  2022)  # 2023–2024
```

### Configuración del modelo

```python
ridge = LinearRegression(
    featuresCol="features",
    labelCol="defunciones",
    maxIter=50,
    regParam=0.3,
    elasticNetParam=0.0,  # 0.0 = L2 puro = Ridge
)
```

### Métricas de evaluación

| Métrica | Valor |
|---|---|
| Período de entrenamiento | 2015–2022 |
| Período de prueba | 2023–2024 |
| **R²** | **0.5227** |
| RMSE | 26.83 defunciones |
| MAE | 13.47 defunciones |

### Análisis de exceso de mortalidad

```python
exceso = (pred.groupBy("anio", "mes")
    .agg(
        F.sum("defunciones").alias("observado"),
        F.sum("prediction").alias("esperado")
    )
    .withColumn("exceso", F.col("observado") - F.col("esperado"))
    .orderBy("anio", "mes")
)
```

Los resultados alimentan directamente el análisis comparativo de la sección [Análisis y Recomendaciones](analisis_recomendaciones.md).

### Persistencia

```python
# /Volumes/workspace/ml/modelos/ridge_pronostico_pesos.json
pesos = {
    "modelo": "LinearRegression-Ridge",
    "coeficientes": [...],
    "intercepto": ...,
    "features_categoricas": cat_cols,
    "feature_extra": "anio",
    "regParam": 0.3,
    "elasticNetParam": 0.0,
    "mlflow_run_id": run_id,
}
```

---

## Auditoría de Ejecuciones

Los notebooks 2 y 3 registran cada ejecución en `ml.ml_control_log`, siguiendo el mismo patrón de gobernanza que `dw.etl_control_log` de la Fase 2:

```sql
CREATE TABLE IF NOT EXISTS ml.ml_control_log (
    ejecucion_id   BIGINT GENERATED ALWAYS AS IDENTITY,
    notebook       STRING,
    modelo         STRING,
    fecha_inicio   TIMESTAMP,
    fecha_fin      TIMESTAMP,
    filas_train    BIGINT,
    filas_test     BIGINT,
    metricas       STRING,
    mlflow_run_id  STRING
)
```

!!! tip "Reproducibilidad"
    Con el `mlflow_run_id` almacenado en la tabla de control es posible recuperar los parámetros exactos, las métricas y los artefactos de cualquier ejecución pasada desde la interfaz de MLflow en Databricks.
