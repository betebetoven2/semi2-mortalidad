Proyecto
Plataforma Analítica de Mortalidad End-to-End
Exploración de Datos del Estado de la Salud: Análisis de Mortalidad Pre-COVID y Post-COVID en Guatemala y Centroamérica / Fuentes de Datos (Publicas)
Modalidad
Aprendizaje basado en proyectos bajo una consultoría modelo Naciones Unidas / PNUD. El encargo está orientado a resultados, no a herramientas: los Términos de Referencia definen qué debe lograrse; el equipo decide, propone y justifica el cómo.
Trabajo en equipo (firma consultora).  Entrega oficial: UEDI.  Defensa: oral.  Estructura: tres (3) fases acumulativas.
Nota: La nube y las herramientas quedan a discreción del estudiante. En el presente enunciado no se le obliga al estudiante ni se le incita a utilizar herramientas de paga. 
Cantidad de Equipo: 3 Integrantes. 
Modalidad de Calificación: Oral y Presentación. 


Contexto del Encargo
En el marco de una iniciativa de cooperación internacional para el fortalecimiento de los sistemas de información en salud, el Programa de las Naciones Unidas para el Desarrollo (PNUD), en acompañamiento al Ministerio de Salud Pública y Asistencia Social (MSPAS), busca comprender cómo cambiaron los patrones de mortalidad en el país entre el período pre-COVID (2015–2019) y el período post-COVID (2020 en adelante), con el fin de orientar decisiones de política pública y asignación de recursos.
El problema es, antes que de salud, de ingeniería de datos: la información de defunciones existe, pero está fragmentada en múltiples fuentes, formatos y niveles de calidad. El registro nacional transita del RENAP al INE, que codifica las causas de muerte bajo el estándar CIE-10 y publica estadísticas vitales; estos datos coexisten con registros institucionales, regionales e internacionales. La institución cliente no cuenta con una plataforma analítica integrada que permita consolidar, gobernar y explotar dichos datos para responder preguntas estratégicas.
Su equipo ha sido contratado como firma consultora para diseñar y construir una prueba de concepto (PoC) de una plataforma de datos de punta a punta (End-to-End) y entregar recomendaciones basadas en evidencia. Este es un caso ficticio con fines educativos.
Cláusula de cooperación internacional. A partir de un acuerdo institucional, el PNUD vincula a centros de investigación para el Sur Global en Europa; por lo tanto, la plataforma debe cumplir con el EU Data Act y con los principios de manejo ético de datos sensibles de salud (datos anonimizados y/o agregados).


Objetivos
Objetivo general
Diseñar, implementar y demostrar una plataforma de datos de punta a punta que integre fuentes heterogéneas de mortalidad, las gobierne bajo una arquitectura por capas hacia un repositorio analítico tipo Data Warehouse, y entregue evidencia comparativa pre-COVID / post-COVID que sustente recomendaciones de política para la institución cliente.
Objetivos específicos
Diseñar e implementar procesos de ETL/ELT sobre fuentes de datos heterogéneas (locales y en la nube).
Construir una arquitectura por capas con tablas Sandbox, Stage y Fact-Dimensiones (modelado dimensional).
Consolidar la información en un repositorio analítico (Data Warehouse) tanto en la nube como en una instancia local, demostrando interoperabilidad entre ambos.
Aplicar Aprendizaje Automático (Machine Learning) a un problema real de mortalidad.
Producir visualización analítica en al menos dos (2) herramientas de BI distintas, demostrando interoperabilidad.
Garantizar el manejo ético, anonimizado y/o agregado de datos sensibles, en cumplimiento del EU Data Act.
Justificar técnicamente, ante el cliente, cada decisión de ingeniería adoptada.
Competencias que el Equipo Debe Demostrar
Diseño e implementación de procesos ETL/ELT.
Modelado dimensional y construcción de repositorios tipo Data Warehouse.
Manejo de bases de datos relacionales y no relacionales.
Conocimiento práctico de formatos y protocolos de intercambio de información: JSON, XML, HTTP/HTTPS y servicios web/APIs (clave para la interoperabilidad entre herramientas de BI).
Aprendizaje automático aplicado a un problema real.
Visualización analítica en al menos dos herramientas de BI.
Deseables: nociones de gobernanza de datos, calidad y diccionarios de metadatos; sensibilidad para el manejo ético de datos sensibles (salud, mortalidad); interés en transformación digital del sector público y cooperación internacional.
Estructura del Proyecto: Tres Fases Acumulativas
El proyecto se desarrolla y se evalúa en tres (3) fases. Cada fase constituye un hito de la consultoría, pero la naturaleza del trabajo es acumulativa y end-to-end: en la defensa de cada fase el equipo debe poder ejecutar el flujo completo desde el inicio (desde la fuente de datos) hasta el entregable correspondiente. No se evalúa el incremento de manera aislada; se evalúa que la tubería funcione de extremo a extremo en su estado actual.
Fase
Foco principal
Salida demostrable (desde el inicio)
Fase 1
Identificación, estructuración, limpieza e ingesta de datos
Datos crudos consolidados en la zona de aterrizaje (Sandbox), con diccionario de datos y plan de anonimización, Diagrama de Despliegue de la Solución, Diagrama ERD de Modelo de Datos. 
Fase 2
Transformación, arquitectura por capas y almacenamiento (DW)
Flujo Sandbox → Stage →Datawarehouse cargado en un DW en la nube y en un DW local interoperables.
Fase 3
Machine Learning, visualización analítica e interoperabilidad BI
Modelo de ML productivo (Regresion Lineal, K-means, RandomForests) debe ser desarrollado o AWS Sagemaker o en Databricks + 2 visualizaciones en Power BI y 2 en otra herramienta, con análisis pre/post-COVID.


Regla transversal — “cada fase desde el inicio”. En toda defensa de fase, el equipo deberá demostrar el recorrido completo del dato: origen → ingesta → capas → repositorio → (según la fase) modelo y visualización. Una fase no se da por aprobada si la tubería previa dejó de funcionar.

Fase 1 — Fundamentos de Datos: Identificación, Estructuración, Limpieza e Ingesta
Identificación y obtención de fuentes de datos
El equipo debe localizar, gestionar y obtener datos de defunciones estructurados, con cobertura suficiente para comparar el período pre-COVID (2015–2019) con el período post-COVID (2020 en adelante). Las fuentes deben incluir Guatemala y, a nivel comparativo, al menos un referente de Centroamérica.
RENAP — solicitud formal de información. El equipo redactará y gestionará una solicitud de información de registros de defunción ante el Registro Nacional de las Personas (RENAP), documentando el oficio y la respuesta como parte de la trazabilidad del dato.
INE — estadísticas vitales. Defunciones con codificación de causas CIE-10 publicadas por el Instituto Nacional de Estadística.
MSPAS y fuentes institucionales / regionales / internacionales. Registros que enriquezcan el análisis y permitan validar la calidad.
Centroamérica. Al menos una fuente regional comparable (p. ej. institutos de estadística homólogos) para situar a Guatemala en contexto regional.
Requisito de datos. El conjunto de trabajo debe estar estructurado y centrado en defunciones (mortalidad), con dimensiones mínimas de tiempo (año/mes), geografía (departamento/municipio) y causa (CIE-10), suficientes para el análisis pre/post-COVID.
Estructuración y limpieza
Desde la estructuración y limpieza de datos, el equipo consigue y prepara sus datos: normalización de esquemas, estandarización de códigos CIE-10, tratamiento de valores faltantes y atípicos, deduplicación, conciliación de catálogos geográficos y validación de integridad. Toda regla de limpieza debe quedar documentada.
Ingesta desde fuentes heterogéneas
La ingesta debe demostrar el manejo de fuentes heterogéneas, combinando orígenes locales y en la nube. Como mínimo, el equipo deberá integrar datos provenientes de: (Minimo 4 fuentes distintas)
Google Drive (archivos compartidos / exportaciones).
SharePoint (repositorio documental institucional).
Servicio de almacenamiento de objetos S3 (u Object Storage equivalente) en la nube de su elección.
Base de datos relacional gestionada (RDS) como fuente — local o en la nube.
Es posible utilizar webscrappers para obtener la información. 
Zona de aterrizaje: Tabla Sandbox (Base de datos sandbox)
Los datos ingeridos aterrizan, sin transformación destructiva, en la Tabla Sandbox: una zona de exploración fiel al origen que preserva la materia prima para auditoría y reproceso.
Gobernanza inicial y ética
Diccionario de datos y catálogo de metadatos preliminar.
Plan de anonimización / agregación de datos sensibles (cumplimiento EU Data Act).
Registro de procedencia (data lineage) desde la fuente hasta el Sandbox.
Entregables: 
1. Modelo de Datos producido en DataModeler 
2. Arquitectura de Despliegue producida en Draw.io 
3. Pipelines de Ingesta de Datos versionadas en Github, se utilizará git blame para corroborar cambios. 
4. Documentación desplegada con Github Actions (Mkdocs) en Github. 
 
Restricciones: 
1. No es posible Utilizar Mermaid ni PlantUML para diagramados. 
2. Durante la calificación se deberá tener cámara encendida y se deberá presentar toda la pantalla. 
3. Se le realizará 1 pregunta a cada integrante sobre las arquitecturas, si no le es posible responder entonces existirá una penalización de 20 puntos al equipo. 
4. La entrega de esta fase es requisito para la entrega de la siguiente fase. 
5. No es posible mover los horarios de calificación media vez se hayan establecido. 
6. Se debe utilizar la siguiente fuente de datos (una de las múltiples fuentes, el estudiante es libre de utilizar más fuentes de datos no referentes a esta misma): https://datos.ine.gob.gt/dataset/estadisticas-vitales-defunciones 
Se sugiere también la linea base de OMS https://platform.who.int/mortality/countries/country-details/MDB/guatemala 
El estudiante deberá proponer más fuentes de datos para la ingesta y realizar un catálogo de fuentes de datos. 

Fecha de Entrega: 12 de Junio a las 23:59
Fase 2 — Transformación, Arquitectura por Capas y Almacenamiento (Data Warehouse)
Proceso de transformación y almacenamiento por capas
El equipo construye el proceso de transformación y almacenamiento sobre una arquitectura por capas. Cada capa cumple un propósito y se materializa en tablas explícitas:
Capa / Tabla
Propósito
Tabla Sandbox
Aterrizaje fiel al origen (proveniente de la Fase 1). Materia prima, sin transformación destructiva.
Tabla Stage
Datos conformados, limpios, tipados y estandarizados; aplicación de reglas de negocio y de calidad.
Base de Datos (DW)
Modelo dimensional (esquema estrella): tabla(s) de hechos de defunciones y sus dimensiones (tiempo, geografía, causa CIE-10, sexo, grupo etario).


Orquestación de la transformación
ETL o ELT Jobs . No es obligatorio realizar el proceso ETL en la nube. Sin embargo, no se aceptarán pipelines utilizando el Gitlab Runner o Github Runner. 
Repositorio analítico (Data Warehouse target)
El flujo debe culminar en una base de datos target final, de tipo repositorio Data Warehouse. Se exige una arquitectura híbrida que demuestre interoperabilidad nube–local:
DW en la nube. Repositorio analítico en la nube de su elección (cualquier nube).
Data Warehouse local. El proyecto debe incluir una réplica del Datawarehouse de manera local. 
Criterio de aceptación — Fase 2. Debe demostrarse, en ejecución y desde el inicio, el recorrido Sandbox → Stage → Fact-Dimensiones, con carga efectiva tanto en el DW en la nube como en el DW local, y evidencia de que el sistema va a traer datos del DW local.
Entregables: 
1. Modelo de Datos Fact-Dimensions (Snowflake, Estrella) producido en DataModeler y el ERD. 
2. Arquitectura de Despliegue producida en Draw.io 
3. Pipelines de Transformación de Datos versionadas en Github, se utilizará git blame para corroborar cambios. 
4. Documentación desplegada con Github Actions (Mkdocs) en Github.
Fecha de Entrega: 21 de Junio a las 12:00 (Medio-Día)
