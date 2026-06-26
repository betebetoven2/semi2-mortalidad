# Visualización e Interoperabilidad BI

## Estrategia de Visualización

El encargo exige demostrar **interoperabilidad real entre herramientas de BI**, no solo la existencia de dos gráficas independientes. La estrategia adoptada conecta ambas herramientas al mismo repositorio analítico (Data Warehouse), de modo que cualquier actualización en el DW se refleja en ambas plataformas sin duplicación de lógica de transformación.

| Herramienta | Vistas entregadas | Fuente de datos |
|---|---|---|
| **Power BI** | 2 dashboards (Power Query + DAX) | Conexión directa al DW |
| **Herramienta alternativa** | 2 dashboards | Conexión directa al DW |

---

## Power BI

### Preparación de datos — Power Query

Power Query se utiliza como capa de transformación ligera dentro de Power BI. Las transformaciones pesadas (limpieza, modelado dimensional) ya ocurrieron en las capas Stage y Gold del pipeline de Databricks; Power Query solo realiza ajustes de presentación:

- Selección de columnas relevantes para cada vista.
- Tipado explícito de fechas y categorías.
- Creación de columnas calculadas de apoyo (p. ej. etiqueta `"Pre-COVID"` / `"Post-COVID"` a partir del año).

### Medidas DAX

Las medidas analíticas centrales se definen en DAX para aprovechar el motor de cálculo columnar de Power BI:

```dax
-- Total de defunciones en el período seleccionado
Total Defunciones = SUM(fact_defunciones[total_defunciones])

-- Tasa de variación entre períodos
Variación % Pre-Post COVID =
VAR pre  = CALCULATE([Total Defunciones], dim_tiempo[periodo] = "Pre-COVID")
VAR post = CALCULATE([Total Defunciones], dim_tiempo[periodo] = "Post-COVID")
RETURN DIVIDE(post - pre, pre, BLANK())

-- Defunciones por capítulo CIE-10 (top causas)
Defunciones por Capítulo =
CALCULATE(
    [Total Defunciones],
    ALLEXCEPT(fact_defunciones, dim_causa[capitulo_1])
)
```

### Vista 1 — Análisis Comparativo Pre/Post-COVID por Causa

Comparativa de mortalidad entre los dos períodos desagregada por capítulo CIE-10, con énfasis en el capítulo U (COVID-19 directo) y el capítulo J (enfermedades respiratorias generales). Incluye gráfico de barras agrupadas, tabla de variación porcentual y filtros por departamento y año.

### Vista 2 — Tendencia Mensual y Exceso de Mortalidad

Serie de tiempo de defunciones mensuales observadas vs. defunciones esperadas según el modelo Ridge, con área sombreada para el exceso o déficit. Permite identificar visualmente el valor atípico de mayo de 2024 y el patrón de normalización post-pandemia en 2023.

---

## Herramienta Alternativa

Las dos vistas adicionales replican los mismos análisis core conectándose al mismo DW, lo que constituye la demostración de interoperabilidad: **la misma fuente de verdad, dos plataformas distintas**.

### Vista 3 — Distribución Geográfica de Mortalidad

Mapa de calor departamental con la tasa de defunciones por 100,000 habitantes, comparando pre y post-COVID. Permite identificar departamentos con mayor impacto diferencial de la pandemia.

### Vista 4 — Segmentación por Grupo Etario y Sexo

Pirámide de mortalidad por grupo etario y sexo, filtrable por período y capítulo de causa. Complementa el análisis de los coeficientes del modelo logístico con una representación visual directamente interpretable por el cliente.

---

## Demostración de Interoperabilidad

!!! success "Criterio de interoperabilidad"
    La interoperabilidad no se demuestra con capturas de pantalla: en la defensa oral se ejecuta en vivo la actualización de datos en el DW y se muestra cómo ambas herramientas reflejan el cambio sin intervención manual adicional.

El flujo completo de interoperabilidad es:

```
Fuente original
      │
      ▼
Pipeline Databricks (Fase 2)
      │   Sandbox → Stage → Gold / Fact-Dimensiones
      ▼
Data Warehouse (nube + local)
      │
      ├──▶  Power BI ──▶ Vista 1, Vista 2
      │
      └──▶  Herramienta alternativa ──▶ Vista 3, Vista 4
```

Ambas conexiones apuntan al mismo esquema del DW. No existe una copia intermedia de datos ni una exportación manual entre herramientas.
