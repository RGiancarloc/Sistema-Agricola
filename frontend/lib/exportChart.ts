import { toPng } from "html-to-image";

export interface ExportChartOptions {
  fileName: string;
  chartTitle?: string;
  subtitle?: string;
}

/**
 * Exports a DOM element as a high-resolution PNG image with a light color theme.
 * Temporarily switches styles, text colors, and SVG strokes to clear, light tones.
 */
export async function exportChartAsLightImage(
  elementIdOrElement: string | HTMLElement,
  options: ExportChartOptions
): Promise<void> {
  const element =
    typeof elementIdOrElement === "string"
      ? document.getElementById(elementIdOrElement)
      : elementIdOrElement;

  if (!element) {
    console.error(`[exportChart] Elemento no encontrado:`, elementIdOrElement);
    throw new Error(`Elemento '${elementIdOrElement}' no encontrado en el DOM`);
  }

  // Save and apply light theme class
  element.classList.add("chart-light-export");

  // Track original attributes for SVG lines & text elements that might have hardcoded dark colors
  const modifiedSvgElements: Array<{
    el: Element;
    attr: string;
    origVal: string | null;
  }> = [];

  // Update SVG grid lines and tick text
  element.querySelectorAll("line, path, text, tspan").forEach((node) => {
    const el = node as SVGElement;
    const tagName = el.tagName.toLowerCase();

    // Grid lines
    if (el.closest(".recharts-cartesian-grid") || el.closest(".recharts-polar-grid")) {
      const origStroke = el.getAttribute("stroke");
      modifiedSvgElements.push({ el, attr: "stroke", origVal: origStroke });
      el.setAttribute("stroke", "#e2e8f0");
    }

    // Axis lines
    if (
      el.classList.contains("recharts-cartesian-axis-line") ||
      el.classList.contains("recharts-cartesian-axis-tick-line")
    ) {
      const origStroke = el.getAttribute("stroke");
      modifiedSvgElements.push({ el, attr: "stroke", origVal: origStroke });
      el.setAttribute("stroke", "#64748b");
    }

    // Texts and ticks
    if (tagName === "text" || tagName === "tspan") {
      const origFill = el.getAttribute("fill");
      // Only override if not part of a colored pie slice or special colored indicator
      if (!el.closest(".recharts-pie-labels") || origFill === "#808080" || origFill === "#94a3b8") {
        modifiedSvgElements.push({ el, attr: "fill", origVal: origFill });
        el.setAttribute("fill", "#1e293b");
      }
    }
  });

  // Brief pause for reflow & font rendering
  await new Promise((resolve) => setTimeout(resolve, 180));

  try {
    const dataUrl = await toPng(element, {
      backgroundColor: "#ffffff",
      pixelRatio: 2.5, // Crisp 2.5x resolution for academic reports
      cacheBust: true,
      skipFonts: true, // Prevents cross-origin font stylesheet errors
      filter: (node: HTMLElement) => {
        // Exclude elements marked as no-export (buttons, dropdowns, etc.)
        if (node.classList && (node.classList.contains("no-export") || node.classList.contains("export-btn"))) {
          return false;
        }
        return true;
      },
    });

    // Create download link and trigger
    const link = document.createElement("a");
    const cleanFileName = options.fileName.replace(/\.png$/i, "");
    link.download = `${cleanFileName}.png`;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    // Revert SVG attributes
    modifiedSvgElements.forEach(({ el, attr, origVal }) => {
      if (origVal !== null) {
        el.setAttribute(attr, origVal);
      } else {
        el.removeAttribute(attr);
      }
    });

    // Remove export class
    element.classList.remove("chart-light-export");
  }
}

export interface BatchChartConfig {
  id: string;
  fileName: string;
  title: string;
}

/**
 * Downloads multiple charts sequentially in light mode with a slight pause between each.
 */
export async function exportAllCharts(
  charts: BatchChartConfig[],
  onProgress?: (index: number, total: number, title: string) => void
): Promise<void> {
  for (let i = 0; i < charts.length; i++) {
    const chart = charts[i];
    onProgress?.(i + 1, charts.length, chart.title);
    try {
      await exportChartAsLightImage(chart.id, {
        fileName: chart.fileName,
        chartTitle: chart.title,
      });
      // Pause between downloads for browser stability
      await new Promise((resolve) => setTimeout(resolve, 400));
    } catch (err) {
      console.error(`[exportAllCharts] Error al exportar gráfico '${chart.title}':`, err);
    }
  }
}

