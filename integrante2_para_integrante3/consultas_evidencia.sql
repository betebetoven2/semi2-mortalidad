-- =============================================================================
-- CONSULTAS DE EVIDENCIA Y AUDITORÍA - FASE 1
-- Objetivo: Validar la integridad, linaje y volumetría de los datos cargados.
-- =============================================================================

SET search_path TO sandbox, public;

-- -----------------------------------------------------------------------------
-- 1. Auditoría de Volumetría Total
-- Comprueba que la suma de todas las tablas coincida con los 923,226 registros 
-- procesados por el script de Python.
-- -----------------------------------------------------------------------------
SELECT 
    'sandbox_ine_defunciones' AS nombre_tabla, COUNT(*) AS total_registros 
FROM sandbox_ine_defunciones
UNION ALL
SELECT 
    'sandbox_oms_indicadores', COUNT(*) 
FROM sandbox_oms_indicadores
UNION ALL
SELECT 
    'sandbox_worldbank_indicadores', COUNT(*) 
FROM sandbox_worldbank_indicadores
UNION ALL
SELECT 
    'sandbox_gdrive_diccionario', COUNT(*) 
FROM sandbox_gdrive_diccionario
ORDER BY total_registros DESC;

-- -----------------------------------------------------------------------------
-- 2. Validación de Linaje de Datos (Data Lineage)
-- Demuestra de qué archivo exacto proviene cada bloque de registros del INE 
-- y en qué momento se cargaron en el Sandbox.
-- -----------------------------------------------------------------------------
SELECT 
    fuente_archivo, 
    COUNT(*) AS total_filas,
    MIN(fecha_carga) AS momento_carga
FROM sandbox_ine_defunciones
GROUP BY fuente_archivo
ORDER BY fuente_archivo;

-- -----------------------------------------------------------------------------
-- 3. Auditoría de Calidad y Completitud (Nulos)
-- Verifica la salud de los datos del INE evaluando la cantidad de valores nulos 
-- en columnas críticas para análisis futuros.
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_evaluado,
    SUM(CASE WHEN sexo IS NULL THEN 1 ELSE 0 END) AS nulos_sexo,
    SUM(CASE WHEN edadif IS NULL THEN 1 ELSE 0 END) AS nulos_edad_fallecido,
    SUM(CASE WHEN depocu IS NULL THEN 1 ELSE 0 END) AS nulos_departamento_ocurrencia,
    SUM(CASE WHEN caudef IS NULL THEN 1 ELSE 0 END) AS nulos_causa_defuncion
FROM sandbox_ine_defunciones;

-- -----------------------------------------------------------------------------
-- 4. Perfilado de Datos: Top 5 Causas de Mortalidad (Histórico General)
-- Una consulta exploratoria rápida para confirmar que los datos tienen sentido 
-- lógico a nivel de negocio.
-- -----------------------------------------------------------------------------
SELECT 
    caudef AS codigo_cie_10, 
    COUNT(*) AS total_fallecimientos
FROM sandbox_ine_defunciones
WHERE caudef IS NOT NULL
GROUP BY caudef
ORDER BY total_fallecimientos DESC
LIMIT 5;

-- -----------------------------------------------------------------------------
-- 5. Validación de Datos Internacionales (Banco Mundial)
-- Confirma que los datos de Centroamérica se estructuraron correctamente por país.
-- -----------------------------------------------------------------------------
SELECT 
    country_value AS pais,
    COUNT(DISTINCT indicator_id) AS indicadores_unicos,
    COUNT(*) AS total_mediciones_historicas
FROM sandbox_worldbank_indicadores
GROUP BY country_value
ORDER BY pais;
