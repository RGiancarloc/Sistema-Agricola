"use client";

import { useState } from "react";
import "leaflet/dist/leaflet.css";
import {
  CircleMarker,
  MapContainer,
  Polygon,
  TileLayer,
  Tooltip,
  LayersControl,
  LayerGroup,
  useMap,
  Marker,
  Popup,
} from "react-leaflet";
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
    return g.coordinates.map((ring: number[][]) => ring.map((coord: number[]) => [coord[1], coord[0]]));
  }
  if (g.type === "MultiPolygon") {
    return g.coordinates
      .map((poly: number[][][]) => poly.map((ring) => ring.map((coord: number[]) => [coord[1], coord[0]])))
      .flat();
  }
  return [];
}

function points(geometry: GeoFeature["geometry"]): [number, number][] {
  if (!geometry) return [];
  const g = geometry as { type: string; coordinates: any };
  if (g.type === "Point") return [[g.coordinates[1], g.coordinates[0]]];
  return [];
}

interface EnhancedMapViewProps {
  parcelas: FeatureCollection | null;
  habitats: FeatureCollection | null;
  colmenas: FeatureCollection | null;
  showParcelas?: boolean;
  showHabitats?: boolean;
  showColmenas?: boolean;
}

function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  map.setView(center, zoom);
  return null;
}

export default function EnhancedMapView({
  parcelas,
  habitats,
  colmenas,
  showParcelas = true,
  showHabitats = true,
  showColmenas = true,
}: EnhancedMapViewProps) {
  const [selectedParcela, setSelectedParcela] = useState<string | null>(null);

  const parcelasByCrop = parcelas?.features.reduce((acc, f) => {
    const crop = f.properties.cultivo;
    if (!acc[crop]) acc[crop] = [];
    acc[crop].push(f);
    return acc;
  }, {} as Record<string, any[]>) || {};

  return (
    <div className="enhanced-map-container">
      <MapContainer center={[-8.3, -78.85]} zoom={10} className="enhanced-map" scrollWheelZoom>
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="OpenStreetMap">
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satélite">
            <TileLayer
              attribution="&copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Térreno">
            <TileLayer
              attribution="&copy; OpenStreetMap"
              url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>

          {showHabitats && (
            <LayersControl.Overlay checked name="Hábitats Semi-naturales">
              <LayerGroup>
                {habitats?.features.map((f) =>
                  toLatLngRings(f.geometry).map((ring, i) => (
                    <Polygon
                      key={`hab-${f.id}-${i}`}
                      positions={ring as any}
                      pathOptions={{
                        color: "#16a34a",
                        fillColor: "#16a34a",
                        fillOpacity: 0.25,
                        weight: 2,
                      }}
                    >
                      <Tooltip>
                        <div>
                          <strong>Hábitat {f.properties.codigo}</strong>
                          <br />
                          Tipo: {f.properties.tipo}
                          <br />
                          Área: {f.properties.area_ha} ha
                        </div>
                      </Tooltip>
                    </Polygon>
                  ))
                )}
              </LayerGroup>
            </LayersControl.Overlay>
          )}

          {showParcelas && (
            <LayersControl.Overlay checked name="Parcelas - Palto">
              <LayerGroup>
                {parcelasByCrop.palto?.map((f) =>
                  toLatLngRings(f.geometry).map((ring, i) => (
                    <Polygon
                      key={`par-pal-${f.id}-${i}`}
                      positions={ring as any}
                      pathOptions={{
                        color: CROP_COLORS.palto,
                        fillColor: CROP_COLORS.palto,
                        fillOpacity: selectedParcela === f.id ? 0.6 : 0.35,
                        weight: selectedParcela === f.id ? 3 : 1,
                      }}
                      eventHandlers={{
                        click: () => setSelectedParcela(f.id),
                      }}
                    >
                      <Tooltip>
                        <div>
                          <strong>{f.properties.codigo}</strong>
                          <br />
                          Cultivo: Palto
                          <br />
                          Área: {f.properties.area_ha} ha
                        </div>
                      </Tooltip>
                    </Polygon>
                  ))
                )}
              </LayerGroup>
            </LayersControl.Overlay>
          )}

          {showParcelas && (
            <LayersControl.Overlay checked name="Parcelas - Arándano">
              <LayerGroup>
                {parcelasByCrop.arandano?.map((f) =>
                  toLatLngRings(f.geometry).map((ring, i) => (
                    <Polygon
                      key={`par-ara-${f.id}-${i}`}
                      positions={ring as any}
                      pathOptions={{
                        color: CROP_COLORS.arandano,
                        fillColor: CROP_COLORS.arandano,
                        fillOpacity: selectedParcela === f.id ? 0.6 : 0.35,
                        weight: selectedParcela === f.id ? 3 : 1,
                      }}
                      eventHandlers={{
                        click: () => setSelectedParcela(f.id),
                      }}
                    >
                      <Tooltip>
                        <div>
                          <strong>{f.properties.codigo}</strong>
                          <br />
                          Cultivo: Arándano
                          <br />
                          Área: {f.properties.area_ha} ha
                        </div>
                      </Tooltip>
                    </Polygon>
                  ))
                )}
              </LayerGroup>
            </LayersControl.Overlay>
          )}

          {showParcelas && (
            <LayersControl.Overlay checked name="Parcelas - Espárrago">
              <LayerGroup>
                {parcelasByCrop.esparrago?.map((f) =>
                  toLatLngRings(f.geometry).map((ring, i) => (
                    <Polygon
                      key={`par-esp-${f.id}-${i}`}
                      positions={ring as any}
                      pathOptions={{
                        color: CROP_COLORS.esparrago,
                        fillColor: CROP_COLORS.esparrago,
                        fillOpacity: selectedParcela === f.id ? 0.6 : 0.35,
                        weight: selectedParcela === f.id ? 3 : 1,
                      }}
                      eventHandlers={{
                        click: () => setSelectedParcela(f.id),
                      }}
                    >
                      <Tooltip>
                        <div>
                          <strong>{f.properties.codigo}</strong>
                          <br />
                          Cultivo: Espárrago
                          <br />
                          Área: {f.properties.area_ha} ha
                        </div>
                      </Tooltip>
                    </Polygon>
                  ))
                )}
              </LayerGroup>
            </LayersControl.Overlay>
          )}

          {showColmenas && (
            <LayersControl.Overlay checked name="Colmenas">
              <LayerGroup>
                {colmenas?.features.map((f) =>
                  points(f.geometry).map((p, i) => (
                    <CircleMarker
                      key={`col-${f.id}-${i}`}
                      center={p}
                      radius={6}
                      pathOptions={{
                        color: "#facc15",
                        fillColor: "#facc15",
                        fillOpacity: 0.9,
                        weight: 2,
                      }}
                    >
                      <Tooltip>
                        <div>
                          <strong>Colmena {f.properties.codigo}</strong>
                          <br />
                          Cajas: {f.properties.n_colmenas}
                        </div>
                      </Tooltip>
                    </CircleMarker>
                  ))
                )}
              </LayerGroup>
            </LayersControl.Overlay>
          )}
        </LayersControl>
      </MapContainer>

      <div className="map-legend">
        <h4>Leyenda</h4>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: CROP_COLORS.palto }}></span>
          <span>Palto</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: CROP_COLORS.arandano }}></span>
          <span>Arándano</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: CROP_COLORS.esparrago }}></span>
          <span>Espárrago</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: "#16a34a" }}></span>
          <span>Hábitat</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: "#facc15" }}></span>
          <span>Colmena</span>
        </div>
      </div>

      {selectedParcela && (
        <div className="map-selection-info">
          <button
            className="close-btn"
            onClick={() => setSelectedParcela(null)}
          >
            ×
          </button>
          <h4>Parcela Seleccionada</h4>
          <p>ID: {selectedParcela}</p>
          <button className="action-btn">Ver Detalles</button>
        </div>
      )}
    </div>
  );
}
