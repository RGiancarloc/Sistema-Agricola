"use client";

import { useState } from "react";

interface Alert {
  id: string;
  type: "critical" | "warning" | "info" | "success";
  title: string;
  message: string;
  timestamp: Date;
  parcela_id?: string;
  action?: string;
}

interface AlertPanelProps {
  alerts?: Alert[];
}

export default function AlertPanel({ alerts: initialAlerts }: AlertPanelProps) {
  const [alerts] = useState<Alert[]>(
    initialAlerts || [
      {
        id: "1",
        type: "critical",
        title: "Baja productividad detectada",
        message: "Parcela P-23 muestra productividad 40% below average",
        timestamp: new Date(Date.now() - 3600000),
        parcela_id: "P-23",
        action: "Revisar intervención",
      },
      {
        id: "2",
        type: "warning",
        title: "Temperatura elevada",
        message: "Temperatura proyectada excede óptimo para arándano en SSP5-8.5",
        timestamp: new Date(Date.now() - 7200000),
        action: "Ver simulación",
      },
      {
        id: "3",
        type: "info",
        title: "Nuevo hábitat disponible",
        message: "Hábitat H-15 agregado al sistema",
        timestamp: new Date(Date.now() - 86400000),
      },
      {
        id: "4",
        type: "success",
        title: "Optimización completada",
        message: "MIQCP encontró solución con brecha del 2.3%",
        timestamp: new Date(Date.now() - 172800000),
        action: "Ver recomendaciones",
      },
      {
        id: "5",
        type: "warning",
        title: "Conectividad reducida",
        message: "Conectividad estructural disminuyó 15% en zona norte",
        timestamp: new Date(Date.now() - 259200000),
        parcela_id: "P-45",
      },
    ]
  );

  const [filter, setFilter] = useState<"all" | "critical" | "warning" | "info" | "success">("all");

  const filteredAlerts = alerts.filter((a) => filter === "all" || a.type === filter);

  const typeConfig = {
    critical: { icon: "🚨", bgColor: "#7f1d1d", borderColor: "#dc2626" },
    warning: { icon: "⚠️", bgColor: "#78350f", borderColor: "#f59e0b" },
    info: { icon: "ℹ️", bgColor: "#1e3a5f", borderColor: "#3b82f6" },
    success: { icon: "✅", bgColor: "#14532d", borderColor: "#22c55e" },
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(hours / 24);

    if (days > 0) return `Hace ${days} día${days > 1 ? "s" : ""}`;
    if (hours > 0) return `Hace ${hours} hora${hours > 1 ? "s" : ""}`;
    return "Hace menos de 1 hora";
  };

  const counts = {
    all: alerts.length,
    critical: alerts.filter((a) => a.type === "critical").length,
    warning: alerts.filter((a) => a.type === "warning").length,
    info: alerts.filter((a) => a.type === "info").length,
    success: alerts.filter((a) => a.type === "success").length,
  };

  return (
    <div className="alert-panel">
      <div className="alert-header">
        <h3>Panel de Alertas</h3>
        <div className="alert-counts">
          <span className="badge critical">{counts.critical}</span>
          <span className="badge warning">{counts.warning}</span>
          <span className="badge info">{counts.info}</span>
          <span className="badge success">{counts.success}</span>
        </div>
      </div>

      <div className="alert-filters">
        <button
          className={`filter-btn ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          Todas ({counts.all})
        </button>
        <button
          className={`filter-btn ${filter === "critical" ? "active" : ""}`}
          onClick={() => setFilter("critical")}
        >
          Críticas ({counts.critical})
        </button>
        <button
          className={`filter-btn ${filter === "warning" ? "active" : ""}`}
          onClick={() => setFilter("warning")}
        >
          Advertencias ({counts.warning})
        </button>
        <button
          className={`filter-btn ${filter === "info" ? "active" : ""}`}
          onClick={() => setFilter("info")}
        >
          Info ({counts.info})
        </button>
        <button
          className={`filter-btn ${filter === "success" ? "active" : ""}`}
          onClick={() => setFilter("success")}
        >
          Éxito ({counts.success})
        </button>
      </div>

      <div className="alert-list">
        {filteredAlerts.length === 0 ? (
          <div className="no-alerts">No hay alertas con este filtro</div>
        ) : (
          filteredAlerts.map((alert) => {
            const config = typeConfig[alert.type];
            return (
              <div
                key={alert.id}
                className="alert-item"
                style={{
                  backgroundColor: config.bgColor,
                  borderLeftColor: config.borderColor,
                }}
              >
                <div className="alert-content">
                  <div className="alert-header-row">
                    <span className="alert-icon">{config.icon}</span>
                    <span className="alert-title">{alert.title}</span>
                    <span className="alert-time">{formatTime(alert.timestamp)}</span>
                  </div>
                  <p className="alert-message">{alert.message}</p>
                  {alert.parcela_id && (
                    <span className="alert-parcela">Parcela: {alert.parcela_id}</span>
                  )}
                  {alert.action && (
                    <button className="alert-action">{alert.action}</button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
