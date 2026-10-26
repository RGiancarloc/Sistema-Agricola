"""Generacion de datos sinteticos realistas y sembrado de la base de datos.

Ejecutable como modulo::

    python -m app.seeds.generate --reset

Todo el muestreo deriva de ``settings.seed`` -> reproducible.
"""
from __future__ import annotations

import argparse
import math
from typing import Dict, List, Sequence

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import crops, params, scenarios, settings
from app.core.db import Base, SessionLocal, engine, init_db
from app.core.geo import make_rectangle, point_wkt
from app.core.logging import get_logger
from app.core.seed_utils import master_rng
from app.domain import models as M

logger = get_logger(__name__)

CULTIVOS = sorted(crops().keys())
M_PER_DEG_LAT = 111_320.0


def _m_per_deg_lon(lat: float) -> float:
    return M_PER_DEG_LAT * math.cos(math.radians(lat))


# Clusters de la zona de estudio: valle de Moche y Chavimochic (Viru).
CLUSTERS = [
    {"name": "Moche", "lon": -79.00, "lat": -8.17, "weight": 0.45, "spread": 0.055},
    {"name": "Chavimochic", "lon": -78.78, "lat": -8.42, "weight": 0.55, "spread": 0.085},
]

PLANTAS_SILVESTRES = [
    "Baccharis salicifolia",
    "Acacia macracantha",
    "Prosopis pallida",
    "Lantana camara",
    "Brassica campestris",
    "Medicago sativa",
    "Taraxacum officinale",
    "Helianthus annuus",
    "Trifolium pratense",
    "Vicia faba",
    "Eucalyptus globulus",
    "Foeniculum vulgare",
    "Solanum pimpinellifolium",
]

# gremio, anidamiento, rango de forrajeo (m) tipicos
POLINIZADORES_BASE = [
    ("Apis mellifera", "Apidae", "abeja", "cavidad", 2000),
    ("Bombus opifex", "Apidae", "abeja", "cavidad", 1500),
    ("Xylocopa splendidula", "Apidae", "abeja", "tallo", 900),
    ("Centris cineraria", "Apidae", "abeja", "suelo", 1200),
    ("Anthophora spp.", "Apidae", "abeja", "suelo", 900),
    ("Halictus spp.", "Halictidae", "abeja", "suelo", 400),
    ("Lasioglossum spp.", "Halictidae", "abeja", "suelo", 350),
    ("Augochlora spp.", "Halictidae", "abeja", "suelo", 300),
    ("Andrena spp.", "Andrenidae", "abeja", "suelo", 500),
    ("Diadasia spp.", "Apidae", "abeja", "suelo", 600),
    ("Colletes spp.", "Colletidae", "abeja", "suelo", 450),
    ("Megachile spp.", "Megachilidae", "abeja", "cavidad", 600),
    ("Euglossa spp.", "Apidae", "abeja", "cavidad", 800),
    ("Toxomerus spp.", "Syrphidae", "mosca", "otro", 300),
    ("Allograpta spp.", "Syrphidae", "mosca", "otro", 280),
    ("Eristalis tenax", "Syrphidae", "mosca", "otro", 500),
    ("Copestylum spp.", "Syrphidae", "mosca", "otro", 400),
    ("Familia Bombyliidae", "Bombyliidae", "mosca", "suelo", 350),
    ("Familia Tachinidae", "Tachinidae", "mosca", "otro", 300),
    ("Cycloneda sanguinea", "Coccinellidae", "escarabajo", "otro", 200),
    ("Astylus spp.", "Melyridae", "escarabajo", "otro", 250),
    ("Macrodactylus spp.", "Scarabaeidae", "escarabajo", "suelo", 300),
    ("Danaus erippus", "Nymphalidae", "mariposa", "otro", 700),
    ("Vanessa carye", "Nymphalidae", "mariposa", "otro", 600),
    ("Leptotes trigemmatus", "Lycaenidae", "mariposa", "otro", 350),
    ("Hylaeus spp.", "Colletidae", "abeja", "tallo", 400),
]

INTERVENCIONES_CATALOGO = [
    ("habitat_floral", "Franja de habitat floral para polinizadores", "habitat",
     1200.0, 0.0, 0.12, 0.20, 0.05, 5,
     "Siembra de mezcla de flores nativas en bordes y franjas no productivas."),
    ("habitat_nesting", "Sitios de nidificacion para abejas silvestres", "habitat",
     900.0, 0.0, 0.10, 0.16, 0.03, 7,
     "Sustratos de suelo desnudo y madera perforada para abejas solitarias."),
    ("corredor_ecologico", "Corredor ecologico entre parches", "habitat",
     1500.0, 0.0, 0.08, 0.18, 0.04, 8,
     "Conectividad vegetal que reduce aislamiento funcional del paisaje."),
    ("colmena_manejo", "Refuerzo de colmenas manejadas", "manejo",
     0.0, 600.0, 0.15, 0.02, 0.08, 3,
     "Instalacion/refuerzo de colmenas de Apis mellifera con manejo sanitario."),
    ("manejo_integrado_plagas", "Manejo integrado de plagas (MIP)", "manejo",
     400.0, 0.0, 0.06, 0.10, 0.06, 4,
     "Reduccion de agroquimicos que danan polinizadores."),
    ("riego_eficiente", "Riego eficiente tecnificado", "manejo",
     800.0, 0.0, 0.00, 0.05, 0.10, 6,
     "Optimiza disponibilidad hidrica y estabilidad del rendimiento."),
]


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------
def _sample_cluster(rng: np.random.Generator) -> dict:
    idx = rng.choice(len(CLUSTERS), p=[c["weight"] for c in CLUSTERS])
    return CLUSTERS[int(idx)]


def gen_parcelas(rng: np.random.Generator, n: int) -> List[M.Parcela]:
    parcelas: List[M.Parcela] = []
    # pesos por cultivo (dominancia observada en la zona)
    crop_names = ["palto", "arandano", "esparrago"]
    crop_p = [0.40, 0.34, 0.26]
    for i in range(n):
        cl = _sample_cluster(rng)
        lon = cl["lon"] + rng.normal(0, cl["spread"])
        lat = cl["lat"] + rng.normal(0, cl["spread"] * 0.7)
        crop = crop_names[int(rng.choice(len(crop_names), p=crop_p))]
        area_ha = float(np.clip(rng.lognormal(mean=math.log(6.0), sigma=0.7), 0.5, 40.0))
        side_m = math.sqrt(area_ha * 10_000.0)
        width_deg = side_m * rng.uniform(0.8, 1.25) / _m_per_deg_lon(lat)
        height_deg = side_m * rng.uniform(0.8, 1.25) / M_PER_DEG_LAT
        angle = float(rng.uniform(0, 180))
        geom = make_rectangle(lon, lat, width_deg, height_deg, angle)
        parcela = M.Parcela(
            codigo=f"PARC-{i + 1:03d}",
            cultivo=crop,
            variedad=None,
            area_ha=round(area_ha, 3),
            tipo_suelo=str(rng.choice(["franco", "franco-arenoso", "arenoso", "franco-arcilloso"])),
            sistema_riego=str(rng.choice(["goteo", "microaspersion", "gravedad", "aspersion"])),
            edad_plantacion_anios=round(float(rng.uniform(1, 15)), 1),
            geom=geom,
        )
        parcelas.append(parcela)
    return parcelas


def gen_estaciones(rng: np.random.Generator, n: int) -> List[M.EstacionClima]:
    estaciones: List[M.EstacionClima] = []
    for i in range(n):
        cl = CLUSTERS[i % len(CLUSTERS)]
        lon = cl["lon"] + rng.normal(0, 0.03)
        lat = cl["lat"] + rng.normal(0, 0.02)
        elev = float(np.clip(rng.normal(80, 60), 5, 400))
        estaciones.append(
            M.EstacionClima(
                codigo=f"EST-{i + 1:02d}",
                nombre=f"Estacion {cl['name']}-{i + 1}",
                elevacion_m=round(elev, 1),
                geom=point_wkt(lon, lat),
            )
        )
    return estaciones


def gen_clima(
    rng: np.random.Generator, estaciones: Sequence[M.EstacionClima]
) -> tuple[List[M.ObservacionClima], Dict[int, dict]]:
    cfg = params()["simulation"]
    y0, y1 = cfg["year_start"], cfg["year_end"]
    obs: List[M.ObservacionClima] = []
    # Anomalias tipo ENSO en anios calidos conocidos de la costa norte.
    enso_years = {2015: -0.3, 2016: 0.4, 2017: 1.2, 2018: 0.2, 2019: 0.1,
                  2020: 0.0, 2021: 0.1, 2022: 0.2, 2023: 1.0, 2024: 0.4}
    annual: Dict[int, dict] = {}
    for est in estaciones:
        base = 21.5 - est.elevacion_m * 0.006
        for anio in range(y0, y1 + 1):
            trend = 0.03 * (anio - y0)  # calentamiento historico leve
            gdd_acc = 0.0
            tsum = psum = 0.0
            for mes in range(1, 13):
                seasonal = 3.6 * math.cos(2 * math.pi * (mes - 2) / 12)
                tmean = base + seasonal + trend + enso_years.get(anio, 0.0) * 0.6
                tmean += rng.normal(0, 0.6)
                tmax = tmean + 4.5 + rng.normal(0, 0.7)
                tmin = tmean - 4.5 + rng.normal(0, 0.7)
                # precipitacion desertica: picos en verano
                p = max(0.0, rng.gamma(1.2, 0.9) + 1.5 * math.cos(2 * math.pi * (mes - 2) / 12))
                p *= (1.0 + max(0.0, enso_years.get(anio, 0.0)))
                humedad = float(np.clip(rng.normal(82, 6), 55, 98))
                gdd = max(0.0, ((tmax + tmin) / 2.0) - 10.0)
                gdd_acc += gdd
                tsum += tmean
                psum += p
                obs.append(
                    M.ObservacionClima(
                        estacion=est, anio=anio, mes=mes,
                        tmax_c=round(tmax, 2), tmin_c=round(tmin, 2),
                        tmean_c=round(tmean, 2), precip_mm=round(p, 2),
                        humedad_pct=round(humedad, 1), gdd=round(gdd, 2),
                    )
                )
            annual.setdefault(anio, {"tmean": [], "gdd": [], "precip": []})
            annual[anio]["tmean"].append(tsum / 12.0)
            annual[anio]["gdd"].append(gdd_acc)
            annual[anio]["precip"].append(psum)
    # Promedios multi-estacion por anio.
    annual = {
        a: {
            "tmean": float(np.mean(v["tmean"])),
            "gdd": float(np.mean(v["gdd"])),
            "precip": float(np.mean(v["precip"])),
        }
        for a, v in annual.items()
    }
    return obs, annual


def gen_plantas(rng: np.random.Generator) -> List[M.EspeciePlanta]:
    plantas: List[M.EspeciePlanta] = []
    for name in CULTIVOS:
        c = crops()[name]
        meses = c["fenologia"]["floracion_meses"]
        plantas.append(
            M.EspeciePlanta(
                nombre=c["cientifico"], tipo="cultivo", es_cultivo_ref=True,
                meses_floracion=",".join(str(m) for m in meses),
            )
        )
    for name in PLANTAS_SILVESTRES:
        start = int(rng.integers(1, 13))
        span = int(rng.integers(3, 6))
        meses = sorted({((start + k - 1) % 12) + 1 for k in range(span)})
        plantas.append(
            M.EspeciePlanta(
                nombre=name, tipo="silvestre", es_cultivo_ref=False,
                meses_floracion=",".join(str(m) for m in meses),
            )
        )
    return plantas


def gen_polinizadores(rng: np.random.Generator) -> List[M.Polinizador]:
    pols: List[M.Polinizador] = []
    for name, taxon, gremio, nido, rango in POLINIZADORES_BASE:
        start = int(rng.integers(1, 13))
        span = int(rng.integers(4, 12))
        meses = sorted({((start + k - 1) % 12) + 1 for k in range(span)})
        pols.append(
            M.Polinizador(
                nombre=name, taxon=taxon, gremio=gremio, anidamiento=nido,
                rango_forrajeo_m=float(rango),
                meses_actividad=",".join(str(m) for m in meses),
            )
        )
    return pols


def _months(spec: str) -> set[int]:
    try:
        return {int(x) for x in spec.split(",") if x.strip()}
    except ValueError:
        return set(range(1, 13))


def gen_ndvi(
    rng: np.random.Generator, parcelas: Sequence[M.Parcela]
) -> List[M.IndiceVegetacion]:
    cfg = params()["simulation"]
    y0, y1 = cfg["year_start"], cfg["year_end"]
    out: List[M.IndiceVegetacion] = []
    for p in parcelas:
        peak = crops()[p.cultivo]["ndvi_pico_mes"]
        base = float(rng.uniform(0.45, 0.65))
        amp = float(rng.uniform(0.15, 0.28))
        for anio in range(y0, y1 + 1):
            for mes in range(1, 13):
                seasonal = amp * math.cos(2 * math.pi * (mes - peak) / 12)
                val = base + seasonal + rng.normal(0, 0.03)
                out.append(
                    M.IndiceVegetacion(
                        parcela=p, anio=anio, mes=mes,
                        ndvi=round(float(np.clip(val, 0.05, 0.95)), 4),
                    )
                )
    return out


def gen_red(
    rng: np.random.Generator,
    parcelas: Sequence[M.Parcela],
    plantas: Sequence[M.EspeciePlanta],
    polinizadores: Sequence[M.Polinizador],
) -> List[M.ObservacionRed]:
    """Red bipartita con estructura anidada (latentes aditivos)."""
    cultura_por_nombre = {crops()[k]["cientifico"]: k for k in CULTIVOS}
    # latentes -> anidamiento: generalista alto, especialista bajo
    lat_planta = {p.nombre: float(x) for p, x in zip(plantas, rng.uniform(0.2, 1.0, len(plantas)))}
    lat_pol = {q.nombre: float(x) for q, x in zip(polinizadores, rng.uniform(0.2, 1.0, len(polinizadores)))}
    sim = params()["simulation"]
    anios = list(range(sim["year_start"], sim["year_end"] + 1))
    out: List[M.ObservacionRed] = []
    silvestres = [p for p in plantas if not p.es_cultivo_ref]
    for p in parcelas:
        crop_sci = crops()[p.cultivo]["cientifico"]
        crop_planta = next(pl for pl in plantas if pl.nombre == crop_sci)
        n_wild = int(rng.integers(2, 5))
        wild = list(rng.choice(len(silvestres), size=min(n_wild, len(silvestres)), replace=False))
        disponibles = [crop_planta] + [silvestres[int(i)] for i in wild]
        for pl in disponibles:
            fm = _months(pl.meses_floracion)
            for q in polinizadores:
                am = _months(q.meses_actividad)
                overlap = fm & am
                if not overlap:
                    continue
                # umbral de interaccion (estructura anidada)
                if lat_planta[pl.nombre] + lat_pol[q.nombre] < 1.0:
                    # pequena probabilidad residual de interacciones debiles
                    if rng.random() > 0.06:
                        continue
                lam = 1.2 * lat_planta[pl.nombre] * lat_pol[q.nombre] * len(overlap)
                for anio in anios:
                    for mes in sorted(overlap):
                        v = rng.poisson(lam)
                        if v <= 0:
                            continue
                        out.append(
                            M.ObservacionRed(
                                parcela=p, planta=pl, polinizador=q,
                                anio=anio, mes=mes, visitas=float(v),
                            )
                        )
    return out


def gen_rendimiento(
    rng: np.random.Generator,
    parcelas: Sequence[M.Parcela],
    annual_clima: Dict[int, dict],
    red: Sequence[M.ObservacionRed],
) -> List[M.ObservacionRendimiento]:
    cfg = params()["simulation"]
    y0, y1 = cfg["year_start"], cfg["year_end"]
    # metricas de red por (parcela, anio): tasa mensual de visitas y riqueza
    vis: Dict[tuple, float] = {}
    rich: Dict[tuple, set] = {}
    visits_total: Dict[str, float] = {}
    rich_total: Dict[str, set] = {}
    for o in red:
        key = (o.parcela.codigo, o.anio)
        vis[key] = vis.get(key, 0.0) + o.visitas
        rich.setdefault(key, set()).add(o.polinizador.nombre)
        visits_total[o.parcela.codigo] = visits_total.get(o.parcela.codigo, 0.0) + o.visitas
        rich_total.setdefault(o.parcela.codigo, set()).add(o.polinizador.nombre)
    out: List[M.ObservacionRendimiento] = []
    for p in parcelas:
        c = crops()[p.cultivo]
        # calidad latente de la parcela (efecto aleatorio por parcela)
        calidad = float(rng.normal(0, 0.08))
        for anio in range(y0, y1 + 1):
            clima = annual_clima[anio]
            visits = vis.get((p.codigo, anio), 0.0) / 12.0
            richness = float(len(rich.get((p.codigo, anio), set())))
            clim_factor = float(np.clip(1.0 + 0.02 * (clima["tmean"] - 21.0), 0.8, 1.15))
            poll_factor = _pollination_factor(c, visits, richness, rng)
            noise = float(rng.normal(0, 0.06))
            rend = c["rendimiento_base_t_ha"] * clim_factor * poll_factor * (1.0 + calidad + noise)
            out.append(
                M.ObservacionRendimiento(
                    parcela=p, anio=anio,
                    rendimiento_t_ha=round(max(0.1, rend), 3),
                    precipitacion_anual_mm=round(clima["precip"], 1),
                    gdd_anual=round(clima["gdd"], 1),
                    t_mean_anual_c=round(clima["tmean"], 2),
                )
            )
    return out


def _pollination_factor(c: dict, visits: float, richness: float,
                        rng: np.random.Generator) -> float:
    """Factor multiplicador de rendimiento por polinizacion (0.6-1.1)."""
    dep = c["dependencia_polinizadores_silvestres"] + c["dependencia_abeja_mielifera"]
    # saturacion: mas visitas y riqueza -> mas servicio, con rendimientos decrecientes
    service = 1.0 - math.exp(-(0.06 * visits + 0.12 * richness))
    deficit = max(0.0, 1.0 - service)
    factor = 1.0 - dep * c["sensibilidad_deficit_polinizacion"] * deficit
    factor += rng.normal(0, 0.01)
    return float(np.clip(factor, 0.6, 1.15))


def gen_intervenciones() -> List[M.Intervencion]:
    out: List[M.Intervencion] = []
    for cod, nombre, tipo, ch, cf, ep, eb, eprod, vida, desc in INTERVENCIONES_CATALOGO:
        out.append(
            M.Intervencion(
                codigo=cod, nombre=nombre, tipo=tipo, costo_usd_ha=ch,
                costo_usd_fijo=cf, efecto_polinizacion=ep, efecto_biodiversidad=eb,
                efecto_productividad=eprod, vida_util_anios=vida, descripcion=desc,
            )
        )
    return out


def gen_escenarios() -> List[M.Escenario]:
    cfg = scenarios()["escenarios"]
    out: List[M.Escenario] = []
    for cod, s in cfg.items():
        out.append(
            M.Escenario(
                codigo=cod, nombre=s["nombre"], ssp=s.get("ssp"),
                anio_inicio=2015, anio_fin=2050,
                delta_temp_final_c=float(s["delta_temp_anual"][-1]),
                delta_precip_final_pct=float(s["delta_precip_anual_pct"][-1]),
                descripcion=s.get("descripcion"),
            )
        )
    return out


def gen_habitats(rng: np.random.Generator, n: int) -> List[M.Habitat]:
    out: List[M.Habitat] = []
    for i in range(n):
        cl = _sample_cluster(rng)
        lon = cl["lon"] + rng.normal(0, cl["spread"] * 1.2)
        lat = cl["lat"] + rng.normal(0, cl["spread"] * 0.9)
        area_ha = float(np.clip(rng.lognormal(math.log(2.5), 0.6), 0.2, 20.0))
        side_m = math.sqrt(area_ha * 10_000.0)
        w = side_m * rng.uniform(0.8, 1.3) / _m_per_deg_lon(lat)
        h = side_m * rng.uniform(0.8, 1.3) / M_PER_DEG_LAT
        out.append(
            M.Habitat(
                codigo=f"HAB-{i + 1:03d}",
                tipo=str(rng.choice(["floral", "nesting", "mixto"])),
                calidad=round(float(rng.uniform(0.3, 0.95)), 3),
                area_ha=round(area_ha, 3),
                geom=make_rectangle(lon, lat, w, h, float(rng.uniform(0, 180))),
            )
        )
    return out


def gen_colmenas(rng: np.random.Generator, n: int) -> List[M.Colmena]:
    out: List[M.Colmena] = []
    for i in range(n):
        cl = _sample_cluster(rng)
        lon = cl["lon"] + rng.normal(0, cl["spread"])
        lat = cl["lat"] + rng.normal(0, cl["spread"] * 0.8)
        out.append(
            M.Colmena(
                codigo=f"COL-{i + 1:03d}", n_colmenas=int(rng.integers(5, 40)),
                activa=True, geom=point_wkt(lon, lat),
            )
        )
    return out


def gen_uso_suelo(rng: np.random.Generator, n: int = 24) -> List[M.UsoSuelo]:
    clases = ["cultivo_agricola", "matorral_costero", "suelo_desnudo", "urbano", "humedal"]
    out: List[M.UsoSuelo] = []
    for i in range(n):
        cl = _sample_cluster(rng)
        lon = cl["lon"] + rng.normal(0, cl["spread"] * 1.5)
        lat = cl["lat"] + rng.normal(0, cl["spread"] * 1.2)
        area_ha = float(rng.uniform(5, 200))
        side_m = math.sqrt(area_ha * 10_000.0)
        w = side_m / _m_per_deg_lon(lat)
        h = side_m / M_PER_DEG_LAT
        out.append(
            M.UsoSuelo(clase=str(rng.choice(clases)), area_ha=round(area_ha, 1),
                       geom=make_rectangle(lon, lat, w, h, float(rng.uniform(0, 180))))
        )
    return out


# ---------------------------------------------------------------------------
# Orquestacion del seed
# ---------------------------------------------------------------------------
def seed_all(session: Session, reset: bool = True, verbose: bool = True) -> dict:
    sd = params()["seed_data"]
    rng = master_rng()

    if reset:
        Base.metadata.drop_all(bind=engine)
        init_db()
    else:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

    parcelas = gen_parcelas(rng, sd["n_parcelas"])
    estaciones = gen_estaciones(rng, sd["n_estaciones_clima"])
    obs_clima, annual_clima = gen_clima(rng, estaciones)
    plantas = gen_plantas(rng)
    polinizadores = gen_polinizadores(rng)
    red = gen_red(rng, parcelas, plantas, polinizadores)
    ndvi = gen_ndvi(rng, parcelas)
    rendimiento = gen_rendimiento(rng, parcelas, annual_clima, red)
    habitats = gen_habitats(rng, sd["n_habitats"])
    colmenas = gen_colmenas(rng, sd["n_colmenas"])
    uso = gen_uso_suelo(rng)
    intervenciones = gen_intervenciones()
    escenarios = gen_escenarios()

    session.add_all(parcelas)
    session.add_all(estaciones)
    session.add_all(obs_clima)
    session.add_all(plantas)
    session.add_all(polinizadores)
    session.add_all(habitats)
    session.add_all(colmenas)
    session.add_all(uso)
    session.add_all(intervenciones)
    session.add_all(escenarios)
    session.flush()  # asigna IDs para relaciones
    session.add_all(red)
    session.add_all(ndvi)
    session.add_all(rendimiento)
    session.commit()

    resumen = {
        "parcelas": len(parcelas),
        "estaciones": len(estaciones),
        "observaciones_clima": len(obs_clima),
        "especies_planta": len(plantas),
        "polinizadores": len(polinizadores),
        "interacciones_red": len(red),
        "registros_ndvi": len(ndvi),
        "rendimientos": len(rendimiento),
        "habitats": len(habitats),
        "colmenas": len(colmenas),
        "uso_suelo": len(uso),
        "intervenciones": len(intervenciones),
        "escenarios": len(escenarios),
    }
    if verbose:
        logger.info("Seed completado: %s", resumen)
    return resumen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera datos sinteticos (seed).")
    parser.add_argument("--no-reset", action="store_true",
                        help="No recrea el esquema; solo limpia y reinserta.")
    args = parser.parse_args(argv)
    init_db()
    with SessionLocal() as session:
        resumen = seed_all(session, reset=not args.no_reset)
    print("Seed completado:")
    for k, v in resumen.items():
        print(f"  {k:>22}: {v}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
