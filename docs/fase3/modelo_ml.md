# Modelo de Aprendizaje Automático

## Propósito

La Fase 3 incorpora un componente de aprendizaje automático sobre los datos consolidados en el repositorio analítico. El objetivo es analizar patrones de mortalidad pre-COVID y post-COVID con modelos reproducibles, interpretables y compatibles con el encargo.

## Problemas modelados

Se documentaron dos formulaciones principales:

### 1. Clasificación binaria de período

El primer modelo clasifica cada defunción entre:

- `PRE_COVID` para registros de 2015 a 2019
- `POST_COVID` para registros de 2020 a 2024

Esta formulación permite identificar qué variables explican mejor el cambio estructural entre períodos.

### 2. Pronóstico mensual de defunciones

El segundo modelo estima el conteo mensual de defunciones agregado por departamento y causa. Esta formulación permite contrastar la mortalidad observada contra una línea base esperada.

## Técnicas utilizadas

El informe documenta dos técnicas concretas:

- **Regresión logística**, para clasificación binaria
- **Regresión de cresta (ridge regression)**, para pronóstico de conteos

El enunciado de la Fase 3 también permite formulaciones equivalentes o complementarias como regresión multiclase, regresión lineal, K-means y Random Forest, siempre que el problema quede bien justificado.

## Resultados reportados

### Regresión logística

El modelo de clasificación obtuvo los siguientes indicadores:

| Métrica | Valor |
|---|---:|
| Registros de entrenamiento | 735,384 |
| Registros de prueba | 183,847 |
| Área bajo la curva ROC | 0.6171 |
| Exactitud | 0.5867 |
| F1 | 0.6656 |

### Regresión de cresta

El modelo de pronóstico mensual alcanzó:

| Métrica | Valor |
|---|---:|
| Coeficiente de determinación | 0.5227 |
| RMSE | 26.83 |
| MAE | 13.47 |

## Hallazgos relevantes

- El capítulo CIE-10 `U` fue el predictor más fuerte de pertenencia al período post-COVID.
- El capítulo `J` se asoció en mayor medida con el período pre-COVID.
- En 2023, la mayoría de los meses evaluados quedaron por debajo de la tendencia esperada.
- Mayo de 2024 presentó una desviación positiva notable, con 1,488 defunciones por encima de lo esperado.

## Restricción operativa

La herramienta de implementación queda a discreción del equipo. El enunciado permite Amazon SageMaker, Databricks o Google Colab, pero exige cuidado con secretos y credenciales en cuadernos.

## Justificación metodológica

La selección de modelos responde a dos criterios:

- interpretabilidad ante la defensa oral,
- y compatibilidad con una PoC de ingeniería de datos centrada en mortalidad.

Estos modelos permiten explicar el comportamiento del fenómeno sin depender de arquitecturas opacas o sobredimensionadas para el tamaño del problema.