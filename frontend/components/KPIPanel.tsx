"use client";

interface KPIPanelProps {
  data: {
    parcelas: number;
    habitats: number;
    colmenas: number;
    especies_planta: number;
    polinizadores: number;
    productividad_media: number;
    polinizacion_media: number;
    biodiversidad_media: number;
    conectividad_media: number;
    area_total_ha: number;
    presupuesto_disponible: number;
    intervenciones_activas: number;
  };
}

export default function KPIPanel({ data }: KPIPanelProps) {
  const kpis = [
    {
      title: "Parcelas Activas",
      value: data.parcelas,
      unit: "",
      icon: "🌾",
      color: "#22c55e",
      trend: "+2.5%",
      trendUp: true,
    },
    {
      title: "Área Total",
      value: data.area_total_ha,
      unit: "ha",
      icon: "📐",
      color: "#38bdf8",
      trend: "+1.2%",
      trendUp: true,
    },
    {
      title: "Hábitats",
      value: data.habitats,
      unit: "",
      icon: "🌿",
      color: "#16a34a",
      trend: "+5.0%",
      trendUp: true,
    },
    {
      title: "Colmenas",
      value: data.colmenas,
      unit: "",
      icon: "🐝",
      color: "#facc15",
      trend: "+3.8%",
      trendUp: true,
    },
    {
      title: "Productividad Media",
      value: data.productividad_media,
      unit: "t/ha",
      icon: "📈",
      color: "#8b5cf6",
      trend: "+4.2%",
      trendUp: true,
    },
    {
      title: "Polinización",
      value: data.polinizacion_media,
      unit: "",
      icon: "🌸",
      color: "#ec4899",
      trend: "+1.8%",
      trendUp: true,
    },
    {
      title: "Biodiversidad",
      value: data.biodiversidad_media,
      unit: "",
      icon: "🦋",
      color: "#14b8a6",
      trend: "+2.1%",
      trendUp: true,
    },
    {
      title: "Conectividad",
      value: data.conectividad_media,
      unit: "",
      icon: "🔗",
      color: "#f59e0b",
      trend: "+0.9%",
      trendUp: true,
    },
    {
      title: "Especies Planta",
      value: data.especies_planta,
      unit: "",
      icon: "🌱",
      color: "#22c55e",
      trend: "+1.5%",
      trendUp: true,
    },
    {
      title: "Polinizadores",
      value: data.polinizadores,
      unit: "",
      icon: "🦗",
      color: "#f59e0b",
      trend: "+3.2%",
      trendUp: true,
    },
    {
      title: "Presupuesto",
      value: data.presupuesto_disponible,
      unit: "USD",
      icon: "💰",
      color: "#22c55e",
      trend: "-12.5%",
      trendUp: false,
    },
    {
      title: "Intervenciones",
      value: data.intervenciones_activas,
      unit: "",
      icon: "⚙️",
      color: "#38bdf8",
      trend: "+8.7%",
      trendUp: true,
    },
  ];

  return (
    <div className="kpi-panel">
      <h3 className="kpi-title">Indicadores Clave de Rendimiento</h3>
      <div className="kpi-grid">
        {kpis.map((kpi, index) => (
          <div key={index} className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-icon">{kpi.icon}</span>
              <span className="kpi-trend" style={{ color: kpi.trendUp ? "#22c55e" : "#ef4444" }}>
                {kpi.trend}
              </span>
            </div>
            <div className="kpi-value" style={{ color: kpi.color }}>
              {typeof kpi.value === "number" ? kpi.value.toFixed(2) : kpi.value}
              <span className="kpi-unit">{kpi.unit}</span>
            </div>
            <div className="kpi-label">{kpi.title}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
