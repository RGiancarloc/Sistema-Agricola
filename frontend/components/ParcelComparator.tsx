"use client";

import { useState } from "react";

interface ParcelData {
  id: string;
  codigo: string;
  cultivo: string;
  area_ha: number;
  productividad: number;
  polinizacion: number;
  biodiversidad: number;
  conectividad: number;
  ndvi: number;
  temperatura: number;
  precipitacion: number;
}

interface ParcelComparatorProps {
  parcelas: ParcelData[];
}

export default function ParcelComparator({ parcelas }: ParcelComparatorProps) {
  const [selected1, setSelected1] = useState<string>("");
  const [selected2, setSelected2] = useState<string>("");

  const p1 = parcelas.find((p) => p.id === selected1);
  const p2 = parcelas.find((p) => p.id === selected2);

  const metrics = [
    { key: "area_ha", label: "Área (ha)", unit: "" },
    { key: "productividad", label: "Productividad", unit: " t/ha" },
    { key: "polinizacion", label: "Polinización", unit: "" },
    { key: "biodiversidad", label: "Biodiversidad", unit: "" },
    { key: "conectividad", label: "Conectividad", unit: "" },
    { key: "ndvi", label: "NDVI", unit: "" },
    { key: "temperatura", label: "Temperatura", unit: " °C" },
    { key: "precipitacion", label: "Precipitación", unit: " mm" },
  ];

  const getDiffColor = (v1: number, v2: number) => {
    const diff = ((v2 - v1) / v1) * 100;
    if (diff > 5) return "#22c55e";
    if (diff < -5) return "#ef4444";
    return "#94a3b8";
  };

  const getDiffText = (v1: number, v2: number) => {
    const diff = ((v2 - v1) / v1) * 100;
    if (diff > 0) return `+${diff.toFixed(1)}%`;
    return `${diff.toFixed(1)}%`;
  };

  return (
    <div className="parcel-comparator">
      <h3 className="comparator-title">Comparador de Parcelas</h3>

      <div className="comparator-selectors">
        <div className="selector-group">
          <label>Parcela 1</label>
          <select
            className="control-select"
            value={selected1}
            onChange={(e) => setSelected1(e.target.value)}
          >
            <option value="">Seleccionar...</option>
            {parcelas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.codigo} - {p.cultivo}
              </option>
            ))}
          </select>
        </div>

        <div className="selector-group">
          <label>Parcela 2</label>
          <select
            className="control-select"
            value={selected2}
            onChange={(e) => setSelected2(e.target.value)}
          >
            <option value="">Seleccionar...</option>
            {parcelas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.codigo} - {p.cultivo}
              </option>
            ))}
          </select>
        </div>
      </div>

      {p1 && p2 && (
        <div className="comparator-results">
          <table className="comparator-table">
            <thead>
              <tr>
                <th>Métrica</th>
                <th>{p1.codigo}</th>
                <th>{p2.codigo}</th>
                <th>Diferencia</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => {
                const v1 = (p1 as any)[m.key] || 0;
                const v2 = (p2 as any)[m.key] || 0;
                return (
                  <tr key={m.key}>
                    <td>{m.label}</td>
                    <td>{v1.toFixed(2)}{m.unit}</td>
                    <td>{v2.toFixed(2)}{m.unit}</td>
                    <td style={{ color: getDiffColor(v1, v2) }}>
                      {getDiffText(v1, v2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="comparator-summary">
            <div className="summary-card">
              <h4>Mejor Productividad</h4>
              <div className="summary-value">
                {p1.productividad > p2.productividad ? p1.codigo : p2.codigo}
              </div>
              <div className="summary-sub">
                {Math.max(p1.productividad, p2.productividad).toFixed(2)} t/ha
              </div>
            </div>

            <div className="summary-card">
              <h4>Mejor Polinización</h4>
              <div className="summary-value">
                {p1.polinizacion > p2.polinizacion ? p1.codigo : p2.codigo}
              </div>
              <div className="summary-sub">
                {Math.max(p1.polinizacion, p2.polinizacion).toFixed(3)}
              </div>
            </div>

            <div className="summary-card">
              <h4>Mayor Biodiversidad</h4>
              <div className="summary-value">
                {p1.biodiversidad > p2.biodiversidad ? p1.codigo : p2.codigo}
              </div>
              <div className="summary-sub">
                {Math.max(p1.biodiversidad, p2.biodiversidad).toFixed(3)}
              </div>
            </div>

            <div className="summary-card">
              <h4>Mayor Conectividad</h4>
              <div className="summary-value">
                {p1.conectividad > p2.conectividad ? p1.codigo : p2.codigo}
              </div>
              <div className="summary-sub">
                {Math.max(p1.conectividad, p2.conectividad).toFixed(3)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
