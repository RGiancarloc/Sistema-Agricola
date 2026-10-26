"""Pruebas de integracion de la API (OpenAPI y endpoints clave)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health(seeded):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["counts"]["parcelas"] > 0


def test_openapi_documented():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/v1/red" in paths
    assert "/api/v1/estadistico/mixto" in paths
    assert "/api/v1/optimizacion" in paths


def test_parcelas_geojson(seeded):
    r = client.get("/api/v1/datos/parcelas")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 10


def test_red_metrics(seeded):
    r = client.get("/api/v1/red")
    assert r.status_code == 200
    assert "connectance" in r.json()


def test_paisaje(seeded):
    r = client.get("/api/v1/paisaje")
    assert r.status_code == 200
    assert "resumen_global" in r.json()


def test_simulacion(seeded):
    r = client.get("/api/v1/simulacion/ssp245")
    assert r.status_code == 200
    assert r.json()["n_parcelas"] > 0


def test_optimizacion_ga(seeded):
    r = client.post("/api/v1/optimizacion", json={"metodo": "ga_abc"})
    assert r.status_code == 200
    assert "ga_abc" in r.json()


def test_ecosistema(seeded):
    r = client.get("/api/v1/ecosistema")
    assert r.status_code == 200
    assert "resumen" in r.json()


def test_export_csv(seeded):
    r = client.get("/api/v1/export/recomendaciones.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_export_pdf(seeded):
    r = client.get("/api/v1/export/reporte.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_simulacion_persist_and_export(seeded):
    r = client.get("/api/v1/simulacion/ssp245?persist=true")
    assert r.status_code == 200
    assert r.json()["persistido"] is True
    csv = client.get("/api/v1/export/resultados.csv?escenario=ssp245")
    assert csv.status_code == 200
    assert len(csv.content) > 1000

