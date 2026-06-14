# Marco Ético de Uso de Datos

Los datos del INE en la capa Sandbox contienen información individual sobre personas fallecidas: edad exacta, causa de muerte, etnia, municipio de residencia y ocupación. Aunque las personas ya fallecieron, la ética de salud pública y la protección de datos exigen tratar esta información con responsabilidad.

---

## Fundamentos Legales y Normativos

| Instrumento | Aplicación en este proyecto |
|---|---|
| **Convenio 169 OIT** | Protege datos étnicos de pueblos indígenas. Las columnas `perdif` y `puedif` son datos protegidos. |
| **Principio de proporcionalidad (GDPR art. 5)** | Usar solo el nivel de detalle necesario para el análisis. Datos individuales solo en capas restringidas. |
| **Ética de salud pública (OPS/OMS)** | Los microdatos de mortalidad deben procesarse de forma que no permitan reidentificación de familias. |
| **Políticas INE Guatemala** | Los datos son de uso público pero su reutilización debe respetar la privacidad de los deudos. |

---

## Principios de Gobernanza del Proyecto

!!! danger "Regla de Oro — Inmutabilidad del Dato Crudo"
    El dato en la capa **Sandbox es inmutable e inaccesible para usuarios finales**. No se puede modificar, eliminar ni reutilizar directamente. Todo acceso analítico ocurre sobre capas superiores (Silver/Gold) donde las transformaciones de privacidad ya han sido aplicadas.

!!! success "Cero Destrucción"
    Ningún registro fue eliminado durante la ingesta, incluso si contiene nulos o esquemas incompletos. Esta regla preserva la trazabilidad completa al dato original.

!!! info "Acceso por capas"
    El nivel de detalle disponible para cada usuario depende de la capa a la que tiene acceso. Ver [Plan de Anonimización](anonimizacion.md) para la arquitectura Sandbox → Silver → Gold.

---

## Clasificación de Sensibilidad por Columna

=== "Sensibilidad ALTA"

    Columnas que, combinadas entre sí, pueden identificar a un individuo o su familia, o que están protegidas por normativa específica.

    | Columna | Tabla | Justificación |
    |---|---|---|
    | `edadif` | ine_defunciones | Edad exacta + causa + municipio permite reidentificación en comunidades pequeñas |
    | `mupocu` | ine_defunciones | Municipios con <100 habitantes; la combinación con causa puede identificar al fallecido |
    | `mupreg` | ine_defunciones | Ídem municipio de ocurrencia |
    | `mredif` | ine_defunciones | Municipio de residencia habitual — dato de localización |
    | `mnadif` | ine_defunciones | Municipio de nacimiento — dato biográfico |
    | `perdif` / `puedif` | ine_defunciones | Etnia — protegida por Convenio 169 OIT |
    | `caudef` | ine_defunciones | Causa CIE-10 exacta — estigmatizante si se cruza con etnia o localidad |

=== "Sensibilidad MEDIA"

    Columnas que aportan contexto útil pero cuya exposición sin controles puede ser problemática.

    | Columna | Tabla | Justificación |
    |---|---|---|
    | `diaocu` | ine_defunciones | Día exacto de muerte — redundante para tendencias; innecesariamente preciso |
    | `ciuodif` | ine_defunciones | Ocupación — dato personal; alta tasa de nulos que limita su uso |

=== "Sensibilidad BAJA"

    Columnas necesarias para los análisis principales y que por sí solas no permiten reidentificación.

    | Columna | Tabla | Justificación |
    |---|---|---|
    | `sexo` | ine_defunciones | Necesario para análisis epidemiológico; no identificante solo |
    | `anoocu` | ine_defunciones | Año de muerte — necesario para series de tiempo |
    | `depocu` | ine_defunciones | Departamento — granularidad suficientemente agregada |

=== "Sin sensibilidad"

    Datos estadísticos agregados a nivel país, sin información individual.

    | Columna | Tabla | Justificación |
    |---|---|---|
    | `numeric_value` | oms_indicadores | Indicador agregado nacional OMS |
    | `value` | worldbank_indicadores | Indicador agregado nacional Banco Mundial |

---

## Criterios de Acceso por Perfil

| Perfil | Capa Accesible | Justificación |
|---|---|---|
| **Ingeniero de datos** | Sandbox + Silver + Gold | Necesita acceso completo para ETL y depuración |
| **Epidemiólogo / Investigador** | Silver + Gold | Requiere causa detallada; no necesita dato crudo individual |
| **Analista de políticas públicas** | Gold | Solo necesita tendencias agregadas por departamento |
| **Público general / Dashboard** | Gold (vistas curadas) | Solo cifras consolidadas, sin posibilidad de reidentificación |

---

!!! abstract "Siguiente paso"
    Ver el [Plan de Anonimización](anonimizacion.md) para las técnicas concretas y las vistas SQL que implementan estas políticas.
