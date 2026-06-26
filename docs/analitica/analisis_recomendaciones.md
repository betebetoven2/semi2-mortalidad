# Análisis y Recomendaciones

## Metodología Analítica

La comparación entre el período previo a la pandemia (2015–2019) y el período posterior (2020–2024) sigue el enfoque de **exceso de mortalidad** adoptado por la Organización Mundial de la Salud, que consiste en comparar la mortalidad observada contra una línea base de mortalidad esperada construida a partir del período previo. En este proyecto ese enfoque se operacionaliza mediante dos técnicas complementarias:

- **Regresión Logística** — clasifica cada defunción individual según su período de ocurrencia a partir de sus atributos demográficos, geográficos y de causa. Los coeficientes del modelo indican qué categorías están más asociadas a cada período.
- **Regresión Ridge** — pronostica el conteo mensual de defunciones agregado por departamento y capítulo de causa, entrenada sobre 2015–2022 y evaluada sobre 2023–2024. La diferencia entre lo observado y lo esperado es la aproximación al exceso de mortalidad.

---

## Hallazgos del Modelo de Clasificación

### Resultado global

| Métrica | Valor |
|---|---|
| Registros de entrenamiento | 735,384 |
| Registros de prueba | 183,847 |
| Área bajo la curva ROC | 0.6171 |
| Exactitud | 0.5867 |
| Puntuación F1 | 0.6656 |

Un AUC de 0.617 indica poder discriminativo moderado, resultado esperable: la mayoría de las causas de muerte no varía radicalmente con la ocurrencia de una pandemia. Los hallazgos relevantes provienen de la lectura de los coeficientes individuales, no de la exactitud global del modelo.

### Hallazgo principal — La firma de la pandemia

El coeficiente de mayor magnitud absoluta del modelo correspondió al **capítulo U de la CIE-10** (códigos especiales, donde se registra la mortalidad directa por COVID-19), con un valor de **7.19**. Este resultado supera ampliamente al segundo coeficiente en magnitud (pueblo de pertenencia Xinka, 1.18).

!!! info "Validación de coherencia del repositorio"
    Sin que se le proporcionara ninguna indicación explícita sobre la existencia de la pandemia, el modelo identificó por sí mismo que el capítulo U es el predictor individual más fuerte de pertenencia al período post-COVID. Esto constituye una validación sustantiva de la coherencia del repositorio analítico construido a lo largo de las tres fases.

### Hallazgo secundario — Enfermedades respiratorias generales

El capítulo J (enfermedades del sistema respiratorio) presentó un coeficiente de **−0.63**, asociándolo en mayor medida con el período *previo* a la pandemia. Este resultado, contraintuitivo a primera vista, es consistente con un fenómeno documentado internacionalmente: las medidas de mitigación (uso de mascarilla, restricción de movilidad) redujeron significativamente la transmisión de enfermedades respiratorias distintas al COVID-19. Dado que la mortalidad directa por COVID-19 se contabiliza bajo el capítulo U y no bajo el J, el descenso relativo en el capítulo J sugiere que la reducción de otras enfermedades respiratorias tuvo un peso mayor que cualquier incremento marginal dentro de esta categoría general.

### Hallazgo terciario — Asistencia médica no registrada

Las defunciones sin registro de nivel de asistencia médica recibida presentaron un coeficiente de **1.00**, asociándolas en mayor medida con el período post-COVID. Esto sugiere un vacío de información que se amplió durante la pandemia, probablemente por la saturación del sistema de salud.

---

## Hallazgos del Modelo de Pronóstico

### Resultados en el período de evaluación (2023–2024)

| Métrica | Valor |
|---|---|
| R² | 0.5227 |
| RMSE | 26.83 defunciones |
| MAE | 13.47 defunciones |

### Patrón de normalización post-pandemia

La comparación entre la mortalidad observada y la mortalidad esperada reveló que la mayoría de los meses de 2023 (nueve de doce) presentaron mortalidad observada **por debajo** de lo que el modelo habría anticipado según el patrón histórico 2015–2022. Este resultado es consistente con un proceso de normalización posterior a la pandemia, en el cual la mortalidad general no exhibe un arrastre sostenido una vez superada la fase aguda.

### Valor atípico — Mayo de 2024

Se identificó una desviación positiva de **1,488 defunciones** en mayo de 2024 respecto al valor esperado, la más alta de todo el período de evaluación. Este mes constituye un objeto de investigación adicional que el análisis agregado no permite atribuir a una causa específica.

---

## Recomendaciones de Política Pública

### 1. Fortalecimiento del registro de asistencia médica

El hallazgo de que las defunciones sin registro de asistencia médica se asociaron con el período post-COVID (coeficiente 1.00) sugiere un vacío de información que limita la capacidad de monitoreo de la calidad de atención durante períodos de alta demanda. Se recomienda que el **MSPAS** emita una directiva para reforzar la completitud de este campo en el certificado de defunción.

### 2. Investigación específica del exceso de mortalidad de mayo de 2024

Dado que mayo de 2024 constituye el valor atípico de mayor magnitud detectado en el período de evaluación, se recomienda una investigación desagregada por causa de muerte y departamento para determinar si la desviación responde a un evento puntual o a un cambio estructural no capturado por el modelo agregado.

### 3. Vigilancia de enfermedades respiratorias no asociadas a COVID-19

El hallazgo de que el capítulo J se asoció en mayor medida con el período pre-COVID sugiere un efecto protector colateral de las medidas de mitigación. Conforme dichas medidas se relajan permanentemente, se recomienda mantener **vigilancia epidemiológica** sobre si la mortalidad por causas respiratorias no asociadas a COVID-19 retorna a sus niveles pre-pandemia.

### 4. Adopción del nivel de capítulo CIE-10 como estándar de reporte

Tanto el hallazgo de calidad de datos de la Fase 1 (13.55% de causas registradas como síntomas y signos mal definidos) como los resultados de esta fase confirman que el **nivel de capítulo CIE-10** (primer carácter del código) produce señales estadísticamente robustas e interpretables para reporte poblacional, en contraste con el código completo cuya alta dispersión limita su utilidad para el análisis agregado.

---

## Limitaciones del Estudio

- El AUC de 0.617 indica poder discriminativo moderado. Los atributos demográficos disponibles no determinan por sí solos el período de ocurrencia de una defunción, condición esperable que no invalida los hallazgos individuales sobre los coeficientes.
- El modelo de pronóstico no incorpora variables exógenas (condiciones climáticas, eventos epidemiológicos específicos) que podrían explicar con mayor precisión los meses de mayor desviación.
- El 13.55% de causas clasificadas como mal definidas introduce ruido inherente en cualquier análisis desagregado por causa específica — limitación de la fuente original, no de la metodología.
