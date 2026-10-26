"""Verifica que el modelo estadistico de efectos mixtos corra sobre los datos reales integrados."""
from app.core.config import params
from app.core.db import SessionLocal
from app.landscape.analysis import landscape_metrics
from app.services import repository as repo
from app.stats.mixed_effects import fit_mixed_effects


def test_real_data_mixed_effects(session=None, seeded=None):
    from app.core.db import init_db
    from app.domain import models as M
    from app.ingestion.ingest_real import ingest_real_data
    from app.seeds.generate import seed_all
    from sqlalchemy import func, select

    own_session = False
    if session is None:
        init_db()
        session = SessionLocal()
        own_session = True

    try:
        # Asegurar que existan parcelas base en la BD
        has_parcelas = session.scalar(select(func.count()).select_from(M.Parcela)) or 0
        if has_parcelas == 0:
            seed_all(session, reset=True)

        # Asegurar que los datos reales esten presentes en la BD actual
        n_obs = session.scalar(select(func.count()).select_from(M.ObservacionRendimiento)) or 0
        if n_obs < 540:
            ingest_real_data(session, verbose=False)

        p = params()["landscape"]
        parcelas = repo.parcelas_entities(session)
        habitats = repo.habitats_entities(session)
        colmenas = repo.colmenas_entities(session)
        per_parcel = landscape_metrics(
            parcelas, habitats, colmenas,
            radius_m=p["habitat_search_radius_m"],
            threshold_m=p["connectivity_threshold_m"],
        )
        df = repo.rendimiento_dataframe(session, per_parcel)
        assert not df.empty, "El dataframe de rendimientos no debe estar vacio"
        assert len(df) == 540, f"Se esperaban 540 observaciones, se obtuvieron {len(df)}"

        # Ajuste de efectos mixtos
        res = fit_mixed_effects(df, include_crop=True)
        assert res["n_observaciones"] == 540
        assert "coeficientes" in res
        print(f"Stats report OK: n={res['n_observaciones']}, grupos={res['n_grupos']}, AIC={res['aic']:.2f}")
        for c in res["coeficientes"]:
            p_val = f"{c['p_value']:.4f}" if c['p_value'] is not None else "N/A"
            print(f"  {c['variable']:<30}: coef={c['coef']:.4f}, p={p_val}")
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    test_real_data_mixed_effects()
