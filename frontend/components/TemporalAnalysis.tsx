"use client";

import { useState, useMemo } from "react";
import {
  Line,
  LineChart,
  Bar,
  BarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import ExportButton from "@/components/ExportButton";

export interface TemporalData {
  anio: number;
  mes?: number;
  productividad: number;
  polinizacion: number;
  temperatura: number;
  precipitacion: number;
  ndvi: number;
  biodiversidad: number;
  conectividad?: number;
}

export interface TemporalAnalysisProps {
  data: TemporalData[];
  scenario?: string;
  includeComparison?: boolean;
}

export const METRICS_CONFIG = [
  { key: "productividad", label: "Productividad (t/ha)", color: "#22c55e" },
  { key: "polinizacion", label: "Polinización", color: "#38bdf8" },
  { key: "temperatura", label: "Temperatura (°C)", color: "#f59e0b" },
  { key: "precipitacion", label: "Precipitación (mm)", color: "#8b5cf6" },
  { key: "ndvi", label: "NDVI", color: "#ec4899" },
  { key: "biodiversidad", label: "Biodiversidad", color: "#14b8a6" },
];

export default function TemporalAnalysis({
  data,
  scenario = "linea_base",
  includeComparison = false,
}: TemporalAnalysisProps) {
  const [viewMode, setViewMode] = useState<"yearly" | "monthly">("yearly");
  const [selectedMetric, setSelectedMetric] = useState<string>("productividad");

  const yearlyData = useMemo(() => {
    const yearMap = new Map<number, any>();
    data.forEach((d) => {
      const year = d.anio;
      const existing = yearMap.get(year) || {
        anio: year,
        productividad: 0,
        polinizacion: 0,
        temperatura: 0,
        precipitacion: 0,
        ndvi: 0,
        biodiversidad: 0,
        count: 0,
      };
      existing.productividad += d.productividad;
      existing.polinizacion += d.polinizacion;
      existing.temperatura += d.temperatura;
      existing.precipitacion += d.precipitacion;
      existing.ndvi += d.ndvi;
      existing.biodiversidad += d.biodiversidad;
      existing.count = (existing.count || 0) + 1;
      yearMap.set(year, existing);
    });

    return Array.from(yearMap.values())
      .map((d: any) => ({
        anio: d.anio,
        productividad: d.productividad / (d.count || 1),
        polinizacion: d.polinizacion / (d.count || 1),
        temperatura: d.temperatura / (d.count || 1),
        precipitacion: d.precipitacion / (d.count || 1),
        ndvi: d.ndvi / (d.count || 1),
        biodiversidad: d.biodiversidad / (d.count || 1),
      }))
      .sort((a, b) => a.anio - b.anio);
  }, [data]);

  const monthlyData = useMemo(() => {
    return data
      .filter((d) => d.mes !== undefined)
      .sort((a, b) => {
        if (a.anio !== b.anio) return a.anio - b.anio;
        return (a.mes || 0) - (b.mes || 0);
      }) as any[];
  }, [data]);

  const currentData = viewMode === "yearly" ? yearlyData : monthlyData;
  const selectedMetricConfig =
    METRICS_CONFIG.find((m) => m.key === selectedMetric) || METRICS_CONFIG[0];

  const trend = useMemo(() => {
    if (currentData.length < 2) return { slope: 0, direction: "stable" };
    const first = currentData[0][selectedMetric as keyof TemporalData] as number;
    const last = currentData[currentData.length - 1][
      selectedMetric as keyof TemporalData
    ] as number;
    const slope = ((last - first) / (first || 1)) * 100;
    return {
      slope,
      direction: slope > 2 ? "increasing" : slope < -2 ? "decreasing" : "stable",
    };
  }, [currentData, selectedMetric]);

  const stats = useMemo(() => {
    const values = currentData.map(
      (d) => d[selectedMetric as keyof TemporalData] as number
    );
    if (!values.length) return { avg: 0, max: 0, min: 0, std: 0 };
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const max = Math.max(...values);
    const min = Math.min(...values);
    const std = Math.sqrt(
      values.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / values.length
    );
    return { avg, max, min, std };
  }, [currentData, selectedMetric]);

  return (
    <div id="chart-analisis-temporal" className="temporal-analysis">
      <div className="card-header-with-action">
        <div className="temporal-header-left">
          <h3 className="temporal-title" style={{ margin: 0 }}>
            Análisis Temporal - {scenario}
          </h3>
          <div className="temporal-controls no-export" style={{ marginLeft: 12 }}>
            <button
              type="button"
              className={`temporal-btn ${viewMode === "yearly" ? "active" : ""}`}
              onClick={() => setViewMode("yearly")}
            >
              Anual
            </button>
            <button
              type="button"
              className={`temporal-btn ${viewMode === "monthly" ? "active" : ""}`}
              onClick={() => setViewMode("monthly")}
            >
              Mensual
            </button>
          </div>
        </div>
        <ExportButton
          targetId="chart-analisis-temporal"
          fileName="analisis_temporal_colores_claros"
          title="Análisis Temporal"
          label="Descargar Análisis Temporal"
        />
      </div>

      <div className="temporal-metrics">
        <div className="metric-card">
          <h4>Promedio</h4>
          <div className="metric-value">{stats.avg.toFixed(2)}</div>
        </div>
        <div className="metric-card">
          <h4>Máximo</h4>
          <div className="metric-value">{stats.max.toFixed(2)}</div>
        </div>
        <div className="metric-card">
          <h4>Mínimo</h4>
          <div className="metric-value">{stats.min.toFixed(2)}</div>
        </div>
        <div className="metric-card">
          <h4>Desviación</h4>
          <div className="metric-value">{stats.std.toFixed(2)}</div>
        </div>
        <div className="metric-card">
          <h4>Tendencia</h4>
          <div className={`metric-value ${trend.direction}`}>
            {trend.slope > 0 ? "+" : ""}
            {trend.slope.toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="temporal-metric-selector">
        <label>Métrica Seleccionada:</label>
        <select
          className="control-select"
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
        >
          {METRICS_CONFIG.map((m) => (
            <option key={m.key} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="temporal-chart">
        <ResponsiveContainer width="100%" height={340}>
          <AreaChart data={currentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey={viewMode === "yearly" ? "anio" : "mes"}
              stroke="#94a3b8"
              tickFormatter={(v) => (viewMode === "yearly" ? v : `M${v}`)}
            />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Area
              type="monotone"
              dataKey={selectedMetric}
              name={selectedMetricConfig.label}
              stroke={selectedMetricConfig.color}
              fill={selectedMetricConfig.color}
              fillOpacity={0.4}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {includeComparison && (
        <MetricsComparison data={data} viewMode={viewMode} />
      )}
    </div>
  );
}

export function MetricsComparison({
  data,
  viewMode = "yearly",
}: {
  data: TemporalData[];
  viewMode?: "yearly" | "monthly";
}) {
  const yearlyData = useMemo(() => {
    const yearMap = new Map<number, any>();
    data.forEach((d) => {
      const year = d.anio;
      const existing = yearMap.get(year) || {
        anio: year,
        productividad: 0,
        polinizacion: 0,
        temperatura: 0,
        precipitacion: 0,
        ndvi: 0,
        biodiversidad: 0,
        count: 0,
      };
      existing.productividad += d.productividad;
      existing.polinizacion += d.polinizacion;
      existing.temperatura += d.temperatura;
      existing.precipitacion += d.precipitacion;
      existing.ndvi += d.ndvi;
      existing.biodiversidad += d.biodiversidad;
      existing.count = (existing.count || 0) + 1;
      yearMap.set(year, existing);
    });

    return Array.from(yearMap.values())
      .map((d: any) => ({
        anio: d.anio,
        productividad: d.productividad / (d.count || 1),
        polinizacion: d.polinizacion / (d.count || 1),
        temperatura: d.temperatura / (d.count || 1),
        precipitacion: d.precipitacion / (d.count || 1),
        ndvi: d.ndvi / (d.count || 1),
        biodiversidad: d.biodiversidad / (d.count || 1),
      }))
      .sort((a, b) => a.anio - b.anio);
  }, [data]);

  const currentData = yearlyData;

  return (
    <div id="chart-comparacion-metricas" className="temporal-comparison-container">
      <div className="card-header-with-action">
        <h3 style={{ margin: 0 }}>Comparación de Métricas</h3>
        <ExportButton
          targetId="chart-comparacion-metricas"
          fileName="comparacion_metricas_colores_claros"
          title="Comparación de Métricas"
          label="Descargar Comparación de Métricas"
        />
      </div>
      <div style={{ height: 280, marginTop: 12 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={currentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="anio"
              stroke="#94a3b8"
              tickFormatter={(v) => `${v}`}
            />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            {METRICS_CONFIG.slice(0, 4).map((m) => (
              <Line
                key={m.key}
                type="monotone"
                dataKey={m.key}
                name={m.label}
                stroke={m.color}
                dot={{ r: 3 }}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
