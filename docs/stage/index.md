# Capa Stage — Bronze a Data Warehouse

## Introducción

Esta sección documenta la **Capa Stage** del pipeline: *Transformación, arquitectura por capas y almacenamiento*. El pipeline de datos integra la zona de aterrizaje (Bronze) con la capa de conformación (Stage) y culmina en un repositorio analítico dimensional (Data Warehouse) desplegado en la nube y replicado localmente.

La documentación está organizada en tres ejes:

1. **Hallazgos del Análisis Exploratorio de Datos (EDA)** — Perfilamiento de la capa Bronze que identifica problemas de calidad e informa las decisiones de diseño.

2. **Reglas de Conformidad** — Las 12+ reglas de limpieza, validación y estandarización que transforman Bronze en Stage.

3. **Modelo Dimensional** — Justificación y arquitectura del Data Warehouse en esquema estrella, optimizado para análisis pre/post-COVID.

## Flujo de datos

```
Bronze (Databricks, crudo)
    ↓
Stage (conformado, limpio, anonimizado)
    ↓
Data Warehouse (modelo estrella en Databricks + PostgreSQL local)
    ↓
Análisis y visualización (BI, ML)
```

## Volumen de datos consolidados

| Capa | Registros | Estado |
|---|---:|---|
| Bronze | 919,231 | Ingesta completa (2015–2024) |
| Stage | 919,231 | Limpieza y conformación |
| DW fact_defunciones | 919,231 | Modelo dimensional |

## Marcos metodológicos

- **Arquitectura Medallion:** Bronze (crudo) → Silver/Stage (conformado) → Gold (agregado/público)
- **CRISP-DM:** Énfasis en *Data Understanding* y *Data Preparation* para calidad garantizada
- **Modelado Dimensional:** Esquema estrella (Kimball) optimizado para análisis multidimensional
- **Dimensiones de Calidad:** Completitud, Unicidad, Validez, Consistencia, Exactitud, Vigencia
