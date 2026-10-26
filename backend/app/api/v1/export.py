"""Exportacion de resultados (CSV y PDF)."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.domain import models as M
from app.services import pipelines

router = APIRouter(prefix="/export", tags=["exportacion"])


@router.get("/resultados.csv", summary="CSV de resultados de simulacion persistidos")
def resultados_csv(session: SessionDep, escenario: str | None = None) -> Response:
    stmt = select(M.ResultadoSimulacion, M.Parcela.codigo, M.Escenario.codigo).join(
        M.Parcela, M.ResultadoSimulacion.parcela_id == M.Parcela.id
    ).join(M.Escenario, M.ResultadoSimulacion.escenario_id == M.Escenario.id)
    if escenario:
        stmt = stmt.where(M.Escenario.codigo == escenario)
    rows = session.execute(stmt).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["escenario", "parcela", "anio", "mes", "productividad_t_ha",
                     "produccion_total_t", "visitas", "riqueza", "deficit",
                     "score_ecosistema"])
    for r, pcode, ecode in rows:
        writer.writerow([ecode, pcode, r.anio, r.mes, r.productividad_t_ha,
                         r.produccion_total_t, r.visitas_polinizadores,
                         r.riqueza_polinizadores, r.deficit_polinizacion,
                         r.score_ecosistema])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados.csv"},
    )


@router.get("/recomendaciones.csv", summary="CSV de recomendaciones")
def recomendaciones_csv(session: SessionDep, escenario: str | None = None) -> Response:
    recs = pipelines.list_recommendations(session, escenario)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(recs[0].keys()) if recs else
                            ["id", "escenario", "parcela_id", "intervencion",
                             "area_ha", "costo_usd", "prioridad", "metodo"])
    writer.writeheader()
    writer.writerows(recs)
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recomendaciones.csv"},
    )


@router.get("/reporte.pdf", summary="Reporte PDF ejecutivo del sistema")
def reporte_pdf(session: SessionDep, escenario: str = Query("ssp585")) -> Response:
    from fpdf import FPDF

    eco = pipelines.ecosystem_report(session)["resumen"]
    sim = pipelines.simulation_report(session, escenario, persist=False)
    recs = pipelines.list_recommendations(session)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, settings.app_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "Region: Valle de Moche y Chavimochic (La Libertad, Peru)",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "1. Indicadores ecosistemicos (promedio)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for k, v in eco.items():
        pdf.cell(0, 6, f"  - {k}: {v:.3f}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"2. Simulacion escenario: {sim.get('nombre', escenario)}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    r = sim.get("resumen", {})
    pdf.cell(0, 6, f"  - Productividad inicial: {r.get('productividad_inicial', 0):.2f} t/ha",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Productividad final:   {r.get('productividad_final', 0):.2f} t/ha",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Cambio: {r.get('cambio_productividad_pct', 0):.1f} %",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Score final: {r.get('score_final', 0):.3f}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"3. Recomendaciones ({len(recs)})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if not recs:
        pdf.cell(0, 6, "  (Sin recomendaciones almacenadas; ejecute /optimizacion con persist=true)",
                 new_x="LMARGIN", new_y="NEXT")
    for rec in recs[:40]:
        pdf.multi_cell(0, 5, f"  - P{rec['parcela_id']} | {rec['intervencion']} | "
                             f"costo ${rec['costo_usd']:.0f} | prioridad {rec['prioridad']}",
                       new_x="LMARGIN", new_y="NEXT")
    return Response(
        content=bytes(pdf.output()), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte.pdf"},
    )
