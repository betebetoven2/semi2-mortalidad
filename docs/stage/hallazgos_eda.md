# Hallazgos del Análisis Exploratorio de Datos (EDA)

## Resumen ejecutivo

El perfilamiento de la capa Bronze identificó siete hallazgos fundamentales (H1–H7) que alteran decisiones de diseño del pipeline. Estos hallazgos provienen de análisis sobre las 6 dimensiones de calidad de datos y están documentados en detalle en el reporte técnico *Reporte de Perfilamiento y Guía de Construcción Bronze → Stage*.

Cada hallazgo tiene impacto directo en la construcción de la capa Stage y en la justificación del modelo dimensional del Data Warehouse.

---

## Hallazgo H1: Unificación de esquema entre fuentes INE

**Constatación:** La única diferencia de esquema entre `bronze.xlsx_ine` (2018–2024) y `bronze.sav_ine_legacy` (2015–2017) es la columna `Areag` (clasificación urbano/rural), que existe únicamente en el legacy.

**Impacto en decisión:**
- Se construye una única tabla `stage.defunciones` que consolida ambas fuentes
- `Areag` se agrega como NULL a los registros 2018–2024 (conservando la información disponible sin contaminar con datos faltantes)
- Total consolidado: 919,231 registros de defunciones (2015–2024) en una sola tabla normalizada

**Implicación para análisis:**
Posibilita comparar tendencias pre-COVID (2015–2019) vs post-COVID (2020–2024) sobre una base unificada, aunque con limitación temporal para análisis urbano/rural (solo 2015–2017).

---

## Hallazgo H2: Artefacto de precisión numérica en datos legacy

**Constatación:** Los datos del formato SAV legacy (2015–2017) guardaron valores numéricos como punto flotante convertido a texto: `"1.0"` en lugar de `"1"`, `"101.0"` en lugar de `"101"`.

**Problema técnico:**
- Sin normalización, la columna `Sexo` cargada como {`"1.0"`, `"2.0"`} no coincide con {`"1"`, `"2"`} del xlsx
- Los códigos municipales: `"0101"` (xlsx) vs `"101.0"` (legacy) se particionan erróneamente en dos grupos geográficos distintos
- Pérdida de ceros iniciales, especialmente crítica para claves compuestas

**Regla de conformidad aplicada (R-VALID-1):**
Antes de cualquier validación, agregación o anonimización, se normaliza el artefacto float:
- Remoción del sufijo `.0` mediante expresión regular
- Normalización de valores textuales vacíos (`"nan"`, `"none"`, `""`) a NULL

**Impacto en el modelo dimensional:**
Garantiza que llaves de dimensión (geografía, sexo) sean consistentes entre periodos, evitando exploding joins.

---

## Hallazgo H3: Corrección de semántica — Etnia vs Período de edad

**Constatación crítica:** En la documentación original del plan de anonimización, la columna `Perdif` estaba clasificada como "etnia". Esto es **incorrecto**.

**Verdad técnica:**
- `Perdif` (Período de edad): unidad de medida de `Edadif`
  - 1 = Menos de un mes
  - 2 = 1 a 11 meses
  - 3 = 1 año y más
  - 9 = Ignorado / Edad desconocida
- `Puedif` (Pueblo/Etnia): clasificación étnica real
  - Categorías: 1 (Indígena), 2 (Ladino), 3 (Xinca), 4 (Garifuna), 5 (Otro), 9 (Ignorado)

**Impacto en corrección:**
- La anonimización por k-anonimato debe usar `Puedif`, no `Perdif`
- `Perdif` es dimensión explícita de transformación (convierte edad en años, meses o días)
- En el modelo dimensional: existe `dim_grupo_etario` sobre edad (derivada de `Edadif` + `Perdif`) y `dim_pueblo` sobre etnia (`Puedif`)

**Implicación política/ética:**
Corrige la representación étnica en análisis de mortalidad, esencial para equidad en decisiones de política pública.

---

## Hallazgo H4: Edad en unidades mixtas — Corrección fundamental

**Constatación:** Aproximadamente 46,000 registros (5% del total) tienen edad expresada en unidades no estandarizadas:
- ~1,997 registros (xlsx): edad en días o meses
- ~1,300 registros (legacy): edad en días o meses
- El indicador es `Perdif ∈ {1, 2}` (menos de un mes, 1-11 meses)

**Problema de análisis:**
Si se trata ingenuamente `Edadif=25` con `Perdif=1` (25 días) como "grupo etario 25-30 años", se introduce un sesgo sistemático en morbimortalidad infantil.

**Corrección aplicada (C2):**
La edad estandarizada (`edad_anios`) debe derivarse de:
- Si `Perdif=3` (años): `edad_anios = Edadif`
- Si `Perdif=2` (meses): `edad_anios = NULL` (registrar como <1 año en grupo etario)
- Si `Perdif=1` (días): `edad_anios = NULL` (registrar como <1 año en grupo etario)
- Si `Perdif=9` (ignorado): `edad_anios = NULL` (sin imputar)

**Impacto en modelo:**
La dimensión `dim_grupo_etario` utiliza 7 grupos OPS (Organización Panamericana de la Salud):
- <1 año (incluye días, meses)
- 1-4 años
- 5-9 años
- 10-19 años
- 20-49 años
- 50-64 años
- ≥65 años

---

## Hallazgo H5: Cobertura limitada de clasificación urbano/rural

**Constatación:** La columna `Areag` (urbano/rural) existe únicamente en el dataset legacy (2015–2017):
- 2015–2017: 245,167 registros con `Areag` poblada
- 2018–2024: 674,064 registros sin `Areag` (NULL)

**Limitación metodológica:**
No es posible realizar análisis comparativo urbano/rural pre/post-COVID sin imputación (que violaría garantías de calidad).

**Decisión arquitectónica:**
- Se incluye `Areag` como columna en `dim_geografia` con valor NULL para 2018–2024
- Se documenta la limitación explícitamente
- Posibles análisis: solo período 2015–2017

**Implicación política:**
Recomendación al cliente (MSPAS): solicitar al INE recolección de `Areag` en datasets posteriores para análisis longitudinal completo.

---

## Hallazgo H6: Calidad de causas de defunción — Capítulo R elevado

**Constatación:** El 100% de valores en `Caudef` están en formato CIE-10 válido. Sin embargo, la distribución revela un patrón de calidad:

| Characterística | Valor |
|---|---|
| Códigos CIE-10 únicos (xlsx) | ~2,692 |
| Códigos CIE-10 únicos (legacy) | ~2,110 |
| Registros en capítulo R (mal definidos) | ~123,400 (~13.5%) |
| Registros con COVID-19 (U071) | ~15,800 (~1.7%) |
| Top 5 causas | I219, R99X, J189, E149, R98X |

**Significado epidemiológico:**
- Capítulo R (síntomas, signos y hallazgos anormales) representa aproximadamente 1 de cada 7 defunciones
- Indica déficit en codificación de causa raíz, particularmente en contextos de recursos limitados
- COVID-19 (U071) está correctamente capturado en el período post-COVID

**Decisión de diseño:**
- En `dim_causa_cie10`: flag `mal_definida = TRUE` para capítulo R
- Permite análisis de completitud y calidad de causa, con opción de exclusión filtrada
- Documentación explícita de caveat para decisiones de política pública

**Implicación analítica:**
Análisis de mortalidad por causa real (excluyendo mal definidas) produce conclusiones más robustas.

---

## Hallazgo H7: Cobertura insuficiente de pueblo/etnia

**Constatación:** La columna `Puedif` (pueblo/etnia) tiene cobertura incompleta:
- Faltantes codificados como `9` (Ignorado): 16–19% del total
- Distribución de categorías: sesgo hacia Ladino (código 2)
- Faltantes no uniformes por período (posible mejora en recolección 2020+)

**Impacto en anonimización:**
- Para k-anonimato: los registros con `Puedif=9` deben convertirse a NULL
- Reduce el cuasi-identificador "pueblo" y mejora la garantía de anonimato
- Afecta análisis desagregado por etnia (algunos grupos infrarepresentados)

**Decisión de gobernanza:**
- Se documenta completitud de etnia por año
- Análisis de mortalidad por pueblo: reportes agregados solo con n ≥ 5
- Recomendación: mejorar recolección de etnia en certificados de defunción

---

## Síntesis: De hallazgos a decisiones

| Hallazgo | Dimensión de calidad | Regla de conformidad | Impacto en Stage | Impacto en DW |
|---|---|---|---|---|
| H1 | Consistencia | Unificación de esquema | Una sola tabla de hechos | Fact única 2015–2024 |
| H2 | Validez | R-VALID-1 (normalizar float) | Estandarización previa a joins | Llaves de dim consistentes |
| H3 | Exactitud semántica | C1 (separar etnia de edad) | Puedif como dimensión independiente | dim_pueblo separada |
| H4 | Validez de edad | C2 (estandarizar a años) | edad_anios derivada de Edadif+Perdif | dim_grupo_etario con <1 año |
| H5 | Vigencia / Cobertura | C4 (limitación documentada) | Areag = NULL 2018–2024 | Análisis urbano/rural 2015–2017 solo |
| H6 | Exactitud de causa | C5 (flag mal_definida) | Caudef validado 100% | dim_causa_cie10 con jerarquía CIE |
| H7 | Completitud de etnia | C6 (cobertura 81–84%) | Puedif = 9 → NULL | dim_pueblo con caveat |

Cada decisión de conformidad tiene raíz en datos y es reproducible mediante auditoría (git blame).
