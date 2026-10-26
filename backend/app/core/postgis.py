"""Soporte PostGIS: columnas espaciales nativas e indices GIST.

Las geometrias viven como WKT (TEXT) en el esquema ORM para ser portables con
SQLite. En PostgreSQL/PostGIS este modulo anade una columna nativa
``geom_4326 geometry(<tipo>,4326)`` por tabla espacial, la mantiene sincronizada
con la columna WKT mediante disparadores y crea el indice GIST correspondiente.

Es idempotente: puede ejecutarse en cada arranque.
"""
from __future__ import annotations

from sqlalchemy import Engine

from app.core.logging import get_logger

logger = get_logger(__name__)

# tabla -> tipo de geometria nativa
GEOMETRY_TABLES: dict[str, str] = {
    "parcela": "POLYGON",
    "uso_suelo": "POLYGON",
    "habitat": "POLYGON",
    "colmena": "POINT",
    "estacion_clima": "POINT",
}

_TRIGGER_FN = """
CREATE OR REPLACE FUNCTION sync_geom_{table}() RETURNS trigger AS $$
BEGIN
    IF NEW.geom IS NULL THEN
        NEW.geom_4326 := NULL;
    ELSE
        NEW.geom_4326 := ST_SetSRID(ST_GeomFromText(NEW.geom), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def ensure_postgis_geometry(engine: Engine) -> None:
    """Crea columnas PostGIS nativas, disparadores de sincronizacion e indices GIST."""
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
        for table, gtype in GEOMETRY_TABLES.items():
            conn.exec_driver_sql(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "
                f"geom_4326 geometry({gtype}, 4326)"
            )
            conn.exec_driver_sql(_TRIGGER_FN.format(table=table))
            conn.exec_driver_sql(
                f"DROP TRIGGER IF EXISTS trg_sync_geom_{table} ON {table}"
            )
            conn.exec_driver_sql(
                f"CREATE TRIGGER trg_sync_geom_{table} "
                f"BEFORE INSERT OR UPDATE OF geom ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION sync_geom_{table}()"
            )
            conn.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_geom_4326 "
                f"ON {table} USING GIST (geom_4326)"
            )
            conn.exec_driver_sql(
                f"UPDATE {table} SET geom_4326 = "
                f"ST_SetSRID(ST_GeomFromText(geom), 4326) "
                f"WHERE geom IS NOT NULL AND geom_4326 IS NULL"
            )
    logger.info("Esquema PostGIS preparado (%d tablas espaciales)", len(GEOMETRY_TABLES))
