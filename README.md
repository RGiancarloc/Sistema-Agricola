# Gemelo digital de paisajes agricolas y redes de polinizadores

Plataforma web que modela espacio-temporalmente el paisaje agricola y la red
planta-polinizador, simula escenarios climaticos y recomienda intervenciones
(habitats, colmenas, manejo) para maximizar productividad y servicios
ecosistemicos.

- **Zona de estudio**: Valle de Moche y Chavimochic (La Libertad, Peru).
- **Cultivos de referencia** (parametrizables): palto, arandano, esparrago.

> Los datos incluidos son **sinteticos pero realistas** (se generan con semilla
> fija), de modo que el sistema corre de inmediato sin datos reales.

---

## 1. Arquitectura

Arquitectura modular por capas: `domain` (puro) <- `servicios analiticos`
(paisaje, red, estadistica, simulacion, optimizacion, ecosistema) <- `api`.

```
SistemaAgricola/
├─ docker-compose.yml            # PostGIS + backend + frontend
├─ .env.example                  # variables de entorno
├─ config/                       # parametros YAML (reproducibilidad)
│  ├─ params.yaml                # semilla, bbox, escenarios, optimizacion
│  ├─ crops.yaml                 # parametros por cultivo
│  └─ scenarios.yaml             # deltas climaticos por SSP
├─ docker/initdb/                # habilitacion de PostGIS
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements*.txt
│  ├─ pytest.ini
│  ├─ app/
│  │  ├─ main.py                 # FastAPI (OpenAPI en /docs)
│  │  ├─ core/                   # config, db, geo, logging, semillas
│  │  ├─ domain/models.py        # entidades ORM (PostGIS/SQLite)
│  │  ├─ ingestion/              # cargadores + validacion (Fase 1)
│  │  ├─ landscape/analysis.py   # conectividad y habitat (Fase 2)
│  │  ├─ network/analysis.py     # red bipartita: NODF, modularidad, robustez
│  │  ├─ stats/mixed_effects.py  # modelos mixtos (Fase 2)
│  │  ├─ simulation/engine.py    # motor mensual de escenarios (Fase 3)
│  │  ├─ optimization/           # MIQCP (Pyomo) + GA-ABC hibrido (Fase 3)
│  │  ├─ ecosystem/indicators.py # indicadores y score agregado (Fase 3)
│  │  ├─ services/               # repositorio + pipelines
│  │  ├─ api/v1/                 # routers REST documentados
│  │  └─ seeds/generate.py       # generador de datos sinteticos
│  └─ tests/                     # pytest (calculos criticos)
└─ frontend/                     # Next.js + TypeScript (Fase 4)
   ├─ app/                       # layout + pagina
   ├─ components/                # mapa Leaflet, series, grafo, dashboard
   └─ lib/api.ts                 # cliente tipado de la API
```

## 2. Stack

| Capa      | Tecnologia |
|-----------|------------|
| Backend   | Python 3.11 + FastAPI |
| BD        | PostgreSQL + PostGIS (SQLite en desarrollo) |
| Calculo   | NumPy, Pandas, GeoPandas, SciPy, statsmodels, NetworkX, Pyomo (HiGHS) |
| Frontend  | Next.js + TypeScript + Leaflet + Recharts |
| Infra     | Docker Compose |

---

## 3. Inicio rapido

### Opcion A - Docker Compose (recomendada)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000  ·  Docs OpenAPI: http://localhost:8000/docs
- Dashboard: http://localhost:3000

Al arrancar, el backend crea el esquema PostGIS y siembra los datos sinteticos
si la base esta vacia.

### Opcion B - Local (sin Docker)

Backend (base SQLite):

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate     # Windows PowerShell
pip install -r requirements-dev.txt
python -m app.seeds.generate                          # genera datos sinteticos
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

> Variables: `SA_DATABASE_URL`, `SA_SEED`, `SA_CONFIG_DIR`, `SA_CORS_ORIGINS`,
> `NEXT_PUBLIC_API_URL` (ver `.env.example`).

---

## 4. Reproducibilidad

- Toda la aleatoriedad deriva de `seed` en `config/params.yaml` (y `SA_SEED`).
- Parametros de cultivo, escenarios y optimizacion viven en YAML, no en codigo.
- Regenerar datos: `POST /api/v1/datos/seed` o `python -m app.seeds.generate`.

---

## 5. API REST (resumen)

Todos los endpoints bajo `/api/v1` y documentados en `/docs` (OpenAPI).

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET  | `/health` | Estado y conteos de datos |
| GET  | `/config` | Parametros/cultivos/escenarios activos |
| GET  | `/datos/parcelas` | Parcelas como GeoJSON |
| GET  | `/datos/habitats`, `/datos/colmenas`, `/datos/uso-suelo` | Capas GeoJSON |
| GET  | `/datos/clima`, `/datos/ndvi`, `/datos/escenarios`, `/datos/intervenciones` | Series/tablas |
| POST | `/datos/seed` | Regenera datos sinteticos |
| GET  | `/paisaje` | Conectividad, habitat y contexto por parcela |
| GET  | `/red`, `/red/grafo` | Metricas de red y grafo para visualizacion |
| GET  | `/estadistico/mixto` | Modelo mixto productividad ~ polinizacion + clima + paisaje |
| GET  | `/simulacion/{escenario}` | Simulacion mensual (`?persist=true` guarda) |
| POST | `/simulacion/comparar` | Compara varios escenarios |
| POST | `/optimizacion` | MIQCP vs GA-ABC (`persist` guarda recomendaciones) |
| GET  | `/optimizacion/recomendaciones` | Recomendaciones almacenadas |
| GET  | `/ecosistema` | Indicadores y score agregado |
| GET  | `/export/resultados.csv`, `/export/recomendaciones.csv`, `/export/reporte.pdf` | Exportacion |

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/v1/optimizacion \
     -H "Content-Type: application/json" \
     -d '{"metodo":"comparar","persist":true}'
```

---

## 6. Modelo cientifico (sintesis)

- **Paisaje (M2)**: distancia great-circle a habitat/colmenas, area de habitat en
  un radio, indice de conectividad estructural (componentes, mayor componente).
- **Red (M3)**: matriz de visitas -> connectance, **NODF** (anidamiento),
  **modularidad** (Louvain), **robustez** ante extincion secuencial de
  polinizadores.
- **Estadistica (M4)**: `MixedLM` con
  `rendimiento ~ visitas + riqueza + clima + paisaje + C(cultivo)`, intercepto
  aleatorio por parcela `(1|parcela)`; reporta coeficientes, IC, ICC, AIC/BIC.
- **Simulacion (M5)**: paso mensual 2015-2050;
  `rendimiento = base * f_clima(T) * f_polinizacion(servicio) * (1+efecto parcela)`,
  con deltas de temperatura/precipitacion interpolados por escenario
  (linea base, SSP2-4.5, SSP5-8.5).
- **Optimizacion (M6)**:
  - **MIQCP** con Pyomo (binarias de intervencion + area continua + termino
    cuadratico convexo), resuelto con **HiGHS** (`appsi_highs`). Si el solver
    no soporta MIQP, se resuelve la version MILP (se reporta en `nota`).
  - **GA-ABC hibrido**: algoritmo genetico + colonia artificial de abejas
    (empleadas / observadoras / exploradoras) con la misma funcion objetivo y
    restricciones de presupuesto y area. Se comparan ambos enfoques
    (beneficio, costo, tiempo y brecha %).
- **Servicios ecosistemicos (M7)**: polinizacion (saturacion exponencial),
  productividad (relativa al potencial) y biodiversidad (riqueza + habitat +
  conectividad), combinadas en un **score** con pesos configurables.

---

## 7. Dashboard

- Mapa interactivo (Leaflet): parcelas por cultivo, habitats y colmenas.
- Series temporales por escenario (Recharts).
- Grafo bipartita planta-polinizador.
- Panel de servicios ecosistemicos y score.
- Comparador de escenarios y panel de recomendaciones.
- Exportacion PDF/CSV.

---

## 8. Pruebas

```bash
cd backend
pytest                 # 35 pruebas de calculos criticos y de la API
pytest --cov=app
```

Cubren: generacion de datos, geometria, metricas de red (NODF/robustez),
modelo mixto, simulacion (monotonia del delta climatico y del calentamiento),
optimizacion (factibilidad de presupuesto/area), indicadores e integracion API
(incluida exportacion PDF/CSV).

---

## 9. Entrega por fases

| Fase | Contenido | Estado |
|------|-----------|--------|
| 1 | Estructura, Docker, esquema PostGIS, seed sintetico | Completa |
| 2 | API + modelos (red, efectos mixtos, paisaje) | Completa |
| 3 | Simulacion + optimizacion (MIQCP y GA-ABC) | Completa |
| 4 | Dashboard (mapa, series, grafo, escenarios, recomendaciones) | Completa |
| 5 | Pruebas, documentacion y validacion | Completa |

---

## 10. Limitaciones y notas

- Datos **sinteticos**: calibrados a ordenes de magnitud; deben reemplazarse por
  observaciones reales para uso operativo.
- `statsmodels` con REML no expone AIC/BIC; se calculan con el numero de
  parametros estimados (ver `stats/mixed_effects.py`).
- El solver de MIQCP por defecto (HiGHS) no resuelve MIQP; la formulacion
  incluye el termino cuadratico y, si no hay solver compatible, se resuelve su
  linealizacion (MILP), indicado en el campo `nota` de la respuesta.
- En desarrollo se usa SQLite (geometrias como WKT); en PostgreSQL/PostGIS las
  mismas columnas se materializan como tipo `geometry(...,4326)` con indice GIST.
