"use client";

import React, { useState } from "react";
import { exportChartAsLightImage } from "@/lib/exportChart";

interface ExportButtonProps {
  targetId: string;
  fileName: string;
  title?: string;
  label?: string;
  variant?: "primary" | "secondary" | "compact";
  className?: string;
  onExportStart?: () => void;
  onExportEnd?: () => void;
}

export default function ExportButton({
  targetId,
  fileName,
  title,
  label = "Descargar Imagen",
  variant = "primary",
  className = "",
  onExportStart,
  onExportEnd,
}: ExportButtonProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (status === "loading") return;

    setStatus("loading");
    onExportStart?.();

    try {
      await exportChartAsLightImage(targetId, {
        fileName,
        chartTitle: title,
      });
      setStatus("success");
      setTimeout(() => setStatus("idle"), 2500);
    } catch (err) {
      console.error("[ExportButton] Error al exportar gráfico:", err);
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    } finally {
      onExportEnd?.();
    }
  };

  const getButtonText = () => {
    switch (status) {
      case "loading":
        return "Generando...";
      case "success":
        return "✓ ¡Descargado!";
      case "error":
        return "✗ Reintentar";
      default:
        return label;
    }
  };

  const getButtonIcon = () => {
    switch (status) {
      case "loading":
        return "⏳";
      case "success":
        return "✓";
      case "error":
        return "⚠";
      default:
        return "📥";
    }
  };

  return (
    <button
      type="button"
      className={`no-export export-chart-btn export-${variant} status-${status} ${className}`}
      onClick={handleDownload}
      disabled={status === "loading"}
      title={`Descargar ${title || "gráfico"} en formato PNG con colores claros`}
    >
      <span className="export-btn-icon">{getButtonIcon()}</span>
      <span className="export-btn-text">{getButtonText()}</span>
    </button>
  );
}
