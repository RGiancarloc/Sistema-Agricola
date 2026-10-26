const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export { API_BASE };

export type GeoFeature = {
  type: "Feature";
  id?: number;
  geometry: { type: string; coordinates: any } | null;
  properties: Record<string, any>;
};
export type FeatureCollection = { type: "FeatureCollection"; features: GeoFeature[] };

export type SeriesRow = {
  anio: number;
  productividad_media_t_ha: number;
  visitas_medias: number;
  riqueza_media: number;
  deficit_polinizacion_medio: number;
  score_medio: number;
};
export type SimulationResult = {
  escenario: string;
  nombre: string;
  anios: number[];
  serie: SeriesRow[];
  resumen: Record<string, number>;
  n_parcelas: number;
};
