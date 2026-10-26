"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Scatter,
  ScatterChart,
  ZAxis,
  Pie,
  PieChart,
  Cell,
} from "recharts";

const COLORS = ["#22c55e", "#38bdf8", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

interface RadarChartProps {
  data: any[];
  keys: string[];
  nameKey: string;
}

export function CustomRadarChart({ data, keys, nameKey }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis dataKey={nameKey} stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <PolarRadiusAxis angle={90} domain={[0, 1]} stroke="#94a3b8" />
        {keys.map((key, i) => (
          <Radar
            key={key}
            name={key}
            dataKey={key}
            stroke={COLORS[i % COLORS.length]}
            fill={COLORS[i % COLORS.length]}
            fillOpacity={0.3}
            strokeWidth={2}
          />
        ))}
        <Legend />
        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

interface AreaChartProps {
  data: any[];
  dataKey: string;
  name: string;
  color?: string;
}

export function CustomAreaChart({ data, dataKey, name, color = "#22c55e" }: AreaChartProps) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="anio" stroke="#94a3b8" />
        <YAxis stroke="#94a3b8" />
        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
        <Area type="monotone" dataKey={dataKey} name={name} stroke={color} fill={color} fillOpacity={0.4} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface ScatterChartProps {
  data: any[];
  xKey: string;
  yKey: string;
  sizeKey?: string;
}

export function CustomScatterChart({ data, xKey, yKey, sizeKey }: ScatterChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          type="number"
          dataKey={xKey}
          name="Área"
          unit=" ha"
          stroke="#94a3b8"
          label={{ value: "Área (ha)", position: "insideBottom", offset: -10, fill: "#94a3b8" }}
        />
        <YAxis
          type="number"
          dataKey={yKey}
          name="Productividad"
          unit=" t/ha"
          stroke="#94a3b8"
          label={{ value: "Productividad (t/ha)", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
        />
        {sizeKey && <ZAxis type="number" dataKey={sizeKey} range={[60, 300]} name="Área" />}
        <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
        <Legend />
        <Scatter name="Parcelas agrícolas" data={data} fill="#22c55e" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

interface PieChartProps {
  data: any[];
  dataKey: string;
  nameKey: string;
}

export function CustomPieChart({ data, dataKey, nameKey }: PieChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="48%"
          labelLine={true}
          label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
          outerRadius={85}
          fill="#8884d8"
          dataKey={dataKey}
          nameKey={nameKey}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Legend />
        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

interface HeatmapProps {
  data: any[][];
  xLabels: string[];
  yLabels: string[];
  title?: string;
}

export function Heatmap({ data, xLabels, yLabels, title }: HeatmapProps) {
  const maxValue = Math.max(...data.flat());
  const minValue = Math.min(...data.flat());
  const range = maxValue - minValue || 1;

  const getColor = (value: number) => {
    const normalized = (value - minValue) / range;
    const r = Math.floor(255 * normalized);
    const g = Math.floor(255 * (1 - normalized));
    return `rgb(${r}, ${g}, 100)`;
  };

  return (
    <div className="heatmap-container">
      {title && <h4 style={{ margin: "0 0 12px", fontSize: 13, color: "#94a3b8" }}>{title}</h4>}
      <div className="heatmap-grid">
        <div className="heatmap-corner"></div>
        {xLabels.map((label) => (
          <div key={label} className="heatmap-label-x">{label}</div>
        ))}
        {data.map((row, i) => (
          <div key={i} className="heatmap-row">
            <div className="heatmap-label-y">{yLabels[i]}</div>
            {row.map((value, j) => (
              <div
                key={`${i}-${j}`}
                className="heatmap-cell"
                style={{ backgroundColor: getColor(value) }}
                title={`${value.toFixed(2)}`}
              >
                {value.toFixed(1)}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
