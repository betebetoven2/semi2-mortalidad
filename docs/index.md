# Plataforma Analítica de Mortalidad

**Seminario de Sistemas 2 | USAC 2026 | Grupo 3**

---

Este sitio documenta la gobernanza de datos de la Plataforma Analítica de Mortalidad de Guatemala y Centroamérica. La plataforma integra registros individuales de defunciones del INE Guatemala (2015–2024) con indicadores regionales de la OMS y el Banco Mundial, consolidando **923,226 registros** en una arquitectura ELT sobre AWS S3, PostgreSQL y Databricks.

La documentación está organizada en cinco ejes:

<div class="grid cards" markdown>

-   :material-database-arrow-down:{ .lg .middle } **Procedencia**

    ---

    Catálogo completo de las cinco fuentes de datos: institución, URL, formato, años cubiertos, volumen y limitaciones conocidas.

    [:octicons-arrow-right-24: Ver catálogo de fuentes](procedencia/index.md)

-   :material-transit-connection-variant:{ .lg .middle } **Linaje de Datos**

    ---

    Trazabilidad extremo a extremo: desde la fuente pública hasta cada fila en Sandbox. Arquitectura del pipeline ELT y diccionario de las cinco tablas físicas.

    [:octicons-arrow-right-24: Ver arquitectura del pipeline](lineage/index.md)

-   :material-database-export:{ .lg .middle } **Transformación Fase 2**

    ---

    Perfilamiento de datos, reglas de conformidad y modelo dimensional. Transformación de Bronze a Data Warehouse en esquema estrella.

    [:octicons-arrow-right-24: Ver transformación y DW](stage/index.md)

-   :material-chart-box-outline:{ .lg .middle } **Fase 3**

    ---

    Aprendizaje automático, visualización analítica, interoperabilidad BI y recomendaciones de política sobre el repositorio dimensional.

    [:octicons-arrow-right-24: Ver explotación analítica](fase3/index.md)

-   :material-shield-account:{ .lg .middle } **Ética y Gobernanza**

    ---

    Marco ético de uso de datos sensibles de salud pública, clasificación de sensibilidad por columna y plan de anonimización por capas (Sandbox → Silver → Gold).

    [:octicons-arrow-right-24: Ver marco ético](etica/index.md)

</div>

---

## Resumen del Dataset

| Fuente | Institución | Formato | Años | Registros |
|---|---|---|---|---|
| INE Defunciones 2018–2024 | INE Guatemala | Excel (.xlsx) | 2018–2024 | 674,064 |
| INE Defunciones 2015–2017 | INE Guatemala | SAV / Parquet | 2015–2017 | 245,167 |
| WHO/OMS GHO | OMS | JSON (OData) | 1990–2023 | 1,708 |
| World Bank | Banco Mundial | JSON | 2010–2024 | 450 |
| Diccionario INE | Equipo (interno) | Excel (.xlsx) | N/A | 1,837 |
| **Total** | | | | **923,226** |

## Arquitectura en una línea

```
Fuentes públicas → Raspberry Pi (scrapers Python) → AWS S3 → PostgreSQL Sandbox → Databricks Bronze
```

!!! info "Estado de desarrollo"
    Esta documentación cubre las **Fases 1, 2 y 3** del proyecto. Fase 1: ingesta masiva a Sandbox. Fase 2: transformación a capas y Data Warehouse dimensional. Fase 3: aprendizaje automático, visualización analítica e interoperabilidad BI.
