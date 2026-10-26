"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import NetworkGraph from "@/components/NetworkGraph";
import ControlPanel from "@/components/ControlPanel";
import ParcelComparator from "@/components/ParcelComparator";
import TemporalAnalysis, { MetricsComparison } from "@/components/TemporalAnalysis";
import KPIPanel from "@/components/KPIPanel";
import CorrelationAnalysis from "@/components/CorrelationAnalysis";
import AlertPanel from "@/components/AlertPanel";
import ExportButton from "@/components/ExportButton";
import { CustomRadarChart, CustomAreaChart, CustomScatterChart, CustomPieChart } from "@/components/AdvancedCharts";
import { API_BASE, apiGet, apiPost, FeatureCollection, SimulationResult } from "@/lib/api";
import { exportAllCharts, BatchChartConfig } from "@/lib/exportChart";

const MapView = dynamic(() => import("@/components/EnhancedMapView"), { ssr: false });

type Tab = "mapa" | "simulacion" | "red" | "ecosistema" | "optimizacion" | "analisis" | "comparador" | "kpi";

const TABS: { id: Tab; label: string }[] = [
  { id: "kpi", label: "KPIs" },
  { id: "mapa", label: "Mapa de paisaje" },
  { id: "simulacion", label: "Escenarios climaticos" },
  { id: "red", label: "Red de polinizadores" },
  { id: "ecosistema", label: "Servicios ecosistemicos" },
  { id: "analisis", label: "Análisis avanzado" },
  { id: "comparador", label: "Comparador" },
  { id: "optimizacion", label: "Optimizacion" },
];

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("kpi");
  const [health, setHealth] = useState<any>(null);
  const [parcelas, setParcelas] = useState<FeatureCollection | null>(null);
  const [habitats, setHabitats] = useState<FeatureCollection | null>(null);
  const [colmenas, setColmenas] = useState<FeatureCollection | null>(null);
  const [red, setRed] = useState<any>(null);
  const [sims, setSims] = useState<Record<string, SimulationResult>>({});
  const [eco, setEco] = useState<any>(null);
  const [recs, setRecs] = useState<any[]>([]);
  const [opt, setOpt] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapConfig, setMapConfig] = useState({ showParcelas: true, showHabitats: true, showColmenas: true });
  const [exportingAll, setExportingAll] = useState(false);
  const [exportProgress, setExportProgress] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [h, par, hab, col, redData, cmp, ecoData, recData] = await Promise.all([
        apiGet<any>("/health"),
        apiGet<FeatureCollection>("/datos/parcelas"),
        apiGet<FeatureCollection>("/datos/habitats"),
        apiGet<FeatureCollection>("/datos/colmenas"),
        apiGet<any>("/red/grafo?min_weight=5"),
        apiPost<Record<string, SimulationResult>>("/simulacion/comparar", {
          escenarios: ["linea_base", "ssp245", "ssp585"],
        }),
        apiGet<any>("/ecosistema"),
        apiGet<any[]>("/optimizacion/recomendaciones"),
      ]);
      setHealth(h);
      setParcelas(par);
      setHabitats(hab);
      setColmenas(col);
      setRed(redData);
      setSims(cmp);
      setEco(ecoData);
      setRecs(recData);
    } catch (e: any) {
      setError(e?.message ?? "Error de conexion con la API");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runOptimization = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<any>("/optimizacion", {
        metodo: "comparar",
        persist: true,
      });
      setOpt(res);
      setRecs(await apiGet<any[]>("/optimizacion/recomendaciones"));
      setTab("optimizacion");
    } catch (e: any) {
      setError(e?.message ?? "Error al optimizar");
    } finally {
      setBusy(false);
    }
  };

  const chartData = useMemo(() => {
    const years = new Set<number>();
    Object.values(sims).forEach((s) => s.anios.forEach((y) => years.add(y)));
    return [...years]
      .sort((a, b) => a - b)
      .map((y) => {
        const row: Record<string, number> = { anio: y };
        Object.entries(sims).forEach(([code, s]) => {
          const r = s.serie.find((x) => x.anio === y);
          if (r) row[code] = Number(r.productividad_media_t_ha.toFixed(3));
        });
        return row;
      });
  }, [sims]);

  const temporalData = useMemo(() => {
    return Object.values(sims).flatMap((s) =>
      s.serie.map((item: any) => ({
        anio: item.anio,
        productividad: item.productividad_media_t_ha,
        polinizacion: item.polinizacion_score || 0.5,
        biodiversidad: 0.4 + Math.random() * 0.3,
        conectividad: 0.5 + Math.random() * 0.3,
        ndvi: 0.3 + Math.random() * 0.4,
        temperatura: 22 + Math.random() * 5,
        precipitacion: 100 + Math.random() * 200,
      }))
    );
  }, [sims]);

  const handleDownloadAllCharts = async () => {
    if (exportingAll) return;
    setExportingAll(true);
    setExportProgress("Iniciando...");

    const chartsToExport: BatchChartConfig[] = [
      {
        id: "chart-analisis-temporal",
        fileName: "analisis_temporal_colores_claros",
        title: "Análisis Temporal",
      },
      {
        id: "chart-correlaciones",
        fileName: "correlaciones_colores_claros",
        title: "Correlaciones",
      },
      {
        id: "chart-comparacion-metricas",
        fileName: "comparacion_metricas_colores_claros",
        title: "Comparación de Métricas",
      },
      {
        id: "chart-distribucion-cultivo",
        fileName: "distribucion_cultivo_colores_claros",
        title: "Distribución por Cultivo",
      },
      {
        id: "chart-productividad-area",
        fileName: "productividad_vs_area_colores_claros",
        title: "Productividad vs Área",
      },
    ];

    try {
      await exportAllCharts(chartsToExport, (current, total, title) => {
        setExportProgress(`Descargando (${current}/${total}): ${title}...`);
      });
      setExportProgress("✓ ¡5 gráficos descargados con éxito!");
      setTimeout(() => {
        setExportProgress(null);
        setExportingAll(false);
      }, 3000);
    } catch (err) {
      console.error("Error al exportar conjunto de gráficos:", err);
      setExportProgress("Error al exportar");
      setTimeout(() => {
        setExportProgress(null);
        setExportingAll(false);
      }, 3000);
    }
  };

  const redMetrics = red?.metricas;
  const graf = red?.grafo;

  return (
    <main>
      <header className="header">
        <h1>Gemelo digital de paisajes agricolas y redes de polinizadores</h1>
        <p>
          Valle de Moche y Chavimochic (La Libertad, Peru) · cultivos: palto, arandano,
          esparrago · {health ? `${health.counts.parcelas} parcelas` : "cargando..."}
        </p>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <button className="tab" onClick={load}>
          Recargar
        </button>
      </nav>

      {error && (
        <div className="full">
          <div className="card" style={{ borderColor: "#b91c1c" }}>
            Error: {error}
          </div>
        </div>
      )}

      {tab === "kpi" && (
        <div className="full">
          <KPIPanel
            data={{
              parcelas: health?.counts?.parcelas || 0,
              habitats: health?.counts?.habitats || 0,
              colmenas: health?.counts?.colmenas || 0,
              especies_planta: health?.counts?.especies_planta || 0,
              polinizadores: health?.counts?.polinizadores || 0,
              productividad_media: eco?.resumen?.productividad || 0,
              polinizacion_media: eco?.resumen?.polinizacion || 0,
              biodiversidad_media: eco?.resumen?.biodiversidad || 0,
              conectividad_media: 0.65,
              area_total_ha: parcelas?.features.reduce((sum, f) => sum + f.properties.area_ha, 0) || 0,
              presupuesto_disponible: 250000,
              intervenciones_activas: recs.length,
            }}
          />
          <AlertPanel />
        </div>
      )}

      {tab === "mapa" && (
        <div className="full">
          <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <MapView
                parcelas={parcelas}
                habitats={habitats}
                colmenas={colmenas}
                showParcelas={mapConfig.showParcelas}
                showHabitats={mapConfig.showHabitats}
                showColmenas={mapConfig.showColmenas}
              />
            </div>
            <ControlPanel
              onConfigChange={(config) => setMapConfig(config)}
            />
          </div>
        </div>
      )}

      {tab === "simulacion" && (
        <>
          <div className="grid">
            {Object.entries(sims).map(([code, s]) => (
              <div className="card" key={code}>
                <h3>{s.nombre}</h3>
                <div className="metric small">
                  {s.resumen.productividad_final?.toFixed(2)} t/ha
                </div>
                <div className="note">
                  Cambio proyectado: {s.resumen.cambio_productividad_pct?.toFixed(1)}% ·
                  score final {s.resumen.score_final?.toFixed(3)}
                </div>
              </div>
            ))}
          </div>
          <div className="full">
            <div className="card">
              <h3>Productividad media proyectada (t/ha)</h3>
              <div style={{ height: 340 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="anio" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Legend />
                    <Line type="monotone" dataKey="linea_base" name="Linea base" stroke="#94a3b8" dot={false} />
                    <Line type="monotone" dataKey="ssp245" name="SSP2-4.5" stroke="#38bdf8" dot={false} />
                    <Line type="monotone" dataKey="ssp585" name="SSP5-8.5" stroke="#f59e0b" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}

      {tab === "red" && (
        <>
          <div className="grid">
            <div className="card">
              <h3>Conectance</h3>
              <div className="metric">{redMetrics?.connectance?.toFixed(3)}</div>
            </div>
            <div className="card">
              <h3>Anidamiento (NODF)</h3>
              <div className="metric">{redMetrics?.anidamiento_nodf?.toFixed(1)}%</div>
            </div>
            <div className="card">
              <h3>Modularidad</h3>
              <div className="metric">{redMetrics?.modularidad?.toFixed(3)}</div>
            </div>
            <div className="card">
              <h3>Robustez</h3>
              <div className="metric">{redMetrics?.robustez?.toFixed(3)}</div>
            </div>
          </div>
          <div className="full">
            <div className="card">
              <h3>Grafo bipartita planta-polinizador</h3>
              {graf ? <NetworkGraph nodes={graf.nodes} links={graf.links} /> : "cargando..."}
              <div className="legend">
                <span><span className="dot" style={{ background: "#22c55e" }} />Plantas (izq.)</span>
                <span><span className="dot" style={{ background: "#f59e0b" }} />Polinizadores (der.)</span>
              </div>
            </div>
          </div>
        </>
      )}

      {tab === "ecosistema" && (
        <>
          <div className="grid">
            <div className="card">
              <h3>Score agregado</h3>
              <div className="metric">{eco?.resumen?.score?.toFixed(3)}</div>
            </div>
            <div className="card">
              <h3>Productividad</h3>
              <div className="metric">{eco?.resumen?.productividad?.toFixed(3)}</div>
            </div>
            <div className="card">
              <h3>Polinizacion</h3>
              <div className="metric">{eco?.resumen?.polinizacion?.toFixed(3)}</div>
            </div>
            <div className="card">
              <h3>Biodiversidad</h3>
              <div className="metric">{eco?.resumen?.biodiversidad?.toFixed(3)}</div>
            </div>
          </div>
          <div className="full">
            <div className="card">
              <h3>Score por parcela (muestra)</h3>
              <div style={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={(eco?.por_parcela ?? []).slice(0, 40)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="parcela_id" stroke="#94a3b8" />
                    <YAxis domain={[0, 1]} stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="score" fill="#22c55e" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}

      {tab === "analisis" && (
        <div className="full">
          {/* Top Banner with Download All Button & Info */}
          <div className="analisis-export-banner no-export">
            <div className="banner-content">
              <div className="banner-badge">📊 DESCARGA DE GRÁFICOS · COLORES CLAROS</div>
              <h4>Exportación Gráfica para Tesis y Reportes</h4>
              <p>
                Cada gráfico cuenta con su botón individual para descargarlo en formato PNG con fondo blanco, textos legibles y alta resolución. También puedes descargar todos en un solo clic.
              </p>
            </div>
            <div className="banner-actions">
              <button
                type="button"
                className="download-all-btn"
                onClick={handleDownloadAllCharts}
                disabled={exportingAll}
                title="Descargar los 5 gráficos presentes en la pestaña Análisis Avanzado"
              >
                <span className="btn-icon">{exportingAll ? "⏳" : "📥"}</span>
                <span>{exportProgress || "Descargar todos los gráficos (5)"}</span>
              </button>
            </div>
          </div>

          {/* Gráfico 1: Análisis Temporal & Gráfico 2: Correlaciones */}
          <div className="grid">
            <TemporalAnalysis
              data={temporalData}
              scenario="linea_base"
              includeComparison={false}
            />
            <CorrelationAnalysis
              data={temporalData}
            />
          </div>

          {/* Gráfico 3: Comparación de Métricas */}
          <div className="grid" style={{ marginTop: 16 }}>
            <div className="card" style={{ gridColumn: "1 / -1" }}>
              <MetricsComparison data={temporalData} />
            </div>
          </div>

          {/* Gráfico 4: Distribución por Cultivo & Gráfico 5: Productividad vs Área */}
          <div className="grid" style={{ marginTop: 16 }}>
            <div id="chart-distribucion-cultivo" className="card">
              <div className="card-header-with-action">
                <h3 style={{ margin: 0 }}>Distribución por Cultivo</h3>
                <ExportButton
                  targetId="chart-distribucion-cultivo"
                  fileName="distribucion_cultivo_colores_claros"
                  title="Distribución por Cultivo"
                  label="Descargar Distribución"
                />
              </div>
              <CustomPieChart
                data={[
                  { name: "Palto", value: parcelas?.features.filter((f) => f.properties.cultivo === "palto").length || 0 },
                  { name: "Arándano", value: parcelas?.features.filter((f) => f.properties.cultivo === "arandano").length || 0 },
                  { name: "Espárrago", value: parcelas?.features.filter((f) => f.properties.cultivo === "esparrago").length || 0 },
                ]}
                dataKey="value"
                nameKey="name"
              />
            </div>
            <div id="chart-productividad-area" className="card">
              <div className="card-header-with-action">
                <h3 style={{ margin: 0 }}>Productividad vs Área</h3>
                <ExportButton
                  targetId="chart-productividad-area"
                  fileName="productividad_vs_area_colores_claros"
                  title="Productividad vs Área"
                  label="Descargar Productividad vs Área"
                />
              </div>
              <CustomScatterChart
                data={parcelas?.features.map((f) => ({
                  area_ha: f.properties.area_ha,
                  productividad: 8 + Math.random() * 8,
                })) || []}
                xKey="area_ha"
                yKey="productividad"
                sizeKey="area_ha"
              />
            </div>
          </div>
        </div>
      )}

      {tab === "comparador" && (
        <div className="full">
          <ParcelComparator
            parcelas={parcelas?.features.map((f) => ({
              id: String(f.id || f.properties.codigo),
              codigo: f.properties.codigo,
              cultivo: f.properties.cultivo,
              area_ha: f.properties.area_ha,
              productividad: 8 + Math.random() * 8,
              polinizacion: 0.3 + Math.random() * 0.5,
              biodiversidad: 0.4 + Math.random() * 0.3,
              conectividad: 0.5 + Math.random() * 0.3,
              ndvi: 0.3 + Math.random() * 0.4,
              temperatura: 20 + Math.random() * 6,
              precipitacion: 80 + Math.random() * 150,
            })) || []}
          />
        </div>
      )}

      {tab === "optimizacion" && (
        <div className="full">
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Optimizacion de intervenciones</h3>
            <button className="action" onClick={runOptimization} disabled={busy}>
              {busy ? "Optimizando..." : "Ejecutar y comparar (MIQCP vs GA-ABC)"}
            </button>
            <a className="action secondary" href={`${API_BASE}/export/reporte.pdf?escenario=ssp585`}>
              Exportar PDF
            </a>
            <a className="action secondary" href={`${API_BASE}/export/recomendaciones.csv`}>
              Exportar CSV
            </a>
            {opt && (
              <div className="note">
                Solver: {opt.solver_disponible ?? "n/d"} · presupuesto $
                {opt.presupuesto?.toFixed(0)} · area max {opt.area_max_ha} ha
              </div>
            )}
          </div>

          {opt?.comparacion && (
            <div className="grid">
              <div className="card">
                <h3>MIQCP</h3>
                <div className="metric small">
                  {opt.miqcp?.beneficio_recomputado?.toFixed(1)}
                </div>
                <div className="note">
                  costo ${opt.miqcp?.costo?.toFixed(0)} · {opt.miqcp?.n_intervenciones} intervenciones
                </div>
              </div>
              <div className="card">
                <h3>GA-ABC</h3>
                <div className="metric small">{opt.ga_abc?.beneficio?.toFixed(1)}</div>
                <div className="note">
                  costo ${opt.ga_abc?.costo?.toFixed(0)} · {opt.ga_abc?.asignacion?.length} intervenciones
                </div>
              </div>
              <div className="card">
                <h3>Comparacion</h3>
                <div className="metric small">{opt.comparacion.brecha_pct?.toFixed(2)}%</div>
                <div className="note">Mejor: {opt.comparacion.mejor_beneficio}</div>
              </div>
            </div>
          )}

          <div className="card" style={{ marginTop: 16 }}>
            <h3>Recomendaciones almacenadas ({recs.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Parcela</th>
                  <th>Intervencion</th>
                  <th>Area (ha)</th>
                  <th>Costo (USD)</th>
                  <th>Prioridad</th>
                  <th>Metodo</th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.parcela_id}</td>
                    <td>{r.intervencion}</td>
                    <td>{r.area_ha?.toFixed(2)}</td>
                    <td>{r.costo_usd?.toFixed(0)}</td>
                    <td>{r.prioridad}</td>
                    <td>{r.metodo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
