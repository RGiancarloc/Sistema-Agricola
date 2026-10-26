"use client";

import { useMemo } from "react";

import ExportButton from "@/components/ExportButton";

interface CorrelationAnalysisProps {
  data: Array<{
    productividad: number;
    polinizacion: number;
    biodiversidad: number;
    conectividad: number;
    ndvi: number;
    temperatura: number;
    precipitacion: number;
  }>;
}

export default function CorrelationAnalysis({ data }: CorrelationAnalysisProps) {
  const correlationMatrix = useMemo(() => {
    const variables = [
      "productividad",
      "polinizacion",
      "biodiversidad",
      "conectividad",
      "ndvi",
      "temperatura",
      "precipitacion",
    ];

    const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const std = (arr: number[]) => {
      const m = mean(arr);
      return Math.sqrt(arr.reduce((sum, val) => sum + Math.pow(val - m, 2), 0) / arr.length);
    };

    const correlation = (x: number[], y: number[]) => {
      const mx = mean(x);
      const my = mean(y);
      const sx = std(x);
      const sy = std(y);
      if (sx === 0 || sy === 0) return 0;
      const covariance = x.reduce((sum, xi, i) => sum + (xi - mx) * (y[i] - my), 0) / x.length;
      return covariance / (sx * sy);
    };

    const matrix: number[][] = [];
    for (let i = 0; i < variables.length; i++) {
      const row: number[] = [];
      for (let j = 0; j < variables.length; j++) {
        const x = data.map((d) => (d as any)[variables[i]]);
        const y = data.map((d) => (d as any)[variables[j]]);
        row.push(correlation(x, y));
      }
      matrix.push(row);
    }

    return { matrix, variables };
  }, [data]);

  const getColor = (value: number) => {
    const abs = Math.abs(value);
    if (value > 0) {
      const intensity = Math.floor(abs * 255);
      return `rgba(34, 197, 94, ${0.2 + abs * 0.8})`;
    } else {
      const intensity = Math.floor(abs * 255);
      return `rgba(239, 68, 68, ${0.2 + abs * 0.8})`;
    }
  };

  const getTextColor = (value: number) => {
    return Math.abs(value) > 0.5 ? "#fff" : "#e2e8f0";
  };

  const insights = useMemo(() => {
    const insights: string[] = [];
    const { matrix, variables } = correlationMatrix;

    const strongCorrelations: { var1: string; var2: string; value: number }[] = [];
    for (let i = 0; i < variables.length; i++) {
      for (let j = i + 1; j < variables.length; j++) {
        const value = matrix[i][j];
        if (Math.abs(value) > 0.5) {
          strongCorrelations.push({
            var1: variables[i],
            var2: variables[j],
            value,
          });
        }
      }
    }

    strongCorrelations.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    strongCorrelations.slice(0, 5).forEach((c) => {
      const direction = c.value > 0 ? "positiva" : "negativa";
      const strength = Math.abs(c.value) > 0.7 ? "fuerte" : "moderada";
      insights.push(
        `Correlación ${strength} ${direction} entre ${c.var1} y ${c.var2} (${c.value.toFixed(2)})`
      );
    });

    return insights;
  }, [correlationMatrix]);

  return (
    <div id="chart-correlaciones" className="correlation-analysis">
      <div className="card-header-with-action">
        <h3 className="correlation-title" style={{ margin: 0 }}>Análisis de Correlación</h3>
        <ExportButton
          targetId="chart-correlaciones"
          fileName="correlaciones_colores_claros"
          title="Correlaciones"
          label="Descargar Correlaciones"
        />
      </div>

      <div className="correlation-matrix">
        <table className="correlation-table">
          <thead>
            <tr>
              <th></th>
              {correlationMatrix.variables.map((v) => (
                <th key={v} className="rotated-header">
                  <span>{v}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {correlationMatrix.matrix.map((row, i) => (
              <tr key={i}>
                <td className="row-header">{correlationMatrix.variables[i]}</td>
                {row.map((value, j) => (
                  <td
                    key={j}
                    className={`corr-cell ${Math.abs(value) > 0.6 ? "corr-cell-high" : "corr-cell-low"}`}
                    style={{
                      backgroundColor: getColor(value),
                      color: getTextColor(value),
                      fontWeight: Math.abs(value) > 0.5 ? "bold" : "normal",
                    }}
                  >
                    {value.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="correlation-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ background: "rgba(239, 68, 68, 0.8)" }}></div>
          <span>Correlación negativa fuerte</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: "rgba(239, 68, 68, 0.4)" }}></div>
          <span>Correlación negativa moderada</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: "rgba(34, 197, 94, 0.4)" }}></div>
          <span>Correlación positiva moderada</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: "rgba(34, 197, 94, 0.8)" }}></div>
          <span>Correlación positiva fuerte</span>
        </div>
      </div>

      <div className="correlation-insights">
        <h4>Insights Principales</h4>
        <ul>
          {insights.map((insight, index) => (
            <li key={index}>{insight}</li>
          ))}
          {insights.length === 0 && <li>No se encontraron correlaciones fuertes</li>}
        </ul>
      </div>
    </div>
  );
}
