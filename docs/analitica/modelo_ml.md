# Modelo de Machine Learning

## Visión General

Se implementaron dos modelos complementarios sobre el repositorio analítico consolidado en la Fase 2, ambos ejecutados en **Databricks Serverless** con trazabilidad completa vía **MLflow**:

| # | Técnica | Problema | Tabla de entrada |
|---|---|---|---|
| **Notebook 2** | Regresión Logística | Clasificación binaria pre/post-COVID | `ml.dataset_defunciones` |
| **Notebook 3** | Regresión Ridge (L2) | Pronóstico de defunciones mensuales | `ml.dataset_mensual_depto_causa` |

Ambas técnicas están explícitamente autorizadas en los términos de referencia del encargo.

---

## Decisiones Transversales de Diseño

### Por qué L2 (Ridge) y no L1 (Lasso)

Las variables predictoras en ambos modelos son categóricas, codificadas con `StringIndexer` + `OneHotEncoder`. Este proceso genera columnas **mutuamente correlacionadas** dentro de cada grupo (las dummies de un mismo campo son excluyentes entre sí). La regularización L1 (Lasso) en presencia de multicolinealidad tiende a eliminar arbitrariamente una de las variables correlacionadas. Ridge (L2) distribuye el peso entre ellas de forma suave, sin anular ninguna, que es el comportamiento correcto cuando se trabaja con grupos de variables categóricas codificadas.

### Pipeline de *features* separado del modelo final

Spark Connect ML (motor de Databricks Serverless) impone un límite documentado de **256 MB** sobre cualquier objeto de modelo serializado (`CONNECT_ML.MODEL_SIZE_OVERFLOW_EXCEPTION`). Un `Pipeline` que encadena `StringIndexer` + `OneHotEncoder` + el estimador final supera ese límite al guardarse, aunque los coeficientes matemáticos pesen apenas unos kilobytes.

La solución adoptada en ambos notebooks separa el proceso en dos pasos:

1. **Pipeline de features** — se ajusta *solo* sobre el conjunto de entrenamiento y se usa para transformar train y test. No se persiste.
2. **Modelo final** — se ajusta sobre los datos ya transformados. Solo este objeto se guarda, porque su tamaño real (un vector de coeficientes) está muy por debajo del límite.

Esta separación preserva la propiedad de no fuga de datos: el pipeline de features nunca se entera de las distribuciones del conjunto de prueba.

### Persistencia de pesos

Los pesos de cada modelo se guardan como un JSON liviano en `/Volumes/workspace/ml/modelos/`, evitando por completo el límite de 256 MB. En un modelo lineal, los pesos *son* el vector de coeficientes más el intercepto — el artefacto es completamente suficiente para reproducir predicciones.

---

## Notebook 2 — Regresión Logística: Clasificación Pre/Post-COVID

### Problema de negocio

Dado un registro de defunción (sexo, grupo etario, etnia, departamento, capítulo de causa CIE-10, mes, tipo de lugar y nivel de asistencia médica), predecir si pertenece al período **PRE\_COVID (2015–2019)** o **POST\_COVID (2020–2024)**.

La Regresión Logística fue elegida sobre modelos de caja negra (Random Forest, redes neuronales) porque sus coeficientes son directamente legibles como el efecto de cada categoría sobre la probabilidad del evento — un requisito de interpretabilidad para un informe de política pública donde el cliente necesita explicaciones, no solo predicciones.

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
# Parámetros registrados: técnica, regParam, elasticNetParam, maxIter, features
# Métricas registradas: auc, accuracy, f1
```

### Persistencia

```python
# Pesos guardados en:
# /Volumes/workspace/ml/modelos/logistic_periodo_pesos.json
pesos = {
    "modelo": "LogisticRegression",
    "coeficientes": [...],   # vector completo de coeficientes
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

Pronosticar el **conteo mensual de defunciones** para una combinación departamento × capítulo CIE-10, en función del tiempo y las categorías. El modelo se entrena sobre el período histórico 2015–2022 y se evalúa sobre 2023–2024, operacionalizando el enfoque de **exceso de mortalidad** adoptado por la OMS: comparar lo observado contra una línea base construida con datos previos a la pandemia.

### Variables predictoras

```python
cat_cols = ["mes", "trimestre", "codigo_depto", "capitulo_1", "periodo"]
# + variable numérica continua: anio
```

### Partición temporal train/test

A diferencia del notebook 2, aquí se usa una **partición temporal** (no aleatoria), que es la estrategia correcta para evaluar la capacidad de pronóstico hacia adelante en una serie de tiempo:

```python
train_raw = mensual.filter(F.col("anio") <= 2022)  # 2015–2022
test_raw  = mensual.filter(F.col("anio") >  2022)  # 2023–2024
```

### Configuración del modelo

```python
ridge = LinearRegression(
    featuresCol="features",
    labelCol="defunciones",
    maxIter=50,
    regParam=0.3,         # fuerza de regularización
    elasticNetParam=0.0,  # 0.0 = L2 puro = Ridge
)
```

### Métricas de evaluación

| Métrica | Valor |
|---|---|
| Período de entrenamiento | 2015–2022 |
| Período de prueba | 2023–2024 |
| **R² (coeficiente de determinación)** | **0.5227** |
| RMSE (raíz del error cuadrático medio) | 26.83 defunciones |
| MAE (error absoluto medio) | 13.47 defunciones |

El grano de evaluación es departamento × capítulo de causa × mes, lo que implica que los errores son sobre conteos agregados, no registros individuales.

### Análisis de exceso de mortalidad

El notebook calcula directamente la diferencia entre lo observado y lo esperado por mes:

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

Los resultados de esta tabla alimentan directamente el análisis comparativo pre/post-COVID documentado en la sección de [Análisis y Recomendaciones](analisis_recomendaciones.md).

### Trazabilidad MLflow

```python
mlflow.set_experiment("/Shared/mortalidad_ridge_pronostico")
# Parámetros registrados: técnica, regParam, split temporal
# Métricas registradas: rmse, mae, r2
```

### Persistencia

```python
# Pesos guardados en:
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

Ambos notebooks registran cada ejecución en `ml.ml_control_log`, siguiendo el mismo patrón de gobernanza que `dw.etl_control_log` de la Fase 2:

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
