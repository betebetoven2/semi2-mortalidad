-- ============================================================================
--  DW · Modelo Estrella — Defunciones (Mortalidad Guatemala 2015–2024)
--  Proyecto: Plataforma Analítica de Mortalidad — PNUD / MSPAS
--  Uso: importar en DataModeler para generar el ERD (Paso 6, Fase 2)
--
--  Grano del hecho: una defunción.
--  Construido a partir de stage.defunciones (capa conformada).
--  Las decisiones de diseño derivan del EDA Bronze→Stage:
--    - dim_grupo_etario sobre edad_anios corregida con Perdif (C2)
--    - dim_pueblo = etnia real Puedif, separada de Perdif (C1)
--    - dim_causa_cie10 con jerarquía 4→3→1 confirmada (H6)
--    - dim_geografia con area solo válida 2015–2017 (C4)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DIMENSIÓN TIEMPO
-- ----------------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    id_tiempo   INT          NOT NULL,   -- AAAAMM
    anio        INT          NOT NULL,
    mes         INT          NOT NULL,
    trimestre   INT          NOT NULL,
    periodo     VARCHAR(10)  NOT NULL,   -- PRE_COVID / POST_COVID
    CONSTRAINT pk_dim_tiempo PRIMARY KEY (id_tiempo)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN GEOGRAFÍA (ocurrencia)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_geografia (
    id_geografia  INT          NOT NULL,  -- depto(2) + municipio(4)
    codigo_depto  INT          NOT NULL,  -- 1..22
    codigo_muni   VARCHAR(4)   NOT NULL,  -- '0101'..  (lpad 4)
    area          VARCHAR(20)  NULL,      -- urbano/rural (solo 2015–2017, C4)
    CONSTRAINT pk_dim_geografia PRIMARY KEY (id_geografia)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN CAUSA CIE-10 (jerarquía 4 → 3 → 1)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_causa_cie10 (
    id_causa        VARCHAR(8)  NOT NULL,  -- código completo CIE-10
    codigo_completo VARCHAR(8)  NOT NULL,
    categoria_3     VARCHAR(3)  NOT NULL,  -- categoría (3 chars)
    capitulo_1      VARCHAR(1)  NOT NULL,  -- capítulo (1 char)
    mal_definida    BOOLEAN     NOT NULL,  -- capítulo R (~13.5%, C5)
    CONSTRAINT pk_dim_causa PRIMARY KEY (id_causa)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN SEXO
-- ----------------------------------------------------------------------------
CREATE TABLE dim_sexo (
    id_sexo    INT          NOT NULL,   -- 1,2,9
    sexo_desc  VARCHAR(15)  NOT NULL,
    CONSTRAINT pk_dim_sexo PRIMARY KEY (id_sexo)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN GRUPO ETARIO (7 grupos OPS + No especificado)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_grupo_etario (
    id_grupo_etario  INT          NOT NULL,  -- 0..6, 9
    grupo_edad       VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_dim_grupo_etario PRIMARY KEY (id_grupo_etario)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN PUEBLO / ETNIA (Puedif)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_pueblo (
    id_pueblo    INT          NOT NULL,  -- 1..5, 9
    pueblo_desc  VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_dim_pueblo PRIMARY KEY (id_pueblo)
);

-- ----------------------------------------------------------------------------
-- DIMENSIÓN LUGAR (sitio + asistencia + certificador)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_lugar (
    id_lugar           INT          NOT NULL,
    tipo_lugar         VARCHAR(5)   NULL,
    asistencia_medica  VARCHAR(5)   NULL,
    certificador       VARCHAR(5)   NULL,
    CONSTRAINT pk_dim_lugar PRIMARY KEY (id_lugar)
);

-- ----------------------------------------------------------------------------
-- TABLA DE HECHOS
-- ----------------------------------------------------------------------------
CREATE TABLE fact_defunciones (
    id_tiempo        INT          NOT NULL,
    id_geografia     INT          NOT NULL,
    id_causa         VARCHAR(8)   NOT NULL,
    id_sexo          INT          NOT NULL,
    id_grupo_etario  INT          NOT NULL,
    id_pueblo        INT          NOT NULL,
    id_lugar         INT          NOT NULL,
    periodo          VARCHAR(10)  NOT NULL,  -- degenerate dim
    cantidad         INT          NOT NULL,  -- medida (=1)

    CONSTRAINT fk_fact_tiempo
        FOREIGN KEY (id_tiempo)       REFERENCES dim_tiempo (id_tiempo),
    CONSTRAINT fk_fact_geografia
        FOREIGN KEY (id_geografia)    REFERENCES dim_geografia (id_geografia),
    CONSTRAINT fk_fact_causa
        FOREIGN KEY (id_causa)        REFERENCES dim_causa_cie10 (id_causa),
    CONSTRAINT fk_fact_sexo
        FOREIGN KEY (id_sexo)         REFERENCES dim_sexo (id_sexo),
    CONSTRAINT fk_fact_grupo_etario
        FOREIGN KEY (id_grupo_etario) REFERENCES dim_grupo_etario (id_grupo_etario),
    CONSTRAINT fk_fact_pueblo
        FOREIGN KEY (id_pueblo)       REFERENCES dim_pueblo (id_pueblo),
    CONSTRAINT fk_fact_lugar
        FOREIGN KEY (id_lugar)        REFERENCES dim_lugar (id_lugar)
);
