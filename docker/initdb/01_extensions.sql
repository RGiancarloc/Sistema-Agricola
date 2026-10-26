-- ===========================================================================
-- Inicializacion PostGIS del gemelo digital agricola.
-- Se ejecuta automaticamente en el primer arranque del contenedor `db`.
-- El esquema de tablas lo crea la aplicacion (SQLAlchemy) usando tipos
-- geometry(...,4326) de PostGIS, por lo que aqui solo se habilitan extensiones.
-- ===========================================================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- Esquema dedicado (opcional, comentado). Por defecto usamos `public`.
-- CREATE SCHEMA IF NOT EXISTS agricola;
