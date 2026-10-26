"use client";

import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Polygon, TileLayer, Tooltip } from "react-leaflet";
import type { FeatureCollection, GeoFeature } from "@/lib/api";

const CROP_COLORS: Record<string, string> = {
  palto: "#22c55e",
  arandano: "#38bdf8",
  esparrago: "#f59e0b",
};

function toLatLngRings(geometry: GeoFeature["geometry"]): number[][][] {
  if (!geometry) return [];
  const g = geometry as { type: string; coordinates: any };
  if (g.type === "Polygon") {
    return g.coordinates.map((ring: number[][]) => ring.map(([lng, lat]) => [lat, lng]));
  }
  if (g.type === "MultiPolygon") {
    return g.coordinates.map((poly: number[][][]) =>
      poly.map((ring) => ring.map(([lng, lat]) => [lat, lng]))
    ).flat();
  }
  return [];
}

function points(geometry: GeoFeature["geometry"]): [number, number][] {
  if (!geometry) return [];
  const g = geometry as { type: string; coordinates: any };
  if (g.type === "Point") return [[g.coordinates[1], g.coordinates[0]]];
  return [];
}

export default function MapView({
  parcelas,
  habitats,
  colmenas,
}: {
  parcelas: FeatureCollection | null;
  habitats: FeatureCollection | null;
  colmenas: FeatureCollection | null;
}) {
  return (
    <MapContainer
      center={[-8.3, -78.85]}
      zoom={10}
      className="map"
      scrollWheelZoom
    >
      <TileLayer
        attribution="&copy; OpenStreetMap"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {habitats?.features.map((f) =>
        toLatLngRings(f.geometry).map((ring, i) => (
          <Polygon
            key={`hab-${f.id}-${i}`}
            positions={ring as any}
            pathOptions={{ color: "#16a34a", fillColor: "#16a34a", fillOpacity: 0.18, weight: 1 }}
          >
            <Tooltip>
              {`Habitat ${f.properties.codigo} (${f.properties.tipo}) · ${f.properties.area_ha} ha`}
            </Tooltip>
          </Polygon>
        ))
      )}
      {parcelas?.features.map((f) =>
        toLatLngRings(f.geometry).map((ring, i) => (
          <Polygon
            key={`par-${f.id}-${i}`}
            positions={ring as any}
            pathOptions={{
              color: CROP_COLORS[f.properties.cultivo] || "#94a3b8",
              fillColor: CROP_COLORS[f.properties.cultivo] || "#94a3b8",
              fillOpacity: 0.35,
              weight: 1,
            }}
          >
            <Tooltip>
              {`${f.properties.codigo} · ${f.properties.cultivo} · ${f.properties.area_ha} ha`}
            </Tooltip>
          </Polygon>
        ))
      )}
      {colmenas?.features.map((f) =>
        points(f.geometry).map((p, i) => (
          <CircleMarker
            key={`col-${f.id}-${i}`}
            center={p}
            radius={5}
            pathOptions={{ color: "#facc15", fillColor: "#facc15", fillOpacity: 0.9 }}
          >
            <Tooltip>{`Colmena ${f.properties.codigo} · ${f.properties.n_colmenas} cajas`}</Tooltip>
          </CircleMarker>
        ))
      )}
    </MapContainer>
  );
}
