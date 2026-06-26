# Visualización Analítica e Interoperabilidad BI

## Alcance

La Fase 3 exige demostrar que el repositorio analítico puede alimentar al menos dos herramientas de visualización distintas. En el enunciado se solicita expresamente:

- dos visualizaciones en **Power BI**,
- y dos visualizaciones en otra herramienta a elección del equipo, por ejemplo Tableau.

## Criterio de integración

La interoperabilidad no debe entenderse solo como exportación de archivos, sino como capacidad de consumir el mismo modelo de datos desde herramientas distintas sin perder consistencia semántica.

## Herramientas y preparación

### Power BI

La preparación de datos debe realizarse con:

- **Power Query** para transformación inicial
- **DAX** para medidas y cálculos

### Otra herramienta de BI

La segunda plataforma puede ser Tableau u otra equivalente, siempre que permita reproducir visualizaciones analíticas sobre el modelo dimensional.

## Vistas mínimas esperadas

### En Power BI

- tendencia temporal de defunciones por período,
- distribución de causas de muerte por capítulo CIE-10.

### En la segunda herramienta

- análisis geográfico de mortalidad,
- y comparación pre/post-COVID por grupo etario o pueblo.

## Integración con Databricks

El enunciado incluye una tarea complementaria sobre integraciones con Databricks para habilitar una vista de Power BI y otra herramienta. Por tanto, la documentación de esta fase debe dejar explícito:

- el origen del dato,
- la transformación aplicada,
- y el punto de consumo BI.

## Criterio de evaluación

La evidencia debe mostrar que la información puede ser trazada desde el Data Warehouse hasta el tablero final sin romper el flujo end-to-end.