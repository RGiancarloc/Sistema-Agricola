"use client";

import { useState } from "react";

interface ControlPanelProps {
  onFilterChange?: (filters: any) => void;
  onConfigChange?: (config: any) => void;
}

export default function ControlPanel({ onFilterChange, onConfigChange }: ControlPanelProps) {
  const [filters, setFilters] = useState({
    cultivo: "todos",
    areaMin: 0,
    areaMax: 100,
    yearStart: 2015,
    yearEnd: 2050,
    escenario: "linea_base",
  });

  const [config, setConfig] = useState({
    showHabitats: true,
    showColmenas: true,
    showParcelas: true,
    animationSpeed: "normal",
    theme: "dark",
  });

  const handleFilterChange = (key: string, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  const handleConfigChange = (key: string, value: any) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    onConfigChange?.(newConfig);
  };

  return (
    <div className="control-panel">
      <h3 className="control-panel-title">Panel de Control</h3>

      <div className="control-section">
        <h4>Filtros de Cultivo</h4>
        <select
          className="control-select"
          value={filters.cultivo}
          onChange={(e) => handleFilterChange("cultivo", e.target.value)}
        >
          <option value="todos">Todos los cultivos</option>
          <option value="palto">Palto</option>
          <option value="arandano">Arándano</option>
          <option value="esparrago">Espárrago</option>
        </select>
      </div>

      <div className="control-section">
        <h4>Área (ha)</h4>
        <div className="control-range">
          <input
            type="number"
            className="control-input"
            placeholder="Mín"
            value={filters.areaMin}
            onChange={(e) => handleFilterChange("areaMin", parseFloat(e.target.value) || 0)}
          />
          <span>-</span>
          <input
            type="number"
            className="control-input"
            placeholder="Máx"
            value={filters.areaMax}
            onChange={(e) => handleFilterChange("areaMax", parseFloat(e.target.value) || 100)}
          />
        </div>
      </div>

      <div className="control-section">
        <h4>Rango Temporal</h4>
        <div className="control-range">
          <input
            type="number"
            className="control-input"
            value={filters.yearStart}
            onChange={(e) => handleFilterChange("yearStart", parseInt(e.target.value))}
          />
          <span>-</span>
          <input
            type="number"
            className="control-input"
            value={filters.yearEnd}
            onChange={(e) => handleFilterChange("yearEnd", parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="control-section">
        <h4>Escenario Climático</h4>
        <select
          className="control-select"
          value={filters.escenario}
          onChange={(e) => handleFilterChange("escenario", e.target.value)}
        >
          <option value="linea_base">Línea base</option>
          <option value="ssp245">SSP2-4.5 (Mitigación)</option>
          <option value="ssp585">SSP5-8.5 (Alto)</option>
        </select>
      </div>

      <div className="control-section">
        <h4>Capas del Mapa</h4>
        <label className="control-checkbox">
          <input
            type="checkbox"
            checked={config.showParcelas}
            onChange={(e) => handleConfigChange("showParcelas", e.target.checked)}
          />
          <span>Parcelas</span>
        </label>
        <label className="control-checkbox">
          <input
            type="checkbox"
            checked={config.showHabitats}
            onChange={(e) => handleConfigChange("showHabitats", e.target.checked)}
          />
          <span>Hábitats</span>
        </label>
        <label className="control-checkbox">
          <input
            type="checkbox"
            checked={config.showColmenas}
            onChange={(e) => handleConfigChange("showColmenas", e.target.checked)}
          />
          <span>Colmenas</span>
        </label>
      </div>

      <div className="control-section">
        <h4>Velocidad de Animación</h4>
        <select
          className="control-select"
          value={config.animationSpeed}
          onChange={(e) => handleConfigChange("animationSpeed", e.target.value)}
        >
          <option value="slow">Lenta</option>
          <option value="normal">Normal</option>
          <option value="fast">Rápida</option>
        </select>
      </div>

      <button className="control-button" onClick={() => {
        setFilters({ cultivo: "todos", areaMin: 0, areaMax: 100, yearStart: 2015, yearEnd: 2050, escenario: "linea_base" });
        setConfig({ showHabitats: true, showColmenas: true, showParcelas: true, animationSpeed: "normal", theme: "dark" });
        onFilterChange?.({ cultivo: "todos", areaMin: 0, areaMax: 100, yearStart: 2015, yearEnd: 2050, escenario: "linea_base" });
        onConfigChange?.({ showHabitats: true, showColmenas: true, showParcelas: true, animationSpeed: "normal", theme: "dark" });
      }}>
        Restablecer Filtros
      </button>
    </div>
  );
}
